"""Fail-closed qualification for R29 successor proposal boundaries."""
import importlib.util
import json
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).with_name("successor.py")
SPEC = importlib.util.spec_from_file_location("r29_successor", SCRIPT)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)

class R29SuccessorGate(unittest.TestCase):
    def test_duplicate_keys_rejected(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_JSON_KEY"):
            MOD.parse(b'{"outcome":"negative","outcome":"positive"}')

    def test_nonfinite_rejected(self):
        with self.assertRaisesRegex(ValueError, "INVALID_FLOAT"):
            MOD.parse(b'{"score":NaN}')

    def test_wrong_run_rejected_before_science(self):
        with self.assertRaisesRegex(ValueError, "PARENT_RUN_ID_DRIFT"):
            MOD.build(b"{}", b"{}", b"{}", b"{}", "0")

    def test_claim_drift_rejected_before_science(self):
        manifest = json.dumps({"experiment_id":MOD.PARENT_ID}).encode()
        original = json.dumps({"github_run_id":MOD.PARENT_RUN}).encode()
        with self.assertRaisesRegex(ValueError, "FIRST_USE_CLAIM_DRIFT"):
            MOD.build(manifest, original, b"{}", b"{}", MOD.PARENT_RUN)

    def test_no_dispatch_surface(self):
        source = SCRIPT.read_text()
        for banned in ("gh workflow run", "subprocess.run", "subprocess.Popen", "actions: write"):
            self.assertNotIn(banned, source)
        self.assertIn('"new_original_dispatch_authorized": False', source)
        self.assertIn('"ckb_execution_authority_unchanged": True', source)

if __name__ == "__main__":
    unittest.main()
