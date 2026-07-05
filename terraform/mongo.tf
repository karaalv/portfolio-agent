# --- MongoDB Atlas Infrastructure ---

# --- Config and Providers ---

provider "mongodbatlas" {
  client_id     = var.mongodb_atlas_client_id
  client_secret = var.mongodb_atlas_client_secret
}

# --- Environment Configuration ---

locals {
  mongodb_environments = {
    dev = {
      environment   = "development"
      project_name  = "Portfolio-Development"
      cluster_name  = "portfolio-development-cluster"
      cidr          = "0.0.0.0/0"
      ip_comment    = "Allow connections from anywhere for development"
      region_name   = "US_EAST_1"
      instance_size = "M0"
    }
    prod = {
      environment   = "production"
      project_name  = "Portfolio-Production"
      cluster_name  = "portfolio-production-cluster"
      cidr          = "18.170.57.91/32"
      ip_comment    = "Allow connections from EC2 instance"
      region_name   = "US_EAST_1"
      instance_size = "M0"
    }
  }
}

# --- Projects ---

resource "mongodbatlas_project" "projects" {
  for_each = local.mongodb_environments

  name   = each.value.project_name
  org_id = var.mongodb_atlas_org_id

  tags = {
    environment = each.value.environment
  }
}

# --- Clusters ---

resource "mongodbatlas_advanced_cluster" "clusters" {
  for_each = local.mongodb_environments

  project_id = mongodbatlas_project.projects[each.key].id
  name       = each.value.cluster_name

  cluster_type = "REPLICASET"
  labels = {
    environment = each.value.environment
  }

  replication_specs = [
    {
      region_configs = [
        {
          priority              = 7
          region_name           = each.value.region_name
          provider_name         = "TENANT"
          backing_provider_name = "AWS"

          electable_specs = {
            instance_size = each.value.instance_size
          }
        }
      ]
    }
  ]
}

# --- Network Access ---

resource "mongodbatlas_project_ip_access_list" "ip_access" {
  for_each = local.mongodb_environments

  project_id = mongodbatlas_project.projects[each.key].id
  cidr_block = each.value.cidr
  comment    = each.value.ip_comment
}
