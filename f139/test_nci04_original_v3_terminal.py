"""V3 original-owner consumer: fail closed on any missing provider identity."""
from __future__ import annotations
import copy
import io
import zipfile
import unittest

from f139.nci04_native_contract import Candidate, canonical, digest
from f139.nci04_signed_native import NativeAdmission
from f139.nci04_worker_v3 import (
    unit, COMMAND, BUILD, ATLAS, TARGET, CLOSED,
    SCHEMA as R_SCHEMA, receipt_v3)
from f139.nci04_original_v3_terminal import (
    inner_zip, V3TerminalDenied, MEMBERS,
    qualified_original_github_run)


class OriginalV3CustodyTests(unittest.TestCase):
    def setUp(self):
        candidate=Candidate(
            intent_sha256="a"*64,qualification_key="b"*64,
            target_commit="fc5d28a836f33caad3a576e0a6d4a1bf211cd857",
            target_tree_sha="4cab523b03f7316b2470eddb93c479ec9e8cbab4",
            path=TARGET,before_sha256="c"*64,after_sha256="d"*64,
            after_bytes=b"test-only",lane="Yggdrasil")
        self.admission=NativeAdmission(
            "f139-nci04-i1200-999999999999-aaaaaaaa","Yggdrasil",
            "9"*40,1234567890,"ubuntu-latest",1200,1200123,candidate,"e"*64)
        names=[ATLAS,"test_free_fanout_sidecar.py","test_native_cells.py",
               "test_portable_checkpoint.py","test_extra.py"]
        def row(cmd,status,count):
            return {"argv":list(cmd),"status":status,
                    "returncode":1 if status==CLOSED else 0,
                    "discovered_tests":count,
                    "child_peak_rss_bytes":52428800,
                    "child_cpu_ms":55,"resource_samples":4,
                    "resource_budget_verified":True,
                    "resource_accounting":"psutil-sampled-process-tree-v1"}
        self.report={
            "schema":R_SCHEMA,"os":"ubuntu-latest",
            "ticket_source_commit":candidate.target_commit,
            "target_tree_sha":candidate.target_tree_sha,
            "intent_sha256":candidate.intent_sha256,
            "qualification_key":candidate.qualification_key,
            "source_module_inventory":names,"source_split_pass":True,
            "baseline_full_pass":True,"all_candidate_modules_pass":True,
            "g29_modified_source_expected_negative":True,
            "resource_accounting":"psutil-sampled-process-tree-v1",
            "baseline_g29":row(unit(ATLAS),"PASS",4),
            "baseline_full":row(COMMAND+("-p","test_*.py","-v"),"PASS",54),
            "candidate_g29_negative":row(unit(ATLAS),CLOSED,4),
            "candidate_compile":row(BUILD,"PASS",None),
            "candidate_nonatlas":{
                name:row(unit(name),"PASS",5)
                for name in names if name!=ATLAS},
            "native_qualified":True,"child_cpu_rss_verified":True,
        }
        self.receipt=receipt_v3(self.admission,self.report)

    def zipbytes(self, report=None, receipt=None, extra=False):
        report=self.report if report is None else report
        receipt=self.receipt if receipt is None else receipt
        obj=io.BytesIO()
        with zipfile.ZipFile(obj,"w",compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("f139-v3-native-report.json",canonical(report))
            z.writestr("f139-v3-native-receipt.json",canonical(receipt))
            if extra: z.writestr("untrusted.txt",b"tampered")
        return obj.getvalue()

    def verify(self, data):
        meta={"size_in_bytes":len(data),"digest":"sha256:"+digest(data),
              "expired":False}
        return inner_zip(data,meta,self.admission)

    def test_positive_development_only_signed_report_and_two_exact_zip_members(self):
        blob=self.zipbytes()
        self.assertEqual(set(MEMBERS),
                         {"f139-v3-native-report.json",
                          "f139-v3-native-receipt.json"})
        result=self.verify(blob)
        self.assertEqual(len(result["receipt_sha256"]),64)

    def test_original_positive_cannot_be_simulated_from_negative_receipt(self):
        report=copy.deepcopy(self.report)
        report["native_qualified"]=False
        report["child_cpu_rss_verified"]=False
        receipt=dict(self.receipt,native_qualified=False)
        with self.assertRaises(V3TerminalDenied):
            self.verify(self.zipbytes(report,receipt))

    def test_wrong_signed_source_receipt_or_resource_denied(self):
        for change in (
            ("target_tree_sha","f"*40),
            ("intent_sha256","f"*64),
            ("resource_accounting","unverified"),
        ):
            report=copy.deepcopy(self.report)
            report[change[0]]=change[1]
            with self.subTest(field=change[0]),self.assertRaises(ValueError):
                self.verify(self.zipbytes(report))

    def test_missing_resource_test_and_forged_test_module_denied(self):
        changes=[
            lambda r:r["candidate_nonatlas"].pop("test_native_cells.py"),
            lambda r:r["candidate_nonatlas"]["test_native_cells.py"].update(child_cpu_ms=0),
            lambda r:r["candidate_g29_negative"].update(status="PASS"),
            lambda r:r["baseline_full"].update(discovered_tests=0),
        ]
        for i,change in enumerate(changes):
            report=copy.deepcopy(self.report)
            change(report)
            with self.subTest(i=i),self.assertRaises(ValueError):
                self.verify(self.zipbytes(report))

    def test_outer_provider_zip_digest_and_member_inventory_enforced(self):
        blob=self.zipbytes()
        with self.assertRaises(V3TerminalDenied):
            inner_zip(blob,{"size_in_bytes":len(blob),
                           "digest":"sha256:"+"0"*64,"expired":False},
                      self.admission)
        with self.assertRaises(V3TerminalDenied):
            self.verify(self.zipbytes(extra=True))

    def test_github_run_requires_authentic_controller_source(self):
        class FakeProvider:
            def get(self,path):
                if path.endswith("/jobs?per_page=100"):
                    return {"jobs":[],"total_count":0}
                return {"id":1000,"status":"completed","conclusion":"success",
                        "display_title":"F139 forged","name":"F139 forged",
                        "event":"workflow_dispatch"}
        with self.assertRaises(V3TerminalDenied):
            qualified_original_github_run(
                FakeProvider(),1000,self.admission.ticket,
                self.admission.source_sha,"2026-10-29T14:00:00Z",
                {"ubuntu-latest":self.admission})


if __name__=="__main__":
    unittest.main()
