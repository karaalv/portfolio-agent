# Portfolio agent infrastructure

The infrastructure configuration lives in three independent Terraform roots under `terraform/`. All AWS access uses the `karaalv-sandbox` profile and London (`eu-west-2`) for regional resources. Export `AWS_PROFILE=karaalv-sandbox` in the shell before using the AWS provider or S3 state backends. Verify the selected account with `aws sts get-caller-identity`.

## State and deployment order

`terraform-state/` creates the shared S3 bucket using local bootstrap state. `aws/` and `mongodb/` then store their state at separate S3 keys, `aws/terraform.tfstate` and `mongodb/terraform.tfstate`. Both use S3 lockfiles. The state bucket has versioning, AES-256 encryption and public access blocking. Keep the bootstrap state secure and keep all state and actual `terraform.tfvars` files out of Git.

Apply `terraform-state` first, AWS second, and MongoDB third. The MongoDB root reads the AWS root's state to obtain the EC2 public IP. The backend bucket name is provided during each service root's `terraform init`; it is also an input variable for MongoDB's remote-state data source. See [Terraform instructions](../../terraform/README.md) for commands.

## AWS resources

| Area | Current configuration |
| --- | --- |
| DNS | Route 53 hosted zone for `alvinkaranja.dev`, with an alias record for `api.alvinkaranja.dev` pointing to CloudFront. |
| Container registry | ECR repository `portfolio-repo`, image scanning on push and a 30-day untagged-image lifecycle policy. |
| Compute | ARM `t4g.small` EC2 instance in a supplied London VPC, using an Ubuntu ARM AMI and the startup script in `aws/scripts/`. The optional key pair must exist in the sandbox account. |
| Network access | EC2 security group with outbound access, SSH from the supplied admin CIDR, and CloudFront origin-facing traffic on port 30001. |
| Edge | CloudFront distribution for the API, with cache, origin-request and CORS response-header policies. Its ACM certificate ARN is supplied as an input and must refer to a certificate in `us-east-1`. |
| Secrets and access | EC2 instance role with ECR read, Secrets Manager read, SSM and S3 read permissions; GitHub Actions OIDC role with ECR, SSM and deployment-bucket policies. |
| Deployment storage | Versioned S3 bucket for deployment scripts, named from the sandbox account ID. This is separate from the Terraform state bucket. |

The AWS root outputs `ec2_public_ip`. The current instance public IP is not reserved, so replacing the instance may require a subsequent MongoDB apply to update Atlas access. Existing bootstrap scripts and deployment permissions were carried over and should be reviewed before redeployment.

## MongoDB Atlas resources

The Atlas root uses a service account client ID and secret plus an Atlas organisation ID. Its `mongodb_environments` local explicitly defines development, test and production projects, each with an M0 cluster configured in Atlas region `EU_WEST_2` on AWS. The development and test project IP access lists currently permit all source IPs; production permits the AWS EC2 public IP read from the AWS Terraform state. Narrow development and test access before storing sensitive data.

These projects share one Terraform root and one state for now. Separate environment roots or workspaces are deferred. Confirm free-cluster availability and service-account permissions in the new Atlas organisation before applying.

## Current status

The prior combined Terraform root and its old local state were removed after the user reported the infrastructure torn down. The previous variable file is retained as ignored `terraform/terraform.tfvars.legacy` for review; none of the new roots loads it. This restructuring has not provisioned cloud resources. Plans and applies require the new sandbox profile, account-specific AWS values, a chosen state bucket name, and the new Atlas organisation credentials.
