"""Adversarial source-only verification for efficient-language identity binding."""
from __future__ import annotations
import ast
import copy
import json
from pathlib import Path
import unittest

import screen_contract as s


def sample():
    return {
        "schema": s.SCHEMA, "mode": "prepare_only",
        "candidate": {"mechanism": "latent-state-to-language",
                      "commit_sha": "a"*40, "tree_sha": "b"*40,
                      "config_sha256": "c"*64},
        "comparator": {"family": "recurrent", "commit_sha": "d"*40,
                       "tree_sha": "e"*40, "config_sha256": "f"*64},
        "data": {"train_sha256": "1"*64,
                 "development_sha256": "2"*64,
                 "holdout_sha256": "3"*64},
        "protocol_sha256": "4"*64,
        "environment_sha256": "5"*64,
        "meter_source_sha256": "6"*64,
        "focused_suite_sha256": "7"*64,
        "budgets": {"max_training_cpu_seconds": 60,
                    "max_inference_cpu_seconds": 20,
                    "max_peak_memory_bytes": 64*1024*1024, "max_trials": 1},
        "authority": {"science_admitted": False, "first_use": False,
                      "dispatch": False, "new_controller": False,
                      "paid_api_calls": 0},
    }


def receipt(contract):
    return {
        "schema": s.RECEIPT_SCHEMA,
        "candidate_key": s.candidate_key(contract),
        "suite_sha256": contract["focused_suite_sha256"],
        "environment_sha256": contract["environment_sha256"],
        "output_sha256": "8"*64, "test_count": 11,
        "status": "PASS", "scientific_first_use": False,
    }


class ScreeningContract(unittest.TestCase):
    def test_stable_key_and_canonical_payload(self):
        contract = sample()
        shuffled = dict(reversed(list(contract.items())))
        self.assertEqual(s.candidate_key(contract), s.candidate_key(shuffled))
        self.assertEqual(len(s.candidate_key(contract)), 64)
        self.assertEqual(s.parse(s.canonical(contract)), contract)

    def test_each_custody_identity_changes_fingerprint(self):
        first = sample()
        paths = [
            ("candidate", "commit_sha", "9"*40),
            ("candidate", "tree_sha", "9"*40),
            ("candidate", "config_sha256", "9"*64),
            ("candidate", "mechanism", "parallel-verify-repair"),
            ("comparator", "family", "state-space"),
            ("comparator", "commit_sha", "9"*40),
            ("comparator", "tree_sha", "9"*40),
            ("comparator", "config_sha256", "9"*64),
            ("data", "train_sha256", "9"*64),
            ("data", "development_sha256", "9"*64),
            ("data", "holdout_sha256", "9"*64),
            ("budgets", "max_trials", 2),
        ]
        for field, subfield, new in paths:
            other = copy.deepcopy(first)
            other[field][subfield] = new
            with self.subTest(field=field, subfield=subfield):
                self.assertNotEqual(s.candidate_key(first),
                                    s.candidate_key(other))
        for field in ("protocol_sha256", "environment_sha256",
                      "meter_source_sha256", "focused_suite_sha256"):
            other = copy.deepcopy(first)
            other[field] = "9"*64
            with self.subTest(field=field):
                self.assertNotEqual(s.candidate_key(first),
                                    s.candidate_key(other))

    def test_reject_identity_relabeling_and_extra_fields(self):
        for changed in (
            ("schema", "not-v1"), ("mode", "execute"),
            ("protocol_sha256", "not-a-sha"),
        ):
            other = sample()
            other[changed[0]] = changed[1]
            with self.subTest(changed=changed), self.assertRaises(s.Refused):
                s.candidate_key(other)
        other = sample()
        other["runner_secret"] = "pretend-token"
        with self.assertRaisesRegex(s.Refused, "FIELDS"):
            s.candidate_key(other)

    def test_reject_missing_or_crossed_splits(self):
        other = sample()
        other["data"]["holdout_sha256"] = other["data"]["train_sha256"]
        with self.assertRaisesRegex(s.Refused, "SPLITS"):
            s.candidate_key(other)
        other = sample()
        del other["data"]["holdout_sha256"]
        with self.assertRaisesRegex(s.Refused, "DATA_FIELDS"):
            s.candidate_key(other)

    def test_reject_budget_escalation_and_boolean_as_integer(self):
        for field, value in (
            ("max_trials", 5), ("max_trials", True),
            ("max_training_cpu_seconds", 601),
            ("max_training_cpu_seconds", 0),
            ("max_inference_cpu_seconds", 301),
            ("max_peak_memory_bytes", 4*1024**3+1),
        ):
            other = sample()
            other["budgets"][field] = value
            with self.subTest(field=field,value=value),self.assertRaises(s.Refused):
                s.candidate_key(other)

    def test_reject_science_dispatch_or_paid_api_self_authorization(self):
        for field, value in (
            ("science_admitted", True), ("first_use", True),
            ("dispatch", True), ("new_controller", True),
            ("paid_api_calls", 1),
        ):
            other = sample()
            other["authority"][field] = value
            with self.subTest(field=field),self.assertRaisesRegex(
                    s.Refused, "AUTHORITY_ESCALATION"):
                s.candidate_key(other)

    def test_reject_duplicate_nonfinite_and_oversized_raw_json(self):
        with self.assertRaisesRegex(s.Refused, "DUPLICATE"):
            s.parse(b'{"protocol_sha256":"A","protocol_sha256":"B"}')
        with self.assertRaises(s.Refused):
            s.parse(b'{"score":Infinity}')
        with self.assertRaisesRegex(s.Refused, "INPUT_SIZE"):
            s.parse(b" "*17000)
        with self.assertRaises(s.Refused):
            s.parse(b"[]")

    def test_matching_receipt_never_grants_reuse_or_scientific_first_use(self):
        contract = sample()
        report = s.inspect_focused_receipt(contract, receipt(contract))
        self.assertTrue(report["exact_identity_match"])
        self.assertFalse(report["cached_qualification_authorized"])
        self.assertFalse(report["provider_custody_independently_verified"])
        self.assertFalse(report["scientific_first_use"])
        self.assertEqual(report["disposition"],
                         "EXTERNAL_PROVIDER_VERIFICATION_REQUIRED")

    def test_source_test_environment_and_suite_drift_reject_old_receipt(self):
        contract = sample()
        old = receipt(contract)
        for field, value in (
            ("candidate_key", "9"*64), ("suite_sha256", "9"*64),
            ("environment_sha256", "9"*64)
        ):
            other = dict(old, **{field: value})
            with self.subTest(field=field), self.assertRaisesRegex(
                    s.Refused, "STALE_FOCUSED_RECEIPT"):
                s.inspect_focused_receipt(contract, other)

    def test_zero_tests_forged_science_and_unsupported_status_are_denied(self):
        contract = sample()
        for field, value in (
            ("test_count", 0), ("test_count", True),
            ("status", "SKIPPED"), ("scientific_first_use", True),
            ("output_sha256", "garbage"),
        ):
            fake = dict(receipt(contract), **{field: value})
            with self.subTest(field=field), self.assertRaises(s.Refused):
                s.inspect_focused_receipt(contract, fake)

    def test_measurement_presence_explicitly_separates_unknown_and_zero(self):
        values = {k: None for k in s.MEASUREMENTS}
        values["language_fidelity"] = 0.0
        values["task_quality"] = 1.0
        values["sequential_latency_seconds"] = 0.23
        coverage = s.measurement_coverage(values)
        self.assertIn("training_flops", coverage["unavailable"])
        self.assertIn("energy_joules", coverage["unavailable"])
        self.assertIn("language_fidelity", coverage["measured"])
        self.assertFalse(coverage["completeness"])
        self.assertFalse(coverage["quality_or_scientific_gain_claimed"])

    def test_reject_fake_metrics_nonfinite_or_wrong_unit_types(self):
        values = {k: None for k in s.MEASUREMENTS}
        for field, value in (
            ("language_fidelity", 1.01), ("task_quality", -0.01),
            ("inference_flops", 1.5), ("training_flops", True),
            ("peak_memory_bytes", -1), ("energy_joules", float("nan")),
            ("sequential_latency_seconds", float("inf")),
        ):
            altered = dict(values, **{field: value})
            with self.subTest(field=field), self.assertRaises(s.Refused):
                s.measurement_coverage(altered)

    def test_software_contract_cannot_dispatch_or_fetch_private_sources(self):
        path = Path(s.__file__)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        allowed = {"__future__", "hashlib", "json", "math", "re"}
        prohibited = {"os", "subprocess", "urllib", "requests", "socket",
                      "sqlite3", "pathlib", "ctypes", "http", "shutil",
                      "time", "cloudflare"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertIn(alias.name.split(".")[0], allowed)
                    self.assertNotIn(alias.name.split(".")[0], prohibited)
            if isinstance(node, ast.ImportFrom):
                self.assertIn((node.module or "").split(".")[0], allowed)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id,
                                 ("eval", "exec", "compile", "__import__",
                                  "open", "dispatch", "system"))


if __name__ == "__main__":
    unittest.main()
