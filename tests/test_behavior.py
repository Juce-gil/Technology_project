import unittest
from smartcar.behavior import BehaviorManager, RunState
from smartcar.config import CarConfig
from smartcar.line_source import LineReading
from smartcar.obstacle import ObstacleLevel, ObstacleReading


class FakeMotor:
    def __init__(self): self.commands = []
    def run(self, left, right): self.commands.append((left, right))
    def brake(self): self.commands.append((0, 0))
    def close(self): pass


class FakeHAL:
    def __init__(self): self.button = False
    def button_read(self): return self.button


class FakeLine:
    def read(self): return LineReading(0, 1, True, 0)
    def is_healthy(self): return True


class FakeController:
    def command(self, reading, now): return 100, 100, False


class FakeObstacles:
    def __init__(self): self.level = ObstacleLevel.CLEAR
    def read(self): return ObstacleReading(self.level, 100, (False, False), 0)


class BehaviorTests(unittest.TestCase):
    def setUp(self):
        self.config = CarConfig(); self.config.safety.clear_confirm_seconds = 0.5
        self.config.safety.button_debounce_seconds = 0.05
        self.motor, self.hal, self.obstacles = FakeMotor(), FakeHAL(), FakeObstacles()
        self.manager = BehaviorManager(self.motor, FakeLine(), FakeController(), self.obstacles,
                                       self.hal, self.config)

    def test_obstacle_requires_clear_and_button(self):
        self.obstacles.level = ObstacleLevel.BLOCKED
        self.assertEqual(self.manager.update(0), RunState.PAUSED)
        self.obstacles.level = ObstacleLevel.CLEAR
        self.assertEqual(self.manager.update(1), RunState.WAIT_CLEAR)
        self.hal.button = True
        self.assertEqual(self.manager.update(1.6), RunState.WAIT_CLEAR)
        self.assertEqual(self.manager.update(1.7), RunState.RUNNING)

    def test_sensor_error_brakes(self):
        self.obstacles.level = ObstacleLevel.SENSOR_ERROR
        self.assertEqual(self.manager.update(0), RunState.PAUSED)
        self.assertEqual(self.motor.commands[-1], (0, 0))

    def test_fault_is_latched(self):
        class StopController:
            def command(self, reading, now): return 0, 0, True
        self.manager.controller = StopController()
        self.assertEqual(self.manager.update(0), RunState.FAULT)
        before = len(self.motor.commands)
        self.assertEqual(self.manager.update(1), RunState.FAULT)
        self.assertEqual(self.motor.commands[-1], (0, 0))
        self.assertEqual(len(self.motor.commands), before + 1)

    def test_button_held_during_obstacle_does_not_resume(self):
        self.hal.button = True; self.obstacles.level = ObstacleLevel.BLOCKED
        self.manager.update(0); self.manager.update(0.1)
        self.obstacles.level = ObstacleLevel.CLEAR
        self.manager.update(1); self.manager.update(2)
        self.assertEqual(self.manager.state, RunState.WAIT_CLEAR)
        self.hal.button = False
        self.manager.update(2.1); self.manager.update(2.2)
        self.hal.button = True
        self.manager.update(2.3); self.manager.update(2.4)
        self.assertEqual(self.manager.state, RunState.RUNNING)

    def test_remote_resume_uses_same_clear_safety_gate(self):
        self.obstacles.level = ObstacleLevel.BLOCKED
        self.manager.update(0)
        self.assertFalse(self.manager.request_resume())
        self.obstacles.level = ObstacleLevel.CLEAR
        self.manager.update(1)
        self.assertTrue(self.manager.request_resume())
        self.assertEqual(self.manager.update(1.2), RunState.WAIT_CLEAR)
        self.assertEqual(self.manager.update(1.6), RunState.RUNNING)

    def test_remote_resume_is_cancelled_if_obstacle_returns(self):
        self.obstacles.level = ObstacleLevel.BLOCKED; self.manager.update(0)
        self.obstacles.level = ObstacleLevel.CLEAR; self.manager.update(1)
        self.assertTrue(self.manager.request_resume())
        self.obstacles.level = ObstacleLevel.BLOCKED; self.manager.update(1.2)
        self.obstacles.level = ObstacleLevel.CLEAR; self.manager.update(2)
        self.assertEqual(self.manager.update(3), RunState.WAIT_CLEAR)


if __name__ == "__main__": unittest.main()
