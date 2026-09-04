import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from control_panel import CONTROL_PORT, CarProcess


class ControlPanelTests(unittest.TestCase):
    def test_gpio_command_is_bounded_to_project(self):
        command = CarProcess.command("ir", "gpio")
        self.assertEqual(command[0], sys.executable)
        self.assertIn("--line-source", command)
        self.assertIn("--tcp-host", command)
        self.assertEqual(command[-2:], ["--tcp-port", str(CONTROL_PORT)])

    def test_arduino_port_is_an_argument_not_a_shell_command(self):
        port = "/dev/ttyACM0;touch /tmp/unsafe"
        command = CarProcess.command("ir", "arduino", port)
        self.assertEqual(command[-2:], ["--arduino-port", port])

    def test_invalid_choices_are_rejected(self):
        with self.assertRaises(ValueError): CarProcess.command("bad", "gpio")
        with self.assertRaises(ValueError): CarProcess.command("ir", "bad")


if __name__ == "__main__": unittest.main()
