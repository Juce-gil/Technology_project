import time
from dataclasses import dataclass
from enum import Enum


class ObstacleLevel(Enum):
    CLEAR = "clear"
    WARNING = "warning"
    BLOCKED = "blocked"
    SENSOR_ERROR = "sensor_error"


@dataclass
class ObstacleReading:
    level: ObstacleLevel
    distance_cm: float
    infrared: tuple
    timestamp: float


class ObstacleDetector:
    def __init__(self, hal, config):
        self.hal = hal; self.config = config; self.failures = 0

    def read(self):
        distance = self.hal.distance_filtered()
        infrared = tuple(bool(v) for v in self.hal.read_avoid())
        if distance < 0:
            self.failures += 1
            level = ObstacleLevel.SENSOR_ERROR if self.failures >= self.config.sensor_failure_limit else ObstacleLevel.WARNING
        else:
            self.failures = 0
            if any(infrared) or distance < self.config.blocked_cm: level = ObstacleLevel.BLOCKED
            elif distance < self.config.warning_cm: level = ObstacleLevel.WARNING
            else: level = ObstacleLevel.CLEAR
        return ObstacleReading(level, distance, infrared, time.monotonic())
