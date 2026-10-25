"""G32: genuine isolated SQLite transitions and V2 provider ZIP validation."""
from __future__ import annotations

import base64
from dataclasses import replace
import json
from unittest import mock
import unittest

from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_issue import inspect_owner_issue, make_signed_dispatch_inputs
from f139.nci04_owner_ledger import admit_native_issue, activate_native
from f139.nci04_signed_native import admit_native_intent
from f139.nci04_v2_owner_permit import issue_v2_owner_permit
from f139.nci04_worker_v2 import SOURCE_SHA, SOURCE_TREE
from f139.nci04_g32_owner_custody import (
    V2CustodyDenied, authenticate_original_admission,
    verify_v2_development_custody,
)
from f139.test_nci04_owner_ledger import LedgerTests
from f139.test_nci04_owner_issue import (
    issue as original_fixture, MAIN, HMAC,
)
from f139.test_nci04_worker_v2 import V2ContractTests
from f139.test_nci04_provider_receipt_v2 import bundle

RUN = 40200000001


class OriginalOwnerG32Tests(unittest.TestCase):
    def setUp(self):
        # Real SQLite engine and SHA event-chain with a synthetic original
        # prefix. This never touches the protected owner's real database.
        self.owner = LedgerTests()
        self.owner.setUp()
        self.addCleanup(self.owner.doCleanups)
        self.db = self.owner.db
        for n in range(180):
            with self.db.transaction():
                self.db.event("FIXTURE_UNTRUSTED", {"step": n})
        self.assertEqual(self.db.meta()["head_seq"], 220)
        self.assertTrue(activate_native(self.db, self.owner.approval()))
        raw = original_fixture("Yggdrasil")
        body = json.loads(raw["body"])
        obj = json.loads(base64.b64decode(body["intent_base64"]))
        change = b"def g32_source_only_probe():\n    return None\n"
        obj.update({
            "target_commit": SOURCE_SHA, "target_tree_sha": SOURCE_TREE,
            "path": "yggdrasil/public_causal_cells.py",
            "before_sha256": digest(b""), "after_sha256": digest(change),
            "after_base64": base64.b64encode(change).decode("ascii"),
        })
        body["intent_base64"] = base64.b64encode(canonical(obj)).decode("ascii")
        raw["body"] = json.dumps(body, sort_keys=True)
        self.issue = inspect_owner_issue(
            raw, protected_main=MAIN,
            authenticated_target_commit=SOURCE_SHA,
            authenticated_target_tree=SOURCE_TREE)
        self.assertTrue(admit_native_issue(
            self.db, self.issue, "2026-10-25T16:00:00Z"))
        self.db.claim(self.issue.ticket, "2026-10-25T16:01:00Z")
        self.db.dispatch_observed(self.issue.ticket)
        self.db.verify()
        self.admissions = {}
        self.permits = {}
        self.provider = {}
        frozen = next(row for row in self.db.conn.execute(
            "SELECT seq,sha,payload FROM events WHERE kind='NATIVE_DEVELOPMENT_ADMITTED'")
            if json.loads(row["payload"])["ticket"] == self.issue.ticket)
        fields = make_signed_dispatch_inputs(
            self.issue, owner_hmac_key=HMAC, epoch=self.db.meta()["epoch"])
        self.frozen = frozen
        f = V2ContractTests()
        f.setUp()
        for oslabel in ("ubuntu-latest", "windows-latest"):
            controller = {
                "key": HMAC, "ticket": self.issue.ticket,
                "lane": "Yggdrasil", "source_sha": MAIN,
                "epoch": str(self.db.meta()["epoch"]),
                "signature": fields["signature"],
                "repository": "spoonman136668-ai/FORGE",
                "ref": "refs/heads/main",
                "event": "workflow_dispatch", "head_sha": MAIN,
                "run_attempt": "1", "run_id": str(RUN), "os": oslabel,
            }
            a = admit_native_intent(
                controller, self.issue.intent_raw,
                native_signature=fields["native_signature"],
                issue_number=str(self.issue.number),
                issue_id=str(self.issue.issue_id),
                issue_body_sha256=self.issue.issue_body_sha256,
                authenticated_main_sha=MAIN,
                authenticated_target_commit=SOURCE_SHA,
                authenticated_target_tree=SOURCE_TREE)
            self.admissions[oslabel] = a
            self.permits[oslabel] = issue_v2_owner_permit(
                a, owner_key=HMAC, epoch=self.db.meta()["epoch"],
                admission_event_seq=frozen["seq"],
                admission_event_sha256=frozen["sha"],
                authenticated_source_sha=MAIN)
            r = f.report(oslabel)
            r["intent_sha256"] = a.intent.intent_sha256
            r["qualification_key"] = a.intent.qualification_key
            r["candidate_sha256"] = a.intent.after_sha256
            artifact, meta = bundle(a, r)
            self.provider[oslabel] = {
                "zip_bytes": artifact, "metadata": meta}

    def check(self, **kwargs):
        return verify_v2_development_custody(
            self.db, kwargs.get("admissions", self.admissions),
            kwargs.get("permits", self.permits),
            kwargs.get("provider", self.provider), owner_key=HMAC)

    def test_two_platforms_are_source_bound_but_not_science(self):
        before = self.db.meta()
        report = self.check()
        self.assertTrue(report["both_platforms_development_qualified"])
        self.assertEqual(report["original_admission_event_seq"],
                         self.frozen["seq"])
        self.assertGreater(report["original_admission_event_seq"], 220)
        self.assertFalse(report["provider_origin_independently_attested"])
        self.assertFalse(report["original_v2_terminal_custody_written"])
        self.assertFalse(report["scientific_first_use_authorized"])
        self.assertEqual(report["accepted_ref_mutations"], 0)
        self.assertEqual(before, self.db.meta())

    def test_original_admission_reconstructs_signature_and_event(self):
        p = authenticate_original_admission(
            self.db, self.admissions["ubuntu-latest"], owner_key=HMAC)
        self.assertEqual(p["event_sha256"], self.frozen["sha"])
        self.assertEqual(p["source_sha"], MAIN)
        self.assertEqual(p["ticket"], self.issue.ticket)

    def test_reject_consumed_history_even_with_valid_new_receipt(self):
        with mock.patch(
                "f139.nci04_g32_owner_custody.FIRST_NEW_EVENT", 10000):
            with self.assertRaisesRegex(
                    V2CustodyDenied, "HISTORICAL_NATIVE_REPLAY_DENIED"):
                self.check()

    def test_no_real_original_event_or_missing_dispatch_denied(self):
        row = self.db.conn.execute(
            "SELECT stage FROM tasks WHERE ticket=?",
            (self.issue.ticket,)).fetchone()
        self.assertEqual(row["stage"], "WAIT_PROVIDER")
        self.db.conn.execute(
            "UPDATE tasks SET stage='READY' WHERE ticket=?",
            (self.issue.ticket,))
        with self.assertRaises(ValueError):
            self.check()

    def test_old_v1_verified_terminal_not_v2_custody(self):
        self.db.conn.execute(
            "UPDATE tasks SET stage='VERIFIED',run_id=? WHERE ticket=?",
            (RUN, self.issue.ticket))
        with self.assertRaisesRegex(
                V2CustodyDenied, "EXACT_INFLIGHT_NATIVE_STATE_REQUIRED"):
            self.check()

    def test_wrong_provider_zip_hash_and_os_denied(self):
        x = {key: dict(value) for key, value in self.provider.items()}
        oslabel = "ubuntu-latest"
        x[oslabel]["metadata"] = dict(
            x[oslabel]["metadata"], digest="sha256:" + "0" * 64)
        with self.assertRaises(ValueError):
            self.check(provider=x)
        x[oslabel]["metadata"] = self.provider[oslabel]["metadata"]
        x[oslabel]["zip_bytes"] = b"invalid"
        with self.assertRaises(ValueError):
            self.check(provider=x)

    def test_cross_os_run_or_candidate_mismatch_denied(self):
        altered = dict(self.admissions)
        altered["windows-latest"] = replace(
            altered["windows-latest"], run_id=RUN + 1)
        with self.assertRaises(ValueError):
            self.check(admissions=altered)
        altered = dict(self.admissions)
        altered["windows-latest"] = altered["ubuntu-latest"]
        with self.assertRaisesRegex(
                V2CustodyDenied, "SIGNED_ADMISSION_OS_DRIFT"):
            self.check(admissions=altered)

    def test_owner_permit_wrong_epoch_or_HMAC_denied(self):
        altered = dict(self.permits)
        altered["ubuntu-latest"] = altered["ubuntu-latest"].replace(
            b'"hmac_sha256":"', b'"hmac_sha256":"' + b"0", 1)
        with self.assertRaises(ValueError):
            self.check(permits=altered)

    def test_negative_provider_report_retained_without_terminal(self):
        label = "windows-latest"
        f = V2ContractTests()
        f.setUp()
        r = f.report(label)
        a = self.admissions[label]
        r["intent_sha256"] = a.intent.intent_sha256
        r["qualification_key"] = a.intent.qualification_key
        r["candidate_sha256"] = a.intent.after_sha256
        r["candidate_behavior"][0]["outcome"] = "TEST_FAILURE"
        r["candidate_behavior"][0]["returncode"] = 1
        r["candidate_behavior"] = r["candidate_behavior"][:1]
        r["candidate_compile"] = None
        r["qualification_complete"] = False
        zipped, meta = bundle(a, r)
        originals = dict(self.provider)
        originals[label] = {"zip_bytes": zipped, "metadata": meta}
        before = self.db.meta()
        report = self.check(provider=originals)
        self.assertFalse(report["both_platforms_development_qualified"])
        self.assertEqual(report["disposition"],
                         "V2_DEVELOPMENT_NEGATIVE_RETAINED")
        self.assertFalse(report["original_v2_terminal_custody_written"])
        self.assertEqual(before, self.db.meta())


if __name__ == "__main__":
    unittest.main()
