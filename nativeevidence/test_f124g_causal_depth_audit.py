"""F124-G source-pinned TRAIN causal retrieval and depth diagnostics."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f124g_causal_depth_audit as a
import f124f_public_graph_source as source
import f124f_conditional_memory as model

class F124GScientificBoundary(unittest.TestCase):
    def pair(self):
        return source.build(160000,[1,1,2],"Wingless","TRAIN")

    def test_pinned_frozen_source_and_untouched_originals(self):
        a.source_identity()
        self.assertEqual(a.BASE_SHA,"25e6f7c900ed37f3102b095a866ade467bbaeaf7")
        self.assertEqual(a.F124F_TRAIN_SHA,
          "4cf3bbd2338d62c595288c459fea066db674246964c6a582971f823454162350")
        self.assertEqual(a.F124F_MODEL_BLOB,
                         "30b50f9500a7905378b53613280658b1b95c9a29")

    def test_exact_forward_replay_at_frozen_threshold(self):
        pos,neg=self.pair()
        for arm in ("A","B"):
            w=model.initial(arm)
            for obs in (pos,neg):
                score=model.forward(obs,w,arm)[0]
                x=a.witness(obs,w,arm)
                self.assertAlmostEqual(score,x["score"],places=12)
                self.assertEqual(len(x["byhop"]),len(obs["roles"]))
                self.assertEqual(x["score"]>=.5,
                                 score>=.5)
                self.assertTrue(x["causal_target_records"] in (0,1))
            self.assertEqual(a.witness(neg,w,arm)["causal_target_records"],0)

    def test_public_causal_reference_is_scorer_only(self):
        p,n=self.pair()
        true_path=a.public_true_path(p)
        self.assertEqual(len(true_path),len(p["roles"]))
        self.assertEqual(source.public_routes(p),1)
        self.assertEqual(source.public_routes(n),0)
        with self.assertRaises(source.Invalid):
            a.public_true_path(n)
        for arm in ("A","B"):
            metrics=a.causal_deletion(p,model.initial(arm),arm)
            self.assertTrue(metrics["causal_deletion_truth_invalidates_route"])
            self.assertTrue(metrics["distractor_deletion_keeps_route"])
            self.assertTrue(isinstance(metrics["true_join_edge_score_drop"],float))

    def test_query_priority_ablation_does_not_mutate_models(self):
        p,_=self.pair()
        for arm in ("A","B"):
            weights=model.initial(arm)
            original=list(weights)
            with_query=a.witness(p,weights,arm)
            no_query=a.witness(p,weights,arm,query_priority=False)
            self.assertAlmostEqual(with_query["score"],
                                   model.forward(p,weights,arm)[0],places=12)
            self.assertAlmostEqual(no_query["score"],
                model.forward(p,weights,arm,query_priority=False)[0],places=12)
            self.assertEqual(weights,original)

    def test_posthoc_threshold_is_disallowed_scientifically(self):
        rows=[{"positive":.7,"negative":.6},{"positive":.3,"negative":.2}]
        out=a.oracle_threshold(rows)
        self.assertEqual(out["original_frozen_decision_threshold"],.5)
        self.assertTrue(out["not_eligible_for_acceptance"])
        self.assertEqual(out["label_informed_train_oracle_upper_bound_pairs"],1)

    def test_public_fields_and_reserved_cases_fail_closed(self):
        p,_=self.pair()
        for k in ("oracle","truth","chosen_route","changed_edge"):
            bad=copy.deepcopy(p)
            bad[k]=1
            with self.subTest(k=k),self.assertRaises(source.Invalid):
                a.witness(bad,model.initial("A"),"A")
        with self.assertRaises(source.Invalid):
            source.build(160100,[1,1,2],"Wingless","CONFIRM")
        with self.assertRaises(source.Invalid):
            a.witness(p,model.initial("B")[:-1],"B")
        self.assertFalse(set(source.TRAIN["Yggdrasil"]) &
                         set(source.RESERVED_CONFIRM["Yggdrasil"]))

    def test_reject_forged_immutable_train_receipt(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"fraud.json"
            p.write_text("{}")
            with self.assertRaisesRegex(source.Invalid,
                                        "IMMUTABLE_TRAIN_RECEIPT_DRIFT"):
                a.read_train_receipt(p)

if __name__=="__main__":
    unittest.main()
