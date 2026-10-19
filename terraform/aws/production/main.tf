data "terraform_remote_state" "shared" {
  backend = "s3"
  config = {
    bucket       = "portfolio-agent-tfstate-eu-west-2-533267122031"
    key          = "aws/shared/terraform.tfstate"
    region       = "eu-west-2"
    use_lockfile = true
  }
}

module "agent" {
  source = "../modules/environment"
  providers = {
    aws           = aws
    aws.us_east_1 = aws.us_east_1
  }

  environment         = "production"
  acm_certificate_arn = var.acm_certificate_arn
  ubuntu_ami_id       = var.ubuntu_ami_id
  repo_secret_arn     = var.repo_secret_arn
  env_secret_arn      = var.env_secret_arn
  deployment_ref      = var.deployment_ref
  alarm_emails        = var.alarm_emails
  scripts_bucket_name = data.terraform_remote_state.shared.outputs.scripts_bucket_name
  ssm_log_group_arn   = data.terraform_remote_state.shared.outputs.ssm_log_group_arn
}
