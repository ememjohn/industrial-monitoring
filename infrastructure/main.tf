terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.30"
    }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "industrial-monitoring"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

module "networking" {
  source               = "./modules/networking"
  project_name         = var.project_name
  environment          = var.environment
  vpc_cidr             = var.vpc_cidr
  availability_zones   = slice(data.aws_availability_zones.available.names, 0, 2)
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
}

module "security" {
  source            = "./modules/security"
  project_name      = var.project_name
  environment       = var.environment
  vpc_id            = module.networking.vpc_id
  allowed_ssh_cidrs = var.allowed_ssh_cidrs
}

module "compute" {
  source                       = "./modules/compute"
  project_name                 = var.project_name
  environment                  = var.environment
  aws_region                   = var.aws_region
  vpc_id                       = module.networking.vpc_id
  public_subnet_id             = module.networking.public_subnet_ids[0]
  private_subnet_id            = module.networking.private_subnet_ids[0]
  kafka_security_group_id      = module.security.kafka_security_group_id
  app_security_group_id        = module.security.app_security_group_id
  monitoring_security_group_id = module.security.monitoring_security_group_id
  bastion_security_group_id    = module.security.bastion_security_group_id
  key_pair_name                = var.key_pair_name
  kafka_instance_type          = var.kafka_instance_type
  app_instance_type            = var.app_instance_type
  monitoring_instance_type     = var.monitoring_instance_type
  kafka_broker_count           = var.kafka_broker_count
}
