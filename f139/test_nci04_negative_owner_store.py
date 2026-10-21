"""A8B: original-owner append-only native negative with cold restart proofs.

These tests use an isolated synthetic SQLite fixture ONLY. The real owner's
event47 hash, issue696 HMAC and provider ZIP are never used in CI.
"""
from __future__ import annotations

from pathlib import Path
import unittest
from unittest import mock

from f139.local_controller import Database
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_ledger import admit_native_issue
from f139.nci04_negative_owner_store import (
    OwnerNegativeCustodyDenied, admit_original_negative_custody,
    verify_original_negative_custody, KIND, _paths)
from test_nci04_owner_ledger import LedgerTests
from test_nci04_provider_receipt import bundle, zipper
from test_nci04_owner_issue import MAIN, HMAC


class OwnerNegativeStoreTests(unittest.TestCase):
    def setUp(self):
        # Reuse the existing isolated original 40-event fixture with original
        # prefix pin already patched to the synthetic event23 hash.
        LedgerTests.setUp(self)
        self.assertTrue(admit_native_issue(self.db,self.native,
                                          "2026-10-21T10:00:00Z"))
        self.db.conn.execute(
            "UPDATE tasks SET stage='QUARANTINED',"
            "quarantine_reason='FAILED_OR_CANCELLED_NO_REPLAY'"
            " WHERE ticket=?", (self.native.ticket,))
        with self.db.transaction():
            self.db.event("ATTEMPT_QUARANTINED",{
                "ticket": self.native.ticket,
                "reason":"FAILED_OR_CANCELLED_NO_REPLAY"})
        for i in range(4):
            with self.db.transaction():
                self.db.event("FIXTURE_UNTRUSTED",{"after_quarantine":i})
        self.assertEqual(self.db.meta()["head_seq"],47)
        self.head=self.db.meta()["head_hash"]
        issue,rid,_,report,receipt,body=bundle(negative=True)
        # The shared fixtures describe precisely the same owner issue.
        self.assertEqual(issue.ticket,self.native.ticket)
        self.rid=rid
        self.artid=rid+13
        self.archive=zipper(body,report)
        self.task=dict(self.db.conn.execute(
            "SELECT * FROM tasks WHERE ticket=?",(self.native.ticket,)).fetchone())
        self.run={
            "id":rid, "run_attempt":1, "event":"workflow_dispatch",
            "head_sha":MAIN,"head_branch":"main",
            "status":"completed","conclusion":"failure",
            "repository":{"full_name":"spoonman136668-ai/FORGE"},
        }
        self.jobs=[
            {"id":rid+10,"run_id":rid,"name":"native-authorize",
             "status":"completed","conclusion":"success"},
            {"id":rid+15,"run_id":rid,"name":"execute",
             "status":"completed","conclusion":"skipped"},
            {"id":rid+11,"run_id":rid,"name":"native-execute (ubuntu-latest)",
             "status":"completed","conclusion":"failure"},
            {"id":rid+12,"run_id":rid,"name":"native-execute (windows-latest)",
             "status":"completed","conclusion":"failure"},
        ]
        self.artifact={
            "id":self.artid,"name":"forge-f139-native-receipt-ubuntu-latest",
            "digest":"sha256:"+digest(self.archive),
            "size_in_bytes":len(self.archive),"expired":False,
            "workflow_run":{"id":rid,"head_sha":MAIN},
        }
        for name,value in {
            "OWNER_HEAD":self.head,"SOURCE_SHA":MAIN,
            "TICKET":self.native.ticket,"RUN_ID":rid,
            "ARTIFACT_ID":self.artid,"ARTIFACT_SHA":digest(self.archive)
        }.items():
            patcher=mock.patch("f139.nci04_negative_owner_store."+name,value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.db.verify()

    def admit(self, **overrides):
        opts={
            "run":self.run,"jobs":self.jobs,"artifact":self.artifact,
            "archive":self.archive,"owner_hmac_key":HMAC,"epoch":1,
        }
        opts.update(overrides)
        return admit_original_negative_custody(self.db,**opts)

    def test_durable_negative_once_cold_restart_and_history_unchanged(self):
        first=[dict(row) for row in self.db.conn.execute(
            "SELECT seq,kind,payload,sha FROM events ORDER BY seq")]
        task_before=self.task
        result=self.admit()
        self.assertEqual(result["original_negative_custody"],"PASS")
        self.assertFalse(result["scientific_first_use"])
        self.assertFalse(result["successor_source_transition_authorized"])
        self.assertEqual(self.db.meta()["head_seq"],48)
        self.assertEqual([dict(row) for row in self.db.conn.execute(
            "SELECT seq,kind,payload,sha FROM events WHERE seq<=47 ORDER BY seq")],
            first)
        task_after=dict(self.db.conn.execute(
            "SELECT * FROM tasks WHERE ticket=?",(self.native.ticket,)).fetchone())
        self.assertEqual(task_after,task_before)
        _,_,original=_paths(self.db,self.native.ticket,self.rid)
        self.assertEqual(original.read_bytes(),self.archive)
        self.assertTrue(verify_original_negative_custody(self.db))
        self.db.close()
        self.db=Database(self.path)
        self.addCleanup(self.db.close)
        self.db.verify()
        self.assertEqual(self.db.meta()["head_seq"],48)
        with self.assertRaisesRegex(OwnerNegativeCustodyDenied,
                                    "OWNER_47_EVENT_HEAD_OR_STATE_DRIFT"):
            self.admit()
        self.assertEqual(self.db.meta()["head_seq"],48)

    def test_missing_changed_and_symlinked_original_zip_fail_cold_restart(self):
        self.admit()
        _,_,file=_paths(self.db,self.native.ticket,self.rid)
        file.write_bytes(b"forged")
        with self.assertRaisesRegex(OwnerNegativeCustodyDenied,
                                    "ORIGINAL_ZIP_CUSTODY_TAMPERED"):
            self.db.verify()
        file.write_bytes(self.archive)
        file.unlink()
        with self.assertRaises(OwnerNegativeCustodyDenied):
            self.db.verify()

    def test_provider_forgery_never_writes_archive_or_event(self):
        attempts=(
            {"run":{**self.run,"run_attempt":2}},
            {"run":{**self.run,"conclusion":"success"}},
            {"run":{**self.run,"head_sha":"9"*40}},
            {"jobs":self.jobs[:2]},
            {"artifact":{**self.artifact,"digest":"sha256:"+"9"*64}},
            {"epoch":2},
            {"owner_hmac_key":"wrong-secret"*5},
        )
        for changes in attempts:
            with self.subTest(changes=changes),self.assertRaises(Exception):
                self.admit(**changes)
            self.assertEqual(self.db.meta()["head_seq"],47)
        _,_,file=_paths(self.db,self.native.ticket,self.rid)
        self.assertFalse(file.exists())

    def test_fail_after_disk_before_sql_preserves_original_bytes_for_recovery(self):
        real=self.db.event
        def fail_one(kind,payload):
            if kind == KIND:
                raise OSError("SIMULATED_SQLITE_WRITE_INTERRUPTED")
            return real(kind,payload)
        with mock.patch.object(self.db,"event",side_effect=fail_one):
            with self.assertRaisesRegex(OSError,"SIMULATED_SQLITE_WRITE_INTERRUPTED"):
                self.admit()
        self.assertEqual(self.db.meta()["head_seq"],47)
        _,directory,file=_paths(self.db,self.native.ticket,self.rid)
        self.assertEqual(file.read_bytes(),self.archive)
        self.assertTrue(self.admit()["original_negative_custody"]=="PASS")
        self.assertEqual(self.db.meta()["head_seq"],48)

    def test_conflicting_existing_original_bytes_never_overwritten(self):
        _,directory,file=_paths(self.db,self.native.ticket,self.rid)
        directory.mkdir(parents=True)
        file.write_bytes(b"untrusted original")
        with self.assertRaisesRegex(OwnerNegativeCustodyDenied,
                                    "ORIGINAL_ZIP_CONFLICT"):
            self.admit()
        self.assertEqual(file.read_bytes(),b"untrusted original")
        self.assertEqual(self.db.meta()["head_seq"],47)

    def test_partial_previous_write_is_not_silently_accepted(self):
        _,directory,file=_paths(self.db,self.native.ticket,self.rid)
        directory.mkdir(parents=True)
        (directory/"ubuntu-latest.zip.partial").write_bytes(b"partial")
        with self.assertRaisesRegex(OwnerNegativeCustodyDenied,
                                    "PARTIAL_ORIGINAL_NEEDS_REVIEW"):
            self.admit()
        self.assertEqual(self.db.meta()["head_seq"],47)
        self.assertFalse(file.exists())


if __name__ == "__main__":
    unittest.main()
