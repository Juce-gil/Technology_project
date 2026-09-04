#include <softPwm.h>
#include "hal_internal.h"

void led_set(int red, int green, int blue) {
    if (!g_hal_initialized) return;
    softPwmWrite(PIN_LED_R, hal_clamp(red, 0, 255));
    softPwmWrite(PIN_LED_G, hal_clamp(green, 0, 255));
    softPwmWrite(PIN_LED_B, hal_clamp(blue, 0, 255));
}
