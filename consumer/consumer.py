import json
import logging
import os
import signal
import time
from typing import Optional

from confluent_kafka import Consumer, Producer, KafkaError, KafkaException
from consumer.detector import AnomalyDetector
from consumer import metrics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_TELEMETRY = "equipment.telemetry"
TOPIC_ANOMALIES = "equipment.anomalies"
TOPIC_DLQ       = "equipment.dlq"
GROUP_ID        = "anomaly-detection-service"

CONSUMER_CONFIG = {
    "bootstrap.servers": BOOTSTRAP,
    "group.id": GROUP_ID,
    "auto.offset.reset": "latest",
    "enable.auto.commit": False,
    "session.timeout.ms": 30000,
}
PRODUCER_CONFIG = {
    "bootstrap.servers": BOOTSTRAP,
    "acks": "all",
    "retries": 3,
    "enable.idempotence": True,
}


class AnomalyConsumerService:
    def __init__(self):
        self.consumer = Consumer(CONSUMER_CONFIG)
        self.producer = Producer(PRODUCER_CONFIG)
        self.detector = AnomalyDetector(window_size=60)
        self._running = False
        signal.signal(signal.SIGTERM, self._stop)
        signal.signal(signal.SIGINT,  self._stop)
        metrics.start_metrics_server()

    def run(self):
        self.consumer.subscribe([TOPIC_TELEMETRY])
        logger.info("Consumer started | topic=%s group=%s", TOPIC_TELEMETRY, GROUP_ID)
        self._running = True

        while self._running:
            msg = self.consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    logger.error("Kafka error: %s", msg.error())
                    metrics.record_error("kafka_error")
                continue
            self._process(msg)

        self.producer.flush(timeout=10)
        self.consumer.close()
        logger.info("Consumer stopped cleanly")

    def _process(self, msg):
        start = time.monotonic()
        try:
            reading = json.loads(msg.value().decode("utf-8"))
            required = {"equipment_id","equipment_type","metric_name","value","timestamp"}
            if not required.issubset(reading.keys()):
                raise ValueError(f"Missing fields: {required - set(reading.keys())}")
        except Exception as e:
            logger.error("Bad message: %s", e)
            metrics.record_error("deserialization_error")
            self._dlq(msg, str(e))
            self.consumer.commit(message=msg)
            return

        metrics.record_message(reading)
        metrics.end_to_end_latency.labels(
            metric_name=reading["metric_name"]
        ).observe(time.time() - reading.get("timestamp", time.time()))

        for anomaly in self.detector.analyse(reading):
            metrics.record_anomaly(anomaly)
            self._publish_anomaly(anomaly)
            logger.warning("ANOMALY | %s/%s | %s | %s | value=%.2f",
                anomaly.equipment_id, anomaly.metric_name,
                anomaly.anomaly_type, anomaly.severity, anomaly.current_value)

        self.consumer.commit(message=msg)
        metrics.message_processing_latency.labels(
            equipment_type=reading["equipment_type"]
        ).observe(time.monotonic() - start)

    def _publish_anomaly(self, anomaly):
        try:
            self.producer.produce(
                topic=TOPIC_ANOMALIES,
                key=anomaly.equipment_id.encode(),
                value=json.dumps(anomaly.to_dict()).encode(),
            )
            self.producer.poll(0)
            metrics.messages_published_anomaly.labels(severity=anomaly.severity).inc()
        except KafkaException as e:
            logger.error("Failed to publish anomaly: %s", e)
            metrics.record_error("anomaly_publish_error")

    def _dlq(self, msg, reason):
        try:
            self.producer.produce(
                topic=TOPIC_DLQ,
                value=json.dumps({
                    "failure_reason": reason,
                    "failed_at": time.time(),
                    "raw": msg.value().decode("utf-8", errors="replace"),
                }).encode()
            )
            self.producer.poll(0)
        except Exception as e:
            logger.error("DLQ write failed: %s", e)

    def _stop(self, signum, frame):
        logger.info("Shutdown signal received")
        self._running = False


def main():
    AnomalyConsumerService().run()

if __name__ == "__main__":
    main()
