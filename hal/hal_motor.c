#include <wiringPi.h>
#include <softPwm.h>
#include <stdlib.h>
#include "hal_internal.h"

static void drive_one(int speed, int pin_go, int pin_back, int pin_pwm) {
    speed = hal_clamp(speed, -PWM_RANGE, PWM_RANGE);
    if (speed > 0) {
        digitalWrite(pin_go, HIGH); digitalWrite(pin_back, LOW);
    } else if (speed < 0) {
        digitalWrite(pin_go, LOW); digitalWrite(pin_back, HIGH);
    } else {
        digitalWrite(pin_go, LOW); digitalWrite(pin_back, LOW);
    }
    softPwmWrite(pin_pwm, abs(speed));
}

void motor_run(int left_speed, int right_speed) {
    if (!g_hal_initialized) return;
    drive_one(left_speed, PIN_LEFT_GO, PIN_LEFT_BACK, PIN_LEFT_PWM);
    drive_one(right_speed, PIN_RIGHT_GO, PIN_RIGHT_BACK, PIN_RIGHT_PWM);
}

void motor_brake(void) {
    if (!g_wiring_initialized) return;
    softPwmWrite(PIN_LEFT_PWM, 0); softPwmWrite(PIN_RIGHT_PWM, 0);
    digitalWrite(PIN_LEFT_GO, LOW); digitalWrite(PIN_LEFT_BACK, LOW);
    digitalWrite(PIN_RIGHT_GO, LOW); digitalWrite(PIN_RIGHT_BACK, LOW);
}
