# Complete Guide: Deploying Flask Application to AWS EKS

This guide walks you through migrating your Flask application from AWS ECS (Elastic Container Service) to AWS EKS (Elastic Kubernetes Service). We will use AWS Fargate for serverless compute, mirroring our ECS experience, but utilizing the massive ecosystem of Kubernetes.

---

## Phase 1: Understanding EKS vs. ECS

### What is EKS?
EKS is Amazon's managed Kubernetes service. Kubernetes (K8s) is the industry standard for container orchestration, originally developed by Google.

### EKS vs. ECS: Why use Kubernetes?

1. **Vendor Lock-in:** ECS is an AWS-only proprietary system. Kubernetes is open-source. A Kubernetes manifest will run on AWS EKS, Google GKE, Azure AKS, or even your local machine (Minikube/Docker Desktop) with minimal changes.
2. **Ecosystem & Tools:** Kubernetes has a vast, massive community. Tools like Helm (Package manager for K8s), Prometheus (Monitoring), and Istio (Service Mesh) integrate natively.
3. **Declarative State Management:** In Kubernetes, you write YAML "Manifests" that declare the *desired state* of your system (e.g., "I want 3 replicas of the Flask container, exposed on port 80"). Kubernetes constantly self-heals by killing misbehaving pods and starting new ones to ensure the current state matches your desired state.
4. **Complexity:** The main trade-off is complexity. ECS uses Tasks and Services. K8s uses Pods, ReplicaSets, Deployments, Services, Ingress, ConfigMaps, Secrets, etc.

---

## Phase 2: Prerequisites & Infrastructure Provisioning

To work with EKS, you need a different set of command-line tools.

### 1. Required Local Tools Configuration (Windows)

Before creating the cluster, you must install and configure three core tools on your local machine:

#### A. AWS CLI (Authentication)
The AWS CLI securely connects your terminal to your AWS account.
1. Download and run the official installer: [AWS CLI Installer for Windows](https://awscli.amazonaws.com/AWSCLIV2.msi)
2. Open a new terminal and verify the installation: `aws --version`
3. Configure your credentials by typing `aws configure` and entering your IAM keys:
   - **AWS Access Key ID:** Your IAM User Access Key
   - **AWS Secret Access Key:** Your IAM User Secret Key
   - **Default region name:** `us-east-1`
   - **Default output format:** `json`

#### B. eksctl (Cluster Builder)
`eksctl` is used to dramatically simplify the creation of the EKS cluster and its underlying remote infrastructure.
1. For Windows, the easiest way to install it is using `winget` (Windows Package Manager) in PowerShell:
   ```powershell
   winget install weavenetworks.eksctl
   ```
2. Verify: `eksctl version`

#### C. kubectl (Kubernetes Deployer)
`kubectl` is the tool used to send your YAML manifests to the cluster to run your Flask app.
1. Download the Windows executable using PowerShell:
   ```powershell
   curl.exe -LO "https://dl.k8s.io/release/v1.30.0/bin/windows/amd64/kubectl.exe"
   ```
2. Move `kubectl.exe` directly into your `portfolio_project` directory, or ideally, add it to your system PATH.
3. Verify: `kubectl version --client`

### 2. Provisioning the EKS Cluster (using Fargate)
Instead of clicking through the AWS Console, the easiest way to spin up an EKS cluster is via `eksctl`.

Run the following command in your terminal. We will use the `fargate` flag so you don't have to manage EC2 nodes, just like your ECS setup:

```bash
eksctl create cluster \
  --name flask-k8s-cluster \
  --region us-east-1 \
  --fargate
```

> **Warning:** Creating an EKS cluster takes 15-20 minutes. It provisions a VPC, NAT Gateways, the Control Plane, and Fargate profiles automatically in the background using CloudFormation.

### 3. Verify Cluster Connection
Once complete, `eksctl` will automatically update your `~/.kube/config` file. Test your connection:
```bash
kubectl get nodes
kubectl get pods -A
```

---

## Phase 3: Application Manifests

In Kubernetes, we define everything via YAML manifests. For a web application, you must decouple "compute" from "networking" using two primary resources: a **Deployment** and a **Service**.

**Why do we need both?**
- **The Deployment (Compute - The "What"):** Keeps your containers running. Pods (containers) in Kubernetes are ephemeral—if a node crashes or you update code, old Pods die and new ones are born with entirely new IP addresses. The Deployment serves as a manager, ensuring your desired number of Pods are always running (self-healing). However, without a Service, these Pods are unreachable from the internet.
- **The Service (Networking - The "Where"):** Keeps your application reachable. It acts as a stable, permanent entry point. The Service receives traffic from the internet (via an AWS Load Balancer) and intelligently routes it only to the ephemeral Pods that are currently healthy and active.

### 1. The Deployment (`k8s/flask-deployment.yaml`)
A Deployment manages a set of identical Pods (a Pod is essentially a wrapper around your Docker container). It handles scaling and rolling code updates without downtime.

Here is the manifest, broken down line-by-line:

```yaml
# 1. API Version & Kind
# Tells Kubernetes what type of resource we want to create. 
# "apps/v1" is the API group, and "Deployment" is the specific controller.
apiVersion: apps/v1
kind: Deployment

# 2. Metadata
# Identifies this specific Deployment resource within your cluster.
metadata:
  name: flask-app-deployment
  labels:
    app: flask-web

# 3. Deployment Specification (The Desired State)
spec:
  # How many identical copies of your container should run?
  replicas: 2 
  
  # The Selector defines how the Deployment knows which Pods it owns. 
  # It continuously looks for any Pod running with the label "app: flask-web".
  selector:
    matchLabels:
      app: flask-web 

  # 4. Pod Template
  # When the Deployment needs to spin up a new replica, it uses this template.
  template:
    metadata:
      # These labels get attached to the newly created Pods.
      # Notice this matches the selector above exactly!
      labels:
        app: flask-web
    spec:
      containers:
      - name: flask-container
        # The Docker image to pull from your AWS ECR Registry.
        # (Replace <YOUR_AWS_ACCOUNT_ID> with your actual 12-digit AWS ID)
        image: <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/flask-app-repo:latest 
        ports:
        # The internal port your Flask application listens on within the container
        - containerPort: 8000
```

### 2. The Service (`k8s/flask-service.yaml`)
Pods are ephemeral (they die and get new random IP addresses). A Kubernetes *Service* gives them a static IP/hostname. To expose it to the internet on AWS, we use the type `LoadBalancer`, which automatically provisions an AWS Classic Load Balancer.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: flask-app-service
spec:
  type: LoadBalancer # Triggers AWS to create a real load balancer
  selector:
    app: flask-web # Routes traffic to pods with this label
  ports:
    - protocol: TCP
      port: 80          # The exposed port on the Load Balancer
      targetPort: 8000  # The port your Flask app listens on in the container
```

### 3. Applying the Manifests (Manual approach)
If we were doing this manually, we apply these files using `kubectl`:
```bash
kubectl apply -f k8s/flask-deployment.yaml
kubectl apply -f k8s/flask-service.yaml
```

To get your public URL, you'd check the services:
```bash
kubectl get services
```
*Look for the `EXTERNAL-IP` of the `flask-app-service`. It will be a long AWS URL.*

---

## Phase 4: CI/CD Pipeline Update (GitHub Actions)

When you do git push, we want GitHub Actions to:
1. Build the new Docker image.
2. Push to ECR (Same as before!).
3. Update the Kubernetes Deployment to use the new image.

### Updating `.github/workflows/deploy.yml`
You only need to change the final steps of your ECS pipeline. The "Deploy to ECS" step gets replaced with a "Deploy to EKS" step.

```yaml
      # ... Previous steps (checkout, configure-aws-credentials, login-ecr, build-and-push) ...

      - name: Setup kubectl
        uses: azure/setup-kubectl@v3
        with:
          version: 'latest'
          
      - name: Update kubeconfig
        run: aws eks update-kubeconfig --name flask-k8s-cluster --region us-east-1

      - name: Deploy to EKS
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: flask-app-repo
          IMAGE_TAG: ${{ github.sha }}
        run: |
          # Use envsubst to inject the image URI dynamically, or simply restart the deployment
          # A simple rollout restart forces the cluster to pull the 'latest' tag again:
          kubectl rollout restart deployment flask-app-deployment
```

### How the Automation Flow Works (Zero-Downtime Updates)

Once this pipeline is set up, you rarely need to modify the EKS infrastructure. The fully automated deployment flow works like this:

1. **Trigger:** You run `git push` with your new Python code.
2. **Build & Push:** GitHub Actions wakes up, builds the new Docker image, and pushes it to your AWS ECR.
3. **Notify Kubernetes:** *(Crucial Step)* Pods do not automatically watch ECR for changes. GitHub Actions must securely connect to your EKS cluster and run the `kubectl rollout restart` command shown above to tell the cluster that new code is available.
4. **Rolling Update:** Kubernetes receives the command and initiates a "Zero-Downtime Rolling Update." It spins up 1 *new* Pod pulling the fresh `latest` image from ECR. Once that new Pod is healthy and accepting traffic, it kills 1 *old* Pod. It repeats this process until all Pods are replaced.

Because of this architecture, your application never goes offline during a code update, and the process is completely "hands-off" for the developer!

---

## Phase 5: Resource Cleanup (CRITICAL)

Unlike ECS Fargate which is practically free when not actively running a task, the EKS Control Plane costs ~$72/month (~$0.10/hr) just to exist, regardless of whether you have traffic.

When you are done testing, you **MUST MUST MUST** delete the cluster to stop billing.

```bash
eksctl delete cluster --name flask-k8s-cluster --region us-east-1
```
This command ensures the VPC, NAT Gateways, Load Balancers, and EC2/Fargate instances are all cleanly removed.

---

## Phase 6: Local Testing (Without Cloud)

Before spending money on AWS, you can easily test these Kubernetes manifests right on your laptop! 

### 1. Prerequisites
- Have **Docker Desktop** installed on your machine.
- Open Docker Desktop -> **Settings** (Gear icon) -> **Kubernetes** -> Check **"Enable Kubernetes"**.
- Click "Apply & Restart". This secretly creates a fully functional, single-node cluster directly on your machine.

### 2. Verify Local Context
Because this cluster is local, you skip the `aws cli` and `eksctl` completely. Tell `kubectl` to talk to Docker instead of AWS:
```bash
kubectl config use-context docker-desktop
kubectl get nodes
```
*(You should see your laptop acting as a single node named `docker-desktop`)*

### 3. Deploying Locally
1. Build your Docker image locally so your laptop's cluster can see it:
   ```bash
   docker build -t flask-app-repo:latest .
   ```
2. **Temporarily** modify your `k8s/flask-deployment.yaml` to point to this new local image instead of AWS:
   ```yaml
   # Change from the AWS ECR URL to just:
   image: flask-app-repo:latest
   ```
3. Apply the manifests exactly like you would in the cloud:
   ```bash
   kubectl apply -f k8s/flask-deployment.yaml
   kubectl apply -f k8s/flask-service.yaml
   ```

### 4. Viewing the Application
When Kubernetes sees `type: LoadBalancer` in a local environment, it automatically maps port 80 directly to your local machine. 

Simply open your web browser and navigate to:
**`http://localhost`**
