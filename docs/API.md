# Public API

## C HAL

- `hal_init()` initializes all GPIO and PWM and returns `0` on success.
- `hal_cleanup()` brakes, turns the controllable RGB output off and releases state.
- `motor_run(left,right)` accepts signed speeds from -255 to 255.
- `motor_brake()` sets PWM and all direction outputs low.
- `servo_set_angle(channel,angle)` accepts channels 0..2 and angles 0..180.
- `sensor_distance_filtered()` returns centimeters or a negative error code.
- `sensor_read_tracking(int[4])` returns left-outer through right-outer active flags.
- `sensor_read_avoid(int[2])` returns left/right active flags.
- `button_read()` returns 1 while the active-low onboard button is pressed.
- `led_set(r,g,b)` accepts channel levels from 0 to 255.

## Python

- `LineSource.read() -> LineReading(error, confidence, detected, timestamp)`;
  error is normalized to -1..1.
- `MotorBackend.run(left,right)` and `brake()` hide GPIO versus Arduino control.
- `ObstacleDetector.read()` returns level, distance, infrared states and timestamp.
- `BehaviorManager.update()` executes one deterministic control cycle.
- `Detection(class_name,confidence,bbox)` is the common optional DNN result.

## Serial protocol

```text
AA | version | command | sequence | payload_length | payload | CRC8
```

CRC8 uses polynomial `0x07` over bytes from `version` through the payload.
Integers are little-endian. Commands are `01 SET_MOTOR(int16,int16)`, `02 BRAKE`,
`03 HEARTBEAT`, `04 GET_STATUS`, and `81 STATUS`. STATUS payload contains
`battery_mV:uint16` (zero if unavailable), `left:int16`, `right:int16`, and
`error_flags:uint8`.

## TCP diagnostics/control

TCP is disabled by default and requires `--tcp-token` or the preferable
`SMARTCAR_TCP_TOKEN` environment variable. Frames end with `#`.
Authenticate using `$4WD,AUTH,<token>#`. The commands `STOP`, `STATUS`,
`RESUME`, `SPEED,<value>` and `LED,<r>,<g>,<b>` are available. Only one client is
accepted, buffers are bounded, and fragmented/coalesced frames are handled.
`RESUME` only queues a request; the behavior loop accepts it after the system is
in `WAIT_CLEAR` and all obstacle inputs remain clear for the configured interval.
STATUS uses the behavior loop's cached sensor snapshot so it never triggers
concurrent ultrasonic measurements.

## Migrated visual helpers

- `ColorDetector.detect(frame)` returns the largest HSV color target as a
  `Detection` and handles both red hue bands.
- `TargetTracker.command(detection, frame_shape)` returns signed differential
  motor speeds, or a stop request when the target is absent.
