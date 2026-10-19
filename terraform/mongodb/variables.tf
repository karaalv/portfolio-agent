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

variable "read_aws_remote_state" {
  description = "Read the AWS state for production network access. Disable when bootstrapping Atlas before AWS."
  type        = bool
  default     = true
}

variable "development_access_cidr" {
  description = "Trusted client IPv4 CIDR permitted to access development and test clusters."
  type        = string

  validation {
    condition     = can(cidrnetmask(var.development_access_cidr)) && try(tonumber(split("/", var.development_access_cidr)[1]) == 32, false)
    error_message = "Supply a single trusted IPv4 address with a /32 prefix."
  }
}
