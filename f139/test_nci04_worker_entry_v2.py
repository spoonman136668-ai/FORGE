"""G30 signed V2 developmental seam, never a live native workflow."""
from __future__ import annotations

from dataclasses import replace
import inspect
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from f139.nci04_signed_native import NativeAdmission
from f139.nci04_worker_entry import execute_v2_development, NativeWorkerBlocked, cli
from f139.nci04_worker_v2 import RECEIPT_SCHEMA, SOURCE_SHA, SOURCE_TREE
from f139.test_nci04_worker_v2 import V2ContractTests


class SignedV2BridgeTests(unittest.TestCase):
    def setUp(self):
        f = V2ContractTests()
        f.setUp()
        self.f = f
        self.label = "windows-latest" if os.name == "nt" else "ubuntu-latest"
        self.admission = NativeAdmission(
            "f139-nci04-i933-" + "e" * 12 + "-" + f.c.intent_sha256[:8],
            "Yggdrasil", "e" * 40, 40200000001, self.label, 933, 6010000333,
            f.c, "f" * 64)
        t = tempfile.TemporaryDirectory(prefix="f139-g30-source-only-")
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.original, self.scratch, self.output = (
            self.root / "original", self.root / "scratch", self.root / "output")
        for p in (self.original, self.scratch, self.output):
            p.mkdir()

    def invoke(self, admission=None, report=None):
        r = self.f.report(self.label) if report is None else report
        with mock.patch("f139.nci04_worker_v2.run_v2", return_value=r) as run:
            result = execute_v2_development(
                self.admission if admission is None else admission,
                self.original, self.scratch, self.output)
        return result, run

    def test_qualified_separate_v2_receipt_no_v1_artifacts(self):
        (receipt, passed), run = self.invoke()
        self.assertTrue(passed)
        self.assertEqual(receipt["schema"], RECEIPT_SCHEMA)
        self.assertEqual(receipt["original_signed_admission_sha256"], "f" * 64)
        self.assertFalse(receipt["scientific_first_use_authorized"])
        self.assertTrue((self.output / "f139-v2-development-receipt.json").is_file())
        self.assertTrue((self.output / "f139-v2-development-report.json").is_file())
        self.assertFalse((self.output / "f139-receipt.json").exists())
        self.assertEqual(run.call_count, 1)

    def test_invalid_signer_source_lane_and_os_fail_closed(self):
        for bad in (
            replace(self.admission, authorization_sha256=""),
            replace(self.admission, lane="Wingless"),
            replace(self.admission, source_sha="invalid"),
            replace(self.admission, ticket="unbound"),
            replace(self.admission, issue_number=0),
            replace(self.admission, runner_os="macos-latest"),
            replace(self.admission, intent=replace(
                self.admission.intent, target_tree_sha="0" * 40)),
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.invoke(admission=bad)
            self.assertEqual(list(self.output.iterdir()), [])

    def test_bad_report_does_not_write_any_receipt(self):
        report = self.f.report(self.label)
        report["scientific_first_use"] = True
        with self.assertRaises(ValueError):
            self.invoke(report=report)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_negative_diagnostic_is_preserved_as_negative_v2_only(self):
        report = self.f.report(self.label)
        report["candidate_behavior"][0]["outcome"] = "TEST_FAILURE"
        report["candidate_behavior"][0]["returncode"] = 1
        report["candidate_behavior"] = report["candidate_behavior"][:1]
        report["candidate_compile"] = None
        report["qualification_complete"] = False
        (receipt, passed), _ = self.invoke(report=report)
        self.assertFalse(passed)
        self.assertFalse(receipt["native_qualified"])
        self.assertEqual(receipt["schema"], RECEIPT_SCHEMA)
        self.assertFalse((self.output / "f139-receipt.json").exists())

    def test_no_overwrite_replay_or_unisolated_output(self):
        self.invoke()
        with self.assertRaisesRegex(NativeWorkerBlocked, "V2_ISOLATED_ROOT"):
            self.invoke()

    def test_signing_secret_cannot_leak_to_v2(self):
        with mock.patch.dict(os.environ, {"F139_WORKER_HMAC_KEY": "test-secret"}):
            with self.assertRaisesRegex(NativeWorkerBlocked, "V2_CREDENTIAL"):
                self.invoke()
        self.assertEqual(list(self.output.iterdir()), [])

    def test_existing_live_cli_does_not_expose_v2(self):
        live = inspect.getsource(cli)
        self.assertIn('commands.add_parser("execute")', live)
        self.assertNotIn('commands.add_parser("execute-v2")', live)
        self.assertNotIn("execute_v2_development(", live)


if __name__ == "__main__":
    unittest.main()
