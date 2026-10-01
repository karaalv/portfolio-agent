locals {

  # Obtains IP address of production EC2
  # instance from AWS remote state
  production_ec2_ip = (
    try(data.terraform_remote_state.aws.outputs.ec2_public_ip, null)
  )
  # If IP is not available, default to blocking all access
  production_access_cidr = (
    local.production_ec2_ip != null ? "${local.production_ec2_ip}/32" : "0.0.0.0/32"
  )
  mongodb_environments = {
    development = {
      project_name  = "Portfolio-Development"
      cluster_name  = "portfolio-development-cluster"
      instance_size = "M0"
      region_name   = "EU_WEST_2"
      cidr_block    = "0.0.0.0/0"
    }
    test = {
      project_name  = "Portfolio-Test"
      cluster_name  = "portfolio-test-cluster"
      instance_size = "M0"
      region_name   = "EU_WEST_2"
      cidr_block    = "0.0.0.0/0"
    }
    production = {
      project_name  = "Portfolio-Production"
      cluster_name  = "portfolio-production-cluster"
      instance_size = "M0"
      region_name   = "EU_WEST_2"
      cidr_block    = local.production_access_cidr
    }
  }
}
