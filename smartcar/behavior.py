import logging
import threading
import time
from enum import Enum
from .obstacle import ObstacleLevel


class RunState(Enum):
    RUNNING = "running"
    PAUSED = "paused"
    WAIT_CLEAR = "wait_clear"
    FAULT = "fault"


class DebouncedButton:
    def __init__(self, read_fn, debounce_seconds):
        self.read_fn = read_fn; self.debounce = debounce_seconds
        self.raw = False; self.stable = False; self.changed_at = time.monotonic()

    def pressed_edge(self, now):
        raw = bool(self.read_fn())
        if raw != self.raw: self.raw, self.changed_at = raw, now
        if raw != self.stable and now - self.changed_at >= self.debounce:
            self.stable = raw
            return self.stable
        return False


class BehaviorManager:
    def __init__(self, motor, line_source, line_controller, obstacle_detector, hal, config,
                 person_detector=None):
        self.motor = motor; self.line_source = line_source; self.controller = line_controller
        self.obstacles = obstacle_detector; self.hal = hal; self.config = config
        self.person_detector = person_detector; self.state = RunState.RUNNING
        self.clear_since = None; self.person_hits = 0; self.resume_armed = False
        self.last_obstacle = None; self.last_line = None; self._status_lock = threading.Lock()
        self._remote_resume = threading.Event()
        self.button = DebouncedButton(hal.button_read, config.safety.button_debounce_seconds)
        self.log = logging.getLogger("smartcar.behavior")

    def update(self, now=None):
        now = time.monotonic() if now is None else now
        button_edge = self.button.pressed_edge(now)
        if self.state == RunState.FAULT:
            self._safety_brake(); return self.state
        obstacle = self.obstacles.read()
        with self._status_lock: self.last_obstacle = obstacle
        person_blocked = self._person_blocked()
        unsafe = obstacle.level in (ObstacleLevel.BLOCKED, ObstacleLevel.SENSOR_ERROR) or person_blocked

        if unsafe:
            if self.state != RunState.PAUSED: self.log.warning("safety pause: %s", obstacle.level.value)
            self.state = RunState.PAUSED; self.clear_since = None
            self.resume_armed = False; self._remote_resume.clear(); self._safety_brake(); return self.state

        if self.state == RunState.PAUSED:
            self.clear_since = now if obstacle.level == ObstacleLevel.CLEAR else None
            self.state = RunState.WAIT_CLEAR; self.resume_armed = not self.button.stable
            self._safety_brake(); return self.state

        if self.state == RunState.WAIT_CLEAR:
            self._safety_brake()
            if obstacle.level != ObstacleLevel.CLEAR:
                self.clear_since = None; self._remote_resume.clear(); return self.state
            if not self.button.stable: self.resume_armed = True
            if self.clear_since is None: self.clear_since = now
            clear_long_enough = now - self.clear_since >= self.config.safety.clear_confirm_seconds
            remote_resume = self._remote_resume.is_set()
            if clear_long_enough and self.resume_armed and (button_edge or remote_resume):
                self._remote_resume.clear()
                self.state = RunState.RUNNING; self.log.info("manual resume accepted")
            return self.state

        if obstacle.level == ObstacleLevel.WARNING:
            speed = self.config.motor.warning_speed; self.motor.run(speed, speed); return self.state

        reading = self.line_source.read()
        with self._status_lock: self.last_line = reading
        if hasattr(self.line_source, "is_healthy") and not self.line_source.is_healthy():
            self.state = RunState.FAULT; self._safety_brake(); self.log.error("line source unhealthy")
            return self.state
        left, right, must_stop = self.controller.command(reading, now)
        if must_stop:
            self.state = RunState.FAULT; self._safety_brake(); self.log.error("line lost timeout")
        else: self.motor.run(left, right)
        return self.state

    def pause(self, reason="operator"):
        self.log.warning("pause requested: %s", reason)
        self.state = RunState.PAUSED
        self.clear_since = None
        self.resume_armed = False
        self._safety_brake()

    def _safety_brake(self):
        if hasattr(self.controller, "reset_motion"): self.controller.reset_motion()
        self.motor.brake()

    def request_resume(self):
        """Queue a resume request; update() remains the sole safety gate."""
        if self.state != RunState.WAIT_CLEAR:
            return False
        self._remote_resume.set()
        return True

    def status(self):
        with self._status_lock:
            obstacle, line = self.last_obstacle, self.last_line
        result = {"state": self.state.value, "person_hits": self.person_hits}
        if obstacle is not None:
            result.update({"obstacle": obstacle.level.value, "distance_cm": obstacle.distance_cm,
                           "avoid": list(obstacle.infrared)})
        if line is not None:
            result.update({"line_error": line.error, "line_confidence": line.confidence,
                           "line_detected": line.detected})
        return result

    def _person_blocked(self):
        if self.person_detector is None: return False
        if hasattr(self.person_detector, "healthy") and not self.person_detector.healthy():
            self.log.error("person detector unhealthy")
            return True
        detections = self.person_detector.latest()
        found = any(d.class_name == "person" for d in detections)
        self.person_hits = self.person_hits + 1 if found else 0
        return self.person_hits >= self.config.safety.person_confirm_frames

    def shutdown(self):
        try: self._safety_brake()
        except Exception: self.log.exception("motor brake failed during shutdown")
        try:
            if hasattr(self.line_source, "close"): self.line_source.close()
            if self.person_detector is not None: self.person_detector.close()
        finally:
            try: self.motor.close()
            except Exception: self.log.exception("motor backend close failed")
