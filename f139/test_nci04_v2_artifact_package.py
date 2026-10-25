"""G33 credential-free V2 worker to canonical G14 ZIP fixture round trips."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

from f139.nci04_native_contract import canonical, digest
from f139.nci04_provider_receipt_v2 import (
    V2ProviderDenied, MEMBERS, verify_v2_provider_zip,
)
from f139.nci04_signed_native import NativeAdmission
from f139.nci04_v2_artifact_package import (
    PACKAGE, INPUT_RECEIPT, INPUT_REPORT, V2PackagingDenied,
    package_v2_development_output,
)
from f139.nci04_worker_entry import execute_v2_development
from f139.test_nci04_worker_v2 import V2ContractTests


class G33V2ArtifactTests(unittest.TestCase):
    def setUp(self):
        v2 = V2ContractTests()
        v2.setUp()
        self.fixture = v2
        self.oslabel = "windows-latest" if os.name == "nt" else "ubuntu-latest"
        self.admission = NativeAdmission(
            "f139-nci04-i933-eeeeeeeeeeee-" + v2.c.intent_sha256[:8],
            "Yggdrasil", "e" * 40, 40200000001,
            self.oslabel, 933, 6010000333, v2.c, "f" * 64)
        t = tempfile.TemporaryDirectory(prefix="f139-g33-source-only-")
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        for name in ("original", "scratch", "out"):
            (self.root / name).mkdir()
        self.output = self.root / "out"

    def run_worker(self, report=None):
        report = (self.fixture.report(self.oslabel)
                  if report is None else report)
        with mock.patch("f139.nci04_worker_v2.run_v2",
                        return_value=report):
            return execute_v2_development(
                self.admission, self.root / "original",
                self.root / "scratch", self.output)

    def provider(self, *, require_qualified=True):
        raw = (self.output / PACKAGE).read_bytes()
        meta = {
            "digest": "sha256:" + digest(raw),
            "size_in_bytes": len(raw),
            "run_id": self.admission.run_id,
            "runner_os": self.admission.runner_os,
            "source_sha": self.admission.source_sha,
        }
        return verify_v2_provider_zip(
            raw, meta, self.admission,
            require_qualified=require_qualified)

    def test_live_dev_api_yields_exact_g14_zip_and_no_v1_receipt(self):
        (receipt, passed) = self.run_worker()
        self.assertTrue(passed)
        self.assertTrue(receipt["native_qualified"])
        self.assertEqual(
            {p.name for p in self.output.iterdir()},
            {INPUT_RECEIPT, INPUT_REPORT, PACKAGE})
        self.assertFalse((self.output / "f139-receipt.json").exists())
        with zipfile.ZipFile(self.output / PACKAGE) as z:
            self.assertEqual(set(z.namelist()), MEMBERS)
            self.assertEqual(
                z.read("f139-v2-receipt.json"),
                (self.output / INPUT_RECEIPT).read_bytes())
            self.assertEqual(
                z.read("f139-v2-native-report.json"),
                (self.output / INPUT_REPORT).read_bytes())
        self.assertTrue(self.provider()["qualified"])

    def test_negative_creates_zip_but_never_positive_custody(self):
        report = self.fixture.report(self.oslabel)
        report["candidate_behavior"][0]["outcome"] = "TEST_FAILURE"
        report["candidate_behavior"][0]["returncode"] = 1
        report["candidate_behavior"] = report["candidate_behavior"][:1]
        report["candidate_compile"] = None
        report["qualification_complete"] = False
        receipt, ok = self.run_worker(report)
        self.assertFalse(ok)
        self.assertFalse(receipt["native_qualified"])
        self.assertFalse(self.provider(require_qualified=False)["qualified"])
        with self.assertRaisesRegex(
                V2ProviderDenied, "INCOMPLETE_NEGATIVE_CANNOT_BE_PROMOTED"):
            self.provider()

    def test_package_is_reproducible_byte_for_byte(self):
        self.run_worker()
        first = (self.output / PACKAGE).read_bytes()
        clone = self.root / "clone"
        clone.mkdir()
        for name in (INPUT_RECEIPT, INPUT_REPORT):
            (clone / name).write_bytes((self.output / name).read_bytes())
        result = package_v2_development_output(clone, self.admission)
        self.assertEqual(first, (clone / PACKAGE).read_bytes())
        self.assertEqual(result["zip_sha256"], digest(first))
        self.assertFalse(result["provider_origin_authenticated"])
        self.assertFalse(result["owner_event_written"])
        self.assertFalse(result["scientific_first_use_authorized"])

    def test_mismatched_signed_receipt_rejected_before_zip_written(self):
        self.run_worker()
        (self.output / PACKAGE).unlink()
        path = self.output / INPUT_RECEIPT
        obj = json.loads(path.read_bytes())
        obj["native_qualified"] = False
        path.write_bytes(canonical(obj))
        with self.assertRaisesRegex(
                V2PackagingDenied, "V2_SIGNED_RECEIPT_OR_REPORT_MISMATCH"):
            package_v2_development_output(self.output, self.admission)
        self.assertFalse((self.output / PACKAGE).exists())

    def test_missing_or_extra_input_refused(self):
        self.run_worker()
        (self.output / PACKAGE).unlink()
        (self.output / "untrusted_extra.txt").write_text("unauthorized")
        with self.assertRaisesRegex(
                V2PackagingDenied, "V2_INPUT_INVENTORY_OR_REPLAY"):
            package_v2_development_output(self.output, self.admission)
        (self.output / "untrusted_extra.txt").unlink()
        (self.output / INPUT_REPORT).unlink()
        with self.assertRaisesRegex(
                V2PackagingDenied, "V2_INPUT_INVENTORY_OR_REPLAY"):
            package_v2_development_output(self.output, self.admission)

    def test_duplicate_zip_write_is_denied(self):
        self.run_worker()
        with self.assertRaisesRegex(
                V2PackagingDenied, "V2_INPUT_INVENTORY_OR_REPLAY"):
            package_v2_development_output(self.output, self.admission)

    def test_noncanonical_or_incorrect_version_denied(self):
        self.run_worker()
        (self.output / PACKAGE).unlink()
        path = self.output / INPUT_REPORT
        value = json.loads(path.read_bytes())
        path.write_bytes(json.dumps(value, indent=2).encode())
        with self.assertRaisesRegex(
                V2PackagingDenied, "V2_SOURCE_NONCANONICAL"):
            package_v2_development_output(self.output, self.admission)
        path.write_bytes(canonical(value))
        value["schema"] = "forge.f139.nci04.native-development-diagnostic.v1"
        path.write_bytes(canonical(value))
        with self.assertRaises(ValueError):
            package_v2_development_output(self.output, self.admission)
        self.assertFalse((self.output / PACKAGE).exists())

    def test_reject_wrong_admission_run_os_and_candidate(self):
        from dataclasses import replace
        self.run_worker()
        (self.output / PACKAGE).unlink()
        for bad in (
            replace(self.admission, run_id=40200000002),
            replace(self.admission, runner_os=(
                "ubuntu-latest" if self.oslabel == "windows-latest"
                else "windows-latest")),
            replace(self.admission, authorization_sha256="0" * 64),
            replace(self.admission, intent=replace(
                self.admission.intent, after_sha256="0" * 64)),
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                package_v2_development_output(self.output, bad)
        self.assertFalse((self.output / PACKAGE).exists())

    def test_zip_file_is_development_only_and_has_no_secret(self):
        self.run_worker()
        raw = (self.output / PACKAGE).read_bytes()
        self.assertNotIn(b"F139_WORKER_HMAC_KEY", raw)
        self.assertNotIn(b"f139-receipt.json", raw)
        self.assertLess(len(raw), 2_000_000)
        self.assertTrue(self.provider()["receipt"]["development_only"])
        self.assertFalse(
            self.provider()["receipt"]["scientific_first_use_authorized"])


if __name__ == "__main__":
    unittest.main()
