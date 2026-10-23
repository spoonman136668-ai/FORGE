"""Adversarial source-only turnaround accounting; no provider or science claims."""
from __future__ import annotations

import ast
import copy
import math
from pathlib import Path
import unittest

import screen_contract as identity
import turnaround_advisory as t
from test_screen_contract import sample


def observation(contract, *, evidence="8", workload="9", seconds=50.0,
                quality=0.9):
    return {
        "schema": t.SCHEMA,
        "candidate_key": identity.candidate_key(contract),
        "environment_sha256": contract["environment_sha256"],
        "suite_sha256": contract["focused_suite_sha256"],
        "workload_sha256": workload * 64,
        "evidence_sha256": evidence * 64,
        "stages_seconds": {
            "intake": 2.0, "focused_tests": seconds,
            "comparator": 10.0, "evidence_archive": 3.0,
            "full_regression": 20.0,
        },
        "independent_evaluation_seconds": None,
        "total_cpu_seconds": seconds + 40,
        "peak_memory_bytes": 123456,
        "artifact_bytes": 4321,
        "energy_joules": None,
        "task_quality": quality,
        "hard_false_positives": 0,
        "human_interventions": 0,
        "regression_test_count": 13,
    }


class TurnaroundAdvisory(unittest.TestCase):
    def setUp(self):
        self.contract = sample()
        self.a = observation(self.contract)
        self.b = observation(self.contract, evidence="a", seconds=20.0)

    def compare(self):
        return t.compare_turnaround(self.contract, self.a, self.b)

    def test_matched_timings_report_numeric_savings_only(self):
        report = self.compare()
        self.assertEqual(report["baseline_seconds"], 85.0)
        self.assertEqual(report["candidate_seconds"], 55.0)
        self.assertEqual(report["observed_saving_seconds"], 30.0)
        self.assertTrue(report["apparent_development_gain"])
        self.assertFalse(report["qualified_turnaround_gain_verified"])
        self.assertFalse(report["provider_custody_independently_verified"])
        self.assertFalse(report["full_regression_independently_verified"])
        self.assertFalse(report["independent_evaluation_performed"])
        self.assertFalse(report["cached_qualification_authorized"])
        self.assertFalse(report["scientific_first_use"])
        self.assertFalse(report["scientific_breakthrough_claimed"])

    def test_observed_slower_case_is_negative_not_promoted(self):
        self.b["stages_seconds"]["focused_tests"] = 65.0
        report = self.compare()
        self.assertLess(report["observed_saving_seconds"], 0)
        self.assertFalse(report["apparent_development_gain"])

    def test_quality_loss_blocks_apparent_gain_even_if_faster(self):
        self.b["task_quality"] = 0.8
        report = self.compare()
        self.assertGreater(report["observed_saving_seconds"], 0)
        self.assertFalse(report["apparent_development_gain"])

    def test_unmeasured_energy_cannot_be_imputed(self):
        report = self.compare()
        self.assertFalse(report["energy_comparable"])
        self.assertIsNone(report["observed_energy_delta_joules"])
        self.a["energy_joules"] = 3.0
        self.b["energy_joules"] = 2.5
        self.assertEqual(self.compare()["observed_energy_delta_joules"], -0.5)
        self.b["energy_joules"] = None
        self.assertIsNone(self.compare()["observed_energy_delta_joules"])

    def test_changed_source_or_environment_rejects_comparison(self):
        for field, changed in (
            ("candidate_key", "b" * 64),
            ("environment_sha256", "a" * 64),
            ("suite_sha256", "a" * 64),
            ("workload_sha256", "e" * 64),
        ):
            altered = copy.deepcopy(self.b)
            altered[field] = changed
            with self.subTest(field=field), self.assertRaises(identity.Refused):
                t.compare_turnaround(self.contract, self.a, altered)

    def test_same_observation_replay_is_rejected(self):
        self.b["evidence_sha256"] = self.a["evidence_sha256"]
        with self.assertRaisesRegex(identity.Refused, "REPLAYED"):
            self.compare()

    def test_missing_stages_and_required_final_regression_rejected(self):
        for key, bad in (("full_regression", None),
                         ("full_regression", 0),
                         ("comparator", -1),
                         ("intake", float("inf")),
                         ("focused_tests", True)):
            altered = copy.deepcopy(self.b)
            if bad is None:
                del altered["stages_seconds"][key]
            else:
                altered["stages_seconds"][key] = bad
            with self.subTest(key=key, bad=bad), self.assertRaises(identity.Refused):
                t.compare_turnaround(self.contract, self.a, altered)

    def test_no_invented_first_use_or_independent_evaluation(self):
        for value in (1.0, 0.0, False, True):
            self.b["independent_evaluation_seconds"] = value
            with self.subTest(value=value), self.assertRaisesRegex(
                    identity.Refused, "FIRST_USE"):
                self.compare()

    def test_hard_false_positives_and_zero_regression_disallowed(self):
        for field, value in (("hard_false_positives", 1),
                             ("regression_test_count", 0),
                             ("human_interventions", -1),
                             ("peak_memory_bytes", True),
                             ("task_quality", 1.2),
                             ("total_cpu_seconds", float("nan")),
                             ("energy_joules", -1.0)):
            altered = copy.deepcopy(self.b)
            altered[field] = value
            with self.subTest(field=field), self.assertRaises(identity.Refused):
                t.compare_turnaround(self.contract, self.a, altered)

    def test_hidden_extra_field_and_invalid_source_rejected(self):
        self.b["cached_provider_verified"] = True
        with self.assertRaisesRegex(identity.Refused, "FIELDS"):
            self.compare()
        self.b.pop("cached_provider_verified")
        self.contract["candidate"]["commit_sha"] = "0" * 39
        with self.assertRaises(identity.Refused):
            self.compare()

    def test_no_io_process_or_scientific_admission_apis(self):
        tree = ast.parse(Path(t.__file__).read_text(encoding="utf-8"))
        allowed = {"__future__", "math", "screen_contract"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertIn(alias.name.split(".")[0], allowed)
            if isinstance(node, ast.ImportFrom):
                self.assertIn((node.module or "").split(".")[0], allowed)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, ("eval", "exec", "open",
                    "__import__", "dispatch", "system", "authorize", "write"))


if __name__ == "__main__":
    unittest.main()
