# Terraform state bootstrap

This root creates the S3 bucket used by the AWS and MongoDB Atlas Terraform roots. It runs with a **local backend** because the remote bucket does not exist until this root is applied. Its local `terraform.tfstate` must be preserved securely after bootstrap; deleting it would lose Terraform's ownership record for the bucket.

Export `AWS_PROFILE=karaalv-sandbox` and use London (`eu-west-2`). Choose a globally unique bucket name in an ignored `terraform.tfvars`, copied from `terraform.tfvars.example`:

```sh
terraform -chdir=terraform/terraform-state init
terraform -chdir=terraform/terraform-state plan
terraform -chdir=terraform/terraform-state apply
terraform -chdir=terraform/terraform-state output -raw state_bucket_name
```

The bucket enables versioning, AES-256 server-side encryption and public access blocking. `prevent_destroy` protects it from an ordinary destroy. Service roots use distinct S3 keys and native S3 lockfiles. Do not put this bootstrap root's state into the bucket it manages without a separate migration plan.
