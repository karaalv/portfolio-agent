resource "mongodbatlas_advanced_cluster" "clusters" {
  for_each = local.mongodb_environments

  project_id   = mongodbatlas_project.projects[each.key].id
  name         = each.value.cluster_name
  cluster_type = "REPLICASET"

  replication_specs = [{
    region_configs = [{
      priority              = 7
      region_name           = each.value.region_name
      provider_name         = "TENANT"
      backing_provider_name = "AWS"
      electable_specs = {
        instance_size = each.value.instance_size
      }
    }]
  }]
}
