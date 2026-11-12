"""F53 structural FIT-only controls. NEVER access fresh F53 DEV episode seeds."""
import unittest
import numpy as np

import f51_original_acrobot_transfer_dev as f51
import f53_original_acrobot_supported_residual_dev as f53


class FrozenOriginalF53Source(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fit=f53.frozen_fit()  # Only original public F51 book training seeds.

    def test_source_and_previous_fit_exact(self):
        self.assertEqual(self.fit["source"]["upstream_commit"],f51.ORIGINAL_COMMIT)
        self.assertEqual(self.fit["source"]["acrobot_git_blob"],f51.ORIGINAL_FILE_BLOB)
        self.assertEqual(self.fit["fit_record_sha256"],f53.ORIGINAL_F51_FIT_SHA256)
        self.assertEqual(self.fit["fit_steps"],8974)
        self.assertEqual(self.fit["fit_action_counts"],[3604,1824,3546])
        self.assertEqual(self.fit["fit_episodes"],48)

    def test_all_frozen_cohorts_disjoint(self):
        f53.validate_cohorts()
        historic=set((*f51.FIT,*f51.TRANSFER,*f51.RETENTION,*f51.FORBIDDEN))
        self.assertFalse(set((*f53.TRANSFER,*f53.RETENTION)) & historic)
        self.assertEqual(len((*f53.TRANSFER,*f53.RETENTION)),24)

    def test_calibration_finite_and_strictly_positive(self):
        b=self.fit
        self.assertEqual(b["theta"].shape,(3,15))
        self.assertEqual(b["inverses"].shape,(3,15,15))
        self.assertEqual(b["thresholds"].shape,(3,))
        self.assertTrue(np.all(np.isfinite(b["inverses"])))
        self.assertTrue(np.all(b["thresholds"]>0))
        self.assertEqual(f53.MARGIN,4.0)
        self.assertEqual(f53.SUPPORT_QUANTILE,.90)

    def test_determinism_on_fit_public_observation(self):
        obs=np.asarray([1.,0.,1.,0.,0.,.1])
        b=self.fit
        for arm in f53.ARMS:
            x=f53.SupportedPolicy(arm,b["theta"],b["inverses"],b["thresholds"])
            y=f53.SupportedPolicy(arm,b["theta"],b["inverses"],b["thresholds"])
            self.assertEqual(x.action(obs),y.action(obs))
            self.assertEqual(x.snapshot()["decisions"],1)
            self.assertEqual(y.snapshot()["decisions"],1)

    def test_insufficient_advantage_falls_back_to_momentum(self):
        b=self.fit
        zero=np.zeros((3,15),dtype=np.float64)
        pos=np.asarray([1.,0.,1.,0.,0.,-.1])
        neg=np.asarray([1.,0.,1.,0.,0.,+.1])
        for arm in ("supported-residual","margin-only","rotated-credit"):
            for obs in (pos,neg):
                p=f53.SupportedPolicy(arm,zero,b["inverses"],b["thresholds"])
                self.assertEqual(p.action(obs),f51.energy_rule(obs))
                self.assertEqual(p.momentum_disagreements,0)

    def test_existing_policy_comparators_same_fqi_base(self):
        b=self.fit
        obs=np.asarray([1.,0.,1.,0.,0.,.1])
        for kind in f53.CONVENTIONAL:
            p=f53.SupportedPolicy(kind,b["theta"],b["inverses"],b["thresholds"])
            original=f51.Policy(kind,b["theta"])
            self.assertEqual(p.action(obs),original.action(obs))
            self.assertTrue(np.array_equal(p.theta,b["theta"]))

    def test_reject_all_unapproved_and_original_scored_seeds(self):
        b=self.fit
        for seed in (59,83,*f51.TRANSFER,*f51.RETENTION,43011):
            with self.subTest(seed=seed):
                with self.assertRaises(ValueError):
                    f53.evaluate(seed,"nips","supported-residual",
                                 b["theta"],b["inverses"],b["thresholds"])

    def test_original_book_training_source_smoke(self):
        # Original external source, familiar FIT episode only; NO F53 scored seed.
        env=f51.new_real_env("book")
        try:
            obs,_=env.reset(seed=f51.FIT[0]*100)
            for _ in range(20):
                a=f51.energy_rule(obs)
                obs,reward,ended,truncated,_=env.step(a)
                self.assertEqual(len(obs),6)
                self.assertTrue(np.all(np.isfinite(obs)))
                self.assertTrue(np.isfinite(reward))
                if ended or truncated:
                    break
        finally:
            env.close()


if __name__=="__main__":
    unittest.main()
