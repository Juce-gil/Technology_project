#include <wiringPi.h>
#include "hal_internal.h"

static int servo_pin(int channel) {
    if (channel == 0) return PIN_SERVO_FRONT;
    if (channel == 1) return PIN_SERVO_UP_DOWN;
    if (channel == 2) return PIN_SERVO_LEFT_RIGHT;
    return -1;
}

void servo_set_angle(int channel, int angle) {
    int pin = servo_pin(channel);
    if (!g_hal_initialized || pin < 0) return;
    angle = hal_clamp(angle, 0, 180);
    int pulse_us = 500 + angle * 2000 / 180;
    /* Several complete 50 Hz periods make a standalone command reliable. */
    int i;
    for (i = 0; i < 8; ++i) {
        digitalWrite(pin, HIGH);
        delayMicroseconds((unsigned int)pulse_us);
        digitalWrite(pin, LOW);
        delayMicroseconds((unsigned int)(20000 - pulse_us));
    }
}
