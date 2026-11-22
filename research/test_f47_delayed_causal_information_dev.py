"""F47 FIT-only structure, delayed-physics and first-use refusal checks.

No transfer/retention episode or scientific result is consumed here.
"""
import inspect
import json
import math
import tempfile
import unittest

import f47_delayed_causal_information_dev as f47


class F47FocusedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.training, cls.coverage = f47.fit_data()
        cls.fit = f47.fit_shared(cls.training)

    def test_exact_common_training_only_action_consequences(self):
        self.assertEqual(8,len(self.training))
        self.assertEqual((192,192,192),tuple(self.coverage))
        self.assertEqual(576,sum(len(e) for w in self.training for e in w))
        self.assertEqual(576,self.fit["fit_transition_count"])
        self.assertEqual(8,self.fit["training_worlds"])
        self.assertEqual(8,len(self.fit["mode_winners"]))
        self.assertEqual(6,len(self.fit["prior"]))
        self.assertAlmostEqual(1.0,sum(self.fit["prior"]),places=12)
        self.assertTrue(all(x>0 for x in self.fit["prior"]))
        self.assertEqual(self.fit,json.loads(f47.canonical(self.fit)))
        self.assertEqual(f47.digest(self.training), f47.digest(f47.fit_data()[0]))

    def test_delayed_action_effects_and_final_only_reward(self):
        seed, ep = f47.FIT_SEEDS[0],0
        world=f47.CausalWorld(seed,ep,switching=False)
        start=world.state
        noise0,flip0=f47.exogenous(seed,ep,0)
        nxt,sensor,reward,terminal=world.step(0)
        self.assertEqual(start^noise0,nxt)  # First action is still queued.
        self.assertEqual(int((seed%6)>=3)^int(flip0),sensor)
        self.assertEqual(-1,reward)
        self.assertFalse(terminal)
        noise1,_=f47.exogenous(seed,ep,1)
        nxt1,sig1,r1,done1=world.step(1)
        self.assertEqual(nxt ^ f47.EFFECTS[seed%6][0] ^ noise1,nxt1)
        self.assertEqual(-1,sig1)
        self.assertEqual(-1,r1)
        self.assertFalse(done1)
        for action in (0,1,2,0):
            state,sig,reward,done=world.step(action)
        self.assertTrue(done)
        self.assertEqual(6,world.steps)
        self.assertTrue(isinstance(reward,int))
        with self.assertRaisesRegex(ValueError,"INVALID_OR_EXTRA_REAL_ACTION"):
            world.step(1)

    def test_hidden_interference_source_uses_real_steps_not_oracle(self):
        seed,ep=f47.FIT_SEEDS[2],1
        # Unit-test a private evaluator with mode switching, still FIT seed only.
        w=f47.CausalWorld(seed,ep,switching=True)
        for t,command in enumerate((0,1,0,1,2,0)):
            old,pending=w.state,w.pending
            current_mode=((seed%6+3)%6 if t in (3,4) else seed%6)
            actual=(f47.EFFECTS[current_mode][pending] if pending!=2 else 0)
            noise,noise_signal=f47.exogenous(seed,ep,t)
            state,sensor,_,_=w.step(command)
            self.assertEqual(old ^ actual ^ noise,state)
            self.assertEqual((int(current_mode>=3)^int(noise_signal))
                             if pending==2 else -1,sensor)
        self.assertEqual(["self","state","goal","pending","physical_t"],
                         list(inspect.signature(f47.Policy.decide).parameters))
        self.assertEqual(["self","old","pending_applied","new","witness"],
                         list(inspect.signature(f47.Policy.observe).parameters))

    def test_exact_noise_likelihood_and_information_is_paid(self):
        prior=self.fit["prior"]
        self.assertAlmostEqual(0.8,f47.observed_likelihood(0,0,1,-1))
        self.assertAlmostEqual(0.2/3,f47.observed_likelihood(0,0,0,-1))
        self.assertEqual(0.0,f47.observed_likelihood(0,0,7,-1))
        self.assertAlmostEqual(0.8*0.8,f47.observed_likelihood(0,2,0,0))
        self.assertAlmostEqual(0.8*0.2,f47.observed_likelihood(0,2,0,1))
        self.assertGreaterEqual(f47.witness_info(prior),0.0)
        self.assertLessEqual(f47.witness_info(prior),0.7)
        self.assertTrue(all(0<=f47.two_step_score(0,0,2,a,prior)+3<=5
                            for a in (0,1,2)))
        for kind in f47.ARMS:
            p=f47.Policy(kind,self.fit,0)
            action=p.decide(0,5,2,0)
            self.assertIn(action,(0,1,2))
            self.assertEqual(0,p.updates)
            self.assertEqual(int(action==2),p.sensors)

    def test_bayesian_update_source_only_and_wrong_credit(self):
        prior=self.fit["prior"]
        new,flag=f47.update_belief(prior,prior,0,0,1,-1)
        self.assertFalse(flag)
        self.assertAlmostEqual(1.0,sum(new),places=12)
        self.assertNotEqual(new,prior)
        wrong,_=f47.update_belief(prior,prior,0,0,1,-1,corrupt=True)
        self.assertNotEqual(new,wrong)
        p=f47.Policy("active-probe",self.fit,0)
        old=p.probs[:]
        p.observe(0,0,1,-1)
        self.assertNotEqual(old,p.probs)
        n=f47.Policy("no-feedback",self.fit,0)
        n.observe(0,0,1,-1)
        self.assertEqual(old,n.probs)
        with self.assertRaisesRegex(ValueError,"SENSOR_MISSING"):
            f47.observed_likelihood(0,2,0,-1)
        with self.assertRaisesRegex(ValueError,"PHANTOM"):
            f47.observed_likelihood(0,0,1,0)

    def test_frozen_cohorts_protection_and_no_evaluation_in_unit_tests(self):
        groups=[set(f47.FIT_SEEDS),set(f47.TRANSFER_SEEDS),set(f47.RETENTION_SEEDS)]
        self.assertEqual([8,24,12],[len(s) for s in groups])
        self.assertFalse(groups[0]&groups[1] or groups[0]&groups[2] or groups[1]&groups[2])
        self.assertFalse(set(f47.FORBIDDEN)&set.union(*groups))
        self.assertTrue(all(s%6 in (4,5) for s in groups[1]))
        self.assertTrue(all(s%6 in (0,1,2,3) for s in groups[0]|groups[2]))
        with self.assertRaisesRegex(ValueError,"UNAUTHORIZED_DEV_OR_FIRST_USE"):
            f47.evaluate_episode(59,0,"active-probe",self.fit)
        with self.assertRaisesRegex(ValueError,"UNAUTHORIZED_WORLD_OR_PROTECTED"):
            f47.CausalWorld(59,0,switching=False)
        with self.assertRaisesRegex(ValueError,"UNKNOWN_CONTROL"):
            f47.Policy("hidden_mode_oracle",self.fit,0)
        with self.assertRaisesRegex(ValueError,"F47_USAGE"):
            f47.main([])
        self.assertEqual(len(f47.ARMS),8)
        self.assertEqual(len(f47.CONVENTIONAL),4)
        self.assertEqual(f47.NEGATIVES,("wrong-credit","no-feedback"))


if __name__=="__main__":
    unittest.main(verbosity=2)
