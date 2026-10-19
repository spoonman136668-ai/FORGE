"""F124-BL focused engineering tests; zero registered-source first use."""
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


native=load("f124bl_equal_native_test","f124bl_equal_native.py")
measure=load("f124bl_measure_test","f124bl_measure.py")


class NativeWorkCostTests(unittest.TestCase):
    def test_both_arms_execute_real_native_work_without_changing_original_policy(self):
        for tag in ("U","R"):
            original=native.evaluate("AZ_forced_diagnostic",tag)
            candidate=native.evaluate("learned",tag)
            self.assertEqual(original["same_public_48_sha256"],
                             candidate["same_public_48_sha256"])
            self.assertEqual(original["same_native_graph_sha256"],
                             candidate["same_native_graph_sha256"])
            witness=original["native_workload"]
            self.assertEqual(witness["original_AZ_policy_decision"],"abstain")
            self.assertFalse(witness["original_AZ_unmodified_native_execution"])
            self.assertFalse(witness["scientifically_admissible"])
            self.assertTrue(witness["forced_native_work"])
            self.assertFalse(witness["diagnostic_override_changes_AZ_policy"])
            for arm in (original,candidate):
                work=arm["native_workload"]["native_work"]
                self.assertEqual(arm["native_workload"]["native_graph_calls"],1)
                self.assertLessEqual(work["max_active"],7)
                self.assertLessEqual(work["max_retained"],9)
                self.assertFalse(arm["protected_validation_or_U_R_used"])
                self.assertFalse(arm["original_192_TRAIN_replayed"])
                self.assertFalse(arm["whole_resource_parity_qualified"])

    def test_unknown_model_or_protected_source_refused(self):
        for arm,tag in (("learned","902000"),("AZ_forced_diagnostic","903000"),
                        ("AZ","U"),("other","R")):
            with self.assertRaises(RuntimeError):
                native.evaluate(arm,tag)

    def test_resource_receipt_cannot_promote_ineligible_control(self):
        records=[]
        for tag in ("U","R"):
            for arm in ("learned","AZ_forced_diagnostic"):
                for _ in range(3):
                    records.append({"arm":arm,"fixture":tag,
                        "cpu_ns_including_source_import_fit_native_scorer":100000,
                        "whole_child_peak_RSS_bytes":20100000,
                        "native_execution":{
                            "same_public_48_sha256":tag,
                            "same_native_graph_sha256":tag,
                            "native_workload":{"native_graph_calls":1,
                              "native_work":{"max_active":2,"max_retained":1}}}})
        r=measure.combine(records)
        self.assertTrue(r["same_native_graph_executed_both_arms"])
        self.assertEqual(r["samples"],12)
        self.assertFalse(r["AZ_forced_diagnostic_is_eligible_baseline"])
        self.assertFalse(r["full_scientific_resource_parity"])
        self.assertFalse(r["original_train_complete_firstuse_record_published"])
        self.assertEqual(r["protected_U_R_cases_generated"],0)
        self.assertTrue(r["AZ_original_scientific_abstention_preserved"])
        records[0]["native_execution"]["same_native_graph_sha256"]="mismatch"
        with self.assertRaises(RuntimeError):
            measure.combine(records)


if __name__=="__main__":
    unittest.main()
