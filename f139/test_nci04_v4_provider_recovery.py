"""Synthetic v4 provider-negative source succession: no real provider or operator writes."""
import unittest
from unittest import mock

from f139.local_controller import F139Error, hash_bytes, canonical
from f139.nci04_owner_ledger import activate_native
from test_nci04_two_negative_transition import TwoNegativeControllerIntegration, NEW_SOURCE


class OwnerProviderV4(TwoNegativeControllerIntegration):
    def bootstrap(self):
        self.append_second()
        self.transition()
        source=NEW_SOURCE
        original23=self.db.conn.execute("SELECT sha FROM events WHERE seq=23").fetchone()["sha"]
        synthetic=mock.patch("f139.nci04_owner_ledger.SEALED_OWNER_PREFIX_HEAD",original23)
        synthetic.start()
        self.addCleanup(synthetic.stop)
        self.assertEqual(self.db.meta()["source_sha"],source)
        # Synthetic predecessor fixture: add the same six historical
        # verified identities the original frozen D2K foundation requires.
        # Production checks remain unmodified and are exercised directly.
        from f139.nci04_negative_owner_store import SOURCE_SHA as OLD_SOURCE
        historic=(
            ("f139-d2c-wingless-659bb1f4d751","Wingless",44),
            ("f139-d2j-wingless-5a252f8dde24","Wingless",45),
            ("f139-d2j-yggdrasil-5a252f8dde24","Yggdrasil",46),
            ("f139-d2k-i687-5a252f8dde24-5a2ecddb","Wingless",39513293606),
            ("f139-d2k-i688-5a252f8dde24-02ded761","Yggdrasil",39513381790),
        )
        for ticket,lane,rid in historic:
            self.db.conn.execute(
                "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha,"
                "run_id,evidence_dir,evidence_sha) VALUES(?,?,?,'VERIFIED',?,?,?,?)",
                (ticket,lane,OLD_SOURCE,"a"*64,rid,
                 "/synthetic/verified","b"*64))
        approval={
            "schema":"forge.f139.nci04.owner-native-approval.v1",
            "source_sha":source,
            "expected_event_head_sha256":self.db.meta()["head_hash"],
            "native_development_approved":True,
            "scientific_first_use":False,"create_controller":False,
            "paid_api_calls":0,
        }
        activate_native(self.db,approval)
        self.assertTrue(self.db.meta()["head_seq"]>=58)
        for issue,lane,failed in ((900,"Wingless","ubuntu-latest"),
                                  (901,"Yggdrasil","windows-latest")):
            ticket="f139-nci04-i"+str(issue)+"-"+source[:12]+"-"+("a"*8 if issue==900 else "b"*8)
            provider={
                "ticket":ticket,"run_id":39930000000+issue,
                "source_sha":source,
                "jobs":{
                    "ubuntu-latest":{"job_id":900000+issue,
                        "conclusion":"failure" if failed=="ubuntu-latest" else "success"},
                    "windows-latest":{"job_id":990000+issue,
                        "conclusion":"failure" if failed=="windows-latest" else "success"},
                },
                "artifact_ids":[90001+issue],
                "provider_terminal":"FAILURE_NO_REPLAY",
                "scientific_first_use":False,
            }
            with self.db.transaction():
                self.db.conn.execute(
                    "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha,"
                    "quarantine_reason) VALUES(?,?,?,'QUARANTINED',?,?)",
                    (ticket,lane,source,"d"*64,"FAILED_OR_CANCELLED_NO_REPLAY"))
                self.db.event("NATIVE_FAILED_PROVIDER_CUSTODY",{
                    "schema":"forge.f139.owner-native-provider-negative.v1",
                    "ticket":ticket,"run_id":provider["run_id"],
                    "source_sha":source,
                    "provider_sha256":hash_bytes(canonical(provider)),
                    "provider":provider,"scientific_first_use":False})
                self.db.event("ATTEMPT_QUARANTINED",{
                    "ticket":ticket,"reason":"FAILED_OR_CANCELLED_NO_REPLAY"})
        return source

    def test_v4_two_authenticated_provider_negatives_source_transition(self):
        source=self.bootstrap()
        sealed=self.db.meta()["head_hash"]
        prior_events=[tuple(r) for r in self.db.conn.execute(
            "SELECT seq,sha FROM events ORDER BY seq")]
        with mock.patch("f139.nci04_owner_ledger.audit_native_events"):
            self.db.verify()
            self.db.transition_source("d"*40,allow_certified_negative=True)
            self.db.verify()
            self.assertNotEqual(self.db.meta()["head_hash"],sealed)
            self.assertEqual(self.db.meta()["source_sha"],"d"*40)
            after_events=[tuple(r) for r in self.db.conn.execute(
                "SELECT seq,sha FROM events ORDER BY seq LIMIT ?",(len(prior_events),))]
            self.assertEqual(prior_events,after_events)
            doc=self.db.conn.execute(
                "SELECT payload FROM events ORDER BY seq DESC LIMIT 1").fetchone()
            import json
            val=json.loads(doc["payload"])
            self.assertEqual(val["schema"],"forge.f139.source-transition.v4")
            self.assertEqual(val["custodied_negative_tasks"],4)
            self.assertEqual(len(val["custodied_negative_tickets"]),4)
            self.assertEqual(len(val["provider_failures_sha256"]),64)
            # Original-owner recovery: the first v4 source transition was
            # sealed but activation failed. Permit exactly one idle, no-new-
            # dispatch v4 successor, then require new per-source approval.
            self.db.transition_source("e"*40,allow_certified_negative=True)
            self.assertEqual(self.db.meta()["source_sha"],"e"*40)
            approval={
                "schema":"forge.f139.nci04.owner-native-approval.v1",
                "source_sha":"e"*40,
                "expected_event_head_sha256":self.db.meta()["head_hash"],
                "native_development_approved":True,
                "scientific_first_use":False,"create_controller":False,
                "paid_api_calls":0,
            }
            from f139.nci04_owner_ledger import verify_native_activation
            self.assertTrue(activate_native(self.db,approval))
            self.assertTrue(verify_native_activation(self.db))
            self.assertEqual(self.db.meta()["head_seq"],len(prior_events)+3)
            self.db.close()
            from f139.local_controller import Database
            self.db=Database(self.path)
            self.addCleanup(self.db.close)
            self.db.verify()

    def test_forged_provider_event_digest_is_rejected(self):
        self.bootstrap()
        with self.db.transaction():
            event=self.db.conn.execute(
                "SELECT seq,payload FROM events "
                "WHERE kind='NATIVE_FAILED_PROVIDER_CUSTODY' ORDER BY seq LIMIT 1").fetchone()
            import json
            value=json.loads(event["payload"])
            value["provider_sha256"]="e"*64
            import sqlite3
            with self.assertRaises(sqlite3.IntegrityError):
                self.db.conn.execute("UPDATE events SET payload=? WHERE seq=?",
                                     (canonical(value).decode(),event["seq"]))
        self.db.verify()

    def test_v4_refuses_unlisted_extra_negative(self):
        self.bootstrap()
        with self.db.transaction():
            self.db.conn.execute(
                "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha,"
                "quarantine_reason) VALUES(?,?,?,'QUARANTINED',?,?)",
                ("f139-nci04-i903-"+NEW_SOURCE[:12]+"-"+"a"*8,"Wingless",
                 NEW_SOURCE,"e"*64,"FAILED_OR_CANCELLED_NO_REPLAY"))
        with mock.patch("f139.nci04_owner_ledger.audit_native_events"):
            with self.assertRaises(F139Error):
                self.db.transition_source("d"*40,allow_certified_negative=True)
            self.assertEqual(self.db.meta()["source_sha"],NEW_SOURCE)


if __name__=="__main__":
    unittest.main()
