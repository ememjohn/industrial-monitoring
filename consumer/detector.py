import time
import statistics
from collections import deque
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class AnomalyType(str, Enum):
    THRESHOLD_HIGH = "threshold_high"
    THRESHOLD_LOW  = "threshold_low"
    STATISTICAL_ZSCORE = "statistical_zscore"


@dataclass
class ThresholdConfig:
    critical_high: float
    warning_high: float
    warning_low: float
    critical_low: float
    unit: str


@dataclass
class AnomalyEvent:
    equipment_id: str
    equipment_type: str
    metric_name: str
    sensor_id: str
    anomaly_type: str
    severity: str
    current_value: float
    threshold_breached: Optional[float]
    z_score: Optional[float]
    baseline_mean: Optional[float]
    baseline_stddev: Optional[float]
    timestamp: float
    message: str
    was_injected: bool = False

    def to_dict(self):
        return {
            "equipment_id": self.equipment_id,
            "equipment_type": self.equipment_type,
            "metric_name": self.metric_name,
            "sensor_id": self.sensor_id,
            "anomaly_type": self.anomaly_type,
            "severity": self.severity,
            "current_value": round(self.current_value, 4),
            "threshold_breached": self.threshold_breached,
            "z_score": round(self.z_score, 3) if self.z_score is not None else None,
            "baseline_mean": round(self.baseline_mean, 4) if self.baseline_mean else None,
            "baseline_stddev": round(self.baseline_stddev, 4) if self.baseline_stddev else None,
            "timestamp": self.timestamp,
            "message": self.message,
            "was_injected": self.was_injected,
        }


THRESHOLDS = {
    "temperature": ThresholdConfig(110.0, 95.0,  45.0, 35.0,  "celsius"),
    "pressure":    ThresholdConfig(25.0,  20.0,  3.0,  1.5,   "bar"),
    "vibration":   ThresholdConfig(18.0,  12.0,  0.0,  -1.0,  "mm/s"),
    "rpm":         ThresholdConfig(3500.0,3000.0,600.0, 450.0, "rpm"),
}


class MetricWindow:
    def __init__(self, window_size=60):
        self._values = deque(maxlen=window_size)
        self.window_size = window_size

    def add(self, value):
        self._values.append(value)

    @property
    def is_warm(self):
        return len(self._values) >= self.window_size // 2

    @property
    def mean(self):
        return statistics.mean(self._values) if self._values else None

    @property
    def stddev(self):
        return statistics.stdev(self._values) if len(self._values) >= 2 else None

    def z_score(self, value):
        m, s = self.mean, self.stddev
        if m is None or s is None or s == 0:
            return None
        return (value - m) / s


class AnomalyDetector:
    def __init__(self, window_size=60, zscore_warning=2.5, zscore_critical=3.5):
        self.window_size = window_size
        self.zscore_warning = zscore_warning
        self.zscore_critical = zscore_critical
        self._windows: dict = {}

    def analyse(self, reading: dict) -> list:
        eq_id  = reading["equipment_id"]
        metric = reading["metric_name"]
        value  = reading["value"]

        if eq_id not in self._windows:
            self._windows[eq_id] = {}
        if metric not in self._windows[eq_id]:
            self._windows[eq_id][metric] = MetricWindow(self.window_size)

        window = self._windows[eq_id][metric]
        anomalies = []

        t = self._check_threshold(reading, value)
        if t:
            anomalies.append(t)

        if window.is_warm:
            s = self._check_statistical(reading, value, window)
            if s:
                anomalies.append(s)

        window.add(value)
        return anomalies

    def _check_threshold(self, reading, value):
        config = THRESHOLDS.get(reading["metric_name"])
        if not config:
            return None
        metric = reading["metric_name"]

        if value >= config.critical_high:
            sev, thresh, atype = "critical", config.critical_high, AnomalyType.THRESHOLD_HIGH.value
            msg = f"{metric} critically high: {value:.2f} {config.unit} (limit: {thresh})"
        elif value >= config.warning_high:
            sev, thresh, atype = "warning", config.warning_high, AnomalyType.THRESHOLD_HIGH.value
            msg = f"{metric} above warning: {value:.2f} {config.unit} (limit: {thresh})"
        elif value <= config.critical_low:
            sev, thresh, atype = "critical", config.critical_low, AnomalyType.THRESHOLD_LOW.value
            msg = f"{metric} critically low: {value:.2f} {config.unit} (limit: {thresh})"
        elif value <= config.warning_low:
            sev, thresh, atype = "warning", config.warning_low, AnomalyType.THRESHOLD_LOW.value
            msg = f"{metric} below warning: {value:.2f} {config.unit} (limit: {thresh})"
        else:
            return None

        return AnomalyEvent(
            equipment_id=reading["equipment_id"],
            equipment_type=reading["equipment_type"],
            metric_name=metric,
            sensor_id=reading["sensor_id"],
            anomaly_type=atype, severity=sev,
            current_value=value, threshold_breached=thresh,
            z_score=None, baseline_mean=None, baseline_stddev=None,
            timestamp=reading["timestamp"], message=msg,
            was_injected=reading.get("is_injected_anomaly", False),
        )

    def _check_statistical(self, reading, value, window):
        z = window.z_score(value)
        if z is None or abs(z) < self.zscore_warning:
            return None
        sev = "critical" if abs(z) >= self.zscore_critical else "warning"
        config = THRESHOLDS.get(reading["metric_name"])
        unit = config.unit if config else ""
        metric = reading["metric_name"]
        return AnomalyEvent(
            equipment_id=reading["equipment_id"],
            equipment_type=reading["equipment_type"],
            metric_name=metric,
            sensor_id=reading["sensor_id"],
            anomaly_type=AnomalyType.STATISTICAL_ZSCORE.value,
            severity=sev, current_value=value,
            threshold_breached=None, z_score=z,
            baseline_mean=window.mean, baseline_stddev=window.stddev,
            timestamp=reading["timestamp"],
            message=f"{metric} statistical anomaly: {value:.2f} {unit} (z={z:.2f})",
            was_injected=reading.get("is_injected_anomaly", False),
        )
