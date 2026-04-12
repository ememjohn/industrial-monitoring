import random
import time
import math
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class EquipmentType(str, Enum):
    PUMP = "pump"
    COMPRESSOR = "compressor"
    TURBINE = "turbine"
    MOTOR = "motor"


@dataclass
class SensorConfig:
    min_value: float
    max_value: float
    normal_mean: float
    normal_stddev: float
    unit: str


@dataclass
class SensorReading:
    sensor_id: str
    equipment_id: str
    equipment_type: str
    metric_name: str
    value: float
    unit: str
    timestamp: float
    is_injected_anomaly: bool = False
    anomaly_type: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "sensor_id": self.sensor_id,
            "equipment_id": self.equipment_id,
            "equipment_type": self.equipment_type,
            "metric_name": self.metric_name,
            "value": round(self.value, 4),
            "unit": self.unit,
            "timestamp": self.timestamp,
            "is_injected_anomaly": self.is_injected_anomaly,
            "anomaly_type": self.anomaly_type,
        }


class Sensor:
    CONFIGS: dict = {
        "temperature": SensorConfig(40.0, 120.0, 75.0, 2.5, "celsius"),
        "pressure":    SensorConfig(1.0,  30.0,  12.0, 0.8, "bar"),
        "vibration":   SensorConfig(0.0,  25.0,  3.5,  0.6, "mm/s"),
        "rpm":         SensorConfig(500.0,4000.0,1500.0,50.0,"rpm"),
    }

    def __init__(self, sensor_id, equipment_id, equipment_type, metric_name):
        self.sensor_id = sensor_id
        self.equipment_id = equipment_id
        self.equipment_type = equipment_type
        self.metric_name = metric_name
        self.config = self.CONFIGS[metric_name]
        self._current_value = self.config.normal_mean + random.gauss(0, self.config.normal_stddev)
        self._reading_count = 0

    def read(self, override_value=None, anomaly_type=None):
        self._reading_count += 1
        if override_value is not None:
            value = max(self.config.min_value, min(self.config.max_value, override_value))
            is_anomaly = True
        else:
            value = self._random_walk_step()
            is_anomaly = False
        return SensorReading(
            sensor_id=self.sensor_id,
            equipment_id=self.equipment_id,
            equipment_type=self.equipment_type.value,
            metric_name=self.metric_name,
            value=value,
            unit=self.config.unit,
            timestamp=time.time(),
            is_injected_anomaly=is_anomaly,
            anomaly_type=anomaly_type,
        )

    def _random_walk_step(self):
        reversion = 0.05 * (self.config.normal_mean - self._current_value)
        noise = random.gauss(0, self.config.normal_stddev * 0.3)
        cycle = math.sin(self._reading_count * 0.1) * self.config.normal_stddev * 0.5
        self._current_value += reversion + noise + cycle
        self._current_value = max(self.config.min_value, min(self.config.max_value, self._current_value))
        return self._current_value


class EquipmentUnit:
    METRICS = ["temperature", "pressure", "vibration", "rpm"]

    def __init__(self, equipment_id, equipment_type):
        self.equipment_id = equipment_id
        self.equipment_type = equipment_type
        self.sensors = {
            m: Sensor(f"{equipment_id}_{m}", equipment_id, equipment_type, m)
            for m in self.METRICS
        }

    def read_all(self, overrides=None, anomaly_types=None):
        overrides = overrides or {}
        anomaly_types = anomaly_types or {}
        return [
            self.sensors[m].read(
                override_value=overrides.get(m),
                anomaly_type=anomaly_types.get(m)
            )
            for m in self.METRICS
        ]
