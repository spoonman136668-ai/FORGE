"""G4 read-only/source-only tests: original negative and no-replay custody."""
from __future__ import annotations

from contextlib import contextmanager
import json
import sqlite3
import unittest
from unittest.mock import patch

from f139.nci04_owner_publication import (
    G1_ORIGINAL_PARENT, ATTEMPT_KIND, SUCCESS_KIND, history_proof, publish_once,
    OwnerPublicationDenied,
)


class FakeDb:
    def __init__(self, event):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("CREATE TABLE events(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,payload TEXT)")
        self.conn.execute("CREATE TABLE tasks(ticket TEXT,stage TEXT,source_sha TEXT)")
        self.event("NATIVE_DEVELOPMENT_ADMITTED", event)
        self.conn.execute("INSERT INTO tasks VALUES(?,?,?)",
                          (event["ticket"], "QUARANTINED", event["source_sha"]))
        self.head = "a" * 64
        self.source = "b" * 40

    def verify(self):
        pass

    def meta(self):
        return {"enabled": 1, "legacy_suspended": 1,
                "source_sha": self.source, "head_hash": self.head}

    def ready(self):
        return None

    def actives(self):
        return []

    def verified_native_provider_failures(self):
        return {G1_EVENT["ticket"]: (G1_EVENT["source_sha"], "c"*64)}

    @contextmanager
    def transaction(self):
        yield self.conn

    def event(self, kind, payload):
        self.conn.execute("INSERT INTO events VALUES(?,?)",
                          (kind, json.dumps(payload)))
        if kind == ATTEMPT_KIND:
            self.head = "d" * 64


G1_EVENT = {
    "issue_number": 840, "lane": "Yggdrasil",
    "native_path": "yggdrasil/public_causal_cells.py",
    "native_target_commit": G1_ORIGINAL_PARENT,
    "scientific_first_use": False, "ticket": "f139-nci04-i840-abc",
    "source_sha": "a" * 40, "native_intent_base64": "unused",
}


class OriginalOwnerPublicationTests(unittest.TestCase):
    def test_g1_without_original_negative_refuses(self):
        db = FakeDb(G1_EVENT)
        db.conn.execute("UPDATE tasks SET stage='VERIFIED'")
        with self.assertRaisesRegex(OwnerPublicationDenied, "ORIGINAL_NEGATIVE"):
            history_proof(db)

    def test_witness_denied_before_preflight_or_write(self):
        db = FakeDb(G1_EVENT)
        writes = []
        with self.assertRaisesRegex(OwnerPublicationDenied, "WITNESS_REQUIRED"):
            publish_once(db, lambda _: None, lambda *a: writes.append(a),
                         db.source, owner_witness=lambda: False)
        self.assertEqual(writes, [])
        self.assertEqual(list(db.conn.execute(
            "SELECT * FROM events WHERE kind=?", (ATTEMPT_KIND,))), [])

    def test_existing_attempt_never_retries(self):
        db = FakeDb(G1_EVENT)
        db.event(ATTEMPT_KIND, {"candidate_identity": "f"*64})
        writes = []
        result = publish_once(db, lambda _: None, lambda *a: writes.append(a),
                              db.source, owner_witness=lambda: True)
        self.assertEqual(result["disposition"],
                         "G3_DRAFT_ALREADY_ATTEMPTED_NO_REPLAY")
        self.assertEqual(writes, [])

    def test_partial_write_is_recorded_before_remote_call_and_never_retried(self):
        db = FakeDb(G1_EVENT)
        plan = dict(candidate_identity="c"*64, mechanism_sha256="e"*64,
                    parent_commit=G1_ORIGINAL_PARENT, before_blob="f"*40,
                    source_sha256="b"*64)
        observed = []
        def failing_publisher(*args, **kwargs):
            observed.append(len(list(db.conn.execute(
                "SELECT 1 FROM events WHERE kind=?", (ATTEMPT_KIND,)))))
            raise ConnectionError("ambiguous")
        with patch("f139.nci04_owner_publication.history_proof",
                   return_value=(set(), set())), patch(
                "f139.nci04_owner_publication.publisher_preflight",
                return_value=plan), patch(
                "f139.nci04_owner_publication.publish_single_draft",
                side_effect=failing_publisher):
            first = publish_once(db, lambda _: None, lambda *_: None,
                                 db.source, owner_witness=lambda: True)
            second = publish_once(db, lambda _: None, lambda *_: None,
                                  db.source, owner_witness=lambda: True)
        self.assertEqual(observed, [1])
        self.assertEqual(first["disposition"], "G3_DRAFT_OUTCOME_AMBIGUOUS_NO_RETRY")
        self.assertEqual(second["disposition"], "G3_DRAFT_ALREADY_ATTEMPTED_NO_REPLAY")
        self.assertFalse(list(db.conn.execute(
            "SELECT 1 FROM events WHERE kind=?", (SUCCESS_KIND,))))

    def test_preflight_denial_never_writes_or_consumes_attempt(self):
        db = FakeDb(G1_EVENT)
        writes = []
        with patch("f139.nci04_owner_publication.history_proof",
                   return_value=(set(), set())), patch(
                "f139.nci04_owner_publication.publisher_preflight",
                side_effect=ValueError("bad parent")):
            result = publish_once(db, lambda _: None,
                                  lambda *a: writes.append(a),
                                  db.source, owner_witness=lambda: True)
        self.assertEqual(result["disposition"], "G3_PREFLIGHT_BLOCKED")
        self.assertEqual(writes, [])
        self.assertEqual(list(db.conn.execute(
            "SELECT * FROM events WHERE kind=?", (ATTEMPT_KIND,))), [])


if __name__ == "__main__":
    unittest.main()
