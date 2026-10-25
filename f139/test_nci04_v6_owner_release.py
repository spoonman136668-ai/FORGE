"""G15 fail-closed approval contract tests; entirely read only."""
import copy
import json
import sqlite3
import unittest

from f139.nci04_native_contract import canonical,digest
from f139.nci04_v6_owner_release import (
    APPROVAL_SCHEMA, V6ReleaseDenied, validate_v6_owner_approval,
)
from f139.nci04_owner_ledger import SEALED_OWNER_PREFIX_HEAD


class FakeDB:
    def __init__(self):
        self.head="c"*64
        self.source="a"*40
        self.v5="d"*64
        self.conn=sqlite3.connect(":memory:")
        self.conn.row_factory=sqlite3.Row
        self.conn.execute("CREATE TABLE events(seq INTEGER,kind TEXT,sha TEXT,payload TEXT)")
        self.conn.execute("CREATE TABLE tasks(ticket TEXT,stage TEXT)")
        first="f139-nci04-first"
        second="f139-nci04-second"
        self.tickets=[first,second]+[f"f139-nci04-{i}" for i in range(11)]
        for t in self.tickets:
            self.conn.execute("INSERT INTO tasks VALUES(?,'QUARANTINED')",(t,))
        docs=[]
        for n in range(4):
            d={"schema":"forge.f139.source-transition.v5",
               "from_source_sha":f"{n+1:040x}",
               "to_source_sha":f"{n+2:040x}"}
            docs.append(d)
            self.conn.execute(
                "INSERT INTO events VALUES(?, 'SOURCE_TRANSITION_ADMITTED',?,?)",
                (n+1, self.v5 if n==3 else f"{n+1:064x}",canonical(d).decode()))
        self.first=first
        self.second=second
        self.failures={t:(self.source,"b"*64) for t in self.tickets[2:]}

    def meta(self):
        return {"source_sha":self.source,"head_seq":218,"head_hash":self.head,
                "enabled":1,"legacy_suspended":1}

    def actives(self):
        return []

    def ready(self):
        return None

    def verified_native_provider_failures(self):
        return self.failures


class G15ApprovalTests(unittest.TestCase):
    def setUp(self):
        from unittest import mock
        self.db=FakeDB()
        self.pin=mock.patch(
            "f139.nci04_negative_owner_store.TICKET",self.db.first)
        self.second=mock.patch(
            "f139.nci04_split_negative_owner_store.TICKET",self.db.second)
        self.pin.start();self.second.start()
        self.addCleanup(self.pin.stop);self.addCleanup(self.second.stop)
        self.approval={
            "schema":APPROVAL_SCHEMA,
            "from_source_sha":"a"*40,"to_source_sha":"e"*40,
            "expected_event_head_sha256":"c"*64,
            "expected_event_head_seq":218,
            "sealed_23_event_head_sha256":SEALED_OWNER_PREFIX_HEAD,
            "v5_terminal_event_sha256":"d"*64,
            "custodied_negative_tickets_sha256":digest(canonical(sorted(self.db.tickets))),
            "native_development_only":True,"v2_receipt_authorized":False,
            "scientific_first_use":False,"new_controller":False,
            "new_scheduler":False,"paid_api_calls":0}

    def test_exact_explicit_schema_passes_without_modification(self):
        before=list(self.db.conn.execute("SELECT * FROM events"))
        x=validate_v6_owner_approval(self.db,self.approval)
        self.assertEqual(x["negative_tasks"],13)
        self.assertFalse(x["v2_receipt_authorized"])
        self.assertEqual(before,list(self.db.conn.execute("SELECT * FROM events")))

    def test_all_unapproved_flags_are_refused(self):
        changes=[
            ("schema","forge.f139.nci04.owner-source-transition-approval.v1"),
            ("from_source_sha","0"*40),
            ("expected_event_head_sha256","0"*64),
            ("expected_event_head_seq",219),
            ("sealed_23_event_head_sha256","0"*64),
            ("v5_terminal_event_sha256","0"*64),
            ("custodied_negative_tickets_sha256","0"*64),
            ("native_development_only",False),
            ("v2_receipt_authorized",True),
            ("scientific_first_use",True),
            ("new_controller",True),("new_scheduler",True),
            ("paid_api_calls",1),
            ("to_source_sha","1"*40),
        ]
        for key,value in changes:
            with self.subTest(key=key):
                q=dict(self.approval,**{key:value})
                with self.assertRaises(V6ReleaseDenied):
                    validate_v6_owner_approval(self.db,q)

    def test_missing_extra_and_second_v6_are_rejected(self):
        for change in ("missing","extra","v6"):
            with self.subTest(change=change):
                q=copy.deepcopy(self.approval)
                if change=="missing":q.pop("v5_terminal_event_sha256")
                if change=="extra":q["allow_arbitrary"]=True
                if change=="v6":
                    x={"schema":"forge.f139.source-transition.v6",
                       "from_source_sha":"a"*40,"to_source_sha":"e"*40}
                    self.db.conn.execute(
                        "INSERT INTO events VALUES(999,'SOURCE_TRANSITION_ADMITTED',?,?)",
                        ("f"*64,canonical(x).decode()))
                with self.assertRaises(V6ReleaseDenied):
                    validate_v6_owner_approval(self.db,q)

    def test_active_pending_and_negative_drift_rejected(self):
        self.db.ready=lambda:{"ticket":"bad"}
        with self.assertRaises(V6ReleaseDenied):
            validate_v6_owner_approval(self.db,self.approval)
        self.db.ready=lambda:None
        self.db.conn.execute("DELETE FROM tasks WHERE ticket=?",(self.db.tickets[0],))
        with self.assertRaises(V6ReleaseDenied):
            validate_v6_owner_approval(self.db,self.approval)


if __name__=="__main__":
    unittest.main()
