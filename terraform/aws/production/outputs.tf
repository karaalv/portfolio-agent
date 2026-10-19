output "ec2_public_ip" {
  description = "Current node address for Atlas access."
  value       = module.agent.ec2_public_ip
}

output "instance_id" {
  description = "SSM target instance ID."
  value       = module.agent.instance_id
}

output "instance_name" {
  description = "Unique deployment target Name tag."
  value       = module.agent.instance_name
}

output "api_domain" {
  description = "Environment API hostname."
  value       = module.agent.api_domain
}

output "cloudfront_distribution_id" {
  description = "Environment API distribution ID."
  value       = module.agent.cloudfront_distribution_id
}
