import struct
import unittest

from smartcar.protocol import CMD_BRAKE, CMD_SET_MOTOR, FrameParser, encode_frame, encode_motor


class ProtocolTests(unittest.TestCase):
    def test_round_trip_fragmented(self):
        encoded = encode_motor(7, -120, 200)
        parser = FrameParser()
        self.assertEqual(parser.feed(encoded[:3]), [])
        frames = parser.feed(encoded[3:])
        self.assertEqual(frames, [(CMD_SET_MOTOR, 7, struct.pack("<hh", -120, 200))])

    def test_bad_crc_is_rejected_and_parser_recovers(self):
        bad = bytearray(encode_frame(CMD_BRAKE, 1)); bad[-1] ^= 0xFF
        valid = encode_frame(CMD_BRAKE, 2)
        self.assertEqual(FrameParser().feed(bytes(bad) + valid), [(CMD_BRAKE, 2, b"")])

    def test_payload_limit(self):
        with self.assertRaises(ValueError): encode_frame(1, 1, b"x" * 33)


if __name__ == "__main__": unittest.main()
