import json
import logging
import os
import signal
import time
from typing import Optional

from confluent_kafka import Producer, KafkaError, KafkaException
from simulator.sensor import EquipmentType, EquipmentUnit
from simulator.anomaly_injector import AnomalyInjector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

BOOTSTRAP         = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
INJECTION_RATE    = float(os.environ.get("ANOMALY_INJECTION_RATE", "0.08"))
MESSAGES_PER_SEC  = float(os.environ.get("MESSAGES_PER_SECOND", "2.0"))
TOPIC_TELEMETRY   = "equipment.telemetry"

PRODUCER_CONFIG = {
    "bootstrap.servers": BOOTSTRAP,
    "acks": "all",
    "retries": 5,
    "retry.backoff.ms": 500,
    "linger.ms": 10,
    "compression.type": "lz4",
    "enable.idempotence": True,
}

FLEET = [
    ("pump-01",       EquipmentType.PUMP),
    ("pump-02",       EquipmentType.PUMP),
    ("compressor-01", EquipmentType.COMPRESSOR),
    ("turbine-01",    EquipmentType.TURBINE),
    ("motor-01",      EquipmentType.MOTOR),
]


class TelemetryProducer:
    def __init__(self):
        self.producer = Producer(PRODUCER_CONFIG)
        self.injectors = [
            AnomalyInjector(EquipmentUnit(eid, etype), INJECTION_RATE)
            for eid, etype in FLEET
        ]
        self._running = False
        self._sent = 0
        self._errors = 0
        signal.signal(signal.SIGTERM, self._stop)
        signal.signal(signal.SIGINT,  self._stop)
        logger.info("Producer ready | fleet=%d | injection=%.0f%%",
                    len(self.injectors), INJECTION_RATE * 100)

    def _on_delivery(self, err: Optional[KafkaError], msg):
        if err:
            self._errors += 1
            logger.error("Delivery failed: %s", err)
        else:
            self._sent += 1
            if self._sent % 500 == 0:
                logger.info("Sent %d messages (%d errors)", self._sent, self._errors)

    def run(self):
        self._running = True
        interval = 1.0 / MESSAGES_PER_SEC

        while self._running:
            t0 = time.monotonic()
            for injector in self.injectors:
                for reading in injector.read_all():
                    try:
                        self.producer.produce(
                            topic=TOPIC_TELEMETRY,
                            key=reading.equipment_id.encode(),
                            value=json.dumps(reading.to_dict()).encode(),
                            callback=self._on_delivery,
                        )
                    except BufferError:
                        self.producer.flush(timeout=5)
                    except KafkaException as e:
                        logger.critical("Fatal Kafka error: %s", e)
                        self._running = False
                        break
            self.producer.poll(0)
            sleep = max(0, interval - (time.monotonic() - t0))
            if sleep:
                time.sleep(sleep)

        pending = self.producer.flush(timeout=30)
        logger.info("Shutdown | sent=%d errors=%d undelivered=%d",
                    self._sent, self._errors, pending)

    def _stop(self, signum, frame):
        logger.info("Signal %d — shutting down", signum)
        self._running = False


def main():
    TelemetryProducer().run()

if __name__ == "__main__":
    main()
