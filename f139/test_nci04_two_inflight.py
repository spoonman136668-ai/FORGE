"""F139 same-controller dual native in-flight admission and restart tests.

Only historical fixture identities, mock provider and isolated temporary SQLite.
No paid API, protected first-use, real controller, second scheduler, or dispatch.
"""
import unittest

from f139.local_controller import Database, run_once
from f139.nci04_owner_issue import inspect_owner_issue
from f139.nci04_owner_ledger import (
    activate_native, native_recent_starts, verify_native_activation)
from test_nci04_owner_issue import issue as make_issue, MAIN, TARGET, TREE, HMAC
from test_nci04_owner_ledger import LedgerTests


class NativeDualInFlightTests(unittest.TestCase):
    def setUp(self):
        self.original=LedgerTests("test_admit_exactly_once_and_verify_original_ledger")
        self.original.setUp()
        self.addCleanup(self.original.doCleanups)
        self.db=self.original.db
        self.assertTrue(activate_native(self.db,self.original.approval()))

    def work(self, n):
        raw=make_issue()
        raw["number"]=n
        raw["id"]=5952000000+n
        return inspect_owner_issue(
            raw,protected_main=MAIN,
            authenticated_target_commit=TARGET,
            authenticated_target_tree=TREE)

    class Provider:
        def __init__(self, issues):
            self.issues=issues
            self.dispatches=[]
            self.candidate_reads=[]
        def protected_main(self):return MAIN
        def d2k_eligible_issues(self,source):return []
        def native_eligible_issues(self,source,*,historical_issues=None):
            assert source==MAIN
            return [issue for issue in self.issues
                    if issue.number not in (historical_issues or {})]
        def dispatch_native(self, fields, issue):
            assert fields["ticket"]==issue.ticket
            self.dispatches.append(issue.ticket)
        def candidates(self,ticket,started_at):
            self.candidate_reads.append(ticket)
            return None

    def test_dual_native_dispatched_by_original_tick_and_stable_on_restart(self):
        issues=[self.work(810),self.work(811),self.work(812)]
        api=self.Provider(issues)
        first=run_once(self.db,api,self.original.path,HMAC,
                       now="2026-10-22T10:00:00Z")
        self.assertEqual(first["disposition"],"DEVELOPMENT_DISPATCHED_ONCE")
        self.assertEqual(first["ticket"],issues[0].ticket)
        second=run_once(self.db,api,self.original.path,HMAC,
                        now="2026-10-22T10:01:00Z")
        self.assertEqual(second["disposition"],"DEVELOPMENT_DISPATCHED_ONCE")
        self.assertEqual(second["ticket"],issues[1].ticket)
        self.assertEqual(len(self.db.actives()),2)
        self.assertTrue(all(r["stage"]=="WAIT_PROVIDER" for r in self.db.actives()))
        self.db.verify()
        self.assertEqual(native_recent_starts(
            self.db,"2026-10-22T10:02:00Z"),2)
        third=run_once(self.db,api,self.original.path,HMAC,
                       now="2026-10-22T10:02:00Z")
        self.assertEqual(third["disposition"],
                         "TWO_NATIVE_WORKERS_ACTIVE_NO_REDISPATCH")
        self.assertEqual(api.dispatches,[issues[0].ticket,issues[1].ticket])
        self.assertFalse(any(row["ticket"]==issues[2].ticket
                             for row in self.db.conn.execute("SELECT ticket FROM tasks")))
        self.db.close()
        self.db=Database(self.original.path)
        self.addCleanup(self.db.close)
        self.assertTrue(verify_native_activation(self.db))
        self.assertEqual(len(self.db.actives()),2)
        after_restart=run_once(self.db,api,self.original.path,HMAC,
                               now="2026-10-22T10:03:00Z")
        self.assertEqual(after_restart["disposition"],
                         "TWO_NATIVE_WORKERS_ACTIVE_NO_REDISPATCH")
        self.assertEqual(len(api.dispatches),2)
        self.db.verify()
        self.assertFalse(any(
            ticket==issues[2].ticket for ticket in api.dispatches))

    def test_native_started_second_before_first_provider_has_finished(self):
        issues=[self.work(813),self.work(814)]
        api=self.Provider(issues)
        t0=run_once(self.db,api,self.original.path,HMAC,
                    now="2026-10-22T11:00:00Z")
        self.assertEqual(t0["ticket"],issues[0].ticket)
        t1=run_once(self.db,api,self.original.path,HMAC,
                    now="2026-10-22T11:01:00Z")
        self.assertEqual(t1["ticket"],issues[1].ticket)
        self.assertEqual(len(api.dispatches),2)
        self.assertEqual(len(set(api.dispatches)),2)
        self.assertEqual(len(self.db.actives()),2)


if __name__=="__main__":
    unittest.main()
