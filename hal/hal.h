#ifndef SMARTCAR_HAL_H
#define SMARTCAR_HAL_H

#ifdef __cplusplus
extern "C" {
#endif

enum { HAL_OK = 0, HAL_ERR_INIT = -1, HAL_ERR_ARG = -2, HAL_ERR_TIMEOUT = -3 };

int hal_init(void);
void hal_cleanup(void);
int hal_is_initialized(void);

void motor_run(int left_speed, int right_speed);
void motor_brake(void);
void servo_set_angle(int channel, int angle);

float sensor_distance(void);
float sensor_distance_filtered(void);
void sensor_read_tracking(int state[4]);
void sensor_read_avoid(int state[2]);
int button_read(void);

void led_set(int red, int green, int blue);

#ifdef __cplusplus
}
#endif
#endif
