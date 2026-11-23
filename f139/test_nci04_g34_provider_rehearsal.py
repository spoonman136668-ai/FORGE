"""G34 offline synthetic upload transport guard tests."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from f139.nci04_g34_provider_rehearsal import build_fixture, G34Denied, main
from f139.nci04_v2_artifact_package import PACKAGE
from f139.nci04_native_contract import digest


class G34UploadTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="g34-v2-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.platform = "windows-latest" if os.name == "nt" else "ubuntu-latest"

    def test_produce_and_verify_exact_zip_synthetic(self):
        proof = build_fixture(self.root, "f"*40, self.platform)
        self.assertEqual(proof["sha256"],
                         digest((self.root / PACKAGE).read_bytes()))
        self.assertTrue(proof["synthetic"])
        self.assertFalse(proof["science"])
        self.assertFalse(proof["owner_dispatch"])
        self.assertFalse(proof["native_execution"])
        self.assertFalse(proof["provider_origin_authenticated"])

    def test_bad_identity_never_writes_artifact(self):
        opposite = "windows-latest" if self.platform == "ubuntu-latest" else "ubuntu-latest"
        for sha, platform in (("f"*39, self.platform), ("f"*40, opposite)):
            with self.assertRaises(G34Denied):
                build_fixture(self.root, sha, platform)
            self.assertEqual(list(self.root.iterdir()), [])

    def test_reuse_does_not_overwrite_receipts(self):
        build_fixture(self.root, "f"*40, self.platform)
        with self.assertRaisesRegex(G34Denied, "OUTPUT_NOT_FRESH"):
            build_fixture(self.root, "f"*40, self.platform)

    def test_no_production_dispatch_allowed(self):
        env = {"GITHUB_REPOSITORY": "spoonman136668-ai/FORGE",
               "GITHUB_EVENT_NAME": "workflow_dispatch",
               "GITHUB_REF": "refs/heads/main"}
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch("sys.argv", ["g34", "--output", str(self.root)]):
                with self.assertRaisesRegex(G34Denied, "PR_ONLY_WITHOUT_OWNER_KEY"):
                    main()

    def test_workflow_cannot_schedule_or_use_owner_key(self):
        path = (Path(__file__).resolve().parent.parent /
                ".github/workflows/f139-g34-v2-artifact-transport.yml")
        raw = path.read_text()
        self.assertIn("pull_request:", raw)
        self.assertIn("actions/upload-artifact@v4", raw)
        self.assertIn("f139-v2-development-provider.zip", raw)
        for term in ("workflow_dispatch:", "schedule:", "secrets.",
                     "F139_WORKER_HMAC_KEY:", "f139-receipt.json"):
            self.assertNotIn(term, raw)


if __name__ == "__main__":
    unittest.main()
