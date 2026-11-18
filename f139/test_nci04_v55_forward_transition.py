"""V55 source-transition v45 frozen synthetic replay/negative qualification.

NEVER contacts the original Windows F139 owner or a real provider.
"""
from __future__ import annotations

import copy
import inspect
import json
import sqlite3
import unittest
from unittest.mock import patch

from f139.nci04_native_contract import canonical, digest
from f139.nci04_v55_forward_transition import (
    ANCHOR_SEQ, ANCHOR_SHA, FIELDS, MIN_OWNER_RUN, PREVIOUS,
    PURPOSE, SCHEMA, SOURCE, ForwardTransitionDenied, verify_cold_event,
)


class V45Replay(unittest.TestCase):
    def setUp(self):
        conn = sqlite3.connect(":memory:", isolation_level=None)
        conn.row_factory = sqlite3.Row
        self.conn = conn
        self.addCleanup(conn.close)
        conn.execute("CREATE TABLE events(seq INTEGER,kind TEXT,sha TEXT,"
                     "prior_sha TEXT,payload TEXT)")
        conn.execute("CREATE TABLE tasks(ticket TEXT,lane TEXT,source_sha TEXT,"
                     "stage TEXT,manifest_sha TEXT,run_id INTEGER,"
                     "evidence_dir TEXT,evidence_sha TEXT,quarantine_reason TEXT)")
        old_source = "2d6ca3ea8852f6c70ee0981da3f222d0b982c279"
        self.prior = [{
            "schema":PREVIOUS,"from_source_sha":old_source,"to_source_sha":SOURCE,
            "custodied_negative_tickets":[],
        }]
        source_event_sha = "a" * 64
        activation_sha = ANCHOR_SHA
        conn.execute("INSERT INTO events VALUES(1848,'SOURCE_TRANSITION_ADMITTED',?,?,?)",
                     (source_event_sha, "f"*64, json.dumps(self.prior[0])))
        conn.execute("INSERT INTO events VALUES(1849,'NATIVE_DEVELOPMENT_ACTIVATED',?,?,?)",
                     (activation_sha,source_event_sha,json.dumps({
                         "schema":"forge.f139.nci04.owner-native-activation.v1",
                         "source_sha":SOURCE})))
        # Full history used for the source-custody negative; no unreviewed tasks.
        for i in range(154):
            conn.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?)",
                         (f"p{i:04d}","Wingless",SOURCE,"VERIFIED",
                          "c"*64,i+1,"sealed","d"*64,None))
        for i in range(56):
            ticket=f"q{i:04d}"
            conn.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?)",
                         (ticket,"Yggdrasil",SOURCE,"QUARANTINED",
                          "e"*64,None,None,None,"kept"))
            self.prior[0]["custodied_negative_tickets"].append(ticket)
        # Rebind historic JSON payload to final frozen predecessor packet.
        conn.execute("UPDATE events SET payload=? WHERE seq=1848",
                     (json.dumps(self.prior[0]),))
        self.db = type("FakeDB",(),{"conn":conn})()
        self.row = dict(seq=ANCHOR_SEQ+1,prior_sha=ANCHOR_SHA)
        history=[dict(r) for r in conn.execute(
            "SELECT ticket,lane,source_sha,stage,manifest_sha,run_id,"
            "evidence_dir,evidence_sha,quarantine_reason FROM tasks ORDER BY ticket")]
        self.doc = {
            "schema":SCHEMA, "from_source_sha":SOURCE,
            "to_source_sha":"f"*40,
            "prior_event_head_sha256":ANCHOR_SHA,
            "event1849_ancestor_sha256":ANCHOR_SHA,
            "prior_source_transition_sha256":source_event_sha,
            "prior_activation_sha256":activation_sha,
            "owner_run_id":MIN_OWNER_RUN+1,
            "qualified_main_run_id":44179547958,
            "rehearsal_run_id":44179547712,
            "backup_sqlite_sha256":"5"*64,
            "genenv_executable_sha256":"6"*64,
            "generation_mechanism_sha256":"7"*64,
            "terminal_tasks_sha256":digest(canonical(history)),
            "verified_historical_tasks":154,
            "custodied_negative_tasks":56,
            "custodied_negative_tickets":sorted(
                self.prior[0]["custodied_negative_tickets"]),
            "source_transition_purpose":PURPOSE,
            "native_development_approved":True,
            "scientific_first_use":False,"new_dispatches":0,
            "new_controller":False,"new_scheduler":False,
            "new_queue":False,"paid_api_calls":0,
        }
        mock=patch("f139.nci04_v55_forward_transition.verify_native_activation",
                   return_value=True)
        mock.start()
        self.addCleanup(mock.stop)

    def test_exact_source_cold_replay_passes_without_writes(self):
        before = self.conn.total_changes
        self.assertEqual(set(self.doc),FIELDS)
        self.assertTrue(verify_cold_event(
            self.db,self.row,self.doc,self.prior))
        self.assertEqual(before,self.conn.total_changes)

    def test_corrupted_authentication_release_or_science_denied(self):
        examples=[
            ("to_source_sha",SOURCE),
            ("to_source_sha","2d6ca3ea8852f6c70ee0981da3f222d0b982c279"),
            ("prior_event_head_sha256","0"*64),
            ("event1849_ancestor_sha256","0"*64),
            ("prior_source_transition_sha256","0"*64),
            ("prior_activation_sha256","0"*64),
            ("owner_run_id",MIN_OWNER_RUN),
            ("qualified_main_run_id",0),
            ("rehearsal_run_id",self.doc["qualified_main_run_id"]),
            ("backup_sqlite_sha256","invalid"),
            ("genenv_executable_sha256","invalid"),
            ("generation_mechanism_sha256","invalid"),
            ("terminal_tasks_sha256","0"*64),
            ("custodied_negative_tickets",[]),
            ("verified_historical_tasks",153),
            ("custodied_negative_tasks",55),
            ("source_transition_purpose","promote-science"),
            ("native_development_approved",False),
            ("scientific_first_use",True),
            ("new_dispatches",1),
            ("new_controller",True),
            ("new_scheduler",True),
            ("new_queue",True),
            ("paid_api_calls",1),
        ]
        for key,value in examples:
            with self.subTest(key=key):
                d=dict(self.doc,**{key:value})
                with self.assertRaises(ForwardTransitionDenied):
                    verify_cold_event(self.db,self.row,d,self.prior)

    def test_replay_source_drift_and_missing_original_anchor_denied(self):
        with self.assertRaises(ForwardTransitionDenied):
            verify_cold_event(self.db,self.row,self.doc,
                              self.prior+[dict(self.doc)])
        self.conn.execute("UPDATE events SET sha=? WHERE seq=1849",
                          ("0"*64,))
        with self.assertRaises(ForwardTransitionDenied):
            verify_cold_event(self.db,self.row,self.doc,self.prior)

    def test_stale_predecessor_or_new_unsealed_task_denied(self):
        self.row["prior_sha"]="1"*64
        with self.assertRaises(ForwardTransitionDenied):
            verify_cold_event(self.db,self.row,self.doc,self.prior)
        self.row["prior_sha"]=ANCHOR_SHA
        self.conn.execute("UPDATE tasks SET stage='READY' WHERE ticket='p0001'")
        with self.assertRaises(ForwardTransitionDenied):
            verify_cold_event(self.db,self.row,self.doc,self.prior)

    def test_later_genuine_event_head_is_supported(self):
        self.conn.execute("INSERT INTO events VALUES(1850,'DUMMY_EVENT',?,?,?)",
                          ("e"*64,ANCHOR_SHA,"{}"))
        self.row = dict(seq=1851,prior_sha="e"*64)
        self.doc["prior_event_head_sha256"]="e"*64
        self.assertTrue(verify_cold_event(
            self.db,self.row,self.doc,self.prior))

    def test_cold_replay_after_separate_future_activation(self):
        # The historical v45 predecessor is still source-locked when a
        # later fully authenticated current activation moves to target.
        target = self.doc["to_source_sha"]
        self.conn.execute(
            "INSERT INTO events VALUES(1850,'SOURCE_TRANSITION_ADMITTED',?,?,?)",
            ("c"*64, ANCHOR_SHA, json.dumps(self.doc)))
        self.conn.execute(
            "INSERT INTO events VALUES(1851,'NATIVE_DEVELOPMENT_ACTIVATED',?,?,?)",
            ("d"*64, "c"*64, json.dumps({
                "schema":"forge.f139.nci04.owner-native-activation.v1",
                "source_sha":target,
            })))
        with patch("f139.nci04_v55_forward_transition.verify_native_activation",
                   side_effect=lambda db, *, expected_source:
                       expected_source == target) as check:
            self.assertTrue(verify_cold_event(
                self.db, self.row, self.doc, self.prior))
            check.assert_called_once_with(self.db, expected_source=target)
        with patch("f139.nci04_v55_forward_transition.verify_native_activation",
                   return_value=False):
            with self.assertRaises(ForwardTransitionDenied):
                verify_cold_event(self.db, self.row, self.doc, self.prior)

    def test_cold_replay_rejects_unauthenticated_original_predecessor(self):
        self.conn.execute(
            "UPDATE events SET payload=? WHERE seq=1849",
            (json.dumps({"source_sha":SOURCE,
                         "schema":"not-an-original-activation"}),))
        with self.assertRaises(ForwardTransitionDenied):
            verify_cold_event(self.db, self.row, self.doc, self.prior)

    def test_no_deployment_or_source_verifier_bypass(self):
        from f139 import local_controller, nci04_owner_ledger
        from f139 import nci04_v55_forward_transition as v45
        original=inspect.getsource(v45)
        controller=inspect.getsource(local_controller.Database.verify)
        activation=inspect.getsource(nci04_owner_ledger.activate_native)
        for forbidden in ("Register-ScheduledTask","Set-ScheduledTask",
                          "UPDATE meta SET", "def install(", "def live(",
                          "def dispatch(", "gh api --method POST"):
            self.assertNotIn(forbidden,original)
        self.assertIn('if is_v45:',controller)
        self.assertIn("v55_forward_transition import verify_cold_event",
                      controller)
        # V45 still requires separate owner release and source-bound
        # executable custody; this test supplies neither authority.
        self.assertIn("forge.f139.source-transition.v45",activation)
        self.assertIn("SingleOwner.held",original)


if __name__=="__main__":
    unittest.main()
