resource "aws_iam_role" "codebuild" {
  name        = "portfolio-agent-codebuild"
  description = "Build scripts, publish agent images and write build logs."
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "codebuild.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "codebuild" {
  name = "portfolio-agent-build"
  role = aws_iam_role.codebuild.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat([
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:GetObjectVersion"]
        Resource = "${aws_s3_bucket.ci_scripts.arn}/*"
      },

      {
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      },

      {
        Effect   = "Allow"
        Action   = ["ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart", "ecr:CompleteLayerUpload", "ecr:PutImage"]
        Resource = aws_ecr_repository.agent.arn
      },

      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.codebuild.arn}:*"
      }
      ], length(var.build_secret_arns) == 0 ? [] : [{
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
        Resource = var.build_secret_arns
    }])
  })
}

resource "aws_codebuild_project" "arm" {
  name          = local.codebuild_name
  description   = "Run versioned S3 build scripts on native ARM Docker compute."
  service_role  = aws_iam_role.codebuild.arn
  build_timeout = 30

  source {
    type      = "NO_SOURCE"
    buildspec = file("${path.module}/../config/codebuild/buildspec.yml")
  }

  environment {
    type                        = "ARM_CONTAINER"
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux-aarch64-standard:3.0"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = true

    environment_variable {
      name  = "BUCKET_NAME"
      value = aws_s3_bucket.ci_scripts.id
    }
  }

  artifacts {
    type = "NO_ARTIFACTS"
  }

  logs_config {
    cloudwatch_logs {
      status     = "ENABLED"
      group_name = aws_cloudwatch_log_group.codebuild.name
    }
  }

  depends_on = [aws_iam_role_policy.codebuild]
}
