output "state_bucket_name" {
  description = "S3 bucket used by the AWS and MongoDB Terraform backends."
  value       = aws_s3_bucket.terraform_state.bucket
}
