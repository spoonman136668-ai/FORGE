"""Actual F139 run_once one-shot mode entry, with no live owner/API action.

The Windows running-owner witness is mocked ONLY in these disposable tests.
The existing scheduler/CLI never passes the optional mode admission arguments.
"""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from f139.local_controller import Database, F139Error, SingleOwner, run_once
from f139.nci04_phase_original_admission import OriginalModeAdmissionDenied
from f139.nci04_phase_mode_replay import read_original_owner_mode
from f139.test_nci04_phase_original_admission import (
    external_provider, owner_comment)
from f139.test_nci04_phase_comment_read import SOURCE


def invoke(db, path, provider, *, comment_id=None, head=None):
    return run_once(
        db, provider, path, "x" * 32,
        now="2026-11-19T02:05:00Z",
        manual_phase_comment_id=comment_id,
        expected_phase_head_sha256=head)


class OriginalTickManualModeTests(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory(prefix="f139-phase-once-tick-")
        path = Path(temp.name) / "state.sqlite"
        db = Database.initialize(path, SOURCE)
        db.enable(legacy_suspended=True)
        return temp, path, db

    def test_no_optional_arguments_has_zero_manual_provider_reads(self):
        temp, path, db = self.fixture()
        p, calls = external_provider([owner_comment(111)])
        try:
            with SingleOwner(path.with_suffix(".lock")):
                result = invoke(db, path, p)
            self.assertEqual(result["disposition"], "QUEUE_EMPTY_NO_SCIENCE")
            self.assertEqual(calls, [])
            self.assertEqual(db.meta()["head_seq"], 1)
        finally:
            db.close()
            temp.cleanup()

    def test_exact_operator_hold_commits_once_inside_original_tick(self):
        temp, path, db = self.fixture()
        p, calls = external_provider([owner_comment(111)])
        try:
            head = db.meta()["head_hash"]
            with patch("f139.local_controller.native_original_running_publisher_profile",
                       return_value=True), SingleOwner(path.with_suffix(".lock")):
                report = invoke(db, path, p, comment_id=111, head=head)
            self.assertEqual(report["disposition"],
                             "PHASE_HOLD_NO_NEW_ADMISSIONS")
            self.assertFalse(report["scientific_first_use"])
            self.assertFalse(report["worker_dispatched"])
            self.assertEqual(db.conn.execute(
                "SELECT COUNT(*) FROM events WHERE kind='PHASE_MODE_ADMITTED'"
            ).fetchone()[0], 1)
            self.assertIn("repos/spoonman136668-ai/FORGE/issues/comments/111",
                          calls)
            db.verify()
        finally:
            db.close()
            temp.cleanup()

    def test_cold_hold_then_explicit_auto_restores_existing_intake(self):
        temp, path, db = self.fixture()
        first, second = owner_comment(111), owner_comment(112, "AUTO")
        p1, _ = external_provider([first])
        try:
            with patch("f139.local_controller.native_original_running_publisher_profile",
                       return_value=True), SingleOwner(path.with_suffix(".lock")):
                r1 = invoke(db, path, p1, comment_id=111,
                            head=db.meta()["head_hash"])
            self.assertEqual(r1["mode"], "HOLD")
            db.close()
            db = Database(path)
            p2, _ = external_provider([first, second], exact=second)
            with patch("f139.local_controller.native_original_running_publisher_profile",
                       return_value=True), SingleOwner(path.with_suffix(".lock")):
                r2 = invoke(db, path, p2, comment_id=112,
                            head=db.meta()["head_hash"])
                state = read_original_owner_mode(
                    db=db, installed_source_sha=SOURCE,
                    protected_main_sha=SOURCE, owner_epoch=1)
            self.assertEqual(r2["disposition"], "QUEUE_EMPTY_NO_SCIENCE")
            self.assertEqual(state["mode"], "AUTO")
            self.assertEqual(state["consumed_comment_ids"], frozenset({111, 112}))
        finally:
            db.close()
            temp.cleanup()

    def test_replay_of_previous_command_refused_at_original_tick(self):
        temp, path, db = self.fixture()
        p, _ = external_provider([owner_comment(111)])
        try:
            with patch("f139.local_controller.native_original_running_publisher_profile",
                       return_value=True), SingleOwner(path.with_suffix(".lock")):
                invoke(db, path, p, comment_id=111,
                       head=db.meta()["head_hash"])
                after = db.meta()
                with self.assertRaises(OriginalModeAdmissionDenied):
                    invoke(db, path, p, comment_id=111,
                           head=db.meta()["head_hash"])
                self.assertEqual(db.meta(), after)
        finally:
            db.close()
            temp.cleanup()

    def test_stale_expected_head_refused_no_comment_reads(self):
        temp, path, db = self.fixture()
        p, calls = external_provider([owner_comment(111)])
        try:
            with SingleOwner(path.with_suffix(".lock")):
                with self.assertRaises(F139Error):
                    invoke(db, path, p, comment_id=111, head="0" * 64)
            self.assertEqual(calls, [])
            self.assertEqual(db.meta()["head_seq"], 1)
        finally:
            db.close()
            temp.cleanup()

    def test_missing_pair_rejected_without_any_provider_effect(self):
        temp, path, db = self.fixture()
        p, calls = external_provider([owner_comment(111)])
        try:
            for opts in ({"comment_id": 111},
                         {"head": db.meta()["head_hash"]},
                         {"comment_id": True, "head": "0" * 64},
                         {"comment_id": 111, "head": "invalid"}):
                with self.subTest(opts=opts):
                    with self.assertRaises(F139Error):
                        invoke(db, path, p, **opts)
            self.assertEqual(calls, [])
            self.assertEqual(db.meta()["head_seq"], 1)
        finally:
            db.close()
            temp.cleanup()

    def test_running_owner_witness_missing_denied_no_event(self):
        temp, path, db = self.fixture()
        p, calls = external_provider([owner_comment(111)])
        try:
            with patch("f139.local_controller.native_original_running_publisher_profile",
                       return_value=False), SingleOwner(path.with_suffix(".lock")):
                with self.assertRaises(OriginalModeAdmissionDenied):
                    invoke(db, path, p, comment_id=111,
                           head=db.meta()["head_hash"])
            self.assertEqual(calls, [])
            self.assertEqual(db.meta()["head_seq"], 1)
        finally:
            db.close()
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
