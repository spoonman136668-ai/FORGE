"""RSI-R5 read-only, unchanged-budget source-selection A/B development trial.

All measured NO_GO outcomes are retained. Green CI != speedup, RSI or science.
"""
import json
import unittest

from f139.rsi_r5_diversity_impact import (
    ABBA, CODE, FIXTURE_BLOB, PARENT, PROPOSER_BLOB, SCENARIOS,
    SCHEMA, SPEC, arm_run, measure, need, read_pinned, scenario_source,
)


class NativeProposalDiversityImpact(unittest.TestCase):
    def test_source_identity_and_historical_source_splits(self):
        self.assertEqual(PARENT, "3e83e0ddba0aedd397298a07ef53d1bc6bf301b3")
        self.assertEqual(SCHEMA, "forge.f139.rsi-r5.diversity-impact-dev.v1")
        self.assertEqual(len(SCENARIOS), 3)
        self.assertEqual(ABBA, ("ablation", "qualified", "qualified", "ablation"))
        self.assertGreater(len(read_pinned(CODE, PROPOSER_BLOB)), 1000)
        self.assertGreater(len(read_pinned(SPEC, FIXTURE_BLOB)), 1000)
        self.assertEqual([len(scenario_source(x)) for x in SCENARIOS],
                         [7, 8, 9])

    def test_reject_source_and_scenario_spoofing(self):
        with self.assertRaisesRegex(ValueError, "R5_DIVERSITY_PINNED_SOURCE_DRIFT"):
            read_pinned(SPEC, "0"*40)
        with self.assertRaisesRegex(ValueError, "R5_DIVERSITY_SCENARIO_UNAUTHORIZED"):
            scenario_source("arbitrary")
        with self.assertRaisesRegex(ValueError, "R5_DIVERSITY_ARM_UNAUTHORIZED"):
            arm_run("legacy_only", "random")
        with self.assertRaisesRegex(ValueError, "R5_DIVERSITY_NEGATIVE_CONTROL"):
            need(False, "NEGATIVE_CONTROL")

    def test_isolated_abba_unchanged_candidate_budget_with_preserved_negative(self):
        receipt = measure()
        self.assertEqual(receipt["schema"], SCHEMA)
        self.assertEqual(receipt["origin"], PARENT)
        self.assertEqual([c["scenario"] for c in receipt["cases"]],
                         list(SCENARIOS))
        self.assertIn(receipt["development_disposition"],
                      ("MEASURED_PROVEN_DUPLICATE_REDUCTION",
                       "R5_DUPLICATE_SELECTION_NO_GO"))
        self.assertFalse(receipt["owner_executed"])
        self.assertFalse(receipt["rsi_proven"])
        self.assertFalse(receipt["scientific_pass"])
        for sample in receipt["cases"]:
            self.assertGreater(sample["baseline_selected"], 0)
            self.assertGreater(sample["qualified_selected"], 0)
            self.assertLessEqual(sample["baseline_selected"], 16)
            self.assertLessEqual(sample["qualified_selected"], 16)
            self.assertLessEqual(sample["qualified_proven"],
                                 sample["baseline_proven"])
            self.assertEqual([v["arm"] for v in sample["ABBA"]], list(ABBA))
            self.assertEqual(len(sample["paired_whole_wall_speedup_A_over_B"]), 2)
            for v in sample["ABBA"]:
                self.assertGreater(v["whole_child_wall_seconds"], 0)
                self.assertGreaterEqual(v["cpu_seconds"], 0)
                self.assertGreaterEqual(v["selection_wall_seconds"], 0)
        print("RSI_R5_ORIGINAL_SOURCE_SELECTION_RECEIPT=" +
              json.dumps(receipt, sort_keys=True, separators=(",", ":")))
        print("RSI_R5_ENGINEERING_DEVELOPMENT_DISPOSITION=" +
              receipt["development_disposition"])
        print("RSI_R5_ORIGINAL_OWNER_RUN=FALSE")
        print("RSI_R5_SCIENTIFIC_FIRST_USE=FALSE")
        print("RSI_R5_AUTONOMOUS_RSI=NOT_PROVEN")


if __name__ == "__main__":
    unittest.main()
