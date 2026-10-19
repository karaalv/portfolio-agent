# Portfolio Agent image, secret and Kubernetes deployment operations.

SHELL := /usr/bin/env bash
.SHELLFLAGS := -euo pipefail -c
.DEFAULT_GOAL := build-push
# Preserve prerequisite order even with make -j on older GNU Make.
.NOTPARALLEL:

# --- Service and environment configuration ---

SERVICE_NAME := portfolio-agent
PORTFOLIO_AGENT_ENV ?= staging
ifeq ($(strip $(PORTFOLIO_AGENT_ENV)),production)
DEPLOY_ENV := production
else
DEPLOY_ENV := staging
endif

AWS_PROFILE ?=
AWS_REGION ?= eu-west-2
PROFILE_ARG = $(if $(strip $(AWS_PROFILE)),--profile "$(AWS_PROFILE)",)
ACCOUNT_ID ?=
REPO_NAME ?= $(SERVICE_NAME)
IMAGE_TAG ?= $(shell git rev-parse --short HEAD)
BUILD_PLATFORM ?= linux/arm64
# The account and registry are resolved inside recipes, not during make -n.
IMAGE_REF = $${registry}/$(REPO_NAME):$(IMAGE_TAG)

STAGING_ENV_SECRET_ID ?= $(SERVICE_NAME)/env/staging
PROD_ENV_SECRET_ID ?= $(SERVICE_NAME)/env/production
ENV_SECRET_ID = $(if $(filter production,$(DEPLOY_ENV)),$(PROD_ENV_SECRET_ID),$(STAGING_ENV_SECRET_ID))

K8S_NAMESPACE ?= default
K8S_MANIFEST ?= kubernetes/deployment.yaml
K8S_DEPLOYMENT ?= $(SERVICE_NAME)-$(DEPLOY_ENV)
REG_SECRET_NAME ?= regcred-portfolio-agent
ENV_SECRET_NAME ?= $(SERVICE_NAME)-env-$(DEPLOY_ENV)
NODE_PORT ?= 30001
ROLLOUT_TIMEOUT ?= 180s

# --- Shared recipe setup ---

define resolve-registry
account_id="$(ACCOUNT_ID)"; \
if [[ -z "$$account_id" ]]; then \
  echo "[$(SERVICE_NAME)] Resolving the AWS account for $(DEPLOY_ENV)."; \
  account_id="$$(aws sts get-caller-identity $(PROFILE_ARG) --query Account --output text)"; \
fi; \
[[ "$$account_id" =~ ^[0-9]{12}$$ ]] || { \
  echo "[$(SERVICE_NAME)] ERROR: AWS account ID must contain 12 digits." >&2; exit 1; \
}; \
registry="$$account_id.dkr.ecr.$(AWS_REGION).amazonaws.com"; \
IMAGE_REF="$(IMAGE_REF)"
endef

define prepare-temp
umask 077; \
tmp_dir="$$(mktemp -d -t '$(SERVICE_NAME).XXXXXX')"; \
trap 'rm -rf -- "$$tmp_dir"' EXIT
endef

define render-manifest
export IMAGE_REF; \
SERVICE_NAME="$(SERVICE_NAME)" K8S_NAMESPACE="$(K8S_NAMESPACE)" \
  K8S_DEPLOYMENT="$(K8S_DEPLOYMENT)" ENV_SECRET_NAME="$(ENV_SECRET_NAME)" \
  REG_SECRET_NAME="$(REG_SECRET_NAME)" NODE_PORT="$(NODE_PORT)" \
  envsubst '$${IMAGE_REF} $${SERVICE_NAME} $${K8S_NAMESPACE} $${K8S_DEPLOYMENT} $${ENV_SECRET_NAME} $${REG_SECRET_NAME} $${NODE_PORT}' \
  < "$(K8S_MANIFEST)" > "$$tmp_dir/deployment.yaml"
endef

.PHONY: registry-login build push build-push reg-credentials-secret \
	env-secret secrets validate-manifest image-ref-available deploy rollout rollout-status terminate

# --- Image operations ---

registry-login:
	@set -euo pipefail; \
	$(resolve-registry); \
	echo "[$(SERVICE_NAME)] Authenticating Docker with $$registry in $(AWS_REGION)."; \
	aws ecr get-login-password --region "$(AWS_REGION)" $(PROFILE_ARG) \
	  | docker login --username AWS --password-stdin "$$registry"

build:
	@set -euo pipefail; \
	$(resolve-registry); \
	echo "[$(SERVICE_NAME)] Building $$IMAGE_REF with regular Docker for $(BUILD_PLATFORM)."; \
	docker build --platform "$(BUILD_PLATFORM)" -t "$$IMAGE_REF" .; \
	echo "[$(SERVICE_NAME)] Tagging the local image as $${IMAGE_REF%:*}:latest."; \
	docker tag "$$IMAGE_REF" "$${IMAGE_REF%:*}:latest"

push: registry-login
	@set -euo pipefail; \
	$(resolve-registry); \
	echo "[$(SERVICE_NAME)] Pushing versioned image $$IMAGE_REF to ECR."; \
	docker push "$$IMAGE_REF"; \
	echo "[$(SERVICE_NAME)] Pushing $${IMAGE_REF%:*}:latest to ECR."; \
	docker push "$${IMAGE_REF%:*}:latest"; \
	echo "[$(SERVICE_NAME)] Both image tags have been published successfully."

build-push: build push

# --- Secret operations ---

reg-credentials-secret:
	@set -euo pipefail; \
	$(resolve-registry); \
	echo "[$(SERVICE_NAME)] Fetching fresh ECR credentials for $$registry."; \
	registry_password="$$(aws ecr get-login-password --region "$(AWS_REGION)" $(PROFILE_ARG))"; \
	echo "[$(SERVICE_NAME)] Applying $(REG_SECRET_NAME) in namespace $(K8S_NAMESPACE)."; \
	kubectl create secret docker-registry "$(REG_SECRET_NAME)" \
	  --docker-server="$$registry" --docker-username=AWS \
	  --docker-password="$$registry_password" --namespace="$(K8S_NAMESPACE)" \
	  --dry-run=client -o yaml | kubectl apply -f - --namespace="$(K8S_NAMESPACE)"; \
	unset registry_password

env-secret:
	@set -euo pipefail; \
	$(prepare-temp); \
	echo "[$(SERVICE_NAME)] Reading $(DEPLOY_ENV) settings from $(ENV_SECRET_ID) in $(AWS_REGION)."; \
	aws secretsmanager get-secret-value --secret-id "$(ENV_SECRET_ID)" \
	  --region "$(AWS_REGION)" $(PROFILE_ARG) --query SecretString --output text \
	  > "$$tmp_dir/.env.$(DEPLOY_ENV)"; \
	echo "[$(SERVICE_NAME)] Applying environment secret $(ENV_SECRET_NAME) in namespace $(K8S_NAMESPACE)."; \
	kubectl create secret generic "$(ENV_SECRET_NAME)" \
	  --from-env-file="$$tmp_dir/.env.$(DEPLOY_ENV)" --namespace="$(K8S_NAMESPACE)" \
	  --dry-run=client -o yaml | kubectl apply -f - --namespace="$(K8S_NAMESPACE)"; \
	echo "[$(SERVICE_NAME)] Environment secret refreshed; private temporary files will be removed on exit."

secrets: reg-credentials-secret env-secret

# --- Deployment operations ---

validate-manifest:
	@set -euo pipefail; \
	test -f "$(K8S_MANIFEST)" || { \
	  echo "[$(SERVICE_NAME)] ERROR: Missing manifest $(K8S_MANIFEST)." >&2; exit 1; \
	}; \
	echo "[$(SERVICE_NAME)] Deployment manifest found: $(K8S_MANIFEST)."

image-ref-available:
	@set -euo pipefail; \
	$(resolve-registry); \
	echo "[$(SERVICE_NAME)] Checking ECR for $$IMAGE_REF before changing $(DEPLOY_ENV) resources."; \
	aws ecr describe-images --repository-name "$(REPO_NAME)" \
	  --image-ids "imageTag=$(IMAGE_TAG)" --region "$(AWS_REGION)" \
	  $(PROFILE_ARG) > /dev/null || { \
	    echo "[$(SERVICE_NAME)] ERROR: Cannot verify $$IMAGE_REF. Check AWS access or run make build-push." >&2; exit 1; \
	  }

deploy: validate-manifest image-ref-available secrets
	@set -euo pipefail; \
	$(resolve-registry); \
	$(prepare-temp); \
	echo "[$(SERVICE_NAME)] Rendering $(K8S_MANIFEST) for $(DEPLOY_ENV) with $$IMAGE_REF."; \
	$(render-manifest); \
	echo "[$(SERVICE_NAME)] Applying deployment and service $(K8S_DEPLOYMENT) in namespace $(K8S_NAMESPACE)."; \
	kubectl apply -f "$$tmp_dir/deployment.yaml" --namespace="$(K8S_NAMESPACE)"; \
	echo "[$(SERVICE_NAME)] Waiting up to $(ROLLOUT_TIMEOUT) for the $(DEPLOY_ENV) deployment."; \
	kubectl rollout status "deployment/$(K8S_DEPLOYMENT)" \
	  --namespace="$(K8S_NAMESPACE)" --timeout="$(ROLLOUT_TIMEOUT)"; \
	echo "[$(SERVICE_NAME)] Deployment $(K8S_DEPLOYMENT) is ready with $$IMAGE_REF."

rollout: secrets
	@set -euo pipefail; \
	echo "[$(SERVICE_NAME)] Secrets refreshed. Restarting deployment/$(K8S_DEPLOYMENT) in namespace $(K8S_NAMESPACE)."; \
	kubectl rollout restart "deployment/$(K8S_DEPLOYMENT)" --namespace="$(K8S_NAMESPACE)"; \
	kubectl rollout status "deployment/$(K8S_DEPLOYMENT)" \
	  --namespace="$(K8S_NAMESPACE)" --timeout="$(ROLLOUT_TIMEOUT)"; \
	echo "[$(SERVICE_NAME)] Rollout complete for $(DEPLOY_ENV); restarted pods read the refreshed secrets."

rollout-status:
	@set -euo pipefail; \
	echo "[$(SERVICE_NAME)] Checking rollout status for deployment/$(K8S_DEPLOYMENT) in namespace $(K8S_NAMESPACE)."; \
	kubectl rollout status "deployment/$(K8S_DEPLOYMENT)" \
	  --namespace="$(K8S_NAMESPACE)" --timeout="$(ROLLOUT_TIMEOUT)"

terminate: validate-manifest
	@set -euo pipefail; \
	$(prepare-temp); \
	IMAGE_REF='unused:termination'; \
	$(render-manifest); \
	echo "[$(SERVICE_NAME)] Deleting the $(DEPLOY_ENV) deployment and service $(K8S_DEPLOYMENT); Kubernetes secrets are retained."; \
	kubectl delete -f "$$tmp_dir/deployment.yaml" --namespace="$(K8S_NAMESPACE)" --ignore-not-found=true; \
	echo "[$(SERVICE_NAME)] $(DEPLOY_ENV) deployment and service termination complete."
