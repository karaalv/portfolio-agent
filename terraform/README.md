# Terraform

The state bucket is
`portfolio-agent-tfstate-eu-west-2-533267122031` in London.
The bootstrap root manages it with local state; service roots
use separate encrypted S3 state objects with native lockfiles.

| Root | Responsibility | State |
| --- | --- | --- |
| `terraform-state/` | Existing shared state bucket | Local bootstrap state |
| `aws/shared/` | CI/CD, ECR and deployment logs | `aws/shared/terraform.tfstate` |
| `aws/staging/` | Disposable staging infrastructure | `aws/staging/terraform.tfstate` |
| `aws/production/` | Production infrastructure | `aws/production/terraform.tfstate` |
| `mongodb/` | Persistent Atlas projects and access lists | `mongodb/terraform.tfstate` |

```sh
export AWS_PROFILE=karaalv-sandbox
export AWS_REGION=eu-west-2
export TF_STATE_BUCKET=portfolio-agent-tfstate-eu-west-2-533267122031
aws sts get-caller-identity

terraform -chdir=terraform/aws/shared init
terraform -chdir=terraform/aws/staging init
terraform -chdir=terraform/aws/production init
terraform -chdir=terraform/mongodb init -backend-config="bucket=$TF_STATE_BUCKET"
```

Copy each root's `terraform.tfvars.example` and fill in its
inputs. Keep actual variable files and all state out of Git.
Apply shared before environment roots, then update Atlas network
access. Atlas can be bootstrapped first with its AWS state lookup
disabled. Node bootstrap needs an existing image, application
secrets and working database access to complete deployment.

The previous AWS infrastructure was fully torn down. The new
AWS roots start fresh at their separate state keys; no migration
is required. Existing MongoDB and state-bucket resources retain
their current state. See [AWS setup](aws/README.md).

The existing bootstrap state remains local and must be retained
securely. Do not recreate its bucket from a fresh local state.
See [state bucket](terraform-state/README.md) and
[Atlas setup](mongodb/README.md).
