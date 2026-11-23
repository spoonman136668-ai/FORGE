"""A8E2A source-only authentication of the original #706 split-outcome failure.

NOT an owner SQLite custody admission, source transition, or dispatch. Requires
the original succeeded Ubuntu native receipt AND the original failed Windows
setup-python job. An ordinary QUARANTINED stage is never sufficient.
"""
from __future__ import annotations

import re

from f139.nci04_native_contract import digest
from f139.nci04_owner_issue import NativeIssue
from f139.nci04_provider_receipt import native_receipt_from_zip

SOURCE = "09f3d7447900f99dd3d532c5d3d90ed7e8c20ac3"
TICKET = "f139-nci04-i706-09f3d7447900-09dc99f4"
OWNER_HEAD_55 = "cccd83848ebbc0371489a85f473358946d9112397e322899a7b9150c0f3c5e7c"
RUN_ID = 39642950458
WORKFLOW_ID = 388797257
JOBS = {
    "native-authorize": (119370974275, "success"),
    "execute": (119370976252, "skipped"),
    "native-execute (ubuntu-latest)": (119371117159, "success"),
    "native-execute (windows-latest)": (119371117117, "failure"),
}
ARTIFACT_ID = 12366181474
ARTIFACT_SHA256 = "8a030626d5240a3c8301cbec9660aaedfdd39d8a5fdda478fbda2c991bbf23d3"
ARTIFACT_BYTES = 2054
ZIP_NAME = "forge-f139-native-receipt-ubuntu-latest"
WORKER_STEP = "Execute source-bound isolated native candidate and fixed full regression"


class SplitNegativeDenied(ValueError):
    pass


def require(ok: bool, code: str):
    if not ok:
        raise SplitNegativeDenied("F139_A8E2A_" + code)


def verify_706_split_provider_original(*, run: dict, jobs: list[dict],
                                       artifacts: list[dict], archive: bytes,
                                       task: dict, quarantine_event: dict,
                                       owner_head_sha256: str,
                                       issue: NativeIssue, owner_hmac_key: str,
                                       epoch: int) -> dict:
    """Authenticate the exact original failure; return provisional evidence ONLY.

    Caller separately authenticates the GitHub GET and the owner SQLite event
    chain under the original SingleOwner lock. No file or SQLite writes here.
    """
    require(isinstance(issue, NativeIssue) and issue.ticket == TICKET
            and issue.source_sha == SOURCE and issue.number == 706
            and issue.lane == "Wingless",
            "ISSUE_IDENTITY")
    require(isinstance(task, dict)
            and task.get("ticket") == TICKET
            and task.get("lane") == "Wingless"
            and task.get("source_sha") == SOURCE
            and task.get("stage") == "QUARANTINED"
            and task.get("run_id") is None
            and task.get("evidence_sha") is None
            and not task.get("evidence_dir")
            and isinstance(task.get("quarantine_reason"), str)
            and re.fullmatch(r"[A-Z_]{3,72}", task["quarantine_reason"]) is not None,
            "ORIGINAL_TASK_NOT_FAILED")
    require(isinstance(quarantine_event, dict)
            and quarantine_event.get("seq") == 55
            and quarantine_event.get("kind") == "ATTEMPT_QUARANTINED"
            and quarantine_event.get("sha") == OWNER_HEAD_55
            and isinstance(quarantine_event.get("payload"), dict)
            and quarantine_event["payload"] ==
                {"ticket": TICKET, "reason": task["quarantine_reason"]}
            and owner_head_sha256 == OWNER_HEAD_55,
            "ORIGINAL_LEDGER_HEAD_OR_REASON_DRIFT")
    require(isinstance(run, dict)
            and run.get("id") == RUN_ID
            and run.get("workflow_id") == WORKFLOW_ID
            and run.get("path") == ".github/workflows/forge-f139-development-worker.yml"
            and run.get("name") == "F139 " + TICKET
            and run.get("display_title") == "F139 " + TICKET
            and run.get("event") == "workflow_dispatch"
            and run.get("head_branch") == "main"
            and run.get("head_sha") == SOURCE
            and run.get("status") == "completed"
            and run.get("conclusion") == "failure"
            and type(run.get("run_attempt")) is int and run["run_attempt"] == 1
            and isinstance(run.get("repository"), dict)
            and run["repository"].get("full_name") == "spoonman136668-ai/FORGE",
            "ORIGINAL_PROVIDER_RUN_DRIFT")
    require(isinstance(jobs, list) and len(jobs) == len(JOBS),
            "PROVIDER_JOB_COUNT")
    found = {}
    for job in jobs:
        require(isinstance(job, dict) and isinstance(job.get("name"), str)
                and job["name"] in JOBS and job["name"] not in found
                and type(job.get("id")) is int
                and job["id"] == JOBS[job["name"]][0]
                and job.get("run_id") == RUN_ID
                and job.get("status") == "completed"
                and job.get("conclusion") == JOBS[job["name"]][1],
                "PROVIDER_JOB_DRIFT")
        found[job["name"]] = job
    require(set(found) == set(JOBS), "PROVIDER_JOB_SET")
    def step(job_name, step_name, conclusion):
        steps = found[job_name].get("steps")
        require(isinstance(steps, list)
                and len([s for s in steps
                         if isinstance(s, dict) and
                         s.get("name") == step_name and
                         s.get("conclusion") == conclusion]) == 1,
                "PROVIDER_JOB_STEP_DRIFT")
    step("native-execute (windows-latest)", "Run actions/setup-python@v5", "failure")
    step("native-execute (windows-latest)", WORKER_STEP, "skipped")
    step("native-execute (ubuntu-latest)", WORKER_STEP, "success")
    require(isinstance(artifacts, list) and len(artifacts) == 1
            and isinstance(artifacts[0], dict),
            "PROVIDER_ARTIFACT_SET")
    artifact = artifacts[0]
    wr = artifact.get("workflow_run")
    require(artifact.get("id") == ARTIFACT_ID
            and artifact.get("name") == ZIP_NAME
            and artifact.get("expired") is False
            and artifact.get("digest") == "sha256:" + ARTIFACT_SHA256
            and artifact.get("size_in_bytes") == ARTIFACT_BYTES
            and isinstance(wr, dict) and wr.get("id") == RUN_ID
            and wr.get("head_sha") == SOURCE,
            "PROVIDER_ORIGINAL_ARTIFACT_DRIFT")
    require(type(archive) is bytes and len(archive) == ARTIFACT_BYTES
            and digest(archive) == ARTIFACT_SHA256,
            "ORIGINAL_ZIP_BYTES_DRIFT")
    require(isinstance(owner_hmac_key, str) and len(owner_hmac_key) >= 32
            and type(epoch) is int and epoch > 0,
            "ORIGINAL_OWNER_HMAC_UNAVAILABLE")
    # This original Ubuntu job SUCCEEDED, unlike #696; it must have a
    # cryptographically valid POSITIVE native receipt, never a forged negative.
    verified = native_receipt_from_zip(
        archive, artifact, task, RUN_ID, "ubuntu-latest",
        epoch, issue, owner_hmac_key=owner_hmac_key, expect_qualified=True)
    require(verified.get("native_qualified") is True
            and verified.get("ticket") == TICKET
            and verified.get("source_sha") == SOURCE
            and verified.get("run_id") == RUN_ID
            and verified.get("scientific_originals_dispatched") == 0
            and verified.get("scientific_first_use_authorized") is False,
            "UBUNTU_RECEIPT_AUTHORITY_DRIFT")
    return {
        "schema": "forge.f139.nci04.split-original-negative.v1",
        "ticket": TICKET, "source_sha": SOURCE, "run_id": RUN_ID,
        "provider_artifact_id": ARTIFACT_ID,
        "provider_artifact_sha256": ARTIFACT_SHA256,
        "provider_zip_bytes": ARTIFACT_BYTES,
        "owner_head_seq": 55, "owner_head_sha256": OWNER_HEAD_55,
        "quarantine_reason": task["quarantine_reason"],
        "ubuntu_native_qualified": True, "windows_python_setup_failed": True,
        "whole_run_qualified": False,
        "original_owner_durable_custody": False,
        "scientific_first_use": False,
        "successor_source_transition_authorized": False,
    }
