resource "aws_s3_bucket" "ci_scripts" {
  bucket = "${local.account_id}-portfolio-agent-ci-cd-scripts"
}

resource "aws_s3_bucket_ownership_controls" "ci_scripts" {
  bucket = aws_s3_bucket.ci_scripts.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_versioning" "ci_scripts" {
  bucket = aws_s3_bucket.ci_scripts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "ci_scripts" {
  bucket                  = aws_s3_bucket.ci_scripts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "ci_scripts" {
  bucket = aws_s3_bucket.ci_scripts.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_policy" "ci_scripts_tls" {
  bucket = aws_s3_bucket.ci_scripts.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = [aws_s3_bucket.ci_scripts.arn, "${aws_s3_bucket.ci_scripts.arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
}
