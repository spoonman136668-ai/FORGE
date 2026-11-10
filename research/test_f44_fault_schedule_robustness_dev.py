"""F44 exact protocol / fake original negative tests.

These fixtures MUST NOT emit genuine original Gymnasium result labels.
"""
from pathlib import Path
import inspect
import json
import sys
import tempfile
import unittest

import numpy as np

import f41_original_mountaincar_dev as f41
import f42_original_actuator_reversal_dev as f42
import f43_train_calibrated_contradiction_dev as f43
import f44_fault_schedule_robustness_dev as f44


class ActionSpace:
    n = 3


class FakeCar:
    action_space = ActionSpace()

    def reset(self, seed):
        self.t = 0
        self.state = [-.5 + .001 * (seed % 17), 0.0]
        return self.state[:], {"hidden": "unread"}

    def step(self, action):
        if self.t >= 11:
            raise ValueError("F44_FAKE_STEPPED_AFTER_DONE")
        self.t += 1
        p, v = self.state
        v = .91 * v + .001 * (action - 1)
        p += v
        self.state = [p, v]
        return self.state[:], -1.0, self.t == 11, False, {"actual_hidden": "unread"}

    def close(self):
        pass


class FakeGym:
    def make(self, name, render_mode):
        if name != "MountainCar-v0" or render_mode is not None:
            raise AssertionError("FAKE_TEST_INTERFACE_CHANGED")
        return FakeCar()


class F44Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gym = FakeGym()
        cls.transcript, cls.coverage = f41.training(cls.gym)
        cls.model = f41.fit_dynamics(cls.transcript)
        cls.fit = {
            "dynamics": cls.model,
            "tau": 0.12375435588208586,
            "calibration_n": 15127,
            "training_sha256": f44.TRAIN_SHA256,
            "training_transitions": 18138,
            "training_episodes": 96,
            "training_action_counts": [7107, 3011, 8020],
            "source_fit_sha256": f44.digest(cls.model),
        }

    def test_strong_controls_and_exactly_new_unconsumed_scenarios(self):
        self.assertEqual(9, len(f44.KINDS))
        self.assertEqual(f43.KINDS, f44.KINDS)
        self.assertEqual(f43.CONVENTIONAL, f44.CONVENTIONAL)
        self.assertEqual(f43.ABLATIONS, f44.ABLATIONS)
        self.assertEqual(8, len(f44.FAULT_WORLDS))
        self.assertEqual(4, len(f44.RETENTION_WORLDS))
        new_seeds = set(f44.FAULT_WORLDS) | set(f44.RETENTION_WORLDS)
        self.assertEqual(12, len(new_seeds))
        self.assertFalse(new_seeds.intersection(f43.FAULT_WORLDS))
        self.assertFalse(new_seeds.intersection(f43.NO_FAULT_WORLDS))
        self.assertFalse(new_seeds.intersection(f42.FAULT_WORLDS))
        self.assertFalse(new_seeds.intersection(f41.EVAL_SEEDS))
        self.assertFalse(new_seeds.intersection(f41.TRAIN_SEEDS))
        self.assertFalse(new_seeds.intersection(f44.FORBIDDEN))
        self.assertEqual([1,3,1,3], [len(f44.FAULT_WORLDS[k])
                         for k in (1543,1567,1553,1571)])
        self.assertTrue(all(0 <= a < b <= 200 for windows in f44.FAULT_WORLDS.values()
                            for a,b in windows))
        self.assertTrue(all(all(windows[i][1] < windows[i+1][0]
                            for i in range(len(windows)-1))
                            for windows in f44.FAULT_WORLDS.values()))

    def test_original_training_only_refusal_and_frozen_model(self):
        self.assertNotEqual(f44.TRAIN_SHA256, f44.digest(self.transcript))
        with self.assertRaisesRegex(ValueError, "F41_TRAINING_ONLY_TRANSCRIPT_DRIFT"):
            f43.source_fit(self.gym)
        self.assertEqual((6,2), np.asarray(self.model["global"]).shape)
        self.assertEqual(f44.TRAIN_SHA256, f43.TRAIN_SHA256)
        self.assertEqual(list(inspect.signature(f43.policy_for).parameters),
                         ["kind","dynamics","tau"])
        self.assertEqual(list(inspect.signature(f44.run_episode).parameters),
                         ["gym","seed","kind","model","tau"])

    def test_external_faults_never_exposed_to_policy(self):
        for seed, windows in f44.FAULT_WORLDS.items():
            for a,b in windows:
                self.assertEqual(2, f42.effective_action(0,a,windows))
                self.assertEqual(2, f42.effective_action(0,b-1,windows))
                self.assertEqual(0, f42.effective_action(0,b,windows))
        no_fault = f44.run_episode(self.gym,1583,"calibrated-contradiction",self.model,.1)
        self.assertEqual(0,no_fault["faulted_actions"])
        self.assertEqual(0,no_fault["forced_probes"])
        self.assertEqual(11,no_fault["steps"])
        self.assertEqual(-11,no_fault["return"])
        faulted = f44.run_episode(self.gym,1501,"rolling8-probe",self.model,.1)
        self.assertEqual(11,faulted["steps"])
        self.assertLessEqual(faulted["forced_probes"],16)
        self.assertEqual(0,faulted["faulted_actions"])  # first reversal only after step 20
        self.assertTrue(all("requested" in x and "physical" in x for x in faulted["trace"]))

    def test_fake_original_never_issues_genuine_dev_signal(self):
        report=f44.score(self.gym,self.fit,f44.SOURCE)
        self.assertEqual("F44_ORIGINAL_RUNTIME_UNVERIFIED",report["classification"])
        self.assertEqual(9,len(report["arms"]))
        self.assertEqual(108,sum(len(a["worlds"]) for a in report["arms"].values()))
        self.assertTrue(all(w["cold_matches"] for arm in report["arms"].values()
                            for w in arm["worlds"]))
        self.assertTrue(all(w["forced_probes"]<=16 for arm in report["arms"].values()
                            for w in arm["worlds"]))
        self.assertTrue(all(w["forced_probes"]==0
                            for w in report["arms"]["calibrated-contradiction"]["worlds"]))
        self.assertGreater(report["decision_cost_ratio_to_strongest"],0)
        self.assertFalse(report["scientific_accepted"])
        self.assertFalse(report["owner_eligible"])
        self.assertFalse(report["first_use_consumed"])
        self.assertFalse(report["unmodified_original_gymnasium_task"])
        self.assertEqual(report["report_sha256"],f44.digest({
            k:v for k,v in report.items() if k!="report_sha256"
        }))
        self.assertTrue(isinstance(report["frozen_conditions_met"],bool))

    def test_guarded_missing_source_bad_seed_or_bad_fit(self):
        for seed in f44.FORBIDDEN:
            with self.assertRaisesRegex(ValueError,"PROTECTED_OR_UNAUTHORIZED"):
                f44.run_episode(self.gym,seed,"velocity-rule",self.model,.1)
        with self.assertRaisesRegex(ValueError,"PROTECTED_OR_UNAUTHORIZED"):
            f44.run_episode(self.gym,1409,"velocity-rule",self.model,.1)
        with self.assertRaisesRegex(ValueError,"UNREGISTERED_CONTROL"):
            f44.run_episode(self.gym,1501,"new_controller",self.model,.1)
        bad = {**self.fit, "training_sha256":"tampered"}
        with self.assertRaisesRegex(ValueError,"FROZEN_TRAINING_ONLY_CUSTODY"):
            f44.score(self.gym,bad,f44.SOURCE)
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises((ValueError, RuntimeError, FileNotFoundError)):
                f44.original_gym(Path(folder))
            with self.assertRaisesRegex(ValueError,"OUTPUT_INSIDE_ORIGINAL_SOURCE"):
                f44.main([folder,str(Path(folder)/"result.json")])
        self.assertNotIn("gymnasium",sys.modules)


if __name__ == "__main__":
    unittest.main(verbosity=2)
