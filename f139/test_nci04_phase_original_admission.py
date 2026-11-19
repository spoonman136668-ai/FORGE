"""Synthetic original-SQLite atomic writer tests; never a live release.

Mocking the Windows running-owner witness here is TEST ONLY. Production code
cannot skip it. No GitHub POST, scheduled task or original installed DB.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from f139.local_controller import Database, GitHub, SingleOwner
from f139.nci04_phase_comment_read import ISSUE_ROUTE
from f139.nci04_phase_original_admission import (
    ISSUE_COMMENT_ROUTE, OriginalModeAdmissionDenied,
    admit_original_owner_mode_once,
)
from f139.nci04_phase_mode_replay import read_original_owner_mode
from f139.test_nci04_phase_comment_read import provider as fake_provider, SOURCE
from f139.test_nci04_phase_manual_intent import comment, intent


def owner_comment(comment_id: int, mode: str = "HOLD", lane=None) -> dict:
    raw = comment(intent(mode=mode, lane=lane, source=SOURCE, epoch=1))
    raw["id"] = comment_id
    return raw


def external_provider(rows: list[dict], *, exact: dict | None = None,
                      corrupt_exact: bool = False,
                      before_exact=None):
    p, calls = fake_provider(pages=[rows])
    base = p.runner
    selected = exact or rows[0]

    def request(args):
        route = args[0]
        if route.startswith(ISSUE_COMMENT_ROUTE):
            calls.append(route)
            if before_exact is not None:
                before_exact()
            value = dict(selected)
            if corrupt_exact:
                value["updated_at"] = "2026-11-19T00:00:00Z"
            return json.dumps(value).encode()
        return base(args)

    p.runner = request
    # Exact main is simulated by this offline provider. Production provider
    # uses GitHub.protected_main() and the current original source readback.
    p.protected_main = lambda: SOURCE
    return p, calls


def invoke(db, path, p, selected: int, *, head=None):
    return admit_original_owner_mode_once(
        db=db, db_path=path, provider=p,
        selected_comment_id=selected,
        expected_owner_head_sha256=(
            db.meta()["head_hash"] if head is None else head))


class OriginalOwnerModeAdmissionTests(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory(prefix="f139-phase-original-")
        path = Path(temp.name) / "state.sqlite"
        db = Database.initialize(path, SOURCE)
        db.enable(legacy_suspended=True)
        return temp, path, db

    def test_atomic_hold_commit_and_cold_readback(self):
        tmp, path, db = self.fixture()
        p, calls = external_provider([owner_comment(111)])
        try:
            before = db.meta()
            with patch("f139.local_controller.native_original_running_publisher_profile",
                       return_value=True), SingleOwner(path.with_suffix(".lock")):
                result = invoke(db, path, p, 111)
            self.assertEqual(result["mode"], "HOLD")
            self.assertTrue(result["mode_admitted"])
            self.assertFalse(result["worker_dispatched"])
            self.assertFalse(result["scientific_first_use"])
            self.assertFalse(result["self_source_mutation"])
            self.assertEqual(db.meta()["head_seq"], before["head_seq"] + 1)
            self.assertEqual(
                calls.count(ISSUE_COMMENT_ROUTE + "111"), 1)
            db.close()
            ro = Database.open_readonly(path)
            try:
                restored = read_original_owner_mode(
                    db=ro, installed_source_sha=SOURCE,
                    protected_main_sha=SOURCE, owner_epoch=1)
                self.assertEqual(restored["mode"], "HOLD")
                self.assertEqual(restored["consumed_comment_ids"],
                                 frozenset({111}))
            finally:
                ro.close()
        finally:
            try:
                db.close()
            except Exception:
                pass
            tmp.cleanup()

    def test_replayed_comment_is_denied_without_head_change(self):
        tmp, path, db = self.fixture()
        p, _ = external_provider([owner_comment(111)])
        try:
            with patch("f139.local_controller.native_original_running_publisher_profile",
                       return_value=True), SingleOwner(path.with_suffix(".lock")):
                invoke(db, path, p, 111)
                original = db.meta()
                with self.assertRaises(OriginalModeAdmissionDenied):
                    invoke(db, path, p, 111)
                self.assertEqual(db.meta(), original)
        finally:
            db.close()
            tmp.cleanup()

    def test_new_auto_command_explicitly_supersedes_old_hold(self):
        tmp, path, db = self.fixture()
        first = owner_comment(111)
        second = owner_comment(112, "AUTO")
        p, _ = external_provider([first])
        try:
            with patch("f139.local_controller.native_original_running_publisher_profile",
                       return_value=True), SingleOwner(path.with_suffix(".lock")):
                invoke(db, path, p, 111)
                p2, _ = external_provider([first, second], exact=second)
                result = invoke(db, path, p2, 112)
                self.assertEqual(result["mode"], "AUTO")
                history = read_original_owner_mode(
                    db=db, installed_source_sha=SOURCE,
                    protected_main_sha=SOURCE, owner_epoch=1)
                self.assertEqual(history["consumed_comment_ids"],
                                 frozenset({111, 112}))
        finally:
            db.close()
            tmp.cleanup()

    def test_only_oldest_eligible_command_can_be_consumed(self):
        tmp, path, db = self.fixture()
        p, _ = external_provider([owner_comment(111), owner_comment(112)],
                                 exact=owner_comment(112))
        try:
            before = db.meta()
            with patch("f139.local_controller.native_original_running_publisher_profile",
                       return_value=True), SingleOwner(path.with_suffix(".lock")):
                with self.assertRaisesRegex(
                        OriginalModeAdmissionDenied, "NOT_OLDEST_ELIGIBLE"):
                    invoke(db, path, p, 112)
                self.assertEqual(db.meta(), before)
        finally:
            db.close()
            tmp.cleanup()

    def test_edited_comment_denied_before_sqlite_mutation(self):
        tmp, path, db = self.fixture()
        p, _ = external_provider([owner_comment(111)], corrupt_exact=True)
        try:
            before = db.meta()
            with patch("f139.local_controller.native_original_running_publisher_profile",
                       return_value=True), SingleOwner(path.with_suffix(".lock")):
                with self.assertRaises(OriginalModeAdmissionDenied):
                    invoke(db, path, p, 111)
            self.assertEqual(db.meta(), before)
        finally:
            db.close()
            tmp.cleanup()

    def test_head_race_during_comment_readback_denied(self):
        tmp, path, db = self.fixture()
        ran = [False]

        def competing_event():
            if not ran[0]:
                ran[0] = True
                with db.transaction():
                    db.event("DEVELOPMENT_OBSERVATION",
                             {"schema": "forge.f139.source-test-race.v1"})

        p, _ = external_provider([owner_comment(111)],
                                 before_exact=competing_event)
        try:
            with patch("f139.local_controller.native_original_running_publisher_profile",
                       return_value=True), SingleOwner(path.with_suffix(".lock")):
                with self.assertRaises(OriginalModeAdmissionDenied):
                    invoke(db, path, p, 111)
            self.assertTrue(ran[0])
            self.assertEqual(db.conn.execute(
                "SELECT COUNT(*) FROM events WHERE kind='PHASE_MODE_ADMITTED'"
            ).fetchone()[0], 0)
            db.verify()
        finally:
            db.close()
            tmp.cleanup()

    def test_stale_expected_head_denied_before_catalog_read(self):
        tmp, path, db = self.fixture()
        p, calls = external_provider([owner_comment(111)])
        try:
            with patch("f139.local_controller.native_original_running_publisher_profile",
                       return_value=True), SingleOwner(path.with_suffix(".lock")):
                with self.assertRaisesRegex(
                        OriginalModeAdmissionDenied, "OWNER_STATE_OR_HEAD_DRIFT"):
                    invoke(db, path, p, 111, head="0" * 64)
            self.assertEqual(calls, [])
        finally:
            db.close()
            tmp.cleanup()

    def test_unqualified_native_running_witness_denied_without_write(self):
        tmp, path, db = self.fixture()
        p, calls = external_provider([owner_comment(111)])
        try:
            with patch("f139.local_controller.native_original_running_publisher_profile",
                       return_value=False), SingleOwner(path.with_suffix(".lock")):
                with self.assertRaisesRegex(
                        OriginalModeAdmissionDenied, "ORIGINAL_RUNNING_OWNER"):
                    invoke(db, path, p, 111)
            self.assertEqual(calls, [])
            self.assertEqual(db.meta()["head_seq"], 1)
        finally:
            db.close()
            tmp.cleanup()

    def test_absent_mutex_denied_before_network_and_owner_witness(self):
        tmp, path, db = self.fixture()
        p, calls = external_provider([owner_comment(111)])
        try:
            with patch("f139.local_controller.native_original_running_publisher_profile") as witness:
                with self.assertRaisesRegex(
                        OriginalModeAdmissionDenied, "ORIGINAL_MUTEX_OR_DB"):
                    invoke(db, path, p, 111)
                witness.assert_not_called()
            self.assertEqual(calls, [])
        finally:
            db.close()
            tmp.cleanup()

    def test_wrong_original_database_denied(self):
        tmp, path, db = self.fixture()
        p, calls = external_provider([owner_comment(111)])
        try:
            with patch("f139.local_controller.native_original_running_publisher_profile") as witness, SingleOwner(path.with_suffix(".lock")):
                with self.assertRaises(OriginalModeAdmissionDenied):
                    invoke(db, Path(tmp.name) / "other.sqlite", p, 111)
                witness.assert_not_called()
            self.assertEqual(calls, [])
        finally:
            db.close()
            tmp.cleanup()

    def test_disabled_original_controller_denied(self):
        with tempfile.TemporaryDirectory(prefix="f139-phase-original-") as folder:
            path = Path(folder) / "state.sqlite"
            db = Database.initialize(path, SOURCE)
            p, calls = external_provider([owner_comment(111)])
            try:
                with patch("f139.local_controller.native_original_running_publisher_profile",
                           return_value=True), SingleOwner(path.with_suffix(".lock")):
                    with self.assertRaisesRegex(
                            OriginalModeAdmissionDenied, "OWNER_STATE_OR_HEAD_DRIFT"):
                        invoke(db, path, p, 111)
                self.assertEqual(calls, [])
            finally:
                db.close()

    def test_post_append_failure_rolls_back_with_no_replay(self):
        tmp, path, db = self.fixture()
        p, _ = external_provider([owner_comment(111)])
        original_event = db.event

        def crash_after_append(kind, data):
            original_event(kind, data)
            raise RuntimeError("crash-simulated-after-append")

        try:
            before = db.meta()
            with patch("f139.local_controller.native_original_running_publisher_profile",
                       return_value=True), SingleOwner(path.with_suffix(".lock")):
                with patch.object(db, "event", side_effect=crash_after_append):
                    with self.assertRaisesRegex(RuntimeError, "crash-simulated"):
                        invoke(db, path, p, 111)
                self.assertEqual(db.meta(), before)
            db.verify()
        finally:
            db.close()
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
