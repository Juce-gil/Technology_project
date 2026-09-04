import unittest
from smartcar.config import LineConfig, MotorConfig
from smartcar.line_source import IRLineSource, LineController, LineReading


class FakeHAL:
    def __init__(self, values): self.values = values
    def read_tracking(self): return self.values


class LineTests(unittest.TestCase):
    def test_ir_center(self):
        reading = IRLineSource(FakeHAL([0, 1, 1, 0])).read()
        self.assertTrue(reading.detected); self.assertAlmostEqual(reading.error, 0.0)

    def test_ir_left(self):
        reading = IRLineSource(FakeHAL([1, 0, 0, 0])).read()
        self.assertEqual(reading.error, -1.0)

    def test_lost_line_eventually_stops(self):
        cfg = LineConfig(lost_stop_seconds=2.0)
        controller = LineController(cfg, MotorConfig())
        controller.command(LineReading(-0.5, 1, True, 1), now=1.0)
        _, _, stop = controller.command(LineReading(0, 0, False, 4), now=4.0)
        self.assertTrue(stop)

    def test_lost_line_holds_then_searches(self):
        cfg = LineConfig(lost_search_seconds=1.0, lost_stop_seconds=3.0, kp=0, kd=0)
        controller = LineController(cfg, MotorConfig(base_speed=100, search_speed=50))
        controller.command(LineReading(-0.5, 1, True, 0), now=0)
        self.assertEqual(controller.command(LineReading(0, 0, False, .5), now=.5), (50, 50, False))
        self.assertEqual(controller.command(LineReading(0, 0, False, 2), now=2), (-50, 50, False))


if __name__ == "__main__": unittest.main()
