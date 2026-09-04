import threading
import time
from abc import ABCMeta, abstractmethod
from .protocol import CMD_BRAKE, CMD_GET_STATUS, CMD_HEARTBEAT, encode_frame, encode_motor


class MotorBackend(metaclass=ABCMeta):
    @abstractmethod
    def run(self, left, right): pass
    @abstractmethod
    def brake(self): pass
    def close(self): self.brake()


class GPIOMotorBackend(MotorBackend):
    def __init__(self, hal): self.hal = hal
    def run(self, left, right): self.hal.motor_run(left, right)
    def brake(self): self.hal.motor_brake()


class ArduinoMotorBackend(MotorBackend):
    def __init__(self, port, baudrate=115200, timeout=0.2, serial_factory=None):
        if serial_factory is None:
            try: import serial
            except ImportError as exc: raise RuntimeError("install pyserial for Arduino backend") from exc
            serial_factory = serial.Serial
        self.serial = serial_factory(port, baudrate=baudrate, timeout=timeout)
        self.sequence = 0; self.closed = False; self.last_error = None
        self._lock = threading.RLock()
        self._thread = threading.Thread(target=self._heartbeat, daemon=True)
        self._thread.start()

    def _send(self, command, payload=b""):
        with self._lock:
            if self.closed: raise RuntimeError("Arduino backend is closed")
            self.sequence = (self.sequence + 1) & 0xFF
            frame = encode_frame(command, self.sequence, payload)
            try:
                written = self.serial.write(frame)
                if written is not None and written != len(frame): raise IOError("short serial write")
                self.last_error = None
            except Exception as exc:
                self.last_error = exc
                raise

    def run(self, left, right):
        with self._lock:
            if self.closed: raise RuntimeError("Arduino backend is closed")
            self.sequence = (self.sequence + 1) & 0xFF
            frame = encode_motor(self.sequence, int(left), int(right))
            try:
                written = self.serial.write(frame)
                if written is not None and written != len(frame): raise IOError("short serial write")
                self.last_error = None
            except Exception as exc:
                self.last_error = exc
                raise

    def brake(self): self._send(CMD_BRAKE)
    def request_status(self): self._send(CMD_GET_STATUS)

    def _heartbeat(self):
        while not self.closed:
            try: self._send(CMD_HEARTBEAT)
            except Exception as exc: self.last_error = exc
            time.sleep(0.2)

    def close(self):
        self.closed = True
        self._thread.join(timeout=0.5)
        try:
            with self._lock:
                self.closed = False
                self._send(CMD_BRAKE)
        except Exception: pass
        finally:
            self.closed = True
            self.serial.close()
