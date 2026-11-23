"""A6 native source-bound provider ZIP receipt positive/negative custody tests."""
import io
import json
import unittest
import zipfile

from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_issue import inspect_owner_issue, make_signed_dispatch_inputs
from f139.nci04_provider_receipt import native_receipt_from_zip, NativeReceiptDenied
from f139.nci04_signed_native import admit_native_intent, receipt_from_report
from test_nci04_owner_issue import issue as make_issue, MAIN, TARGET, TREE, HMAC
from test_nci04_signed_native import report as make_report


def bundle(negative=False):
    issue = inspect_owner_issue(make_issue(), protected_main=MAIN,
                                authenticated_target_commit=TARGET,
                                authenticated_target_tree=TREE)
    rid=39510000000
    oslabel="ubuntu-latest"
    signed=make_signed_dispatch_inputs(issue,owner_hmac_key=HMAC,epoch=1)
    inp={
        "key":HMAC, "ticket":issue.ticket, "lane":issue.lane,
        "source_sha":MAIN,"epoch":"1","signature":signed["signature"],
        "repository":"spoonman136668-ai/FORGE",
        "ref":"refs/heads/main","event":"workflow_dispatch",
        "head_sha":MAIN,"run_attempt":"1", "run_id":str(rid),
        "os":oslabel,
    }
    accepted=admit_native_intent(
        inp,issue.intent_raw,native_signature=signed["native_signature"],
        issue_number=str(issue.number),issue_id=str(issue.issue_id),
        issue_body_sha256=issue.issue_body_sha256,
        authenticated_main_sha=MAIN,authenticated_target_commit=TARGET,
        authenticated_target_tree=TREE)
    report=make_report(accepted,fail=negative)
    receipt=receipt_from_report(accepted,report)
    raw_receipt=canonical(receipt)
    return issue,rid,oslabel,report,receipt,raw_receipt


def zipper(receipt_raw, report):
    zipbytes=io.BytesIO()
    entries={
        "f139-receipt.json":receipt_raw,
        "f139-receipt.sha256":(digest(receipt_raw)+
                               "  f139-receipt.json\n").encode(),
        "f139-native-report.json":canonical(report),
    }
    with zipfile.ZipFile(zipbytes,"w",zipfile.ZIP_DEFLATED) as archive:
        for name, blob in entries.items():
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
            archive.writestr(info,blob,compress_type=zipfile.ZIP_DEFLATED)
    return zipbytes.getvalue()


def verify(raw, issue, rid, oslabel, **changes):
    task={"ticket":issue.ticket,"lane":issue.lane,"source_sha":issue.source_sha}
    meta={"digest":"sha256:"+digest(raw),"size_in_bytes":len(raw)}
    return native_receipt_from_zip(raw,meta,task,rid,oslabel,1,issue,
                                   owner_hmac_key=HMAC,**changes)


class ProviderReceiptTests(unittest.TestCase):
    def test_original_source_receipt_matches_signed_owner(self):
        issue,rid,oslabel,report,receipt,body=bundle()
        raw=zipper(body,report)
        self.assertEqual(verify(raw,issue,rid,oslabel),receipt)
        self.assertTrue(receipt["native_qualified"])
        self.assertFalse(receipt["local_custody_verified"])
        self.assertFalse(receipt["controller_unattended_verified"])

    def test_provider_zip_byte_corruption_blocks_reconciliation(self):
        issue,rid,oslabel,report,receipt,body=bundle()
        raw=zipper(body,report)
        task={"ticket":issue.ticket,"lane":issue.lane,"source_sha":issue.source_sha}
        metadata={"digest":"sha256:"+digest(raw),"size_in_bytes":len(raw)}
        with self.assertRaisesRegex(NativeReceiptDenied,"PROVIDER_ZIP_IDENTITY"):
            native_receipt_from_zip(raw+b"tamper",metadata,task,rid,oslabel,1,
                                    issue,owner_hmac_key=HMAC)

    def test_negative_native_full_regression_is_not_verified(self):
        issue,rid,oslabel,report,receipt,body=bundle(negative=True)
        with self.assertRaisesRegex(NativeReceiptDenied,"NATIVE_FULL_REGRESSION_INCOMPLETE"):
            verify(zipper(body,report),issue,rid,oslabel)

    def test_different_git_target_or_issue_not_reused(self):
        issue,rid,oslabel,report,receipt,body=bundle()
        with self.assertRaises(Exception):
            verify(zipper(body,report),issue,rid+1,oslabel)
        with self.assertRaises(Exception):
            verify(zipper(body,report),issue,rid,"windows-latest")

    def test_false_pass_receipt_cannot_override_failed_native_evidence(self):
        issue,rid,oslabel,report,receipt,body=bundle(negative=True)
        receipt["native_qualified"]=True
        forged=canonical(receipt)
        with self.assertRaisesRegex(NativeReceiptDenied,"NATIVE_RECEIPT_OR_RESULT_DRIFT"):
            verify(zipper(forged,report),issue,rid,oslabel)

    def test_no_added_member_or_missing_report(self):
        issue,rid,oslabel,report,receipt,body=bundle()
        valid=zipper(body,report)
        tampered=io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(valid)) as inn, zipfile.ZipFile(tampered,"w") as out:
            for name in inn.namelist():out.writestr(name,inn.read(name))
            out.writestr("shadow.txt",b"not allowed")
        with self.assertRaisesRegex(NativeReceiptDenied,"NATIVE_ARTIFACT_MEMBERS"):
            verify(tampered.getvalue(),issue,rid,oslabel)


if __name__ == "__main__":
    unittest.main()
