"""Negative/read-only contracts for a frozen original-owner V59 cold witness.

The SQLite fixture is *not* a surrogate original owner or a release permit.
Full historical verification remains delegated to Database.verify() on the
native original-host RO handle; this unit fixture only tests new boundaries.
"""
from __future__ import annotations

import json
import sqlite3
import unittest
from unittest.mock import patch

from f139 import nci04_v59_owner_forward_readiness as v59


class FakeVerifiedDb:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self._readonly_opened = True
        self._verified = 0
        self._meta = {"source_sha": v59.SOURCE, "head_seq": v59.HEAD_SEQ,
                      "head_hash": v59.HEAD_SHA256,
                      "enabled": 1, "legacy_suspended": 1}
        self.conn.execute("CREATE TABLE events (seq INTEGER, kind TEXT, sha TEXT, payload TEXT)")
        self.conn.execute("CREATE TABLE tasks (stage TEXT)")
        self.conn.executemany("INSERT INTO tasks VALUES (?)",
                              [("VERIFIED",)]*v59.MIN_VERIFIED +
                              [("QUARANTINED",)]*v59.HISTORICAL_NEGATIVES)
        entries = [
            (v59.TRANSITION_SEQ, "SOURCE_TRANSITION_ADMITTED",
             v59.TRANSITION_SHA256, json.dumps({
                 "schema": v59.PREDECESSOR_SCHEMA,
                 "to_source_sha": v59.SOURCE,
                 "scientific_first_use": False})),
            (v59.ACTIVATION_SEQ, "NATIVE_DEVELOPMENT_ACTIVATED",
             v59.ACTIVATION_SHA256, json.dumps({
                 "source_sha": v59.SOURCE, "scientific_first_use": False})),
            (v59.HEAD_SEQ, "NATIVE_V_TWO_PROVIDER_CUSTODY",
             v59.HEAD_SHA256, "{}"),
        ]
        entries += [(i, "MODEL_DRAFT_ATTEMPTED", "a"*64, "{}")
                    for i in range(1, v59.ATTEMPTS + 1)]
        entries += [(300+i, "MODEL_DRAFT_AUTHENTICATED", "b"*64, "{}")
                    for i in range(1, v59.AUTHENTICATED + 1)]
        self.conn.executemany("INSERT INTO events VALUES (?,?,?,?)", entries)
        self.conn.execute("PRAGMA query_only=ON")

    def verify(self):
        self._verified += 1

    def meta(self):
        return dict(self._meta)

    def ready(self):
        return self.conn.execute(
            "SELECT * FROM tasks WHERE stage='READY' LIMIT 1").fetchone()

    def actives(self):
        return self.conn.execute(
            "SELECT * FROM tasks WHERE stage IN ('START_RISK','WAIT_PROVIDER')").fetchall()

    def close(self):
        self.conn.close()


class FrozenV59ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.db = FakeVerifiedDb()
        self.addCleanup(self.db.close)
        patches = (
            patch.object(v59, "Database", FakeVerifiedDb),
            patch.object(v59, "verify_native_activation", return_value=True),
            patch.object(v59, "custodied_ids", return_value={"a"*64, "b"*64}),
        )
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_idle_original_audit_is_nonmutating_and_non_authorizing(self):
        before = self.db.conn.total_changes
        doc = v59.audit_frozen_original_readonly(self.db)
        self.assertEqual(self.db.conn.total_changes, before)
        self.assertGreaterEqual(self.db._verified, 1)
        self.assertEqual(doc["head_seq"], 1864)
        self.assertEqual(doc["source_sha"], v59.SOURCE)
        self.assertEqual(doc["negative_publication_custodies"], 2)
        for key in ("source_transition_authorized", "scientific_first_use",
                    "worker_dispatched", "controller_created", "new_scheduler",
                    "replay_authorized"):
            self.assertIs(doc[key], False)

    def test_reject_wrong_source_or_head_and_expired_owner_state(self):
        self.db._meta["head_seq"] += 1
        with self.assertRaisesRegex(v59.FrozenOwnerReadinessDenied, "HEAD_DRIFT"):
            v59.audit_frozen_original_readonly(self.db)
        self.db._meta["head_seq"] -= 1
        self.db._meta["source_sha"] = "0"*40
        with self.assertRaisesRegex(v59.FrozenOwnerReadinessDenied, "HEAD_DRIFT"):
            v59.audit_frozen_original_readonly(self.db)
        self.db._meta["source_sha"] = v59.SOURCE
        self.db._meta["enabled"] = 0
        with self.assertRaisesRegex(v59.FrozenOwnerReadinessDenied, "HEAD_DRIFT"):
            v59.audit_frozen_original_readonly(self.db)

    def test_reject_unexpected_historical_transition_or_tampered_v47(self):
        self.db.conn.execute("PRAGMA query_only=OFF")
        self.db.conn.execute("UPDATE events SET sha=? WHERE seq=?",
                             ("c"*64, v59.TRANSITION_SEQ))
        self.db.conn.execute("PRAGMA query_only=ON")
        with self.assertRaisesRegex(v59.FrozenOwnerReadinessDenied, "IMMUTABLE_V47"):
            v59.audit_frozen_original_readonly(self.db)

    def test_reject_pending_work_and_wrong_publication_custody(self):
        self.db.conn.execute("PRAGMA query_only=OFF")
        self.db.conn.execute("INSERT INTO tasks VALUES ('READY')")
        self.db.conn.execute("PRAGMA query_only=ON")
        with self.assertRaisesRegex(v59.FrozenOwnerReadinessDenied, "NOT_IDLE"):
            v59.audit_frozen_original_readonly(self.db)
        self.db.conn.execute("PRAGMA query_only=OFF")
        self.db.conn.execute("DELETE FROM tasks WHERE stage='READY'")
        self.db.conn.execute("INSERT INTO events VALUES (?,?,?,?)",
                             (500, "MODEL_DRAFT_ATTEMPTED", "a"*64, "{}"))
        self.db.conn.execute("PRAGMA query_only=ON")
        with self.assertRaisesRegex(v59.FrozenOwnerReadinessDenied, "MODEL_DRAFT"):
            v59.audit_frozen_original_readonly(self.db)

    def test_reject_unauthorized_open_or_non_query_only_db(self):
        self.db._readonly_opened = False
        with self.assertRaisesRegex(v59.FrozenOwnerReadinessDenied, "READONLY_DATABASE"):
            v59.audit_frozen_original_readonly(self.db)
        self.db._readonly_opened = True
        self.db.conn.execute("PRAGMA query_only=OFF")
        with self.assertRaisesRegex(v59.FrozenOwnerReadinessDenied, "QUERY_ONLY"):
            v59.audit_frozen_original_readonly(self.db)

    def test_no_spoofed_database_class(self):
        self.db.__class__ = type("SimilarDb", (FakeVerifiedDb,), {})
        with self.assertRaisesRegex(v59.FrozenOwnerReadinessDenied, "READONLY_DATABASE"):
            v59.audit_frozen_original_readonly(self.db)


if __name__ == "__main__":
    unittest.main()
