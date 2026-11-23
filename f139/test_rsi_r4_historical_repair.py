"""R4 negative source-custody controls; no historical repair outcome is run."""
from dataclasses import replace
from pathlib import Path
import unittest

from f139.rsi_r4_historical_repair import (
    COHORTS, MAX_BYTES, ORIGIN, PREREG_BLOB, PREREG_PATH, SCHEMA, TASKS,
    ReplayDenied, Task, _checked_source, candidate_source_identity,
    check_prereg_bytes, git_blob, inspect_original_pair, validate_catalog,
)

ROOT = Path(__file__).resolve().parents[1]


class HistoricalRepairInventoryTests(unittest.TestCase):
    def test_prereg_separate_commit_and_frozen_corpus(self):
        doc = (ROOT / PREREG_PATH).read_bytes()
        # Windows default checkout line endings are not the historical Git
        # blob bytes; authenticate normalized stored bytes, not the worktree.
        doc = doc.replace(b"\r\n", b"\n")
        self.assertTrue(check_prereg_bytes(doc))
        self.assertEqual(git_blob(doc), PREREG_BLOB)
        self.assertTrue(validate_catalog())
        self.assertEqual(ORIGIN, "cf727267007d0637abd8d8cd98a0fbbbd37f2752")
        self.assertEqual(len(TASKS), 6)
        self.assertEqual([t.pr for t in TASKS], [1434, 1508, 1517, 1525, 1334, 1543])
        self.assertEqual([t.cohort for t in TASKS],
                         ["train", "train", "validation", "historic_holdout",
                          "historic_holdout", "format_negative"])
        self.assertEqual({t.cohort for t in TASKS}, COHORTS)
        self.assertEqual(len({(t.pr, t.path) for t in TASKS}), len(TASKS))
        groups = {}
        for task in TASKS:
            groups.setdefault(task.path, set()).add(task.cohort)
        self.assertTrue(all(len(values) == 1 for values in groups.values()))
        self.assertLessEqual(MAX_BYTES, 400_000)

    def test_frozen_task_mutations_deny(self):
        for bad in (
            TASKS[:-1], TASKS + (TASKS[-1],), tuple(reversed(TASKS)),
            tuple(replace(t, cohort="train") if t.pr == 1525 else t
                  for t in TASKS),
            tuple(replace(t, before_blob="0" * 40) if t.pr == 1434 else t
                  for t in TASKS),
            tuple(replace(t, path="../f139/local_controller.py") if t.pr == 1517 else t
                  for t in TASKS),
        ):
            with self.subTest(sample=bad), self.assertRaises(ReplayDenied):
                validate_catalog(bad)

    def test_prereg_source_tamper_and_type_denied(self):
        doc = (ROOT / PREREG_PATH).read_bytes().replace(b"\r\n", b"\n")
        for bad in (doc+b"x", doc[:-1], doc.replace(b"RSI-R4", b"RSI-R5"),
                    None, "not bytes"):
            with self.subTest(kind=type(bad)), self.assertRaises(ReplayDenied):
                check_prereg_bytes(bad)

    def test_source_git_blob_and_parse_guards(self):
        simple = b"def solve(x):\n    return x + 1\n"
        sha = git_blob(simple)
        self.assertEqual(_checked_source(simple, sha, "f139/fix.py"), simple)
        for bad, expected in (
            (simple + b"\n# changed\n", "SOURCE_GIT_BLOB_DRIFT"),
            (b"def solve(:\n", "SOURCE_GIT_BLOB_DRIFT"),
            (b"", "SOURCE_TYPE_OR_SIZE"),
            ("def solve(): pass", "SOURCE_TYPE_OR_SIZE"),
        ):
            with self.subTest(bad=str(bad)[:40]), self.assertRaisesRegex(
                    ReplayDenied, expected):
                _checked_source(bad, sha, "f139/fix.py")
        malformed = b"def solve(:\n"
        with self.assertRaisesRegex(ReplayDenied, "SOURCE_PYTHON_INVALID"):
            _checked_source(malformed, git_blob(malformed), "f139/fix.py")
        with self.assertRaisesRegex(ReplayDenied, "SOURCE_TYPE_OR_SIZE"):
            _checked_source(b"x" * (MAX_BYTES + 1),
                            git_blob(b"x" * (MAX_BYTES + 1)), "f139/fix.py")

    def test_pinned_source_reader_rejects_invalid_evidence(self):
        calls = []
        def wrong_reader(sha, path):
            calls.append((sha, path))
            return b"def f(): return None\n"
        with self.assertRaisesRegex(ReplayDenied, "SOURCE_GIT_BLOB_DRIFT"):
            inspect_original_pair(TASKS[0], wrong_reader)
        self.assertEqual(calls, [(TASKS[0].before_commit, TASKS[0].path)])
        with self.assertRaisesRegex(ReplayDenied, "READ_ONLY_SOURCE_GET_REQUIRED"):
            inspect_original_pair(TASKS[0], None)
        with self.assertRaisesRegex(ReplayDenied, "UNDECLARED_REPAIR_TASK"):
            inspect_original_pair(replace(TASKS[0], pr=9999), wrong_reader)
        with self.assertRaisesRegex(ReplayDenied, "UNDECLARED_REPAIR_TASK"):
            candidate_source_identity(replace(TASKS[0], pr=9999), b"x", b"y")

    def test_format_negative_and_no_forged_repair_success(self):
        fmt = TASKS[-1]
        self.assertEqual(fmt.cohort, "format_negative")
        with self.assertRaisesRegex(ReplayDenied, "FORMAT_CHANGE_NOT_LEARNING"):
            candidate_source_identity(fmt, b"original", b"changed")
        with self.assertRaisesRegex(ReplayDenied, "SOURCE_GIT_BLOB_DRIFT"):
            candidate_source_identity(TASKS[0], b"untrusted", b"changed")
        self.assertEqual(SCHEMA, "forge.f139.rsi-r4.historical-repair-replay.v1")


if __name__ == "__main__":
    unittest.main()
