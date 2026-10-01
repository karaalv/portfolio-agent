resource "mongodbatlas_project_ip_access_list" "ip_access" {
  for_each = local.mongodb_environments

  project_id = mongodbatlas_project.projects[each.key].id
  cidr_block = each.value.cidr_block
  comment    = "Access for the ${each.key} portfolio project"
}
