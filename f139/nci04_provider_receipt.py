"""F139 NCI04-A6 original-provider receipt validator.

Deterministic receipt verification from signed owner issue and both original
GitHub Actions provider ZIPs, never from an attacker-authored 'PASS' string.
No source execution, network call, SQLite mutation or science authority.
"""
from __future__ import annotations

import base64
import io
import json
import re
import zipfile

from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_issue import NativeIssue, make_signed_dispatch_inputs
from f139.nci04_signed_native import (
    admit_native_intent, receipt_from_report, Untrusted)

MEMBERS = frozenset({
    "f139-receipt.json", "f139-receipt.sha256",
    "f139-native-report.json",
})
MAX_REPORT = 64000
MAX_ZIP = 2_000_000


class NativeReceiptDenied(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise NativeReceiptDenied("F139_NCI04_A6_" + reason)


def native_receipt_from_zip(raw: bytes, meta: dict, task: dict,
                            run_id: int, oslabel: str, epoch: int,
                            issue: NativeIssue, *, owner_hmac_key: str,
                            expect_qualified: bool = True):
    require(isinstance(raw, bytes) and 0<len(raw)<MAX_ZIP
            and isinstance(meta, dict)
            and meta.get("digest")=="sha256:"+digest(raw)
            and meta.get("size_in_bytes")==len(raw),
            "PROVIDER_ZIP_IDENTITY")
    require(isinstance(issue,NativeIssue) and isinstance(task,dict)
            and task["ticket"]==issue.ticket and task["lane"]==issue.lane
            and task["source_sha"]==issue.source_sha
            and oslabel in ("ubuntu-latest","windows-latest")
            and type(run_id) is int and run_id>0
            and type(epoch) is int and epoch>0,
            "NATIVE_TASK_IDENTITY")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names=archive.namelist()
            require(len(names)==len(MEMBERS) and set(names)==MEMBERS
                    and all(not x.is_dir() and x.file_size <= MAX_REPORT
                            and x.compress_size<=MAX_REPORT
                            for x in archive.infolist()),
                    "NATIVE_ARTIFACT_MEMBERS")
            receipt_raw=archive.read("f139-receipt.json")
            sha_raw=archive.read("f139-receipt.sha256")
            report_raw=archive.read("f139-native-report.json")
    except NativeReceiptDenied:
        raise
    except (OSError,ValueError,zipfile.BadZipFile,RuntimeError) as exc:
        raise NativeReceiptDenied("F139_NCI04_A6_NATIVE_ZIP_INVALID") from exc
    require(sha_raw==(digest(receipt_raw)+"  f139-receipt.json\n").encode(),
            "NATIVE_RECEIPT_SHA")
    try:
        receipt=json.loads(receipt_raw)
        report=json.loads(report_raw)
    except (ValueError,UnicodeDecodeError) as exc:
        raise NativeReceiptDenied("F139_NCI04_A6_RECEIPT_JSON_INVALID") from exc
    require(isinstance(receipt,dict) and isinstance(report,dict)
            and len(canonical(report))<=MAX_REPORT
            and len(canonical(receipt))<=8192,
            "NATIVE_REPORT_TOO_LARGE")
    expected_fields=make_signed_dispatch_inputs(
        issue, owner_hmac_key=owner_hmac_key, epoch=epoch)
    actual={
        "key":owner_hmac_key, "ticket":issue.ticket, "lane":issue.lane,
        "source_sha":issue.source_sha, "epoch":str(epoch),
        "signature":expected_fields["signature"],
        "repository":"spoonman136668-ai/FORGE",
        "ref":"refs/heads/main", "event":"workflow_dispatch",
        "head_sha":issue.source_sha, "run_attempt":"1",
        "run_id":str(run_id), "os":oslabel,
    }
    verified=admit_native_intent(
        actual, issue.intent_raw,
        native_signature=expected_fields["native_signature"],
        issue_number=str(issue.number), issue_id=str(issue.issue_id),
        issue_body_sha256=issue.issue_body_sha256,
        authenticated_main_sha=issue.source_sha,
        authenticated_target_commit=issue.candidate.target_commit,
        authenticated_target_tree=issue.candidate.target_tree_sha)
    expected=receipt_from_report(verified,report)
    # Same complete authenticated report/receipt, not a partial/malleable
    # subset. Receiver does not trust unchecked claimed 'native_qualified'.
    require(receipt==expected, "NATIVE_RECEIPT_OR_RESULT_DRIFT")
    # Existing positive callers still require PASS by default. This private
    # opt-in negative path exists ONLY to certify a failed provider original;
    # it never marks a failed task VERIFIED or authorizes a successor.
    require(type(expect_qualified) is bool and
            expected["native_qualified"] is expect_qualified,
            "NATIVE_FULL_REGRESSION_INCOMPLETE")
    return expected


def native_negative_from_zip(raw: bytes, meta: dict, task: dict,
                             run_id: int, oslabel: str, epoch: int,
                             issue: NativeIssue, *, owner_hmac_key: str):
    """Authenticate a signed FAILED original without promoting its status.

    Uses identical full intent/HMAC/receipt/ZIP byte verification as positive
    custody, but asserts native_qualified=False; never returns a PASS.
    """
    negative = native_receipt_from_zip(
        raw, meta, task, run_id, oslabel, epoch, issue,
        owner_hmac_key=owner_hmac_key, expect_qualified=False)
    require(negative["native_qualified"] is False, "FALSE_NEGATIVE")
    return negative
