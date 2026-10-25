"""G37: GitHub ten-input routing and fail-closed original owner release tests."""
import os
from pathlib import Path
import re
import unittest
from unittest import mock

from f139.local_controller import v2_owner_terminal_release_guard


class G37CompactWorkflowTests(unittest.TestCase):
    def test_dispatch_inputs_remain_ten(self):
        file = (Path(__file__).resolve().parent.parent /
                ".github/workflows/forge-f139-development-worker.yml")
        raw = file.read_text()
        body = raw.split("  workflow_dispatch:\n    inputs:\n", 1)[1].split(
            "\npermissions:", 1)[0]
        fields = re.findall(r"^      ([a-z0-9_]+):$", body, re.M)
        self.assertEqual(set(fields), {
            "ticket", "lane", "source_sha", "epoch", "signature",
            "issue_number", "issue_id", "body_sha256",
            "target_package", "native_bundle"})
        self.assertEqual(len(fields), 10)
        self.assertIn("inputs.target_package == 'f139-nci04-v2'", raw)
        self.assertIn("inputs.target_package != 'f139-nci04-v2'", raw)

    def test_original_v2_has_no_automatic_release(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(v2_owner_terminal_release_guard("a" * 40))

    def test_release_fails_closed_on_wrong_source_or_unqualified_writer(self):
        good = "a" * 40
        with mock.patch.dict(os.environ, {
            "F139_V2_ORIGINAL_OWNER_RELEASE_SOURCE": good,
            "F139_V2_PROVIDER_TERMINAL_WRITER_APPROVED": "false"
        }, clear=True):
            self.assertFalse(v2_owner_terminal_release_guard(good))
        with mock.patch.dict(os.environ, {
            "F139_V2_ORIGINAL_OWNER_RELEASE_SOURCE": "b" * 40,
            "F139_V2_PROVIDER_TERMINAL_WRITER_APPROVED": "true"
        }, clear=True):
            self.assertFalse(v2_owner_terminal_release_guard(good))

    def test_source_pin_and_terminal_writer_both_required(self):
        with mock.patch.dict(os.environ, {
            "F139_V2_ORIGINAL_OWNER_RELEASE_SOURCE": "a" * 40,
            "F139_V2_PROVIDER_TERMINAL_WRITER_APPROVED": "true"
        }, clear=True):
            self.assertTrue(v2_owner_terminal_release_guard("a" * 40))
            self.assertFalse(v2_owner_terminal_release_guard("invalid"))

    def test_no_extra_controller_or_secret_reference_in_dispatch_contract(self):
        raw = (Path(__file__).resolve().parent.parent /
               ".github/workflows/forge-f139-development-worker.yml").read_text()
        self.assertNotIn("\n  schedule:", raw)
        self.assertNotIn("\n  push:", raw)
        self.assertIn("native-authorize-v2:", raw)
        self.assertIn("native-execute-v2:", raw)
        self.assertIn("F139_V2_OWNER_SIGNATURE='v2_owner_signature'", raw)


if __name__ == "__main__":
    unittest.main()
