# --- AWS Infrastructure ---

# --- Provider Configuration ---

provider "aws" {
  region  = var.aws_region
  profile = "personal"
}

# --- Resources ---

# - Route 53 Hosted Zone -

resource "aws_route53_zone" "alvinkaranja_dev" {
  comment = "Hosted zone for portfolio."
  name    = "alvinkaranja.dev"
}

# Cloudfront Record
resource "aws_route53_record" "api_domain" {
  zone_id = aws_route53_zone.alvinkaranja_dev.zone_id
  name    = "api.alvinkaranja.dev"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.cloudfront_main.domain_name
    zone_id                = aws_cloudfront_distribution.cloudfront_main.hosted_zone_id
    evaluate_target_health = false
  }
}

# - ECR Repository -

resource "aws_ecr_repository" "portfolio_repo" {
  name                 = "portfolio-repo"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# Cleanup lifecycle
resource "aws_ecr_lifecycle_policy" "cleanup" {
  repository = aws_ecr_repository.portfolio_repo.name

  policy = <<EOF
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Expire untagged images after 30 days",
      "selection": {
        "tagStatus": "untagged",
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 30
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}
EOF
}

# - EC2 Access Profile -

resource "aws_iam_role" "ec2_role" {
  name = "ec2-access-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# Read from ECR
resource "aws_iam_role_policy_attachment" "ec2_ecr_policy" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# Reading secrets
resource "aws_iam_policy" "ec2_secrets_read" {
  name        = "ec2-secretsmanager-read"
  description = "Allow EC2 to read secrets from AWS Secrets Manager."

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ]
      Resource = [
        var.repo_secret_arn,
        var.env_secret_arn
      ]
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ec2_secrets_policy" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.ec2_secrets_read.arn
}

# SSM Access
resource "aws_iam_role_policy_attachment" "ssm_managed" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# S3 access
resource "aws_iam_role_policy_attachment" "ec2_s3_readonly" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

# Profile
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "ec2-access-profile"
  role = aws_iam_role.ec2_role.name
}

# - EC2 Security Group -

resource "aws_security_group" "ec2_sg" {
  name        = "ec2-sg"
  description = "Security group for EC2 instance, defines the ingress rules for the application and ssh access."
  vpc_id      = var.eu_west_2_vpc_id
}

# Egress
resource "aws_vpc_security_group_egress_rule" "allow_all" {
  security_group_id = aws_security_group.ec2_sg.id
  description       = "Allow all outbound traffic."
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

# Ingress
data "aws_ec2_managed_prefix_list" "cf_origin" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}

resource "aws_vpc_security_group_ingress_rule" "ssh_admin" {
  security_group_id = aws_security_group.ec2_sg.id
  description       = "Allow SSH from admin IP."
  ip_protocol       = "tcp"
  from_port         = 22
  to_port           = 22
  cidr_ipv4         = var.admin_ip_cidr
}

resource "aws_vpc_security_group_ingress_rule" "cf_port_30001" {
  security_group_id = aws_security_group.ec2_sg.id
  description       = "Allow CloudFront origin traffic to port 30001."
  ip_protocol       = "tcp"
  from_port         = 30001
  to_port           = 30001
  prefix_list_id    = data.aws_ec2_managed_prefix_list.cf_origin.id
}

# - EC2 Instance -

# Ubuntu arm64 ami
data "aws_ami" "ubuntu_arm_latest" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-arm64-server-*"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
  owners = ["099720109477"] # Canonical
}

# EC2 Instance
resource "aws_instance" "ec2_instance" {
  ami           = data.aws_ami.ubuntu_arm_latest.id
  instance_type = "t4g.small"
  key_name      = "ec2_key_personal"

  iam_instance_profile = aws_iam_instance_profile.ec2_profile.name
  security_groups      = [aws_security_group.ec2_sg.name]

  # Startup script
  user_data = file("${path.module}/scripts/ec2_setup.sh")
}

# - CloudFront -

# Cache policy
resource "aws_cloudfront_cache_policy" "cache_policy" {
  name        = "cache-policy"
  default_ttl = 0
  min_ttl     = 0
  max_ttl     = 0

  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config {
      cookie_behavior = "none"
    }
    headers_config {
      header_behavior = "none"
    }
    query_strings_config {
      query_string_behavior = "none"
    }
  }
}

# Origin request policy
resource "aws_cloudfront_origin_request_policy" "origin_request_policy" {
  name    = "origin-request-policy"
  comment = "Forward all cookies to origin"

  cookies_config {
    cookie_behavior = "all"
  }

  headers_config {
    header_behavior = "allViewer"
  }

  query_strings_config {
    query_string_behavior = "all"
  }
}

# Response headers policy
resource "aws_cloudfront_response_headers_policy" "cors_policy" {
  name    = "cors-policy"
  comment = "CORS policy for CloudFront distributions"

  cors_config {
    access_control_allow_credentials = true
    access_control_allow_headers {
      items = [
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "frontend-token",
        "Connection",
        "Upgrade",
        "Sec-WebSocket-Key",
        "Sec-WebSocket-Version",
        "Sec-WebSocket-Accept",
        "Sec-WebSocket-Protocol"
      ]
    }
    access_control_allow_methods {
      items = ["ALL"]
    }
    access_control_allow_origins {
      items = [
        "https://alvinkaranja.dev",
        "https://api.alvinkaranja.dev",
        "https://staging.alvinkaranja.dev"
      ]
    }
    origin_override            = false
    access_control_max_age_sec = 86400
  }
}

# Main distribution
resource "aws_cloudfront_distribution" "cloudfront_main" {
  enabled = true
  comment = "CloudFront for api.alvinkaranja.dev"

  aliases = ["api.alvinkaranja.dev"]

  origin {
    domain_name = aws_instance.ec2_instance.public_dns
    origin_id   = "api-origin"

    custom_origin_config {
      http_port              = 30001
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id       = "api-origin"
    viewer_protocol_policy = "redirect-to-https"

    allowed_methods = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods  = ["GET", "HEAD"]

    cache_policy_id            = aws_cloudfront_cache_policy.cache_policy.id
    origin_request_policy_id   = aws_cloudfront_origin_request_policy.origin_request_policy.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.cors_policy.id
  }

  viewer_certificate {
    acm_certificate_arn = var.acm_arn
    ssl_support_method  = "sni-only"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
}

# - S3 -

resource "aws_s3_bucket" "deploy_scripts" {
  bucket = "${var.aws_account_id}-portfolio-deploy-scripts"
}

resource "aws_s3_bucket_versioning" "deploy_scripts_versioning" {
  bucket = aws_s3_bucket.deploy_scripts.id

  versioning_configuration {
    status = "Enabled"
  }
}

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
            "token.actions.githubusercontent.com:sub" = "repo:karaalv/portfolio-agent:ref:refs/heads/main"
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