terraform {
  backend "s3" {
    bucket       = "portfolio-agent-tfstate-eu-west-2-533267122031"
    key          = "aws/production/terraform.tfstate"
    region       = "eu-west-2"
    use_lockfile = true
    encrypt      = true
  }
}
