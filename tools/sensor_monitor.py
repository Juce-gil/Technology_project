#!/usr/bin/env python3
"""Safe, read-only sensor monitor for bench calibration."""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from smartcar.hal_wrapper import SmartCarHAL


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--interval", type=float, default=0.2)
    args = parser.parse_args()
    hal = SmartCarHAL(); hal.init()
    started = time.monotonic()
    try:
        hal.motor_brake()
        while time.monotonic() - started < args.duration:
            distance = hal.distance_filtered()
            print(json.dumps({
                "t": round(time.monotonic() - started, 1),
                "track": hal.read_tracking(),
                "avoid": hal.read_avoid(),
                "distance_cm": None if distance < 0 else round(distance, 1),
                "button": hal.button_read(),
            }, separators=(",", ":")), flush=True)
            hal.motor_brake()
            time.sleep(max(0.0, args.interval))
    finally:
        hal.motor_brake(); hal.cleanup()
    return 0


if __name__ == "__main__": raise SystemExit(main())
