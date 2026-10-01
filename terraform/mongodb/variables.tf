variable "mongodb_atlas_org_id" {
  description = "Atlas organisation ID."
  type        = string
}

variable "mongodb_atlas_client_id" {
  description = "Atlas service account client ID."
  type        = string
  sensitive   = true
}

variable "mongodb_atlas_client_secret" {
  description = "Atlas service account client secret."
  type        = string
  sensitive   = true
}

variable "state_bucket_name" {
  description = "S3 bucket containing the AWS Terraform state."
  type        = string
}
