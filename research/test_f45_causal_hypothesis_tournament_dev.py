"""F45 structural falsifiers; fake physics must never issue genuine original result."""
from pathlib import Path
import json
import tempfile
import unittest

import numpy as np

import f41_original_mountaincar_dev as f41
import f42_original_actuator_reversal_dev as f42
import f43_train_calibrated_contradiction_dev as f43
import f44_fault_schedule_robustness_dev as f44
import f45_causal_hypothesis_tournament_dev as f45


class ActionSpace:
    n = 3


class FakeCar:
    action_space = ActionSpace()

    def reset(self,seed):
        self.t=0
        self.state=[-.48+.001*(seed%11),0.0]
        return self.state[:],{"ignored":11}

    def step(self,action):
        if self.t>=8:
            raise AssertionError("FAKE_AFTER_DONE")
        self.t+=1
        p,v=self.state
        v=.92*v+.001*(action-1)
        p+=v
        self.state=[p,v]
        return self.state[:],-1.0,self.t==8,False,{"hidden":10}

    def close(self):
        pass


class FakeGym:
    def make(self,name,render_mode):
        if name!="MountainCar-v0" or render_mode is not None:
            raise ValueError("FAKE_WRONG_PUBLIC_INTERFACE")
        return FakeCar()


class F45Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gym=FakeGym()
        cls.samples,cls.coverage=f41.training(cls.gym)
        cls.model=f41.fit_dynamics(cls.samples)
        cls.fit={
            "dynamics":cls.model,
            "tau":0.12375435588208586,
            "training_sha256":f45.TRAIN_SHA256,
            "training_episodes":96,
            "training_transitions":18138,
            "training_action_counts":[7107,3011,8020],
            "calibration_n":15127,
            "source_fit_sha256":f45.digest(cls.model),
        }

    def test_frozen_original_training_refuses_fake_source(self):
        self.assertEqual(768,len(self.samples))
        self.assertNotEqual(f45.TRAIN_SHA256,f45.digest(self.samples))
        with self.assertRaisesRegex(ValueError,"F41_TRAINING_ONLY_TRANSCRIPT_DRIFT"):
            f45.frozen_fit(self.gym)
        self.assertEqual((6,2),np.asarray(self.model["global"]).shape)
        self.assertEqual(f45.TRAIN_SHA256,f43.TRAIN_SHA256)

    def test_new_fault_windows_disjoint_earlier_cohorts_and_no_first_use(self):
        self.assertEqual(8,len(f45.FAULT_WORLDS))
        self.assertEqual(4,len(f45.RETENTION_WORLDS))
        all_new=set(f45.FAULT_WORLDS)|set(f45.RETENTION_WORLDS)
        self.assertEqual(12,len(all_new))
        for old in (set(f41.TRAIN_SEEDS),set(f41.EVAL_SEEDS),
                    set(f42.FAULT_WORLDS),set(f43.FAULT_WORLDS),
                    set(f44.FAULT_WORLDS),set(f44.RETENTION_WORLDS),
                    set(f43.NO_FAULT_WORLDS),{59,83}):
            self.assertFalse(all_new.intersection(old))
        self.assertTrue(all(all(0<=start<end<=200 for start,end in windows)
            for windows in f45.FAULT_WORLDS.values()))
        self.assertEqual(11,len(f45.KINDS))
        self.assertEqual(6,len(f45.CONVENTIONAL))
        self.assertEqual(4,len(f45.TOURNAMENT))

    def test_model_averaged_shared_action_sequences_and_information_ablation(self):
        state=[-.5,.003]
        p=.32
        normal,reverse=f45.hypothesis_returns(state,self.model)
        self.assertEqual(normal.shape,(81,))
        self.assertEqual(reverse.shape,(81,))
        bonus=f45.information_bonus(state,self.model,p)
        self.assertEqual(bonus.shape,(81,))
        self.assertTrue(np.all(bonus>=0))
        self.assertTrue(np.all(bonus<=.04+1e-12))
        self.assertTrue(np.all(bonus[f41.SEQUENCES[:,0]==1]==0))
        candidate=f45.Tournament("hypothesis-tournament",self.model)
        candidate.posterior=p
        expected=int(f41.SEQUENCES[int(np.argmax((1-p)*normal+p*reverse+bonus)),0])
        self.assertEqual(expected,candidate.decide(state,0))
        no_info=f45.Tournament("tournament-no-info",self.model)
        no_info.posterior=p
        expected_plain=int(f41.SEQUENCES[int(np.argmax((1-p)*normal+p*reverse)),0])
        self.assertEqual(expected_plain,no_info.decide(state,0))
        self.assertEqual(0,candidate.probes)

    def test_public_consequences_update_beliefs_and_negative_controls(self):
        w=np.zeros((6,2),dtype=float)
        w[4,1]=.003
        m={"global":w.tolist(),"residual":np.zeros((3,6,2)).tolist()}
        state=[-.48,0.0]
        reverse_next=f41.predict([state],[2],m)[0].tolist()
        c=f45.Tournament("hypothesis-tournament",m)
        wrong=f45.Tournament("tournament-wrong-credit",m)
        fixed=f45.Tournament("tournament-static-belief",m)
        no_info=f45.Tournament("tournament-no-info",m)
        for q in (c,wrong,fixed,no_info):
            q.observe(state,0,reverse_next)
        self.assertGreater(c.posterior,.02)
        self.assertEqual(c.posterior,no_info.posterior)
        self.assertLess(wrong.posterior,c.posterior)
        self.assertLess(wrong.posterior,.03+.94*.02)
        self.assertEqual(fixed.posterior,.02)
        self.assertEqual(fixed.posterior_changes,0)
        self.assertGreater(c.informative,0)
        for q in (c,wrong,fixed,no_info):
            self.assertIn(q.decide(state,1),(0,1,2))
            self.assertEqual(0,q.probes)

    def test_fake_score_always_unverified_even_if_metrics_pass(self):
        r=f45.assess(self.gym,self.fit,f45.SOURCE)
        self.assertEqual("F45_ORIGINAL_RUNTIME_UNVERIFIED",r["classification"])
        self.assertEqual(132,sum(len(a["worlds"]) for a in r["arms"].values()))
        self.assertEqual(set(f45.KINDS),set(r["arms"]))
        self.assertTrue(all(w["cold_matches"] for a in r["arms"].values()
                            for w in a["worlds"]))
        self.assertTrue(all(w["probes"]==0 for w in r["arms"]["hypothesis-tournament"]["worlds"]))
        self.assertFalse(r["scientific_accepted"])
        self.assertFalse(r["owner_eligible"])
        self.assertFalse(r["first_use_consumed"])
        self.assertFalse(r["unmodified_original_gymnasium_task"])
        self.assertEqual(r["report_sha256"],
                         f45.digest({k:v for k,v in r.items() if k!="report_sha256"}))

    def test_reject_first_use_invalid_source_and_unknown_arm(self):
        for seed in f45.FORBIDDEN:
            with self.assertRaisesRegex(ValueError,"PROTECTED_OR_UNAUTHORIZED"):
                f45.episode(self.gym,seed,"fixed-mpc",self.model,.1)
        with self.assertRaisesRegex(ValueError,"PROTECTED_OR_UNAUTHORIZED"):
            f45.episode(self.gym,1802,"fixed-mpc",self.model,.1)
        with self.assertRaisesRegex(ValueError,"UNREGISTERED_POLICY"):
            f45.policy_for("extra_controller",self.model,.1)
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises((ValueError,RuntimeError,FileNotFoundError)):
                f45.original_gym(Path(root))
            with self.assertRaisesRegex(ValueError,"REPORT_INSIDE_PINNED_GYMNASIUM"):
                f45.main([root,str(Path(root)/"result.json")])
        bad={**self.fit,"training_sha256":"not source"}
        with self.assertRaisesRegex(ValueError,"FROZEN_SOURCE_FIT_NOT_QUALIFIED"):
            f45.assess(self.gym,bad,f45.SOURCE)


if __name__=="__main__":
    unittest.main(verbosity=2)
