resource "aws_security_group" "node" {
  name        = "${local.name}-node"
  description = "CloudFront origin ingress to the single Portfolio Agent node."
  vpc_id      = data.aws_vpc.default.id
}

resource "aws_vpc_security_group_ingress_rule" "cloudfront" {
  security_group_id = aws_security_group.node.id
  description       = "CloudFront origin HTTP and WebSocket traffic."
  ip_protocol       = "tcp"
  from_port         = 30001
  to_port           = 30001
  prefix_list_id    = data.aws_ec2_managed_prefix_list.cloudfront.id
}

resource "aws_vpc_security_group_egress_rule" "node" {
  security_group_id = aws_security_group.node.id
  description       = "Outbound package installation, SSM, AWS APIs and application services."
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_iam_role" "node" {
  name        = "${local.name}-ec2"
  description = "Instance access for ${var.environment} image pulls, secrets and SSM."
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.node.name
  policy_arn = "arn:${local.partition}:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "ecr" {
  role       = aws_iam_role.node.name
  policy_arn = "arn:${local.partition}:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_role_policy" "node" {
  name = "${local.name}-deployment"
  role = aws_iam_role.node.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
        Resource = [var.repo_secret_arn, var.env_secret_arn]
      },

      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:GetObjectVersion"]
        Resource = "arn:${local.partition}:s3:::${var.scripts_bucket_name}/*"
      },

      {
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = "arn:${local.partition}:s3:::${var.scripts_bucket_name}"
      },

      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogStreams"]
        Resource = "${var.ssm_log_group_arn}:*"
      },

      {
        Effect   = "Allow"
        Action   = "logs:DescribeLogGroups"
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "node" {
  name = "${local.name}-ec2"
  role = aws_iam_role.node.name
}

resource "aws_instance" "node" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = "t4g.small"
  subnet_id                   = local.subnet_id
  associate_public_ip_address = true
  iam_instance_profile        = aws_iam_instance_profile.node.name
  vpc_security_group_ids      = [aws_security_group.node.id]
  user_data_replace_on_change = false
  user_data = templatefile("${path.module}/../../config/ec2/setup.sh.tftpl", {
    environment     = var.environment
    deployment_ref  = var.deployment_ref
    repo_secret_arn = var.repo_secret_arn
  })
  root_block_device {
    volume_size           = 40
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
    tags = {
      Project   = "portfolio-agent"
      ManagedBy = "terraform"
    }
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  # Name is required by the EC2 deployment action's instance lookup.
  tags = { Name = local.name }
  depends_on = [
    aws_iam_role_policy.node,
    aws_iam_role_policy_attachment.ssm,
    aws_iam_role_policy_attachment.ecr,
    aws_vpc_security_group_egress_rule.node
  ]
}
