locals {
  service_name       = "portfolio-agent"
  partition          = data.aws_partition.current.partition
  account_id         = data.aws_caller_identity.current.account_id
  codebuild_name     = "portfolio-agent-arm-codebuild"
  ssm_log_group_name = "/aws/ssm/portfolio-agent/deployments"
}

locals {
  github_oidc_arn = var.github_oidc_provider_arn != null ? var.github_oidc_provider_arn : aws_iam_openid_connect_provider.github[0].arn
}
