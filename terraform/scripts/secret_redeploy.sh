# Use this script for redeploying pod with updated secrets

echo "Setting up secret redeployment"
export AWS_REGION="eu-west-2"
export K8S_NAMESPACE="default"

mkdir -p tmp

echo "Pulling new secrets"
aws secretsmanager get-secret-value \
    --secret-id portfolio-agent/env/prod \
    --region $AWS_REGION \
    --query SecretString \
    --output text > tmp/.env.prod

kubectl create secret generic portfolio-env-prod \
    --from-env-file=tmp/.env.prod \
    --namespace=$K8S_NAMESPACE \
    --dry-run=client -o yaml | kubectl apply -f -

echo "Redeploying deployment"
kubectl rollout restart deployment portfolio-agent -n $K8S_NAMESPACE

echo "Cleaning up temporary files"
rm -rf tmp

echo "Secret redeployment complete"