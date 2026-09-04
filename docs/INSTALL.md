# Installation and operation

## Prerequisites

Target: Raspberry Pi 4B, Raspbian Buster, Python 3.7+, GCC, GNU Make,
wiringPi and OpenCV 4.x. The current Yahboom image already has GCC,
Python 3.7.3 and OpenCV 4.1.2.

```bash
sudo apt-get install build-essential python3-opencv python3-serial
cd /home/pi/SmartCarV2
make install
make test
```

Do not install packages while connected only to the car access point. Connect
the Pi to a routed Wi-Fi network first, or copy packages over SSH.

## Prevent GPIO contention

The factory image starts `/home/pi/bluetooth.sh`, which runs the legacy
`bluetooth_control` binary. Disable that autostart entry before SmartCarV2 is
used, then reboot or terminate the old process. Do not run both controllers.

## USB SSH on Raspberry Pi 4B/Buster

Back up the SD card first. Add `dtoverlay=dwc2` to `/boot/config.txt`, and add
`modules-load=dwc2,g_ether` to the existing single line in `/boot/cmdline.txt`.
Enable SSH with `sudo systemctl enable ssh`. After reboot, connect the Pi USB-C
data port to the computer and use the RNDIS/USB Ethernet interface. Do not edit
`cmdline.txt` into multiple lines. Retain Wi-Fi SSH as the recovery path.

## First run

1. Raise all wheels and disconnect the LED board if its wiring is uncertain.
2. Build with `make install` and run `make test`.
3. Start IR mode at low configured speed.
4. Confirm forward direction for each wheel; swap direction configuration or
   motor leads only with power removed.
5. Put the car on the track only after obstacle braking and Ctrl+C braking pass.

The onboard button uses wiringPi pin 10 (BCM8). The old image also assigns that
pin to the buzzer in another example, so SmartCarV2 deliberately does not drive
the buzzer.
