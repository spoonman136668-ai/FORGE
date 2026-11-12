"""F43: interface, training-only calibration, negative and cold replay checks.

Fake physics is intentionally NOT an original-Gymnasium scientific result.
"""
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

import f41_original_mountaincar_dev as f41
import f42_original_actuator_reversal_dev as f42
import f43_train_calibrated_contradiction_dev as f43


class FakeActionSpace:
    n = 3


class FakeWorld:
    action_space = FakeActionSpace()

    def reset(self, seed):
        self.steps = 0
        self.state = [-0.55 + .001 * (seed % 29), 0.0]
        return self.state[:], {"privileged": 99}

    def step(self, action):
        if self.steps >= 10:
            raise AssertionError("F43_STEPPED_AFTER_TERMINATION")
        self.steps += 1
        p, v = self.state
        v = .90 * v + .0008 * (action - 1)
        p += v
        self.state = [p, v]
        return self.state[:], -1.0, self.steps == 10, False, {"unread": 1}

    def close(self):
        pass


class FakeGym:
    def make(self, identifier, render_mode):
        if identifier != "MountainCar-v0" or render_mode is not None:
            raise AssertionError("F43_NOT_PUBLIC_GYM_INTERFACE")
        return FakeWorld()


class F43Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fake = FakeGym()
        cls.samples, cls.counts = f41.training(cls.fake)
        cls.model = f41.fit_dynamics(cls.samples)

    def test_frozen_original_training_hash_refuses_fake(self):
        self.assertEqual(960, len(self.samples))
        self.assertNotEqual(f43.TRAIN_SHA256, f43.digest(self.samples))
        with self.assertRaisesRegex(ValueError, "F41_TRAINING_ONLY_TRANSCRIPT_DRIFT"):
            f43.source_fit(self.fake)
        self.assertEqual((6, 2), np.asarray(self.model["global"]).shape)
        self.assertEqual(set(f43.FAULT_WORLDS), {1409, 1423, 1439, 1451})
        self.assertEqual(f43.NO_FAULT_WORLDS, (1471, 1483))
        self.assertTrue(set(f43.FAULT_WORLDS).isdisjoint(f42.FAULT_WORLDS))

    def test_training_only_calibration_has_fixed_formula_and_minimum(self):
        self.assertAlmostEqual(0.128, f43.threshold_from_training_magnitudes([.32]*1000))
        self.assertAlmostEqual(.02, f43.threshold_from_training_magnitudes([.001]*1000))
        self.assertAlmostEqual(.75, f43.threshold_from_training_magnitudes([10.0]*1000))
        for values in ([.32]*999, [float("nan")]*1000, [0.0]*1000):
            with self.assertRaisesRegex(ValueError, "INVALID_TRAIN_ONLY_CALIBRATION"):
                f43.threshold_from_training_magnitudes(values)

    def test_mechanism_credits_actual_observation_not_hidden_action(self):
        # Model with a 0.003 predicted velocity difference between commands 0 and 2.
        w = np.zeros((6,2),dtype=float)
        w[2,1] = 0.0
        w[4,1] = 0.003
        dynamics={"global":w.tolist(),"residual":np.zeros((3,6,2)).tolist()}
        state=[-.5,0.0]
        reversed_next = f41.predict([state],[2],dynamics)[0].tolist()
        correct=f43.CalibratedPolicy("calibrated-contradiction",dynamics,.1)
        wrong=f43.CalibratedPolicy("wrong-credit-no-probe",dynamics,.1)
        passive=f43.CalibratedPolicy("no-adapt-no-probe",dynamics,.1)
        for _ in range(2):
            correct.observe(state,0,reversed_next)
            wrong.observe(state,0,reversed_next)
            passive.observe(state,0,reversed_next)
        self.assertTrue(correct.as_reverse)
        self.assertEqual(1,correct.flips)
        self.assertFalse(wrong.as_reverse)
        self.assertEqual(0,wrong.flips)
        self.assertFalse(passive.as_reverse)
        self.assertEqual(0,passive.flips)
        for step in range(17):
            correct.decide(state,step)
            wrong.decide(state,step)
            passive.decide(state,step)
        self.assertEqual((correct.probes,wrong.probes,passive.probes),(0,0,0))

    def test_strong_baselines_and_real_fault_windows(self):
        self.assertEqual(9,len(f43.KINDS))
        self.assertEqual(6,len(f43.CONVENTIONAL))
        self.assertIn("rolling8-probe",f43.CONVENTIONAL)
        self.assertIn("rolling8-no-probe",f43.CONVENTIONAL)
        for seed, windows in f43.FAULT_WORLDS.items():
            self.assertNotIn(seed,f43.FIRST_USE_FORBIDDEN)
            for start,stop in windows:
                self.assertEqual(2,f42.effective_action(0,start,windows))
                self.assertEqual(0,f42.effective_action(0,stop,windows))
        for kind in f43.KINDS:
            policy=f43.policy_for(kind,self.model,.05)
            self.assertIsInstance(policy,f42.Policy)
            self.assertIn(policy.decide([-.45,0.003],0),(0,1,2))
            self.assertLessEqual(policy.probes,16)
        with self.assertRaisesRegex(ValueError,"UNREGISTERED_POLICY"):
            f43.policy_for("not-registered",self.model,.05)

    def test_fake_assessment_cannot_issue_original_science_label(self):
        fit={
            "dynamics":self.model,
            "tau":.10,
            "training_sha256":"FAKE_SOURCE",
            "training_episodes":96,
            "training_transitions":len(self.samples),
            "training_action_counts":self.counts,
            "calibration_n":1000,
            "calibration_median_abs_l":.25,
            "source_fit_sha256":f43.digest(self.model),
        }
        report=f43.assess(self.fake,fit,f43.SOURCE)
        self.assertEqual("F43_ORIGINAL_RUNTIME_UNVERIFIED",report["classification"])
        self.assertFalse(report["scientific_accepted"])
        self.assertFalse(report["owner_eligible"])
        self.assertFalse(report["first_use_consumed"])
        self.assertEqual(9,len(report["arms"]))
        self.assertEqual(54,sum(len(v["worlds"]) for v in report["arms"].values()))
        self.assertTrue(all(w["cold_matches"] for arm in report["arms"].values()
                            for w in arm["worlds"]))
        self.assertEqual(0,sum(w["probes"] for w in report["arms"]["calibrated-contradiction"]["worlds"]))
        self.assertEqual(report["report_sha256"],
                         f43.digest({k:v for k,v in report.items() if k!="report_sha256"}))

    def test_first_use_import_and_output_fail_closed(self):
        for seed in f43.FIRST_USE_FORBIDDEN:
            with self.assertRaisesRegex(ValueError,"PROTECTED_FIRST_USE"):
                f43.episode(self.fake,seed,"fixed-mpc",self.model,.1)
        with self.assertRaisesRegex(ValueError,"UNAUTHORIZED_DEV"):
            f43.episode(self.fake,1103,"fixed-mpc",self.model,.1)
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises((ValueError, RuntimeError, FileNotFoundError)):
                f43.original_gym(Path(root))
            with self.assertRaisesRegex(ValueError,"REPORT_INSIDE_PINNED_ORIGINAL"):
                f43.main([root,str(Path(root)/"result.json")])
        self.assertNotIn("gymnasium",sys.modules)


if __name__=="__main__":
    unittest.main(verbosity=2)
