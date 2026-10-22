"""A6 original SQLite native intake/replay tests; isolated fixture only."""
import base64
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from f139.local_controller import Database, hash_bytes, run_once
from f139.nci04_owner_issue import inspect_owner_issue
from f139.nci04_owner_ledger import (
    NativeLedgerDenied, audit_native_events, admit_native_issue,
    frozen_native_issue, KIND, APPROVAL_SCHEMA, activate_native,
    verify_native_activation)
from test_nci04_owner_issue import issue as make_issue, MAIN, TARGET, TREE, HMAC


class LedgerTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory(prefix="f139-a6-ledger-")
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.path = self.root / "state.sqlite"
        self.db = Database.initialize(self.path, MAIN)
        self.addCleanup(self.db.close)
        self.db.enable(legacy_suspended=True)
        # Fixture is intentionally NOT the real historic chain. Override
        # just the sealed anchor in this isolated test; production never may.
        for i in range(39):
            with self.db.transaction():
                self.db.event("FIXTURE_UNTRUSTED", {"fixture_sequence": i})
        seq23 = self.db.conn.execute("SELECT sha FROM events WHERE seq=23").fetchone()["sha"]
        patcher = mock.patch("f139.nci04_owner_ledger.SEALED_OWNER_PREFIX_HEAD", seq23)
        patcher.start()
        self.addCleanup(patcher.stop)
        for ix, (lane, ticket) in enumerate((
            ("Qualification", "f139-d2c-qualification-659bb1f4d751"),
            ("Wingless", "f139-d2c-wingless-659bb1f4d751"),
            ("Wingless", "f139-d2j-wingless-5a252f8dde24"),
            ("Yggdrasil", "f139-d2j-yggdrasil-5a252f8dde24"),
            ("Wingless", "f139-d2k-i687-5a252f8dde24-5a2ecddb"),
            ("Yggdrasil", "f139-d2k-i688-5a252f8dde24-02ded761"),
        )):
            rid = 39513293606 if "i687" in ticket else (
                39513381790 if "i688" in ticket else 42 + ix)
            self.db.conn.execute(
                "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha,"
                "run_id,evidence_dir,evidence_sha) VALUES(?,?,?,'VERIFIED',?,?,?,?)",
                (ticket, lane, MAIN, "c"*64, rid, "/dev/fixture-only", "d"*64))
        self.native = inspect_owner_issue(
            make_issue(), protected_main=MAIN,
            authenticated_target_commit=TARGET, authenticated_target_tree=TREE)
        self.assertEqual(self.db.meta()["head_seq"], 40)

    def test_admit_exactly_once_and_verify_original_ledger(self):
        before = self.db.meta()["head_seq"]
        self.assertTrue(admit_native_issue(self.db, self.native, "2026-10-21T10:00:00Z"))
        self.assertEqual(self.db.meta()["head_seq"], before + 2)
        self.db.verify()
        tasks = [dict(x) for x in self.db.conn.execute(
            "SELECT * FROM tasks WHERE ticket=?", (self.native.ticket,))]
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["stage"], "READY")
        recovered = frozen_native_issue(self.db, self.native.ticket)
        self.assertEqual(recovered.intent_raw, self.native.intent_raw)
        self.assertEqual(recovered.candidate.qualification_key,
                         self.native.qualification_key)
        self.assertFalse(admit_native_issue(self.db, self.native, "2026-10-21T10:05:00Z"))
        self.assertEqual(self.db.meta()["head_seq"], before + 2)
        reopened = Database(self.path)
        reopened.verify()
        reopened.close()

    def test_cross_source_and_same_issue_number_rejected(self):
        with self.assertRaisesRegex(NativeLedgerDenied, "SOURCE_OR_DAY_DRIFT"):
            altered = inspect_owner_issue(
                make_issue(), protected_main=MAIN,
                authenticated_target_commit=TARGET, authenticated_target_tree=TREE)
            from dataclasses import replace
            altered = replace(altered, source_sha="9"*40)
            admit_native_issue(self.db, altered, "2026-10-21T10:00:00Z")
        self.assertEqual(self.db.meta()["head_seq"], 40)

    def test_original_23_event_pin_absent_fails_closed(self):
        with mock.patch("f139.nci04_owner_ledger.SEALED_OWNER_PREFIX_HEAD", "9"*64):
            with self.assertRaisesRegex(NativeLedgerDenied, "ORIGINAL_23_EVENT_PIN_DRIFT"):
                admit_native_issue(self.db, self.native, "2026-10-21T10:00:00Z")
        self.assertEqual(self.db.meta()["head_seq"], 40)

    def test_original_d2k_local_runs_required(self):
        self.db.conn.execute(
            "UPDATE tasks SET run_id=999 WHERE ticket LIKE 'f139-d2k-i688-%'")
        with self.assertRaisesRegex(NativeLedgerDenied, "D2K_LOCAL_CUSTODY_NOT_VERIFIED"):
            admit_native_issue(self.db, self.native, "2026-10-21T10:00:00Z")

    def test_native_history_source_tampering_fails_closed(self):
        self.assertTrue(admit_native_issue(self.db, self.native, "2026-10-21T10:00:00Z"))
        self.db.conn.execute("UPDATE tasks SET manifest_sha=? WHERE ticket=?",
                             ("e"*64, self.native.ticket))
        with self.assertRaisesRegex(NativeLedgerDenied, "TASK_ADMISSION_MISMATCH"):
            self.db.verify()

    def test_reject_native_intent_event_deletion(self):
        self.assertTrue(admit_native_issue(self.db, self.native, "2026-10-21T10:00:00Z"))
        with self.assertRaises(Exception):
            self.db.conn.execute("DELETE FROM events WHERE kind=?", (KIND,))

    def test_owner_legacy_scheduler_keeps_native_gate_inert(self):
        class NoNativeProvider:
            def protected_main(self): return MAIN
            def d2k_eligible_issues(self, source): return []
            def native_eligible_issues(self, source, *, historical_issues=None):
                raise AssertionError("production must NOT inspect native issues")
        result = run_once(self.db, NoNativeProvider(), self.path, HMAC,
                          now="2026-10-21T10:00:00Z")
        self.assertEqual(result["disposition"], "QUEUE_EMPTY_NO_SCIENCE")
        self.assertEqual(self.db.meta()["head_seq"], 40)

    def test_no_second_pending_work(self):
        self.db.conn.execute(
            "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha) "
            "VALUES(?,?,?,'READY',?)",
            ("f139-existing-ready-task", "Wingless", MAIN, "a"*64))
        with self.assertRaisesRegex(NativeLedgerDenied, "OTHER_WORK_PENDING"):
            admit_native_issue(self.db, self.native, "2026-10-21T10:00:00Z")



    def approval(self):
        return {
            "schema": APPROVAL_SCHEMA, "source_sha": MAIN,
            "expected_event_head_sha256": self.db.meta()["head_hash"],
            "native_development_approved": True,
            "scientific_first_use": False, "create_controller": False,
            "paid_api_calls": 0,
        }

    def test_explicit_native_activation_is_durable_and_idempotent(self):
        self.assertFalse(verify_native_activation(self.db))
        approved = self.approval()
        original = self.db.meta()
        self.assertTrue(activate_native(self.db, approved))
        self.assertEqual(self.db.meta()["head_seq"], original["head_seq"]+1)
        self.assertTrue(verify_native_activation(self.db))
        with self.assertRaisesRegex(NativeLedgerDenied, "APPROVAL_LEDGER_OR_SOURCE_DRIFT"):
            activate_native(self.db, approved)
        self.assertEqual(self.db.meta()["head_seq"], original["head_seq"]+1)
        reopened = Database(self.path)
        self.assertTrue(verify_native_activation(reopened))
        reopened.close()

    def test_native_activation_denies_implicit_authorization(self):
        variants = (
            {"scientific_first_use": True},
            {"create_controller": True},
            {"paid_api_calls": 1},
            {"native_development_approved": False},
            {"source_sha": "9"*40},
            {"expected_event_head_sha256": "9"*64},
        )
        for fields in variants:
            with self.subTest(fields=fields):
                with self.assertRaises(NativeLedgerDenied):
                    activate_native(self.db,{**self.approval(), **fields})
        self.assertFalse(verify_native_activation(self.db))
        self.assertEqual(self.db.meta()["head_seq"],40)

    def test_native_signed_dispatch_provider_custody_restart_no_replay(self):
        """Isolated fake provider, genuine original SQLite state machine."""
        from f139.nci04_owner_issue import make_signed_dispatch_inputs
        from f139.nci04_signed_native import admit_native_intent, receipt_from_report
        from f139.nci04_native_contract import canonical, digest
        from test_nci04_signed_native import report as produce_report
        from test_nci04_provider_receipt import zipper
        issue = self.native
        runid = 39510000000

        class FakeNativeProvider:
            dispatches = []
            archives = {}
            def protected_main(self):return MAIN
            def d2k_eligible_issues(self,source):return []
            def native_eligible_issues(self, source, *, historical_issues=None):return [issue]
            def dispatch_native(self,fields,record):
                self.dispatches.append((fields,record))
                self.auth = fields
            def candidates(self,ticket,started_at):
                return {"id":runid,"ticket":ticket}
            def run_proof(self,run,ticket,source,started_at):
                self.archives = {}
                artifacts = []
                for oslabel in ("ubuntu-latest","windows-latest"):
                    inp = {
                        "key":HMAC, "ticket":issue.ticket,"lane":issue.lane,
                        "source_sha":MAIN,"epoch":"1",
                        "signature":self.auth["signature"],
                        "repository":"spoonman136668-ai/FORGE",
                        "ref":"refs/heads/main","event":"workflow_dispatch",
                        "head_sha":MAIN,"run_attempt":"1",
                        "run_id":str(runid),"os":oslabel,
                    }
                    accepted=admit_native_intent(
                        inp,issue.intent_raw,
                        native_signature=self.auth["native_signature"],
                        issue_number=str(issue.number), issue_id=str(issue.issue_id),
                        issue_body_sha256=issue.issue_body_sha256,
                        authenticated_main_sha=MAIN,
                        authenticated_target_commit=TARGET,
                        authenticated_target_tree=TREE)
                    report=produce_report(accepted)
                    receipt=receipt_from_report(accepted,report)
                    data=zipper(canonical(receipt),report)
                    artid=runid+(1 if oslabel=="ubuntu-latest" else 2)
                    self.archives[artid]=data
                    artifacts.append({
                        "id":artid,"name":"forge-f139-native-receipt-"+oslabel,
                        "expired":False,
                        "workflow_run":{"id":runid,"head_sha":MAIN},
                        "digest":"sha256:"+digest(data),
                        "size_in_bytes":len(data),
                    })
                return runid,artifacts
            def artifact(self,artid):
                return self.archives[artid]

        gh=FakeNativeProvider()
        self.assertTrue(activate_native(self.db,self.approval()))
        started=run_once(self.db,gh,self.path,HMAC,
                         now="2026-10-21T10:00:00Z")
        self.assertEqual(started["disposition"],"DEVELOPMENT_DISPATCHED_ONCE")
        self.assertEqual(len(gh.dispatches),1)
        self.assertEqual(self.db.active()["stage"],"WAIT_PROVIDER")
        self.db.close()
        self.db=Database(self.path)
        self.addCleanup(self.db.close)
        again=run_once(self.db,gh,self.path,HMAC,
                       now="2026-10-21T10:01:00Z")
        self.assertEqual(again["disposition"],"QUEUE_EMPTY_NO_SCIENCE")
        self.assertEqual(len(gh.dispatches),1)
        local=self.db.conn.execute(
            "SELECT * FROM tasks WHERE ticket=?",(issue.ticket,)).fetchone()
        self.assertEqual(local["stage"],"VERIFIED")
        self.assertEqual(local["run_id"],runid)
        evidence=list((self.root/"evidence"/issue.ticket).rglob("*.zip"))
        self.assertEqual(len(evidence),2)
        self.assertEqual(run_once(self.db,gh,self.path,HMAC,
                          now="2026-10-21T10:02:00Z")["disposition"],
                         "QUEUE_EMPTY_NO_SCIENCE")
        self.assertEqual(len(gh.dispatches),1)


if __name__ == "__main__":
    unittest.main()
