"""F41 structural smoke: fake action physics NEVER qualifies original DEV science."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

SOURCE = Path(__file__).with_name("f41_original_mountaincar_dev.py")
spec = importlib.util.spec_from_file_location("f41_original_mountaincar_dev", SOURCE)
f41 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f41)


class FakeActionSpace:
    n = 3


class FakeCar:
    action_space = FakeActionSpace()

    def __init__(self):
        self.closed = False
        self.steps = 0

    def reset(self, seed):
        self.steps = 0
        self.state = [-0.5 + .001 * (seed % 10), 0.0]
        return self.state[:], {"not_a_training_oracle": True}

    def step(self, action):
        if self.steps >= 9:
            raise ValueError("FAKE_STEPPED_AFTER_DONE")
        self.steps += 1
        p, v = self.state
        v = .9*v + .001 * (action - 1)
        p += v
        self.state = [p, v]
        return self.state[:], -1.0, self.steps == 9, False, {"ignored": 1}

    def close(self):
        self.closed = True


class FakeGym:
    def make(self, identifier, render_mode):
        if identifier != "MountainCar-v0" or render_mode is not None:
            raise AssertionError("F41_NOT_ORIGINAL_PUBLIC_INTERFACE")
        return FakeCar()


class F41StructuralTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gym = FakeGym()
        cls.samples, cls.coverage = f41.training(cls.gym)
        cls.models = f41.fit_models(cls.samples)

    def test_same_training_transcript_and_all_three_actions(self):
        self.assertEqual(96*9, len(self.samples))
        self.assertEqual(len(self.samples), sum(self.coverage))
        self.assertTrue(all(v > 0 for v in self.coverage))
        self.assertEqual((6, 2), np.asarray(self.models["global-linear-mpc"]["global"]).shape)
        self.assertEqual((3, 6, 2), np.asarray(self.models["regime-residual-mpc"]["residual"]).shape)
        self.assertEqual((3, 6), np.asarray(self.models["trained-fitted-q"]).shape)
        self.assertEqual((3, 3), np.asarray(self.models["trained-behavior-cloning"]).shape)
        self.assertIs(type(self.models["regime-residual-mpc"]["gate"]), bool)
        self.assertEqual(self.models, json.loads(f41.canonical(self.models)))
        self.assertEqual(f41.digest(self.samples), f41.digest(f41.training(self.gym)[0]))

    def test_fake_fixture_cannot_issue_original_classification(self):
        report = f41.assess(self.gym, self.models, f41.digest(self.samples), f41.SOURCE)
        self.assertEqual("F41_ORIGINAL_RUNTIME_UNVERIFIED", report["classification"])
        self.assertFalse(report["scientific_accepted"])
        self.assertFalse(report["first_use_consumed"])
        self.assertFalse(report["owner_eligible"])
        self.assertTrue(report["development_only"])
        self.assertEqual(set(f41.KINDS), set(report["arms"]))
        self.assertEqual(8, len(report["arms"]["regime-residual-mpc"]["worlds"]))
        self.assertTrue(all(world["cold_matches"] for arm in report["arms"].values()
                            for world in arm["worlds"]))
        self.assertEqual(report["report_sha256"], f41.digest({k:v for k,v in report.items()
                                                              if k != "report_sha256"}))
        self.assertIn(report["strongest_conventional"],
                      ("velocity-rule", "trained-behavior-cloning",
                       "trained-fitted-q", "global-linear-mpc"))
        self.assertIs(type(report["frozen_thresholds_met"]), bool)

    def test_wrong_action_and_identity_are_true_negative_controls(self):
        state = [-.45, .004]
        scores = {kind: f41.choose(state, kind, self.models) for kind in f41.KINDS}
        self.assertTrue(all(v in (0, 1, 2) for v in scores.values()))
        self.assertNotEqual(self.models["global-linear-mpc"]["global"],
                            self.models["wrong-action-mpc"]["global"])
        self.assertEqual("identity", self.models["no-dynamics-mpc"])
        with self.assertRaisesRegex(ValueError, "F41_INVALID_DYNAMICS_ACTIONS"):
            f41.dyn_design([[0.0, 0.0]], [3])
        with self.assertRaisesRegex(ValueError, "F41_UNKNOWN_POLICY"):
            f41.choose(state, "not-an-arm", self.models)

    def test_no_firstuse_nonfinite_or_bad_source(self):
        for seed in f41.FIRST_USE_FORBIDDEN:
            with self.assertRaisesRegex(ValueError, "FIRST_USE"):
                f41.episode(self.gym, seed, "velocity-rule")
        with self.assertRaisesRegex(ValueError, "BAD_PUBLIC_OBSERVATION"):
            f41.public_obs([0.0, float("nan")])
        with self.assertRaisesRegex(ValueError, "BAD_PUBLIC_OBSERVATION_SHAPE"):
            f41.public_obs([0.0, 0.0, 0.0])
        with self.assertRaisesRegex(ValueError, "NO_REAL_TRAINING"):
            f41.fit_models([])
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises((ValueError, RuntimeError, ModuleNotFoundError, FileNotFoundError)):
                f41.original_gym(Path(folder))
            with self.assertRaises(ValueError):
                f41.main([folder, str(Path(folder) / "result.json")])
        self.assertNotIn("gymnasium", sys.modules)


if __name__ == "__main__":
    unittest.main(verbosity=2)
