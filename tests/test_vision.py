import unittest
try:
    import numpy as np
except ImportError:
    np = None
from smartcar.vision import MobileNetSSDPersonDecoder


@unittest.skipIf(np is None, "numpy not installed")
class VisionTests(unittest.TestCase):
    def test_person_decoder_filters_class_and_confidence(self):
        output = np.array([[[[0, 15, .9, .1, .2, .8, .9],
                              [0, 7, .99, 0, 0, 1, 1],
                              [0, 15, .2, 0, 0, 1, 1]]]], dtype=np.float32)
        result = MobileNetSSDPersonDecoder(.55)(output, (100, 200, 3))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].class_name, "person")
        self.assertEqual(result[0].bbox, (20, 20, 160, 90))


if __name__ == "__main__": unittest.main()
