locals {
  subnet_id   = sort(data.aws_subnets.default.ids)[0]
  name        = "portfolio-agent-${var.environment}"
  api_domain  = var.environment == "production" ? "api.alvinkaranja.dev" : "api.staging.alvinkaranja.dev"
  site_domain = var.environment == "production" ? "alvinkaranja.dev" : "staging.alvinkaranja.dev"
  account_id  = data.aws_caller_identity.current.account_id
  partition   = data.aws_partition.current.partition
  health_targets = {
    api     = { host = local.api_domain, path = "/api/system/health" }
    website = { host = local.site_domain, path = "/" }
  }
}
