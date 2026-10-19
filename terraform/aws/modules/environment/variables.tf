variable "environment" {
  description = "Deployment environment."
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Use staging or production."
  }
}

variable "acm_certificate_arn" {
  description = "Issued us-east-1 ACM certificate covering this environment's API hostname."
  type        = string
  validation {
    condition     = can(regex("^arn:aws:acm:us-east-1:[0-9]{12}:certificate/", var.acm_certificate_arn))
    error_message = "CloudFront requires an ACM certificate ARN from us-east-1."
  }
}

variable "ubuntu_ami_id" {
  description = "Pinned Ubuntu 26.04 LTS ARM64 AMI in eu-west-2, serial 20261003."
  type        = string
  default     = "ami-00627c8cb63796b98"
}

variable "repo_secret_arn" {
  description = "Secrets Manager ARN holding the raw GitHub deploy private key."
  type        = string
}

variable "env_secret_arn" {
  description = "Secrets Manager ARN holding this environment's application settings."
  type        = string
}

variable "scripts_bucket_name" {
  description = "Shared bucket read by deployment scripts."
  type        = string
}

variable "ssm_log_group_arn" {
  description = "Shared CloudWatch log group for SSM deployment output."
  type        = string
}

variable "deployment_ref" {
  description = "Git branch, tag or SHA to check out during initial deployment."
  type        = string
}

variable "alarm_emails" {
  description = "Recipients for health alarms; each SNS subscription needs confirmation."
  type        = set(string)
  default     = ["alvinnjiiri@gmail.com"]
}
