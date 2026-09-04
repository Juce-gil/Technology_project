import unittest
from smartcar.config import MotorConfig
from smartcar.target_tracker import TargetTracker
from smartcar.vision import Detection


class TargetTrackerTests(unittest.TestCase):
    def test_centered_target_drives_symmetrically(self):
        tracker = TargetTracker(MotorConfig(), kd=0)
        left, right, stop = tracker.command(Detection("red", .9, (120, 50, 200, 150)), (240, 320, 3), now=1)
        self.assertFalse(stop); self.assertEqual(left, right)

    def test_missing_target_stops(self):
        self.assertEqual(TargetTracker(MotorConfig()).command(None, (240, 320, 3)), (0, 0, True))


if __name__ == "__main__": unittest.main()
