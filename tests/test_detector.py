import time
import random
import pytest
from consumer.detector import AnomalyDetector, AnomalyType


def reading(value, metric="temperature", equipment_id="pump-01", injected=False):
    return {
        "equipment_id": equipment_id,
        "equipment_type": "pump",
        "metric_name": metric,
        "sensor_id": f"{equipment_id}_{metric}",
        "value": value,
        "unit": "celsius",
        "timestamp": time.time(),
        "is_injected_anomaly": injected,
    }


def warm(detector, metric, baseline, count=40):
    for _ in range(count):
        detector.analyse(reading(baseline + random.gauss(0, 1.0), metric=metric))


class TestThresholds:
    def test_normal_no_anomaly(self):
        assert AnomalyDetector().analyse(reading(75.0)) == []

    def test_critical_high(self):
        events = AnomalyDetector().analyse(reading(115.0))
        assert any(e.severity == "critical" for e in events)

    def test_warning_high(self):
        events = AnomalyDetector().analyse(reading(97.0))
        assert any(e.severity == "warning" for e in events)

    def test_critical_low(self):
        events = AnomalyDetector().analyse(reading(30.0))
        assert any(e.severity == "critical" for e in events)

    def test_pressure_critical(self):
        events = AnomalyDetector().analyse(reading(26.0, metric="pressure"))
        assert any(e.severity == "critical" for e in events)

    def test_rpm_critical(self):
        events = AnomalyDetector().analyse(reading(3600.0, metric="rpm"))
        assert any(e.severity == "critical" for e in events)


class TestStatistical:
    def test_no_fire_before_warmup(self):
        d = AnomalyDetector(window_size=60)
        for _ in range(5):
            events = d.analyse(reading(3.5, metric="vibration"))
            stat = [e for e in events if e.anomaly_type == AnomalyType.STATISTICAL_ZSCORE.value]
            assert stat == []

    def test_fires_after_warmup(self):
        d = AnomalyDetector(window_size=60, zscore_warning=2.5)
        warm(d, "vibration", 3.5, count=40)
        events = d.analyse(reading(15.0, metric="vibration"))
        stat = [e for e in events if e.anomaly_type == AnomalyType.STATISTICAL_ZSCORE.value]
        assert len(stat) >= 1

    def test_drift_detected(self):
        d = AnomalyDetector(window_size=30, zscore_warning=2.0)
        warm(d, "temperature", 75.0, count=35)
        # collect ALL anomalies across all drift readings
        all_stat = []
        for i in range(30):
            events = d.analyse(reading(75.0 + i * 0.5))
            all_stat.extend([e for e in events
                             if e.anomaly_type == AnomalyType.STATISTICAL_ZSCORE.value])
        assert len(all_stat) >= 1

    def test_independent_equipment_windows(self):
        d = AnomalyDetector(window_size=10)
        for _ in range(15):
            d.analyse(reading(3.5, metric="vibration", equipment_id="pump-01"))
        events = d.analyse(reading(3.5, metric="vibration", equipment_id="pump-02"))
        stat = [e for e in events if e.anomaly_type == AnomalyType.STATISTICAL_ZSCORE.value]
        assert stat == []
