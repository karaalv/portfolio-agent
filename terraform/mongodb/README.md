# MongoDB Atlas Terraform root

This root manages three Atlas projects, `Portfolio-Development`, `Portfolio-Test` and `Portfolio-Production`, with an M0 cluster in each. The `mongodb_environments` local declares the settings for each environment explicitly. All three clusters use Atlas region `EU_WEST_2` on AWS, matching London. The projects remain in one root for now; separate environment configurations can be introduced later.

Set the Atlas organisation ID and service account credentials in an ignored `terraform.tfvars`, using `terraform.tfvars.example` as a guide. Also set `state_bucket_name` to the S3 bucket created by `terraform-state/`. Do not commit credentials.

Export `AWS_PROFILE=karaalv-sandbox` before initialising or using this root. Terraform uses that profile both for its S3 backend and to read the AWS root's state:

```sh
terraform -chdir=terraform/mongodb init -backend-config="bucket=$TF_STATE_BUCKET"
terraform -chdir=terraform/mongodb plan
```

Apply the AWS root first. The production Atlas access list reads `ec2_public_ip` from `aws/terraform.tfstate` and allows only that address. The development and test access lists currently allow `0.0.0.0/0`; narrow them before using those projects for sensitive data. Atlas project and M0 availability must be checked in the new organisation before applying.
