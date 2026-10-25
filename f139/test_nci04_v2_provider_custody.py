"""G14 V2 immutable provider ZIP custody and downgrade/falsification tests."""
import io
import json
import unittest
import zipfile
from dataclasses import replace

from f139.nci04_native_contract import NativeContractError, canonical, digest
from f139.nci04_signed_native import NativeAdmission
from f139.nci04_worker_v2 import receipt_v2
from f139.nci04_v2_provider_custody import inspect_provider_v2_zip
from f139.test_nci04_worker_v2 import V2ContractTests


class V2ProviderCustodyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = V2ContractTests()
        self.fixture.setUp()
        self.admission = NativeAdmission(
            "f139-nci04-i907-eeeeeeeeeeee-aaaaaaaa",
            "Yggdrasil","e"*40,123,"ubuntu-latest",
            907,6019876053,self.fixture.c,"f"*64)

    def zip(self, *, report=None, receipt=None, names=None):
        if report is None:
            report = self.fixture.report()
        if receipt is None:
            receipt = receipt_v2(self.admission, report)
        report_bytes = canonical(report)
        receipt_bytes = canonical(receipt)
        parts = {
            "f139-receipt.json": receipt_bytes,
            "f139-receipt.sha256": (
                digest(receipt_bytes) + "  f139-receipt.json\n").encode(),
            "f139-native-report.json": report_bytes,
        }
        stream = io.BytesIO()
        with zipfile.ZipFile(stream,"w",compression=zipfile.ZIP_DEFLATED) as z:
            for name in (names or list(parts)):
                z.writestr(name,parts.get(name,b"bad"))
        return stream.getvalue()

    def inspect(self, raw, **kw):
        args = {
            "admission": self.admission,
            "provider_sha256": "sha256:" + digest(raw),
            "provider_size": len(raw),
            "provider_run_id": 123,
            "provider_head_sha": "e"*40,
            "artifact_name": "forge-f139-native-receipt-ubuntu-latest",
        }
        args.update(kw)
        return inspect_provider_v2_zip(raw,**args)

    def test_authentic_positive_provider_zip(self):
        raw=self.zip()
        record=self.inspect(raw)
        self.assertTrue(record["native_qualified"])
        self.assertFalse(record["owner_admission"])
        self.assertFalse(record["scientific_first_use"])

    def test_proper_negative_is_preserved_as_negative(self):
        report=self.fixture.report()
        report["candidate_behavior"][0]["outcome"]="TEST_FAILURE"
        report["candidate_behavior"][0]["returncode"]=1
        report["candidate_behavior"]=report["candidate_behavior"][:1]
        report["candidate_compile"]=None
        report["qualification_complete"]=False
        doc=self.inspect(self.zip(report=report))
        self.assertFalse(doc["native_qualified"])

    def test_run_source_os_and_digest_are_authenticated_inputs(self):
        raw=self.zip()
        for patch in (
            {"provider_run_id":124},
            {"provider_head_sha":"0"*40},
            {"artifact_name":"forge-f139-native-receipt-windows-latest"},
            {"provider_sha256":"sha256:"+"0"*64},
            {"provider_size":len(raw)+1},
            {"admission":replace(self.admission,authorization_sha256="0"*64)},
        ):
            with self.subTest(patch=patch):
                with self.assertRaises(NativeContractError):
                    self.inspect(raw,**patch)

    def test_v1_schema_downgrade_and_forged_success_denied(self):
        report=self.fixture.report()
        report["schema"]="forge.f139.nci04.native-development-diagnostic.v1"
        raw=self.zip(report=report,receipt={
            "schema":"forge.f139.nci04.native-execution-receipt.v1"})
        with self.assertRaises(NativeContractError):
            self.inspect(raw)
        report=self.fixture.report()
        report["candidate_behavior"][0]["outcome"]="TEST_FAILURE"
        report["candidate_behavior"][0]["returncode"]=1
        report["candidate_behavior"]=report["candidate_behavior"][:1]
        report["candidate_compile"]=None
        report["qualification_complete"]=False
        fake=receipt_v2(self.admission,report)
        fake["native_qualified"]=True
        with self.assertRaises(NativeContractError):
            self.inspect(self.zip(report=report,receipt=fake))

    def test_duplicate_missing_and_extra_zip_members_denied(self):
        good=self.zip()
        for names in (
            ["f139-receipt.json","f139-receipt.json",
             "f139-native-report.json"],
            ["f139-receipt.json","f139-receipt.sha256"],
            ["f139-receipt.json","f139-receipt.sha256",
             "f139-native-report.json","evil.txt"],
        ):
            with self.subTest(names=names):
                with self.assertRaises(NativeContractError):
                    self.inspect(self.zip(names=names))
        self.assertTrue(self.inspect(good)["native_qualified"])


if __name__ == "__main__":
    unittest.main()
