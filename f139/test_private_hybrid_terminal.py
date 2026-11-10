"""Synthetic private-terminal ZIPs. No project execution or live HMAC key."""
import io
import json
import unittest
import zipfile

from f139.nci04_native_contract import canonical, digest
from f139.nci04_signed_native import admit_native_intent, receipt_from_report
from f139.private_hybrid_owner_binding import verify_credentialed_owner_binding
from f139.private_hybrid_terminal import (
    PrivateTerminalDenied, TRANSPORT, verify_private_provider_terminal,
)
from f139 import test_private_hybrid_owner_binding as source
from f139 import test_nci04_signed_native as base

REPO = "spoonman136668-ai/TTT-Hybrid-Lab"


def pack(values):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as f:
        for name in sorted(values):
            f.writestr(name, values[name])
    return buf.getvalue()


def example(*, fail=False):
    ref, payload, provider, inp, sig = source.fixture()
    admission = admit_native_intent(
        inp, payload, native_signature=sig,
        issue_number=source.ISSUE, issue_id=source.ISSUE_ID,
        issue_body_sha256=source.BODY, authenticated_main_sha=source.OWNER,
        authenticated_target_commit=source.COMMIT,
        authenticated_target_tree=source.TREE)
    bound = verify_credentialed_owner_binding(
        canonical(ref), payload, original_ticket_inputs=inp,
        native_signature=sig, issue_number=source.ISSUE,
        issue_id=source.ISSUE_ID, issue_body_sha256=source.BODY,
        owner_source_sha=source.OWNER, private_commit=source.COMMIT,
        private_tree=source.TREE, authenticated_repository_metadata=source.MD,
        provider_file=provider)
    report = base.report(admission, fail=fail)
    receipt = receipt_from_report(admission, report)
    rec_raw, rep_raw = canonical(receipt), canonical(report)
    transport = {
        "schema": TRANSPORT, "repository": REPO,
        "private_run_id": 42830000001, "private_job_id": 129900000001,
        "private_artifact_id": 123000001,
        "original_owner_run_id": admission.run_id,
        "source_sha": admission.source_sha,
        "private_payload_sha256": admission.intent.intent_sha256,
        "private_target_commit": admission.intent.target_commit,
        "private_target_tree": admission.intent.target_tree_sha,
        "private_storage_commit": ref["private_payload_commit"],
        "private_storage_tree": ref["private_payload_tree"],
        "native_receipt_sha256": digest(rec_raw),
        "native_report_sha256": digest(rep_raw),
        "scientific_first_use": False, "owner_ledger_verified": False,
        "private_worker_signed_verified": False,
    }
    files = {
        "f139-native-receipt.json": rec_raw,
        "f139-native-receipt.sha256":
            (digest(rec_raw) + "  f139-native-receipt.json\n").encode(),
        "f139-native-report.json": rep_raw,
        "f139-private-provider-binding.json": canonical(transport),
    }
    raw = pack(files)
    meta = {
        "repository": REPO, "private": True,
        "private_run_id": transport["private_run_id"],
        "private_job_id": transport["private_job_id"],
        "private_artifact_id": transport["private_artifact_id"],
        "original_owner_run_id": admission.run_id,
        "source_sha": admission.source_sha,
        "private_commit": ref["private_payload_commit"],
        "private_tree": ref["private_payload_tree"],
        "digest": "sha256:" + digest(raw), "size_in_bytes": len(raw),
    }
    return raw, files, meta, admission, bound, ref


def inspect(raw, meta, admission, bound, ref):
    return verify_private_provider_terminal(raw, meta, admission, bound,
                                            verified_private_reference=ref)


class PrivateTerminalSyntheticTests(unittest.TestCase):
    def test_recomputed_report_positive_does_not_claim_real_worker_execution(self):
        raw, _, meta, admission, bound, ref = example()
        result = inspect(raw, meta, admission, bound, ref)
        self.assertTrue(result["provider_zip_structurally_verified"])
        self.assertTrue(result["reported_native_qualified"])
        for field in ("original_owner_live_issuance_verified",
                      "independent_private_worker_execution_verified",
                      "durable_owner_ledger_settled", "scientific_first_use",
                      "candidate_accepted"):
            self.assertFalse(result[field])
        for value in ("after_base64", "synthetic", "private_payload_path",
                      "def ", source.KEY):
            self.assertNotIn(value, json.dumps(result))

    def test_negative_terminal_is_retained_not_promoted(self):
        raw, _, meta, admission, bound, ref = example(fail=True)
        result = inspect(raw, meta, admission, bound, ref)
        self.assertFalse(result["reported_native_qualified"])
        self.assertFalse(result["candidate_accepted"])

    def test_provider_metadata_tamper_fails(self):
        raw, _, meta, admission, bound, ref = example()
        mutations = (
            {"private": False}, {"private": None},
            {"repository": "spoonman136668-ai/FORGE"},
            {"private_run_id": meta["private_run_id"]+1},
            {"private_job_id": meta["private_job_id"]+1},
            {"private_artifact_id": meta["private_artifact_id"]+1},
            {"original_owner_run_id": meta["original_owner_run_id"]+1},
            {"source_sha": "f"*40}, {"private_commit": "f"*40},
            {"private_tree": "f"*40}, {"digest": "sha256:"+"0"*64},
            {"size_in_bytes": meta["size_in_bytes"]+1},
            {"extra": "forged"},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(PrivateTerminalDenied):
                inspect(raw, {**meta, **mutation}, admission, bound, ref)

    def test_signed_credentialed_binding_is_not_a_bare_claim(self):
        raw, _, meta, admission, bound, ref = example()
        for change in ({"ticket": "forged"}, {"provided_owner_hmac_pair_matched": False},
                       {"authorization_binding_sha256": "0"*64},
                       {"private_payload_sha256": "0"*64},
                       {"original_owner_live_issue_verified": True},
                       {"private_worker_executed": True}, {"schema": "untrusted"}):
            with self.subTest(change=change), self.assertRaises(PrivateTerminalDenied):
                inspect(raw, meta, admission, {**bound, **change}, ref)

    def test_private_ref_target_and_storage_mismatch(self):
        raw, _, meta, admission, bound, ref = example()
        for change in ({"private_target_commit": "0"*40},
                       {"private_target_tree": "0"*40},
                       {"private_payload_commit": "0"*40},
                       {"private_payload_tree": "0"*40},
                       {"private_payload_sha256": "0"*64},
                       {"lane": "Wingless"}):
            with self.subTest(change=change), self.assertRaises(PrivateTerminalDenied):
                inspect(raw, meta, admission, bound, {**ref, **change})

    def test_transport_tamper_even_with_new_valid_zip_digest(self):
        raw, files, meta, admission, bound, ref = example()
        t = json.loads(files["f139-private-provider-binding.json"])
        for change in ({"native_report_sha256": "0"*64},
                       {"native_receipt_sha256": "0"*64},
                       {"private_run_id": t["private_run_id"]+1},
                       {"private_job_id": t["private_job_id"]+1},
                       {"private_storage_commit": "0"*40},
                       {"private_target_commit": "0"*40},
                       {"owner_ledger_verified": True},
                       {"private_worker_signed_verified": True},
                       {"scientific_first_use": True},
                       {"extra": "unauthorized"}):
            altered = dict(files)
            altered["f139-private-provider-binding.json"] = canonical({**t, **change})
            bad = pack(altered)
            with self.subTest(change=change), self.assertRaises(PrivateTerminalDenied):
                inspect(bad, {**meta, "digest": "sha256:"+digest(bad),
                              "size_in_bytes": len(bad)}, admission, bound, ref)

    def test_native_receipt_or_report_rejects_forged_success(self):
        raw, files, meta, admission, bound, ref = example(fail=True)
        for target in ("f139-native-receipt.json", "f139-native-report.json"):
            altered = dict(files)
            obj = json.loads(altered[target])
            if target.endswith("receipt.json"):
                obj["native_qualified"] = True
            else:
                obj["qualification_complete"] = True
            altered[target] = canonical(obj)
            if target.endswith("receipt.json"):
                altered["f139-native-receipt.sha256"] = (
                    digest(altered[target]) + "  f139-native-receipt.json\n").encode()
            t = json.loads(altered["f139-private-provider-binding.json"])
            t["native_receipt_sha256"] = digest(altered["f139-native-receipt.json"])
            t["native_report_sha256"] = digest(altered["f139-native-report.json"])
            altered["f139-private-provider-binding.json"] = canonical(t)
            bad = pack(altered)
            with self.subTest(target=target), self.assertRaises(ValueError):
                inspect(bad, {**meta,"digest":"sha256:"+digest(bad),
                              "size_in_bytes":len(bad)}, admission, bound, ref)

    def test_zip_member_and_json_security(self):
        raw, files, meta, admission, bound, ref = example()
        for bad_files in (
            {**files, "extra.json": b"{}"},
            {k:v for k,v in files.items() if k!="f139-native-report.json"},
            {**files, "f139-native-report.json": b"{}"},
            {**files,"f139-native-receipt.sha256": b"0"*64},
            {**files,"f139-private-provider-binding.json":
                files["f139-private-provider-binding.json"] + b" "},
        ):
            bad = pack(bad_files)
            self.assertNotEqual(raw, bad)
            with self.assertRaises(ValueError):
                inspect(bad, {**meta,"digest":"sha256:"+digest(bad),
                              "size_in_bytes":len(bad)}, admission, bound, ref)
        with self.assertRaises(PrivateTerminalDenied):
            inspect(b"not ZIP", {**meta,"digest":"sha256:"+digest(b"not ZIP"),
                                 "size_in_bytes":7}, admission, bound, ref)


if __name__ == "__main__":
    unittest.main()
