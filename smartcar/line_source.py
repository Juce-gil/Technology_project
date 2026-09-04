import time
from dataclasses import dataclass


@dataclass
class LineReading:
    error: float
    confidence: float
    detected: bool
    timestamp: float


class IRLineSource:
    WEIGHTS = (-1.0, -0.35, 0.35, 1.0)

    def __init__(self, hal): self.hal = hal

    def read(self):
        values = self.hal.read_tracking()
        active = [w for w, value in zip(self.WEIGHTS, values) if value]
        if not active: return LineReading(0.0, 0.0, False, time.monotonic())
        return LineReading(sum(active) / len(active), len(active) / 4.0, True, time.monotonic())

    def is_healthy(self): return True


class CameraLineSource:
    def __init__(self, config, capture=None):
        try: import cv2
        except ImportError as exc: raise RuntimeError("OpenCV is required for camera line following") from exc
        self.cv2 = cv2; self.config = config
        self.capture = capture if capture is not None else cv2.VideoCapture(config.camera_index)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, config.frame_width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, config.frame_height)
        self.failed_reads = 0

    def read(self):
        ok, frame = self.capture.read()
        if not ok or frame is None:
            self.failed_reads += 1
            return LineReading(0.0, 0.0, False, time.monotonic())
        self.failed_reads = 0
        gray = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2GRAY)
        top = int(gray.shape[0] * self.config.roi_top_ratio)
        roi = gray[top:, :]
        mode = self.cv2.THRESH_BINARY_INV if self.config.dark_line else self.cv2.THRESH_BINARY
        _, mask = self.cv2.threshold(roi, self.config.threshold, 255, mode)
        kernel = self.cv2.getStructuringElement(self.cv2.MORPH_RECT, (5, 5))
        mask = self.cv2.morphologyEx(mask, self.cv2.MORPH_OPEN, kernel)
        contours = self.cv2.findContours(mask, self.cv2.RETR_EXTERNAL, self.cv2.CHAIN_APPROX_SIMPLE)[-2]
        if not contours: return LineReading(0.0, 0.0, False, time.monotonic())
        contour = max(contours, key=self.cv2.contourArea)
        area = float(self.cv2.contourArea(contour)); roi_area = float(mask.shape[0] * mask.shape[1])
        moments = self.cv2.moments(contour)
        if moments["m00"] <= 0 or area / roi_area < 0.002:
            return LineReading(0.0, 0.0, False, time.monotonic())
        cx = moments["m10"] / moments["m00"]
        error = (cx - mask.shape[1] / 2.0) / (mask.shape[1] / 2.0)
        confidence = min(1.0, area / (roi_area * 0.12))
        return LineReading(max(-1.0, min(1.0, error)), confidence, True, time.monotonic())

    def close(self):
        if self.capture is not None: self.capture.release()

    def is_healthy(self): return self.failed_reads < 3


class LineController:
    def __init__(self, config, motor_config):
        self.config = config; self.motor = motor_config
        self.last_error = 0.0; self.last_seen = None; self.last_time = None
        self.last_output = (0, 0)

    def command(self, reading, now=None):
        now = time.monotonic() if now is None else now
        if reading.detected:
            dt = max(0.01, now - self.last_time) if self.last_time is not None else 0.1
            derivative = (reading.error - self.last_error) / dt
            turn = self.config.kp * reading.error + self.config.kd * derivative
            self.last_error = reading.error; self.last_seen = now; self.last_time = now
            base = self.motor.base_speed
            output = (self._clip(base + turn), self._clip(base - turn))
            self.last_output = output
            return output[0], output[1], False
        elapsed = float("inf") if self.last_seen is None else now - self.last_seen
        if elapsed >= self.config.lost_stop_seconds: return 0, 0, True
        if elapsed < self.config.lost_search_seconds:
            left, right = self.last_output
            scale = self.motor.search_speed / float(max(1, max(abs(left), abs(right))))
            return int(left * min(1.0, scale)), int(right * min(1.0, scale)), False
        direction = 1 if self.last_error >= 0 else -1
        speed = self.motor.search_speed
        return direction * speed, -direction * speed, False

    def _clip(self, value):
        return int(max(-self.motor.max_speed, min(self.motor.max_speed, value)))
