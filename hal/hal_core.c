#include <wiringPi.h>
#include <softPwm.h>
#include "hal_internal.h"

int g_hal_initialized = 0;
int g_wiring_initialized = 0;

int hal_clamp(int value, int lower, int upper) {
    if (value < lower) return lower;
    if (value > upper) return upper;
    return value;
}

int hal_init(void) {
    int pwm_left = 0, pwm_right = 0, pwm_r = 0, pwm_g = 0;
    if (g_hal_initialized) return HAL_OK;
    if (wiringPiSetup() < 0) return HAL_ERR_INIT;
    g_wiring_initialized = 1;

    const int outputs[] = {PIN_LEFT_GO, PIN_LEFT_BACK, PIN_RIGHT_GO,
        PIN_RIGHT_BACK, PIN_TRIG, PIN_LED_R, PIN_LED_G, PIN_LED_B,
        PIN_SERVO_FRONT, PIN_SERVO_UP_DOWN, PIN_SERVO_LEFT_RIGHT};
    unsigned int i;
    for (i = 0; i < sizeof(outputs) / sizeof(outputs[0]); ++i) {
        pinMode(outputs[i], OUTPUT);
        digitalWrite(outputs[i], LOW);
    }
    const int inputs[] = {PIN_TRACK_L1, PIN_TRACK_L2, PIN_TRACK_R1,
        PIN_TRACK_R2, PIN_AVOID_LEFT, PIN_AVOID_RIGHT, PIN_ECHO, PIN_BUTTON};
    for (i = 0; i < sizeof(inputs) / sizeof(inputs[0]); ++i) pinMode(inputs[i], INPUT);
    pullUpDnControl(PIN_BUTTON, PUD_UP);

    if (softPwmCreate(PIN_LEFT_PWM, 0, PWM_RANGE) != 0) goto fail;
    pwm_left = 1;
    if (softPwmCreate(PIN_RIGHT_PWM, 0, PWM_RANGE) != 0) goto fail;
    pwm_right = 1;
    if (softPwmCreate(PIN_LED_R, 0, PWM_RANGE) != 0) goto fail;
    pwm_r = 1;
    if (softPwmCreate(PIN_LED_G, 0, PWM_RANGE) != 0) goto fail;
    pwm_g = 1;
    if (softPwmCreate(PIN_LED_B, 0, PWM_RANGE) != 0) goto fail;
    g_hal_initialized = 1;
    motor_brake();
    led_set(0, 0, 0);
    return HAL_OK;
fail:
    digitalWrite(PIN_LEFT_GO, LOW); digitalWrite(PIN_LEFT_BACK, LOW);
    digitalWrite(PIN_RIGHT_GO, LOW); digitalWrite(PIN_RIGHT_BACK, LOW);
    if (pwm_left) softPwmStop(PIN_LEFT_PWM);
    if (pwm_right) softPwmStop(PIN_RIGHT_PWM);
    if (pwm_r) softPwmStop(PIN_LED_R);
    if (pwm_g) softPwmStop(PIN_LED_G);
    g_wiring_initialized = 0;
    return HAL_ERR_INIT;
}

void hal_cleanup(void) {
    if (!g_hal_initialized) return;
    motor_brake();
    led_set(0, 0, 0);
    softPwmStop(PIN_LEFT_PWM); softPwmStop(PIN_RIGHT_PWM);
    softPwmStop(PIN_LED_R); softPwmStop(PIN_LED_G); softPwmStop(PIN_LED_B);
    g_hal_initialized = 0;
    g_wiring_initialized = 0;
}

int hal_is_initialized(void) { return g_hal_initialized; }
