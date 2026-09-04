#include <sys/time.h>
#include <stdint.h>
#include <wiringPi.h>
#include "hal_internal.h"

static uint64_t micros_now(void) {
    struct timeval tv; gettimeofday(&tv, 0);
    return (uint64_t)tv.tv_sec * 1000000ULL + (uint64_t)tv.tv_usec;
}

float sensor_distance(void) {
    if (!g_hal_initialized) return (float)HAL_ERR_INIT;
    digitalWrite(PIN_TRIG, LOW); delayMicroseconds(2);
    digitalWrite(PIN_TRIG, HIGH); delayMicroseconds(15); digitalWrite(PIN_TRIG, LOW);
    uint64_t deadline = micros_now() + 30000ULL;
    while (digitalRead(PIN_ECHO) == LOW) if (micros_now() >= deadline) return (float)HAL_ERR_TIMEOUT;
    uint64_t start = micros_now(); deadline = start + 30000ULL;
    while (digitalRead(PIN_ECHO) == HIGH) if (micros_now() >= deadline) return (float)HAL_ERR_TIMEOUT;
    return (micros_now() - start) * 0.017f;
}

static void sort(float *a, int n) {
    int i, j; float t;
    for (i = 0; i < n - 1; ++i) for (j = i + 1; j < n; ++j)
        if (a[j] < a[i]) { t = a[i]; a[i] = a[j]; a[j] = t; }
}

float sensor_distance_filtered(void) {
    float samples[5]; int count = 0, tries = 0;
    while (count < 5 && tries++ < 8) {
        float v = sensor_distance();
        if (v >= 0.0f && v <= 500.0f) samples[count++] = v;
        delay(10);
    }
    if (count < 3) return (float)HAL_ERR_TIMEOUT;
    sort(samples, count);
    if (count >= 5) return (samples[1] + samples[2] + samples[3]) / 3.0f;
    return samples[count / 2];
}

void sensor_read_tracking(int state[4]) {
    if (!state) return;
    if (!g_hal_initialized) { state[0] = state[1] = state[2] = state[3] = 0; return; }
    state[0] = digitalRead(PIN_TRACK_L1) == LOW;
    state[1] = digitalRead(PIN_TRACK_L2) == LOW;
    state[2] = digitalRead(PIN_TRACK_R1) == LOW;
    state[3] = digitalRead(PIN_TRACK_R2) == LOW;
}

void sensor_read_avoid(int state[2]) {
    if (!state) return;
    if (!g_hal_initialized) { state[0] = state[1] = 0; return; }
    state[0] = digitalRead(PIN_AVOID_LEFT) == LOW;
    state[1] = digitalRead(PIN_AVOID_RIGHT) == LOW;
}

int button_read(void) { return g_hal_initialized ? (digitalRead(PIN_BUTTON) == LOW) : 0; }
