"""F51 original upstream Gymnasium Acrobot provenance and FIT-only controls.

No scored TRANSFER or RETENTION seeds are instantiated in focused testing.
No fake physics or fixtures can count as a successful original environment.
"""
import inspect
import math
import os
from pathlib import Path
import unittest

import numpy as np
import f51_original_acrobot_transfer_dev as f51


class F51OriginalEnvironmentChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=f51.check_original()

    def test_exact_source_module_not_local_or_emulated(self):
        self.assertEqual(f51.ORIGINAL_COMMIT,self.source["upstream_commit"])
        self.assertEqual(f51.ORIGINAL_FILE_BLOB,self.source["acrobot_git_blob"])
        self.assertEqual("1.2.3",self.source["gymnasium_version"])
        expected=(Path(os.environ["F51_ORIGINAL_GYMNASIUM_ROOT"])/
                  "gymnasium/envs/classic_control/acrobot.py").resolve()
        self.assertEqual(str(expected),self.source["module_path"])
        self.assertEqual(Path(inspect.getfile(f51.AcrobotEnv)).resolve(),expected)
        self.assertEqual(len(f51.ARMS),5)
        self.assertEqual(len(f51.CONTROLS),3)

    def test_unaltered_real_book_and_nips_physics_step(self):
        for mode in ("book","nips"):
            env=f51.new_real_env(mode)
            try:
                obs,_=env.reset(seed=f51.FIT[0]*100+1)
                self.assertEqual((6,),obs.shape)
                self.assertEqual(mode,env.unwrapped.book_or_nips)
                seen=[]
                for t in range(16):
                    action=t%3
                    next_obs,reward,terminated,truncated,_=env.step(action)
                    self.assertEqual((6,),next_obs.shape)
                    self.assertTrue(np.all(np.isfinite(next_obs)))
                    self.assertTrue(reward in (-1.0,0.0))
                    seen.append(float(np.linalg.norm(next_obs-obs)))
                    obs=next_obs
                    if terminated or truncated:
                        break
                self.assertTrue(any(x>0 for x in seen))
            finally:
                env.close()

    def test_original_public_only_features_and_momentum(self):
        ob=[1.,0.,1.,0.,.0,.0]
        phi=f51.features(ob)
        self.assertEqual((f51.DIMS,),phi.shape)
        self.assertAlmostEqual(phi[0],1.0)
        self.assertTrue(np.all(np.isfinite(phi)))
        self.assertEqual(2,f51.energy_rule(ob))
        self.assertEqual(0,f51.energy_rule([1,0,1,0,0,-1]))
        with self.assertRaisesRegex(ValueError,"PUBLIC_SIX_OBSERVATIONS"):
            f51.features([0,1,2])
        self.assertEqual(["self","obs"],
                         list(inspect.signature(f51.Policy.action).parameters))
        self.assertEqual(["self","old","actual_action","reward","next_observation","done"],
                         list(inspect.signature(f51.Policy.observe).parameters))

    def test_train_small_real_source_fit_prefix_fqi_and_all_arms(self):
        records=[]
        for episode in range(2):
            env=f51.new_real_env("book")
            try:
                obs,_=env.reset(seed=f51.FIT[0]*100+episode)
                for t in range(36):
                    a=t%3
                    nxt,r,terminated,truncated,_=env.step(a)
                    records.append([list(map(float,obs)),a,float(r),
                                    list(map(float,nxt)),bool(terminated),bool(truncated)])
                    obs=nxt
                    if terminated or truncated:
                        break
            finally:
                env.close()
        self.assertGreaterEqual(len(records),40)
        self.assertEqual({0,1,2},set(r[1] for r in records))
        q=f51.fit_fqi(records,passes=2)
        self.assertEqual((3,f51.DIMS),q.shape)
        self.assertTrue(np.all(np.isfinite(q)))
        first=records[0]
        for kind in f51.ARMS:
            p=f51.Policy(kind,q)
            action=p.action(first[0])
            self.assertIn(action,(0,1,2))
            p.observe(first[0],first[1],first[2],first[3],False)
            self.assertEqual(1,p.physical_observations)
            self.assertTrue(np.all(np.isfinite(p.theta)))
        with self.assertRaisesRegex(ValueError,"UNKNOWN_POLICY"):
            f51.Policy("true_nips_oracle",q)

    def test_credit_negative_and_cold_determinism_of_public_fit_only_rollout(self):
        theta=np.zeros((3,f51.DIMS),dtype=np.float64)
        obs=[1.,0.,1.,0.,.1,-.1]
        new=[.999,.01,.999,.01,.15,-.2]
        normal=f51.Policy("always-td",theta)
        wrong=f51.Policy("wrong-credit-td",theta)
        normal.observe(obs,0,-1.,new,False)
        wrong.observe(obs,0,-1.,new,False)
        self.assertFalse(np.array_equal(normal.theta,wrong.theta))
        self.assertTrue(np.any(normal.theta[0]!=0))
        self.assertTrue(np.any(wrong.theta[1]!=0))
        p=f51.Policy("contradiction-gated-td",theta)
        p.observe(obs,2,-1.,new,False)
        self.assertEqual(1,p.physical_observations)
        self.assertGreaterEqual(p.adapt_steps,0)

    def test_frozen_holdout_first_use_and_original_mismatch_refusal(self):
        self.assertEqual([6,12,8],[len(f51.FIT),len(f51.TRANSFER),len(f51.RETENTION)])
        self.assertEqual(26,len(set((*f51.FIT,*f51.TRANSFER,*f51.RETENTION))))
        self.assertFalse(set(f51.FORBIDDEN)&set((*f51.FIT,*f51.TRANSFER,*f51.RETENTION)))
        theta=np.zeros((3,f51.DIMS),dtype=np.float64)
        for bad in (59,83,f51.FIT[0],42):
            with self.assertRaisesRegex(ValueError,"UNAUTHORIZED_DEV_OR_FIRST_USE"):
                f51.evaluate(bad,"book","frozen-fqi",theta)
        with self.assertRaisesRegex(ValueError,"TRANSFER_RETENTION_DYNAMICS_CUSTODY"):
            f51.evaluate(f51.TRANSFER[0],"book","frozen-fqi",theta)
        with self.assertRaisesRegex(ValueError,"F51_USAGE"):
            f51.main([])
        with self.assertRaisesRegex(ValueError,"UNKNOWN_ORIGINAL_DYNAMICS_MODE"):
            f51.new_real_env("patched")
        original=os.environ.pop("F51_ORIGINAL_GYMNASIUM_ROOT")
        try:
            with self.assertRaisesRegex(RuntimeError,"EXTERNAL_ORIGINAL_ROOT_UNVERIFIED"):
                f51.check_original()
        finally:
            os.environ["F51_ORIGINAL_GYMNASIUM_ROOT"]=original


if __name__=="__main__":
    unittest.main(verbosity=2)
