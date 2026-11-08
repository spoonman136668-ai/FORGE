"""R8 owner SQLite no-replay: offline real transaction and negative controls."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from f139.local_controller import Database, SingleOwner
from f139.rsi_r8_owner_custody import (
    KIND, R8CustodyDenied, audit_observed_scopes,
    observe_disabled_development, recorded_scopes,
)
from f139.test_rsi_r7_fresh_failure import (
    fixture, fake, RUN, JOB, PATH, HEAD, LOG_URL, LIST1,
)
from f139.rsi_r7_fresh_failure import scan

OWNER = "b" * 40


class ObservationCustodyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "state.sqlite"
        self.db = Database.initialize(self.path, OWNER)
        self.addCleanup(self.db.close)

    def record(self, provider=None, *, job=JOB, head=HEAD):
        if provider is None:
            provider, _ = fake(fixture())
        return observe_disabled_development(
            db=self.db, provider=provider, run_id=RUN,
            job_id=job, path=PATH, failed_head=head)

    def test_real_wal_record_survives_cold_open_and_r7_excludes_replay(self):
        before = dict(self.db.meta())
        with SingleOwner(self.path.with_suffix(".lock")):
            digest = self.record()
            self.assertNotEqual(digest, before["head_hash"])
            self.assertEqual(self.db.meta()["head_seq"], before["head_seq"] + 1)
            scopes = recorded_scopes(self.db)
            self.assertEqual(len(scopes), 1)
            report = scan(
                provider=fake(fixture())[0], after_run_id=RUN-1,
                not_before_utc="2026-11-08T21:54:00Z",
                target_path=PATH, consumed_scopes=scopes)
            self.assertEqual(report.proposals, ())
            self.assertIn("SCOPE_ALREADY_CONSUMED", report.rejection_codes[0][1])
            with self.assertRaises(R8CustodyDenied):
                self.record()
            self.assertEqual(digest, self.db.meta()["head_hash"])
        self.db.close()
        cold = Database.open_readonly(self.path)
        try:
            self.assertEqual(cold.meta()["head_hash"], digest)
            self.assertEqual(recorded_scopes(cold), scopes)
            self.assertEqual(cold.meta()["head_seq"], before["head_seq"] + 1)
        finally:
            cold.close()
        self.db = Database(self.path)

    def test_no_mutex_denied_before_any_provider_read_or_write(self):
        provider, calls = fake(fixture())
        prior = dict(self.db.meta())
        with self.assertRaisesRegex(R8CustodyDenied, "MUTEX_NOT_HELD"):
            self.record(provider)
        self.assertEqual(calls, [])
        self.assertEqual(dict(self.db.meta()), prior)

    def test_live_owner_and_nonempty_queue_fail_closed(self):
        provider, calls = fake(fixture())
        with SingleOwner(self.path.with_suffix(".lock")):
            self.db.conn.execute("UPDATE meta SET enabled=1,legacy_suspended=1 WHERE id=1")
            try:
                with self.assertRaisesRegex(R8CustodyDenied, "LIVE_OR_NONEMPTY"):
                    self.record(provider)
                self.assertEqual(calls, [])
            finally:
                self.db.conn.execute("UPDATE meta SET enabled=0,legacy_suspended=0 WHERE id=1")

    def test_spoofed_failed_run_cannot_create_event(self):
        for name, patch in (
            ("actor", {"actor": {"login": "other"}}),
            ("attempt", {"run_attempt": 2}),
            ("source", {"head_sha": "a"*40}),
            ("repo", {"head_repository": {"full_name": "unknown/repo"}}),
        ):
            with self.subTest(name=name):
                routes = fixture()
                routes["repos/spoonman136668-ai/FORGE/actions/runs/"+str(RUN)].update(patch)
                p, _ = fake(routes)
                with SingleOwner(self.path.with_suffix(".lock")):
                    with self.assertRaises(R8CustodyDenied):
                        self.record(p)
                self.assertEqual(self.db.meta()["head_seq"], 0)

    def test_failed_log_no_repair_no_custody(self):
        routes = fixture()
        routes[LOG_URL] = b"unrelated build failure without sqlite\n"
        p, _ = fake(routes)
        with SingleOwner(self.path.with_suffix(".lock")):
            with self.assertRaisesRegex(R8CustodyDenied, "READBACK_DENIED"):
                self.record(p)
        self.assertEqual(self.db.meta()["head_seq"], 0)

    def test_forged_owner_permission_event_rejected_and_transaction_rolls_back(self):
        with SingleOwner(self.path.with_suffix(".lock")):
            self.record()
            prior = self.db.meta()["head_hash"]
            row = self.db.conn.execute(
                "SELECT payload FROM events WHERE kind=?", (KIND,)).fetchone()
            payload = json.loads(row["payload"])
            payload["owner_self_scope_authorized"] = True
            with self.assertRaises(R8CustodyDenied):
                with self.db.transaction():
                    # Append a cryptographically consistent yet unauthorized record.
                    # The original persistent event is never updated/deleted.
                    self.db.event(KIND, payload)
                    self.db.verify()
            self.assertEqual(self.db.meta()["head_hash"], prior)

    def test_original_transition_with_stale_owner_source_cannot_be_reused(self):
        # An event can be hash-valid but source-invalid; the new cold audit denies.
        with SingleOwner(self.path.with_suffix(".lock")):
            self.record()
            prior = self.db.meta()["head_hash"]
            event = self.db.conn.execute(
                "SELECT payload FROM events WHERE kind=?", (KIND,)).fetchone()
            payload = json.loads(event["payload"])
            payload["owner_source_sha"] = "a" * 40
            with self.assertRaises(R8CustodyDenied):
                with self.db.transaction():
                    payload["prior_event_head_sha256"] = self.db.meta()["head_hash"]
                    self.db.event(KIND, payload)
                    self.db.verify()
            self.assertEqual(self.db.meta()["head_hash"], prior)


if __name__ == "__main__":
    unittest.main()
