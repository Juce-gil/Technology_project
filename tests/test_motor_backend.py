import unittest
from smartcar.motor_backend import ArduinoMotorBackend
from smartcar.protocol import CMD_BRAKE, FrameParser


class FakeSerial:
    def __init__(self, *args, **kwargs): self.writes = []; self.closed = False
    def write(self, data): self.writes.append(data); return len(data)
    def close(self): self.closed = True


class ShortSerial(FakeSerial):
    def write(self, data): return max(0, len(data) - 1)


class MotorBackendTests(unittest.TestCase):
    def test_close_sends_brake_and_closes(self):
        backend = ArduinoMotorBackend("fake", serial_factory=FakeSerial)
        serial = backend.serial; backend.close()
        commands = []
        parser = FrameParser()
        for packet in serial.writes: commands.extend(frame[0] for frame in parser.feed(packet))
        self.assertIn(CMD_BRAKE, commands); self.assertTrue(serial.closed)

    def test_short_write_is_an_error(self):
        backend = ArduinoMotorBackend("fake", serial_factory=ShortSerial)
        with self.assertRaises(IOError): backend.run(1, 1)
        backend.close()


if __name__ == "__main__": unittest.main()
