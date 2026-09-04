import ctypes
import os
from typing import List


class HALError(RuntimeError):
    pass


class SmartCarHAL:
    def __init__(self, lib_path=None):
        if lib_path is None:
            lib_path = os.path.join(os.path.dirname(__file__), "libsmartcar.so")
        self._lib = ctypes.CDLL(lib_path)
        self._setup_signatures()
        self._initialized = False

    def _setup_signatures(self):
        lib = self._lib
        lib.hal_init.argtypes, lib.hal_init.restype = [], ctypes.c_int
        lib.hal_cleanup.argtypes, lib.hal_cleanup.restype = [], None
        lib.motor_run.argtypes, lib.motor_run.restype = [ctypes.c_int, ctypes.c_int], None
        lib.motor_brake.argtypes, lib.motor_brake.restype = [], None
        lib.servo_set_angle.argtypes, lib.servo_set_angle.restype = [ctypes.c_int, ctypes.c_int], None
        lib.sensor_distance_filtered.argtypes, lib.sensor_distance_filtered.restype = [], ctypes.c_float
        lib.sensor_read_tracking.argtypes = [ctypes.POINTER(ctypes.c_int)]
        lib.sensor_read_tracking.restype = None
        lib.sensor_read_avoid.argtypes = [ctypes.POINTER(ctypes.c_int)]
        lib.sensor_read_avoid.restype = None
        lib.button_read.argtypes, lib.button_read.restype = [], ctypes.c_int
        lib.led_set.argtypes, lib.led_set.restype = [ctypes.c_int] * 3, None

    def init(self):
        rc = self._lib.hal_init()
        if rc != 0:
            raise HALError("HAL initialization failed: {}".format(rc))
        self._initialized = True

    def cleanup(self):
        if self._initialized:
            self._lib.motor_brake()
            self._lib.hal_cleanup()
            self._initialized = False

    def motor_run(self, left, right): self._lib.motor_run(int(left), int(right))
    def motor_brake(self):
        if self._initialized: self._lib.motor_brake()
    def servo_set_angle(self, channel, angle): self._lib.servo_set_angle(channel, angle)
    def distance_filtered(self): return float(self._lib.sensor_distance_filtered())
    def button_read(self): return bool(self._lib.button_read())
    def led_set(self, red, green, blue): self._lib.led_set(red, green, blue)

    def read_tracking(self) -> List[int]:
        arr = (ctypes.c_int * 4)()
        self._lib.sensor_read_tracking(arr)
        return list(arr)

    def read_avoid(self) -> List[int]:
        arr = (ctypes.c_int * 2)()
        self._lib.sensor_read_avoid(arr)
        return list(arr)

    def __enter__(self):
        self.init(); return self

    def __exit__(self, exc_type, exc, tb):
        self.cleanup()
