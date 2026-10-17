"""F123 OS receipt audit: synthetic TRAIN-only parser, no confirmation access."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f123_cross_os_custody as m

def lane(name):
    weights = {"A": [0.25, 0.125, -0.031],
               "B": [0.125, -0.25, 0.375]}
    foundation = [0.1] * 17
    query = [0.2] * 20
    return {"lane": name,
            "train_source_only_selection": "B",
            "train_frozen_weights": weights,
            "train_f122_foundation_weights": foundation,
            "train_query_only_weights": query,
            "weights_sha256": {k: m.digest(v) for k, v in weights.items()},
            "selected_model_weights_sha256": m.digest(weights["B"]),
            "query_only_weights_sha256": m.digest(query),
            "model_arms": {k: {"weight_sha256": m.digest(v),
                               "train_score": {"pairs": 48, "paired_correct": 45},
                               "movement": 1., "parameters": len(v)}
                           for k, v in weights.items()},
            "confirmation_inputs_generated": 0,
            "train_control_scores": {"CTRL_EXACT_SYMBOLIC": {"paired_correct": 48}},
            "advisory_candidate_source_shas": ["1" * 64, "2" * 64]}

def report():
    return {"schema": m.SCHEMA, "cohorts": "TRAIN_ONLY",
            "source_sha": "a" * 40, "run_id": 123, "event": "push",
            "freeze_git_blob": "b" * 40,
            "confirmation_inputs_generated": 0, "scientific_first_use": False,
            "scientific_acceptances": 0, "originals_dispatched": 0,
            "accepted_ref_mutations": 0, "optimizer_promotions": 0,
            "lanes": [lane("Wingless"), lane("Yggdrasil")]}

def refresh_weight_sha(r):
    for item in r["lanes"]:
        for arm in ("A", "B"):
            v = item["train_frozen_weights"][arm]
            item["weights_sha256"][arm] = m.digest(v)
            item["model_arms"][arm]["weight_sha256"] = m.digest(v)
        item["selected_model_weights_sha256"] = m.digest(
            item["train_frozen_weights"][item["train_source_only_selection"]])

class CrossOSCustodyQualification(unittest.TestCase):
    def write(self, root, obj):
        root.mkdir()
        data = (json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n").encode()
        (root / "f123-train-weights.json").write_bytes(data)
        h = hashlib.sha256(data).hexdigest()
        (root / "f123-train-weights.sha256").write_text(
            h + "  f123-train-weights.json\n", encoding="utf-8")
        return h

    def test_bounded_rounding_difference_preserves_distinct_exact_shas(self):
        a, b = report(), report()
        b["lanes"][0]["train_frozen_weights"]["B"][0] += 1e-15
        refresh_weight_sha(b)
        with tempfile.TemporaryDirectory() as root:
            x, y = Path(root) / "u", Path(root) / "w"
            sha_a, sha_b = self.write(x, a), self.write(y, b)
            o = m.audit(x, y)
            self.assertNotEqual(sha_a, sha_b)
            self.assertEqual(o["ubuntu_train_receipt_sha256"], sha_a)
            self.assertEqual(o["windows_train_receipt_sha256"], sha_b)
            self.assertFalse(o["exact_full_report_identity"])
            self.assertGreater(o["cross_os_weight_max_absolute_difference"], 0)
            self.assertFalse(o["scientific_first_use_authorized"])

    def test_semantically_relevant_drift_is_rejected(self):
        a = report()
        for change in ("large_numeric", "score", "selected", "source", "digest"):
            b = copy.deepcopy(a)
            if change == "large_numeric":
                b["lanes"][1]["train_frozen_weights"]["A"][0] += 1e-5
                refresh_weight_sha(b)
            elif change == "score":
                b["lanes"][0]["model_arms"]["A"]["train_score"]["paired_correct"] -= 1
            elif change == "selected":
                b["lanes"][0]["train_source_only_selection"] = "A"
                refresh_weight_sha(b)
            elif change == "source":
                b["source_sha"] = "c" * 40
            else:
                b["lanes"][0]["weights_sha256"]["B"] = "bad"
            with self.subTest(change=change), tempfile.TemporaryDirectory() as root:
                x, y = Path(root) / "u", Path(root) / "w"
                self.write(x, a)
                self.write(y, b)
                with self.assertRaises(m.Invalid):
                    m.audit(x, y)

    def test_byte_integrity_is_mandatory(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root) / "u"
            self.write(p, report())
            with (p / "f123-train-weights.json").open("ab") as f:
                f.write(b" ")
            with self.assertRaisesRegex(m.Invalid, "RECEIPT_SHA_MISMATCH"):
                m.read_receipt(p)

if __name__ == "__main__":
    unittest.main()
