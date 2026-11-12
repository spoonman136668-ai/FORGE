"""Q18 frozen source-free graph rewiring and causal-structure tests."""
import math
import pathlib
import unittest
import experiment as q


class Q18RewiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=q.protocol()

    def test_two_fit_and_two_development_topologies_not_reused(self):
        d=self.p["data"]
        self.assertEqual([x["name"] for x in d["fit_templates"]],
                         list(q.FIT_TEMPLATES))
        self.assertEqual([x["name"] for x in d["dev_templates"]],
                         list(q.DEV_TEMPLATES))
        self.assertTrue(set(q.FIT_TEMPLATES).isdisjoint(q.DEV_TEMPLATES))

    def test_train_dev_roles_and_holdouts(self):
        fit=q.make_episodes("fit",self.p)
        dev=q.make_episodes("dev",self.p)
        self.assertEqual(len(fit),320)
        self.assertEqual(len(dev),128)
        self.assertNotEqual(q.digest(fit),q.digest(dev))
        self.assertEqual(q.digest(fit),q.digest(q.make_episodes("fit",self.p)))

    def test_all_reserved_held_original_roles_fail_before_rng(self):
        for role in ("HELD5_BRANCHING","HELD5_REVERSED_ROLE",
                     "held","original","scientific"):
            with self.subTest(role=role):
                with self.assertRaisesRegex(RuntimeError,
                                            "PROTECTED_HELD_OR_ORIGINAL_GENERATION"):
                    q.make_episodes(role,self.p)

    def test_public_observations_have_no_latent_edge_labels(self):
        for ep in q.make_episodes("fit",self.p)[:64]:
            name,n,edges,counts,y=ep
            self.assertIn(name,q.FIT_TEMPLATES)
            self.assertEqual(len(edges),len(counts))
            self.assertTrue(all(type(k)==int and 0<=k<=12 for k in counts))
            self.assertTrue(y in (0,1))
            self.assertEqual(len(ep),5)
            self.assertIsInstance(edges,tuple)

    def test_diamond_causal_path_decomposition(self):
        es=((0,1),(0,2),(1,3),(2,3))
        self.assertEqual(q.graph_paths(4,es),((0,2),(1,3)))
        self.assertTrue(q.reach(4,es,(1,0,1,0)))
        self.assertTrue(q.reach(4,es,(0,1,0,1)))
        self.assertFalse(q.reach(4,es,(1,0,0,1)))

    def test_public_edge_order_does_not_change_true_reachability(self):
        es=((0,1),(1,2),(2,3),(0,2))
        self.assertTrue(q.reach(4,es,(0,0,1,1)))
        self.assertFalse(q.reach(4,es,(0,1,1,0)))
        self.assertEqual(q.enumerate_reach(4,es,(.5,.5,.5,.5)),5/16)

    def test_probabilistic_reach_exact_at_extreme_edge_probabilities(self):
        es=((0,1),(0,2),(1,3),(2,3))
        self.assertEqual(q.enumerate_reach(4,es,(1.,0.,1.,0.)),1.)
        self.assertEqual(q.enumerate_reach(4,es,(1.,0.,0.,1.)),0.)
        self.assertAlmostEqual(q.enumerate_reach(4,es,(.5,.5,.5,.5)),
                               7/16)

    def test_shared_edge_scoring_respects_skeleton_rewiring(self):
        ep=("DEV4_DIAMOND",4,((0,1),(0,2),(1,3),(2,3)),
            (12,0,12,0),1)
        r=q.predict(q.CAND,(8.,-1.),ep)
        rewired=(ep[0],ep[1],ep[2],(0,12,12,0),ep[4])
        changed=q.predict(q.CAND,(8.,-1.),rewired)
        self.assertGreater(r,changed)

    def test_all_empirical_comparators_see_same_events(self):
        ep=q.make_episodes("fit",self.p)[0]
        examples=[(q.CAND,[2.,-1.]),(q.FLAT,[.1]*7),
                  (q.RNN,[.1]*11),
                  (q.SYM,{"threshold":8,"p_yes":.9,"p_no":.1}),
                  (q.ORACLE,None)]
        for name,model in examples:
            with self.subTest(model=name):
                value=q.predict(name,model,ep)
                self.assertTrue(math.isfinite(value))
                self.assertTrue(0<value<1)

    def test_oracle_probability_monotone_with_edge_evidence(self):
        self.assertLess(q.oracle_edge_posterior(3),
                        q.oracle_edge_posterior(9))
        self.assertGreater(q.oracle_edge_posterior(12),.9)

    def test_all_ablations_leave_truth_labels_unchanged(self):
        dev=q.make_episodes("dev",self.p)
        orig_labels=[ep[4] for ep in dev]
        shuffled=[(*ep[:3],ep[3][1:]+ep[3][:1],ep[4]) for ep in dev]
        self.assertEqual(orig_labels,[ep[4] for ep in shuffled])
        self.assertNotEqual(q.digest(dev),q.digest(shuffled))

    def test_frozen_protocol_no_original_science(self):
        self.assertTrue(self.p["safeguards"]["no_original_scientific_first_use"])
        self.assertTrue(self.p["safeguards"]["no_controller_dispatch_or_unpause"])
        self.assertTrue(self.p["safeguards"]["unfamiliar_five_node_held_unopened"])
        self.assertEqual(self.p["frozen_gate"]["decision_failure"],
                         "DEV_NO_GO_RETAIN_NEGATIVE_NO_HELD")
        self.assertEqual(self.p["fit"]["restarts"],[0,1])

    def test_no_original_engines_or_live_network(self):
        source=pathlib.Path(q.__file__).read_text().lower()
        for word in ("import minigrid","import pycolab","import requests",
                     "import subprocess","import socket","import cloudflare",
                     "import urllib","import github"):
            self.assertNotIn(word,source)


if __name__=="__main__":
    unittest.main()
