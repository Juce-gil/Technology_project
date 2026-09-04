import time


class TargetTracker:
    """PID-like differential steering for a normalized visual target."""
    def __init__(self, motor_config, kp=100.0, kd=25.0, desired_area=0.08):
        self.motor = motor_config; self.kp = kp; self.kd = kd
        self.desired_area = desired_area; self.last_error = 0.0; self.last_time = None

    def command(self, detection, frame_shape, now=None):
        if detection is None: return 0, 0, True
        now = time.monotonic() if now is None else now
        height, width = frame_shape[:2]; x1, y1, x2, y2 = detection.bbox
        center = (x1 + x2) * 0.5
        error = (center - width * 0.5) / (width * 0.5)
        dt = max(0.01, now - self.last_time) if self.last_time is not None else 0.1
        turn = self.kp * error + self.kd * (error - self.last_error) / dt
        area = max(0.0, (x2 - x1) * (y2 - y1) / float(width * height))
        base = int(self.motor.base_speed * max(0.0, min(1.0, 1.0 - area / self.desired_area)))
        self.last_error, self.last_time = error, now
        return self._clip(base + turn), self._clip(base - turn), False

    def _clip(self, value):
        return int(max(-self.motor.max_speed, min(self.motor.max_speed, value)))
