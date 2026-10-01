data "aws_caller_identity" "current" {}

# - S3 -

resource "aws_s3_bucket" "deploy_scripts" {
  bucket = "${data.aws_caller_identity.current.account_id}-portfolio-deploy-scripts"
}

resource "aws_s3_bucket_versioning" "deploy_scripts_versioning" {
  bucket = aws_s3_bucket.deploy_scripts.id

  versioning_configuration {
    status = "Enabled"
  }
}
