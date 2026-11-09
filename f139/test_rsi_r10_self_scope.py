"""R10 one-shot fresh FORGE-self reservation: real SQLite, fake GET."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from f139.local_controller import Database, SingleOwner
from f139.rsi_r10_self_scope import (
    AFTER_RUN, KIND, SelfScopeDenied,
    audit_self_scope, reserve_disabled_development,
)
from f139.rsi_r8_owner_custody import observe_disabled_development
from f139.test_rsi_r7_fresh_failure import (
    fixture, fake, RUN, JOB, HEAD, PATH, LIST1, LIST2, INDEX, RUN_URL, JOB_URL,
)

OWNER = "c" * 40
FRESH = AFTER_RUN + 101


def fresh():
    routes = copy.deepcopy(fixture())
    routes[LIST1]["workflow_runs"][0]["id"] = FRESH
    routes[LIST1]["workflow_runs"][0]["created_at"] = "2026-11-09T01:00:00Z"
    routes[INDEX]["jobs"][0]["run_id"] = FRESH
    routes[RUN_URL]["id"] = FRESH
    routes[JOB_URL]["run_id"] = FRESH
    return fake({
        route.replace(str(RUN), str(FRESH)): value
        for route, value in routes.items()
    })[0]


class OneShotSelfScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "state.sqlite"
        self.db = Database.initialize(self.path, OWNER)
        self.addCleanup(lambda: self.db.close())

    def observed(self, provider):
        return observe_disabled_development(
            db=self.db, provider=provider, run_id=FRESH,
            job_id=JOB, path=PATH, failed_head=HEAD)

    def reserve(self, provider):
        return reserve_disabled_development(
            db=self.db, provider=provider, failed_run_id=FRESH,
            failed_job_id=JOB, target_path=PATH)

    def test_verified_fresh_once_and_cold_reopen_without_authority(self):
        provider = fresh()
        with SingleOwner(self.path.with_suffix(".lock")):
            observed_head = self.observed(provider)
            reserved_head = self.reserve(provider)
            self.assertNotEqual(observed_head, reserved_head)
            self.assertEqual(len(audit_self_scope(self.db)), 1)
            with self.assertRaisesRegex(SelfScopeDenied, "ONE_SHOT_ALREADY_SPENT"):
                self.reserve(provider)
        self.db.close()
        self.db = Database(self.path)
        self.db.verify()
        self.assertEqual(len(audit_self_scope(self.db)), 1)
        self.assertEqual(self.db.meta()["enabled"], 0)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM tasks").fetchone()[0], 0)
        doc = audit_self_scope(self.db)[0]
        self.assertEqual(doc["operator_scope"],
                         "one-fresh-forge-self-development-attempt")
        self.assertFalse(doc["owner_self_scope_authorized"])
        self.assertFalse(doc["worker_dispatched"])
        self.assertFalse(doc["source_promoted"])
        self.assertFalse(doc["scientific_first_use"])

    def test_denies_missing_observation_mutex_and_stale_historical(self):
        provider = fresh()
        with self.assertRaisesRegex(SelfScopeDenied, "ORIGINAL_MUTEX"):
            self.reserve(provider)
        with SingleOwner(self.path.with_suffix(".lock")):
            with self.assertRaisesRegex(
                    SelfScopeDenied, "EXACTLY_ONE_ORIGINAL_OBSERVATION"):
                self.reserve(provider)
            self.observed(provider)
            with self.assertRaisesRegex(SelfScopeDenied, "FRESH_RUN_OR_PATH"):
                reserve_disabled_development(
                    db=self.db, provider=provider,
                    failed_run_id=AFTER_RUN, failed_job_id=JOB,
                    target_path=PATH)
            with self.assertRaisesRegex(SelfScopeDenied, "R8_SCOPE_OR_SOURCE"):
                reserve_disabled_development(
                    db=self.db, provider=provider,
                    failed_run_id=FRESH + 1, failed_job_id=JOB,
                    target_path=PATH)

    def test_denies_live_owner_and_source_drifts(self):
        provider = fresh()
        with SingleOwner(self.path.with_suffix(".lock")):
            self.observed(provider)
            self.db.conn.execute(
                "UPDATE meta SET enabled=1,legacy_suspended=1 WHERE id=1")
            with self.assertRaisesRegex(SelfScopeDenied, "LIVE_OR_NONEMPTY"):
                self.reserve(provider)
            self.db.conn.execute(
                "UPDATE meta SET enabled=0,legacy_suspended=0 WHERE id=1")
            # Authenticated failed job no longer appears in the GET feed.
            # R7 cannot treat the observed R8 event as fresh by itself.
            with self.assertRaises(SelfScopeDenied):
                self.reserve(fake({
                    LIST1: {"workflow_runs": []},
                    LIST2: {"workflow_runs": []},
                })[0])

    def test_event_tamper_and_fake_owner_authority_rejected(self):
        provider = fresh()
        with SingleOwner(self.path.with_suffix(".lock")):
            self.observed(provider)
            self.reserve(provider)
        # Recompute SHA chain to simulate an attacker controlling SQLite
        # file contents, not just an accidental corrupted JSON row.
        row = self.db.conn.execute(
            "SELECT seq,payload,prior_sha FROM events WHERE kind=?", (KIND,)
        ).fetchone()
        doc = json.loads(row["payload"])
        doc["worker_dispatched"] = True
        from f139.local_controller import canonical, hash_bytes
        blob = canonical(doc).decode()
        forged = hash_bytes(canonical({
            "seq": row["seq"], "prior_sha": row["prior_sha"],
            "kind": KIND, "payload": doc}))
        self.db.conn.execute("DROP TRIGGER prevent_event_update")
        self.db.conn.execute(
            "UPDATE events SET payload=?,sha=? WHERE seq=?",
            (blob, forged, row["seq"]))
        self.db.conn.execute(
            "UPDATE meta SET head_hash=? WHERE id=1", (forged,))
        with self.assertRaisesRegex(SelfScopeDenied,
                                    "RESERVATION_FIELDS_OR_AUTHORITY"):
            self.db.verify()

    def test_unchanged_original_owner_lane_and_task_schema(self):
        from f139.local_controller import LANES as OWNER_LANES
        from f139.verify_ticket import LANES as WORKER_LANES
        self.assertNotIn("FORGE-self", OWNER_LANES)
        self.assertNotIn("FORGE-self", WORKER_LANES)
        sql = self.db.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' "
            "AND name='tasks'").fetchone()[0]
        self.assertNotIn("'FORGE-self'", sql)


if __name__ == "__main__":
    unittest.main()
