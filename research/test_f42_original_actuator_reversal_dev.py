"""F42 structural/negative tests. Fake world cannot create original DEV evidence."""
import inspect
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

import f41_original_mountaincar_dev as f41
import f42_original_actuator_reversal_dev as f42


class FakeActionSpace:
    n = 3


class FakeGymCar:
    action_space = FakeActionSpace()

    def __init__(self):
        self.step_count = 0
        self.closed = False

    def reset(self, seed):
        self.step_count = 0
        self.state = [-0.5 + 0.001 * (seed % 13), 0.0]
        return self.state[:], {"ignore": True}

    def step(self, action):
        if self.step_count >= 12:
            raise AssertionError("F42_FAKE_STEPPED_AFTER_TERMINATION")
        self.step_count += 1
        position, velocity = self.state
        velocity = 0.92 * velocity + 0.002 * (action - 1)
        position += velocity
        self.state = [position, velocity]
        return self.state[:], -1.0, self.step_count == 12, False, {"hidden": 77}

    def close(self):
        self.closed = True


class FakeGym:
    def make(self, identifier, render_mode):
        if identifier != "MountainCar-v0" or render_mode is not None:
            raise AssertionError("F42_NO_ORIGINAL_WORLD_IMPORT")
        return FakeGymCar()


class F42Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gym = FakeGym()
        cls.fake_train, cls.action_counts = f41.training(cls.gym)
        cls.dynamics = f41.fit_dynamics(cls.fake_train)

    def test_predeclared_real_trained_source_cannot_be_faked(self):
        self.assertEqual(96 * 12, len(self.fake_train))
        self.assertEqual(96 * 12, sum(self.action_counts))
        self.assertTrue(all(x > 0 for x in self.action_counts))
        with self.assertRaisesRegex(ValueError, "F41_TRAIN_ONLY_TRANSCRIPT_DRIFT"):
            f42.fitted_training(self.gym)
        self.assertEqual((6, 2), np.asarray(self.dynamics["global"]).shape)
        self.assertEqual(f42.TRAIN_HASH,
                         "174dee337d801c1046bd0d26b0ff0c50f89adf36cce4489c43100b4ea0dd1f34")
        self.assertEqual(set(f42.FAULT_WORLDS), {1103, 1117, 1129, 1151})
        self.assertEqual(f42.RETAIN_WORLDS, (1201, 1213))

    def test_actuator_fault_is_hidden_and_boundary_limited(self):
        windows = f42.FAULT_WORLDS[1103]
        for t in (0, 39, 96, 131, 170, 199):
            self.assertEqual(0, f42.effective_action(0, t, windows))
        for t in (40, 95, 132, 169):
            self.assertEqual(2, f42.effective_action(0, t, windows))
            self.assertEqual(0, f42.effective_action(2, t, windows))
            self.assertEqual(1, f42.effective_action(1, t, windows))
        self.assertEqual(["self", "state", "step"],
                         list(inspect.signature(f42.Policy.decide).parameters))
        self.assertEqual(["self", "previous", "commanded", "next_state"],
                         list(inspect.signature(f42.Policy.observe).parameters))
        with self.assertRaisesRegex(ValueError, "INVALID_COMMANDED_ACTION"):
            f42.effective_action(3, 40, windows)
        with self.assertRaisesRegex(ValueError, "INVALID_COMMANDED_ACTION"):
            f42.effective_action(True, 40, windows)

    def test_action_consequence_contradiction_and_wrong_credit(self):
        state = [-0.48, 0.0]
        requested = 0
        reversed_next = f41.predict([state], [2], self.dynamics)[0].tolist()
        evidence = f42.reversal_evidence(state, requested, reversed_next, self.dynamics)
        self.assertGreater(evidence, 0.9)
        self.assertEqual(0, f42.reversal_evidence(state, 1, reversed_next, self.dynamics))
        correct = f42.Policy("contradiction-probe", self.dynamics)
        wrong = f42.Policy("wrong-credit-probe", self.dynamics)
        for _ in range(2):
            correct.observe(state, requested, reversed_next)
            wrong.observe(state, requested, reversed_next)
        self.assertTrue(correct.as_reverse)
        self.assertEqual(1, correct.flips)
        self.assertFalse(wrong.as_reverse)
        self.assertEqual(0, wrong.flips)
        for kind in f42.KINDS:
            policy = f42.Policy(kind, self.dynamics)
            command = policy.decide(state, 0)
            self.assertIn(command, (0, 1, 2))
            self.assertLessEqual(policy.probes, 16)

    def test_fake_score_is_original_unverified_and_cold_matches(self):
        report = f42.assess(self.gym, self.dynamics, "FAKE_TRAIN", f42.SOURCE)
        self.assertEqual("F42_ORIGINAL_RUNTIME_UNVERIFIED", report["classification"])
        self.assertEqual(8, len(report["arms"]))
        self.assertEqual(4, len(report["faulted_eval_seeds"]))
        self.assertEqual(2, len(report["no_fault_eval_seeds"]))
        self.assertTrue(report["original_physics_with_external_actuator_fault"])
        self.assertFalse(report["unmodified_original_gymnasium_task"])
        self.assertFalse(report["scientific_accepted"])
        self.assertFalse(report["first_use_consumed"])
        self.assertFalse(report["owner_eligible"])
        self.assertEqual(set(f42.CONVENTIONAL).intersection(report["arms"]),
                         set(f42.CONVENTIONAL))
        self.assertTrue(all(len(arm["worlds"]) == 6 for arm in report["arms"].values()))
        self.assertTrue(all(w["cold_matches"] for arm in report["arms"].values()
                            for w in arm["worlds"]))
        self.assertTrue(all(w["probes"] <= 16 for arm in report["arms"].values()
                            for w in arm["worlds"]))
        self.assertEqual(report["report_sha256"],
                         f42.digest({k:v for k,v in report.items()
                                     if k != "report_sha256"}))
        self.assertIs(type(report["frozen_thresholds_met"]), bool)

    def test_bad_original_and_first_use_fail_closed(self):
        for seed in f42.FORBIDDEN:
            with self.assertRaisesRegex(ValueError, "FIRST_USE"):
                f42.episode(self.gym, seed, "fixed-mpc", self.dynamics)
        with self.assertRaisesRegex(ValueError, "UNAUTHORIZED_DEV_WORLD"):
            f42.episode(self.gym, 500, "fixed-mpc", self.dynamics)
        with self.assertRaisesRegex(ValueError, "UNKNOWN_POLICY"):
            f42.Policy("not-an-arm", self.dynamics)
        with self.assertRaisesRegex(ValueError, "BAD_PUBLIC_OBSERVATION"):
            f41.public_obs([float("nan"), 0.0])
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises((ValueError, RuntimeError, ModuleNotFoundError)):
                f42.original_gym(Path(root))
            with self.assertRaisesRegex(ValueError, "OUTPUT_INSIDE_PINNED"):
                f42.main([root, str(Path(root) / "dev.json")])
        self.assertNotIn("gymnasium", sys.modules)


if __name__ == "__main__":
    unittest.main(verbosity=2)
