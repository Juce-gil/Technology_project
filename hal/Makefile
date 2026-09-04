CC ?= gcc
CFLAGS ?= -O2 -Wall -Wextra -fPIC
LDFLAGS ?= -shared
LIBS = -lwiringPi -lpthread -lrt
SOURCES = hal_core.c hal_motor.c hal_servo.c hal_sensor.c hal_led.c
TARGET = libsmartcar.so

.PHONY: all install clean
all: $(TARGET)

$(TARGET): $(SOURCES) hal.h hal_internal.h
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $(SOURCES) $(LIBS)

install: $(TARGET)
	cp $(TARGET) ../smartcar/

clean:
	rm -f $(TARGET)
