import unittest
from smartcar.config import CarConfig
from smartcar.remote import CommandServer


class FakeManager:
    def __init__(self): self.paused = False
    def pause(self, reason): self.paused = reason
    def status(self): return {"state": "running"}
    def request_resume(self): return True


class FakeHAL:
    def __init__(self): self.led = None
    def led_set(self, *values): self.led = values


class RemoteTests(unittest.TestCase):
    def setUp(self):
        self.manager, self.hal, self.client = FakeManager(), FakeHAL(), object()
        self.server = CommandServer(self.manager, self.hal, CarConfig(), "secret")

    def test_authentication_and_stop(self):
        self.assertIn("unauthorized", self.server.handle(self.client, "$4WD,STOP#"))
        self.assertIn("authenticated", self.server.handle(self.client, "$4WD,AUTH,secret#"))
        self.assertIn("stopped", self.server.handle(self.client, "$4WD,STOP#"))
        self.assertEqual(self.manager.paused, "tcp")

    def test_speed_is_clamped(self):
        self.server.authenticated.add(self.client)
        self.assertIn("speed=200", self.server.handle(self.client, "$4WD,SPEED,999#"))

    def test_authenticated_resume_only_queues_request(self):
        self.server.authenticated.add(self.client)
        self.assertIn("resume-requested", self.server.handle(self.client, "$4WD,RESUME#"))


if __name__ == "__main__": unittest.main()
