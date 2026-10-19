resource "aws_cloudwatch_log_group" "ssm" {
  name              = local.ssm_log_group_name
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "codebuild" {
  name              = "/aws/codebuild/${local.codebuild_name}"
  retention_in_days = 30
}
