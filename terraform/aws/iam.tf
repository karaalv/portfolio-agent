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
