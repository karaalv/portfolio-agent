# - EC2 Security Group -

resource "aws_security_group" "ec2_sg" {
  name        = "ec2-sg"
  description = "Security group for EC2 instance, defines the ingress rules for the application and ssh access."
  vpc_id      = var.eu_west_2_vpc_id
}

# Egress
resource "aws_vpc_security_group_egress_rule" "allow_all" {
  security_group_id = aws_security_group.ec2_sg.id
  description       = "Allow all outbound traffic."
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

# Ingress
data "aws_ec2_managed_prefix_list" "cf_origin" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}

resource "aws_vpc_security_group_ingress_rule" "ssh_admin" {
  security_group_id = aws_security_group.ec2_sg.id
  description       = "Allow SSH from admin IP."
  ip_protocol       = "tcp"
  from_port         = 22
  to_port           = 22
  cidr_ipv4         = var.admin_ip_cidr
}

resource "aws_vpc_security_group_ingress_rule" "cf_port_30001" {
  security_group_id = aws_security_group.ec2_sg.id
  description       = "Allow CloudFront origin traffic to port 30001."
  ip_protocol       = "tcp"
  from_port         = 30001
  to_port           = 30001
  prefix_list_id    = data.aws_ec2_managed_prefix_list.cf_origin.id
}
