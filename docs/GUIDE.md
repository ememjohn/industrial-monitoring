# Industrial Equipment Monitoring Platform — Complete Build Guide

## What this project is and why it exists

Industrial equipment fails. Pumps overheat. Compressors vibrate beyond safe limits.
Turbines lose RPM without warning. In oil and gas, marine, and manufacturing
environments, a single undetected fault can cause equipment damage, production
loss, or injury.

Most facilities rely on periodic manual inspection or basic threshold alarms.
These approaches share a common weakness — they react after damage has started,
not before.

This platform solves that by streaming sensor data from equipment in real time,
detecting abnormal behaviour as it happens, and surfacing it on a live dashboard
before it becomes a critical failure.

The system monitors five equipment units continuously:
- Two pumps
- One compressor
- One turbine
- One motor

Each unit reports four metrics every 500 milliseconds:
- Temperature (celsius)
- Pressure (bar)
- Vibration (mm/s)
- RPM

That is 40 sensor readings per second flowing through the pipeline at all times.

---

## Architecture overview

The system has five layers. Data flows through each layer in sequence.

Layer 1 — Data generation
Python simulator generates realistic sensor readings with injected faults

Layer 2 — Streaming
Apache Kafka receives and routes messages across a 3-broker cluster

Layer 3 — Processing
Python consumer reads messages and runs anomaly detection on each one

Layer 4 — Observability
Prometheus collects metrics. Grafana renders live dashboards.

Layer 5 — Infrastructure
AWS EC2 instances host all components. Terraform provisions everything.

---

## Tools used and why each one was chosen

### Python
Python runs both the simulator and the anomaly detection consumer.
The confluent-kafka library wraps librdkafka, the highest-performance
Kafka client available. numpy handles statistical calculations.
boto3 connects to AWS services.

Alternative considered: Go. Go offers better raw concurrency and lower
memory usage. At the throughput this system targets — under 500 messages
per second — Python performs adequately and development is faster.

### Apache Kafka
Kafka is the backbone of the streaming layer. It decouples the producer
from the consumer completely. If the consumer crashes, messages wait in
Kafka until it recovers. No data is lost. The consumer replays from its
last committed offset.

Kafka also gives partition-level ordering. All messages from pump-01
land on the same partition in the same order they were produced. This
matters for the statistical detector which needs sequential readings
to build an accurate baseline.

Alternative considered: AWS Kinesis. Kinesis is fully managed and
removes the operational burden of running brokers. The trade-off is
shard-level limits and no native consumer group semantics.

Alternative considered: RabbitMQ. RabbitMQ is excellent for task queues
but does not support message replay. Once a consumer reads a message it
is gone. For a monitoring system where replay is essential, RabbitMQ
is the wrong tool.

### Prometheus
Prometheus scrapes the consumer metrics endpoint every 10 seconds.
The pull model means Prometheus controls the scrape schedule.
The application just exposes an endpoint and waits.

Alternative considered: Datadog. Superior visualisation but expensive
at scale. Prometheus is free and PromQL is an industry standard skill.

### Grafana
Grafana connects to Prometheus and renders metrics as live graphs.
Dashboards auto-refresh every 10 seconds. Threshold lines show visually
when a reading enters warning or critical territory.

Alternative considered: Kibana. Better for log-centric observability.
For time-series metrics Grafana with Prometheus is the cleaner choice.

### Terraform
Terraform declares every AWS resource as code. Running terraform apply
creates the entire infrastructure from nothing in under 10 minutes.
Running terraform destroy removes it completely.

The infrastructure splits into three modules:
- networking — VPC, subnets, route tables, NAT gateway
- security — security groups, IAM roles
- compute — EC2 instances for Kafka, application, monitoring, bastion

Alternative considered: AWS CDK. Uses real programming languages instead
of HCL. More complex for infrastructure review. Terraform declarative
syntax is more readable for teams.

### Docker Compose
Runs the full stack locally for development and testing. One command
starts Zookeeper, three Kafka brokers, Prometheus, Grafana, and Kafka UI.
The entire system runs on a laptop without any cloud account.

### GitHub Actions
Runs the CI/CD pipeline. Every push triggers tests. Every pull request
to main triggers a Terraform plan posted as a PR comment. Merging to
main triggers terraform apply.

---

## Project structure explained
