# MongoDB Atlas Terraform root

This root manages three Atlas projects, `Portfolio-Development`, `Portfolio-Test` and `Portfolio-Production`, with an M0 cluster in each. The `mongodb_environments` local declares the settings for each environment explicitly. All three clusters use Atlas region `EU_WEST_1` on AWS, Ireland. London (`EU_WEST_2`) was rejected by Atlas as unavailable for these M0 clusters during bootstrap. The projects remain in one root for now; separate environment configurations can be introduced later.

Set the Atlas organisation ID and service account credentials in an ignored `terraform.tfvars`, using `terraform.tfvars.example` as a guide. Also set `state_bucket_name` to the S3 bucket created by `terraform-state/`. Do not commit credentials.

Export `AWS_PROFILE=karaalv-sandbox` before initialising or using this root. Terraform uses that profile both for its S3 backend and to read the AWS root's state:

```sh
terraform -chdir=terraform/mongodb init -backend-config="bucket=$TF_STATE_BUCKET"
terraform -chdir=terraform/mongodb plan
```

By default, the production Atlas access list reads `ec2_public_ip` from `aws/terraform.tfstate` and allows only that address. To bootstrap Atlas before AWS, set `read_aws_remote_state = false` in the ignored `terraform.tfvars`. This skips the AWS state lookup and creates no production IP access rule. Once AWS is deployed, set it to `true` and apply this root again.

Set `development_access_cidr` to a trusted client IPv4 address with a `/32` prefix. Development and test allow only this address. Update it when the client's public IP changes. The bootstrap uses this machine's public IP at deployment time.

This root does not create database users. Create database credentials separately before connecting an application. Atlas project and M0 availability must be checked in the organisation before applying.

Bootstrap completed on 7 October 2026: three projects, three M0 clusters in Ireland and two client IP access rules. Production has no IP access rule because AWS remote-state lookup is disabled in the local configuration. A post-apply plan refreshed the live Atlas resources and reported no changes. State is stored at `mongodb/terraform.tfstate` in `portfolio-agent-tfstate-eu-west-2-533267122031`.
