#!/usr/bin/env python3
import argparse
import logging
import os
import signal
import time

from smartcar.behavior import BehaviorManager
from smartcar.config import CarConfig
from smartcar.hal_wrapper import SmartCarHAL
from smartcar.line_source import CameraLineSource, IRLineSource, LineController
from smartcar.motor_backend import ArduinoMotorBackend, GPIOMotorBackend
from smartcar.obstacle import ObstacleDetector
from smartcar.vision import CameraStream, DNNDetector, MobileNetSSDPersonDecoder
from smartcar.remote import CommandServer


def parse_args():
    parser = argparse.ArgumentParser(description="SmartCarV2 safe line-following controller")
    parser.add_argument("--line-source", choices=("ir", "camera"), default="ir")
    parser.add_argument("--motor-backend", choices=("gpio", "arduino"), default="gpio")
    parser.add_argument("--arduino-port", default=None)
    parser.add_argument("--person-model", help="MobileNet-SSD Caffe model (.caffemodel)")
    parser.add_argument("--person-config", help="MobileNet-SSD network definition (.prototxt)")
    parser.add_argument("--log-level", choices=("DEBUG", "INFO", "WARNING", "ERROR"), default="INFO")
    parser.add_argument("--tcp", action="store_true", help="enable authenticated TCP control")
    parser.add_argument("--tcp-token", help="required shared token when --tcp is enabled")
    parser.add_argument("--tcp-host", default=None)
    parser.add_argument("--tcp-port", type=int, default=None)
    return parser.parse_args()


def main():
    args = parse_args(); config = CarConfig().validate()
    logging.basicConfig(level=getattr(logging, args.log_level.upper()),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    stopping = [False]
    signal.signal(signal.SIGINT, lambda *_: stopping.__setitem__(0, True))
    signal.signal(signal.SIGTERM, lambda *_: stopping.__setitem__(0, True))
    hal = SmartCarHAL(); manager = None; motor = None; camera = None; command_server = None
    try:
        hal.init()
        if args.line_source == "camera" or args.person_model:
            camera = CameraStream(config.line.camera_index)
            camera.set(3, config.line.frame_width); camera.set(4, config.line.frame_height); camera.start()
        line_source = IRLineSource(hal) if args.line_source == "ir" else CameraLineSource(config.line, camera)
        person_detector = None
        if args.person_model:
            if not args.person_config: raise ValueError("--person-config is required with --person-model")
            person_detector = DNNDetector(camera, args.person_model,
                                          MobileNetSSDPersonDecoder(config.vision.person_confidence),
                                          config_path=args.person_config).start()
        if args.motor_backend == "gpio": motor = GPIOMotorBackend(hal)
        else:
            port = args.arduino_port or config.arduino.port
            motor = ArduinoMotorBackend(port, config.arduino.baudrate, config.arduino.timeout_seconds)
        manager = BehaviorManager(motor, line_source, LineController(config.line, config.motor),
                                  ObstacleDetector(hal, config.safety), hal, config, person_detector)
        if args.tcp:
            tcp_token = args.tcp_token or os.environ.get("SMARTCAR_TCP_TOKEN")
            if not tcp_token: raise ValueError("--tcp-token or SMARTCAR_TCP_TOKEN is required with --tcp")
            command_server = CommandServer(manager, hal, config, tcp_token,
                                           args.tcp_host or config.remote.host,
                                           args.tcp_port or config.remote.port).start()
        period = 1.0 / config.loop_hz
        while not stopping[0]:
            started = time.monotonic(); manager.update(started)
            time.sleep(max(0.0, period - (time.monotonic() - started)))
    except Exception:
        logging.exception("fatal controller error")
        if motor is not None:
            try: motor.brake()
            except Exception: logging.exception("emergency backend brake failed")
        hal.motor_brake()
        return 1
    finally:
        if command_server is not None: command_server.close()
        if manager is not None: manager.shutdown()
        elif motor is not None: motor.close()
        if camera is not None: camera.close()
        hal.cleanup()
    return 0


if __name__ == "__main__": raise SystemExit(main())
