# Outputs from AWS Infrastructure

output "ec2_public_dns" {
  description = "Public DNS of the EC2 instance"
  value       = aws_instance.ec2_instance.public_dns
}