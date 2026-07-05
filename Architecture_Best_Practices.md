# Portfolio Optimization Architecture & Flow

This document details the end-to-end architecture, data flow, and implementation best practices for the Portfolio Optimization application. It explains how the React Frontend, Flask Backend, AWS infrastructure, and the Axioma API interact to create a highly scalable, asynchronous, and secure system.

---

## Part 1: End-to-End Project Data Flow

This section explains the step-by-step lifecycle of a user request, highlighting exactly **which service is used where**. 

### Step 1: User Interaction (React on S3)
*   **Action:** The user types your web address into their browser and accesses your application. They configure a portfolio "sleeve" for optimization and upload any initial starting trade data.
*   **AWS Services:** The **React UI** is a static Single Page Application (SPA) hosted entirely on an **AWS S3 Bucket** (and optionally distributed globally via **AWS CloudFront** CDN).

### Step 2: API Ingestion (Flask API on EKS Fargate)
*   **Action:** When the user clicks "Submit", the React UI makes a REST API call holding the optimization parameters.
*   **AWS Services:** This request hits an Application Load Balancer and is routed to your **Flask Backend** running inside container pods on an **AWS EKS (Elastic Kubernetes Service)** cluster. These pods run on **AWS Fargate**, meaning they are serverless and scale out automatically.
*   **Processing:** Flask accepts the request, validates the user, saves any uploaded starting trade files directly into a central **AWS S3 Bucket**, and generates a unique tracking `Task ID`.

### Step 3: Event Decoupling (AWS SQS)
*   **Action:** Because Axioma optimizations are massive calculations that take several minutes, Flask cannot hold the HTTP connection open (it would time out).
*   **AWS Services:** Flask takes the `Task ID` and the optimization parameters and writes a message into an **AWS SQS (Simple Queue Service)** queue. 
*   **Response:** The Flask API immediately replies to the React UI with an HTTP 202 (Accepted) response and the `Task ID`. From the API's perspective, the synchronous job is done. 

### Step 4: Background Processing & Axioma (EC2 Worker Node)
*   **Action:** A completely separate backend worker process is actively listening for work to do.
*   **AWS Services:** This worker runs continuously on an **AWS EC2 Instance** (ideally placed inside an Auto Scaling Group for resilience). The EC2 instance polls the SQS queue.
*   **Integration:** When a message arrives, the EC2 worker downloads the initial trade data from S3, packages the request, and makes the heavy synchronous API calls to the **third-party Axioma API**. 
*   *Security Note:* The EC2 instance does not have hardcoded Axioma API keys. It securely retrieves them from **AWS Secrets Manager** using an attached IAM Role.

### Step 4B: Bulk Processing & Dynamic Orchestration (>10 Sleeves)
*   **Action:** If a user requests a massive optimization batch (e.g., > 10 sleeves simultaneously), processing them sequentially on a single worker would take too long.
*   **AWS Services:** Instead of the standard worker, this request triggers an **RPA (Robotic Process Automation) Orchestrator Node**.
*   **Dynamic Infrastructure:** The Orchestrator node utilizes **AWS CloudFormation** to dynamically spin up a temporary, dedicated fleet of EC2 worker nodes automatically.
*   **Execution & Tear Down:** Each temporary EC2 node processes a portion of the sleeves with Axioma. Crucially, once the Orchestrator verifies that all workers have completed their tasks, the Orchestrator executes a teardown sequence—terminating all the temporary EC2 workers and then killing itself to minimize runaway AWS cloud costs.

### Step 5: State Updating (Database & S3)
*   **Action:** Once the optimizations are complete, the respective EC2 worker receives the optimized trades.
*   **AWS Services:** The worker uploads the final, optimized result files into the **S3 Bucket**. It then connects to the central Database (e.g., **AWS RDS** or **DynamoDB**) and updates the task's database row, changing the status from `pending` to `completed`, and saving the new S3 file paths. 

### Step 6: Delivery via Pre-signed URLs (S3 to React)
*   **Action:** While the EC2 worker was busy, the React UI was quietly checking the Flask API every few seconds asking, "Is Task #123 done yet?"
*   **AWS Services:** Once the Flask API sees the `completed` status in the database, it grabs the S3 file path.
*   **Optimization:** Instead of Flask downloading the huge file natively to send to the UI, Flask uses `boto3` to instantly generate a secure, 5-minute **S3 Pre-signed URL**.
*   **Delivery:** Flask hands this URL to React. The user's browser uses that exact URL to download the heavy trade files directly from S3. This perfectly protects your EKS servers from running out of bandwidth or memory.

---

## Part 2: Architecture Implementation Best Practices

The architectural flow described above naturally enforces several modern best practices.

### 1. Application Decoupling
*   Treat the React UI and the Flask API as entirely separate entities. 
*   **CORS Management:** Configure `flask-cors` to explicitly allow traffic *only* from the specific S3/CloudFront domain where the React application is hosted.

### 2. Asynchronous Optimization Workflow
*   **Decoupled Processing via SQS:** Writing to SQS and immediately responding to the UI is excellent design as it prevents HTTP timeouts.
*   **Worker Node Resilience:** Ensure your background polling EC2 instance is part of an Auto Scaling Group (ASG) of size 1. This way, if the EC2 instance crashes or is accidentally terminated, AWS automatically spins up a new one to continue processing the SQS queue without manual intervention.
*   **UI Status Polling:** Implement **exponential backoff** in your React UI polling logic (e.g., check every 2 seconds, then 5 seconds, then 10). Because optimizations take time, you don't want 1,000 users pinging your Flask API every 0.5 seconds and causing a self-inflicted DDoS attack.

### 3. Storage Efficiency (S3 & VPCs)
*   **Pre-signed URLs:** Using Pre-Signed URLs is the gold standard for serving large files. It offloads all heavy file networking to AWS's edge infrastructure rather than your container's CPU.
*   **VPC Endpoints:** Ensure both your EKS Fargate pods and your EC2 worker nodes are configured to use an **S3 Gateway VPC Endpoint**. This ensures all the heavy file transfers between EKS/EC2 and S3 stay strictly within the AWS private network, completely bypassing expensive NAT Gateway data processing charges.

### 4. Kubernetes (EKS + Fargate) Rules
*   **IAM Roles for Service Accounts (IRSA):** Your Flask app needs permissions to access S3 or SQS. Do not pass static AWS Access Keys. Instead, create an IAM Role giving SQS/S3 access, and attach it to the Kubernetes `ServiceAccount` your pod uses. AWS securely injects the credentials.
*   **Liveness and Readiness Probes:** Define these in your `flask-deployment.yaml`. 
    *   *Readiness Probe:* Tells the Load Balancer to only send traffic when Flask is fully booted.
    *   *Liveness Probe:* Tells EKS to automatically restart the container if the application deadlocks.
*   **Statelessness:** Ensure the Flask container stores **zero** local files or session data. This absolute statelessness allows EKS Fargate to autoscale out from 2 pods to 50 pods instantly under heavy traffic without corrupting data.

### 5. CI/CD Operations (GitHub Workflows)
*   **Immutable Image Tags:** Avoid deploying with the `latest` tag in `flask-deployment.yaml`. Have your GitHub Action build the Docker image as `myapp:git-sha`, push to ECR, and programmatically update the EKS deployment manifest with that specific SHA tag. This guarantees exact rollbacks if an update fails.

---

## Part 3: Zero-Downtime Deployment Lifecycle (EKS)

When developers write new code for the Flask API, the infrastructure seamlessly updates the live application without causing errors for active users.

### Step 1: Image Build & ECR Push
*   **Action:** When a developer merges code into the `main` branch, a **GitHub Actions** pipeline is triggered.
*   **Process:** The pipeline builds a new Docker Image containing the updated Python code and pushes it to an **AWS ECR (Elastic Container Registry)** repository with a unique tag (e.g., `v2.0`).

### Step 2: Notifying EKS
*   **Action:** *Crucially, EKS does not actively monitor ECR for new images.* It must be explicitly told to update.
*   **Process:** The final step of the GitHub Action runs a command like `kubectl set image deployment/flask-api flask-container=my-ecr-repo:v2.0`. This command securely connects to the EKS Control Plane and alters the exact Deployment manifest, automatically informing Kubernetes that the desired target state has changed from `v1.0` to `v2.0`.

### Step 3: The Rolling Update (Safeguarding Traffic)
*   **Action:** Upon receiving the new deployment spec, EKS orchestrates a programmatic **Rolling Update**.
*   **Process:**
    1. EKS does **not** terminate the existing `v1.0` pods. They continue serving live user traffic.
    2. EKS pulls the new `v2.0` image from ECR and spins up a brand new `v2.0` pod alongside the old ones.
    3. EKS continuously pings the **Readiness Probe** (`/health` endpoint) on the new `v2.0` pod. It refuses to send any user traffic to this pod until the Python code fully boots up and returns a `200 OK`.
    4. Once the new pod is ready, EKS adds it to the Load Balancer to accept traffic. It simultaneously sends a `SIGTERM` signal to one of the old `v1.0` pods. This tells the old pod: *"Finish whatever SQS writing you are currently doing, stop accepting new requests, and then shut down gracefully."*
    5. This progressive swap repeats dynamically until all `v1.0` pods are replaced by `v2.0` pods. The users experience absolutely zero downtime or dropped HTTP connections.
