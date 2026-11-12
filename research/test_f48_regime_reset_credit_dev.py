"""F48 FIT-only tests: no heldout transfer or retention cohorts consumed."""
import inspect
import json
import math
import unittest

import f48_regime_reset_credit_dev as f48


class F48FocusedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fit_worlds,cls.coverage=f48.fit_data()
        cls.fit=f48.fit_shared(cls.fit_worlds)

    def test_frozen_fit_data_only_not_scored_heldout(self):
        self.assertEqual(8,len(self.fit_worlds))
        self.assertEqual([288,288,192],self.coverage)
        self.assertEqual(768,sum(len(ep) for w in self.fit_worlds for ep in w))
        self.assertEqual(768,self.fit["training_transitions"])
        self.assertEqual(8,self.fit["training_worlds"])
        self.assertEqual(6,len(self.fit["prior"]))
        self.assertEqual(3,len(self.fit["empirical"]))
        self.assertAlmostEqual(1.0,sum(self.fit["prior"]))
        self.assertTrue(all(x>0 for x in self.fit["prior"]))
        self.assertEqual(self.fit,json.loads(f48.canonical(self.fit)))
        self.assertEqual(f48.digest(self.fit_worlds),f48.digest(f48.fit_data()[0]))

    def test_real_delayed_actions_from_fit_only_world(self):
        seed,ep=f48.FIT[0],0
        world=f48.World(seed,ep,switching=False)
        start=world.state
        noise0,flip0=f48.exogenous(seed,ep,0)
        next0,wit0,reward0,done0=world.step(0)
        self.assertEqual(start^noise0,next0)
        self.assertEqual(int(seed%6>=3)^int(flip0),wit0)
        self.assertEqual(-1,reward0)
        self.assertFalse(done0)
        noise1,_=f48.exogenous(seed,ep,1)
        next1,wit1,reward1,done1=world.step(1)
        self.assertEqual(next0^f48.EFFECTS[seed%6][0]^noise1,next1)
        self.assertEqual(-1,wit1)
        self.assertFalse(done1)
        for action in (0,1,2,0,1,0):
            next1,wit1,reward1,done1=world.step(action)
        self.assertEqual(f48.DURATION,world.t)
        self.assertTrue(world.done)
        with self.assertRaisesRegex(ValueError,"INVALID_REAL_STEP"):
            world.step(1)

    def test_fit_only_interference_and_likelihood_grammar(self):
        seed,ep=f48.FIT[3],1
        world=f48.World(seed,ep,switching=True)
        for t,action in enumerate(f48.BEHAVIOR):
            old,pending=world.state,world.pending
            mode=((seed%6+3)%6 if t in (3,4,5) else seed%6)
            delta=(f48.EFFECTS[mode][pending] if pending!=2 else 0)
            noise,flip=f48.exogenous(seed,ep,t)
            nxt,witness,reward,done=world.step(action)
            self.assertEqual(old^delta^noise,nxt)
            self.assertEqual((int(mode>=3)^int(flip)) if pending==2 else -1,witness)
        self.assertAlmostEqual(.8,f48.likelihood(0,0,1,-1,sensor_applied=False))
        self.assertAlmostEqual(.2/3,f48.likelihood(0,0,0,-1,sensor_applied=False))
        self.assertAlmostEqual(.8*.8,f48.likelihood(0,2,0,0,sensor_applied=True))
        self.assertEqual(0,f48.likelihood(0,0,7,-1,sensor_applied=False))
        with self.assertRaisesRegex(ValueError,"MISSING_PUBLIC_SENSOR"):
            f48.likelihood(0,2,0,-1,sensor_applied=True)
        with self.assertRaisesRegex(ValueError,"PHANTOM_PUBLIC_SENSOR"):
            f48.likelihood(0,0,1,0,sensor_applied=False)

    def test_stable_working_reset_and_delayed_credit_vs_wrong_credit(self):
        a=f48.Policy("stable-working-reset",self.fit)
        prior=self.fit["prior"]
        a.working=[1.,0.,0.,0.,0.,0.]
        a.stable=[1.,0.,0.,0.,0.,0.]
        # Hypothesis-0 action-0 effect 1. Seeing effect 4 is impossible under it
        # without changing causal assumptions. This is source-only unit stimulus.
        a.observe(0,0,0,4,-1)
        self.assertEqual(1,a.resets)
        self.assertAlmostEqual(1.,sum(a.working))
        self.assertGreater(a.working[4],0)
        b=f48.Policy("candidate-no-reset",self.fit)
        b.working=[1.,0.,0.,0.,0.,0.]
        # Hazard prior still keeps nonzero support for recovery.
        b.observe(0,0,0,4,-1)
        self.assertEqual(0,b.resets)
        c=f48.Policy("candidate-no-stable",self.fit)
        c.working=[1.,0.,0.,0.,0.,0.]
        c.observe(0,0,0,4,-1)
        self.assertEqual(1,c.resets)
        self.assertEqual(0,c.stable_updates)
        d=f48.Policy("candidate-wrong-credit",self.fit)
        d.observe(0,0,2,1,-1)
        self.assertGreaterEqual(d.abstains,0)
        self.assertEqual(1,d.observations)
        self.assertEqual(["self","state","goal","pending","t"],
                         list(inspect.signature(f48.Policy.decide).parameters))
        self.assertEqual(["self","before","pending","requested","after","witness"],
                         list(inspect.signature(f48.Policy.observe).parameters))
        self.assertNotEqual(f48.likelihood(0,0,1,-1,sensor_applied=False),
                            f48.likelihood(0,2,1,-1,sensor_applied=False))

    def test_strong_fully_fitted_baselines_and_goal_planner(self):
        self.assertEqual(9,len(f48.ARMS))
        self.assertEqual(5,len(f48.CONTROLS))
        self.assertEqual(3,len(f48.NEGATIVES))
        for k in f48.ARMS:
            p=f48.Policy(k,self.fit)
            a=p.decide(1,4,2,0)
            self.assertIn(a,f48.ACTIONS)
            self.assertEqual(0,p.observations)
            self.assertEqual(0,p.resets)
        self.assertIn(f48.planner(1,4,2,self.fit["prior"]),f48.ACTIONS)
        self.assertEqual(3,f48.hamming(0,7))
        with self.assertRaisesRegex(ValueError,"UNKNOWN_POLICY"):
            f48.Policy("true_hidden_mode_oracle",self.fit)
        with self.assertRaisesRegex(ValueError,"INVALID_PUBLIC_CLOCK"):
            f48.Policy("fixed-hazard-bayes",self.fit).decide(0,2,2,8)

    def test_new_frozen_seed_groups_and_first_use_refusal(self):
        groups=[set(f48.FIT),set(f48.TRANSFER),set(f48.RETENTION)]
        self.assertEqual([8,24,12],[len(g) for g in groups])
        self.assertFalse(groups[0]&groups[1] or groups[0]&groups[2] or groups[1]&groups[2])
        self.assertFalse(set(f48.FORBIDDEN)&set.union(*groups))
        self.assertTrue(all(s%6 in (4,5) for s in groups[1]))
        self.assertTrue(all(s%6 in (0,1,2,3) for s in groups[0]|groups[2]))
        with self.assertRaisesRegex(ValueError,"UNAUTHORIZED_EVALUATION_OR_FIRST_USE"):
            f48.episode(59,0,"stable-working-reset",self.fit)
        with self.assertRaisesRegex(ValueError,"FORBIDDEN_OR_UNAUTHORIZED_WORLD"):
            f48.World(59,0,switching=True)
        with self.assertRaisesRegex(ValueError,"F48_USAGE"):
            f48.main([])
        for seed in f48.FIT:
            start,goal=f48.task(seed,0)
            self.assertNotEqual(start,goal)


if __name__=="__main__":
    unittest.main(verbosity=2)
