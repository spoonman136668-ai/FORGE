"""Q17B source-free frozen custody and causal-composition adversarial tests."""
import json
import math
import pathlib
import unittest

import experiment as q


class Q17BLearnedCausalCompositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.design=q.frozen()
        cls.fit=q.episodes("fit",cls.design)

    def test_frozen_protocol_and_comparators(self):
        self.assertEqual(q.PROTO_BLOB,
                         "7b09596afb9a3e2859f2de20e470c91416d94578")
        self.assertEqual(self.design["training"]["epochs"],24)
        self.assertEqual(self.design["training"]["restarts"],[0,1])
        self.assertEqual(len(q.KINDS),5)

    def test_only_composed_training_label_is_output(self):
        self.assertEqual(len(self.fit),256)
        for i, (events,y) in enumerate(self.fit):
            self.assertEqual(y,1 if i>=192 else 0)
            self.assertEqual(len(events),32)
            self.assertTrue(all(len(event)==3 for event in events))
            self.assertEqual(sum(event[0]==0 for event in events),16)
            self.assertEqual(sum(event[0]==1 for event in events),16)
            self.assertTrue(all(set(event).issubset({0,1}) for event in events))

    def test_frozen_roles_disjoint_replay(self):
        development=q.episodes("development",self.design)
        self.assertEqual(len(development),64)
        self.assertEqual(q.cohort_sha(development),
                         q.cohort_sha(q.episodes("development",self.design)))
        self.assertNotEqual(q.cohort_sha(development),
                            q.cohort_sha(self.fit))

    def test_no_reserved_unfamiliar_generation(self):
        for forbidden in ("held","Q17B_H3","Q17B_H4","scientific"):
            with self.subTest(role=forbidden):
                with self.assertRaisesRegex(RuntimeError,
                                            "HELD_OR_REAL_SOURCE_UNAUTHORIZED"):
                    q.episodes(forbidden,self.design)

    def test_all_models_receive_same_public_events(self):
        events,y=self.fit[193]
        arms=[
            (q.KINDS[0],[.2,.1,.3,.1]),
            (q.KINDS[1],[0.,.2,.1,.2]),
            (q.KINDS[2],[.1,.1,.1,0.,0.,.1,.1,.1,.1]),
            (q.KINDS[3],{"threshold_a":9,"threshold_b":9,
                         "p_true":.9,"p_false":.1}),
            (q.KINDS[4],None)
        ]
        for kind,params in arms:
            with self.subTest(kind=kind):
                prediction=q.probability(kind,params,events)
                self.assertTrue(0<prediction<1)
                self.assertTrue(math.isfinite(q.bce(prediction,y)))

    def test_oracle_edge_posterior_is_symmetric(self):
        count=(q.N,q.N)
        event=tuple([(0,0,0)]*q.N+[(1,0,0)]*q.N)
        self.assertEqual(q.counts(event),list(count))
        p=q.probability("ORACLE_BAYES_TWO_EDGE_POSTERIOR",None,event)
        self.assertGreater(p,.5)
        n=tuple([(0,0,1)]*q.N+[(1,0,1)]*q.N)
        self.assertLess(q.probability("ORACLE_BAYES_TWO_EDGE_POSTERIOR",
                                      None,n),.01)

    def test_candidate_factorization_is_genuine_product(self):
        events,_=self.fit[200]
        params=[.6,.2,.8,-.1]
        a,b=q.counts(events)
        score_a=q.sigmoid(params[0]*(2*a-q.N)/q.N+params[1])
        score_b=q.sigmoid(params[2]*(2*b-q.N)/q.N+params[3])
        self.assertAlmostEqual(
            q.probability("LEARNED_FACTORIZED_CAUSAL_EDGES",params,events),
            score_a*score_b,places=12)

    def test_independent_model_gradient_finite(self):
        data=self.fit[:4]
        for kind,params in [
            (q.KINDS[0],[.2,.1,.3,-.2]),
            (q.KINDS[1],[.2,.1,.2,.3]),
            (q.KINDS[2],[.1,.2,.3,0.,0.,.2,.3,.4,0.]),
        ]:
            with self.subTest(kind=kind):
                for index in range(len(params)):
                    plus=params.copy()
                    minus=params.copy()
                    plus[index]+=.0001
                    minus[index]-=.0001
                    grad=(q.average_loss(kind,plus,data)-
                          q.average_loss(kind,minus,data))/.0002
                    self.assertTrue(math.isfinite(grad))

    def test_train_only_symbolic_not_hardcoded_thresholds(self):
        p,cost=q.train_symbolic(self.fit)
        self.assertIn("threshold_a",p)
        self.assertIn("threshold_b",p)
        self.assertGreaterEqual(p["threshold_a"],0)
        self.assertLessEqual(p["threshold_a"],16)
        self.assertEqual(cost["grid_candidates"],289)
        self.assertGreater(p["p_true"],0)
        self.assertLess(p["p_false"],1)

    def test_model_inputs_do_not_expose_hidden_edge_labels(self):
        events,label=self.fit[0]
        self.assertIsInstance(events,tuple)
        self.assertIsInstance(label,int)
        self.assertTrue(all(isinstance(ev,tuple) and len(ev)==3
                            for ev in events))
        self.assertEqual(self.design["causal_world"]["training_labels"],
                         "only composed T available to all trained methods, NEVER the two edge existence labels")

    def test_no_external_origins_or_held_exposure_in_code(self):
        text=pathlib.Path(q.__file__).read_text(encoding="utf-8").lower()
        for denied in ("import minigrid","import pycolab","import requests",
                       "import urllib","import socket","import subprocess",
                       "import cloudflare","import github"):
            self.assertNotIn(denied,text)
        self.assertTrue(
            self.design["acceptance"]["no_claim_of_unfamiliar_task_transfer"])

    def test_source_only_and_negative_retention(self):
        self.assertTrue(self.design["acceptance"]["no_claim_of_unfamiliar_task_transfer"])
        self.assertTrue(self.design["acceptance"]["no_further_tuning_after_dev"])
        self.assertTrue(self.design["acceptance"]["no_original_scientific_execution"])
        self.assertEqual(
            self.design["acceptance"]["decision_failure"],
            "DEV_NO_GO_RETAIN_NEGATIVE_NO_HELD")


if __name__=="__main__":
    unittest.main()
