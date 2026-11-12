"""Q19B frozen anonymous finite interventions, supervised controls, custody."""
import math
import pathlib
import unittest

import experiment as q


class Q19BTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=q.load()
        cls.fit=q.generate("fit",cls.p)
        cls.dev=q.generate("development",cls.p)

    def test_protocol_pin_and_frozen_training(self):
        self.assertEqual(q.FROZEN_BLOB,
                         "b6d4bd82e96355fba92be48b2b5d6425141b2195")
        self.assertEqual(self.p["fit"]["epochs"],20)
        self.assertEqual(self.p["fit"]["restarts"],[0,1])
        self.assertEqual(len(q.ALL),6)

    def test_train_and_dev_family_distinctness(self):
        self.assertEqual(len(self.fit),480)
        self.assertEqual(len(self.dev),288)
        self.assertEqual({r[0] for r in self.fit},{"FIT_ANON1","FIT_ANON2"})
        self.assertEqual({r[0] for r in self.dev},{"DEV_ANON3","DEV_ANON4"})
        self.assertNotEqual(q.hash_cohort(self.fit),q.hash_cohort(self.dev))

    def test_finite_sourcefree_replay_is_deterministic(self):
        self.assertEqual(q.hash_cohort(self.fit),
                         q.hash_cohort(q.generate("fit",self.p)))
        self.assertEqual(q.hash_cohort(self.dev),
                         q.hash_cohort(q.generate("development",self.p)))

    def test_all_held_original_roles_denied_before_generation(self):
        for role in ("held","HELD_4NODE_CHAIN","HELD_4NODE_FORK",
                     "scientific","original",""):
            with self.subTest(role=role):
                with self.assertRaisesRegex(RuntimeError,
                                            "HELD_OR_ORIGINAL_ROLE_DENIED"):
                    q.generate(role,self.p)

    def test_six_public_do_actions_with_six_repetitions(self):
        for row in (self.fit[0],self.fit[-1],self.dev[0]):
            self.assertEqual(len(row[3]),36)
            for i in range(3):
                for action in (0,1):
                    self.assertEqual(sum(ev[0]==i and ev[1]==action
                                         for ev in row[3]),6)
            self.assertTrue(all(ev[2][ev[0]]==ev[1] for ev in row[3]))
            self.assertEqual(q.extract(row[3]),row[1])

    def test_training_rows_have_only_public_evidence_and_target(self):
        for family,features,labels,events in self.fit[:15]:
            self.assertIn(family,("FIT_ANON1","FIT_ANON2"))
            self.assertEqual(len(features),6)
            self.assertEqual(len(labels),6)
            self.assertTrue(all(y in (0,1) for y in labels))
            self.assertTrue(all(0<=a<=6 and 0<=b<=6 for a,b in features))
            self.assertEqual(len(events),36)

    def test_permuted_scms_interventions_are_clamped(self):
        for kind in q.STRUCTURES:
            for perm in q.PERMS:
                for slot in range(3):
                    for action in (0,1):
                        out=q.simulate(kind,perm,1,0,1,(slot,action))
                        self.assertEqual(out[slot],action)
                        self.assertEqual(len(out),3)

    def test_chain_and_fork_ancestor_ground_truth(self):
        self.assertEqual(q.ancestor_labels("chain",(0,1,2)),
                         (1,1,0,1,0,0))
        self.assertEqual(q.ancestor_labels("fork",(0,1,2)),
                         (0,0,1,1,0,0))
        self.assertEqual(len({q.ancestor_labels(k,p)
                              for k in q.STRUCTURES for p in q.PERMS}),9)

    def test_all_empirical_models_finite_with_same_pair_counts(self):
        row=self.fit[13]
        models=[
          (q.CAND,[1.,-.5]),
          (q.FLAT,[0.,.2,.5]*6),
          (q.RNN,[.3,.2,.3,0.,1.,0.]),
          (q.BAYES,{"mean":[0.,.4],"var":[.1,.1],"prior":.4}),
          (q.SYM,{"threshold":2,"positive":.9,"negative":.1}),
        ]
        for name,p in models:
            with self.subTest(model=name):
                pred=q.estimates(name,p,row)
                self.assertEqual(len(pred),6)
                self.assertTrue(all(math.isfinite(v) and 0<v<1
                                    for v in pred))

    def test_gaussian_bayes_estimates_from_fit_only(self):
        p,cost=q.train_bayes(self.fit)
        self.assertGreater(p["prior"],0)
        self.assertLess(p["prior"],1)
        self.assertTrue(all(v>=1/36 for v in p["var"]))
        self.assertTrue(cost["fitted_from_labels_only"])

    def test_symbolic_threshold_fit_uses_supervised_fits(self):
        p,cost=q.train_symbolic(self.fit)
        self.assertGreaterEqual(p["threshold"],-6)
        self.assertLessEqual(p["threshold"],6)
        self.assertEqual(cost["threshold_candidates"],13)

    def test_ancestor_posterior_oracle_is_labeled_privileged(self):
        self.assertTrue(self.p["trained_controls"]["oracle"]
                        ["source_law_privilege"])
        self.assertFalse(self.p["trained_controls"]["bayes"]
                         ["source_law_privilege"])
        x=q.oracle(self.dev[0],self.p)
        self.assertEqual(len(x),6)
        self.assertTrue(all(0<=v<=1 for v in x))

    def test_permuted_causal_order_is_not_supplied_to_learners(self):
        source=pathlib.Path(q.__file__).read_text().lower()
        self.assertNotIn("perm",q.estimates.__code__.co_varnames)
        self.assertNotIn("structure",q.estimates.__code__.co_varnames)
        for forbidden in ("import minigrid","import pycolab",
                          "import requests","import socket",
                          "import subprocess","import cloudflare"):
            self.assertNotIn(forbidden,source)

    def test_dev_never_used_in_fit_gradient(self):
        self.assertEqual(self.p["cohorts"]["no_dev_gradient_updates"],True)
        self.assertEqual(self.p["decision"]["fail"],
                         "DEV_NO_GO_RETAIN_NEGATIVE_NO_HELD")
        self.assertFalse(self.p["guardrails"]["held_generation_allowed"])


if __name__=="__main__":
    unittest.main()
