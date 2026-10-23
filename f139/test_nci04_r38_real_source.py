"""R38 isolated no-network tests for exact-source authenticated read-only use."""
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from f139.nci04_r38_real_source import (
    ReadOnlyGitHub, SourceReadDenied, confirm_live_r7, main,
    FROZEN_R7, require,
)
from f139.test_nci04_r7_package import Fixture
from f139.nci04_r7_package import R37Denied


class _Reply:
    def __init__(self, obj):
        self.obj = json.dumps(obj).encode()
        self.status = 200
    def __enter__(self):
        return self
    def __exit__(self, *unused):
        pass
    def read(self, n):
        return self.obj[:n]


class _Open:
    def __init__(self):
        self.calls = []
    def open(self, request, timeout):
        self.calls.append((request.get_method(), request.full_url))
        return _Reply({"sha": "a"*40})


class _ProviderAdapter:
    def __init__(self, fixture):
        self.fixture = fixture
    def get(self, name):
        return self.fixture(name)


class TestR38ReadOnly(unittest.TestCase):
    def test_get_only_lanes_and_provider_get_no_writer_or_redirect(self):
        x = ReadOnlyGitHub("Wingless")
        x.token = ""
        fake = _Open()
        x.opener = fake
        resource = x.get("repos/spoonman136668-ai/Wingless/git/commits/" + "a"*40)
        self.assertEqual(resource["sha"], "a"*40)
        x.get("repos/spoonman136668-ai/Wingless/git/commits/" + "a"*40)
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(fake.calls[0][0], "GET")
        for forged in (
            "repos/spoonman136668-ai/Yggdrasil/git/blobs/" + "a"*40,
            "repos/spoonman136668-ai/Wingless/issues/1",
            "repos/spoonman136668-ai/Wingless/../FORGE/pulls/1",
            "repos/spoonman136668-ai/Wingless/actions/workflows",
            "https://evil.com/repo",
        ):
            with self.subTest(path=forged):
                with self.assertRaises(SourceReadDenied):
                    x.get(forged)
        self.assertEqual(len(fake.calls), 1)

    def test_full_manifest_with_untrusted_fixtures_never_admissible(self):
        for lane in ("Wingless", "Yggdrasil"):
            fixture = Fixture(lane)
            data = copy.deepcopy(FROZEN_R7)
            data[lane] = {"number": 382, "base": "b"*40, "head": "c"*40}
            with patch("f139.nci04_r38_real_source.FROZEN_R7", data), \
                 patch("f139.nci04_r38_real_source.ReadOnlyGitHub",
                       return_value=_ProviderAdapter(fixture)):
                result = confirm_live_r7(lane)
            self.assertEqual(result["manifest_file_count"], 5)
            self.assertEqual(result["source_snapshot"],
                             "AUTHENTICATED_IMMUTABLE_PROVIDER_GIT")
            self.assertEqual(result["admission"],
                             "BLOCKED_UNIMPLEMENTED_V2_OWNER_CONTRACT")
            self.assertEqual(result["worker"], "NOT_DISPATCHED")
            self.assertFalse(result["first_use"])
            self.assertEqual(result["dependency_evidence_scope"],
                             "base-tree-only-not-transitive-closure")
            self.assertEqual(len(result["manifest_files"]), 5)

    def test_fail_closed_on_source_drift_and_absent_output_directory(self):
        fixture = Fixture("Wingless")
        with patch("f139.nci04_r38_real_source.ReadOnlyGitHub",
                   return_value=_ProviderAdapter(fixture)):
            with self.assertRaises(SourceReadDenied):
                confirm_live_r7("Wingless")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SourceReadDenied):
                main(["--output-dir", tmp])
            self.assertTrue(Path(tmp).is_dir())

    def test_non_supported_lane_and_transport(self):
        with self.assertRaises(SourceReadDenied):
            ReadOnlyGitHub("FORGE")
        with self.assertRaises(SourceReadDenied):
            confirm_live_r7("Optimizer")


if __name__ == "__main__":
    unittest.main()
