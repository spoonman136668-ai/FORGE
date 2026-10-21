"""A8C: retain actual negative custody across native source succession.

Source-only synthetic SQLite fixtures. Never use or overwrite original F139
owner database, original #696 provider run or protected scientific first-use.
"""
import json
import unittest
from unittest import mock

from f139.local_controller import Database, F139Error
from f139.nci04_owner_ledger import (
    activate_native, verify_native_activation, APPROVAL_SCHEMA,
    NativeLedgerDenied)
from f139.nci04_negative_owner_store import (
    OwnerNegativeCustodyDenied, KIND)
from test_nci04_negative_owner_store import OwnerNegativeStoreTests
from test_nci04_owner_issue import MAIN

NEW = "e"*40
THIRD = "f"*40


class SuccessionFromCertifiedNegative(unittest.TestCase):
    def setUp(self):
        # The A8B test fixture is isolated and pins synthetic original heads.
        OwnerNegativeStoreTests.setUp(self)

    def admit(self, **kw):
        return OwnerNegativeStoreTests.admit(self, **kw)

    def approve(self, source):
        return {
            "schema":APPROVAL_SCHEMA,
            "source_sha":source,
            "expected_event_head_sha256":self.db.meta()["head_hash"],
            "native_development_approved":True,
            "scientific_first_use":False,
            "create_controller":False,
            "paid_api_calls":0,
        }

    def test_quarantined_original_cannot_advance_without_custody(self):
        before=self.db.meta()
        with self.assertRaisesRegex(F139Error,
                                    "SOURCE_TRANSITION_UNVERIFIED_OR_PENDING_TASK"):
            self.db.transition_source(NEW)
        with self.assertRaisesRegex((F139Error,ValueError),
                                    "SOURCE_TRANSITION_NEGATIVE_NOT_CUSTODIED"):
            self.db.transition_source(NEW,allow_certified_negative=True)
        self.assertEqual(self.db.meta(),before)
        self.assertFalse(verify_native_activation(self.db))

    def test_original_custody_allows_new_source_activation_no_replay(self):
        negative=self.admit()
        self.assertEqual(self.db.meta()["head_seq"],48)
        self.assertIs(negative["successor_source_transition_authorized"],False)
        original_events=[
            dict(row) for row in self.db.conn.execute(
                "SELECT seq,kind,payload,prior_sha,sha FROM events ORDER BY seq")]
        original_row=dict(self.db.conn.execute(
            "SELECT * FROM tasks WHERE ticket=?",(self.native.ticket,)).fetchone())
        self.db.transition_source(NEW,allow_certified_negative=True)
        self.assertEqual(self.db.meta()["head_seq"],49)
        self.assertEqual(self.db.meta()["source_sha"],NEW)
        transition=json.loads(self.db.conn.execute(
            "SELECT payload FROM events WHERE seq=49").fetchone()["payload"])
        self.assertEqual(transition["schema"],"forge.f139.source-transition.v2")
        self.assertEqual(transition["custodied_negative_tasks"],1)
        self.assertEqual(transition["verified_historical_tasks"],6)
        self.assertFalse(verify_native_activation(self.db))
        self.assertTrue(activate_native(self.db,self.approve(NEW)))
        self.assertTrue(verify_native_activation(self.db))
        self.assertEqual(self.db.meta()["head_seq"],50)
        with self.assertRaisesRegex(NativeLedgerDenied,"NATIVE_ALREADY_ACTIVATED"):
            activate_native(self.db,self.approve(NEW))
        self.assertEqual(dict(self.db.conn.execute(
            "SELECT * FROM tasks WHERE ticket=?",(self.native.ticket,)).fetchone()),
            original_row)
        self.assertEqual([
            dict(row) for row in self.db.conn.execute(
                "SELECT seq,kind,payload,prior_sha,sha FROM events WHERE seq<=48 ORDER BY seq")],
            original_events)
        self.db.close()
        self.db=Database(self.path)
        self.addCleanup(self.db.close)
        self.db.verify()
        self.assertTrue(verify_native_activation(self.db))
        self.assertEqual(self.db.meta()["head_seq"],50)

    def test_future_separate_source_requires_new_owner_approval(self):
        self.admit()
        self.db.transition_source(NEW,allow_certified_negative=True)
        self.assertTrue(activate_native(self.db,self.approve(NEW)))
        self.db.transition_source(THIRD,allow_certified_negative=True)
        self.assertFalse(verify_native_activation(self.db))
        self.assertTrue(activate_native(self.db,self.approve(THIRD)))
        self.assertTrue(verify_native_activation(self.db))
        activations=[
            json.loads(r["payload"]) for r in self.db.conn.execute(
                "SELECT payload FROM events WHERE kind='NATIVE_DEVELOPMENT_ACTIVATED'"
                " ORDER BY seq")]
        self.assertEqual([a["source_sha"] for a in activations],[NEW,THIRD])
        self.db.verify()

    def test_original_zip_tamper_blocks_every_later_source(self):
        self.admit()
        self.db.transition_source(NEW,allow_certified_negative=True)
        self.assertTrue(activate_native(self.db,self.approve(NEW)))
        from f139.nci04_negative_owner_store import _paths
        _,_,original=_paths(self.db,self.native.ticket,self.rid)
        original.write_bytes(b"forged archive")
        with self.assertRaisesRegex(OwnerNegativeCustodyDenied,
                                    "ORIGINAL_ZIP_CUSTODY_TAMPERED"):
            self.db.verify()
        with self.assertRaises(OwnerNegativeCustodyDenied):
            self.db.transition_source(THIRD,allow_certified_negative=True)
        self.assertEqual(self.db.meta()["source_sha"],NEW)

    def test_other_pending_or_quarantined_task_blocks_succession(self):
        self.admit()
        self.db.conn.execute(
            "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha)"
            " VALUES(?,?,?,'READY',?)",
            ("f139-not-authorized", "Wingless", MAIN, "a"*64))
        with self.assertRaisesRegex(F139Error,"SOURCE_TRANSITION_UNVERIFIED_OR_PENDING_TASK"):
            self.db.transition_source(NEW,allow_certified_negative=True)
        self.assertEqual(self.db.meta()["source_sha"],MAIN)


if __name__=="__main__":
    unittest.main()
