# - EC2 Instance -

# Ubuntu arm64 ami
data "aws_ami" "ubuntu_arm_latest" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-arm64-server-*"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
  owners = ["099720109477"] # Canonical
}

# EC2 Instance
resource "aws_instance" "ec2_instance" {
  ami           = data.aws_ami.ubuntu_arm_latest.id
  instance_type = "t4g.small"
  key_name      = var.ec2_key_name

  iam_instance_profile = aws_iam_instance_profile.ec2_profile.name
  security_groups      = [aws_security_group.ec2_sg.name]

  # Startup script
  user_data = file("${path.module}/scripts/ec2_setup.sh")
}
