"""F124-BM nonconsuming original source/protocol gates and scored-outcome integrity.

NO registered BM source make() call except invalid protected ID denial.
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,HERE/path)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


birth=load("f124bm_source_witness_test","f124bm_source_witness.py")
eval=load("f124bm_original_pair_eval_test","f124bm_fit_eval.py")
gf=load("f124bm_new_gf2_test","f124bm_gf2_source.py")
ar=load("f124bm_new_arx_test","f124bm_arx_source.py")


class PrerequisiteTests(unittest.TestCase):
    def test_original_commit_chronology_without_FIT(self):
        r=birth.verify(provider=False)
        self.assertEqual(len(r["birth_receipts"]),3)
        self.assertEqual(r["FIT_or_protected_records_generated"],0)
        self.assertFalse(r["external_thirdparty_scientific_origin"])
        self.assertFalse(r["scientific_acceptance"])

    def test_strict_original_id_independence(self):
        self.assertTrue(set(gf.FIT).isdisjoint(ar.FIT))
        self.assertTrue(set(gf.FIT).isdisjoint(gf.HOLDOUT))
        self.assertTrue(set(ar.FIT).isdisjoint(ar.HOLDOUT))
        for mod in (gf,ar):
            for seed in (900000,901000,902000,903000,914100,915100,
                         914227,915227,-940,-939):
                with self.assertRaises(ValueError):
                    mod.make(seed)
        for seed in (902000,903000,914100,915100):
            with self.assertRaises(RuntimeError):
                eval.source_for(seed)

    def test_same_source_and_original_policies_immutably_pinned(self):
        self.assertEqual(eval.git_blob(
            eval.HERE/"20261018-mass-learned-kernel.py"),eval.T1)
        self.assertEqual(eval.git_blob(
            eval.NATIVE/"f124az_joint_public_inverse.py"),eval.AZ)
        self.assertEqual(eval.git_blob(
            eval.NATIVE/"f124ag_transition_models.py"),eval.NATIVE_SHA)
        self.assertEqual(eval.git_blob(
            eval.HERE/"f124bm_gf2_source.py"),eval.SOURCE_BLOBS["GF2"])
        self.assertEqual(eval.git_blob(
            eval.HERE/"f124bm_arx_source.py"),eval.SOURCE_BLOBS["ARX"])


class AggregatorRejectsShortcuts(unittest.TestCase):
    def rows(self):
        r=[]
        for family,seeds in (("GF2",eval.GF),("ARX",eval.ARX)):
            for seed in seeds:
                for arm in ("learned","AZ"):
                    r.append({
                        "seed":seed,"arm":arm,"source_family":family,
                        "same_public_and_graph_sha256":str(seed),
                        "private_symbolic_truth_only_for_evaluation":{
                            "positive_routes":1,"hard_negative_routes":0},
                        "positive_accepted":True,
                        "hard_negative_accepted":False,
                        "native_policy_trace":{"policy_abstained":False},
                        "task_CPU_ns":500,"whole_process_peak_RSS_bytes":8192,
                    })
        return r

    def test_retention_without_gain_cannot_pass(self):
        x=eval.aggregate(self.rows())
        self.assertFalse(x["FIT_gain_and_FP_constraints_met_in_both"])
        self.assertEqual(x["total_task_arm_evaluations"],64)
        self.assertFalse(x["scientific_out_of_distribution_accepted"])
        self.assertFalse(x["complete_equal_cost_science_proven"])

    def test_hard_negative_and_positive_regressions_rejected(self):
        x=self.rows()
        x[0]["positive_accepted"]=False
        x[0]["hard_negative_accepted"]=True
        y=eval.aggregate(x)
        self.assertIn(914000,y["families"]["GF2"]["baseline_positive_lost_ids"])
        self.assertIn(914000,y["families"]["GF2"]["candidate_hard_false_positive_ids"])
        self.assertFalse(y["FIT_gain_and_FP_constraints_met_in_both"])

    def test_rejects_mismatched_graph_and_partial_results(self):
        x=self.rows()
        x[1]["same_public_and_graph_sha256"]="DIFFERENT"
        with self.assertRaises(RuntimeError):
            eval.aggregate(x)
        with self.assertRaises(RuntimeError):
            eval.aggregate(self.rows()[:-1])


if __name__=="__main__":
    unittest.main()
