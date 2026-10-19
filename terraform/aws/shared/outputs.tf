output "scripts_bucket_name" {
  description = "S3 destination for versioned CI/CD scripts and source archives."
  value       = aws_s3_bucket.ci_scripts.id
}

output "ecr_repository_url" {
  description = "Shared registry repository for staging and production images."
  value       = aws_ecr_repository.agent.repository_url
}

output "github_actions_role_arn" {
  description = "Role assumed by GitHub Actions through OIDC."
  value       = aws_iam_role.github_actions.arn
}

output "codebuild_project_name" {
  description = "Native ARM CodeBuild project."
  value       = aws_codebuild_project.arm.name
}

output "ssm_log_group_name" {
  description = "Pass this group to SendCommand CloudWatchOutputConfig."
  value       = aws_cloudwatch_log_group.ssm.name
}

output "ssm_log_group_arn" {
  description = "Log group to which environment instance roles write SSM output."
  value       = aws_cloudwatch_log_group.ssm.arn
}
