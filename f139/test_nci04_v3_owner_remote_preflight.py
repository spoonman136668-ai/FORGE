"""Negative controls for original-owner remote-first preflight CLI."""
from __future__ import annotations

import base64
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import os
import subprocess
import unittest
from unittest.mock import patch

from f139.nci04_native_contract import canonical
from f139.nci04_v3_owner_remote_preflight import (
    GitHubGET, V3OwnerRemoteDenied, decode_request,
    inspect_before_owner_stop, main,
)
from f139.nci04_v3_remote_readonly_preflight import V3RemotePreflightDenied
from f139.test_nci04_v3_remote_readonly_preflight import (
    HEAD, MERGE, PR, TREE, RUNS, REPO, fixture,
)

REQUEST = dict(owner_source_sha=MERGE, owner_source_tree=TREE,
               pr_number=PR, pr_head_sha=HEAD, **RUNS)


def encoded(doc=REQUEST):
    return base64.b64encode(canonical(doc)).decode("ascii")


class OwnerRemoteFirstTests(unittest.TestCase):
    def test_valid_request_is_get_only_and_never_grants_authority(self):
        api = fixture()
        result = inspect_before_owner_stop(encoded(), api=api)
        self.assertEqual(result["remote_evidence"], "VERIFIED_READ_ONLY")
        self.assertFalse(result["safe_to_disable_task"])
        self.assertEqual(result["original_owner_cold_custody"], "NOT_CHECKED")
        self.assertFalse(result["signed_source_forward"])
        self.assertFalse(result["scientific_first_use"])
        self.assertEqual(result["worker_dispatches"], 0)
        self.assertEqual(set(api.calls), set(api.documents))

    def test_bad_or_replayed_payload_denied_without_network(self):
        for bad in ("", "%%%", "eA==", encoded({"pr_number": PR}),
                    encoded(dict(REQUEST, pr_number=1870)),
                    encoded(dict(REQUEST, pr_number=True)),
                    encoded(dict(REQUEST, owner_source_sha="bad")),
                    encoded(dict(REQUEST, regression_run_id=0)),
                    encoded(dict(REQUEST, unknown=True))):
            with self.subTest(case=bad[:20]):
                api = fixture()
                with self.assertRaises(V3OwnerRemoteDenied):
                    inspect_before_owner_stop(bad, api=api)
                self.assertEqual(api.calls, [])

    def test_noncanonical_and_duplicate_json_denied(self):
        value = canonical(REQUEST).decode("ascii")
        for raw in (value[:-1] + ',"pr_number":1871}',
                    json.dumps(REQUEST), value + "\n", '{"x":1}'):
            with self.subTest(raw=raw[:28]):
                with self.assertRaises(V3OwnerRemoteDenied):
                    decode_request(base64.b64encode(raw.encode()).decode())

    def test_main_drift_and_failed_ci_never_succeed(self):
        for field in ("protected", "head"):
            api = fixture()
            if field == "protected":
                api.documents[REPO + "/branches/main"]["protected"] = False
            else:
                api.documents[REPO + "/actions/runs/111"]["head_sha"] = "d"*40
            with self.subTest(field=field):
                with self.assertRaises(V3RemotePreflightDenied):
                    inspect_before_owner_stop(encoded(), api=api)

    @patch.dict(os.environ, {"GH_TOKEN": "r"*32})
    @patch("f139.nci04_v3_owner_remote_preflight.subprocess.run")
    def test_transport_is_fixed_get_only_and_rejects_unsafe_routes(self, runner):
        runner.return_value = subprocess.CompletedProcess(
            [], 0, '{"name":"main"}', "")
        reader = GitHubGET()
        self.assertEqual(reader.get(REPO + "/branches/main"), {"name":"main"})
        self.assertEqual(runner.call_args.args[0],
                         ["gh", "api", "--method", "GET", REPO + "/branches/main"])
        for route in ("https://evil.example", REPO + "/issues/1830",
                      REPO + "/branches/main;whoami",
                      REPO + "/actions/runs/42/jobs?per_page=500",
                      "repos/other/name/branches/main"):
            with self.subTest(route=route):
                with self.assertRaises(V3OwnerRemoteDenied):
                    reader.get(route)
        self.assertEqual(runner.call_count, 1)

    @patch.dict(os.environ, {"GH_TOKEN": "r"*32})
    @patch("f139.nci04_v3_owner_remote_preflight.subprocess.run")
    def test_provider_errors_json_tamper_timeout_denied(self, runner):
        reader = GitHubGET()
        for reply in (subprocess.CompletedProcess([], 1, "", "403 private"),
                      subprocess.CompletedProcess([], 0, '{"x":1,"x":2}', ""),
                      subprocess.CompletedProcess([], 0, "[]", "")):
            runner.return_value = reply
            with self.subTest(reply=reply.stdout):
                with self.assertRaises(V3OwnerRemoteDenied):
                    reader.get(REPO + "/branches/main")
        runner.side_effect = subprocess.TimeoutExpired(["gh"], 30)
        with self.assertRaises(V3OwnerRemoteDenied):
            reader.get(REPO + "/branches/main")

    def test_missing_token_and_invalid_cli_sanitized(self):
        with patch.dict(os.environ, {"GH_TOKEN": ""}):
            with self.assertRaisesRegex(V3OwnerRemoteDenied, "CREDENTIAL_REQUIRED"):
                GitHubGET().get(REPO + "/branches/main")
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            rc = main([])
        self.assertEqual(rc, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue().strip(),
                         "F139_V3_OWNER_REMOTE_PREFLIGHT=DENIED")

    @patch("f139.nci04_v3_owner_remote_preflight.GitHubGET")
    def test_cli_prints_read_only_with_no_disable_authority(self, adapter):
        adapter.return_value = fixture()
        buf = StringIO()
        with redirect_stdout(buf):
            rc = main([encoded()])
        self.assertEqual(rc, 0)
        self.assertIn("READ_ONLY_PASS", buf.getvalue())
        self.assertIn("COLD_CUSTODY=NOT_CHECKED", buf.getvalue())
        self.assertIn("TASK_MUTATION_AUTHORIZED=FALSE", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
