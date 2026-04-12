variable "project_name" {
  default = "ind-monitor"
}

variable "environment" {
  default = "dev"
}

variable "aws_region" {
  default = "eu-west-1"
}

variable "vpc_cidr" {
  default = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  default = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  default = ["10.0.10.0/24", "10.0.11.0/24"]
}

variable "allowed_ssh_cidrs" {
  default = ["0.0.0.0/0"]
}

variable "key_pair_name" {
  default = "industrial-monitoring"
}

variable "kafka_instance_type" {
  default = "t3.medium"
}

variable "app_instance_type" {
  default = "t3.small"
}

variable "monitoring_instance_type" {
  default = "t3.medium"
}

variable "kafka_broker_count" {
  default = 3
}
