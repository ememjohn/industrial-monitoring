output "bastion_public_ip" {
  description = "Public IP of bastion host"
  value       = module.compute.bastion_public_ip
}

output "monitoring_public_ip" {
  description = "Public IP of monitoring instance"
  value       = module.compute.monitoring_public_ip
}

output "kafka_bootstrap_servers" {
  description = "Kafka bootstrap servers string"
  value       = module.compute.kafka_bootstrap_servers
}

output "grafana_url" {
  description = "Grafana dashboard URL"
  value       = "http://${module.compute.monitoring_public_ip}:3000"
}

output "prometheus_url" {
  description = "Prometheus URL"
  value       = "http://${module.compute.monitoring_public_ip}:9090"
}

output "ssh_to_bastion" {
  description = "SSH command to connect to bastion"
  value       = "ssh -i ~/.ssh/industrial-monitoring.pem ec2-user@${module.compute.bastion_public_ip}"
}
