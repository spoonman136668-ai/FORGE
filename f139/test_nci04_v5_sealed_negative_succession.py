"""Bounded v5 successor across saturated original v4 negative custody.

Synthetic source transitions only. The original immutable provider receipts,
their real SHA lineage and all existing scientific negatives remain untouched.
"""
import json
import unittest
from unittest import mock

from f139.local_controller import F139Error
from f139.nci04_owner_ledger import activate_native, verify_native_activation
from test_nci04_v4_provider_recovery import OwnerProviderV4


class V5SealedOriginalHistory(OwnerProviderV4):
    def saturated_v4(self):
        self.bootstrap()
        for n in range(10):
            self.db.transition_source(
                f"{100+n:040x}", allow_certified_negative=True)
            self.db.verify()
        records=[
            r for r in self.db.conn.execute(
                "SELECT seq,sha,payload FROM events "
                "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")
            if json.loads(r["payload"])["schema"] ==
                "forge.f139.source-transition.v4"]
        self.assertEqual(len(records),10)
        self.assertTrue(verify_native_activation(self.db) is False)
        return records[-1]["sha"]

    def test_v5_seals_saturated_v4_and_preserves_all_negatives(self):
        with mock.patch("f139.nci04_owner_ledger.audit_native_events"):
            v4_seal=self.saturated_v4()
            old_head=self.db.meta()["head_hash"]
            old_events=[
                (r["seq"],r["sha"]) for r in self.db.conn.execute(
                    "SELECT seq,sha FROM events ORDER BY seq")]
            new_source=f"{500:040x}"
            self.db.transition_source(new_source,allow_certified_negative=True)
            self.db.verify()
            doc=json.loads(self.db.conn.execute(
                "SELECT payload FROM events ORDER BY seq DESC LIMIT 1").fetchone()["payload"])
            self.assertEqual(doc["schema"],"forge.f139.source-transition.v5")
            self.assertEqual(doc["v4_terminal_event_sha256"],v4_seal)
            self.assertNotEqual(self.db.meta()["head_hash"],old_head)
            self.assertEqual(self.db.meta()["source_sha"],new_source)
            self.assertFalse(doc["scientific_first_use"])
            self.assertEqual(doc["new_dispatches"],0)
            self.assertEqual(doc["custodied_negative_tasks"],4)
            historical=[
                (r["seq"],r["sha"]) for r in self.db.conn.execute(
                    "SELECT seq,sha FROM events ORDER BY seq LIMIT ?",(len(old_events),))]
            self.assertEqual(historical,old_events)
            approval={
                "schema":"forge.f139.nci04.owner-native-approval.v1",
                "source_sha":new_source,
                "expected_event_head_sha256":self.db.meta()["head_hash"],
                "native_development_approved":True,
                "scientific_first_use":False,"create_controller":False,
                "paid_api_calls":0,
            }
            self.assertTrue(activate_native(self.db,approval))
            self.assertTrue(verify_native_activation(self.db))
            self.db.verify()

    def test_v5_bounded_four_sources_and_fifth_denied(self):
        with mock.patch("f139.nci04_owner_ledger.audit_native_events"):
            self.saturated_v4()
            for n in range(4):
                self.db.transition_source(
                    f"{600+n:040x}",allow_certified_negative=True)
                self.db.verify()
            meta=self.db.meta().copy()
            events=self.db.conn.execute(
                "SELECT COUNT(*) FROM events").fetchone()[0]
            with self.assertRaisesRegex(F139Error,
                                        "SOURCE_TRANSITION_V5_BOUNDED_CAPACITY"):
                self.db.transition_source(
                    f"{604:040x}",allow_certified_negative=True)
            self.assertEqual(self.db.meta(),meta)
            self.assertEqual(self.db.conn.execute(
                "SELECT COUNT(*) FROM events").fetchone()[0],events)
            self.db.verify()

    def test_v5_refuses_historical_source_replay(self):
        with mock.patch("f139.nci04_owner_ledger.audit_native_events"):
            self.saturated_v4()
            before=self.db.meta().copy()
            with self.assertRaisesRegex(F139Error,"SOURCE_TRANSITION_V4_NEGATIVES"):
                self.db.transition_source(
                    f"{100:040x}",allow_certified_negative=True)
            self.assertEqual(self.db.meta(),before)
            self.db.verify()


if __name__=="__main__":
    unittest.main()
