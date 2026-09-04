import threading
import time
from dataclasses import dataclass


@dataclass
class Detection:
    class_name: str
    confidence: float
    bbox: tuple


class CameraStream:
    """One capture thread shared by line following and DNN inference."""
    def __init__(self, index=0):
        import cv2
        self.cv2 = cv2; self.capture = cv2.VideoCapture(index)
        self._frame = None; self._lock = threading.Lock(); self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._closed = False

    def set(self, prop, value): return self.capture.set(prop, value)
    def start(self):
        if not self.capture.isOpened(): raise RuntimeError("camera {} failed to open".format(self.capture))
        self._thread.start(); return self
    def _loop(self):
        while not self._stop.is_set():
            ok, frame = self.capture.read()
            if ok:
                with self._lock: self._frame = frame
            else: self._stop.wait(0.05)

    def read(self):
        with self._lock:
            return (False, None) if self._frame is None else (True, self._frame.copy())

    def release(self):
        if self._closed: return
        self._closed = True
        self._stop.set()
        if self._thread.is_alive(): self._thread.join(timeout=1.0)
        self.capture.release()

    close = release


class DNNDetector:
    """Background OpenCV-DNN detector. Model-specific decoding is injected."""
    def __init__(self, capture, model_path, decoder, input_size=(300, 300), interval=0.2,
                 config_path=None):
        import cv2
        self.cv2 = cv2; self.capture = capture; self.decoder = decoder
        self.net = cv2.dnn.readNet(model_path, config_path or "")
        self.input_size = input_size; self.interval = interval
        self._latest = []; self._lock = threading.Lock(); self._stop = threading.Event()
        self._started_at = time.monotonic(); self._last_update = None; self._error = None
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def start(self): self._thread.start(); return self
    def latest(self):
        with self._lock: return list(self._latest)

    def _loop(self):
        while not self._stop.is_set():
            ok, frame = self.capture.read()
            if ok and frame is not None:
                try:
                    blob = self.cv2.dnn.blobFromImage(frame, 1.0 / 127.5, self.input_size, 127.5, swapRB=True)
                    self.net.setInput(blob); output = self.net.forward()
                    decoded = self.decoder(output, frame.shape)
                    with self._lock:
                        self._latest = decoded; self._last_update = time.monotonic(); self._error = None
                except Exception as exc:
                    with self._lock: self._error = str(exc)
            self._stop.wait(self.interval)

    def healthy(self, max_stale_seconds=2.0):
        with self._lock: last_update, error = self._last_update, self._error
        if error is not None: return False
        now = time.monotonic()
        if last_update is None: return now - self._started_at <= max_stale_seconds
        return now - last_update <= max_stale_seconds

    def close(self):
        self._stop.set()
        if self._thread.is_alive(): self._thread.join(timeout=1.0)


class MobileNetSSDPersonDecoder:
    """Decode the common Caffe MobileNet-SSD [1,1,N,7] output (person id 15)."""
    def __init__(self, confidence=0.55): self.confidence = confidence

    def __call__(self, output, shape):
        height, width = shape[:2]; detections = []
        for row in output.reshape(-1, 7):
            confidence, class_id = float(row[2]), int(row[1])
            if class_id != 15 or confidence < self.confidence: continue
            x1 = max(0, min(width - 1, int(round(float(row[3]) * width))))
            y1 = max(0, min(height - 1, int(round(float(row[4]) * height))))
            x2 = max(0, min(width - 1, int(round(float(row[5]) * width))))
            y2 = max(0, min(height - 1, int(round(float(row[6]) * height))))
            detections.append(Detection("person", confidence, (x1, y1, x2, y2)))
        return detections


class FigurineClassifier:
    def __init__(self, model_path, labels, confidence=0.6):
        import cv2
        self.cv2 = cv2; self.net = cv2.dnn.readNet(model_path)
        self.labels = tuple(labels); self.confidence = confidence

    def classify(self, crop):
        blob = self.cv2.dnn.blobFromImage(crop, 1.0 / 127.5, (224, 224), 127.5, swapRB=True)
        self.net.setInput(blob); scores = self.net.forward().reshape(-1)
        index = int(scores.argmax()); confidence = float(scores[index])
        return (self.labels[index] if confidence >= self.confidence else "unknown", confidence)


class ColorDetector:
    """HSV largest-contour detector migrated from the legacy prototype."""
    DEFAULT_RANGES = {
        "red": (((0, 70, 50), (10, 255, 255)), ((170, 70, 50), (179, 255, 255))),
        "green": (((35, 43, 46), (77, 255, 255)),),
        "blue": (((100, 43, 46), (124, 255, 255)),),
        "yellow": (((26, 43, 46), (34, 255, 255)),),
        "orange": (((11, 43, 46), (25, 255, 255)),),
    }

    def __init__(self, color="red", min_area_ratio=0.002, ranges=None):
        import cv2
        import numpy as np
        self.cv2 = cv2; self.np = np; self.color = color
        self.min_area_ratio = min_area_ratio; self.ranges = ranges or self.DEFAULT_RANGES
        if color not in self.ranges: raise ValueError("unsupported color: {}".format(color))

    def detect(self, frame):
        hsv = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2HSV)
        mask = None
        for lower, upper in self.ranges[self.color]:
            part = self.cv2.inRange(hsv, self.np.array(lower), self.np.array(upper))
            mask = part if mask is None else self.cv2.bitwise_or(mask, part)
        kernel = self.cv2.getStructuringElement(self.cv2.MORPH_ELLIPSE, (5, 5))
        mask = self.cv2.morphologyEx(mask, self.cv2.MORPH_OPEN, kernel)
        mask = self.cv2.morphologyEx(mask, self.cv2.MORPH_CLOSE, kernel)
        contours = self.cv2.findContours(mask, self.cv2.RETR_EXTERNAL, self.cv2.CHAIN_APPROX_SIMPLE)[-2]
        if not contours: return None
        contour = max(contours, key=self.cv2.contourArea); area = float(self.cv2.contourArea(contour))
        frame_area = float(frame.shape[0] * frame.shape[1])
        if area / frame_area < self.min_area_ratio: return None
        x, y, width, height = self.cv2.boundingRect(contour)
        return Detection(self.color, min(1.0, area / (frame_area * 0.15)), (x, y, x + width, y + height))
