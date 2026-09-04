# Test and acceptance plan

## Automated

Run `make test`. Tests cover fragmented/corrupt serial frames, IR line mapping,
lost-line hold/search/braking, configuration validation, obstacle latching,
manual resume debouncing, held-button rejection, latched faults, authenticated
TCP control, person decoding and target steering.

## Bench tests

- Raise wheels; test each signed motor command and Ctrl+C braking.
- Validate all three servos, four tracking sensors, two avoid sensors, ultrasonic
  timeout, button and RGB channels independently.
- Disconnect camera, cover sensors and inject invalid distance readings; each
  safety failure must brake rather than continue.
- With Arduino, disconnect USB and stop the Pi process; motors must stop within
  500 ms. Also test bad CRC, truncated frames and duplicate motor sequences.

## Track tests

- IR and camera modes: straight, left/right bend, crossing and temporary line loss.
- Obstacle at clear, warning and blocked distances.
- Resume button ignored while blocked; accepted only after stable clear time.
- Run each line source for 20 minutes and record completion count, failures,
  CPU load and camera FPS.

## Optional vision evaluation

Keep train/validation/test subjects separate. Record person false positives,
misses and FPS under different light, range and occlusion. Report a confusion
matrix for `dress`, `top`, `trousers`, with low-confidence samples mapped to
`unknown`. Classification is display/logging only and never drives motion.
