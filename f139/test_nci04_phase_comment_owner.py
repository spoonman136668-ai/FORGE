"""Read-only original F139 owner/ledger/issue-comment intake preflight."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from f139.local_controller import Database, GitHub, SingleOwner
from f139.nci04_phase_comment_read import (
    ISSUE_ROUTE, COMMENT_ROUTE, PhaseCommentReadDenied,
    inspect_original_owner_pending_intents,
)
from f139.nci04_phase_mode_replay import KIND
from f139.test_nci04_phase_comment_read import provider, SOURCE
from f139.test_nci04_phase_manual_intent import comment, intent
from f139.test_nci04_phase_mode_replay import admission


def read(db, path, provider_, *, source=SOURCE):
    return inspect_original_owner_pending_intents(
        db=db, db_path=path, provider=provider_,
        protected_main_sha=source)


def owner_comment(comment_id=111, mode="HOLD"):
    # Database.initialize creates epoch=1; do not weaken the authenticated
    # request's strict source/epoch match to make a fixture pass.
    raw = comment(intent(mode=mode, source=SOURCE, epoch=1))
    raw["id"] = comment_id
    return raw


class OriginalOwnerPhaseCommentReadTests(unittest.TestCase):
    def test_original_lock_and_cold_database_read_do_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite"
            db = Database.initialize(path, SOURCE)
            p, calls = provider(pages=[[owner_comment()]])
            try:
                old = db.meta()
                with SingleOwner(path.with_suffix(".lock")):
                    result = read(db, path, p)
                self.assertEqual(calls, [ISSUE_ROUTE, COMMENT_ROUTE + "1"])
                self.assertEqual(result["last_persisted_mode"], "AUTO")
                self.assertEqual(result["original_head_sha256"], old["head_hash"])
                self.assertEqual(len(result["pending"]), 1)
                self.assertTrue(result["original_owner_ledger_verified"])
                self.assertFalse(result["owner_admitted"])
                self.assertFalse(result["dispatch_authorized"])
                self.assertEqual(db.meta(), old)
            finally:
                db.close()

    def test_consumed_comment_is_reconstructed_from_original_sqlite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite"
            db = Database.initialize(path, SOURCE)
            try:
                with db.transaction():
                    db.event(KIND, admission(
                        mode="HOLD", comment_id=110,
                        prior=db.meta()["head_hash"]))
                db.verify()
                p, _ = provider(pages=[[owner_comment(110),
                                        owner_comment(111, "AUTO")]])
                with SingleOwner(path.with_suffix(".lock")):
                    result = read(db, path, p)
                self.assertEqual(result["last_persisted_mode"], "HOLD")
                self.assertEqual(result["last_persisted_mode_comment_id"], 110)
                self.assertEqual([x["comment_id"] for x in result["pending"]],
                                 [111])
            finally:
                db.close()

    def test_original_lock_absence_and_source_drift_deny_before_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite"
            db = Database.initialize(path, SOURCE)
            p, calls = provider()
            try:
                with self.assertRaises(PhaseCommentReadDenied):
                    read(db, path, p)
                with SingleOwner(path.with_suffix(".lock")):
                    with self.assertRaises(PhaseCommentReadDenied):
                        read(db, path, p, source="b" * 40)
                self.assertEqual(calls, [])
            finally:
                db.close()

    def test_original_database_path_drift_denied_before_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite"
            db = Database.initialize(path, SOURCE)
            p, calls = provider()
            try:
                with SingleOwner(path.with_suffix(".lock")):
                    with self.assertRaises(PhaseCommentReadDenied):
                        read(db, Path(tmp) / "absent.sqlite", p)
                self.assertEqual(calls, [])
            finally:
                db.close()

    def test_mutated_ledger_during_get_denied_after_original_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite"
            db = Database.initialize(path, SOURCE)
            p, calls = provider(pages=[[owner_comment()]])
            original_runner = p.runner
            once = [False]

            def racing_provider(args):
                if args == [ISSUE_ROUTE] and not once[0]:
                    once[0] = True
                    with db.transaction():
                        db.event("DEVELOPMENT_OBSERVATION", {
                            "schema": "forge.f139.synthetic-race.v1"})
                return original_runner(args)

            p = GitHub(runner=racing_provider)
            try:
                with SingleOwner(path.with_suffix(".lock")):
                    with self.assertRaisesRegex(
                            PhaseCommentReadDenied,
                            "ORIGINAL_LEDGER_CHANGED_DURING_PROVIDER_READ"):
                        read(db, path, p)
                self.assertTrue(once[0])
                self.assertEqual(db.meta()["head_seq"], 1)
                db.verify()
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
