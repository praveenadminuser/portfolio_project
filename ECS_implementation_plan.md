# Complete AWS ECS & Fargate Architecture Guide

This document serves as your master reference for migrating from raw EC2 instances to a production-grade, serverless container architecture using Amazon ECS and Fargate. 

## 🧠 Core Concepts: ECS vs. Fargate
Before we build, it is critical to understand the relationship between these two services for interviews:
* **ECS (Elastic Container Service) is the *Brain*:** It is the orchestrator. It manages the logic—how many containers should be running, tracking health, and restarting crashed containers. However, it does not physically own any CPUs or RAM.
* **Fargate is the *Muscle*:** It provides the physical computing power. 
  * **The Interview Nuance (Fargate vs EC2):** Under the hood, Fargate *is* rapidly spinning up miniature Linux servers (specifically, highly optimized *Firecracker microVMs*) exactly like an EC2 instance. However, the critical difference is **Visibility and Management**. 
  * With **EC2**, you rent the *entire* server. It sits in your account. You can SSH into it, you must run security patches on the OS, and if you leave it on by accident, you get billed for the whole server.
  * With **Fargate (Serverless)**, Amazon completely hides the server from you. You cannot SSH into the underlying Linux host, and you don't patch the OS. You just say "run my container," and Amazon secretly provisions an invisible micro-server, executes your code, and destroys the server the millisecond it finishes. You only pay for the exact seconds your container is actively running!
---

## 🛠️ Phase 1: AWS Console Setup (Fargate Implementation)

Follow these exact steps in the AWS Console to provision your serverless infrastructure. *We must do this before touching the GitHub Actions code!*

### Step 1: Create the ECS Cluster
*The Cluster is just an empty logical grouping folder for your application.*
1. Log into AWS Console and search for **ECS (Elastic Container Service)**.
2. On the left menu, click **Clusters**, then hit the orange **Create cluster** button.
3. **Cluster name:** `portfolio-cluster`
4. **Infrastructure:** AWS Fargate (Serverless) should automatically be selected by default.
5. Click **Create** at the bottom.

### Step 2: Create a Task Definition
*The Task Definition is the "Blueprint" that tells ECS exactly what Docker image to use and how much RAM/CPU to give the Fargate MUSCLE.*
1. On the left menu, click **Task Definitions**, then hit **Create new task definition** (with new experience).
2. **Task definition family setting:** Name it `portfolio-task`.
3. **Launch type:** Select **AWS Fargate**.
4. **Operating system/Architecture:** Linux / X86_64.
5. **Task size:** Select **.5 vCPU** and **1 GB** memory (keeps costs incredibly low).
6. **Container details:**
   * **Name:** `portfolio-container`
   * **Image URI:** Look up your unique Amazon ECR URL from yesterday and paste the `latest` tag here *(e.g., `123456789.dkr.ecr.eu-north-1.amazonaws.com/portfolio_ecr_registry:latest`)*.
   * **Port mappings:** Set Container port to **5000** (because Python Flask defaults to port 5000). Set protocol to **TCP**.
7. Scroll to the bottom and click **Create**.

### Step 3: Run the ECS Service
*The Service is the "Manager" that actually reads your blueprint (Task Definition) and orders Fargate to start the engines and keep them running 24/7.*
1. Go back to your `portfolio-cluster` on the **Clusters** page.
2. In the Services tab at the bottom, click **Create**.
3. **Compute options:** Select **Launch type** and choose **Fargate**.
4. **Deployment configuration:** 
   * Application type: **Service**
   * Family: `portfolio-task` (select the blueprint you just made)
   * Desired tasks: **1** (This tells ECS to always ensure exactly 1 container is running).
5. **Networking (CRITICAL):**
   * Expand the Networking section. 
   * You will see a **Security group** is being created for you. Look for the "Inbound rules" section.
   * Ensure it allows **Custom TCP** on port **5000** from **Anywhere (0.0.0.0/0)**. *If you do not do this, the internet firewall will block traffic to your Flask app!*
   * Make sure **Public IP** is turned **ON**.
6. Click **Create** at the bottom.

---

> [!IMPORTANT]
> **What happens next?**
> As soon as you click Create, AWS ECS takes your ECR Docker image, hands it to a serverless Fargate machine, and spins it up. 
> To see your live website, click on your newly created Service, go to the **Tasks** tab, click the running task, and look for its **Public IPv4 address**. Copy it and visit `http://[IP_ADDRESS]:5000` in your browser!

---

## 🤖 Phase 2: Extracting the Task Definition

To automate deployments via GitHub Actions, we need a local copy of the ECS Task Definition (your blueprint) in our repository. This allows our CI/CD pipeline to register new revisions dynamically.

### Step 1: Download the Task Definition
1. Open the **AWS Console** and navigate to **ECS**.
2. Go to **Task Definitions** on the left menu.
3. Click on your `portfolio-task` family, then click the latest active revision.
4. Click the **JSON** tab near the top.
5. Copy the entire JSON content.

### Step 2: Save to the Repository
1. Open your code editor and navigate to the `portfolio_project` repository.
2. Create a new file in the root directory named `task-definition.json`.
3. Paste the copied JSON content into this file.
4. **Important Cleanup:** AWS includes some fields that shouldn't be pushed back during automation. Remove the following top-level keys from the end of the JSON file:
   - `taskDefinitionArn`
   - `revision`
   - `status`
   - `requiresAttributes`
   - `compatibilities`
   - `registeredAt`
   - `registeredBy`

## 🚀 Phase 3: Updating GitHub Actions (`deploy.yml`)

Now we must completely rewrite the deployment portion of our CI/CD pipeline. Instead of SSH-ing into an EC2 instance, we will use official AWS Actions to update our ECS service.

### Step 1: Update GitHub Secrets (If Needed)
Ensure the following secrets are available in your **GitHub Repository Settings > Secrets and variables > Actions**:
* `AWS_ACCESS_KEY_ID` (Already exists from our earlier EC2 setup)
* `AWS_SECRET_ACCESS_KEY` (Already exists)
* *Note: The old `EC2_HOST` and `EC2_SSH_KEY` are no longer needed and can be safely deleted.*

### Step 2: Rewrite the `.github/workflows/deploy.yml` File
Update your `deploy.yml` to look exactly like this:

```yaml
name: Deploy to Amazon ECS

on:
  push:
    branches: [ "main" ]
  workflow_dispatch:

env:
  AWS_REGION: eu-north-1                   # Your specific AWS region
  ECR_REPOSITORY: portfolio_ecr_registry   # Your ECR repository name
  ECS_SERVICE: portfolio-task              # The name of your ECS service
  ECS_CLUSTER: portfolio-cluster           # The name of your ECS cluster
  ECS_TASK_DEFINITION: ./task-definition.json # Path to the JSON file we created
  CONTAINER_NAME: portfolio-container      # Name of the container in the task definition

jobs:
  deploy:
    name: Build & Deploy
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ env.AWS_REGION }}

    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v2

    - name: Build, tag, and push image to Amazon ECR
      id: build-image
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        IMAGE_TAG: ${{ github.sha }}
      run: |
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
        docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest
        echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT

    - name: Fill in the new image ID in the Amazon ECS task definition
      id: task-def
      uses: aws-actions/amazon-ecs-render-task-definition@v1
      with:
        task-definition: ${{ env.ECS_TASK_DEFINITION }}
        container-name: ${{ env.CONTAINER_NAME }}
        image: ${{ steps.build-image.outputs.image }}

    - name: Deploy Amazon ECS task definition
      uses: aws-actions/amazon-ecs-deploy-task-definition@v2
      with:
        task-definition: ${{ steps.task-def.outputs.task-definition }}
        service: ${{ env.ECS_SERVICE }}
        cluster: ${{ env.ECS_CLUSTER }}
        wait-for-service-stability: true
```

### Step 3: Architecture Breakdown
*   **`amazon-ecr-login`:** Replaces our raw `awscli` bash commands and automatically logs Docker in.
*   **`amazon-ecs-render-task-definition`:** Takes your fresh `task-definition.json`, cracks it open, and dynamically overwrites the `Image URI` line to point to the brand-new Git commit tag.
*   **`amazon-ecs-deploy-task-definition`:** Takes the dynamically rendered blueprint and uploads it back to AWS, automatically creating a new revision and updating your ECS Service!
