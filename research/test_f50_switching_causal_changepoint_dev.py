"""F50 FIT-only structure/negative controls. NEVER consumes new DEV cohorts."""
import inspect
import json
import math
import unittest

import f50_switching_causal_changepoint_dev as f50


class F50FitOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worlds,cls.coverage=f50.collect_fit()
        cls.fit=f50.fit_model(cls.worlds)

    def test_training_custody_and_conventional_models_fully_fitted(self):
        self.assertEqual(8,len(self.worlds))
        self.assertEqual(1152,sum(len(ep) for w in self.worlds for ep in w))
        self.assertEqual([480,384,288],self.coverage)
        self.assertEqual(1152,self.fit["training_transitions"])
        self.assertEqual(8,self.fit["fit_worlds"])
        self.assertEqual(6,len(self.fit["prior"]))
        self.assertEqual(3,len(self.fit["empirical"]))
        self.assertAlmostEqual(1,sum(self.fit["prior"]),places=12)
        self.assertTrue(all(p>0 for p in self.fit["prior"]))
        self.assertEqual(self.fit,json.loads(f50.canonical(self.fit)))
        self.assertEqual(f50.digest(self.worlds),f50.digest(f50.collect_fit()[0]))

    def test_delayed_physical_effect_and_same_exogenous_noise(self):
        seed,ep=f50.FIT[0],0
        world=f50.World(seed,ep,switching=False)
        start=world.state
        noise,flip=f50.exogenous(seed,ep,0)
        nxt,wit,rwd,done=world.step(0)
        self.assertEqual(start^noise,nxt)  # Pending initial command is a sensor.
        self.assertEqual(int(seed%6>=3)^int(flip),wit)
        self.assertEqual(-1,rwd)
        self.assertFalse(done)
        noise1,_=f50.exogenous(seed,ep,1)
        after,wit1,rwd1,done1=world.step(1)
        self.assertEqual(nxt^f50.EFFECTS[seed%6][0]^noise1,after)
        self.assertEqual(-1,wit1)
        self.assertFalse(done1)
        for action in (0,2,1,0,1,0,2,1,0,1):
            after,wit,rwd,done=world.step(action)
        self.assertEqual(12,world.steps)
        self.assertTrue(done)
        with self.assertRaisesRegex(ValueError,"INVALID_OR_EXTRA_PHYSICAL_ACTION"):
            world.step(0)

    def test_noise_likelihood_and_true_pending_action_credit(self):
        self.assertAlmostEqual(.8,f50.likelihood(0,0,1,-1,sensor_applied=False))
        self.assertAlmostEqual(.2/3,f50.likelihood(0,0,0,-1,sensor_applied=False))
        self.assertAlmostEqual(.64,f50.likelihood(0,2,0,0,sensor_applied=True))
        self.assertAlmostEqual(.16,f50.likelihood(0,2,0,1,sensor_applied=True))
        self.assertEqual(0,f50.likelihood(0,0,7,-1,sensor_applied=False))
        self.assertNotEqual(
            f50.likelihood(0,0,1,-1,sensor_applied=False),
            f50.likelihood(0,2,1,-1,sensor_applied=False))
        with self.assertRaisesRegex(ValueError,"SENSOR_WITNESS_MISSING"):
            f50.likelihood(0,2,0,-1,sensor_applied=True)
        with self.assertRaisesRegex(ValueError,"UNREQUESTED_SENSOR_WITNESS"):
            f50.likelihood(0,0,1,0,sensor_applied=False)

    def test_consecutive_evidence_gate_is_not_single_noise_reset(self):
        fit={"prior":[1/6]*6,"empirical":[1,2,0]}
        c=f50.Policy("corroborated-change",fit)
        c.stable=[1.,0.,0.,0.,0.,0.]
        # Alternative-rule observation (action 0, public XOR effect 4).
        # A single improbable observation never triggers the candidate reset.
        c.observe(0,0,0,4,-1)
        self.assertEqual(0,c.resets)
        c.observe(0,0,0,4,-1)
        self.assertEqual(0,c.resets)
        c.observe(0,0,0,4,-1)
        self.assertEqual(1,c.resets)
        self.assertEqual([],c.last3)
        ablation=f50.Policy("candidate-no-reset",fit)
        ablation.stable=[1.,0.,0.,0.,0.,0.]
        for _ in range(3):
            ablation.observe(0,0,0,4,-1)
        self.assertEqual(0,ablation.resets)
        self.assertEqual(0,ablation.abstains)

    def test_no_privileged_world_or_noise_passed_to_policy(self):
        self.assertEqual(["self","state","goal","pending","t"],
            list(inspect.signature(f50.Policy.decide).parameters))
        self.assertEqual(["self","old","pending","requested","nxt","witness"],
            list(inspect.signature(f50.Policy.observe).parameters))
        for kind in f50.ARMS:
            learner=f50.Policy(kind,self.fit)
            action=learner.decide(0,5,2,0)
            self.assertIn(action,f50.ACTIONS)
            self.assertEqual(0,learner.observations)
        self.assertEqual(9,len(f50.ARMS))
        self.assertEqual(5,len(f50.CONVENTIONAL))
        self.assertEqual(3,len(f50.ABLATIONS))

    def test_fit_only_stationary_negative_control_without_heldout(self):
        c=f50.fit_replay(self.worlds,self.fit)
        self.assertEqual(96,c["episodes"])
        self.assertEqual(1152,c["records"])
        self.assertGreaterEqual(c["single_surprise_resets"],c["candidate_resets"])
        self.assertGreaterEqual(c["candidate_stable_updates"],0)
        self.assertEqual(c,f50.fit_replay(self.worlds,self.fit))

    def test_switch_capable_recent3_accepts_cross_mode_public_consequences(self):
        f=f50.Policy("recent3-switch-bayes",self.fit)
        # Action-0 effect 1 followed by effect 2: source-supported under
        # different latent modes, not explainable by fixed-mode multiplication.
        f.observe(0,0,0,1,-1)
        f.observe(0,0,0,2,-1)
        self.assertAlmostEqual(sum(f.working),1.0,places=12)
        self.assertEqual(2,len(f.history))
        self.assertTrue(all(p>=0 for p in f.working))
        self.assertTrue(any(p>0 for p in f.working))

    def test_fit_only_actual_switching_world_for_all_nine_arms(self):
        # Pre-evaluation smoke: all arms perform 12 real FIT-only physical
        # actions through actual rule reversals, no DEV seeds consumed.
        for arm in f50.ARMS:
            for seed in f50.FIT:
                for ep in range(2):
                    w=f50.World(seed,ep,switching=True)
                    p=f50.Policy(arm,self.fit)
                    for step in range(f50.DURATION):
                        before,pending=w.state,w.pending
                        cmd=p.decide(before,w.goal,pending,step)
                        after,witness,reward,done=w.step(cmd)
                        p.observe(before,pending,cmd,after,witness)
                    self.assertTrue(w.done)
                    self.assertEqual(f50.DURATION,w.steps)
                    self.assertEqual(f50.DURATION,p.observations)
                    self.assertAlmostEqual(sum(p.working),1.0,places=12)

    def test_disjoint_frozen_splits_and_first_use_fail_closed(self):
        groups=[set(f50.FIT),set(f50.TRANSFER),set(f50.RETENTION)]
        self.assertEqual([8,24,12],[len(x) for x in groups])
        self.assertFalse(groups[0]&groups[1] or groups[0]&groups[2] or groups[1]&groups[2])
        self.assertFalse(set(f50.FORBIDDEN)&set.union(*groups))
        self.assertTrue(all(s%6 in (4,5) for s in groups[1]))
        self.assertTrue(all(s%6 in (0,1,2,3) for s in groups[0]|groups[2]))
        for seed in groups[0]:
            s,g=f50.task(seed,0)
            self.assertNotEqual(s,g)
        with self.assertRaisesRegex(ValueError,"UNAUTHORIZED_DEV_OR_PROTECTED"):
            f50.episode(59,0,"corroborated-change",self.fit)
        with self.assertRaisesRegex(ValueError,"UNAUTHORIZED_SOURCE_OR_PROTECTED"):
            f50.World(59,0)
        with self.assertRaisesRegex(ValueError,"UNKNOWN_POLICY_ARM"):
            f50.Policy("oracle_true_hidden_mode",self.fit)
        with self.assertRaisesRegex(ValueError,"F50_USAGE"):
            f50.main([])


if __name__=="__main__":
    unittest.main(verbosity=2)
