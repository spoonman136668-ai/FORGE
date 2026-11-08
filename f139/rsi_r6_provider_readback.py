"""Read-only, original-provider intake for bounded FORGE repair proposals.

This uses the EXISTING F139 GitHub GET adapter, not a controller, queue,
workflow, credential source, scheduler, dispatch, merge or owner hook.
The sole effect is producing a local source-only development proposal.
Caller-supplied run IDs are not authorization to execute the proposal.
"""
from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from hashlib import sha1
import re

from f139.local_controller import GitHub, REPO
from f139.rsi_r6_known_repair_cycle import (
    Evidence, PATH, HEAD, MAX_SOURCE, MAX_LOG,
    Proposal, RepairDenied, digest, propose,
)

READBACK_SCHEMA = "forge.f139.rsi-r6.readonly-github-evidence.v1"
_SHA40 = re.compile(r"[0-9a-f]{40}\Z")
_JOB_NAMES = frozenset({"windows_f139", "windows_native", "original-owner-cold-audit"})
_ALLOWED_EVENTS = frozenset({"push", "pull_request"})


def need(ok: bool, why: str) -> None:
    if not ok:
        raise RepairDenied("F139_RSI_R6_PROVIDER_" + why)


def git_blob(data: bytes) -> str:
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


@dataclass(frozen=True)
class Readback:
    schema: str
    run_id: int
    job_id: int
    original_head_sha: str
    path: str
    source_git_blob_sha: str
    log_sha256: str
    proposal: Proposal
    # Provider readback does not confer permission or ensure source eligibility.
    original_owner_admitted: bool = False
    source_regression_pass: bool = False
    scientific_first_use: bool = False
    production_release: bool = False


def acquire(*, provider: GitHub, run_id: int, job_id: int, path: str,
            expected_head: str, consumed_scopes: frozenset[str]) -> Readback:
    """Fetch a single recorded failure from GitHub using existing read-only IO.

    This does not poll for new work. A separately qualified existing owner
    must source IDs, authorize FORGE self-repair scope, and journal consumption
    before an isolated candidate could be executed or published.
    """
    need(type(provider) is GitHub and type(run_id) is int and run_id > 0
         and type(job_id) is int and job_id > 0
         and type(path) is str and PATH.fullmatch(path) is not None
         and type(expected_head) is str and HEAD.fullmatch(expected_head) is not None,
         "READBACK_INPUT_INVALID")
    base = "repos/" + REPO + "/"
    run = provider.get(base + "actions/runs/" + str(run_id))
    need(type(run) is dict and run.get("id") == run_id
         and run.get("head_sha") == expected_head
         and type(run.get("run_attempt")) is int
         and run["run_attempt"] == 1
         and run.get("status") == "completed"
         and run.get("conclusion") == "failure"
         and run.get("event") in _ALLOWED_EVENTS
         and type(run.get("repository")) is dict
         and run["repository"].get("full_name") == REPO
         and type(run.get("head_repository")) is dict
         and run["head_repository"].get("full_name") == REPO
         and type(run.get("actor")) is dict
         and run["actor"].get("login") == "spoonman136668-ai",
         "RUN_PROVIDER_OR_PROVENANCE_DRIFT")
    job = provider.get(base + "actions/jobs/" + str(job_id))
    need(type(job) is dict and job.get("id") == job_id
         and job.get("run_id") == run_id
         and job.get("status") == "completed"
         and job.get("conclusion") == "failure"
         and job.get("name") in _JOB_NAMES,
         "JOB_PROVIDER_OR_PROVENANCE_DRIFT")
    obj = provider.get(base + "contents/" + path + "?ref=" + expected_head)
    need(type(obj) is dict and obj.get("path") == path
         and obj.get("encoding") == "base64"
         and type(obj.get("sha")) is str
         and _SHA40.fullmatch(obj["sha"]) is not None
         and type(obj.get("size")) is int
         and 0 < obj["size"] <= MAX_SOURCE
         and type(obj.get("content")) is str,
         "SOURCE_PROVIDER_IDENTITY_DRIFT")
    encoded = obj["content"].replace("\n", "")
    need(len(encoded) <= 4 * ((MAX_SOURCE + 2) // 3), "SOURCE_BASE64_SIZE")
    try:
        before = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise RepairDenied("F139_RSI_R6_PROVIDER_SOURCE_NOT_BASE64") from exc
    need(len(before) == obj["size"] and git_blob(before) == obj["sha"],
         "SOURCE_BLOB_READBACK_DRIFT")
    # Logs are read from a failed, immutable attempt. No raw log is printed,
    # archived, or routed into GitHub issues. This is an authenticated read,
    # not permission for a retry or a replacement attempt.
    raw = provider.runner([base + "actions/jobs/" + str(job_id) + "/logs"])
    need(type(raw) is bytes and 0 < len(raw) <= MAX_LOG,
         "JOB_LOG_MISSING_OR_UNBOUNDED")
    witness = Evidence(expected_head, run_id, job_id,
                       "WINDOWS_SQLITE_OPEN_HANDLE_CLEANUP",
                       digest(raw), raw, path, digest(before))
    result = propose(evidence=witness, pinned_before=before,
                     consumed_scopes=consumed_scopes)
    return Readback(READBACK_SCHEMA, run_id, job_id, expected_head, path,
                    obj["sha"], digest(raw), result)
