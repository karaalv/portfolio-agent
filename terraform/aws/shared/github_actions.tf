resource "aws_iam_openid_connect_provider" "github" {
  count          = var.github_oidc_provider_arn == null ? 1 : 0
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

resource "aws_iam_role" "github_actions" {
  name        = "portfolio-agent-github-actions"
  description = "Repository-wide OIDC access for Portfolio Agent CI and deployments."
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = local.github_oidc_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = { "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com" }
        StringLike   = { "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:*" }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_actions" {
  name = "portfolio-agent-ci-deployment"
  role = aws_iam_role.github_actions.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["codebuild:StartBuild", "codebuild:BatchGetBuilds", "codebuild:StopBuild", "codebuild:ListBuildsForProject"]
        Resource = aws_codebuild_project.arm.arn
      },

      {
        Effect   = "Allow"
        Action   = ["s3:ListBucket", "s3:GetBucketLocation"]
        Resource = aws_s3_bucket.ci_scripts.arn
      },

      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = "${aws_s3_bucket.ci_scripts.arn}/*"
      },

      {
        Effect   = "Allow"
        Action   = ["ec2:DescribeInstances", "ssm:DescribeInstanceInformation", "ssm:GetCommandInvocation", "ssm:ListCommandInvocations", "ssm:ListCommands", "ssm:CancelCommand"]
        Resource = "*"
      },

      {
        Effect   = "Allow"
        Action   = "ssm:SendCommand"
        Resource = "arn:${local.partition}:ssm:eu-west-2::document/AWS-RunShellScript"
      },

      {
        Effect    = "Allow"
        Action    = "ssm:SendCommand"
        Resource  = "arn:${local.partition}:ec2:eu-west-2:${local.account_id}:instance/*"
        Condition = { StringEquals = { "ssm:resourceTag/Project" = local.service_name } }
      },

      {
        Effect   = "Allow"
        Action   = ["logs:GetLogEvents", "logs:FilterLogEvents", "logs:DescribeLogStreams"]
        Resource = ["${aws_cloudwatch_log_group.ssm.arn}:*", "${aws_cloudwatch_log_group.codebuild.arn}:*"]
      },

      {
        Effect   = "Allow"
        Action   = "logs:DescribeLogGroups"
        Resource = "*"
      },

      {
        Effect   = "Allow"
        Action   = ["ecr:DescribeImages", "ecr:BatchGetImage"]
        Resource = aws_ecr_repository.agent.arn
      }
    ]
  })
}
