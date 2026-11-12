"""ACC-118 existing-runner integration: execute all 36 frozen FIT/DEV comparisons.

No protected TEST, new workflow, scheduler, acceptance or native deployment.
This test passes when the diagnostic runs correctly, NOT when candidate wins.
"""
from __future__ import annotations
import json
import pathlib
import sys
import unittest

class ACC118FitDevQualification(unittest.TestCase):
    def test_bounded_fitdev_comparison_is_fail_closed(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        research = root / "research" / "acc95_u24"
        self.assertTrue((research / "compare_fitdev.py").is_file())
        sys.path.insert(0, str(research))
        try:
            from compare_fitdev import screen, NO_SCIENCE
            result = screen()
        finally:
            sys.path.remove(str(research))
        self.assertEqual(result["case_count"], 36)
        self.assertEqual((result["fit_cases"], result["dev_cases"]), (32, 4))
        self.assertEqual(len(result["dev_per_case"]), 4)
        self.assertEqual(len(result["dev_aggregate"]), 8)
        self.assertEqual(result["decision"], NO_SCIENCE)
        self.assertEqual(result["scientific_acceptance"], "NOT_GRANTED")
        self.assertFalse(result["data_split_test_accessed"])
        self.assertFalse(result["recurrent_control_qualified"])
        self.assertFalse(result["rss_energy_routing_and_full_resource_qualified"])
        self.assertFalse(result["raw_predictions_retained"])
        self.assertTrue(all(row["split"] == "DEV" for row in result["dev_per_case"]))
        for row in result["dev_per_case"]:
            self.assertEqual(set(row["arms"]), set(result["arms"]))
            self.assertTrue(all(0 <= v["post_switch_accuracy"] <= 1
                                for v in row["arms"].values()))
        print("ACC118_RESULT=" + json.dumps({
            "trace_set_sha256": result["trace_set_sha256"],
            "dev_aggregate": result["dev_aggregate"],
            "dev_per_case": [{"rule": r["first_rule"], "seed": r["seed"],
                              "trace_sha256": r["trace_sha256"],
                              "post_accuracy": {a: v["post_switch_accuracy"]
                                                for a, v in r["arms"].items()},
                              "adapt_error": {a: v["adapt_error"]
                                              for a, v in r["arms"].items()}}
                             for r in result["dev_per_case"]],
            "accuracy_baseline": result["conservative_accuracy_baseline"],
            "error_baseline": result["conservative_error_baseline"],
            "connected_accuracy_delta": result["connected_accuracy_delta"],
            "connected_error_reduction": result["connected_relative_adapt_error_reduction"],
            "classification": result["decision"],
        }, separators=(",", ":"), sort_keys=True))
