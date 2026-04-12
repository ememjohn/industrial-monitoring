import random
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from simulator.sensor import EquipmentUnit

logger = logging.getLogger(__name__)


class AnomalyPattern(str, Enum):
    SPIKE = "spike"
    DRIFT = "drift"
    INTERMITTENT = "intermittent"


@dataclass
class AnomalyScenario:
    pattern: AnomalyPattern
    target_metric: str
    spike_multiplier: float = 2.5
    drift_increment: float = 1.0
    drift_max_readings: int = 30
    fault_probability: float = 0.15
    fault_value_multiplier: float = 3.0


class AnomalyInjector:
    def __init__(self, equipment_unit: EquipmentUnit, injection_rate: float = 0.08):
        self.unit = equipment_unit
        self.injection_rate = injection_rate
        self.scenarios = self._default_scenarios()
        self._scenario_idx = 0
        self._drift_readings: dict = {}
        self._drift_base: dict = {}

    def read_all(self):
        if random.random() < self.injection_rate:
            return self._inject_anomaly()
        return self.unit.read_all()

    def _inject_anomaly(self):
        scenario = self.scenarios[self._scenario_idx % len(self.scenarios)]
        self._scenario_idx += 1
        if scenario.pattern == AnomalyPattern.SPIKE:
            return self._spike(scenario)
        elif scenario.pattern == AnomalyPattern.DRIFT:
            return self._drift(scenario)
        else:
            return self._intermittent(scenario)

    def _spike(self, s):
        config = self.unit.sensors[s.target_metric].config
        overrides = {s.target_metric: config.normal_mean * s.spike_multiplier}
        anomaly_types = {s.target_metric: "spike"}
        return self.unit.read_all(overrides=overrides, anomaly_types=anomaly_types)

    def _drift(self, s):
        m = s.target_metric
        config = self.unit.sensors[m].config
        if m not in self._drift_base:
            self._drift_base[m] = config.normal_mean
            self._drift_readings[m] = 0
        self._drift_readings[m] += 1
        val = self._drift_base[m] + s.drift_increment * self._drift_readings[m]
        if self._drift_readings[m] >= s.drift_max_readings:
            self._drift_base.pop(m)
            self._drift_readings.pop(m)
        return self.unit.read_all(overrides={m: val}, anomaly_types={m: "drift"})

    def _intermittent(self, s):
        overrides, anomaly_types = {}, {}
        for metric, sensor in self.unit.sensors.items():
            if random.random() < s.fault_probability:
                val = sensor.config.normal_mean * (s.fault_value_multiplier if random.random() > 0.5 else 0.2)
                overrides[metric] = val
                anomaly_types[metric] = "intermittent"
        return self.unit.read_all(overrides=overrides, anomaly_types=anomaly_types)

    @staticmethod
    def _default_scenarios():
        return [
            AnomalyScenario(AnomalyPattern.SPIKE,        "temperature", spike_multiplier=2.2),
            AnomalyScenario(AnomalyPattern.DRIFT,        "vibration",   drift_increment=0.8, drift_max_readings=20),
            AnomalyScenario(AnomalyPattern.INTERMITTENT, "pressure",    fault_probability=0.25),
            AnomalyScenario(AnomalyPattern.SPIKE,        "rpm",         spike_multiplier=2.0),
        ]
