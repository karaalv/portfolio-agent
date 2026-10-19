output "ec2_public_ip" {
  description = "Current node IPv4 address for the Atlas allowlist."
  value       = aws_instance.node.public_ip
}

output "instance_id" {
  description = "SSM deployment target instance ID."
  value       = aws_instance.node.id
}

output "instance_name" {
  description = "Unique Name tag used by the deployment action."
  value       = local.name
}

output "api_domain" {
  description = "Public CloudFront API hostname."
  value       = local.api_domain
}

output "cloudfront_distribution_id" {
  description = "API distribution ID."
  value       = aws_cloudfront_distribution.api.id
}
