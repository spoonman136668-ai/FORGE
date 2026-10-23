"""Provider-negative custody: preserve failures without replay or source bypass."""
import unittest

from f139.nci04_owner_issue import inspect_owner_issue
from f139.nci04_owner_ledger import admit_native_issue
from test_nci04_owner_issue import issue as make_issue, MAIN, TARGET, TREE
from test_nci04_owner_ledger import LedgerTests


class ProviderNegativeCustodyTests(unittest.TestCase):
    def setUp(self):
        self.owner=LedgerTests("test_admit_exactly_once_and_verify_original_ledger")
        self.owner.setUp()
        self.addCleanup(self.owner.doCleanups)
        self.db=self.owner.db

    def work(self, number):
        raw=make_issue()
        raw["number"]=number
        raw["id"]=5952234000+number
        return inspect_owner_issue(
            raw, protected_main=MAIN,
            authenticated_target_commit=TARGET,
            authenticated_target_tree=TREE)

    def report(self, ticket, run_id):
        return {
            "ticket":ticket,"run_id":run_id,"source_sha":MAIN,
            "jobs":{
                "windows-latest":{"job_id":run_id+1,"conclusion":"failure"},
                "ubuntu-latest":{"job_id":run_id+2,"conclusion":"failure"},
            },
            "artifact_ids":[run_id+3,run_id+4],
            "provider_terminal":"FAILURE_NO_REPLAY",
            "scientific_first_use":False,
        }

    def start(self, number):
        work=self.work(number)
        self.assertTrue(admit_native_issue(
            self.db,work,"2026-10-23T21:00:00Z"))
        self.db.claim(work.ticket,"2026-10-23T21:00:01Z")
        self.db.dispatch_observed(work.ticket)
        return work

    def test_future_failure_custody_precedes_quarantine(self):
        work=self.start(901)
        self.assertTrue(self.db.custody_failed_native_provider(
            work.ticket,self.report(work.ticket,40030000001),late=False))
        row=self.db.conn.execute(
            "SELECT stage,quarantine_reason,run_id FROM tasks WHERE ticket=?",
            (work.ticket,)).fetchone()
        self.assertEqual(row["stage"],"QUARANTINED")
        self.assertEqual(row["quarantine_reason"],
                         "FAILED_OR_CANCELLED_NO_REPLAY")
        self.assertIsNone(row["run_id"])
        kinds=[r["kind"] for r in self.db.conn.execute(
            "SELECT kind FROM events ORDER BY seq DESC LIMIT 2")]
        self.assertEqual(kinds,["ATTEMPT_QUARANTINED",
                                "NATIVE_FAILED_PROVIDER_CUSTODY"])
        accepted=self.db.verified_native_provider_failures()
        self.assertEqual(accepted[work.ticket][0],MAIN)
        self.db.verify()

    def test_late_custody_binds_existing_exact_quarantine_event(self):
        work=self.start(902)
        self.db.quarantine(work.ticket,"FAILED_OR_CANCELLED_NO_REPLAY")
        q=self.db.conn.execute(
            "SELECT seq,sha FROM events WHERE kind='ATTEMPT_QUARANTINED' "
            "ORDER BY seq DESC LIMIT 1").fetchone()
        before=self.db.meta()["head_seq"]
        self.assertTrue(self.db.custody_failed_native_provider(
            work.ticket,self.report(work.ticket,40030000011),late=True))
        self.assertEqual(self.db.meta()["head_seq"],before+1)
        payload=self.db.conn.execute(
            "SELECT payload FROM events WHERE kind='NATIVE_FAILED_PROVIDER_CUSTODY' "
            "ORDER BY seq DESC LIMIT 1").fetchone()["payload"]
        import json
        doc=json.loads(payload)
        self.assertEqual(doc["schema"],
                         "forge.f139.owner-native-provider-negative.v2")
        self.assertEqual(doc["quarantine_event_seq"],q["seq"])
        self.assertEqual(doc["quarantine_event_sha256"],q["sha"])
        self.assertEqual(
            self.db.verified_native_provider_failures()[work.ticket][0],MAIN)
        self.db.verify()

    def test_duplicate_or_forged_late_custody_fails_closed(self):
        work=self.start(903)
        self.db.quarantine(work.ticket,"FAILED_OR_CANCELLED_NO_REPLAY")
        report=self.report(work.ticket,40030000021)
        self.db.custody_failed_native_provider(work.ticket,report,late=True)
        with self.assertRaisesRegex(Exception,"ALREADY_CUSTODIED"):
            self.db.custody_failed_native_provider(work.ticket,report,late=True)
        other=self.start(904)
        bad=self.report(other.ticket,40030000031)
        bad["source_sha"]="f"*40
        with self.assertRaisesRegex(Exception,"TASK_SOURCE_DRIFT"):
            self.db.custody_failed_native_provider(other.ticket,bad,late=False)


if __name__=="__main__":
    unittest.main()
