"""F139 original-owner native activation capacity is source-bound, not ten.

Synthetic ledger fixture tests only the historical activation source chain.
Real original negative custody is independently verified by Database.verify
and the Windows scratch rehearsal; neither can be waived by these tests.
"""
from __future__ import annotations

import json
import sqlite3
import unittest

from f139.nci04_owner_ledger import (
    ACTIVATION_KIND, ACTIVATION_SCHEMA, NativeLedgerDenied,
    SEALED_OWNER_PREFIX_HEAD, verify_native_activation,
)


def source(n):
    return f"{n:040x}"


class FakeOwnerLedger:
    def __init__(self, n=11):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            "CREATE TABLE events (seq INTEGER PRIMARY KEY, kind TEXT, "
            "payload TEXT, prior_sha TEXT)")
        self.conn.execute("CREATE TABLE tasks (ticket TEXT, source_sha TEXT)")
        self.conn.execute(
            "INSERT INTO tasks VALUES('f139-d2c-frozen-original',?)",
            (source(1),))
        seq = 1
        for i in range(n):
            if i:
                self.conn.execute(
                    "INSERT INTO events(seq,kind,payload,prior_sha)"
                    " VALUES(?,?,?,?)",
                    (seq, "SOURCE_TRANSITION_ADMITTED",
                     json.dumps({"to_source_sha": source(i + 1)}),
                     source(101 + seq)))
                seq += 1
            prior = source(900 + seq)
            self.conn.execute(
                "INSERT INTO events(seq,kind,payload,prior_sha)"
                " VALUES(?,?,?,?)",
                (seq, ACTIVATION_KIND, json.dumps({
                    "schema": ACTIVATION_SCHEMA,
                    "source_sha": source(i + 1),
                    "prior_event_head_sha256": prior,
                    "sealed_original_prefix_sha256":
                        SEALED_OWNER_PREFIX_HEAD,
                    "verified_original_tasks": 4,
                    "verified_d2k_tasks": 2,
                    "new_dispatches": 0,
                    "scientific_first_use": False,
                    "development_only": True,
                }), prior))
            seq += 1
        self.source_sha = source(n)

    def meta(self):
        return {"source_sha": self.source_sha}


class F139ActivationCapacityTests(unittest.TestCase):
    def test_eleven_distinct_original_source_activations_are_valid(self):
        db = FakeOwnerLedger(11)
        self.assertTrue(verify_native_activation(db))
        self.assertEqual(db.conn.execute(
            "SELECT COUNT(*) FROM events WHERE kind=?",
            (ACTIVATION_KIND,)).fetchone()[0], 11)

    def test_extra_activation_without_source_transition_denied(self):
        db = FakeOwnerLedger(11)
        db.conn.execute(
            "DELETE FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' "
            "AND seq=(SELECT MAX(seq) FROM events "
            "WHERE kind='SOURCE_TRANSITION_ADMITTED')")
        with self.assertRaisesRegex(
                NativeLedgerDenied,
                "ACTIVATION_EXCEEDS_SOURCE_TRANSITION_COUNT"):
            verify_native_activation(db)

    def test_reused_source_authority_is_not_reactivated(self):
        db = FakeOwnerLedger(11)
        r = db.conn.execute(
            "SELECT seq,payload FROM events WHERE kind=? ORDER BY seq DESC "
            "LIMIT 1", (ACTIVATION_KIND,)).fetchone()
        doc = json.loads(r["payload"])
        doc["source_sha"] = source(10)
        db.conn.execute("UPDATE events SET payload=? WHERE seq=?",
                        (json.dumps(doc), r["seq"]))
        with self.assertRaisesRegex(
                NativeLedgerDenied, "NATIVE_ACTIVATION_SOURCE_REPLAY"):
            verify_native_activation(db)

    def test_new_protected_source_requires_its_own_activation(self):
        db = FakeOwnerLedger(11)
        db.conn.execute(
            "INSERT INTO events(seq,kind,payload,prior_sha) VALUES(?,?,?,?)",
            (30, "SOURCE_TRANSITION_ADMITTED",
             json.dumps({"to_source_sha": source(12)}), source(920)))
        db.source_sha = source(12)
        self.assertFalse(verify_native_activation(db))

    def test_empty_history_never_claims_activated(self):
        db = FakeOwnerLedger(1)
        db.conn.execute("DELETE FROM events")
        self.assertFalse(verify_native_activation(db))


if __name__ == "__main__":
    unittest.main()
