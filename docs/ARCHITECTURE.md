# Architecture

```text
IR sensors ──> IRLineSource ───────┐
Camera ─────> CameraLineSource ────┼─> BehaviorManager ─> MotorBackend
US + IR ────> ObstacleDetector ────┘          │             ├─ GPIO/C HAL
Button ───────────────────────────────────────┘             └─ Arduino serial

Python ──ctypes──> libsmartcar.so ──wiringPi──> Raspberry Pi GPIO
```

The 10 Hz behavior loop gives safety priority over navigation. `BLOCKED` or
repeated sensor failure brakes immediately. Once clear, the state changes from
`PAUSED` to `WAIT_CLEAR`; only a debounced physical button edge or an authenticated
TCP resume request can resume after the stable-clear interval. A button must first
be observed released after the stop, and a queued TCP request is cancelled if an
obstacle returns, so neither input can bypass the safety gate.
Warning distance uses a reduced straight speed. Clear state delegates to the
selected line source and PD steering controller. A prolonged lost line enters
`FAULT` and remains stopped until restart.

The optional Arduino backend preserves the same `run(left,right)` and `brake()`
interface. Its firmware independently brakes after 500 ms without a valid
motor command or heartbeat.

## State machine

```text
RUNNING -- obstacle/person/sensor failure --> PAUSED
PAUSED  -- obstacle absent ----------------> WAIT_CLEAR
WAIT_CLEAR -- stable clear + manual request --> RUNNING
RUNNING -- line lost timeout -------------> FAULT
FAULT ------------------------------------> restart required
```

## Control priority

1. Fatal exception or sensor failure: brake.
2. Blocking obstacle or confirmed person: brake and latch pause.
3. Warning distance: reduced straight speed.
4. Selected line source: PD differential steering.
5. Lost line: reduced-speed continuation, bounded directional search, followed
   by a latched `FAULT` stop that cannot restart itself.
