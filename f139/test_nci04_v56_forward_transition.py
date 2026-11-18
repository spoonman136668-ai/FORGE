"""V46 synthetic, source-only proof and carry; never original-owner execution."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from f139.local_controller import SingleOwner
from f139.test_nci04_v56_original_pending_preflight import (
    V56OriginalPendingReadOnly,
)
from f139.nci04_v56_original_pending_preflight import SOURCE, TICKET, ANCHOR_SHA
from f139.nci04_v56_forward_transition import (
    SCHEMA, FIELDS, V46TransitionDenied, make_proof,
    verify_cold_event, carried_v46_source,
)

TARGET = "f" * 40
OLD = "b" * 40


class V46SyntheticReadyCarry(V56OriginalPendingReadOnly):
    def setUp(self):
        super().setUp()
        negatives = [f"q{i:04d}" for i in range(56)]
        previous = {
            "schema": "forge.f139.source-transition.v45",
            "from_source_sha": OLD, "to_source_sha": SOURCE,
            "custodied_negative_tickets": negatives,
        }
        self.conn.execute(
            "UPDATE events SET payload=? WHERE seq=1850",
            (json.dumps(previous),)
        )
        for i in range(154):
            self.conn.execute(
                "INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?)",
                (f"p{i:04d}", "Wingless", OLD, "VERIFIED", "a"*64,
                 i+1, None, "sealed", "b"*64, None)
            )
        for ticket in negatives:
            self.conn.execute(
                "INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?)",
                (ticket, "Yggdrasil", OLD, "QUARANTINED", "a"*64,
                 None, None, None, None, "preserved")
            )
        self.previous = [previous]
        self.addCleanup(
            patch.stopall
        )
        p = patch(
            "f139.nci04_v56_forward_transition.verify_native_activation",
            return_value=True,
        )
        p.start()
        self.addCleanup(p.stop)

    def args(self):
        return dict(
            target=TARGET, owner_run_id=44352571202,
            qualified_main_run_id=44352571202,
            rehearsal_run_id=44352571217,
            backup_sqlite_sha256="1"*64,
            genenv_executable_sha256="2"*64,
            generation_mechanism_sha256="3"*64,
        )

    def proof(self):
        with SingleOwner(self.path.with_suffix(".lock")):
            return make_proof(self.db, **self.args())

    def test_exact_source_and_ready_custody_are_inert(self):
        before = self.conn.total_changes
        proof = self.proof()
        self.assertEqual(before, self.conn.total_changes)
        self.assertEqual(set(proof), FIELDS)
        self.assertEqual(proof["schema"], SCHEMA)
        self.assertEqual(proof["original_ready_ticket"], TICKET)
        self.assertEqual(proof["verified_historical_tasks"], 154)
        self.assertEqual(proof["custodied_negative_tasks"], 56)
        self.assertEqual(proof["new_dispatches"], 0)
        self.assertFalse(proof["scientific_first_use"])

    def test_no_implicit_ticket_carry(self):
        self.assertIsNone(carried_v46_source(self.db, TICKET))
        self.assertIsNone(carried_v46_source(self.db, "other"))
        doc = self.proof()
        self.conn.execute(
            "INSERT INTO events VALUES(?,?,?,?)",
            (1856, "SOURCE_TRANSITION_ADMITTED", "c"*64, json.dumps(doc))
        )
        self.conn.execute("UPDATE meta SET source_sha=?", (TARGET,))
        self.assertEqual(carried_v46_source(self.db, TICKET), SOURCE)
        self.assertIsNone(carried_v46_source(self.db, "other"))
        self.conn.execute("UPDATE tasks SET stage='START_RISK',started_at=? "
                          "WHERE ticket=?", ("2026-11-18T17:00:00Z", TICKET))
        self.assertEqual(carried_v46_source(self.db, TICKET), SOURCE)
        self.conn.execute(
            "UPDATE tasks SET manifest_sha=? WHERE ticket=?",
            ("c"*64, TICKET)
        )
        self.assertIsNone(carried_v46_source(self.db, TICKET))

    def test_negative_custody_and_preexisting_dispatch_rejected(self):
        doc = self.proof()
        for field, value in [
            ("scientific_first_use", True),
            ("native_development_approved", False),
            ("new_dispatches", 1),
            ("paid_api_calls", True),
            ("original_ready_ticket", "other"),
            ("original_ready_source_sha", "c"*40),
            ("original_admission_sha256", "a"*64),
            ("custodied_negative_tasks", 0),
            ("terminal_tasks_sha256", "a"*64),
            ("source_transition_purpose", "not-approved"),
            ("to_source_sha", SOURCE),
        ]:
            with self.subTest(field=field):
                with self.assertRaises(V46TransitionDenied):
                    verify_cold_event(
                        self.db, {"seq": 1856, "prior_sha": ANCHOR_SHA},
                        dict(doc, **{field: value}), self.previous,
                    )
        self.conn.execute(
            "INSERT INTO events VALUES(?,?,?,?)",
            (1855, "BEFORE_DISPATCH_INTENT", "d"*64,
             json.dumps({"ticket": TICKET}))
        )
        with self.assertRaisesRegex(V46TransitionDenied, "SPENT"):
            verify_cold_event(
                self.db, {"seq": 1856, "prior_sha": ANCHOR_SHA},
                doc, self.previous,
            )

    def test_cold_verifier_accepts_event_after_original_stage_changes(self):
        doc = self.proof()
        self.conn.execute(
            "UPDATE tasks SET stage='WAIT_PROVIDER',started_at=? WHERE ticket=?",
            ("2026-11-18T17:00:00Z", TICKET)
        )
        self.conn.execute(
            "INSERT INTO events VALUES(?,?,?,?)",
            (1858, "BEFORE_DISPATCH_INTENT", "d"*64,
             json.dumps({"ticket": TICKET}))
        )
        self.assertTrue(verify_cold_event(
            self.db, {"seq": 1856, "prior_sha": ANCHOR_SHA},
            doc, self.previous,
        ))

if __name__ == "__main__":
    unittest.main()
