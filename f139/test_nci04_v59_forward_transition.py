"""V48 source-transition read-only replay negative controls.

Synthetic SQLite deliberately lacks a valid original owner signature; no
test exercises the live scheduler, provider, write route or native adoption.
"""
from __future__ import annotations

import json
import sqlite3
import unittest
from copy import deepcopy
from unittest.mock import patch
from pathlib import Path

from f139 import nci04_v59_forward_transition as v48


class FakeColdSource:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            "CREATE TABLE events (seq INTEGER,kind TEXT,sha TEXT,payload TEXT)")
        self.conn.execute(
            "CREATE TABLE tasks (ticket TEXT,lane TEXT,source_sha TEXT,"
            "stage TEXT,manifest_sha TEXT,run_id INTEGER,evidence_dir TEXT,"
            "evidence_sha TEXT,quarantine_reason TEXT)")
        self.previous = [{
            "schema": v48.PREDECESSOR_SCHEMA,
            "from_source_sha": "0"*40, "to_source_sha": v48.SOURCE,
            "custodied_negative_tickets": ["old-native-negative"],
        }]
        for i in range(155):
            self.conn.execute(
                "INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?)",
                ("v"+str(i), "Yggdrasil", v48.SOURCE, "VERIFIED",
                 "a"*64, i+1, "fixed/evidence", "b"*64, None))
        for i in range(56):
            self.conn.execute(
                "INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?)",
                ("q"+str(i), "Wingless", v48.SOURCE, "QUARANTINED",
                 "a"*64, None, None, None, "CERTIFIED_NEGATIVE"))
        source_events = (
            (v48.TRANSITION_SEQ, "SOURCE_TRANSITION_ADMITTED",
             v48.TRANSITION_SHA256, json.dumps(self.previous[-1])),
            (v48.ACTIVATION_SEQ, "NATIVE_DEVELOPMENT_ACTIVATED",
             v48.ACTIVATION_SHA256, json.dumps({
                 "source_sha": v48.SOURCE,
                 "scientific_first_use": False})),
            (v48.HEAD_SEQ, "NATIVE_V_TWO_PROVIDER_CUSTODY",
             v48.HEAD_SHA256, "{}"),
        )
        self.conn.executemany("INSERT INTO events VALUES (?,?,?,?)",
                              source_events)
        self.ids = [f"{i+1:064x}" for i in range(v48.AUTHENTICATED)]
        self.ids.extend(v48.FROZEN_IDS)
        for i, candidate in enumerate(self.ids):
            self.conn.execute(
                "INSERT INTO events VALUES (?,?,?,?)",
                (i+1, "MODEL_DRAFT_ATTEMPTED", "d"*64,
                 json.dumps({"candidate_identity": candidate})))
        for i, candidate in enumerate(self.ids[:v48.AUTHENTICATED]):
            self.conn.execute(
                "INSERT INTO events VALUES (?,?,?,?)",
                (i+300, "MODEL_DRAFT_AUTHENTICATED", "e"*64,
                 json.dumps({"candidate_identity": candidate})))
        self.row = {"seq": v48.EVENT_SEQ, "prior_sha": v48.HEAD_SHA256}
        self.proof = {
            "schema": v48.SCHEMA,
            "from_source_sha": v48.SOURCE,
            "to_source_sha": "f"*40,
            "prior_event_head_sha256": v48.HEAD_SHA256,
            "event1864_ancestor_sha256": v48.HEAD_SHA256,
            "prior_source_transition_sha256": v48.TRANSITION_SHA256,
            "prior_activation_sha256": v48.ACTIVATION_SHA256,
            "owner_run_id": v48.MIN_OWNER_RUN + 1,
            "qualified_main_run_id": 44533159564,
            "rehearsal_run_id": 44530103898,
            "backup_sqlite_sha256": "a"*64,
            "genenv_executable_sha256": "b"*64,
            "generation_mechanism_sha256": "c"*64,
            "source_transition_purpose": v48.PURPOSE,
            "native_development_approved": True,
            "scientific_first_use": False,
            "new_dispatches": 0, "new_controller": False,
            "new_scheduler": False, "new_queue": False,
            "paid_api_calls": 0,
            **v48.frozen_historical_preimage(self, self.previous),
        }

    def close(self):
        self.conn.close()


class V48ColdReplayTests(unittest.TestCase):
    def setUp(self):
        self.db = FakeColdSource()
        self.addCleanup(self.db.close)

    def test_frozen_event_is_replayable_without_any_source_write(self):
        changes = self.db.conn.total_changes
        self.assertTrue(v48.verify_cold_event(
            self.db, self.db.row, self.db.proof, self.db.previous))
        self.assertEqual(self.db.conn.total_changes, changes)
        self.assertEqual(self.db.proof["model_draft_attempts"], 169)
        self.assertEqual(self.db.proof["model_draft_authenticated"], 167)
        self.assertEqual(self.db.proof["unresolved_publication_identities"],
                         list(v48.FROZEN_IDS))
        self.assertEqual(self.db.proof["custodied_negative_tasks"], 56)
        self.assertEqual(self.db.proof["verified_historical_tasks"], 155)

    def test_no_reused_target_or_previous_transition(self):
        for key, value in (
            ("to_source_sha", v48.SOURCE),
            ("to_source_sha", "0"*40),
            ("to_source_sha", "g"*40),
            ("prior_event_head_sha256", "a"*64),
            ("event1864_ancestor_sha256", "a"*64),
            ("prior_source_transition_sha256", "a"*64),
            ("prior_activation_sha256", "b"*64),
            ("source_transition_purpose", "new-capability"),
        ):
            with self.subTest(key=key,value=value):
                with self.assertRaises(v48.V48TransitionDenied):
                    v48.verify_cold_event(
                        self.db,self.db.row,
                        dict(self.db.proof,**{key:value}),self.db.previous)
        with self.assertRaises(v48.V48TransitionDenied):
            v48.verify_cold_event(
                self.db,self.db.row,self.db.proof,
                self.db.previous+[self.db.proof])

    def test_original_event_identity_and_predecessor_must_match(self):
        scenarios=(
            ("UPDATE events SET sha=? WHERE seq=?",("e"*64,v48.HEAD_SEQ)),
            ("UPDATE events SET sha=? WHERE seq=?",
             ("e"*64,v48.TRANSITION_SEQ)),
            ("UPDATE events SET sha=? WHERE seq=?",
             ("e"*64,v48.ACTIVATION_SEQ)),
        )
        for sql,values in scenarios:
            with self.subTest(values=values):
                self.db.conn.execute("SAVEPOINT scenario")
                try:
                    self.db.conn.execute(sql,values)
                    with self.assertRaises(v48.V48TransitionDenied):
                        v48.verify_cold_event(
                            self.db,self.db.row,self.db.proof,self.db.previous)
                finally:
                    self.db.conn.execute("ROLLBACK TO scenario")
                    self.db.conn.execute("RELEASE scenario")

    def test_no_new_science_paid_actions_or_unknown_authority(self):
        cases = (
            ("scientific_first_use",True),
            ("new_dispatches",1),
            ("new_controller",True),
            ("new_scheduler",True),
            ("new_queue",True),
            ("paid_api_calls",1),
            ("native_development_approved",False),
            ("owner_run_id",v48.MIN_OWNER_RUN),
            ("owner_run_id",True),
            ("rehearsal_run_id",44533159564),
        )
        for key,value in cases:
            with self.subTest(key=key):
                with self.assertRaises(v48.V48TransitionDenied):
                    v48.verify_cold_event(
                        self.db,self.db.row,dict(self.db.proof,**{key:value}),
                        self.db.previous)

    def test_consumed_remote_publications_are_not_replayable(self):
        with self.assertRaises(v48.V48TransitionDenied):
            v48.verify_cold_event(
                self.db,self.db.row,
                dict(self.db.proof,model_draft_attempts=168),self.db.previous)
        with self.assertRaises(v48.V48TransitionDenied):
            v48.verify_cold_event(
                self.db,self.db.row,
                dict(self.db.proof,unresolved_publication_identities=[]),
                self.db.previous)
        self.db.conn.execute(
            "INSERT INTO events VALUES (?,?,?,?)",
            (1500,"MODEL_DRAFT_ATTEMPTED","e"*64,
             json.dumps({"candidate_identity":"f"*64})))
        with self.assertRaises(v48.V48TransitionDenied):
            v48.verify_cold_event(
                self.db,self.db.row,self.db.proof,self.db.previous)

    def test_history_is_immutable_and_old_negative_tasks_not_erased(self):
        with self.assertRaises(v48.V48TransitionDenied):
            v48.verify_cold_event(
                self.db,self.db.row,
                dict(self.db.proof,custodied_negative_tasks=0),
                self.db.previous)
        self.db.conn.execute("DELETE FROM tasks WHERE ticket='q2'")
        with self.assertRaises(v48.V48TransitionDenied):
            v48.verify_cold_event(
                self.db,self.db.row,self.db.proof,self.db.previous)

    def test_schema_rejects_additional_fields_and_wrong_row(self):
        with self.assertRaises(v48.V48TransitionDenied):
            v48.verify_cold_event(
                self.db,self.db.row,
                dict(self.db.proof,source_transition_authorized=True),
                self.db.previous)
        with self.assertRaises(v48.V48TransitionDenied):
            v48.verify_cold_event(
                self.db,dict(self.db.row,seq=1866),self.db.proof,
                self.db.previous)

    def test_no_proposed_cold_proof_without_authentic_v59_preflight(self):
        # A test fake cannot authenticate a real Windows owner. The
        # read-only proof builder must refuse when V59 denies.
        with patch.object(v48,"audit_frozen_original_readonly",
                          side_effect=ValueError("INERT_ORIGINAL_ABSENT")):
            with self.assertRaisesRegex(ValueError,"INERT_ORIGINAL_ABSENT"):
                v48.proposed_cold_proof(
                    self.db,target="f"*40,owner_run_id=v48.MIN_OWNER_RUN+1,
                    qualified_main_run_id=44533159564,
                    rehearsal_run_id=44530103898,
                    backup_sqlite_sha256="a"*64,
                    genenv_executable_sha256="b"*64,
                    generation_mechanism_sha256="c"*64)

    def test_existing_replay_and_genenv_interfaces_are_explicit(self):
        root=Path(__file__).resolve().parents[1]
        local=(root/"f139/local_controller.py").read_text()
        owner=(root/"f139/nci04_owner_ledger.py").read_text()
        backend=(root/"f139/nci04_genenv_owner_backend.py").read_text()
        self.assertIn("is_v48 =",local)
        self.assertIn("from f139.nci04_v59_forward_transition import verify_cold_event",local)
        for body in (local,owner,backend):
            self.assertIn('"forge.f139.source-transition.v48"',body)
        self.assertNotIn("Set-ScheduledTask",str(root/"f139/nci04_v59_forward_transition.py"))


if __name__=="__main__":
    unittest.main()
