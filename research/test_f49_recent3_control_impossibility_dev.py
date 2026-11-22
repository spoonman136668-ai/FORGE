"""F49 control failure diagnosis: FIT-only synthetic public evidence, no DEV scoring.

This captures why the authentic one-shot runtime blocked: a single-mode recent3
window cannot represent a latent mode switch even though each action outcome is
individually physically supported by a legitimate mode and fixed 20% noise.
F49 original candidate, protocol, seeds and scoring remain unchanged.
"""
import inspect
import unittest

import f49_noise_aware_changepoint_dev as f49


class F49Recent3NegativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fit_worlds, cls.coverage=f49.collect_fit()
        cls.fit=f49.fit_model(cls.fit_worlds)

    def test_source_grounded_disjoint_action_effect_hypotheses(self):
        # Under pending physical action 0, effects 1 and 2 correspond to
        # mutually exclusive latent mode classes; XOR residual 3 cannot arise
        # from the source's one-bit noise support (0,1,2,4).
        a=[m for m in range(6) if f49.likelihood(m,0,1,-1,sensor_applied=False)>0]
        b=[m for m in range(6) if f49.likelihood(m,0,2,-1,sensor_applied=False)>0]
        self.assertEqual([0,1],a)
        self.assertEqual([2,3],b)
        self.assertEqual(set(),set(a)&set(b))
        self.assertEqual(6,len(f49.EFFECTS))

    def test_recent3_fails_closed_when_two_physical_effects_cross_modes(self):
        f=f49.Policy("recent3-bayes",self.fit)
        f.observe(0,0,0,1,-1)
        with self.assertRaisesRegex(ValueError,"F49_IMPOSSIBLE_CAUSAL_OBSERVATION"):
            f.observe(0,0,0,2,-1)
        self.assertEqual(2,f.observations)
        # Not a privileged environment call, not a true-source revelation.

    def test_switching_hmm_and_hazard_control_admit_new_modes(self):
        for kind in ("switching-hmm-bayes","fixed-hazard-bayes"):
            f=f49.Policy(kind,self.fit)
            f.observe(0,0,0,1,-1)
            f.observe(0,0,0,2,-1)
            self.assertEqual(2,f.observations)
            self.assertAlmostEqual(1.0,sum(f.working),places=12)
            self.assertTrue(any(x>0 for x in f.working))

    def test_custody_no_scored_seeds_and_public_observations_only(self):
        self.assertEqual(1152,sum(len(ep) for w in self.fit_worlds for ep in w))
        self.assertEqual([480,384,288],self.coverage)
        self.assertFalse(set(f49.FIT)&set(f49.TRANSFER))
        self.assertFalse(set(f49.FIT)&set(f49.RETENTION))
        self.assertFalse(set(f49.FIT)&set(f49.FORBIDDEN))
        self.assertEqual(["self","old","pending","requested","nxt","witness"],
            list(inspect.signature(f49.Policy.observe).parameters))
        with self.assertRaisesRegex(ValueError,"UNAUTHORIZED_DEV_OR_PROTECTED"):
            f49.episode(59,0,"recent3-bayes",self.fit)


if __name__=="__main__":
    unittest.main(verbosity=2)
