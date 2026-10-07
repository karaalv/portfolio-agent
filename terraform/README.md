# Terraform

Each folder is an independent Terraform root with its own state. AWS and MongoDB Atlas use different S3 state keys. `terraform-state` creates their shared S3 bucket and keeps its own bootstrap state locally.

| Root | Manages | State |
| --- | --- | --- |
| `terraform-state/` | S3 state bucket | Local `terraform.tfstate` |
| `aws/` | Portfolio agent AWS infrastructure | `aws/terraform.tfstate` in S3 |
| `mongodb/` | Atlas projects, clusters and access lists | `mongodb/terraform.tfstate` in S3 |

## Before any AWS or Terraform command

Export the sandbox profile in each shell session. Do not depend on a profile saved in Terraform files:

```sh
export AWS_PROFILE=karaalv-sandbox
export AWS_REGION=eu-west-2
aws sts get-caller-identity
```

Confirm that the returned account is the intended sandbox account before planning or applying. On 7 October 2026, the state bucket was created using `karaalv-sandbox`, authenticated as the `alvin` IAM Identity Centre user in account `533267122031`. This bootstrap did not apply the AWS or MongoDB service roots.

## Bootstrap the state bucket

1. Choose a globally unique S3 bucket name and put it in `terraform/terraform-state/terraform.tfvars`. Start from `terraform.tfvars.example`.
2. Initialise, review and apply the state root:

```sh
terraform -chdir=terraform/terraform-state init
terraform -chdir=terraform/terraform-state plan
terraform -chdir=terraform/terraform-state apply
```

Preserve the resulting local bootstrap `terraform.tfstate`. It manages the bucket and is ignored by Git. The bucket has versioning, AES-256 server-side encryption, public access blocking and S3 lockfile support. See [terraform-state/README.md](terraform-state/README.md).

## Configure the service roots

Set the same bucket name in `TF_STATE_BUCKET`, then initialise the AWS and Atlas backends separately. Their backend blocks are partial: `bucket` is required by S3 and is supplied through `-backend-config` at initialisation. The `key` is the state object path inside that bucket. MongoDB also sets `bucket = var.state_bucket_name` in its separate `terraform_remote_state` data source so it can read the AWS state object at `aws/terraform.tfstate`.

```sh
export TF_STATE_BUCKET="$(terraform -chdir=terraform/terraform-state output -raw state_bucket_name)"
terraform -chdir=terraform/aws init -backend-config="bucket=$TF_STATE_BUCKET"
terraform -chdir=terraform/mongodb init -backend-config="bucket=$TF_STATE_BUCKET"
```

Copy each root's `terraform.tfvars.example` to `terraform.tfvars` and supply the required values before planning. The MongoDB root also needs `state_bucket_name` set to that same bucket. Apply in this order: `terraform-state`, `aws`, then `mongodb`. MongoDB reads the EC2 public IP from the AWS state for its production access list. The S3 backend uses native S3 lockfiles, not a DynamoDB lock table.

Do not run `terraform apply` against the old repository-root configuration. Its state was removed after the previous infrastructure was torn down. The old, ignored `terraform.tfvars.legacy` was retained only so account-specific values can be reviewed before they are replaced. No scope uses it automatically.

See [infrastructure architecture](../docs/architecture/infrastructure.md) for the resource inventory and current limitations.
