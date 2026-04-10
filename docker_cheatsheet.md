# Docker & Python Cheat Sheet

Here is a complete cheat sheet of all the Docker and Python commands we've discussed, organized by what they do.

### 🐍 Python / Pip
* **`pip install -r requirements.txt`** 
  Installs all the Python packages listed inside your requirements file. Make sure you don't forget the `-r` flag!

### 🏗️ Building & Tagging
* **`docker build -t my_app .`** 
  Builds a new Docker image from the `Dockerfile` in your current directory and gives it a readable name (`-t my_app`).
* **`docker images`** 
  Lists all Docker images stored locally on your machine.
* **`docker tag <image_id> my_app`** 
  Gives a name to an unnamed/dangling image using its exact Image ID (e.g., `docker tag 9c88f2bb98ac my_app`).

### 🚀 Running Containers
* **`docker run -p 5001:5000 my_app`** 
  Starts a container from your image and maps your computer's port 5001 to the container's internal port 5000. *(Note: Make sure your app is bound to `0.0.0.0` inside your code!)*
* **`docker run -p 5001:5000 --name web_server my_app`** 
  Starts a container from the image and forces Docker to name the live container `web_server` instead of generating a random name.

### 🕵️ Inspecting & Executing
* **`docker ps`** 
  Lists all containers that are currently running.
* **`docker exec -it web_server /bin/bash`** 
  Opens an interactive terminal session inside a *running* container (Warning: you must use the Container Name/ID, not the Image Name).

### 🗑️ Stopping & Cleaning Up
* **`docker stop web_server`** 
  Gracefully stops a running container.
* **`docker rm web_server`** 
  Deletes a stopped container. Use `docker rm -f web_server` to force stop and delete a running container.
* **`docker image prune`** 
  Safely deletes all leftover, untagged images (the ones that show as `<none> <none>`).
* **`docker rmi my_app`** 
  Deletes a specific image. Use `docker rmi -f my_app` to force delete it even if a hidden container is still referenced to it.
* **`docker system prune -a`** 
  The nuclear option: Deletes all stopped containers, unused networks, and any images that don't belong to a currently running container.
