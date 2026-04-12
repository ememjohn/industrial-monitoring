output "kafka_security_group_id" {
  value = aws_security_group.kafka.id
}

output "app_security_group_id" {
  value = aws_security_group.app.id
}

output "monitoring_security_group_id" {
  value = aws_security_group.monitoring.id
}

output "bastion_security_group_id" {
  value = aws_security_group.bastion.id
}
