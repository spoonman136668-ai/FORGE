"""G35 fake provider API transcripts; all original owner stores remain inert."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import io
import json
import unittest
import zipfile

from f139.local_controller import GitHub
from f139.nci04_native_contract import digest
from f139.nci04_g35_provider_origin import (
    G35ProviderDenied, inspect_v2_provider_run, INNER_FILENAME,
    OWNER_REPOSITORY_ID, OWNER_WORKFLOW_ID,
)
from f139.test_nci04_provider_receipt_v2 import positive_fixture, bundle

RUN = 40290000001
START = "2026-10-25T16:00:00Z"
OS = ("ubuntu-latest", "windows-latest")


class G35ProviderOriginTests(unittest.TestCase):
    def setUp(self):
        original, report = positive_fixture()
        self.admissions = {}
        self.artifacts = {}
        self.jobs = [{"name": "native-authorize-v2", "id": 1,
                      "status": "completed", "conclusion": "success"}]
        self.arts = []
        self.ticket = "f139-nci04-i933-eeeeeeeeeeee-aaaaaaaa"
        for ix, label in enumerate(OS):
            a = replace(original, ticket=self.ticket, run_id=RUN,
                        issue_number=933, issue_id=6010000333,
                        runner_os=label)
            r = json.loads(json.dumps(report))
            r["os"] = label
            from f139.nci04_worker_v2 import supported_modules, FROZEN_COUNTS, unit_argv
            mods, excluded = supported_modules(label)
            r["supported_behavior_modules"] = list(mods)
            r["explicit_unsupported_modules"] = list(excluded)
            r["candidate_behavior"] = [
                {**r["candidate_behavior"][0],
                 "argv": list(unit_argv(name)),
                 "test_count": FROZEN_COUNTS[name]} for name in mods]
            zip_inner, _ = bundle(a, r)
            out = io.BytesIO()
            with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as z:
                z.writestr(INNER_FILENAME, zip_inner)
            outer = out.getvalue()
            artifact_id = 50 + ix
            self.artifacts[artifact_id] = outer
            self.arts.append({
                "id": artifact_id,
                "name": "forge-f139-v2-native-receipt-" + label,
                "digest": "sha256:" + digest(outer),
                "size_in_bytes": len(outer),
                "expired": False,
                "workflow_run": {
                    "id": RUN, "repository_id": OWNER_REPOSITORY_ID,
                    "head_repository_id": OWNER_REPOSITORY_ID,
                    "head_sha": a.source_sha},
            })
            self.admissions[label] = a
            self.jobs.append({
                "id": 2 + ix, "name": "native-execute-v2 (" + label + ")",
                "status": "completed", "conclusion": "success",
            })
        self.run = {
            "id": RUN, "name": "F139 " + self.ticket,
            "display_title": "F139 " + self.ticket,
            "event": "workflow_dispatch",
            "workflow_id": OWNER_WORKFLOW_ID,
            "path": ".github/workflows/forge-f139-development-worker.yml",
            "head_sha": original.source_sha,
            "head_branch": "main", "run_attempt": 1,
            "created_at": START, "status": "completed",
            "conclusion": "success",
            "repository": {"id": OWNER_REPOSITORY_ID,
                           "full_name": "spoonman136668-ai/FORGE"},
        }

    def api(self):
        def respond(args):
            path = args[0]
            if path == "repos/spoonman136668-ai/FORGE/actions/runs/" + str(RUN):
                val = self.run
            elif path.endswith("/jobs?per_page=100"):
                val = {"total_count": len(self.jobs), "jobs": self.jobs}
            elif path.endswith("/artifacts?per_page=100"):
                val = {"total_count": len(self.arts), "artifacts": self.arts}
            elif "/actions/artifacts/" in path and path.endswith("/zip"):
                ident = int(path.split("/")[-2])
                return self.artifacts[ident]
            else:
                raise AssertionError("unexpected API route:" + path)
            return json.dumps(val).encode()
        return GitHub(runner=respond)

    def read(self):
        return inspect_v2_provider_run(
            self.api(), run_id=RUN, ticket=self.ticket,
            started_at=START, admissions=self.admissions)

    def test_real_api_reader_contract_checks_both_inner_receipts(self):
        out = self.read()
        self.assertTrue(out["both_platforms_development_qualified"])
        self.assertEqual(set(out["provider_payloads"]), set(OS))
        self.assertEqual(set(out["platforms"]), set(OS))
        self.assertTrue(out["provider_api_metadata_crosschecked"])
        for key in ("original_ledger_and_v2_permit_independently_verified",
                    "original_terminal_written", "unattended_progression_verified",
                    "scientific_first_use_authorized"):
            self.assertFalse(out[key])

    def test_g34_pr_run_is_not_an_original_v2_workflow(self):
        self.run["event"] = "pull_request"
        with self.assertRaisesRegex(G35ProviderDenied,
                                    "ORIGINAL_WORKFLOW_EVENT_SOURCE"):
            self.read()

    def test_v1_authorizer_not_upcast_to_v2(self):
        self.jobs[0]["name"] = "native-authorize"
        with self.assertRaisesRegex(G35ProviderDenied,
                                    "SEPARATE_V2_AUTHORIZER"):
            self.read()

    def test_duplicate_or_absent_provider_job_fails_closed(self):
        self.jobs.append(dict(self.jobs[-1]))
        with self.assertRaisesRegex(G35ProviderDenied,
                                    "INVENTORY_INCOMPLETE_OR_EXTRA"):
            self.read()
        self.jobs.pop()
        self.jobs.pop()
        with self.assertRaisesRegex(G35ProviderDenied,
                                    "INVENTORY_INCOMPLETE_OR_EXTRA"):
            self.read()

    def test_older_attempt_does_not_replay(self):
        self.run["run_attempt"] = 2
        with self.assertRaisesRegex(G35ProviderDenied,
                                    "ORIGINAL_WORKFLOW_EVENT_SOURCE"):
            self.read()

    def test_wrong_source_and_protected_main_denied(self):
        self.run["head_sha"] = "0" * 40
        with self.assertRaisesRegex(G35ProviderDenied,
                                    "ORIGINAL_WORKFLOW_EVENT_SOURCE"):
            self.read()
        self.run["head_sha"] = self.admissions[OS[0]].source_sha
        self.run["head_branch"] = "experimental"
        with self.assertRaises(G35ProviderDenied):
            self.read()

    def test_artifact_digest_wrong_or_duplicate_rejected(self):
        self.arts[0]["digest"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(G35ProviderDenied,
                                    "OUTER_GITHUB_ARTIFACT_BYTES_OR_DIGEST"):
            self.read()
        self.arts[0]["digest"] = "sha256:" + digest(self.artifacts[50])
        self.arts[1]["name"] = self.arts[0]["name"]
        with self.assertRaisesRegex(G35ProviderDenied,
                                    "V2_OS_ARTIFACT_NOT_UNIQUE"):
            self.read()

    def test_wrong_or_extra_outer_member_rejected(self):
        old = self.artifacts[50]
        for members in ((("junk.txt", b"bad"),),
                        ((INNER_FILENAME, b"fake"), ("extra.txt", b"bad"))):
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as z:
                for name, content in members:
                    z.writestr(name, content)
            self.artifacts[50] = buffer.getvalue()
            self.arts[0]["digest"] = "sha256:" + digest(self.artifacts[50])
            self.arts[0]["size_in_bytes"] = len(self.artifacts[50])
            with self.assertRaisesRegex(G35ProviderDenied,
                                        "OUTER_SINGLE_V2_MEMBER"):
                self.read()
        self.artifacts[50] = old

    def test_wrong_signed_admission_run_or_os_fails(self):
        a = self.admissions[OS[1]]
        self.admissions[OS[1]] = replace(a, run_id=RUN + 1)
        with self.assertRaisesRegex(G35ProviderDenied,
                                    "ORIGINAL_PROVIDER_CLIENT_AND_SIGNED"):
            self.read()

    def test_nonterminal_and_incomplete_run_refused(self):
        self.run["status"] = "in_progress"
        self.run["conclusion"] = None
        with self.assertRaisesRegex(G35ProviderDenied, "RUN_NOT_TERMINAL"):
            self.read()

    def test_github_adapter_requires_existing_provider_client(self):
        with self.assertRaisesRegex(G35ProviderDenied,
                                    "ORIGINAL_PROVIDER_CLIENT_AND_SIGNED"):
            inspect_v2_provider_run(
                None, run_id=RUN, ticket=self.ticket, started_at=START,
                admissions=self.admissions)


if __name__ == "__main__":
    unittest.main()
