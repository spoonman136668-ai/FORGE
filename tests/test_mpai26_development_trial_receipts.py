"""Strict source-only MP-AI26 receipt contract negatives; no inference or network."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import mpai26_development_trial_receipts as receipts
import mpai26_new_family_transfer_development as original


def fake_trial():
    rows = []
    for idx, (case, family, _, gold) in enumerate(original.QUESTIONS):
        for arm in original.ARMS:
            decision = gold if arm == "accepted_memory" else "UNKNOWN"
            context = "" if arm == "none" else "sample fixture, not a real model response"
            rows.append({
                "case": case, "family": idx // 2, "arm": arm,
                "decision": decision, "correct": decision == gold,
                "abstained": decision == "UNKNOWN", "unparseable": False,
                "prompt_tokens": 40, "completion_tokens": 1, "latency_ms": 10,
                "context_chars": len(context),
                "context_sha256": hashlib.sha256(context.encode()).hexdigest(),
                "response_sha256": hashlib.sha256(decision.encode()).hexdigest(),
            })
    return {"study": "development_only_nonindependent",
            "protocol_sha": original.protocol_sha(),
            "source_sha": original.SOURCE_SHA, "model_sha": original.MODEL_SHA,
            "trials": rows}


def rejects(value, marker):
    try:
        receipts.validate_private_trial(value)
    except ValueError as e:
        if marker not in str(e):
            raise AssertionError(f"expected {marker}, got {e}") from e
    else:
        raise AssertionError(f"must reject {marker}")


class ReceiptContractTest(unittest.TestCase):
    def test_synthetic_full_matrix_is_structurally_admissible_not_authenticated(self):
        data = fake_trial()
        result = receipts.export_receipt(
            data, run_id=123, run_attempt=1, job="original-windows",
            forge_sha="a" * 40)
        self.assertEqual(result["trial_count"], 24)
        self.assertEqual(result["aggregate"]["accepted_memory"]["correct"], 8)
        self.assertEqual(result["aggregate"]["source_matched_placebo"]["correct"], 0)
        self.assertFalse(result["claims"]["actual_execution_authenticated_by_this_receipt"])
        self.assertFalse(result["claims"]["recursive_improvement_proven"])
        self.assertEqual(result["claims"]["production_memory_writes"], 0)
        self.assertEqual(result["evidence_class"],
                         "EXPOSED_DEVELOPMENT_NOT_INDEPENDENTLY_AUTHENTICATED")

    def test_frozen_source_mismatch(self):
        data = fake_trial()
        data["source_sha"] = "a" * 40
        rejects(data, "FROZEN_SOURCE_DRIFT")

    def test_missing_trial(self):
        data = fake_trial()
        data["trials"].pop()
        rejects(data, "TRIAL_COUNT")

    def test_duplicate_trial(self):
        data = fake_trial()
        data["trials"][1] = dict(data["trials"][0])
        rejects(data, "DUPLICATE_OR_UNKNOWN")

    def test_bad_family(self):
        data = fake_trial()
        data["trials"][0]["family"] = 9
        rejects(data, "FAMILY_OR_DECISION")

    def test_changed_decision_without_outcome_update(self):
        data = fake_trial()
        data["trials"][2]["decision"] = "YES"
        rejects(data, "OUTCOME_INCONSISTENT")

    def test_tampered_hash_and_context(self):
        data = fake_trial()
        data["trials"][0]["response_sha256"] = "bad"
        rejects(data, "DIGEST_INVALID")
        data = fake_trial()
        data["trials"][0]["context_sha256"] = "a" * 64
        rejects(data, "NO_MEMORY_LEAK")

    def test_fake_runtime_job_identity(self):
        with self.assertRaisesRegex(ValueError, "WORKFLOW_IDENTITY"):
            receipts.export_receipt(fake_trial(), run_id=123, run_attempt=1,
                                    job="pretend-owner", forge_sha="a" * 40)

    def test_full_artifact_may_be_created_once_without_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            before = root / "private.json"
            artifact = root / "receipts.json"
            before.write_text(json.dumps(fake_trial()), encoding="utf-8")
            argv = [
                sys.executable,
                str(Path(receipts.__file__).resolve()),
                "--private-trials", str(before),
                "--output", str(artifact),
                "--run-id", "123",
                "--run-attempt", "1",
                "--job", "original-windows",
                "--forge-sha", "a" * 40,
            ]
            first = subprocess.run(argv, capture_output=True, text=True, check=False)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn("custody=NOT_AUTHENTICATED", first.stdout)
            self.assertEqual(json.loads(artifact.read_text())["trial_count"], 24)
            second = subprocess.run(argv, capture_output=True, text=True, check=False)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("MPAI26_RECEIPT_OUTPUT_BOUNDARY", second.stderr)


if __name__ == "__main__":
    unittest.main()
