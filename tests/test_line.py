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
        cfg = LineConfig(lost_search_seconds=1.0, lost_stop_seconds=3.0, kp=0, kd=0,
                         max_speed_change_per_second=1000)
        controller = LineController(cfg, MotorConfig(base_speed=100, search_speed=50))
        controller.command(LineReading(-0.5, 1, True, 0), now=0)
        self.assertEqual(controller.command(LineReading(0, 0, False, .5), now=.5), (50, 50, False))
        self.assertEqual(controller.command(LineReading(0, 0, False, 2), now=2), (-50, 50, False))

    def test_error_and_derivative_are_filtered(self):
        cfg = LineConfig(kp=100, kd=10, error_filter_alpha=0.5,
                         derivative_filter_alpha=0.5, max_speed_change_per_second=10000)
        controller = LineController(cfg, MotorConfig(base_speed=100, max_speed=200))
        self.assertEqual(controller.command(LineReading(0, 1, True, 0), now=0), (100, 100, False))
        left, right, _ = controller.command(LineReading(1, 1, True, .1), now=.1)
        self.assertEqual((left, right), (200, 0))
        self.assertAlmostEqual(controller.filtered_error, .5)
        self.assertAlmostEqual(controller.filtered_derivative, 5.0)

    def test_speed_change_is_limited_but_stop_is_immediate(self):
        cfg = LineConfig(kp=0, kd=0, lost_stop_seconds=1,
                         max_speed_change_per_second=100)
        controller = LineController(cfg, MotorConfig(base_speed=100))
        self.assertEqual(controller.command(LineReading(0, 1, True, 0), now=0), (10, 10, False))
        self.assertEqual(controller.command(LineReading(0, 1, True, .1), now=.1), (20, 20, False))
        self.assertEqual(controller.command(LineReading(0, 0, False, 2), now=2), (0, 0, True))

    def test_reset_clears_stale_motion_and_direction(self):
        controller = LineController(LineConfig(), MotorConfig())
        controller.command(LineReading(-1, 1, True, 0), now=0)
        controller.reset_motion()
        self.assertEqual(controller.last_output, (0, 0))
        self.assertIsNone(controller.last_seen)


if __name__ == "__main__": unittest.main()
