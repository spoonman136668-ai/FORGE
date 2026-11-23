"""Adverse source tests for a no-I/O, no-science-authority dev replay."""
from __future__ import annotations
import copy
import hashlib
import unittest
from unittest.mock import patch

from scripts import nature_training_replay as n


IDS = ["terminal-neg-0001", "terminal-neg-0002", "terminal-neg-0003"]


def digest(label):
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def frozen(**changes):
    data = {"schema": n.SCHEMA, "parent_sha": "a" * 40,
            "parent_tree_sha": "b" * 40,
            "protocol_sha256": digest("frozen-prereg-protocol"),
            "development_corpus_sha256": digest("source-scoped-dev-corpus"),
            "partition": "development", "selected_control": "finite",
            "terminal_event_ids": list(IDS),
            "case_input_sha256": {item: digest("input-" + item) for item in IDS},
            "max_wall_ms": 300, "max_cpu_ms": 300,
            "max_peak_rss_bytes": 200, "negative_control": False}
    data.update(changes)
    return data


def rows(fr, scores=None):
    if scores is None:
        scores = {"A": (True, False, False), "B": (False, False, False),
                  "C": (True, True, True), "D": (True, False, False)}
    return {arm: [
        {"terminal_event_id": item,
         "input_sha256": fr["case_input_sha256"][item],
         "plan_sha256": digest("plan-" + arm + "-" + item),
         "beneficial_dev_outcome": value, "retention_drift_brier": 0.01,
         "wall_ms": 10, "cpu_ms": 10, "peak_rss_bytes": 100,
         "model_calls": 0, "sealed_holdout_access": False,
         "scientific_first_use": False}
        for item, value in zip(IDS, scores[arm])] for arm in n.ARMS}


class PureNatureDevReplayTests(unittest.TestCase):
    def test_four_arm_determinism_and_no_science_promotion(self):
        fr = frozen()
        cases = rows(fr)
        original = copy.deepcopy((fr, cases))
        got = n.evaluate(fr, cases)
        self.assertEqual(got, n.evaluate(fr, cases))
        self.assertEqual(original, (fr, cases))
        self.assertEqual(got["arms"]["A"]["beneficial_training_labels"], 1)
        self.assertEqual(got["arms"]["C"]["beneficial_training_labels"], 3)
        self.assertEqual(got["candidate_vs_control_relative"], 2.0)
        self.assertEqual(got["diagnostic"], "TRAINING_LABELS_ONLY_NOT_SCIENCE")
        self.assertFalse(got["scientific_gain_verified"])
        self.assertFalse(got["comparison_source_authenticated"])
        self.assertFalse(got["original_terminal_receipts_authenticated"])
        self.assertFalse(got["deployment_authorized"])
        self.assertEqual(got["paid_api_calls"], 0)
        self.assertLessEqual(got["paired_two_sided_sign_p"], 1.0)

    def test_zero_control_is_inconclusive_even_with_favorable_candidate(self):
        fr = frozen()
        data = rows(fr)
        for row in data["A"]:
            row["beneficial_dev_outcome"] = False
        got = n.evaluate(fr, data)
        self.assertIsNone(got["candidate_vs_control_relative"])
        self.assertEqual(got["diagnostic"], "NO_CONTROL_SUCCESSES")
        self.assertFalse(got["scientific_gain_verified"])

    def test_negative_control_must_not_invent_gain(self):
        fr = frozen(negative_control=True)
        with self.assertRaisesRegex(n.DevReplayRejected, "NEGATIVE_CONTROL_FALSE_DISCOVERY"):
            n.evaluate(fr, rows(fr))
        empty = rows(fr, {a: (False, False, False) for a in n.ARMS})
        result = n.evaluate(fr, empty)
        self.assertIsNone(result["candidate_vs_control_relative"])
        self.assertFalse(result["scientific_gain_verified"])

    def test_retention_veto_and_equal_process_cost(self):
        fr = frozen()
        sample = rows(fr)
        sample["C"][0]["retention_drift_brier"] = 0.0201
        got = n.evaluate(fr, sample)
        self.assertEqual(got["diagnostic"], "RETENTION_VETO")
        sample = rows(fr)
        sample["C"][0]["cpu_ms"] = 25
        with self.assertRaisesRegex(n.DevReplayRejected, "UNEQUAL_WHOLE_PROCESS_COST"):
            n.evaluate(fr, sample)
        sample = rows(fr)
        sample["C"][0]["wall_ms"] = 300
        with self.assertRaisesRegex(n.DevReplayRejected, "EXCEEDED_RESOURCE_BUDGET"):
            n.evaluate(fr, sample)

    def test_missing_arm_wrong_order_and_duplicate_plan_are_rejected(self):
        fr = frozen()
        sample = rows(fr)
        del sample["D"]
        with self.assertRaisesRegex(n.DevReplayRejected, "FOUR_ARMS_REQUIRED"):
            n.evaluate(fr, sample)
        sample = rows(fr)
        sample["C"].reverse()
        with self.assertRaisesRegex(n.DevReplayRejected, "EVENT_ORDER_OR_INFORMATION_DRIFT"):
            n.evaluate(fr, sample)
        sample = rows(fr)
        sample["C"][1]["plan_sha256"] = sample["C"][0]["plan_sha256"]
        with self.assertRaisesRegex(n.DevReplayRejected, "REPLAYED_PLAN_WITHIN_ARM"):
            n.evaluate(fr, sample)

    def test_caller_source_labels_never_grant_holdout_or_science_authority(self):
        fr = frozen()
        for attr, value in (("sealed_holdout_access", True),
                            ("scientific_first_use", True), ("model_calls", 1)):
            sample = rows(fr)
            sample["A"][0][attr] = value
            with self.assertRaisesRegex(n.DevReplayRejected, "UNAUTHORIZED_MODEL_OR_SCIENCE_ACCESS"):
                n.evaluate(fr, sample)
        sample = rows(fr)
        sample["A"][0]["input_sha256"] = digest("unfamiliar-holdout")
        with self.assertRaisesRegex(n.DevReplayRejected, "HOLDOUT_OR_INPUT_LEAKAGE"):
            n.evaluate(fr, sample)
        with self.assertRaisesRegex(n.DevReplayRejected, "PROTECTED_PARTITION"):
            n.evaluate(frozen(partition="holdout"), rows(fr))

    def test_invalid_freeze_caps_false_identity_and_extra_fields(self):
        fr = frozen()
        for updates, issue in (({"max_cpu_ms": 0}, "BUDGET_NOT_PREDECLARED"),
                               ({"selected_control": "best-after-results"}, "CONTROL_NOT_PRESELECTED"),
                               ({"parent_sha": "main"}, "FREEZE_SOURCE_IDENTITY"),
                               ({"terminal_event_ids": [IDS[0]]}, "FROZEN_EVENT_IDS"),
                               ({"terminal_event_ids": IDS * 4}, "FROZEN_EVENT_IDS")):
            with self.subTest(updates=updates), self.assertRaisesRegex(n.DevReplayRejected, issue):
                n.evaluate(frozen(**updates), rows(fr))
        with self.assertRaisesRegex(n.DevReplayRejected, "FREEZE_FIELDS"):
            n.evaluate({**fr, "protected_results": []}, rows(fr))
        with self.assertRaisesRegex(n.DevReplayRejected, "ROW_FIELDS"):
            data = rows(fr)
            data["C"][0]["post_result_tuning"] = True
            n.evaluate(fr, data)

    def test_no_file_or_network_access_during_diagnostics(self):
        fr = frozen()
        sample = rows(fr)
        with patch("builtins.open", side_effect=AssertionError("filesystem denied")), \
             patch("builtins.input", side_effect=AssertionError("interactive denied")):
            got = n.evaluate(fr, sample)
        self.assertEqual(got["arms"]["C"]["attempts"], 3)


if __name__ == "__main__":
    unittest.main()
