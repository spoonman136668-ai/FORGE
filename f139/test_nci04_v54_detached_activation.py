"""V54 detached transaction rehearsal: synthetic fixtures, no real owner data."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical
from f139.nci04_v54_forward_transition import (
    SOURCE, ANCHOR_SHA, MIN_OWNER_RUN,
    ForwardTransitionDenied,
)
from f139.nci04_v54_detached_activation import (
    rehearse_v44_source_and_activation,
)

TARGET = "a" * 40


class V54DetachedActivation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="f139-v54-test-")
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/"f139-v54-original-rehearsal-123.sqlite"
        conn = sqlite3.connect(str(self.path), isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE meta(id INTEGER PRIMARY KEY,source_sha TEXT,"
                     "enabled INTEGER,legacy_suspended INTEGER,"
                     "head_seq INTEGER,head_hash TEXT)")
        conn.execute("CREATE TABLE events(seq INTEGER PRIMARY KEY,kind TEXT,"
                     "payload TEXT,prior_sha TEXT,sha TEXT)")
        conn.execute("CREATE TABLE tasks(ticket TEXT,lane TEXT,source_sha TEXT,"
                     "stage TEXT,manifest_sha TEXT,run_id INTEGER,"
                     "evidence_dir TEXT,evidence_sha TEXT,"
                     "quarantine_reason TEXT,started_at TEXT)")
        conn.execute("INSERT INTO meta VALUES(1,?,?,?,?,?)",
                     (SOURCE,1,1,1847,ANCHOR_SHA))
        self.negatives = [f"q{i:04d}" for i in range(56)]
        predecessor = {
            "schema":"forge.f139.source-transition.v43",
            "from_source_sha":"2ea68f93cbe6323aa6b0cbe99e47a32f0717b04c",
            "to_source_sha":SOURCE,
            "custodied_negative_tickets":self.negatives,
        }
        conn.execute("INSERT INTO events VALUES(1838,?,?,?,?)",
                     ("SOURCE_TRANSITION_ADMITTED",json.dumps(predecessor),
                      "f"*64,"1"*64))
        conn.execute("INSERT INTO events VALUES(1839,?,?,?,?)",
                     ("NATIVE_DEVELOPMENT_ACTIVATED", json.dumps({
                          "schema":"forge.f139.nci04.owner-native-activation.v1",
                          "source_sha":SOURCE,
                      }),"1"*64,"2"*64))
        conn.execute("INSERT INTO events VALUES(1847,?,?,?,?)",
                     ("PROVIDER_VERIFIED_TERMINAL","{}","9"*64,ANCHOR_SHA))
        for i in range(153):
            conn.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?)",
                         (f"p{i:04d}","Wingless",SOURCE,"VERIFIED",
                          "c"*64,i+1,"sealed","d"*64,None,None))
        for ticket in self.negatives:
            conn.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?)",
                         (ticket,"Yggdrasil",SOURCE,"QUARANTINED",
                          "e"*64,None,None,None,"kept",None))
        db = object.__new__(Database)
        db.filename = self.path
        db.conn = conn
        self.db = db
        self.addCleanup(conn.close)
        # These synthetic fixtures intentionally bypass the full 1847-event
        # original ledger. Full production-chain validation remains a
        # separately required original owner detached-backup qualification.
        ctx = [
            patch.object(Database,"verify",return_value=None),
            patch.object(Database,"meta",new=lambda this:dict(
                this.conn.execute("SELECT * FROM meta WHERE id=1").fetchone())),
            patch("f139.nci04_v54_detached_activation.verified_historical_foundation",
                  return_value=None),
            patch("f139.nci04_v54_forward_transition.verify_native_activation",
                  return_value=True),
            patch("f139.nci04_v54_detached_activation.verify_native_activation",
                  return_value=True),
            patch.dict(os.environ,{"RUNNER_TEMP":self.tmp.name}),
        ]
        for p in ctx:
            p.start()
            self.addCleanup(p.stop)

    def args(self):
        return dict(target=TARGET, owner_run_id=MIN_OWNER_RUN+17,
                    qualified_main_run_id=44191737221,
                    rehearsal_run_id=44191739204,
                    backup_sqlite_sha256="e"*64)

    def with_lock(self, op):
        with SingleOwner(self.path.with_suffix(".lock")):
            return op()

    def test_detached_transition_and_activation_are_atomic_and_once_only(self):
        result=self.with_lock(lambda:rehearse_v44_source_and_activation(
            self.db,**self.args()))
        self.assertTrue(result["detached_only"])
        self.assertFalse(result["deployment_authorized"])
        self.assertEqual(result["head_seq"],1849)
        self.assertEqual(result["historical_events_added"],2)
        self.assertEqual(self.db.meta()["source_sha"],TARGET)
        rows=list(self.db.conn.execute(
            "SELECT kind,payload FROM events WHERE seq>=1848 ORDER BY seq"))
        self.assertEqual([x["kind"] for x in rows],
                         ["SOURCE_TRANSITION_ADMITTED",
                          "NATIVE_DEVELOPMENT_ACTIVATED"])
        self.assertFalse(json.loads(rows[-1]["payload"])["scientific_first_use"])
        with self.assertRaises(ForwardTransitionDenied):
            self.with_lock(lambda:rehearse_v44_source_and_activation(
                self.db,**self.args()))
        self.assertEqual(self.db.meta()["head_seq"],1849)

    def test_cold_commit_error_rolls_back_both_original_event_types(self):
        original = self.db.event
        called=[0]
        def fail_activation(*args,**kwargs):
            called[0]+=1
            if called[0]==2:
                raise RuntimeError("INJECTED_SYNTHETIC_COMMIT_FAILURE")
            return original(*args,**kwargs)
        with patch.object(Database,"event",new=lambda _db,*a,**kw:
                          fail_activation(*a,**kw)):
            with self.assertRaisesRegex(RuntimeError,"INJECTED"):
                self.with_lock(lambda:rehearse_v44_source_and_activation(
                    self.db,**self.args()))
        m=self.db.meta()
        self.assertEqual(m["source_sha"],SOURCE)
        self.assertEqual(m["head_seq"],1847)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM events WHERE seq>=1848").fetchone()[0],0)

    def test_no_original_path_other_temp_or_without_mutex(self):
        with self.assertRaises(ForwardTransitionDenied):
            rehearse_v44_source_and_activation(self.db,**self.args())
        original_path=self.db.filename
        try:
            self.db.filename = self.path.with_name("state.sqlite")
            with self.assertRaises(ForwardTransitionDenied):
                self.with_lock(lambda:rehearse_v44_source_and_activation(
                    self.db,**self.args()))
            self.db.filename=original_path
            with patch.dict(os.environ,{"RUNNER_TEMP":str(self.path.parent.parent)}):
                with self.assertRaises(ForwardTransitionDenied):
                    self.with_lock(lambda:rehearse_v44_source_and_activation(
                        self.db,**self.args()))
        finally:
            self.db.filename=original_path

    def test_unqualified_target_or_negative_drift_fails_before_mutation(self):
        for key,value in (("target",SOURCE),("backup_sqlite_sha256","bad"),
                          ("rehearsal_run_id",44191737221)):
            a=dict(self.args(),**{key:value})
            with self.subTest(key=key),self.assertRaises(ForwardTransitionDenied):
                self.with_lock(lambda:rehearse_v44_source_and_activation(
                    self.db,**a))
        self.assertEqual(self.db.meta()["head_seq"],1847)
        self.assertEqual(self.db.meta()["source_sha"],SOURCE)

    def test_detached_code_has_no_scheduler_network_or_original_owner_route(self):
        import inspect
        from f139 import nci04_v54_detached_activation as module
        code=inspect.getsource(module)
        for forbidden in ("Register-ScheduledTask","Set-ScheduledTask",
                          "Start-ScheduledTask","gh api --method POST",
                          "requests.post(", "subprocess.", "def install(",
                          "def live_release(", "activate_native("):
            self.assertNotIn(forbidden,code)
        self.assertIn("db.transaction()",code)
        self.assertIn("verify_cold_event(db,",code)
        self.assertIn("_DETACHED_NAME.fullmatch",code)


if __name__=="__main__":
    unittest.main()
