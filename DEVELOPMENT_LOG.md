# SmartCarV2 Development Log

Paused: 2026-09-04 (Asia/Shanghai)

Resumed and optimized: 2026-09-04 (Asia/Shanghai)

## Optimization pass

- Fixed latched `FAULT` handling so a lost-line fault cannot drive again on the
  following control cycle.
- Required a post-stop button release before a new press can resume motion.
- Added camera-line and DNN health checks that fail safe.
- Changed TCP STATUS to cached readings, preventing concurrent ultrasonic pulses.
- Changed Arduino heartbeats so they cannot keep stale motion alive.
- Added deterministic cross-platform DNN coordinate rounding.
- Added HAL partial-initialization cleanup, PWM shutdown, 64-bit ultrasonic
  timing and repeat servo pulses.
- Implemented distinct low-speed hold, directional search and final stop phases
  for line loss.
- Added startup configuration validation, hardened Arduino short-write/cleanup
  handling and expanded the suite to 21 tests.

## Sensor calibration run

A 30-second read-only monitor was run with motors continuously braked. The
ultrasonic path responded to nearby objects (samples around 4.5, 6.9, 11.9,
25.1 and 68 cm; open-area readings around 160 cm). Tracking stayed fixed at
`[0,0,0,1]`, avoid stayed fixed at `[0,1]`, and the button remained `False`.
The ultrasonic path is operational; tracking, IR avoid and button require a
focused wiring/pin/sensitivity check if they were physically exercised during
the capture.

## Current status

Implementation is intentionally paused at the user's request. Do not assume the
optional vision changes at the end of this log have been deployed to the Pi.

### Completed locally

- C HAL implemented for initialization/cleanup, signed differential motors,
  three servos, ultrasonic distance with timeout/filtering, four tracking
  sensors, two avoid sensors, onboard button and RGB output.
- Python ctypes wrapper and safe GPIO motor backend implemented.
- IR and camera line sources implemented behind one `LineReading` interface.
- PD steering, bounded lost-line search and latched lost-line stop implemented.
- Obstacle levels and `RUNNING -> PAUSED -> WAIT_CLEAR -> RUNNING` state machine
  implemented with stable-clear time and debounced manual button resume.
- Arduino framed serial protocol, Python backend and watchdog firmware implemented.
- Optional OpenCV-DNN infrastructure, MobileNet-SSD person decoder, figurine
  classifier interface and shared camera stream implemented.
- Installation, architecture, API, schedule and test-plan documentation written.

### Automated verification

- Initial local test run: 8/8 passed.
- Raspberry Pi test run after first deployment: 8/8 passed.
- Local Python compileall passed before the final vision integration edits.
- A ninth vision decoder test was added after that run and still needs execution.

### Raspberry Pi verification

Target: `pi@10.118.221.59`, hostname `yahboom4wd`, Raspbian Buster,
Python 3.7.3, OpenCV 4.1.2.

- `/home/pi/SmartCarV2` was created and the HAL compiled successfully with GCC
  and wiringPi.
- Safe HAL smoke test passed while the legacy controller was temporarily paused:
  - tracking: `[0, 0, 0, 1]`
  - avoid: `[0, 1]`
  - ultrasonic distance: approximately `49.51 cm`
  - button: `False`
- Motors were explicitly braked; no autonomous driving loop was started.
- Legacy `/home/pi/SmartCar/bluetooth_control` was restored and verified as one
  running process (PID at the time: 1155).

## Important deployment boundary

The Pi contains the version deployed before the latest edits to:

- shared `CameraStream`
- MobileNet-SSD person decoder
- `--person-model` / `--person-config` CLI integration
- `tests/test_vision.py`

Those latest files exist locally under `F:\开发板\SmartCarV2` but have not yet
been retested or copied to `/home/pi/SmartCarV2`.

## Known constraints and safety notes

- The factory `bluetooth_control` process and SmartCarV2 must never run together;
  both own the same GPIO/PWM resources.
- WiringPi pin 10 (BCM8) is used as the button in the key example but as the
  buzzer in another legacy example. SmartCarV2 reserves it for the button and
  does not drive the buzzer.
- The photographed RGB headlight remains red even during direct GPIO tests; this
  is currently diagnosed as a cable/interface/lamp-board hardware fault.
- Person model files and figurine training data are not included. Locally
  licensed model artifacts and a subject-separated dataset are still required.
- Arduino firmware is implemented but cannot be hardware-tested until an Arduino
  and its exact motor-driver pin mapping are connected.

## Resume checklist

1. Run local `compileall` and all tests, including `test_vision.py`.
2. Review shared-camera shutdown behavior and DNN error handling.
3. Sync the final vision changes to the Pi and rerun all tests.
4. Do not start `main.py` until the legacy controller is stopped and wheels are raised.
5. Calibrate line thresholds/PID and obstacle distances on the physical track.
6. Supply MobileNet-SSD model files and figurine dataset if optional vision must
   be completed, then measure FPS and accuracy on the Pi.
7. Confirm Arduino board/driver/pins before flashing and watchdog testing.

## Legacy migration

Useful concepts from `SmartCarV2.2` were migrated into the main tree in a
safety-hardened form: authenticated/stream-framed TCP control, HSV color target
detection, and visual target steering. Unsafe legacy HAL, fail-open ultrasonic
handling, automatic obstacle resume and indefinite lost-line driving were not
migrated. The legacy subdirectory was removed after the expanded test suite
passed.
## 2026-09-04 - Sensor identification and buttonless safe resume

- Identified the two blue-lit BST-01 side boards as left/right infrared obstacle sensors.
- Identified the underside four-channel board as the line sensor; line calibration is deferred until a black test strip is available.
- No physical KEY/START button could be confirmed from the installed hardware photographs.
- Added authenticated TCP `RESUME`; it only queues a request. The behavior loop still requires `WAIT_CLEAR` and the configured clear confirmation interval, and cancels the request if an obstacle returns.
- Added regression tests for accepted, premature, and cancelled remote resume requests. All 24 tests pass locally and on the Raspberry Pi.
- Camera enumerates as USB UVC `Sanhao Face` on `/dev/video0` (capture) and `/dev/video1` (metadata), but frame capture timed out and the driver subsequently reported `Device or resource busy`. Camera recovery remains pending; the legacy Bluetooth controller was restored after diagnostics.
