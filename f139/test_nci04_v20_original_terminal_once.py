"""Fail-closed test for original V20 one-shot V3 terminal custody.

Synthetic only: no live owner lock, DPAPI credentials, GitHub POST, or SQLite
mutation. The original Windows host remains the sole terminal authority.
"""
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from f139 import nci04_v20_original_terminal_once as once


class FakeConnection:
    terminal = False

    def execute(self, query, args=()):
        if "PROVIDER_VERIFIED_TERMINAL" in query:
            return [("already-settled",)] if self.terminal else []
        raise AssertionError("Unexpected original SQLite query: " + query)


class FakeDatabase:
    filename = Path("synthetic-original-state.sqlite")
    head_seq = once.HEAD_SEQ
    head_hash = once.HEAD_HASH
    stage = "WAIT_PROVIDER"
    rows = 1
    source = once.SOURCE

    def __init__(self):
        self.conn = FakeConnection()

    def verify(self):
        return None

    def meta(self):
        return {"source_sha": self.source, "enabled": 1,
                "legacy_suspended": 1, "head_seq": self.head_seq,
                "head_hash": self.head_hash}

    def actives(self):
        return [{"ticket": once.TICKET, "source_sha": self.source,
                 "stage": self.stage, "started_at": once.STARTED,
                 "run_id": None} for _ in range(self.rows)]

    def ready(self):
        return None


class OriginalV20OnceTests(TestCase):
    def setUp(self):
        self.db = FakeDatabase()
        self.lock = patch.object(once, "SingleOwner")
        self.owner = self.lock.start()
        self.owner.held.return_value = True
        self.typepatch = patch.object(once, "Database", FakeDatabase)
        self.typepatch.start()
        self.nativepatch = patch.object(once, "verify_native_activation", return_value=True)
        self.nativepatch.start()
        self.addCleanup(self.lock.stop)
        self.addCleanup(self.typepatch.stop)
        self.addCleanup(self.nativepatch.stop)

    def test_read_only_gate_accepts_exact_signed_original_pending_state(self):
        once.inspect_original(self.db)
        self.owner.held.assert_called_once_with(
            self.db.filename.with_suffix(".lock"))

    def test_original_mutex_cannot_be_bypassed(self):
        self.owner.held.return_value = False
        with self.assertRaisesRegex(once.OriginalTerminalDenied,
                                    "OWNER_LOCK_REQUIRED"):
            once.inspect_original(self.db)

    def test_exact_original_ledger_head_required(self):
        self.db.head_seq += 1
        with self.assertRaisesRegex(once.OriginalTerminalDenied,
                                    "EVENT_HEAD_CHANGED"):
            once.inspect_original(self.db)

    def test_exact_original_source_required(self):
        self.db.source = "1" * 40
        with self.assertRaisesRegex(once.OriginalTerminalDenied,
                                    "EVENT_HEAD_CHANGED"):
            once.inspect_original(self.db)

    def test_no_second_ready_or_active_original_task(self):
        self.db.rows = 2
        with self.assertRaisesRegex(once.OriginalTerminalDenied,
                                    "PENDING_TICKET_CHANGED"):
            once.inspect_original(self.db)

    def test_duplicate_terminal_event_rejected(self):
        self.db.conn.terminal = True
        with self.assertRaisesRegex(once.OriginalTerminalDenied,
                                    "TERMINAL_ALREADY_EXISTS"):
            once.inspect_original(self.db)

    def test_reject_nonexistent_original_database_or_short_key(self):
        with self.assertRaisesRegex(once.OriginalTerminalDenied,
                                    "DB_PATH_OR_OWNER_KEY_INVALID"):
            once.settle_one_original(
                Path("f139-this-file-must-not-exist.sqlite"),
                "not-the-real-secret")

    def test_workflow_is_exactly_manual_owner_issue_trigger_not_new_scheduler(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/f139-v20-v3-original-terminal-once.yml"
                    ).read_text(encoding="utf-8")
        self.assertIn("issue_comment:", workflow)
        self.assertNotIn("workflow_dispatch:", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertIn("github.event.issue.number == 807", workflow)
        self.assertIn("FORGE-CODEX-REMOTE", workflow)
        self.assertIn("F139-V20-V3-TERMINAL ", workflow)
        self.assertIn("Enable-ScheduledTask", workflow)
        self.assertIn("F139_V20_TERMINAL_COLD_SQLITE_BACKUP=PASS", workflow)
        self.assertIn("F139_V20_TERMINAL_EXISTING_TASK_RESUMED=PASS", workflow)
        self.assertIn("nci04_v20_original_terminal_once", workflow)


if __name__ == "__main__":
    import unittest
    unittest.main()
