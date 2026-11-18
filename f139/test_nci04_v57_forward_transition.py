"""V57 exact original event1857 witness and V47 cold replay (synthetic only).

No real original-owner SQLite, runner, provider, workflow or scientific first use.
"""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from f139.local_controller import SingleOwner
from f139.test_nci04_v56_forward_transition import V46SyntheticReadyCarry
from f139.nci04_v56_forward_transition import make_proof as v46_make_proof
from f139.nci04_v57_original_pending_preflight import (
    SOURCE, ORIGINAL_SOURCE, TICKET, ANCHOR_SEQ, ANCHOR_SHA,
    READY_SOURCE_TRANSITION_SHA, V57ReadOnlyDenied,
    original_pending_snapshot,
)
from f139.nci04_v57_forward_transition import (
    FIELDS, SCHEMA, V47TransitionDenied,
    make_proof, verify_cold_event, carried_v47_source,
)
from f139.nci04_v30_source_transition import carried_source


TARGET = "e" * 40


class V57OriginalCarriedTicketFixture(unittest.TestCase):
    def setUp(self):
        fixture = V46SyntheticReadyCarry(
            "test_exact_source_and_ready_custody_are_inert")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.db, self.conn, self.path = fixture.db, fixture.conn, fixture.path
        with SingleOwner(self.path.with_suffix(".lock")):
            v46_proof = v46_make_proof(
                self.db, target=SOURCE, owner_run_id=44352571202,
                qualified_main_run_id=44352571202,
                rehearsal_run_id=44352571217,
                backup_sqlite_sha256="1"*64,
                genenv_executable_sha256="2"*64,
                generation_mechanism_sha256="3"*64,
            )
        self.conn.execute("INSERT INTO events VALUES(?,?,?,?)",
                          (1856, "SOURCE_TRANSITION_ADMITTED",
                           READY_SOURCE_TRANSITION_SHA, json.dumps(v46_proof)))
        self.conn.execute("INSERT INTO events VALUES(?,?,?,?)",
                          (1857, "NATIVE_DEVELOPMENT_ACTIVATED", ANCHOR_SHA,
                           json.dumps({"source_sha": SOURCE,
                                       "scientific_first_use": False})))
        self.conn.execute("UPDATE meta SET source_sha=?, head_seq=?, head_hash=?",
                          (SOURCE, ANCHOR_SEQ, ANCHOR_SHA))
        patches = (
            patch("f139.nci04_v57_original_pending_preflight.verify_native_activation",
                  return_value=True),
            patch("f139.nci04_v57_forward_transition.verify_native_activation",
                  return_value=True),
        )
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.previous = [
            json.loads(x["payload"]) for x in self.conn.execute(
                "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED'"
                " ORDER BY seq"
            )
        ]

    def make_proof(self):
        with SingleOwner(self.path.with_suffix(".lock")):
            return make_proof(
                self.db, target=TARGET, owner_run_id=44399971296,
                qualified_main_run_id=44399971356,
                rehearsal_run_id=44399971296,
                backup_sqlite_sha256="4"*64,
                genenv_executable_sha256="5"*64,
                generation_mechanism_sha256="6"*64,
            )

    def test_exact_current_source_preflight_is_read_only(self):
        before = self.conn.total_changes
        with SingleOwner(self.path.with_suffix(".lock")):
            r = original_pending_snapshot(self.db)
        self.assertEqual(self.conn.total_changes, before)
        self.assertEqual(r["source_sha"], SOURCE)
        self.assertEqual(r["ticket_source_sha"], ORIGINAL_SOURCE)
        self.assertEqual(r["head_seq"], 1857)
        self.assertEqual(r["head_sha256"], ANCHOR_SHA)
        self.assertEqual(r["ticket"], TICKET)
        self.assertEqual(r["ticket_stage"], "READY")
        self.assertFalse(r["release_authorized"])

    def test_v47_cold_proof_cannot_mutate_owner(self):
        before = self.conn.total_changes
        proof = self.make_proof()
        self.assertEqual(before, self.conn.total_changes)
        self.assertEqual(set(proof), FIELDS)
        self.assertEqual(proof["schema"], SCHEMA)
        self.assertEqual(proof["from_source_sha"], SOURCE)
        self.assertEqual(proof["original_ready_source_sha"], ORIGINAL_SOURCE)
        self.assertEqual(proof["original_ready_ticket"], TICKET)
        self.assertEqual(proof["verified_historical_tasks"], 154)
        self.assertEqual(proof["custodied_negative_tasks"], 56)
        self.assertEqual(proof["new_dispatches"], 0)
        self.assertFalse(proof["scientific_first_use"])
        self.assertTrue(verify_cold_event(
            self.db, {"seq":1858,"prior_sha":ANCHOR_SHA}, proof, self.previous))

    def test_v47_only_carries_original_identity_under_current_source(self):
        proof = self.make_proof()
        self.assertIsNone(carried_v47_source(self.db, TICKET))
        self.conn.execute("INSERT INTO events VALUES(?,?,?,?)",
                          (1858, "SOURCE_TRANSITION_ADMITTED",
                           "a"*64, json.dumps(proof)))
        self.conn.execute("UPDATE meta SET source_sha=?", (TARGET,))
        self.assertEqual(carried_v47_source(self.db, TICKET), ORIGINAL_SOURCE)
        self.assertEqual(carried_source(self.db, TICKET), ORIGINAL_SOURCE)
        self.assertIsNone(carried_v47_source(self.db, "wrong-ticket"))
        self.conn.execute(
            "UPDATE tasks SET stage='START_RISK',started_at=? WHERE ticket=?",
            ("2026-11-18T22:00:00Z",TICKET))
        self.assertEqual(carried_v47_source(self.db, TICKET), ORIGINAL_SOURCE)
        self.conn.execute(
            "UPDATE tasks SET manifest_sha=? WHERE ticket=?",
            ("b"*64, TICKET))
        self.assertIsNone(carried_v47_source(self.db, TICKET))

    def test_changed_original_anchor_source_or_spent_ticket_rejected(self):
        scenarios = [
            ("UPDATE meta SET source_sha=?", ("d"*40,)),
            ("UPDATE meta SET head_hash=?", ("d"*64,)),
            ("UPDATE meta SET head_seq=?", (1858,)),
            ("UPDATE tasks SET run_id=? WHERE ticket=?", (42,TICKET)),
            ("UPDATE tasks SET stage=? WHERE ticket=?", ("START_RISK",TICKET)),
            ("UPDATE tasks SET manifest_sha=? WHERE ticket=?", ("f"*64,TICKET)),
            ("UPDATE events SET sha=? WHERE seq=1856", ("f"*64,)),
            ("UPDATE events SET sha=? WHERE seq=1857", ("f"*64,)),
        ]
        for sql,args in scenarios:
            with self.subTest(sql=sql):
                self.conn.execute("SAVEPOINT scenario")
                try:
                    self.conn.execute(sql,args)
                    with SingleOwner(self.path.with_suffix(".lock")):
                        with self.assertRaises(V57ReadOnlyDenied):
                            original_pending_snapshot(self.db)
                finally:
                    self.conn.execute("ROLLBACK TO scenario")
                    self.conn.execute("RELEASE scenario")

    def test_no_pretransition_start_or_additional_ready(self):
        self.conn.execute(
            "INSERT INTO events VALUES(?,?,?,?)",
            (1810, "BEFORE_DISPATCH_INTENT", "f"*64,
             json.dumps({"ticket": TICKET})))
        try:
            with SingleOwner(self.path.with_suffix(".lock")):
                with self.assertRaisesRegex(V57ReadOnlyDenied, "SPENT"):
                    original_pending_snapshot(self.db)
        finally:
            self.conn.execute("DELETE FROM events WHERE seq=1810")
        self.conn.execute(
            "INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?)",
            ("other", "Wingless",SOURCE,"READY","a"*64,
             None,None,None,None,None))
        try:
            with SingleOwner(self.path.with_suffix(".lock")):
                with self.assertRaisesRegex(V57ReadOnlyDenied, "EXCLUSIVITY"):
                    original_pending_snapshot(self.db)
        finally:
            self.conn.execute("DELETE FROM tasks WHERE ticket='other'")

    def test_v47_proof_negative_controls(self):
        proof = self.make_proof()
        cases = [
            ("scientific_first_use", True),
            ("new_dispatches", 1),
            ("new_scheduler", True),
            ("paid_api_calls", True),
            ("source_transition_purpose", "not-release"),
            ("original_ready_source_sha", SOURCE),
            ("original_ready_ticket", "other"),
            ("original_intake_sha256", "f"*64),
            ("original_ready_identity_sha256", "f"*64),
            ("terminal_tasks_sha256", "f"*64),
            ("custodied_negative_tasks", 0),
            ("owner_run_id", 44396465727),
        ]
        for field,val in cases:
            with self.subTest(field=field):
                with self.assertRaises(V47TransitionDenied):
                    verify_cold_event(self.db,
                        {"seq":1858,"prior_sha":ANCHOR_SHA},
                        dict(proof,**{field:val}),self.previous)


if __name__ == "__main__":
    unittest.main()
