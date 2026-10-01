# --- IAM Policy Permissions ---

# IAM OIDC for Github
resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

# Role for Github Actions, restricted to portfolio-agent/main
resource "aws_iam_role" "github_actions" {
  name = "github-actions-portfolio-agent"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        },
        Action = "sts:AssumeRoleWithWebIdentity",
        Condition = {
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:karaalv/portfolio-agent:*"
          }
        }
      }
    ]
  })
}

# Policy attachments for Github Actions Role
resource "aws_iam_role_policy_attachment" "pipeline_permissions" {
  role       = aws_iam_role.github_actions.name
  policy_arn = "arn:aws:iam::aws:policy/AWSCodePipeline_FullAccess"
}

resource "aws_iam_role_policy_attachment" "ecr_permissions" {
  role       = aws_iam_role.github_actions.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess"
}

# SSM Permissions for EC2 access
resource "aws_iam_policy" "github_actions_ssm_policy" {
  name = "GitHubActionsSSMPolicy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ec2:DescribeInstances",
        "ssm:SendCommand",
        "ssm:ListCommandInvocations",
        "ssm:GetCommandInvocation",
        "ssm:DescribeInstanceInformation"
      ]
      Resource = "*"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "github_ssm_attach" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.github_actions_ssm_policy.arn
}

# S3 Access
data "aws_iam_policy_document" "github_s3_access" {
  statement {
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:DeleteObject",
      "s3:ListBucket"
    ]
    resources = [
      "${aws_s3_bucket.deploy_scripts.arn}/*"
    ]
  }
}

resource "aws_iam_policy" "github_deploy" {
  name   = "github-deploy-s3-access"
  policy = data.aws_iam_policy_document.github_s3_access.json
}

resource "aws_iam_role_policy_attachment" "github_s3_attach" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.github_deploy.arn
}
