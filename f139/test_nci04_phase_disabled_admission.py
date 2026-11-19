"""Development-only atomic fixture gate; no external provider or live owner."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import tempfile
import unittest

from f139.local_controller import Database, SingleOwner
from f139.nci04_phase_disabled_admission import (
    DevelopmentAdmissionDenied, admit_disposable_intent,
)
from f139.nci04_phase_mode_replay import read_original_owner_mode
from f139.test_nci04_phase_manual_intent import comment, intent, SOURCE


@contextmanager
def disposable():
    with tempfile.TemporaryDirectory(prefix="f139-phase-dev-") as folder:
        path = Path(folder) / "disabled.sqlite"
        db = Database.initialize(path, SOURCE)
        try:
            with SingleOwner(path.with_suffix(".lock")):
                yield db
        finally:
            db.close()


def request(mode="HOLD", *, comment_id=121, epoch=1, lane=None):
    raw = comment(intent(mode=mode, lane=lane, source=SOURCE, epoch=epoch))
    raw["id"] = comment_id
    return raw


def commit(db, raw, *, head=None, source=SOURCE, epoch=1):
    return admit_disposable_intent(
        db=db, comment=raw, installed_source_sha=source,
        protected_main_sha=source, owner_epoch=epoch,
        expected_head_sha256=db.meta()["head_hash"] if head is None else head)


class DisabledAtomicModeAdmissionTests(unittest.TestCase):
    def test_first_hold_commits_exactly_one_event(self):
        with disposable() as db:
            before = db.meta()
            receipt = commit(db, request())
            after = db.meta()
            self.assertEqual(after["head_seq"], before["head_seq"] + 1)
            self.assertEqual(receipt["event_head_sha256"], after["head_hash"])
            self.assertEqual(receipt["mode"], "HOLD")
            self.assertTrue(receipt["disposable_only"])
            for flag in ("owner_live_updated", "dispatch_authorized",
                         "scientific_first_use", "self_source_mutation",
                         "checkpoint_mutation", "accepted_ref_mutation"):
                self.assertFalse(receipt[flag])
            db.verify()

    def test_hold_survives_restart_and_allows_explicit_auto_supersession(self):
        with tempfile.TemporaryDirectory(prefix="f139-phase-dev-") as folder:
            path = Path(folder) / "disabled.sqlite"
            db = Database.initialize(path, SOURCE)
            with SingleOwner(path.with_suffix(".lock")):
                hold = commit(db, request())
            db.close()
            ro = Database.open_readonly(path)
            try:
                restored = read_original_owner_mode(
                    db=ro, installed_source_sha=SOURCE,
                    protected_main_sha=SOURCE, owner_epoch=1)
                self.assertEqual(restored["mode"], "HOLD")
                self.assertEqual(restored["last_comment_id"], 121)
                self.assertFalse(restored["dispatch_authorized"])
            finally:
                ro.close()
            db = Database(path)
            try:
                with SingleOwner(path.with_suffix(".lock")):
                    auto = commit(db, request("AUTO", comment_id=122))
                self.assertEqual(auto["mode"], "AUTO")
                self.assertEqual(db.meta()["head_seq"], hold["event_seq"] + 1)
                db.verify()
            finally:
                db.close()

    def test_duplicate_comment_is_denied_without_history_change(self):
        with disposable() as db:
            raw = request()
            commit(db, raw)
            before = db.meta()
            with self.assertRaises(DevelopmentAdmissionDenied):
                commit(db, raw)
            self.assertEqual(db.meta(), before)

    def test_stale_expected_head_never_advances(self):
        with disposable() as db:
            previous = db.meta()["head_hash"]
            commit(db, request())
            before = db.meta()
            with self.assertRaises(DevelopmentAdmissionDenied):
                commit(db, request("RESEARCH", comment_id=122), head=previous)
            self.assertEqual(db.meta(), before)

    def test_stale_owner_epoch_is_denied(self):
        with disposable() as db:
            before = db.meta()
            with self.assertRaises(DevelopmentAdmissionDenied):
                commit(db, request(epoch=2))
            self.assertEqual(db.meta(), before)

    def test_forged_metadata_is_denied(self):
        with disposable() as db:
            raw = request()
            raw["user"] = {"login": "nonowner", "id": 42}
            with self.assertRaises(DevelopmentAdmissionDenied):
                commit(db, raw)
            self.assertEqual(db.meta()["head_seq"], 0)

    def test_live_enabled_database_is_unconditionally_denied(self):
        with disposable() as db:
            with db.transaction():
                db.conn.execute("UPDATE meta SET enabled=1 WHERE id=1")
            before = db.meta()
            with self.assertRaises(DevelopmentAdmissionDenied):
                commit(db, request())
            self.assertEqual(db.meta(), before)

    def test_nonempty_task_database_is_denied(self):
        with disposable() as db:
            with db.transaction():
                db.conn.execute(
                    "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha) "
                    "VALUES (?,?,?,?,?)",
                    ("fixture-nonempty", "Wingless", SOURCE,
                     "QUARANTINED", "a" * 64))
            before = db.meta()
            with self.assertRaises(DevelopmentAdmissionDenied):
                commit(db, request())
            self.assertEqual(db.meta(), before)

    def test_unlocked_fixture_is_denied(self):
        with tempfile.TemporaryDirectory(prefix="f139-phase-dev-") as folder:
            path = Path(folder) / "disabled.sqlite"
            db = Database.initialize(path, SOURCE)
            try:
                with self.assertRaises(DevelopmentAdmissionDenied):
                    commit(db, request())
                self.assertEqual(db.meta()["head_seq"], 0)
            finally:
                db.close()

    def test_wrong_name_fixture_is_denied(self):
        with tempfile.TemporaryDirectory(prefix="f139-phase-dev-") as folder:
            path = Path(folder) / "original-owner.sqlite"
            db = Database.initialize(path, SOURCE)
            try:
                with SingleOwner(path.with_suffix(".lock")):
                    with self.assertRaises(DevelopmentAdmissionDenied):
                        commit(db, request())
                self.assertEqual(db.meta()["head_seq"], 0)
            finally:
                db.close()

    def test_transaction_rolls_back_after_append_failure(self):
        with disposable() as db:
            before = db.meta()
            original = db.event

            def interrupted(kind, payload):
                original(kind, payload)
                raise RuntimeError("fixture-rollback-test")

            with patch.object(db, "event", side_effect=interrupted):
                with self.assertRaises(RuntimeError):
                    commit(db, request())
            self.assertEqual(db.meta(), before)
            db.verify()
            recovered = read_original_owner_mode(
                db=db, installed_source_sha=SOURCE,
                protected_main_sha=SOURCE, owner_epoch=1)
            self.assertEqual(recovered["mode"], "AUTO")
            self.assertIsNone(recovered["last_comment_id"])

    def test_research_training_and_self_improvement_remain_only_modes(self):
        with disposable() as db:
            receipts = [
                commit(db, request(mode, comment_id=122 + i,
                                   lane="Wingless" if mode == "RESEARCH" else None))
                for i, mode in enumerate(("RESEARCH", "TRAIN", "SELF_IMPROVE"))
            ]
            self.assertEqual([r["mode"] for r in receipts],
                             ["RESEARCH", "TRAIN", "SELF_IMPROVE"])
            self.assertEqual(receipts[-1]["event_seq"], 3)
            db.verify()


if __name__ == "__main__":
    unittest.main()
