"""V41 postcommit HOLD: real SQLite event-pair readback in disposable fixture.

The original Windows controller task and user account are not accessed here.
The real prior negative-event history is independently qualified by the
existing native source suite; this tests the postcommit witness/receipt
boundary using a synthetic high-water fixture and mocked full-history replay.
"""
from contextlib import closing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner
from f139 import nci04_v41_atomic_copy_rehearsal as atomic
from f139 import nci04_v41_native_original_commit as commit
from f139 import nci04_v41_native_postcommit_hold as hold
from f139 import nci04_v41_source_transition as source
from f139 import nci04_v41_pending_escrow as escrow

from f139.test_nci04_v41_atomic_copy_rehearsal import (
    cold_receipt, preserved, owner_intent, synthetic_proof, TARGET, SOURCE,
    HEAD)


class NativePostcommitHoldTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.file = Path(folder.name) / "original.sqlite"
        with patch.object(Database, "verify", return_value=None):
            with closing(Database.initialize(self.file, SOURCE)) as db:
                db.conn.execute(
                    "UPDATE meta SET enabled=1,legacy_suspended=1,"
                    "head_seq=?,head_hash=? WHERE id=1",
                    (escrow.OBSERVED_SEQ, HEAD))
                self.before = db.meta().copy()
                with SingleOwner(self.file.with_suffix(".lock")):
                    with patch.object(source, "build_proof",
                                      side_effect=synthetic_proof):
                        produced = atomic._commit_pair_under_existing_owner_lock(
                            db, original_meta=self.before, target=TARGET,
                            binary_sha="7"*64, toolchain=source.TOOLCHAIN,
                            pending_receipt=preserved(),
                            owner_intent=owner_intent())
        self.receipt = {
            "schema": commit.RECEIPT,
            "original_source_sha": SOURCE,
            "target_source_sha": TARGET,
            "original_head_seq": self.before["head_seq"],
            "committed_head_seq": produced["copy_head_seq"],
            "committed_head_sha256": produced["copy_head_sha256"],
            "escrow_event_sha256": produced["escrow_event_sha256"],
            "sealed_manifest_sha256": "a"*64,
            "release_pr_number": 123,
            "owner_install_comment_id": 456,
            "source_event_owner_approval_id": owner_intent()["owner_comment_id"],
            "original_sqlite_committed": True,
            "owner_task_still_disabled": True,
            "policy_activated": False,
            "native_task_retargeted": False,
            "owner_execution_accepted": False,
            "scientific_first_use": False,
            "hybrid_admission": False,
            "new_dispatches": 0,
        }

    def inspect(self, receipt=None):
        with patch.object(Database, "verify", return_value=None):
            with SingleOwner(self.file.with_suffix(".lock")):
                with closing(Database.open_readonly(self.file)) as db:
                    before = db.meta().copy()
                    changes = db.conn.total_changes
                    outcome = hold.verify_pair_readonly(
                        db, self.receipt if receipt is None else receipt)
                    self.assertEqual(db.meta(), before)
                    self.assertEqual(db.conn.total_changes, changes)
                    self.assertEqual(db.conn.execute(
                        "PRAGMA query_only").fetchone()[0], 1)
                    return outcome

    def test_genuine_two_event_sqlite_postcommit_hold_stays_disarmed(self):
        outcome = self.inspect()
        self.assertEqual(outcome["source_sha"], TARGET)
        self.assertEqual(outcome["committed_head_seq"],
                         escrow.OBSERVED_SEQ+2)
        self.assertEqual(outcome["escrow_event_sha256"],
                         self.receipt["escrow_event_sha256"])
        self.assertTrue(outcome["pending_1715_unadmitted"])
        self.assertTrue(outcome["original_sqlite_cold_verified"])
        for key in ("source_transition_authorized", "postinstall_accepted",
                    "scientific_first_use", "hybrid_admission"):
            self.assertFalse(outcome[key])
        self.assertEqual(outcome["original_owner_mutations"], 0)
        self.assertEqual(outcome["new_dispatches"], 0)

    def test_unlocked_or_writable_handle_refused(self):
        with patch.object(Database, "verify", return_value=None):
            with closing(Database.open_readonly(self.file)) as db:
                with self.assertRaisesRegex(
                        hold.V41PostcommitDenied,
                        "ORIGINAL_LOCKED_QUERY_ONLY_REQUIRED"):
                    hold.verify_pair_readonly(db, self.receipt)
            with SingleOwner(self.file.with_suffix(".lock")):
                with closing(Database(self.file)) as writer:
                    with self.assertRaisesRegex(
                            hold.V41PostcommitDenied,
                            "ORIGINAL_LOCKED_QUERY_ONLY_REQUIRED"):
                        hold.verify_pair_readonly(writer, self.receipt)

    def test_forged_execution_permit_and_uncommitted_receipt_refused(self):
        variants = (
            ("schema", "forged"),
            ("original_source_sha", TARGET),
            ("target_source_sha", SOURCE),
            ("original_sqlite_committed", False),
            ("owner_task_still_disabled", False),
            ("policy_activated", True),
            ("native_task_retargeted", True),
            ("owner_execution_accepted", True),
            ("scientific_first_use", True),
            ("hybrid_admission", True),
            ("new_dispatches", 1),
            ("sealed_manifest_sha256", "invalid"),
            ("original_head_seq", escrow.OBSERVED_SEQ-1),
            ("committed_head_seq", escrow.OBSERVED_SEQ+1),
        )
        for key, value in variants:
            with self.subTest(key=key):
                bad = dict(self.receipt, **{key: value})
                with self.assertRaises(hold.V41PostcommitDenied):
                    self.inspect(bad)

    def test_committed_head_or_escrow_sha_drift_refused(self):
        for field in ("committed_head_sha256", "escrow_event_sha256"):
            with self.subTest(field=field):
                bad = dict(self.receipt, **{field: "0"*64})
                with self.assertRaises(hold.V41PostcommitDenied):
                    self.inspect(bad)

    def test_source_approval_id_changed_refused(self):
        bad = dict(self.receipt, source_event_owner_approval_id=999)
        with self.assertRaisesRegex(
                hold.V41PostcommitDenied,
                "ESCROW_1715_OR_TRANSITION_AUTHORITY_DRIFT"):
            self.inspect(bad)

    def test_bad_orphaned_escrow_audit_refuses_even_if_receipt_looks_valid(self):
        with patch.object(escrow, "audit_committed_escrow",
                          return_value="PROVISIONAL_OWNER_TRANSACTION"):
            with self.assertRaisesRegex(
                    hold.V41PostcommitDenied,
                    "MISSING_MISMATCHED_OR_REPLAYED_EVENT_PAIR"):
                self.inspect()

    def test_native_entrypoint_never_operates_on_hosted_linux_or_ci_windows(self):
        from f139.local_controller import GitHub
        with self.assertRaisesRegex(
                hold.V41PostcommitDenied, "NATIVE_ORIGINAL_HOST_ONLY"):
            hold.inspect_original_postcommit_hold(
                self.file, self.file.parent, receipt=self.receipt,
                api=object.__new__(GitHub))


if __name__ == "__main__":
    unittest.main()
