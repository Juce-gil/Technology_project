import struct

SOF = 0xAA
VERSION = 1
CMD_SET_MOTOR = 0x01
CMD_BRAKE = 0x02
CMD_HEARTBEAT = 0x03
CMD_GET_STATUS = 0x04
CMD_STATUS = 0x81
MAX_PAYLOAD = 32


def crc8(data):
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def encode_frame(command, sequence, payload=b""):
    if len(payload) > MAX_PAYLOAD:
        raise ValueError("payload too long")
    body = bytes((VERSION, command & 0xFF, sequence & 0xFF, len(payload))) + payload
    return bytes((SOF,)) + body + bytes((crc8(body),))


def encode_motor(sequence, left, right):
    return encode_frame(CMD_SET_MOTOR, sequence, struct.pack("<hh", left, right))


class FrameParser:
    def __init__(self): self.buffer = bytearray()

    def feed(self, data):
        self.buffer.extend(data); frames = []
        while True:
            while self.buffer and self.buffer[0] != SOF: del self.buffer[0]
            if len(self.buffer) < 6: break
            length = self.buffer[4]
            if length > MAX_PAYLOAD:
                del self.buffer[0]; continue
            total = 6 + length
            if len(self.buffer) < total: break
            raw = bytes(self.buffer[:total]); del self.buffer[:total]
            body = raw[1:-1]
            if crc8(body) != raw[-1] or body[0] != VERSION: continue
            frames.append((body[1], body[2], body[4:]))
        return frames
