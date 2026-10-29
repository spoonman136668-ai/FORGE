"""Fail-closed public publisher/mirror custody controls. No network or model."""
from __future__ import annotations
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import mpai12_original_publisher_parity as m


def cases():
    return [{
        "id": f"test-ARC-{i:04}",
        "question": {
            "stem": f"Which scientific explanation accounts for observation {i}?",
            "choices": [
                {"label": label, "text": f"Explanation {label} in experiment {i}"}
                for label in "ABCD"
            ],
        },
        "answerKey": "ABCD"[i % 4],
    } for i in range(m.EXPECTED_ROWS)]


class OfficialPublisherParityTests(unittest.TestCase):
    def test_all_299_question_and_answers_match_and_freeze_selected(self):
        primary = cases()
        mirror = copy.deepcopy(primary)
        for row in mirror:
            for item in row["question"]["choices"]:
                item["para"] = "UNTRUSTED_RETRIEVAL_EXTRA_MUST_NOT_AFFECT_CORE"
        got = m.audit(primary, mirror)
        self.assertTrue(got["full_split_source_parity"])
        self.assertEqual(got["all_split_questions"], 299)
        self.assertEqual(got["selected_gold_key_agreement"], 24)
        self.assertEqual(len(got["selected_question_only_sha256"]), 64)

    def test_single_false_mirror_gold_fails_full_parity(self):
        a, b = cases(), cases()
        b[20]["answerKey"] = "B" if a[20]["answerKey"] != "B" else "C"
        with self.assertRaisesRegex(RuntimeError, "CONTENT_OR_GOLD_MISMATCH"):
            m.audit(a, b)

    def test_single_mirror_stem_edit_fails_full_parity(self):
        a, b = cases(), cases()
        b[40]["question"]["stem"] += " appended adversarial text"
        with self.assertRaisesRegex(RuntimeError, "CONTENT_OR_GOLD_MISMATCH"):
            m.audit(a, b)

    def test_option_text_or_label_mutation_fails(self):
        a, b = cases(), cases()
        b[3]["question"]["choices"][0]["text"] = "Injected wrong option"
        with self.assertRaises(RuntimeError):
            m.audit(a, b)
        b = cases()
        b[3]["question"]["choices"][0]["label"] = "B"
        with self.assertRaises(RuntimeError):
            m.audit(a, b)

    def test_missing_or_replayed_id_fails(self):
        a, b = cases(), cases()
        b[13]["id"] = "FORGED-ID"
        with self.assertRaisesRegex(RuntimeError, "QUESTION_ID_POPULATION"):
            m.audit(a, b)
        b = cases()
        b[13]["id"] = b[14]["id"]
        with self.assertRaisesRegex(RuntimeError, "DUPLICATE_ID"):
            m.audit(a, b)

    def test_out_of_set_gold_and_missing_question_rejected(self):
        a, b = cases(), cases()
        b[5]["answerKey"] = "X"
        with self.assertRaisesRegex(RuntimeError, "GOLD_NOT_IN_OPTIONS"):
            m.audit(a, b)
        b = cases()
        b[5]["question"] = None
        with self.assertRaises(RuntimeError):
            m.audit(a, b)

    def test_exact_zip_member_and_count_required(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "publisher-test.zip"
            raw = "\n".join(json.dumps(x) for x in cases()).encode("utf-8")
            with zipfile.ZipFile(p, "w") as archive:
                archive.writestr(m.PUBLISHER_SPLIT, raw)
            rows, sha = m.publisher_rows(p)
            self.assertEqual(len(rows), 299)
            self.assertEqual(sha, m.digest(raw))
            with zipfile.ZipFile(p, "w") as archive:
                archive.writestr("wrong-path/dev.jsonl", raw)
            with self.assertRaisesRegex(RuntimeError, "SPLIT_IDENTITY_MISSING"):
                m.publisher_rows(p)

    def test_original_publisher_pin_has_declared_size_and_hash(self):
        self.assertEqual(m.PUBLISHER_ARCHIVE_BYTES, 680841265)
        self.assertEqual(m.PUBLISHER_ARCHIVE_SHA256,
                         "6d2d5ab50b2ceec6ba5f79c921be77cf2de712ea25a2b3f4fff3acc101cecfa0")
        self.assertIn("ARC-Challenge-Dev.jsonl", m.PUBLISHER_SPLIT)
        self.assertEqual(m.CASES, 24)


if __name__ == "__main__":
    unittest.main()
