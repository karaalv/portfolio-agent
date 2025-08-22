# --- Config ---

.PHONY: push secrets deploy

# For local dev 'export AWS_PROFILE=personal'
AWS_PROFILE   ?= default
AWS_REGION    = eu-west-2
K8S_NAMESPACE = default

REPO_NAME   = portfolio-repo
ACCOUNT_ID  = $(shell aws sts get-caller-identity --profile $(AWS_PROFILE) --query Account --output text)
IMAGE_TAG   = $(shell git rev-parse --short HEAD)
ECR_URI     = $(ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(REPO_NAME)

# --- Targets ---

# Build and push Docker image to ECR
push:
	@echo "🏗️ Building and pushing $(ECR_URI):$(IMAGE_TAG)"
	aws ecr get-login-password --region $(AWS_REGION) --profile $(AWS_PROFILE) \
	| docker login --username AWS --password-stdin $(ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com
	docker buildx build --platform linux/amd64,linux/arm64 \
		-t $(ECR_URI):$(IMAGE_TAG) \
		-t $(ECR_URI):latest \
		--push .
	@echo "✅ Portfolio Agent image pushed: $(ECR_URI)"

# Create/update Kubernetes secrets
secrets:
	@echo "🔑 Creating regcred-portfolio secret in Kubernetes"
	kubectl create secret docker-registry regcred-portfolio \
	  --docker-server=$(ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com \
	  --docker-username=AWS \
	  --docker-password="$$(aws ecr get-login-password --region $(AWS_REGION) --profile $(AWS_PROFILE))" \
	  --namespace=$(K8S_NAMESPACE) \
	  --dry-run=client -o yaml | kubectl apply -f -
	@echo "✅ regcred-portfolio secret ready"

	@echo "🔑 Fetching environment secrets from AWS Secrets Manager"
	mkdir -p tmp
	aws secretsmanager get-secret-value \
	  --secret-id portfolio-agent/env/prod \
	  --region $(AWS_REGION) \
	  --profile $(AWS_PROFILE) \
	  --query SecretString \
	  --output text > tmp/.env.prod

	@echo "🔑 Creating portfolio-env-prod secret in Kubernetes"
	kubectl create secret generic portfolio-env-prod \
	  --from-env-file=tmp/.env.prod \
	  --namespace=$(K8S_NAMESPACE) \
	  --dry-run=client -o yaml | kubectl apply -f -
	@echo "✅ portfolio-env-prod secret ready"

	@echo "🧹 Cleaning up temp files"
	rm -rf ./tmp

# Deploy Portfolio Agent to Kubernetes (depends on secrets)
deploy: secrets
	@echo "🚀 Deploying Portfolio Agent to Kubernetes"
	ECR_URI=$(ECR_URI) IMAGE_TAG=$(IMAGE_TAG) ENV_SECRET=portfolio-env-prod \
	envsubst '$${ECR_URI} $${IMAGE_TAG} $${ENV_SECRET}' < kubernetes/deployment.yaml | \
	kubectl apply -f - --namespace=$(K8S_NAMESPACE)
	@echo "✅ Portfolio Agent deployed"