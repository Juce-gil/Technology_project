# SmartCarV2

SmartCarV2 restructures the Yahboom Raspberry Pi 4WD examples into a safe,
testable controller. C handles GPIO timing and Python handles behavior,
line following and optional vision. Motors always start and exit braked.

For a detailed distinction between implemented code, verified hardware and
remaining work, see [PROJECT_STATUS.md](PROJECT_STATUS.md).

## Quick start on the Raspberry Pi

```bash
cd /home/pi/SmartCarV2
make install
PYTHONPATH=. python3 main.py --line-source ir --motor-backend gpio
```

Camera line following:

```bash
PYTHONPATH=. python3 main.py --line-source camera --motor-backend gpio
```

Arduino motor backend:

```bash
python3 -m pip install --user pyserial
PYTHONPATH=. python3 main.py --line-source ir --motor-backend arduino \
  --arduino-port /dev/ttyACM0
```

Optional MobileNet-SSD person-stop mode (camera is shared with camera-line mode):

```bash
PYTHONPATH=. python3 main.py --line-source camera \
  --person-config models/MobileNetSSD_deploy.prototxt \
  --person-model models/MobileNetSSD_deploy.caffemodel
```

Model files and figurine training data are intentionally not embedded; provide
locally licensed artifacts and keep train/validation/test subjects separated.

Authenticated TCP diagnostics/control migrated from the older prototype:

```bash
SMARTCAR_TCP_TOKEN='change-this-token' PYTHONPATH=. \
  python3 main.py --line-source ir --tcp
```

Commands are terminated by `#`. Authenticate first with
`$4WD,AUTH,change-this-token#`; supported commands are `STOP`, `STATUS`,
`SPEED,<0-200>` and `LED,<r>,<g>,<b>`. `RESUME` only queues a request; motion
resumes when the main behavior loop has independently confirmed that all obstacle
sensors remain clear for the configured interval. This provides a safe fallback
for hardware variants without a physical start button.

Before running, disable the legacy `/home/pi/bluetooth.sh` autostart process.
Two controllers must never own the same GPIO pins at the same time. Raise the
wheels for the first motor test and keep a physical power cutoff within reach.

Read-only bench sensor monitor (motors remain braked):

```bash
PYTHONPATH=. python3 tools/sensor_monitor.py --duration 30
```

See [installation](docs/INSTALL.md), [architecture](docs/ARCHITECTURE.md),
[API](docs/API.md), and the [test plan](docs/TEST_PLAN.md).
