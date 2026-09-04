from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class MotorConfig:
    base_speed: int = 125
    warning_speed: int = 80
    search_speed: int = 65
    max_speed: int = 200


@dataclass
class LineConfig:
    kp: float = 95.0
    kd: float = 28.0
    lost_search_seconds: float = 1.5
    lost_stop_seconds: float = 4.0
    camera_index: int = 0
    frame_width: int = 320
    frame_height: int = 240
    roi_top_ratio: float = 0.55
    threshold: int = 90
    dark_line: bool = True


@dataclass
class SafetyConfig:
    blocked_cm: float = 30.0
    warning_cm: float = 50.0
    clear_confirm_seconds: float = 1.0
    button_debounce_seconds: float = 0.08
    sensor_failure_limit: int = 3
    person_confirm_frames: int = 3


@dataclass
class ArduinoConfig:
    port: str = "/dev/ttyACM0"
    baudrate: int = 115200
    timeout_seconds: float = 0.2


@dataclass
class VisionConfig:
    person_model: str = ""
    person_labels: str = ""
    person_confidence: float = 0.55
    classifier_model: str = ""
    classifier_labels: Tuple[str, ...] = ("dress", "top", "trousers")
    classifier_confidence: float = 0.60


@dataclass
class RemoteConfig:
    host: str = "0.0.0.0"
    port: int = 8888
    max_buffer: int = 4096
    client_timeout_seconds: float = 10.0


@dataclass
class CarConfig:
    loop_hz: float = 10.0
    motor: MotorConfig = field(default_factory=MotorConfig)
    line: LineConfig = field(default_factory=LineConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    arduino: ArduinoConfig = field(default_factory=ArduinoConfig)
    vision: VisionConfig = field(default_factory=VisionConfig)
    remote: RemoteConfig = field(default_factory=RemoteConfig)

    def validate(self):
        if self.loop_hz <= 0: raise ValueError("loop_hz must be positive")
        if not 0 < self.safety.blocked_cm < self.safety.warning_cm:
            raise ValueError("require 0 < blocked_cm < warning_cm")
        if not 0 <= self.line.lost_search_seconds < self.line.lost_stop_seconds:
            raise ValueError("require 0 <= lost_search_seconds < lost_stop_seconds")
        if not 0 <= self.motor.search_speed <= self.motor.max_speed:
            raise ValueError("search_speed outside motor range")
        if not 0 <= self.motor.base_speed <= self.motor.max_speed:
            raise ValueError("base_speed outside motor range")
        if not 0.0 <= self.line.roi_top_ratio < 1.0:
            raise ValueError("roi_top_ratio must be in [0,1)")
        return self
