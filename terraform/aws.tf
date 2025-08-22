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
resource "aws_route53_record" "root" {
  zone_id = aws_route53_zone.alvinkaranja_dev.zone_id
  name    = "alvinkaranja.dev"
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
  instance_type = "t3.small"
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
      items = ["Content-Type", "Authorization", "X-Requested-With", "frontend-token"]
    }
    access_control_allow_methods {
      items = ["ALL"]
    }
    access_control_allow_origins {
      items = ["https://alvinkaranja.dev"]
    }
    origin_override            = false
    access_control_max_age_sec = 86400
  }
}

# Main distribution
resource "aws_cloudfront_distribution" "cloudfront_main" {
  enabled = true
  comment = "CloudFront for alvinkaranja.dev - Vercel + API routing"

  aliases = ["alvinkaranja.dev"]

  origin {
    domain_name = "216.198.79.1"
    origin_id   = "vercel-origin"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2", "TLSv1.3"]
    }
  }

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
    target_origin_id       = "vercel-origin"
    viewer_protocol_policy = "redirect-to-https"

    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods             = ["GET", "HEAD"]

    cache_policy_id            = aws_cloudfront_cache_policy.cache_policy.id
    origin_request_policy_id   = aws_cloudfront_origin_request_policy.origin_request_policy.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.cors_policy.id
  }

  ordered_cache_behavior {
    path_pattern           = "/api/*"
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