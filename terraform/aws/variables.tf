variable "admin_ip_cidr" {
  description = "CIDR allowed to connect to the EC2 SSH port."
  type        = string
}

variable "eu_west_2_vpc_id" {
  description = "VPC ID in the karaalv-sandbox account, eu-west-2."
  type        = string
}

variable "ec2_key_name" {
  description = "Optional EC2 key pair name in the karaalv-sandbox account."
  type        = string
  default     = null
}

variable "repo_secret_arn" {
  description = "ARN of the repository secret in the karaalv-sandbox account."
  type        = string
}

variable "env_secret_arn" {
  description = "ARN of the application environment secret in the karaalv-sandbox account."
  type        = string
}

variable "acm_arn" {
  description = "ACM certificate ARN for CloudFront, issued in us-east-1."
  type        = string
}
