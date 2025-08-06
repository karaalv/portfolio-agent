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