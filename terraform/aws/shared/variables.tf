variable "github_repository" {
  description = "GitHub owner/repository permitted to assume the CI role."
  type        = string
  default     = "karaalv/portfolio-agent"
}

variable "github_oidc_provider_arn" {
  description = "Existing account-wide GitHub OIDC provider ARN; null creates it here."
  type        = string
  default     = null
  nullable    = true
}

variable "build_secret_arns" {
  description = "Specific Secrets Manager ARNs that build scripts need to read."
  type        = list(string)
  default     = []
}
