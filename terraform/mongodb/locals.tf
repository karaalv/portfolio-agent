locals {

  # Production access is omitted until the AWS state supplies an EC2 IP.
  production_ec2_ip = (
    try(data.terraform_remote_state.aws[0].outputs.ec2_public_ip, null)
  )
  production_access_cidr = (
    local.production_ec2_ip != null ? "${local.production_ec2_ip}/32" : null
  )
  mongodb_environments = {
    development = {
      project_name  = "Portfolio-Development"
      cluster_name  = "portfolio-development-cluster"
      instance_size = "M0"
      region_name   = "EU_WEST_1"
      cidr_block    = var.development_access_cidr
    }
    test = {
      project_name  = "Portfolio-Test"
      cluster_name  = "portfolio-test-cluster"
      instance_size = "M0"
      region_name   = "EU_WEST_1"
      cidr_block    = var.development_access_cidr
    }
    production = {
      project_name  = "Portfolio-Production"
      cluster_name  = "portfolio-production-cluster"
      instance_size = "M0"
      region_name   = "EU_WEST_1"
      cidr_block    = local.production_access_cidr
    }
  }
}
