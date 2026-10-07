data "terraform_remote_state" "aws" {
  count   = var.read_aws_remote_state ? 1 : 0
  backend = "s3"

  config = {
    bucket       = var.state_bucket_name
    key          = "aws/terraform.tfstate"
    region       = "eu-west-2"
    use_lockfile = true
  }
}
