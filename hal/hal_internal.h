#ifndef SMARTCAR_HAL_INTERNAL_H
#define SMARTCAR_HAL_INTERNAL_H

#include "hal.h"

/* wiringPi numbering, matched to the Yahboom 4WD image currently installed. */
#define PIN_LEFT_GO 28
#define PIN_LEFT_BACK 29
#define PIN_RIGHT_GO 24
#define PIN_RIGHT_BACK 25
#define PIN_LEFT_PWM 27
#define PIN_RIGHT_PWM 23
#define PIN_TRACK_L1 9
#define PIN_TRACK_L2 21
#define PIN_TRACK_R1 7
#define PIN_TRACK_R2 1
#define PIN_AVOID_LEFT 26
#define PIN_AVOID_RIGHT 0
#define PIN_ECHO 30
#define PIN_TRIG 31
#define PIN_LED_R 3
#define PIN_LED_G 2
#define PIN_LED_B 5
#define PIN_SERVO_FRONT 4
#define PIN_SERVO_UP_DOWN 13
#define PIN_SERVO_LEFT_RIGHT 14
#define PIN_BUTTON 10

#define PWM_RANGE 255
extern int g_hal_initialized;
extern int g_wiring_initialized;
int hal_clamp(int value, int lower, int upper);

#endif
