provider "aws" {
  region              = "eu-west-2"
  allowed_account_ids = ["533267122031"]
  default_tags {
    tags = {
      Project   = "portfolio-agent"
      ManagedBy = "terraform"
    }
  }
}
