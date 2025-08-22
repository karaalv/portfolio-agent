#!/bin/bash
set -e

# Set non-interactive mode for apt-get
export DEBIAN_FRONTEND=noninteractive

# 1. Update packages
echo "1. Updating packages..."

apt-get update -y && apt-get upgrade -y

# 2. Install AWS CLI
echo "2. Installing AWS CLI..."
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y unzip

curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "/tmp/awscliv2.zip"
unzip -q /tmp/awscliv2.zip -d /tmp
sudo /tmp/aws/install

# Clean up
rm -rf /tmp/aws /tmp/awscliv2.zip

# 3. Installing git and make
echo "3. Installing git..."
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y git
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y make

# 4. Installing Docker
echo "4. Installing Docker..."
sudo apt-get install -y ca-certificates curl gnupg lsb-release

sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add ubuntu user to docker group
sudo usermod -aG docker ubuntu

# 5. Installing k3s with docker and setting up kubectl
echo "5. Installing k3s with Docker..."

curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--docker" sh -
sudo ln -sf /usr/local/bin/kubectl /usr/bin/kubectl

mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER:$USER ~/.kube/config
chmod 600 ~/.kube/config

# Wait for the node to appear in kubectl
for i in {1..30}; do
  NODE_NAME=$(hostname)
  if kubectl get node "$NODE_NAME" &>/dev/null; then
    break
  fi
  echo "Waiting for node $NODE_NAME to register with k3s..."
  sleep 5
done

kubectl wait --for=condition=Ready node/"$(hostname)" --timeout=120s

# 6. Pull repo, deploy application with makefile targets
AWS_REGION="eu-west-2"
K8S_NAMESPACE=default

echo "6. Pulling repository and deploying application..."
mkdir -m 700 -p tmp/

aws secretsmanager get-secret-value --secret-id portfolio-agent/deploy-key --region $AWS_REGION \
  --query SecretString --output text > tmp/key

chmod 600 tmp/key
eval `ssh-agent -s`
ssh-add tmp/key
export GIT_SSH_COMMAND='ssh -o StrictHostKeyChecking=no'

cd tmp/
git clone git@github.com:karaalv/portfolio-agent.git

# Deploy
cd portfolio-agent
make deploy

# 7. Clean up and exit
echo "7. Cleaning up and exiting."
cd ~
ssh-agent -k
rm -rf tmp/