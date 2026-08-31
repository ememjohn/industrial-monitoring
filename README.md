# Real-Time Industrial Equipment Monitoring & Anomaly Detection Platform

A production-grade system for real-time telemetry ingestion, anomaly detection,
and operational visibility across a fleet of industrial equipment.

## What this system does

- Simulates 5 industrial equipment units (pumps, compressor, turbine, motor)
- Streams sensor data (temperature, pressure, vibration, RPM) through Apache Kafka
- Detects anomalies using threshold-based and statistical z-score detection
- Visualises live equipment health on Grafana dashboards
- Exposes metrics via Prometheus

## Tech stack

- Python — telemetry simulation and anomaly detection
- Apache Kafka — real-time message streaming (3-broker cluster)
- Prometheus — metrics collection
- Grafana — live dashboards
- Docker — local development environment
- Terraform — AWS infrastructure as code (Phase 2)
- GitHub Actions — CI/CD pipeline (Phase 2)

## Architecture


## How to run locally

1. Clone the repository
   git clone https://github.com/ememjohn/industrial-monitoring.git
   cd industrial-monitoring

2. Create virtual environment
   python3 -m venv venv
   source venv/bin/activate
   pip install confluent-kafka prometheus-client boto3 numpy python-dotenv pytest

3. Start the infrastructure
   docker-compose up -d

4. Start the consumer (terminal 2)
   KAFKA_BOOTSTRAP_SERVERS=localhost:9092 python3 -m consumer.consumer

5. Start the producer (terminal 3)
   KAFKA_BOOTSTRAP_SERVERS=localhost:9092 python3 -m simulator.producer

6. Open dashboards
   Kafka UI:   http://localhost:8080
   Prometheus: http://localhost:9090
   Grafana:    http://localhost:3000  (admin / admin123)

## Run tests

   pytest tests/ -v

## Project structure

   simulator/         telemetry simulation and anomaly injection
   consumer/          anomaly detection service and Prometheus metrics
   tests/             unit tests for the detection engine
   monitoring/        Prometheus and Grafana configuration
   infrastructure/    Terraform AWS infrastructure (Phase 2)

## Anomaly detection

Two detection methods run on every message:

1. Threshold detection — fires immediately when a value crosses a hard limit
2. Z-score detection — fires when a value deviates from recent baseline by 2.5 standard deviations

## Author

Emem John
