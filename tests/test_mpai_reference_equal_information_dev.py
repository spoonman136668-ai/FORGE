"""No-model negative controls for MP-AI10 matched-information development design."""
import hashlib
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from mpai_reference_equal_information_dev import (
    ARMS, TASKS, PREVIOUS_QUESTIONS, verify_same_record
)

SHA = "a" * 40
STATEMENT = (
    "In an eight-question development-only comparison using 16 genuine "
    "local CPU calls, input tokens fell from 3,513 to 1,665, "
    "with the same 96-token output cap in both arms; "
    "but there were no independent factual accuracy grades "
    "or scientific improvement claim exist in this accepted lesson."
)
REFS = [{"type": "acceptance", "ref": "source"}]


def pair():
    pointer = {
        "id": "lesson/mpai-hindsight-h2-development-context-efficiency-20261028",
        "project": "Mind-Palace",
        "kind": "lesson",
        "status": "observed",
        "source_refs": REFS,
        "statement": "reference only",
        "retrieval_preview_kind": "reference_only",
        "full_record_required": True,
        "source_statement_sha256": hashlib.sha256(
            STATEMENT.encode("utf-8")).hexdigest(),
    }
    result = {
        "source_sha": SHA,
        "records_sha256": "b" * 64,
        "scope": ["Mind-Palace"],
        "matches": [pointer],
    }
    a = {
        "receipt": {
            "reference_followup": "disabled",
            "resolved_reference_count": 0,
            "read_only": True,
        },
        "result": result,
    }
    b = {
        "receipt": {
            "reference_followup": "enabled",
            "resolved_reference_count": 1,
            "read_only": True,
        },
        "result": dict(result, resolved_reference_records=[
            {"id": pointer["id"], "project": "Mind-Palace",
             "kind": "lesson", "status": "observed",
             "source_refs": REFS, "statement": STATEMENT}
        ]),
    }
    return a, b


class StudyControls(unittest.TestCase):
    def test_frozen_tasks_are_unique_and_not_prior_four(self):
        self.assertEqual(len(TASKS), 12)
        self.assertEqual(len({t[0] for t in TASKS}), 12)
        self.assertFalse({t[0] for t in TASKS} &
                         {t[0] for t in PREVIOUS_QUESTIONS})
        self.assertEqual(ARMS, ("direct", "reflect"))
        self.assertEqual({t[2] for t in TASKS}, {"YES", "NO", "UNKNOWN"})

    def test_full_evidence_is_exactly_same_statement(self):
        a, b = pair()
        self.assertEqual(verify_same_record(a, b, SHA), STATEMENT)

    def test_source_drift_or_provenance_fails_closed(self):
        a, b = pair()
        with self.assertRaises(RuntimeError):
            verify_same_record(a, b, "c" * 40)
        a, b = pair()
        b["result"]["resolved_reference_records"][0]["source_refs"] = []
        with self.assertRaises(RuntimeError):
            verify_same_record(a, b, SHA)

    def test_no_full_record_fails_closed(self):
        a, b = pair()
        b["result"]["resolved_reference_records"] = []
        with self.assertRaises(RuntimeError):
            verify_same_record(a, b, SHA)


if __name__ == "__main__":
    unittest.main()
