#!/usr/bin/env python3
"""Source-only Wingless Go wire regression. Never execute frozen MiniGrid worlds."""
import json
import os
import unittest
from unittest.mock import Mock

from k4u_native_minigrid import WingBridge, wingless_wire_grid


def sample(blocked=True):
    return {"X": 3, "Y": 4, "GoalX": 6, "GoalY": 7,
            "Direction": 0, "FrontBlocked": blocked}


class WinglessWireTests(unittest.TestCase):
    def test_exact_native_wire_keys_preserve_all_public_values(self):
        for blocked in (True, False):
            record = sample(blocked)
            value = wingless_wire_grid(record)
            self.assertEqual(value, {"x": 3, "y": 4, "goal_x": 6,
                                     "goal_y": 7, "direction": 0,
                                     "front_blocked": blocked})
            self.assertEqual(record["FrontBlocked"], blocked)
            self.assertEqual(len(value), 6)
            self.assertNotIn("GoalX", value)
            self.assertNotIn("FrontBlocked", value)
            self.assertEqual(json.loads(json.dumps(value)), value)

    def test_both_real_transport_calls_use_native_schema(self):
        bridge = object.__new__(WingBridge)
        bridge.request = Mock(return_value={"action": 2})
        self.assertEqual(bridge.choose(sample()), 2)
        bridge.request.assert_called_once_with(
            "choose", before=wingless_wire_grid(sample()))
        bridge.request.reset_mock()
        bridge.learn(sample(), 2, sample(False), 0, False)
        bridge.request.assert_called_once_with(
            "learn", before=wingless_wire_grid(sample()), action=2,
            after=wingless_wire_grid(sample(False)), reward=0.0,
            terminal=False)

    def test_missing_extra_and_invalid_values_fail_closed_before_transport(self):
        cases = []
        for key in sample():
            item = sample()
            del item[key]
            cases.append(item)
        cases.extend([
            {**sample(), "unknown": "hidden"},
            {**sample(), "FrontBlocked": 1},
            {**sample(), "GoalX": True},
            {**sample(), "X": 3.0},
            {**sample(), "GoalX": -1},
            {**sample(), "GoalY": 65},
            {**sample(), "Direction": 4},
        ])
        for value in cases:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    wingless_wire_grid(value)
                bridge = object.__new__(WingBridge)
                bridge.request = Mock()
                with self.assertRaises(ValueError):
                    bridge.choose(value)
                bridge.request.assert_not_called()
                with self.assertRaises(ValueError):
                    bridge.learn(sample(), 2, value, 0, False)
                bridge.request.assert_not_called()

    def test_public_bounds_and_false_blocked_are_valid(self):
        state = {"X": 0, "Y": 64, "GoalX": 64, "GoalY": 0,
                 "Direction": 3, "FrontBlocked": False}
        native = wingless_wire_grid(state)
        self.assertEqual(native["goal_x"], 64)
        self.assertIs(native["front_blocked"], False)

    def test_real_original_go_r2_receives_blocked_outcomes(self):
        binary = os.environ.get("WINGLESS_R2_NATIVE_BRIDGE")
        if not binary:
            self.skipTest("requires explicitly qualified original Go bridge binary")
        bridge = WingBridge(binary)
        try:
            blocked = sample(True)
            open_front = sample(False)
            for _ in range(8):
                bridge.learn(blocked, 2, blocked, 0.0, True)
            snap = json.loads(bridge.snapshot())
            self.assertEqual(snap["data"]["blocked_attempts"], 8)
            self.assertEqual(snap["data"]["blocked_progress"], 0)
            bridge.learn(open_front, 2, open_front, 0.0, True)
            after = json.loads(bridge.snapshot())
            self.assertEqual(after["data"]["blocked_attempts"], 8)
            self.assertNotEqual(after["data"]["original_r1_checkpoint"],
                                snap["data"]["original_r1_checkpoint"])
            self.assertIn(bridge.choose(blocked), (0, 1))
        finally:
            bridge.close()

    def test_original_go_native_goals_actually_change_learned_state(self):
        paths = [os.environ.get("WINGLESS_R1_NATIVE_BRIDGE"),
                 os.environ.get("WINGLESS_R2_NATIVE_BRIDGE")]
        if not all(paths):
            self.skipTest("requires both explicitly qualified original Go binaries")
        for binary in paths:
            with self.subTest(binary=binary):
                first, second = WingBridge(binary), WingBridge(binary)
                try:
                    left, right = sample(False), {**sample(False),
                                                   "GoalX": 9, "GoalY": 10}
                    first.learn(left, 0, left, 1.0, True)
                    second.learn(right, 0, right, 1.0, True)
                    self.assertNotEqual(first.snapshot(), second.snapshot())
                finally:
                    first.close()
                    second.close()


if __name__ == "__main__":
    unittest.main()
