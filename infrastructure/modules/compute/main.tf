terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.30"
    }
  }
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "bastion" {
  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = "t3.micro"
  subnet_id                   = var.public_subnet_id
  vpc_security_group_ids      = [var.bastion_security_group_id]
  key_name                    = var.key_pair_name
  associate_public_ip_address = true

  tags = {
    Name = "${local.name_prefix}-bastion"
    Role = "bastion"
  }
}

resource "aws_instance" "kafka_broker" {
  count         = var.kafka_broker_count
  ami           = data.aws_ami.amazon_linux.id
  instance_type = var.kafka_instance_type
  subnet_id     = var.private_subnet_id

  vpc_security_group_ids = [var.kafka_security_group_id]
  key_name               = var.key_pair_name

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 50
    encrypted             = true
    delete_on_termination = true
  }

  tags = {
    Name     = "${local.name_prefix}-kafka-broker-${count.index + 1}"
    Role     = "kafka-broker"
    BrokerId = tostring(count.index + 1)
  }
}

resource "aws_instance" "app" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.app_instance_type
  subnet_id              = var.private_subnet_id
  vpc_security_group_ids = [var.app_security_group_id]
  key_name               = var.key_pair_name

  tags = {
    Name = "${local.name_prefix}-app"
    Role = "application"
  }

  depends_on = [aws_instance.kafka_broker]
}

resource "aws_instance" "monitoring" {
  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = var.monitoring_instance_type
  subnet_id                   = var.public_subnet_id
  vpc_security_group_ids      = [var.monitoring_security_group_id]
  key_name                    = var.key_pair_name
  associate_public_ip_address = true

  tags = {
    Name = "${local.name_prefix}-monitoring"
    Role = "monitoring"
  }
}
