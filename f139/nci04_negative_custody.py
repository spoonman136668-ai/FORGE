"""F139 A8A: authenticate a failed original provider run without SQLite writes.

This source-only validator does not fetch provider data, persist an original
artifact, change task stage, advance source SHA, or dispatch a successor.
Owner code must obtain run/jobs/artifact details from GitHub independently and
then perform separate durable custody before an A8 source transition.
"""
from __future__ import annotations

from f139.nci04_native_contract import digest
from f139.nci04_provider_receipt import native_negative_from_zip
from f139.nci04_owner_issue import NativeIssue


class NegativeCustodyDenied(ValueError):
    pass


def require(ok, why):
    if not ok:
        raise NegativeCustodyDenied("F139_NCI04_A8_" + why)


def verified_negative_provider_original(*, run: dict, jobs: list,
                                        artifact: dict, archive: bytes,
                                        task: dict, issue: NativeIssue,
                                        owner_hmac_key: str, epoch: int):
    """Return a precise PROVISIONAL negative certificate, never terminal PASS.

    Requires the independent provider's full original failed workflow and
    both terminal OS jobs, plus the unchanged signed HMAC-bound negative ZIP.
    A GitHub artifact alone cannot establish owner-machine durable custody.
    """
    require(isinstance(issue, NativeIssue) and isinstance(task, dict),
            "ISSUE_OR_TASK_NOT_AUTHENTICATED")
    require(isinstance(run, dict) and type(run.get("id")) is int
            and run["id"] > 0
            and run.get("event") == "workflow_dispatch"
            and run.get("head_sha") == issue.source_sha
            and run.get("head_branch") == "main"
            and run.get("status") == "completed"
            and run.get("conclusion") == "failure"
            and type(run.get("run_attempt")) is int
            and run["run_attempt"] == 1
            and isinstance(run.get("repository"), dict)
            and run["repository"].get("full_name") ==
                "spoonman136668-ai/FORGE",
            "FAILED_PROVIDER_RUN_SOURCE_OR_ATTEMPT_DRIFT")
    # The original native workflow also creates a legacy 'execute' job
    # that is *skipped* by design. Preserve that original provider record;
    # reject any additional job, re-run, or unrecognized worker.
    require(isinstance(jobs, list) and len(jobs) == 4 and
            all(isinstance(j, dict) and type(j.get("id")) is int
                and j["id"] > 0 and j.get("status") == "completed"
                and j.get("run_id") == run["id"]
                for j in jobs)
            and len({j["id"] for j in jobs}) == 4,
            "FAILED_PROVIDER_JOB_SET_INVALID")
    state = {j.get("name"):j.get("conclusion") for j in jobs}
    require(len(state) == 4 and
            state.get("execute") == "skipped" and
            state.get("native-authorize") == "success" and
            state.get("native-execute (ubuntu-latest)") == "failure" and
            state.get("native-execute (windows-latest)") in
                ("success", "failure") and
            sum(v == "failure" for v in state.values()) >= 1,
            "FAILED_PROVIDER_JOB_CONCLUSION_DRIFT")
    require(isinstance(artifact, dict) and
            type(artifact.get("id")) is int and artifact["id"] > 0 and
            artifact.get("name") == "forge-f139-native-receipt-ubuntu-latest" and
            artifact.get("expired") is False and
            isinstance(artifact.get("workflow_run"), dict) and
            artifact["workflow_run"].get("id") == run["id"] and
            artifact["workflow_run"].get("head_sha") == issue.source_sha,
            "NEGATIVE_PROVIDER_ARTIFACT_SOURCE_DRIFT")
    receipt = native_negative_from_zip(
        archive, artifact, task, run["id"], "ubuntu-latest",
        epoch, issue, owner_hmac_key=owner_hmac_key)
    require(receipt["native_qualified"] is False and
            receipt["run_id"] == run["id"] and
            receipt["source_sha"] == issue.source_sha and
            receipt["ticket"] == issue.ticket and
            receipt["scientific_originals_dispatched"] == 0 and
            receipt["scientific_first_use_authorized"] is False,
            "NEGATIVE_RECEIPT_AUTHORITY_DRIFT")
    # This is strictly an authentication result; no claim that the bytes
    # exist in owner profile, or that a later source transition is permitted.
    return {
        "schema": "forge.f139.nci04.failed-provider-original.v1",
        "ticket":issue.ticket, "source_sha":issue.source_sha,
        "run_id":run["id"], "run_attempt":1,
        "provider_artifact_id":artifact["id"],
        "provider_artifact_sha256":digest(archive),
        "provider_zip_bytes":len(archive),
        "native_report_sha256":receipt["native_report_sha256"],
        "native_qualified":False,
        "provider_negative_authenticated":True,
        "original_owner_durable_custody":False,
        "original_sqlite_mutations":0,
        "scientific_first_use":False,
        "successor_source_transition_authorized":False,
    }
