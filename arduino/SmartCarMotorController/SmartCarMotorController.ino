#include <Arduino.h>

static const uint8_t SOF = 0xAA, VERSION = 1, MAX_PAYLOAD = 32;
static const uint8_t CMD_SET_MOTOR = 0x01, CMD_BRAKE = 0x02;
static const uint8_t CMD_HEARTBEAT = 0x03, CMD_GET_STATUS = 0x04, CMD_STATUS = 0x81;
static const unsigned long WATCHDOG_MS = 500;

/* Adapt these six pins to the selected Arduino motor driver. */
static const uint8_t LEFT_IN1 = 4, LEFT_IN2 = 5, LEFT_PWM = 6;
static const uint8_t RIGHT_IN1 = 7, RIGHT_IN2 = 8, RIGHT_PWM = 9;

uint8_t frame[1 + 4 + MAX_PAYLOAD + 1], frameIndex = 0, expectedLength = 0;
uint8_t lastSequence = 0; bool haveSequence = false;
unsigned long lastValidCommand = 0; int16_t currentLeft = 0, currentRight = 0;

uint8_t crc8(const uint8_t *data, uint8_t length) {
  uint8_t crc = 0;
  while (length--) {
    crc ^= *data++;
    for (uint8_t i = 0; i < 8; ++i) crc = (crc & 0x80) ? (crc << 1) ^ 0x07 : crc << 1;
  }
  return crc;
}

void driveOne(int16_t speed, uint8_t in1, uint8_t in2, uint8_t pwm) {
  speed = constrain(speed, -255, 255);
  digitalWrite(in1, speed > 0 ? HIGH : LOW);
  digitalWrite(in2, speed < 0 ? HIGH : LOW);
  analogWrite(pwm, abs(speed));
}

void brake() {
  currentLeft = currentRight = 0;
  driveOne(0, LEFT_IN1, LEFT_IN2, LEFT_PWM);
  driveOne(0, RIGHT_IN1, RIGHT_IN2, RIGHT_PWM);
}

void sendStatus(uint8_t sequence, uint8_t errors) {
  /* battery_mV=0 means no battery ADC is configured; then left/right/error. */
  uint8_t body[11] = {VERSION, CMD_STATUS, sequence, 7, 0, 0,
    (uint8_t)(currentLeft & 0xff), (uint8_t)((currentLeft >> 8) & 0xff),
    (uint8_t)(currentRight & 0xff), (uint8_t)((currentRight >> 8) & 0xff), errors};
  Serial.write(SOF); Serial.write(body, sizeof(body)); Serial.write(crc8(body, sizeof(body)));
}

void handleFrame() {
  uint8_t command = frame[2], sequence = frame[3], length = frame[4];
  if (frame[1] != VERSION || crc8(&frame[1], 4 + length) != frame[5 + length]) return;
  if (haveSequence && sequence == lastSequence && command == CMD_SET_MOTOR) return;
  lastSequence = sequence; haveSequence = true;
  if (command == CMD_SET_MOTOR && length == 4) {
    currentLeft = (int16_t)(frame[5] | (frame[6] << 8));
    currentRight = (int16_t)(frame[7] | (frame[8] << 8));
    driveOne(currentLeft, LEFT_IN1, LEFT_IN2, LEFT_PWM);
    driveOne(currentRight, RIGHT_IN1, RIGHT_IN2, RIGHT_PWM);
    lastValidCommand = millis();
  } else if (command == CMD_BRAKE && length == 0) {
    brake(); lastValidCommand = millis();
  } else if (command == CMD_HEARTBEAT && length == 0) {
    /* Link liveness only: stale motion must still hit the 500 ms watchdog. */
  } else if (command == CMD_GET_STATUS && length == 0) {
    sendStatus(sequence, 0);
  }
}

void consume(uint8_t value) {
  if (frameIndex == 0 && value != SOF) return;
  frame[frameIndex++] = value;
  if (frameIndex == 5) {
    if (frame[4] > MAX_PAYLOAD) { frameIndex = 0; return; }
    expectedLength = 6 + frame[4];
  }
  if (expectedLength && frameIndex == expectedLength) {
    handleFrame(); frameIndex = 0; expectedLength = 0;
  }
  if (frameIndex >= sizeof(frame)) { frameIndex = 0; expectedLength = 0; }
}

void setup() {
  pinMode(LEFT_IN1, OUTPUT); pinMode(LEFT_IN2, OUTPUT); pinMode(LEFT_PWM, OUTPUT);
  pinMode(RIGHT_IN1, OUTPUT); pinMode(RIGHT_IN2, OUTPUT); pinMode(RIGHT_PWM, OUTPUT);
  brake(); Serial.begin(115200); lastValidCommand = millis();
}

void loop() {
  while (Serial.available()) consume((uint8_t)Serial.read());
  if (millis() - lastValidCommand > WATCHDOG_MS) brake();
}
