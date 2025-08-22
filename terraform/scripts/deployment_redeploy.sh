# Use this script for redeploying the application
echo "Setting up application redeployment"
AWS_REGION="eu-west-2"
K8S_NAMESPACE=default
mkdir -m 700 -p tmp/

echo "Pulling repo key"

aws secretsmanager get-secret-value --secret-id portfolio-agent/deploy-key --region $AWS_REGION \
  --query SecretString --output text > tmp/key

chmod 600 tmp/key
eval `ssh-agent -s`
ssh-add tmp/key
export GIT_SSH_COMMAND='ssh -o StrictHostKeyChecking=no'

echo "Cloning repository"
cd tmp/
git clone git@github.com:karaalv/portfolio-agent.git

echo "Deploying application"
cd portfolio-agent
make deploy

echo "cleaning up"
cd ~
ssh-agent -k
rm -rf tmp/