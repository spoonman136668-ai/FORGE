"""A8A source-only original negative receipt validation; no owner DB or network."""
from __future__ import annotations
from copy import deepcopy
import unittest

from f139.nci04_native_contract import canonical, digest
from f139.nci04_negative_custody import (
    verified_negative_provider_original, NegativeCustodyDenied)
from f139.nci04_provider_receipt import (
    native_negative_from_zip, native_receipt_from_zip, NativeReceiptDenied)
from test_nci04_provider_receipt import bundle, zipper
from test_nci04_owner_issue import HMAC


class NegativeCustodyTests(unittest.TestCase):
    def setUp(self):
        issue, rid, oslabel, report, receipt, body = bundle(negative=True)
        self.issue, self.rid, self.receipt = issue, rid, receipt
        self.raw = zipper(body, report)
        self.task = {
            "ticket":issue.ticket, "lane":issue.lane,
            "source_sha":issue.source_sha,
        }
        self.run = {
            "id":rid, "run_attempt":1, "event":"workflow_dispatch",
            "head_sha":issue.source_sha, "head_branch":"main",
            "status":"completed", "conclusion":"failure",
            "repository":{"full_name":"spoonman136668-ai/FORGE"},
        }
        self.jobs = [
            {"id":rid+10, "run_id":rid,"name":"native-authorize",
             "status":"completed","conclusion":"success"},
            {"id":rid+15,"run_id":rid,"name":"execute",
             "status":"completed","conclusion":"skipped"},
            {"id":rid+11, "run_id":rid,"name":"native-execute (ubuntu-latest)",
             "status":"completed","conclusion":"failure"},
            {"id":rid+12, "run_id":rid,"name":"native-execute (windows-latest)",
             "status":"completed","conclusion":"failure"},
        ]
        self.artifact = {
            "id":rid+13,
            "name":"forge-f139-native-receipt-ubuntu-latest",
            "digest":"sha256:"+digest(self.raw),
            "size_in_bytes":len(self.raw), "expired":False,
            "workflow_run":{"id":rid,"head_sha":issue.source_sha},
        }

    def certify(self, **replacements):
        params = {
            "run":self.run,"jobs":self.jobs,"artifact":self.artifact,
            "archive":self.raw,"task":self.task,"issue":self.issue,
            "owner_hmac_key":HMAC,"epoch":1,
        }
        params.update(replacements)
        return verified_negative_provider_original(**params)

    def test_negative_original_is_authenticated_but_never_verified(self):
        result = self.certify()
        self.assertEqual(result["run_id"],self.rid)
        self.assertEqual(result["provider_artifact_sha256"],digest(self.raw))
        self.assertEqual(result["native_report_sha256"],
                         self.receipt["native_report_sha256"])
        self.assertIs(result["native_qualified"],False)
        self.assertIs(result["provider_negative_authenticated"],True)
        self.assertIs(result["original_owner_durable_custody"],False)
        self.assertIs(result["successor_source_transition_authorized"],False)
        self.assertEqual(result["original_sqlite_mutations"],0)
        self.assertIs(result["scientific_first_use"],False)
        self.assertEqual(native_negative_from_zip(
            self.raw,self.artifact,self.task,self.rid,"ubuntu-latest",1,
            self.issue,owner_hmac_key=HMAC),self.receipt)
        with self.assertRaisesRegex(NativeReceiptDenied,
                                    "NATIVE_FULL_REGRESSION_INCOMPLETE"):
            native_receipt_from_zip(
                self.raw,self.artifact,self.task,self.rid,"ubuntu-latest",1,
                self.issue,owner_hmac_key=HMAC)

    def test_original_run_is_exactly_one_failed_attempt(self):
        for key,value in (
            ("run_attempt",2),("conclusion","success"),
            ("status","in_progress"),("event","schedule"),
            ("head_sha","9"*40),("head_branch","other"),
            ("repository",{"full_name":"untrusted/other"}),
        ):
            with self.subTest(key=key),self.assertRaisesRegex(
                    NegativeCustodyDenied,"RUN_SOURCE_OR_ATTEMPT_DRIFT"):
                self.certify(run={**self.run,key:value})

    def test_both_os_and_authorizer_jobs_must_match_real_run(self):
        variants = [
            self.jobs[:2],
            [j for j in self.jobs if j["name"]!="execute"],
            [{**self.jobs[0],"conclusion":"failure"},*self.jobs[1:]],
            [self.jobs[0],{**self.jobs[1],"conclusion":"success"},self.jobs[2]],
            [self.jobs[0],{**self.jobs[1],"status":"in_progress"},self.jobs[2]],
            [self.jobs[0],{**self.jobs[1],"run_id":999},self.jobs[2]],
            [self.jobs[0],self.jobs[1],{**self.jobs[2],"name":self.jobs[1]["name"]}],
        ]
        for jobs in variants:
            with self.subTest(jobs=jobs),self.assertRaises(NegativeCustodyDenied):
                self.certify(jobs=jobs)

    def test_missing_false_or_forged_artifact_does_not_certify(self):
        for key,value in (
            ("digest","sha256:"+"0"*64),
            ("size_in_bytes",len(self.raw)+1),
            ("expired",True),
            ("name","other"),
            ("workflow_run",{"id":self.rid+1,"head_sha":self.issue.source_sha}),
        ):
            with self.subTest(key=key),self.assertRaises((NativeReceiptDenied,
                                                           NegativeCustodyDenied)):
                self.certify(artifact={**self.artifact,key:value})
        with self.assertRaises((NativeReceiptDenied,NegativeCustodyDenied)):
            self.certify(archive=self.raw+b"tamper")

    def test_reject_false_pass_even_with_rewritten_sha(self):
        issue,rid,_,report,receipt,body=bundle(negative=True)
        receipt["native_qualified"]=True
        forged=zipper(canonical(receipt),report)
        art={**self.artifact,"digest":"sha256:"+digest(forged),
             "size_in_bytes":len(forged)}
        with self.assertRaisesRegex(NativeReceiptDenied,
                                    "NATIVE_RECEIPT_OR_RESULT_DRIFT"):
            self.certify(artifact=art,archive=forged)

    def test_positive_native_receipt_cannot_be_labeled_negative(self):
        issue,rid,_,report,receipt,body=bundle(negative=False)
        positive=zipper(body,report)
        art={**self.artifact,"digest":"sha256:"+digest(positive),
             "size_in_bytes":len(positive)}
        with self.assertRaisesRegex(NativeReceiptDenied,
                                    "NATIVE_FULL_REGRESSION_INCOMPLETE"):
            self.certify(artifact=art,archive=positive)

    def test_wrong_epoch_or_owner_secret_rejected(self):
        for changes in ({"epoch":2},{"owner_hmac_key":"bad-secret"*8},
                        {"task":{**self.task,"ticket":"untrusted"}}):
            with self.subTest(changes=changes),self.assertRaises(Exception):
                self.certify(**changes)


if __name__ == "__main__":
    unittest.main()
