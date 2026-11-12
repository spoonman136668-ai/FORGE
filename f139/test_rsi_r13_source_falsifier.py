"""R13 source-authenticated Go repair, falsifier and memory ablation tests."""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import unittest

from f139.rsi_r13_source_falsifier import (
    TARGET, ORIGINAL_BLOB, FalsifierDenied, Prior, git_blob,
    inspect_and_propose, rank_review_options,
)

# Original bytes are authenticated by the exact pinned Git blob, but stored in
# this repository so future shallow CI checkouts need no historical commit.
FIXTURE = Path(__file__).resolve().parent / "testdata" / "rsi_r13_original_watchdog.go.txt"
EXPECTED_CANDIDATE_BLOB = "2911bc2005f229941500ae1a28e4d8c887c382d5"


def original_source() -> bytes:
    if FIXTURE.is_symlink() or not FIXTURE.is_file():
        raise AssertionError("original R13 source fixture missing or unsafe")
    raw = FIXTURE.read_bytes()
    if git_blob(raw) != ORIGINAL_BLOB:
        raise AssertionError("original R13 source fixture Git blob drift")
    return raw


def memory(task: str, family: str, option: str, outcome: str,
           cohort: str = "train") -> Prior:
    return Prior(task, family, option,
                 sha256(("source-" + task).encode()).hexdigest(),
                 sha256(("test-" + task).encode()).hexdigest(),
                 outcome, cohort)


class R13SourceFalsifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.before = original_source()
        cls.after = inspect_and_propose(
            path=TARGET, source=cls.before,
            expected_blob=ORIGINAL_BLOB).candidate

    def test_authentic_existing_go_source_and_exact_generated_patch(self) -> None:
        self.assertEqual(git_blob(self.before), ORIGINAL_BLOB)
        result = inspect_and_propose(
            path=TARGET, source=self.before, expected_blob=ORIGINAL_BLOB)
        self.assertEqual(result.candidate, self.after)
        self.assertEqual(git_blob(result.candidate), EXPECTED_CANDIDATE_BLOB)
        self.assertNotEqual(result.before_sha256, result.after_sha256)
        self.assertEqual(sha256(self.after).hexdigest(), result.after_sha256)
        self.assertEqual(result.hazard, "bounded-json-truncation-after-stat")
        self.assertTrue(result.original_reproducer_required)
        self.assertFalse(result.engineering_qualified)
        self.assertFalse(result.original_owner_admitted)
        self.assertFalse(result.scientific_first_use)
        self.assertFalse(result.autonomous_rsi_proven)
        self.assertFalse(result.deployed)

    def test_source_scope_replay_and_drift_rejection(self) -> None:
        correct = {"path": TARGET, "source": self.before,
                   "expected_blob": ORIGINAL_BLOB}
        for variation, why in (
            ({"path": "f139/local_controller.py"}, "TARGET_SCOPE"),
            ({"expected_blob": "0" * 40}, "TARGET_SCOPE"),
            ({"source": self.before + b"\n"}, "SOURCE_BLOB_DRIFT"),
            ({"source": self.after}, "SOURCE_BLOB_DRIFT"),
            ({"source": b""}, "SOURCE_BLOB_DRIFT"),
            ({"source": self.before.replace(b"65537", b"65538")},
             "SOURCE_BLOB_DRIFT"),
        ):
            with self.subTest(variation=variation.keys()), self.assertRaisesRegex(
                    FalsifierDenied, why):
                inspect_and_propose(**(correct | variation))

    def test_current_checkout_is_never_an_approved_owner_patch(self) -> None:
        # Regression: a successful source generator is not a source-admission token.
        result = inspect_and_propose(
            path=TARGET, source=self.before, expected_blob=ORIGINAL_BLOB)
        self.assertFalse(result.original_owner_admitted)
        self.assertFalse(result.autonomous_rsi_proven)

    def test_training_only_memory_changes_review_order_vs_static_control(self) -> None:
        options = ("strict-sentinel", "reject-on-size-drift", "no-change")
        prior = (
            memory("prior-a", "other-file-a", "strict-sentinel", "FAIL"),
            memory("prior-b", "other-file-b", "reject-on-size-drift", "PASS"),
            memory("prior-c", "other-file-c", "strict-sentinel", "FAIL"),
        )
        plain = rank_review_options(
            options=options, history=prior, current_family=TARGET,
            excluded_task_ids=frozenset({"heldout-1"}), use_memory=False)
        learned = rank_review_options(
            options=options, history=prior, current_family=TARGET,
            excluded_task_ids=frozenset({"heldout-1"}), use_memory=True)
        self.assertEqual(plain.ranked, options)
        self.assertEqual(learned.ranked[0], "reject-on-size-drift")
        self.assertNotEqual(plain.ranked, learned.ranked)
        self.assertFalse(learned.eligible_for_owner)
        self.assertFalse(learned.science_accepted)
        self.assertFalse(learned.rsi_proven)

    def test_memory_contamination_and_custody_fail_closed(self) -> None:
        valid = memory("train-a", "other-path", "strict-sentinel", "PASS")
        baseline = dict(options=("strict-sentinel", "no-change"),
                        current_family=TARGET,
                        excluded_task_ids=frozenset({"heldout-a"}),
                        use_memory=True)
        corrupt = [
            (valid, valid),  # task-ID replay
            (valid, replace(valid, task_id="renamed-replay")),  # same source + test
            (replace(valid, task_id="heldout-a"),),
            (replace(valid, source_family=TARGET),),
            (replace(valid, source_sha256="0"),),
            (replace(valid, test_sha256="a" * 63),),
            (replace(valid, outcome="UNVERIFIED"),),
            (replace(valid, cohort="holdout"),),
            (replace(valid, mechanism="unknown"),),
            tuple(memory("task-" + str(i), "family-" + str(i),
                         "strict-sentinel", "PASS") for i in range(129)),
        ]
        for case in corrupt:
            with self.subTest(case=case[:1]), self.assertRaises(FalsifierDenied):
                rank_review_options(history=case, **baseline)
        with self.assertRaises(FalsifierDenied):
            rank_review_options(history=(), options=("no-change", "no-change"),
                                current_family=TARGET,
                                excluded_task_ids=frozenset(), use_memory=False)
        with self.assertRaises(FalsifierDenied):
            rank_review_options(history=(), options=("unknown",),
                                current_family=TARGET,
                                excluded_task_ids=frozenset(), use_memory=False)

    def test_empty_history_does_not_claim_memorized_learning(self) -> None:
        res = rank_review_options(
            options=("strict-sentinel", "no-change"), history=(),
            current_family=TARGET, excluded_task_ids=frozenset(),
            use_memory=True)
        self.assertFalse(res.memory_used)
        self.assertFalse(res.rsi_proven)


if __name__ == "__main__":
    unittest.main()
