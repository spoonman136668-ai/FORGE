"""Source-independent qualification checks for public external-family dev gate."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import mpai11_external_family_transfer as x


def fixture():
    rows = []
    for i in range(299):
        rows.append({
            "id": "external-" + str(i).zfill(3),
            "question": {
                "stem": "Which science concept supports this independent scenario " + str(i) + "?",
                "choices": [
                    {"label": label, "text": label + " explanation " + str(i),
                     "para": "LEAK_ONLY_NEVER_PROMPT"}
                    for label in "ABCD"
                ],
            },
            "answerKey": "ABCD"[i % 4],
        })
    return rows


class ExternalSourceControls(unittest.TestCase):
    def test_git_blob_and_public_row_count_enforced(self):
        raw = ("\n".join(json.dumps(r) for r in fixture()) + "\n").encode("utf-8")
        digest = hashlib.sha1(
            b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw).hexdigest()
        with patch.object(x, "MIRROR_GIT_BLOB_SHA1", digest):
            rows, claimed_sha = x.validate_public_blob(raw)
        self.assertEqual(len(rows), 299)
        self.assertEqual(claimed_sha, hashlib.sha256(raw).hexdigest())
        with self.assertRaises(RuntimeError):
            x.validate_public_blob(raw + b" ")
        with patch.object(x, "MIRROR_GIT_BLOB_SHA1", digest):
            with self.assertRaises(RuntimeError):
                x.validate_public_blob(raw.replace(b"external-000", b"external-999"))

    def test_case_selection_has_no_answer_key_or_retrieval_para(self):
        tasks, gold, cohort = x.freeze_public_cohort(fixture())
        self.assertEqual(len(tasks), x.CASES)
        self.assertEqual(len(gold), x.CASES)
        self.assertEqual(len(cohort), 64)
        self.assertEqual(set(t["id"] for t in tasks), set(gold))
        self.assertEqual(
            {k for task in tasks for k in task},
            {"id", "question", "choices"},
        )
        for task in tasks:
            self.assertNotIn("answerKey", json.dumps(task))
            self.assertNotIn("LEAK_ONLY_NEVER_PROMPT", json.dumps(task))
            self.assertNotIn("para", json.dumps(task))

    def test_cohort_is_invariant_to_values_of_valid_gold_letters(self):
        original = fixture()
        tasks, _, digest = x.freeze_public_cohort(original)
        changed = fixture()
        for row in changed:
            row["answerKey"] = "A"
        alternative, _, sha = x.freeze_public_cohort(changed)
        self.assertEqual(tasks, alternative)
        self.assertEqual(digest, sha)

    def test_prompt_equal_evidence_and_no_gold(self):
        tasks, gold, _ = x.freeze_public_cohort(fixture())
        task = tasks[0]
        for arm in x.ARMS:
            rendered = x.prompt(task, x.POLICIES[arm], "One advisory memory.")
            self.assertIn("One advisory memory.", rendered)
            self.assertIn(task["question"], rendered)
            self.assertNotIn("answerKey", rendered)
            self.assertNotIn("LEAK_ONLY_NEVER_PROMPT", rendered)
            self.assertIn("A:", rendered)
            self.assertIn("D:", rendered)
        self.assertEqual(set(x.POLICIES), set(x.ARMS))
        self.assertIn(task["id"], gold)

    def test_duplicate_fails_closed(self):
        rows = fixture()
        rows[-1]["id"] = rows[0]["id"]
        with self.assertRaises(RuntimeError):
            x.freeze_public_cohort(rows)

    def test_question_family_disjoint_from_mpai10(self):
        from mpai_reference_equal_information_dev import TASKS
        ids, _, _ = x.freeze_public_cohort(fixture())
        self.assertFalse({x["id"] for x in ids} & {t[0] for t in TASKS})
        self.assertEqual(x.MIRROR_COMMIT, "ae51da706ed693b99e7de41c418dad13845e3c09")
        self.assertEqual(x.MIRROR_GIT_BLOB_SHA1,
                         "907d3294123dbe34929e1fb802c2504d698f7dbd")


if __name__ == "__main__":
    unittest.main()
