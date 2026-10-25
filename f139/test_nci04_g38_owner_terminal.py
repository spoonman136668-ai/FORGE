"""G38 disposable original SQLite + both signed V2 OS receipts.

No original-owner workstation, GitHub network, live controller, credentials
or science. External API provenance remains independently tested by G35.
"""
from __future__ import annotations

import io
import json
from pathlib import Path
import unittest
from unittest import mock
import zipfile

from f139.local_controller import Database, GitHub, store_evidence
from f139.nci04_native_contract import digest
from f139.nci04_g38_owner_terminal import (
    G38Denied, KIND, settle_original_v2, verify_g38_custody,
)
from f139.test_nci04_g32_owner_custody import (
    OriginalOwnerG32Tests, RUN,
)
from f139.test_nci04_owner_issue import HMAC
from f139.test_nci04_worker_v2 import V2ContractTests
from f139.test_nci04_provider_receipt_v2 import bundle

OS = ("ubuntu-latest", "windows-latest")


class G38AtomicOwnerTests(unittest.TestCase):
    def setUp(self):
        fx = OriginalOwnerG32Tests()
        fx.setUp()
        self.addCleanup(fx.doCleanups)
        self.fx = fx
        self.db = fx.db
        self.api = GitHub(runner=lambda a: (_ for _ in ()).throw(
            AssertionError("unplanned provider call")))
        self.ticket = fx.issue.ticket
        self.start = "2026-10-25T16:01:00Z"
        self.path = Path(fx.owner.path)
        self.data = self.make_provider(fx.provider)

    def make_provider(self, reports, *, qualified=None):
        platforms, archives = {}, {}
        for number, label in enumerate(OS):
            body = reports[label]["zip_bytes"]
            outer = io.BytesIO()
            with zipfile.ZipFile(outer, "w", zipfile.ZIP_STORED) as z:
                z.writestr("f139-v2-development-provider.zip", body)
            raw = outer.getvalue()
            archives[label] = raw
            check = (qualified[label] if qualified is not None else True)
            platforms[label] = {
                "job_id":900+number,
                "artifact_id":700+number,
                "outer_artifact_sha256":digest(raw),
                "inner_v2_sha256":digest(body),
                "development_qualified":check}
        return {
            "ticket":self.ticket, "run_id":RUN,
            "source_sha":self.db.meta()["source_sha"],
            "authorize_job_id":899,
            "provider_payloads":reports,
            "outer_archives":archives,
            "platforms":platforms,
            "provider_api_metadata_crosschecked":True,
            "both_platforms_development_qualified": (
                all(p["development_qualified"] for p in platforms.values())),
        }

    def apply(self, provider=None):
        with mock.patch(
            "f139.nci04_g38_owner_terminal.inspect_v2_provider_run",
            return_value=self.data if provider is None else provider):
            return settle_original_v2(
                self.db,self.api,self.path,
                ticket=self.ticket,run_id=RUN,started_at=self.start,
                owner_key=HMAC)

    def test_original_two_os_positive_is_atomic_and_cold_verifiable(self):
        result=self.apply()
        self.assertEqual(result["outcome"],"VERIFIED")
        self.assertFalse(result["scientific_first_use"])
        self.db.verify()
        row=self.db.conn.execute(
            "SELECT stage,run_id,evidence_dir,evidence_sha FROM tasks "
            "WHERE ticket=?", (self.ticket,)).fetchone()
        self.assertEqual((row["stage"],row["run_id"]),("VERIFIED",RUN))
        self.assertTrue(Path(row["evidence_dir"]).is_dir())
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM events WHERE kind=?", (KIND,)).fetchone()[0],1)
        reopened=Database(self.path)
        reopened.verify()
        reopened.close()

    def test_all_v2_negative_receipts_retained_without_replay(self):
        label="windows-latest"
        fixture=V2ContractTests()
        fixture.setUp()
        report=fixture.report(label)
        admission=self.fx.admissions[label]
        report["intent_sha256"]=admission.intent.intent_sha256
        report["qualification_key"]=admission.intent.qualification_key
        report["candidate_sha256"]=admission.intent.after_sha256
        report["candidate_behavior"][0]["outcome"]="TEST_FAILURE"
        report["candidate_behavior"][0]["returncode"]=1
        report["candidate_behavior"]=report["candidate_behavior"][:1]
        report["candidate_compile"]=None
        report["qualification_complete"]=False
        blob,meta=bundle(admission,report)
        reports=dict(self.fx.provider)
        reports[label]={"zip_bytes":blob,"metadata":meta}
        signed=self.make_provider(reports,qualified={
            "ubuntu-latest":True,"windows-latest":False})
        result=self.apply(signed)
        self.assertEqual(result["outcome"],"QUARANTINED")
        row=self.db.conn.execute(
            "SELECT stage,run_id,quarantine_reason FROM tasks WHERE ticket=?",
            (self.ticket,)).fetchone()
        self.assertEqual(row["stage"],"QUARANTINED")
        self.assertIsNone(row["run_id"])
        self.assertEqual(row["quarantine_reason"],"FAILED_OR_CANCELLED_NO_REPLAY")
        self.db.verify()
        reopened=Database(self.path)
        reopened.verify()
        reopened.close()
        with self.assertRaisesRegex(G38Denied,"EXACT_WAIT_PROVIDER_NO_REPLAY"):
            self.apply(signed)

    def test_crash_after_files_before_sql_recovers_only_same_bytes(self):
        folder,sha=store_evidence(
            self.path.parent,self.ticket,RUN,self.data["outer_archives"])
        self.assertTrue(Path(folder).is_dir())
        result=self.apply()
        self.assertEqual(result["evidence_manifest_sha256"],sha)
        self.db.verify()

    def test_changed_crash_recovery_bytes_fail_closed(self):
        store_evidence(
            self.path.parent,self.ticket,RUN,self.data["outer_archives"])
        other=dict(self.data)
        changed=dict(other["outer_archives"])
        changed["windows-latest"]=b"untrusted"
        other["outer_archives"]=changed
        with self.assertRaises(ValueError):
            self.apply(other)
        row=self.db.conn.execute(
            "SELECT stage FROM tasks WHERE ticket=?",
            (self.ticket,)).fetchone()
        self.assertEqual(row["stage"],"WAIT_PROVIDER")

    def test_corrupt_durable_zip_detected_on_cold_verification(self):
        self.apply()
        directory=Path(self.db.conn.execute(
            "SELECT evidence_dir FROM tasks WHERE ticket=?",
            (self.ticket,)).fetchone()[0])
        (directory/"ubuntu-latest.zip").write_bytes(b"tampered")
        with self.assertRaisesRegex(G38Denied,"COLD_CUSTODY_GITHUB_ARCHIVE_TAMPERED"):
            self.db.verify()

    def test_second_terminal_cannot_rewrite_verified_owner(self):
        self.apply()
        with self.assertRaisesRegex(G38Denied,"EXACT_WAIT_PROVIDER_NO_REPLAY"):
            self.apply()
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM events WHERE kind=?", (KIND,)).fetchone()[0],1)

    def test_rejected_provider_provenance_does_not_mutate_sqlite(self):
        before=self.db.meta()
        with mock.patch(
            "f139.nci04_g38_owner_terminal.inspect_v2_provider_run",
            side_effect=ValueError("UNTRUSTED_PROVIDER_RUN")):
            with self.assertRaisesRegex(ValueError,"UNTRUSTED_PROVIDER_RUN"):
                settle_original_v2(
                    self.db,self.api,self.path,
                    ticket=self.ticket,run_id=RUN,started_at=self.start,
                    owner_key=HMAC)
        self.assertEqual(before,self.db.meta())
        self.assertFalse((self.path.parent/"evidence"/self.ticket).exists())

    def test_run_id_mismatch_rejected_by_independent_os_receipts(self):
        with self.assertRaises(ValueError):
            with mock.patch(
                "f139.nci04_g38_owner_terminal.inspect_v2_provider_run",
                return_value=self.data):
                settle_original_v2(
                    self.db,self.api,self.path,
                    ticket=self.ticket,run_id=RUN+1,started_at=self.start,
                    owner_key=HMAC)
        self.assertEqual(self.db.conn.execute(
            "SELECT stage FROM tasks WHERE ticket=?",
            (self.ticket,)).fetchone()[0],"WAIT_PROVIDER")

    def test_version_specific_event_and_no_science(self):
        self.apply()
        event=self.db.conn.execute(
            "SELECT payload FROM events WHERE kind=?", (KIND,)).fetchone()
        doc=json.loads(event["payload"])
        self.assertEqual(doc["schema"],
            "forge.f139.g38.original-v2-provider-custody.v1")
        self.assertFalse(doc["scientific_first_use"])
        self.assertEqual(doc["paid_model_calls"],0)
        self.assertEqual(doc["accepted_ref_mutations"],0)
        self.assertGreater(doc["original_admission_event_seq"],220)


if __name__=="__main__":
    unittest.main()
