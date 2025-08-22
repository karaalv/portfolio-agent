# Global variables
variable "admin_ip_cidr" {
  description = "The IP address of the admin user"
  type        = string
}


# Variables for MongoDB Atlas Infrastructure

variable "mongodb_atlas_public_key" {
  description = "Environment variable for MongoDB Atlas public key"
  type        = string
}

variable "mongodb_atlas_private_key" {
  description = "Environment variable for MongoDB Atlas private key"
  type        = string
}

variable "mongodb_atlas_org_id" {
  description = "Environment variable for MongoDB Atlas organization ID"
  type        = string
}

# Variables for AWS Infrastructure

variable "aws_region" {
  description = "The AWS region to deploy resources in"
  type        = string
  default     = "eu-west-2"
}

# Secrets
variable "repo_secret_arn" {
  description = "ARN of the ECR repository secret"
  type        = string
}

variable "env_secret_arn" {
  description = "ARN of the environment secret"
  type        = string
}

# Certificate
variable "acm_arn" {
  description = "ARN of the ACM certificate"
  type        = string
}

variable "eu_west_2_vpc_id" {
  description = "VPC ID for the eu-west-2 region"
  type        = string
}