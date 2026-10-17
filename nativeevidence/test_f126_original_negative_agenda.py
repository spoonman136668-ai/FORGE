"""F126 original scientific-source negative -> autonomous agenda safety tests."""
from __future__ import annotations
import copy
from decimal import Decimal
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import f126_original_negative_agenda as m

class OriginalNegativeQualification(unittest.TestCase):
    def test_preregistered_source_and_scientific_denials(self):
        p,d=m.freeze()
        self.assertEqual(m.f118.gitblob(m.FREEZE.read_bytes().replace(b"\r\n",b"\n")),m.BLOB)
        self.assertTrue(all(p["authority"].values()))
        self.assertEqual(len(d),64)
        self.assertEqual([r["id"] for r in p["originals"]],["F116-O","F117-O"])

    def test_integer_heldout_balanced_accuracy_consistency(self):
        one={"n":73,"positive":48,"negative":25,
             "tp":45,"fn":3,"tn":10,"fp":15,
             "both_classes_present":True,"balanced_accuracy":0.66875}
        self.assertEqual(m.metric(one),668750)
        two={"n":1111,"positive":251,"negative":860,
             "tp":215,"fn":36,"tn":476,"fp":384,
             "both_classes_present":True,"balanced_accuracy":0.705031}
        self.assertEqual(m.metric(two),705031)
        two["balanced_accuracy"]=0.95
        with self.assertRaisesRegex(m.Blocked,"INCONSISTENT_BALANCED"):
            m.metric(two)

    def test_largest_real_loss_selects_shared_node_binding(self):
        rows=[{"experiment":"F116-O","unrecovered_loss_millionths":38333,
               "has_unconnected_pairwise_witnesses":False},
              {"experiment":"F117-O","unrecovered_loss_millionths":205031,
               "has_unconnected_pairwise_witnesses":True}]
        result=m.choose_next(rows)
        self.assertEqual(result["source_experiment"],"F117-O")
        self.assertEqual(result["mechanism_problem"],"SHARED_NODE_BINDING")
        self.assertEqual(result["priority_gap_millionths"],205031)

    def test_counterfactual_different_real_evidence_changes_idea(self):
        rows=[{"experiment":"F116-O","unrecovered_loss_millionths":300000,
               "has_unconnected_pairwise_witnesses":False},
              {"experiment":"F117-O","unrecovered_loss_millionths":205031,
               "has_unconnected_pairwise_witnesses":True}]
        self.assertEqual(m.choose_next(rows)["mechanism_problem"],
                         "ROLE_MARGINAL_SHORTCUT")
        rows[0]["unrecovered_loss_millionths"]=-1
        with self.assertRaises(m.Blocked):
            m.choose_next(rows)

    def test_exact_joint_graph_vs_separate_pair_existence(self):
        for seed in (130000,130007,130100,130131):
            for variant in (0,1):
                g=m.build_pair(seed,"SHARED_NODE_BINDING",variant)
                self.assertTrue(m.connected(g["positive"],g["start"],g["target"],g["roles"]))
                self.assertFalse(m.connected(g["negative"],g["start"],g["target"],g["roles"]))
                self.assertTrue(m.adjacent_global(g["positive"],g["roles"]))
                self.assertTrue(m.adjacent_global(g["negative"],g["roles"]))
                pos=sorted([edge[1] for edge in g["positive"]])
                neg=sorted([edge[1] for edge in g["negative"]])
                self.assertEqual(pos,neg)
                self.assertEqual(m.score_pair(g)["pairwise_existence_paired_correct"],0)

    def test_disjoint_graphs_and_no_after_the_fact_tuning(self):
        rows=[m.evaluate("SHARED_NODE_BINDING",i,"TRAIN") for i in (0,1)]
        confirm=m.evaluate("SHARED_NODE_BINDING",0,"CONFIRM")
        self.assertEqual([x["cases"] for x in rows],[8,8])
        self.assertEqual(confirm["cases"],32)
        self.assertEqual(confirm["exact_oracle_paired_correct"],32)
        self.assertEqual(confirm["pairwise_shortcut_paired_correct"],0)
        self.assertEqual(confirm["role_only_paired_correct"],0)
        self.assertNotEqual(rows[0]["source_sha256"],confirm["source_sha256"])

    def test_duplicate_keys_and_nonfinite_fail_closed(self):
        with self.assertRaisesRegex(m.Blocked,"DUPLICATE_JSON"):
            m.strict(b'{"x":1,"x":2}')
        with self.assertRaisesRegex(m.Blocked,"NONFINITE_JSON"):
            m.strict(b'{"x":NaN}')

    def test_historical_run_mismatch_fails_closed(self):
        p,_=m.freeze()
        s=p["originals"][0]
        inputs={"run":{"id":s["run_id"],"event":"workflow_dispatch",
                       "status":"completed","conclusion":"success"},
                "artifact_metadata":{"total_count":0,"artifacts":[]}}
        with self.assertRaisesRegex(m.Blocked,"ORIGINAL_RUN"):
            m.sealed_run(inputs,s,p["source_graph"])

    def test_fake_zip_digest_or_missing_os_fails_closed(self):
        p,_=m.freeze()
        s=p["originals"][0]
        identity={"id":s["run_id"],"event":"push",
                  "head_sha":s["head"],"path":s["workflow"],
                  "head_branch":s["branch"],"run_attempt":1,
                  "repository":{"full_name":"spoonman136668-ai/FORGE"},
                  "head_repository":{"full_name":"spoonman136668-ai/FORGE"},
                  "status":"completed","conclusion":"success"}
        bad={"run":identity,"artifact_metadata":{"total_count":0,"artifacts":[]}}
        with self.assertRaisesRegex(m.Blocked,"PINNED_ARTIFACT_ZIP"):
            m.sealed_run(bad,s,p["source_graph"])

if __name__=="__main__":
    unittest.main()
