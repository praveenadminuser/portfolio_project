# EKS Deployment — Quick Recap (What, Not How)

A high-level checklist of **what** needs to happen to get the Flask app running on AWS EKS, and **why** each step exists. For the actual commands and manifests, see **[EKS_implementation_plan.md](EKS_implementation_plan.md)**.

> Use this doc to remember the shape of the process. Jump to the detailed plan only when you need the exact command.

---

## The big picture

You are moving the Flask app from ECS to EKS (managed Kubernetes) running on **Fargate** (serverless — no EC2 nodes to manage). The flow is: set up local tools & credentials → provision a cluster → describe the app as YAML → let CI/CD push updates → tear it down when done.

---

## 1. Set up local tools & authentication

_(Detailed plan → Phase 2, Section 1)_

- [ ] **Install AWS CLI** — lets your terminal talk to AWS.
- [ ] **Install eksctl** — the tool that builds the whole cluster with one command.
- [ ] **Install kubectl** — the tool that sends your YAML to the cluster.
- [ ] **Create an IAM admin user** (do **not** use root keys). Root can do anything including closing the account, so:
  - Bootstrap once with a temporary root key.
  - Create a dedicated `admin-cli` IAM user and give it `AdministratorAccess`.
  - Save its keys as a named `admin` profile in the CLI.
  - Delete the root key and turn on MFA on root.
  - **Why:** least-privilege, revocable identity — the standard secure practice.

---

## 2. Provision the EKS cluster

_(Detailed plan → Phase 2, Section 2–3)_

- [ ] **Create the cluster with eksctl** using the `--fargate` flag.
  - **Why Fargate:** no servers to patch or scale; matches the ECS serverless experience.
  - **Heads-up:** takes ~15–20 min; it builds a VPC, NAT gateways, control plane, and Fargate profiles behind the scenes.
- [ ] **Verify the connection** — confirm `kubectl` can see the cluster's nodes/pods.

---

## 3. Describe the application (Kubernetes manifests)

_(Detailed plan → Phase 3)_

- [ ] **Write a Deployment** — the "compute." Says how many copies (replicas) of the container to run and which image to pull from ECR. Self-heals by restarting dead pods.
- [ ] **Write a Service (type LoadBalancer)** — the "networking." Gives the ephemeral pods one stable public entry point via an AWS load balancer.
  - **Why both:** pods die and get new IPs constantly; the Service is the fixed address in front of them.
- [ ] **Apply the manifests** with `kubectl apply` and grab the public URL from the Service's external IP.

---

## 4. Automate deployments (CI/CD)

_(Detailed plan → Phase 4)_

- [ ] **Update GitHub Actions** so that on `git push` it: builds the image → pushes to ECR → tells EKS to roll out the new version.
  - **Key point:** pods don't watch ECR on their own; the pipeline must run `kubectl rollout restart` to trigger the update.
  - **Result:** zero-downtime rolling updates, hands-off for you.

---

## 5. Clean up (do not skip)

_(Detailed plan → Phase 5)_

- [ ] **Delete the cluster** when finished testing.
  - **Why it matters:** the EKS control plane costs ~$72/month just to exist, even idle. Deleting also removes the VPC, NAT gateways, and load balancers so nothing keeps billing.

---

## Optional: test locally first (free)

_(Detailed plan → Phase 6)_

- [ ] **Enable Kubernetes in Docker Desktop** to get a free single-node cluster on your laptop.
- [ ] **Point the image at your local build** and apply the same manifests — reachable at `http://localhost`.
  - **Why:** validate the manifests before spending a cent on AWS.

---

## One-line mental model

> **Install tools → make an IAM admin → `eksctl` builds the cluster → YAML describes the app → CI/CD keeps it updated → delete the cluster to stop the bill.**
