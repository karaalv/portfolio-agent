#!/usr/bin/env bash

# This script redeploys the application 
# with the latest Docker image
set -euo pipefail
set -x

echo "1. Setting up application redeployment"

AWS_REGION="eu-west-2"
K8S_NAMESPACE=default
mkdir -m 700 -p tmp/

echo "2. Pulling repo key"

aws secretsmanager get-secret-value --secret-id portfolio-agent/deploy-key --region $AWS_REGION \
  --query SecretString --output text > tmp/key

chmod 600 tmp/key
eval `ssh-agent -s`
ssh-add tmp/key
export GIT_SSH_COMMAND='ssh -o StrictHostKeyChecking=no'

echo "3. Cloning repository"
cd tmp/
git clone git@github.com:karaalv/portfolio-agent.git

echo "4. Deploying application"
cd portfolio-agent
make deploy

echo "5. Cleaning up"
cd ~
ssh-agent -k
rm -rf tmp/