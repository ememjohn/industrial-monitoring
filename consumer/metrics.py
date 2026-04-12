from prometheus_client import Counter, Histogram, Gauge, start_http_server
import logging
import os

logger = logging.getLogger(__name__)
METRICS_PORT = int(os.environ.get("PROMETHEUS_PORT", "8000"))

messages_consumed = Counter(
    "telemetry_messages_consumed_total",
    "Total telemetry messages consumed",
    ["equipment_id", "equipment_type", "metric_name"],
)
anomalies_detected = Counter(
    "telemetry_anomalies_detected_total",
    "Total anomaly events detected",
    ["equipment_id", "metric_name", "anomaly_type", "severity"],
)
consumer_errors = Counter(
    "telemetry_consumer_errors_total",
    "Total consumer pipeline errors",
    ["error_type"],
)
messages_published_anomaly = Counter(
    "telemetry_anomaly_messages_published_total",
    "Total anomaly events published",
    ["severity"],
)
message_processing_latency = Histogram(
    "telemetry_message_processing_seconds",
    "Time to process one telemetry message",
    ["equipment_type"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)
end_to_end_latency = Histogram(
    "telemetry_end_to_end_latency_seconds",
    "Time from production to detection",
    ["metric_name"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)
current_sensor_value = Gauge(
    "telemetry_sensor_current_value",
    "Most recent sensor reading",
    ["equipment_id", "metric_name", "unit"],
)

def record_message(reading: dict):
    messages_consumed.labels(
        equipment_id=reading["equipment_id"],
        equipment_type=reading["equipment_type"],
        metric_name=reading["metric_name"],
    ).inc()
    current_sensor_value.labels(
        equipment_id=reading["equipment_id"],
        metric_name=reading["metric_name"],
        unit=reading.get("unit", "unknown"),
    ).set(reading["value"])

def record_anomaly(anomaly):
    anomalies_detected.labels(
        equipment_id=anomaly.equipment_id,
        metric_name=anomaly.metric_name,
        anomaly_type=anomaly.anomaly_type,
        severity=anomaly.severity,
    ).inc()

def record_error(error_type: str):
    consumer_errors.labels(error_type=error_type).inc()

def start_metrics_server():
    start_http_server(METRICS_PORT)
    logger.info("Prometheus metrics at http://0.0.0.0:%d/metrics", METRICS_PORT)
