"""Adversarial G100 receipt checks; synthetic data only, no original model."""
import copy
import hashlib
import unittest

from research.cpu_g97.g100_receipt_validator import validate, calculate
from research.cpu_g97.g100_stream_manifest import ARMS, STRATA, freeze, canonical_bytes

HEAD = "a" * 40
TOKENS = 8


def synthetic():
    selected = [{"source_row": i, "instruction_sha256": f"{i:064x}"} for i in range(12)]
    manifest, digest = freeze(selected)
    rec = {
        "schema": "forge.cpu-g100.development.v1",
        "phase": "DEVELOPMENT_ONLY", "source_sha": HEAD,
        "development_stream_sha256": digest, "engineering": "PASS",
        "correctness": "PASS", "scientific_acceptance": "NOT_GRANTED",
        "promotion_allowed": False, "heldout_executed": False,
        "selected_question_hashes": [s["instruction_sha256"] for s in selected],
        "decision": "DEVELOPMENT_NO_GO", "strata": {}
    }
    for stratum in STRATA:
        requests = manifest["strata"][stratum]["requests"]
        reps = []
        for n in range(4):
            arms = {}
            for arm in ARMS:
                rows = [
                    {"index": i, "prefix_id": q["prefix_id"], "source_row": q["source_row"],
                     "hit": False, "admitted": False, "bypass": True,
                     "clone_ns": 0, "request_wall_ns": 1000, "request_cpu_ns": 900,
                     "resident_kv_bytes": 0, "rss_bytes": 1000,
                     "output_sha256": hashlib.sha256(str(i).encode()).hexdigest()}
                    for i, q in enumerate(requests)]
                arms[arm] = {"rows": rows, "wall_ns": 48000, "cpu_ns": 44000,
                             "max_rss": 1000, "max_resident_kv_bytes": 0,
                             "hits": 0, "misses": 48, "admissions": 0,
                             "evictions": 0, "bypasses": 48}
            reps.append({"rep": n + 1,
                         "order": list(ARMS if n % 2 == 0 else tuple(reversed(ARMS))),
                         "arms": arms})
        baseline = [r["arms"]["no_cache"] for r in reps]
        metrics = {}
        for arm in ARMS[1:]:
            metrics[arm] = calculate(baseline, [r["arms"][arm] for r in reps], TOKENS)
            metrics[arm]["qualifies"] = False
        if stratum == "overflow":
            metrics["g100_deferred_first_use"]["improves_overflow_g97"] = False
        rec["strata"][stratum] = {"traffic_sha256": manifest["strata"][stratum]["traffic_sha256"],
                                "repetitions": reps, "metrics": metrics, "exact_parity": True}
    return rec, manifest, canonical_bytes(manifest)


class G100ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.receipt, self.manifest, self.raw = synthetic()

    def verify(self):
        return validate(self.receipt, self.manifest, self.raw, HEAD, tokens=TOKENS)

    def test_clean_synthetic_receipt_yields_no_go(self):
        self.assertEqual(self.verify(), "DEVELOPMENT_NO_GO")

    def test_incorrect_scientific_verdict_rejected(self):
        self.receipt["decision"] = "DEVELOPMENT_CANDIDATE"
        with self.assertRaisesRegex(ValueError, "FALSE_VERDICT"):
            self.verify()

    def test_fabricated_throughput_rejected(self):
        self.receipt["strata"]["mixed"]["metrics"]["g100_deferred_first_use"]["throughput_speedup"] = 1.6
        with self.assertRaisesRegex(ValueError, "METRIC_throughput_speedup"):
            self.verify()

    def test_protected_or_promotion_flag_rejected(self):
        for field in ("heldout_executed", "promotion_allowed"):
            self.receipt[field] = True
            with self.assertRaisesRegex(ValueError, "PROTECTED_OR_PROMOTION"):
                self.verify()
            self.receipt[field] = False

    def test_drifted_manifest_and_source_rejected(self):
        self.receipt["development_stream_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "STREAM_HASH_DRIFT"):
            self.verify()
        self.receipt["development_stream_sha256"] = hashlib.sha256(self.raw).hexdigest()
        self.receipt["source_sha"] = "b" * 40
        with self.assertRaisesRegex(ValueError, "SOURCE_MISMATCH"):
            self.verify()

    def test_row_and_cache_accounting_rejected(self):
        sample = self.receipt["strata"]["overflow"]["repetitions"][0]["arms"]["g100_deferred_first_use"]
        sample["hits"] = 1
        with self.assertRaisesRegex(ValueError, "CACHE_EVENT_TOTAL|COUNTER_ROW_DRIFT"):
            self.verify()
        sample["hits"] = 0
        sample["rows"][0]["source_row"] = 999
        with self.assertRaisesRegex(ValueError, "REQUEST_IDENTITY"):
            self.verify()

    def test_exact_output_digest_parity_required(self):
        sample = self.receipt["strata"]["round_robin"]["repetitions"][1]["arms"]["g100_deferred_first_use"]
        sample["rows"][3]["output_sha256"] = "e" * 64
        with self.assertRaisesRegex(ValueError, "OUTPUT_PARITY"):
            self.verify()

    def test_incomplete_repetition_and_invalid_peak_rejected(self):
        self.receipt["strata"]["bursty"]["repetitions"].pop()
        with self.assertRaisesRegex(ValueError, "REPETITION_COUNT"):
            self.verify()
        self.receipt, self.manifest, self.raw = synthetic()
        sample = self.receipt["strata"]["mixed"]["repetitions"][0]["arms"]["g100_deferred_first_use"]
        sample["max_resident_kv_bytes"] = 86114305
        with self.assertRaisesRegex(ValueError, "RESIDENT_KV_BUDGET"):
            self.verify()


if __name__ == "__main__":
    unittest.main()
