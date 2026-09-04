import unittest
from smartcar.config import CarConfig


class ConfigTests(unittest.TestCase):
    def test_defaults_are_valid(self): self.assertIsInstance(CarConfig().validate(), CarConfig)

    def test_bad_distance_order_is_rejected(self):
        config = CarConfig(); config.safety.blocked_cm = config.safety.warning_cm
        with self.assertRaises(ValueError): config.validate()

    def test_bad_line_timing_is_rejected(self):
        config = CarConfig(); config.line.lost_search_seconds = config.line.lost_stop_seconds
        with self.assertRaises(ValueError): config.validate()


if __name__ == "__main__": unittest.main()
