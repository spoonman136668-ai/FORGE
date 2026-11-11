"""F46 FIT-only structural and first-use negative tests, not transfer evaluation."""
import inspect
import json
import unittest

import f46_causal_information_dev as f46


class F46Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fit_worlds, cls.coverage = f46.collect_training()
        cls.model = f46.fit_shared(cls.fit_worlds)

    def test_frozen_training_only_transcript_and_actual_actions(self):
        self.assertEqual(8,len(self.fit_worlds))
        self.assertEqual(640,sum(len(w) for w in self.fit_worlds))
        self.assertEqual(640,sum(self.coverage))
        self.assertTrue(all(n>0 for n in self.coverage))
        self.assertEqual((3,3,3,3,1,1),tuple(self.model["fit_mode_counts"]))
        self.assertEqual(4,self.model["identified_mode_types"])
        self.assertEqual(14,sum(self.model["fit_mode_counts"]))
        self.assertEqual(self.model,json.loads(f46.canonical(self.model)))
        self.assertEqual(f46.digest(self.fit_worlds),f46.digest(f46.collect_training()[0]))

    def test_six_hidden_worlds_and_live_causal_consequences(self):
        for mode in range(6):
            world=f46.CausalWorld(2100+mode,0,3)
            initial=world.state
            next_state,reward,done=world.step(0)
            self.assertEqual(initial ^ f46.EFFECTS[mode][0],next_state)
            self.assertEqual((9 if next_state==3 else -1),reward)
            self.assertEqual(next_state==3,done)
            with self.assertRaisesRegex(ValueError,"INVALID_PUBLIC_TASK"):
                f46.CausalWorld(2100+mode,0,0)
        self.assertEqual(["self","kind","fit","episode"],
                         list(inspect.signature(f46.Policy.__init__).parameters))
        self.assertEqual(["self","state","goal"],
                         list(inspect.signature(f46.Policy.action).parameters))

    def test_info_gain_and_goal_conditional_prevention_of_free_probes(self):
        p=self.model["prior"]
        self.assertAlmostEqual(1.0,sum(p),places=12)
        self.assertEqual(0.0,f46.info_gain(p,2))
        self.assertGreater(f46.info_gain(p,0),0.0)
        self.assertGreater(f46.info_gain(p,1),0.0)
        for kind in f46.ARMS:
            model=f46.Policy(kind,self.model,2)
            self.assertIn(model.action(0,3),(0,1,2))
            self.assertEqual(0,model.observations)

    def test_exact_bayesian_filter_and_wrong_credit_negative(self):
        p=self.model["prior"]
        observed_effect=f46.EFFECTS[0][0]
        after=f46.update(p,0,observed_effect)
        self.assertAlmostEqual(1.0,sum(after))
        self.assertTrue(all(prob==0.0 for m,prob in enumerate(after)
                            if f46.EFFECTS[m][0]!=observed_effect))
        wrong=f46.update(p,0,observed_effect,corrupt=True)
        self.assertNotEqual(after,wrong)
        active=f46.Policy("active-information",self.model,0)
        nofeed=f46.Policy("no-feedback",self.model,0)
        active.observe(0,0,observed_effect)
        nofeed.observe(0,0,observed_effect)
        self.assertEqual(after,active.probs)
        self.assertEqual(p,nofeed.probs)
        self.assertGreater(active.changes,0)
        with self.assertRaisesRegex(ValueError,"IMPOSSIBLE_OBSERVED"):
            f46.update(p,2,1)

    def test_preregistered_train_transfer_retention_seeds_disjoint(self):
        a,b,c=set(f46.FIT),set(f46.TRANSFER),set(f46.RETENTION)
        self.assertEqual((8,24,8),(len(a),len(b),len(c)))
        self.assertFalse(a&b or b&c or a&c)
        self.assertFalse({59,83}&(a|b|c))
        self.assertTrue(all(seed%6 in (0,1,2,3) for seed in a|c))
        self.assertTrue(all(seed%6 in (4,5) for seed in b))
        for seed in a|b|c:
            for episode in range(4):
                start,goal=f46.task(seed,episode)
                self.assertNotEqual(start,goal)
        with self.assertRaisesRegex(ValueError,"EVALUATION_SEED_NOT_FROZEN"):
            f46.evaluate_episode(59,0,"active-information",self.model)
        with self.assertRaisesRegex(ValueError,"EVALUATION_SEED_NOT_FROZEN"):
            f46.evaluate_episode(2300,0,"active-information",self.model)

    def test_unknown_policy_invalid_world_and_usage_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"UNKNOWN_POLICY"):
            f46.Policy("oracle_mode_lookup",self.model,0)
        with self.assertRaisesRegex(ValueError,"INVALID_REAL_WORLD_STEP"):
            f46.CausalWorld(2100,0,3).step(4)
        with self.assertRaisesRegex(ValueError,"INVALID_REAL_WORLD_STEP"):
            f46.CausalWorld(2100,0,3).step(True)
        with self.assertRaisesRegex(ValueError,"F46_USAGE"):
            f46.main([])
        self.assertEqual(8,len(f46.ARMS))
        self.assertEqual(4,len(f46.CONVENTIONAL))
        self.assertEqual(("wrong-credit","no-feedback"),f46.NEGATIVES)


if __name__=="__main__":
    unittest.main(verbosity=2)
