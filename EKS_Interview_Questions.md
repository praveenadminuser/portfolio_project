# Progressive Interview Question Bank: Cloud-Native Python

This document contains 40 progressive questions based exactly on your Docker -> GitHub Actions -> ECR -> EKS architecture. They are designed to start with very basic concepts and scale up to Senior/Architect level questions.

---

## Level 1: The Basics (What and Why)
*If you struggle with these, revisit the core definitions.*

1. **What is Docker?**
   *Answer:* A platform that packages an application and all its dependencies into a standardized unit called a container, ensuring it runs identically in any environment.
2. **What is the difference between an Image and a Container?**
   *Answer:* An image is the static, read-only blueprint (the recipe). A container is the live, running instance of that image (the baked cake).
3. **What is Amazon ECR?**
   *Answer:* Elastic Container Registry. It is AWS's fully managed secure cloud repository where we store our Docker images.
4. **What does CI/CD stand for?**
   *Answer:* Continuous Integration (automatically testing/building code) and Continuous Deployment (automatically pushing that code to production).
5. **What tool did you use for CI/CD in this project?**
   *Answer:* GitHub Actions.
6. **What is Kubernetes?**
   *Answer:* An open-source container orchestration platform. It manages running, scaling, and repairing containers across multiple servers.
7. **What is Amazon EKS?**
   *Answer:* Elastic Kubernetes Service. It is Amazon's actively managed version of Kubernetes.
8. **What is the difference between AWS ECS and AWS EKS?**
   *Answer:* ECS is a proprietary Amazon service. EKS runs open-source Kubernetes, preventing vendor lock-in and allowing you to use universal tools.
9. **What is AWS Fargate?**
   *Answer:* A serverless compute engine. It allows us to run our containers on AWS without having to manage, patch, or configure the underlying EC2 servers.
10. **What is a "manifest" in Kubernetes?**
    *Answer:* A YAML file that declares the "Desired State" of your application (e.g., how many copies to run, what ports to open).

---

## Level 2: The Building Blocks (How it works)
*Testing your understanding of the files you wrote.*

11. **In your Dockerfile, what does the `FROM` instruction do?**
    *Answer:* It defines the base image we inherit from (e.g., `python:3.10-slim`), providing the OS and Python runtime.
12. **In a CI/CD pipeline, how do you optimize your Dockerfile to ensure the image builds as fast as possible without downloading the same dependencies every time?**
    *Answer:* By utilizing **Docker Layer Caching**. Docker builds images in distinct layers from top to bottom. If a layer changes, every layer beneath it is destroyed and rebuilt. To optimize this, we always decouple the dependencies from the code. We `COPY requirements.txt` and run `pip install` *before* copying the rest of the application code (`COPY . .`). This ensures that if we just change a single line of Python code, the time-consuming `pip install` layer remains safely cached from the previous build.
13. **Why do you use Gunicorn instead of `flask run` in the Dockerfile?**
    *Answer:* `flask run` is for development testing. Gunicorn is a production-grade WSGI server capable of handling multiple concurrent requests securely.
14. **What is a "Pod" in Kubernetes?**
    *Answer:* The smallest deployable unit in Kubernetes. It is essentially a wrapper around your running Docker container.
15. **Why do we use a Kubernetes `Deployment` instead of just running a `Pod` directly?**
    *Answer:* Pods are fragile and die easily. A Deployment acts as a manager; if a Pod dies, the Deployment immediately creates a new one to replace it.
16. **How does a Deployment know which Pods belong to it?**
    *Answer:* Using `Labels` and `Selectors`. The Deployment looks for any Pod tagged with a specific label (like `app: flask-web`).
17. **What is a Kubernetes `Service`?**
    *Answer:* A network routing rule. Because Pods are constantly dying and receiving new IP addresses, the Service provides a permanent, static entry point for traffic.
18. **If `type: LoadBalancer` is put in a Service manifest on EKS, what happens in AWS?**
    *Answer:* EKS talks to AWS and automatically provisions a real AWS Classic Load Balancer to route external internet traffic to the cluster.
19. **What is `kubectl`?**
    *Answer:* The universal command-line tool used by developers to send commands and YAML files to the Kubernetes cluster.
20. **What is `eksctl`?**
    *Answer:* A specialized tool specifically for creating and deleting the physical AWS EKS cluster infrastructure on Amazon.

---

## Level 3: The Pipeline & Automation (Connecting the dots)
*Testing how the tools communicate with each other.*

21. **What triggers your GitHub Actions pipeline?**
    *Answer:* Pushing new code commits to the `main` branch on GitHub.
22. **How does GitHub Actions get permission to upload an image to your private AWS ECR?**
    *Answer:* By configuring AWS API Keys (Access Key ID and Secret Key) securely stored in GitHub Secrets.
23. **Why is it a bad idea to use the tag `:latest` for every Docker image you push?**
    *Answer:* It makes it impossible to know exactly which version of code is running, and makes reverting to an older version incredibly difficult.
24. **How did you uniquely tag your Docker images in the CI/CD pipeline instead of `:latest`?**
    *Answer:* Using `${{ github.sha }}`, which tags the image with the unique Git Commit ID.
25. **After pushing to ECR, how does the CI/CD pipeline talk to Kubernetes?**
    *Answer:* The pipeline installs `kubectl`, authenticates with AWS EKS using `update-kubeconfig`, and runs `kubectl rollout restart`.
26. **What does the command `kubectl rollout restart deployment` actually do?**
    *Answer:* It triggers a Zero-Downtime Rolling Update, telling Kubernetes to fetch the newest container image and replace the old pods.
27. **Explain a Rolling Update.**
    *Answer:* Kubernetes starts 1 new Pod. It waits for it to become healthy. Then it kills 1 old Pod. It repeats this one-by-one so the app never goes offline.
28. **How do you pass environment variables (like a Database URL) into a Docker container?**
    *Answer:* Using the `ENV` instruction in the Dockerfile, or passing them at runtime in the Kubernetes Deployment manifest.
29. **What happens if you delete your Kubernetes Service but leave the Deployment running?**
    *Answer:* Your Python application stays running perfectly, but nobody on the internet can reach it.
30. **If I want to scale my application to handle Christmas traffic, which file do I change?**
    *Answer:* The `flask-deployment.yaml`. You change `replicas: 2` to `replicas: 10`.

---

## Level 4: Senior & Architecture Questions
*Troubleshooting, Security, and Trade-offs.*

31. **What is a `CrashLoopBackOff`, and why is it actually a good thing during a deployment?**
    *Answer:* It means a container keeps crashing quickly after startup. During a Rolling Update, if the new code has a syntax error, the new Pod enters CrashLoopBackOff. Because it isn't healthy, K8s *pauses* the rollout and leaves the old, healthy pods running, preventing a global outage.
32. **Why is storing state (like uploaded user profile pictures or local SQLite databases) inside a Kubernetes Pod a terrible idea?**
    *Answer:* Pods are ephemeral; they can be killed at any time without warning. If the Pod dies, the local storage dies with it. All state must be stored externally (e.g., Amazon S3, AWS RDS).
33. **How would you handle sensitive Database Passwords so they aren't visible in the YAML files on GitHub?**
    *Answer:* I would create a Kubernetes `Secret` resource manually in the cluster, and then reference that Secret in the Deployment YAML to inject it as an Environment Variable at runtime.
34. **If your Python app freezes up but doesn't crash (e.g., deadlocked threads), how does Kubernetes know it's broken?**
    *Answer:* It doesn't, unless you configure `LivenessProbes`. LivenessProbes tell K8s to ping a specific URL (like `/health`) every 10 seconds. If it doesn't get an HTTP 200, K8s kills the Pod and restarts it.
35. **What is the difference between a `Service` and an `Ingress` in Kubernetes?**
    *Answer:* A `Service (LoadBalancer)` exposes a single IP for a single app. An `Ingress` acts as a smart router (like NGINX), allowing you to route traffic to multiple different microservices using just a single Load Balancer based on URL paths (e.g., `/api` goes to Service A, `/web` goes to Service B).
36. **How do you optimize a Python Docker image for security?**
    *Answer:* Do not run the container as the default `root` user. Use a `USER docker-user` command in the Dockerfile so that if the application is compromised, the attacker has limited permissions.
37. **What is horizontal scaling vs vertical scaling?**
    *Answer:* Horizontal means adding *more* Pods/servers (what K8s deploy `replicas` do). Vertical means making a single Pod bigger (adding more CPU/RAM limits to the manifest).
38. **How does Horizontal Pod Autoscaling (HPA) work?**
    *Answer:* You instruct K8s to watch the CPU usage. If average CPU hits 80%, the HPA automatically edits your Deployment to increase the `replicas` count dynamically.
39. **Why might compiling a Python application via Docker on an Apple M-series (ARM) chip cause failures when deployed to AWS standard architecture?**
    *Answer:* ARM chips build ARM-architecture Docker images. Standard AWS Fargate expects AMD64/x86 architectures. You must use Docker `buildx` to cross-compile the image for the target architecture.
40. **How do you view the logging console output of your Python app running inside EKS?**
    *Answer:* You use the `kubectl logs` command combined with the specific Pod name, or you stream the logs using a centralized logging tool like Fluentd to send them to AWS CloudWatch or ElasticSearch.
41. **After successfully building a Docker image in the CI pipeline, how do you verify it doesn't contain critical security vulnerabilities before deploying it to AWS EKS?**
    *Answer:* We implement **DevSecOps** practices using two methods. First, we run an open-source scanner like **Trivy** directly inside the GitHub Action. If it detects CRITICAL vulnerabilities, it immediately fails the pipeline (Shift-Left Security). Second, we enable the **"Scan on Push"** feature in AWS ECR, which uses AWS Inspector to dynamically scan the image the moment it lands in the registry.
