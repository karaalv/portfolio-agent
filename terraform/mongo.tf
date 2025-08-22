# --- MongoDB Atlas Infrastructure ---

# --- Config and Providers ---  

provider "mongodbatlas" {
  public_key  = var.mongodb_atlas_public_key
  private_key = var.mongodb_atlas_private_key
}

# --- Development Project ---

resource "mongodbatlas_project" "portfolio_dev" {
  name   = "Portfolio-Development"
  org_id = var.mongodb_atlas_org_id

  tags = {
    environment = "development"
  }
}

# Cluster Configuration
resource "mongodbatlas_cluster" "portfolio_dev_cluster" {
  project_id = mongodbatlas_project.portfolio_dev.id
  name       = "portfolio-development-cluster"

  # Provider Settings
  provider_name               = "TENANT"
  backing_provider_name       = "AWS"
  provider_region_name        = "US_EAST_1"
  provider_instance_size_name = "M0"

  labels {
    key   = "environment"
    value = "development"
  }
}

# Network access 
resource "mongodbatlas_project_ip_access_list" "portfolio_dev_ip_access" {
  project_id = mongodbatlas_project.portfolio_dev.id
  cidr_block = "0.0.0.0/0"
  comment    = "Allow connections from anywhere for development"
}

# --- Production Project ---

resource "mongodbatlas_project" "portfolio_prod" {
  name   = "Portfolio-Production"
  org_id = var.mongodb_atlas_org_id

  tags = {
    environment = "production"
  }
}

# Cluster Configuration
resource "mongodbatlas_cluster" "portfolio_prod_cluster" {
  project_id = mongodbatlas_project.portfolio_prod.id
  name       = "portfolio-production-cluster"

  # Provider Settings
  provider_name               = "TENANT"
  backing_provider_name       = "AWS"
  provider_region_name        = "US_EAST_1"
  provider_instance_size_name = "M0"

  labels {
    key   = "environment"
    value = "production"
  }
}

# Network access
# TODO: Have access only to the IP of the EC2 instance