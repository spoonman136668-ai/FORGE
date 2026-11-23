"""Fail-closed split original #706 provider contract tests (source only)."""
from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from f139.nci04_owner_issue import NativeIssue
from f139.nci04_split_negative_custody import (
    ARTIFACT_BYTES, ARTIFACT_ID, ARTIFACT_SHA256,
    JOBS, OWNER_HEAD_55, RUN_ID, SOURCE, TICKET, WORKER_STEP, ZIP_NAME,
    SplitNegativeDenied, verify_706_split_provider_original,
)

REASON = "FAILED_OR_CANCELLED_NO_REPLAY"


class SplitOriginalProviderTests(unittest.TestCase):
    def setUp(self):
        self.issue = NativeIssue(
            number=706, issue_id=5958742360, ticket=TICKET, lane="Wingless",
            source_sha=SOURCE, issue_body_sha256="a"*64,
            native_intent_sha256="b"*64, qualification_key="c"*64,
            intent_raw=b"fixture", candidate=None,
        )
        self.task = {
            "ticket": TICKET, "lane": "Wingless", "source_sha": SOURCE,
            "stage": "QUARANTINED", "run_id": None,
            "evidence_sha": None, "evidence_dir": None,
            "quarantine_reason": REASON,
        }
        self.quarantine_event = {
            "seq": 55, "kind": "ATTEMPT_QUARANTINED",
            "sha": OWNER_HEAD_55,
            "payload": {"ticket": TICKET, "reason": REASON},
        }
        self.run = {
            "id": RUN_ID, "workflow_id": 388797257,
            "path": ".github/workflows/forge-f139-development-worker.yml",
            "name": "F139 " + TICKET, "display_title": "F139 " + TICKET,
            "event": "workflow_dispatch", "head_branch": "main",
            "head_sha": SOURCE, "status": "completed", "conclusion": "failure",
            "run_attempt": 1,
            "repository": {"full_name": "spoonman136668-ai/FORGE"},
        }
        self.jobs = [
            {"name": name, "id": identity, "run_id": RUN_ID,
             "status": "completed", "conclusion": conclusion, "steps": []}
            for name, (identity, conclusion) in JOBS.items()
        ]
        windows = next(j for j in self.jobs if j["name"] == "native-execute (windows-latest)")
        windows["steps"] = [
            {"name": "Run actions/setup-python@v5", "conclusion": "failure"},
            {"name": WORKER_STEP, "conclusion": "skipped"},
        ]
        linux = next(j for j in self.jobs if j["name"] == "native-execute (ubuntu-latest)")
        linux["steps"] = [{"name": WORKER_STEP, "conclusion": "success"}]
        self.artifacts = [{
            "id": ARTIFACT_ID, "name": ZIP_NAME, "expired": False,
            "digest": "sha256:" + ARTIFACT_SHA256,
            "size_in_bytes": ARTIFACT_BYTES,
            "workflow_run": {"id": RUN_ID, "head_sha": SOURCE},
        }]
        self.archive = b"x"*ARTIFACT_BYTES

    def proof(self, **updates):
        args = {
            "run": self.run, "jobs": self.jobs,
            "artifacts": self.artifacts, "archive": self.archive,
            "task": self.task, "quarantine_event": self.quarantine_event,
            "owner_head_sha256": OWNER_HEAD_55,
            "issue": self.issue, "owner_hmac_key": "unit-only-owner-key-"+"x"*40,
            "epoch": 1,
        }
        args.update(updates)
        with patch("f139.nci04_split_negative_custody.digest",
                   return_value=ARTIFACT_SHA256), patch(
                "f139.nci04_split_negative_custody.native_receipt_from_zip",
                return_value={
                    "native_qualified": True, "ticket": TICKET,
                    "source_sha": SOURCE, "run_id": RUN_ID,
                    "scientific_originals_dispatched": 0,
                    "scientific_first_use_authorized": False,
                }) as receipt:
            result = verify_706_split_provider_original(**args)
        return result, receipt

    def test_exact_split_original_is_provisional_never_accepted(self):
        result, receipt = self.proof()
        self.assertTrue(result["ubuntu_native_qualified"])
        self.assertTrue(result["windows_python_setup_failed"])
        self.assertFalse(result["whole_run_qualified"])
        self.assertFalse(result["original_owner_durable_custody"])
        self.assertFalse(result["successor_source_transition_authorized"])
        self.assertFalse(result["scientific_first_use"])
        receipt.assert_called_once()
        self.assertTrue(receipt.call_args.kwargs["expect_qualified"])

    def test_provider_run_replay_or_source_spoof_denied(self):
        for key, value in [("id", RUN_ID+1), ("run_attempt", 2),
                           ("head_sha", "f"*40), ("conclusion", "success"),
                           ("event", "push"), ("workflow_id", 1)]:
            with self.subTest(key=key):
                run = {**self.run, key: value}
                with self.assertRaisesRegex(SplitNegativeDenied, "ORIGINAL_PROVIDER_RUN_DRIFT"):
                    self.proof(run=run)

    def test_one_changed_provider_job_identity_denied(self):
        jobs = copy.deepcopy(self.jobs)
        jobs[0]["id"] += 1
        with self.assertRaisesRegex(SplitNegativeDenied, "PROVIDER_JOB_DRIFT"):
            self.proof(jobs=jobs)

    def test_missing_linux_positive_job_denied(self):
        jobs = copy.deepcopy(self.jobs)
        next(j for j in jobs if j["name"] == "native-execute (ubuntu-latest)")["conclusion"] = "failure"
        with self.assertRaisesRegex(SplitNegativeDenied, "PROVIDER_JOB_DRIFT"):
            self.proof(jobs=jobs)

    def test_windows_failure_must_be_setup_python_before_candidate(self):
        for changed_name in ["Run actions/setup-python@v5", WORKER_STEP]:
            with self.subTest(changed_name=changed_name):
                jobs = copy.deepcopy(self.jobs)
                w = next(j for j in jobs if j["name"] == "native-execute (windows-latest)")
                next(s for s in w["steps"] if s["name"] == changed_name)["conclusion"] = "success"
                with self.assertRaisesRegex(SplitNegativeDenied, "PROVIDER_JOB_STEP_DRIFT"):
                    self.proof(jobs=jobs)

    def test_missing_or_extra_zip_denied(self):
        with self.assertRaisesRegex(SplitNegativeDenied, "PROVIDER_ARTIFACT_SET"):
            self.proof(artifacts=[])
        with self.assertRaisesRegex(SplitNegativeDenied, "PROVIDER_ARTIFACT_SET"):
            self.proof(artifacts=self.artifacts*2)

    def test_genuine_zip_digest_and_size_must_match(self):
        with self.assertRaisesRegex(SplitNegativeDenied, "ORIGINAL_ZIP_BYTES_DRIFT"):
            self.proof(archive=b"x"*(ARTIFACT_BYTES-1))
        artifact = copy.deepcopy(self.artifacts)
        artifact[0]["digest"] = "sha256:"+"0"*64
        with self.assertRaisesRegex(SplitNegativeDenied, "PROVIDER_ORIGINAL_ARTIFACT_DRIFT"):
            self.proof(artifacts=artifact)

    def test_quarantine_and_immutable_55_head_required(self):
        task = {**self.task, "stage": "VERIFIED"}
        with self.assertRaisesRegex(SplitNegativeDenied, "ORIGINAL_TASK_NOT_FAILED"):
            self.proof(task=task)
        event = {**self.quarantine_event, "sha": "a"*64}
        with self.assertRaisesRegex(SplitNegativeDenied, "ORIGINAL_LEDGER_HEAD_OR_REASON_DRIFT"):
            self.proof(quarantine_event=event)
        with self.assertRaisesRegex(SplitNegativeDenied, "ORIGINAL_LEDGER_HEAD_OR_REASON_DRIFT"):
            self.proof(owner_head_sha256="a"*64)

    def test_absent_owner_proof_denied(self):
        with self.assertRaisesRegex(SplitNegativeDenied, "ORIGINAL_OWNER_HMAC_UNAVAILABLE"):
            self.proof(owner_hmac_key="")
        with self.assertRaisesRegex(SplitNegativeDenied, "ORIGINAL_OWNER_HMAC_UNAVAILABLE"):
            self.proof(epoch=0)

    def test_report_cannot_forge_whole_workflow_pass(self):
        with patch("f139.nci04_split_negative_custody.digest",
                   return_value=ARTIFACT_SHA256), patch(
                "f139.nci04_split_negative_custody.native_receipt_from_zip",
                return_value={
                    "native_qualified": False, "ticket": TICKET,
                    "source_sha": SOURCE, "run_id": RUN_ID,
                    "scientific_originals_dispatched": 0,
                    "scientific_first_use_authorized": False,
                }):
            with self.assertRaisesRegex(SplitNegativeDenied, "UBUNTU_RECEIPT_AUTHORITY_DRIFT"):
                verify_706_split_provider_original(
                    run=self.run, jobs=self.jobs, artifacts=self.artifacts,
                    archive=self.archive, task=self.task,
                    quarantine_event=self.quarantine_event,
                    owner_head_sha256=OWNER_HEAD_55,
                    issue=self.issue, owner_hmac_key="test-only-"+"x"*40,
                    epoch=1)
if __name__ == "__main__":
    unittest.main()
