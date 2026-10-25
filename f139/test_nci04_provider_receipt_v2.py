"""G14 V2 provider custody integrity and fail-closed version tests."""
import copy
import io
import json
import unittest
import zipfile

from f139.nci04_native_contract import Candidate, canonical, digest
from f139.nci04_signed_native import NativeAdmission
from f139.nci04_worker_v2 import (
    SOURCE_SHA, SOURCE_TREE, REPORT_SCHEMA, RECEIPT_SCHEMA,
    EXPECTED_MODULES, FROZEN_COUNTS, COMPILE, supported_modules,
    unit_argv, receipt_v2,
)
from f139.nci04_provider_receipt_v2 import (
    V2ProviderDenied, verify_v2_provider_zip,
)


def positive_fixture():
    c=Candidate("a"*64, "b"*64, SOURCE_SHA, SOURCE_TREE,
                "yggdrasil/public_causal_cells.py", "c"*64, "d"*64,
                b"def x(): return 1\n","Yggdrasil")
    signed=NativeAdmission(
        "f139-nci04-i907-eeeeeeeeeeee-aaaaaaaa","Yggdrasil","e"*40,
        123,"ubuntu-latest",907,6019876053,c,"f"*64)
    def result(cmd,n=None,status="PASS"):
        return {"argv":list(cmd),"outcome":status,
                "returncode":0 if status=="PASS" else 1,
                "test_count":n,"output_sha256":digest(b"original test output"),
                "output_bytes":20,"elapsed_ms":2}
    modules,excluded=supported_modules("ubuntu-latest")
    report={
        "schema":REPORT_SCHEMA,"intent_sha256":c.intent_sha256,
        "qualification_key":c.qualification_key,
        "target_commit":SOURCE_SHA,"target_tree_sha":SOURCE_TREE,
        "candidate_path":c.path,"candidate_sha256":c.after_sha256,
        "os":"ubuntu-latest","complete_git_ancestry":True,
        "original_tracked_test_modules":sorted(EXPECTED_MODULES),
        "pristine_source_atlas":result(unit_argv("test_code_atlas.py"),4),
        "supported_behavior_modules":list(modules),
        "explicit_unsupported_modules":list(excluded),
        "candidate_behavior":[result(unit_argv(x),FROZEN_COUNTS[x]) for x in modules],
        "candidate_compile":result(COMPILE),
        "qualification_complete":True,"development_only":True,
        "scientific_first_use":False,"protected_holdouts_accessed":0,
        "accepted_ref_mutations":0,"paid_model_calls":0}
    return signed,report


def bundle(signed,report,receipt=None,*,extra=None):
    receipt=receipt if receipt is not None else receipt_v2(signed,report)
    data=canonical(receipt)
    contents={
        "f139-v2-receipt.json":data,
        "f139-v2-receipt.sha256":(digest(data)+"  f139-v2-receipt.json\n").encode(),
        "f139-v2-native-report.json":canonical(report)}
    if extra is not None:
        contents["extra.txt"]=extra
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as zipout:
        for name,blob in contents.items():
            zipout.writestr(name,blob)
    raw=out.getvalue()
    meta={"digest":"sha256:"+digest(raw),"size_in_bytes":len(raw),
          "run_id":signed.run_id,"runner_os":signed.runner_os,
          "source_sha":signed.source_sha}
    return raw,meta


class V2ProviderCustodyTests(unittest.TestCase):
    def test_version2_positive_requires_existing_signed_admission(self):
        signed,report=positive_fixture()
        data,meta=bundle(signed,report)
        result=verify_v2_provider_zip(data,meta,signed)
        self.assertTrue(result["qualified"])
        self.assertEqual(result["receipt"]["schema"],RECEIPT_SCHEMA)

    def test_negative_report_retained_but_never_promoted(self):
        signed,report=positive_fixture()
        report["candidate_behavior"][0]["outcome"]="TEST_FAILURE"
        report["candidate_behavior"][0]["returncode"]=1
        report["candidate_behavior"]=report["candidate_behavior"][:1]
        report["candidate_compile"]=None
        report["qualification_complete"]=False
        data,meta=bundle(signed,report)
        self.assertFalse(
            verify_v2_provider_zip(data,meta,signed,
                                   require_qualified=False)["qualified"])
        with self.assertRaisesRegex(V2ProviderDenied,
                                    "INCOMPLETE_NEGATIVE_CANNOT_BE_PROMOTED"):
            verify_v2_provider_zip(data,meta,signed)

    def test_v1_replay_or_receipt_shape_cannot_pass_v2(self):
        signed,report=positive_fixture()
        receipt=receipt_v2(signed,report)
        receipt["schema"]="forge.f139.nci04.native-execution-receipt.v1"
        raw,meta=bundle(signed,report,receipt)
        with self.assertRaisesRegex(V2ProviderDenied,
                                    "VERSION_OR_AUTHORITY_MISMATCH"):
            verify_v2_provider_zip(raw,meta,signed)

    def test_digest_member_and_os_tampering_rejected(self):
        signed,report=positive_fixture()
        raw,meta=bundle(signed,report)
        altered=dict(meta,digest="sha256:"+"0"*64)
        with self.assertRaisesRegex(V2ProviderDenied,"PROVIDER_SIGNED_IDENTITY_MISMATCH"):
            verify_v2_provider_zip(raw,altered,signed)
        altered=dict(meta,runner_os="windows-latest")
        with self.assertRaisesRegex(V2ProviderDenied,"PROVIDER_SIGNED_IDENTITY_MISMATCH"):
            verify_v2_provider_zip(raw,altered,signed)
        data,extra_meta=bundle(signed,report,extra=b"not permitted")
        with self.assertRaisesRegex(V2ProviderDenied,"PROVIDER_MEMBER_SET_INVALID"):
            verify_v2_provider_zip(data,extra_meta,signed)

    def test_forged_success_cannot_override_failed_report(self):
        signed,report=positive_fixture()
        receipt=receipt_v2(signed,report)
        report["candidate_behavior"][0]["outcome"]="TEST_FAILURE"
        report["candidate_behavior"][0]["returncode"]=1
        report["candidate_behavior"]=report["candidate_behavior"][:1]
        report["candidate_compile"]=None
        report["qualification_complete"]=False
        raw,meta=bundle(signed,report,receipt)
        with self.assertRaisesRegex(V2ProviderDenied,"SIGNED_RECEIPT_OR_RESULT_MISMATCH"):
            verify_v2_provider_zip(raw,meta,signed,require_qualified=False)

    def test_wrong_admission_ticket_source_and_run_rejected(self):
        from dataclasses import replace
        signed,report=positive_fixture()
        raw,meta=bundle(signed,report)
        for altered in (
                replace(signed,ticket="untrusted"),
                replace(signed,run_id=99999),
                replace(signed,source_sha="0"*40),
                replace(signed,authorization_sha256="")):
            with self.subTest(replaced=altered):
                with self.assertRaises((V2ProviderDenied,ValueError)):
                    verify_v2_provider_zip(raw,meta,altered)

    def test_not_new_signer_or_scientific_authority(self):
        signed,report=positive_fixture()
        receipt=receipt_v2(signed,report)
        self.assertEqual(receipt["original_signed_admission_sha256"],"f"*64)
        self.assertTrue(receipt["development_only"])
        self.assertFalse(receipt["scientific_first_use_authorized"])


if __name__=="__main__":
    unittest.main()
