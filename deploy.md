# Set up CI/CD

Setting up Continuous Integration and Continuous Deployment (CI/CD) using GitHub Actions for your DigitalOcean Droplet involves creating a GitHub Actions workflow that triggers on push events to the `main` branch. This workflow will connect to your DigitalOcean Droplet, pull the latest code from GitHub, and restart your Docker containers to apply the updates.

Here is a step-by-step guide to implement CI/CD using GitHub Actions:

## Step 1: Create a Deployment Script on Your Droplet

First, create a script on your DigitalOcean Droplet that will handle pulling the latest code and restarting your Docker containers.

1. **SSH into your Droplet:** `ssh root@your_droplet_ip`

2. **Create the deployment script:** `nano /opt/tide-calendar/deploy.sh`

3. **Add the following content to the deploy.sh script:**

   ```bash
   #!/bin/bash

   # Change to the project directory
   cd /opt/tide-calendar

   # Pull the latest changes from GitHub
   git pull origin main

   # Build and restart the Docker containers
   docker-compose down
   docker-compose up --build -d
   ```

4. **Make the script executable:** `chmod +x /opt/tide-calendar/deploy.sh`

## Step 2: Set Up SSH Keys for GitHub Actions

You need to set up SSH keys to allow GitHub Actions to SSH into your DigitalOcean Droplet.

1. **Generate SSH key pair on your local machine:** `ssh-keygen -t rsa -b 4096 -C "your_email@example.com"`

   Save the key to a file (e.g., `github_actions_key`).

2. **Add the public key to your DigitalOcean Droplet:** `cat ~/.ssh/github_actions_key.pub | ssh root@your_droplet_ip "cat >> ~/.ssh/authorized_keys"`

3. **Add the private key to your GitHub repository as a secret:**
   - Go to your GitHub repository.
   - Click on "Settings" > "Secrets and variables" > "Actions".
   - Click "New repository secret".
   - Name the secret `DO_SSH_KEY`.
   - Paste the content of your private key (`github_actions_key`) into the value field.

## Step 3: Create a GitHub Actions Workflow

1. **Create a `.github/workflows` directory in your repository if it doesn't exist:** `mkdir -p .github/workflows`

2. **Create a workflow file:** `nano .github/workflows/deploy.yml`

3. **Add the following content to the deploy.yml file:**

   ```yaml
   name: Deploy to DigitalOcean

   on:
     push:
       branches:
         - main
     pull_request:
       branches:
         - main

   jobs:
     deploy:
       runs-on: ubuntu-latest

       steps:
       - name: Checkout code
         uses: actions/checkout@v2

       - name: Set up SSH
         uses: webfactory/ssh-agent@v0.5.3
         with:
           ssh-private-key: ${{ secrets.DO_SSH_KEY }}

       - name: Deploy to DigitalOcean Droplet
         run: |
           ssh -o StrictHostKeyChecking=no root@your_droplet_ip 'bash /opt/tide-calendar/deploy.sh'
   ```

## Explanation of the Workflow

- **Trigger Events**: The workflow triggers on push and pull request events to the `main` branch.
- **Checkout Code**: The workflow checks out your repository code.
- **Set up SSH**: The workflow uses the `webfactory/ssh-agent` action to set up SSH access using the secret `DO_SSH_KEY`.
- **Deploy Script**: The workflow SSHs into your DigitalOcean Droplet and runs the `deploy.sh` script to pull the latest code and restart the Docker containers.

### Step 4: Test Your CI/CD Pipeline

1. **Push Changes to the `main` Branch:**

   ```bash
   git add .
   git commit -m "Set up CI/CD with GitHub Actions"
   git push origin main
   ```

2. **Check the Workflow Execution:**
   - Go to your GitHub repository.
   - Click on "Actions".
   - You should see the "Deploy to DigitalOcean" workflow running.
3. **Verify Deployment:**
   - SSH into your DigitalOcean Droplet and ensure that the latest code has been pulled.
   - Check that your Docker containers are running the updated application.

### Summary

By following these steps, you have set up a CI/CD pipeline using GitHub Actions that automatically deploys changes from the `main` branch to your DigitalOcean Droplet. This setup ensures that your application is always up-to-date with the latest code changes, streamlining your deployment process.
