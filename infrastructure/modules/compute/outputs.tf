output "bastion_public_ip" {
  value = aws_instance.bastion.public_ip
}

output "monitoring_public_ip" {
  value = aws_instance.monitoring.public_ip
}

output "kafka_broker_private_ips" {
  value = aws_instance.kafka_broker[*].private_ip
}

output "kafka_bootstrap_servers" {
  value = join(",", [
    for b in aws_instance.kafka_broker :
    "${b.private_ip}:9092"
  ])
}

output "app_instance_private_ip" {
  value = aws_instance.app.private_ip
}
