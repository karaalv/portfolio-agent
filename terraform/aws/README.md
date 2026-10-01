# AWS Terraform root

This root targets the `karaalv-sandbox` AWS account, with regional resources in London (`eu-west-2`). Export `AWS_PROFILE=karaalv-sandbox` before `terraform init`, `plan` or `apply`. Confirm the account with `aws sts get-caller-identity`.

The flat `.tf` files group the existing resources by purpose: Route 53 DNS, ECR, IAM, EC2 and its security group, CloudFront, and the deployment scripts S3 bucket. `scripts/` contains the EC2 startup and redeployment scripts. No resources were created or changed in AWS during this restructuring.

The backend uses the shared state bucket at `aws/terraform.tfstate`. After bootstrapping the bucket:

```sh
cp terraform/aws/terraform.tfvars.example terraform/aws/terraform.tfvars
# Fill in the sandbox VPC, secret ARNs, admin CIDR and CloudFront certificate ARN.
terraform -chdir=terraform/aws init -backend-config="bucket=$TF_STATE_BUCKET"
terraform -chdir=terraform/aws plan
```

The optional EC2 key pair must exist in the sandbox account if set. The CloudFront ACM certificate must be in `us-east-1` even though the EC2 instance and state bucket are in `eu-west-2`. The deployment scripts, AMI choice and account-specific inputs were carried over from the old configuration and need review before an apply.

`ec2_public_ip` is exported for the MongoDB root. It can change if the instance is replaced, so apply the AWS root before replanning MongoDB Atlas access.
