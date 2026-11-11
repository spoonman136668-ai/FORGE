"""FIT-only original-source tests for F52: zero F51 transfer/retention access."""
import inspect
import math
import os
from pathlib import Path
import unittest

import numpy as np
import f51_original_acrobot_transfer_dev as f51
import f52_original_acrobot_fit_value_error_audit as f52


class F52OriginalAcrobotFitOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=f51.check_original()

    def test_real_external_source_and_frozen_unmodified_F51(self):
        self.assertEqual("365080941ea3a815ac09e57a7d4ee263a142651d",
                         self.original["upstream_commit"])
        self.assertEqual("28c440af281858c30e95fb6023f19923065d64fe",
                         self.original["acrobot_git_blob"])
        self.assertEqual("1.2.3",self.original["gymnasium_version"])
        expected=(Path(os.environ["F51_ORIGINAL_GYMNASIUM_ROOT"])/
                  "gymnasium/envs/classic_control/acrobot.py").resolve()
        self.assertEqual(Path(inspect.getfile(f51.AcrobotEnv)).resolve(),expected)
        self.assertEqual("d3114ac66589e6b9f623318da721449090cfd54a",
                         f52.F51_SOURCE_BLOB)
        self.assertEqual("73564b62728d0df0d87955d83a8836aa08e53d15",
                         f52.F52_PROTOCOL_BLOB)
        self.assertEqual(40,f51.FQI_PASSES)
        self.assertEqual(8.,f52.FIT_THRESHOLD)

    def test_frozen_FIT_custody_and_protected_source_first_use_refusal(self):
        self.assertEqual(6,len(f51.FIT))
        self.assertEqual(12,len(f51.TRANSFER))
        self.assertEqual(8,len(f51.RETENTION))
        self.assertEqual(26,len(set((*f51.FIT,*f51.TRANSFER,*f51.RETENTION))))
        self.assertFalse(set(f51.FIT)&set(f51.TRANSFER))
        self.assertFalse(set(f51.FIT)&set(f51.RETENTION))
        self.assertFalse(set(f51.FORBIDDEN)&set((*f51.FIT,*f51.TRANSFER,*f51.RETENTION)))
        self.assertEqual((3604,1824,3546),f52.EXPECTED_FIT_COUNTS)
        self.assertEqual(8974,f52.EXPECTED_FIT_TRANSITIONS)
        with self.assertRaisesRegex(ValueError,"UNAUTHORIZED_DEV_OR_FIRST_USE"):
            f51.evaluate(59,"book","frozen-fqi",np.zeros((3,15)))
        with self.assertRaisesRegex(ValueError,"F52_USAGE"):
            f52.main([])
        self.assertEqual("F51_DEV_NO_GO","F51_DEV_NO_GO")

    def test_only_actual_original_book_physics_for_smoke(self):
        env=f51.new_real_env("book")
        try:
            obs,_=env.reset(seed=f51.FIT[0]*100)
            self.assertEqual("book",env.unwrapped.book_or_nips)
            self.assertEqual((6,),obs.shape)
            for t in range(12):
                nxt,reward,terminated,truncated,_=env.step(t%3)
                self.assertTrue(np.all(np.isfinite(nxt)))
                self.assertEqual((6,),nxt.shape)
                self.assertIn(float(reward),(-1.,0.))
                obs=nxt
                if terminated or truncated:
                    break
        finally:
            env.close()

    def test_frozen_public_TD_arithmetic_under_known_fixed_book(self):
        env=f51.new_real_env("book")
        try:
            obs,_=env.reset(seed=f51.FIT[0]*100+1)
            nxt,reward,terminal,trunc,_=env.step(0)
            row=[list(map(float,obs)),0,float(reward),
                 list(map(float,nxt)),bool(terminal),bool(trunc)]
        finally:
            env.close()
        theta=np.zeros((3,15))
        self.assertAlmostEqual(f52.frozen_q_error(row,theta),float(reward))
        self.assertEqual(["row","theta"],
                         list(inspect.signature(f52.frozen_q_error).parameters))
        with self.assertRaisesRegex(ValueError,"INVALID_PUBLIC_PHYSICAL_ACTION"):
            bad=list(row)
            bad[1]=99
            f52.frozen_q_error(bad,theta)

    def test_actual_credit_negative_and_frozen_original_trigger_semantics(self):
        theta=np.zeros((3,15))
        old=[1.,0.,1.,0.,0.,0.]
        new=[.999,.01,.999,.01,.05,-.04]
        p=f51.Policy("contradiction-gated-td",theta)
        normal=f51.Policy("always-td",theta)
        wrong=f51.Policy("wrong-credit-td",theta)
        for actor in (p,normal,wrong):
            actor.observe(old,0,-1.,new,False)
            self.assertEqual(1,actor.physical_observations)
            self.assertTrue(np.all(np.isfinite(actor.theta)))
        self.assertFalse(np.array_equal(normal.theta,wrong.theta))
        self.assertEqual(0,p.trigger_events)
        self.assertEqual(0,p.adapt_steps)
        self.assertEqual(["self","old","actual_action","reward","next_observation","done"],
                         list(inspect.signature(f51.Policy.observe).parameters))
        self.assertNotIn("mode",inspect.signature(f51.Policy.observe).parameters)

    def test_protocol_preserves_original_F51_science_status(self):
        self.assertEqual("63d31930006ec2f465e4becd989c1a0b922e15a0842ef991fe424074d436a31a",
                         f52.F51_ORIGINAL_FIT_SHA256)
        self.assertEqual(0.98,f51.GAMMA)
        self.assertTrue(math.isfinite(f51.GAMMA))
        self.assertEqual(5,len(f51.ARMS))
        self.assertEqual(3,len(f51.CONTROLS))
        self.assertNotIn("nips",inspect.getsource(f52.audit_training_only))
        self.assertNotIn("f51.evaluate(",inspect.getsource(f52.audit_training_only))
        self.assertNotIn("f51.score(",inspect.getsource(f52.audit_training_only))


if __name__=="__main__":
    unittest.main(verbosity=2)
