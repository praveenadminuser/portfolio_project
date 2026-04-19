# CI/CD Pipeline & AWS Architecture: Interview Study Guide

This document contains the complete step-by-step architecture and configuration process we used to build a fully automated Continuous Integration and Continuous Deployment (CI/CD) pipeline. Use this as your master reference sheet for interviews!

## 🏗️ High-Level Project Architecture

**The Scenario:** You built a Python Flask web application and wanted to deploy it to the cloud fully automatically whenever you pushed new code.
**The Technologies:** Docker, GitHub Actions, AWS IAM, AWS ECR, AWS EC2.

**The Flow (How it works in production):**
1. **Developer (You)** pushes a code change (e.g., adding an `/about` route) to the `main` branch.
2. **GitHub Actions** detects the push and wakes up.
3. **CI Phase (Build):** The GitHub server uses hidden **AWS IAM Secrets** to securely log into Amazon. It uses your `Dockerfile` to build the app, and pushes the new image up to **AWS ECR (Elastic Container Registry)**.
4. **CD Phase (Deploy):** The GitHub server uses a hidden **.pem SSH Key** to remotely tunnel into your **AWS EC2** instance. It forces the EC2 instance to pull the newly built image from ECR, stop the old container, and run the new one on Port 80.

---

## 📝 Detailed Configuration Steps

If an interviewer asks, *"Walk me through exactly how you configured this from scratch,"* here are the exact steps you took across all platforms:

### 1. AWS IAM (Identity & Security)
*Why: GitHub needs permission to push files into your Amazon account. We never use root credentials; we create a robot user.*
* **Step A:** Open AWS Console -> Go to **IAM** -> **Users** -> **Create User** (e.g., `github-actions-bot`).
* **Step B:** Click "Attach policies directly" and select **`AmazonEC2ContainerRegistryPowerUser`**. This follows the principle of *Least Privilege* (giving it just enough power to push images, nothing else).
* **Step C:** Go to the user's "Security credentials" tab -> **Create access key**.
* **Step D:** Copy the **Access Key ID** and **Secret Access Key** (you only get to see the secret key once!).

### 2. AWS ECR (Elastic Container Registry)
*Why: You need a secure bucket to store your compiled Docker images before the web server downloads them.*
* **Step A:** Open AWS Console -> Go to **ECR**.
* **Step B:** Click **Create repository**.
* **Step C:** Make it **Private** and name it exactly what your code expects (e.g., `portfolio_ecr_registry` in region `eu-north-1`).

### 3. AWS EC2 (The Live Web Server)
*Why: This is the actual Linux computer that runs 24/7, hosting your website to the public internet.*
* **Step A:** Open AWS Console -> Go to **EC2** -> **Launch Instance**.
* **Step B:** Choose **Ubuntu** (Free tier) and a `t2.micro` or `t3.micro` size.
* **Step C:** Create and immediately download a **Key Pair** (a `.pem` file). *This is the master key to log into the server.*
* **Step D:** Under Network/Security Group settings, put checkmarks next to **Allow SSH traffic (Port 22)** and **Allow HTTP traffic (Port 80)**.

### 4. GitHub Actions (The Automation Engine)
*Why: This glues everything together and runs the script whenever code is pushed.*
* **Step A:** Go to your GitHub Repository website -> **Settings** -> **Secrets and variables** -> **Actions**. 
* **Step B:** You created four highly sensitive Repository Secrets so they are never hardcoded in the codebase:
  1. `AWS_ACCESS_KEY_ID` (From IAM)
  2. `AWS_SECRET_ACCESS_KEY` (From IAM)
  3. `EC2_HOST` (The Public IP address of your EC2 instance)
  4. `EC2_SSH_KEY` (The entire exact text copied from inside your downloaded `.pem` file)

### 5. Writing the Pipeline Code (`deploy.yml`)
*Why: GitHub Actions looks for a specifically formatted YAML file inside the `.github/workflows/` folder.*
* **Triggers:** You set `on: push: branches: [main]` so it only deploys production code, and `workflow_dispatch:` to get a manual "Run Workflow" button in the UI.
* **The `build` Job:**
  * `uses: actions/checkout@v4`: Downloads the repo code onto GitHub's server.
  * `uses: aws-actions/configure-aws-credentials`: Securely injects those AWS Secrets.
  * `uses: docker/build-push-action`: Runs your `Dockerfile` and pushes the finished image up to your ECR URL.
* **The `deploy` Job:**
  * `needs: build`: Tells this step to wait until the image finishes uploading.
  * `uses: appleboy/ssh-action`: Opens the remote connection to your EC2 instance using your `.pem` key.
  * **The Bash Script (Running directly on EC2):**
    1. Installs official versions of `awscli` and `docker`.
    2. Runs `docker pull` to download the image from ECR.
    3. Runs `docker stop` and `docker rm` to kill the old container.
    4. Runs `docker run -d -p 80:5000 ...` to start the new container in the background, mapping the internet port (80) to Flask's internal port (5000).

---

> [!TIP]
> **Interview Pro-Tip:**
> If an interviewer asks you what you struggled with, mention the Region Mismatch Error! Explain how your AWS API authentication failed with a *"name unknown"* error because the GitHub Action defaulted to pushing the image to `us-east-1` (Virginia), but you intentionally provisioned your ECR bucket in `eu-north-1` (Stockholm) for better latency. Changing the AWS_REGION environment variable instantly fixed the pipeline. Interviewers love real-world debugging stories!
