"""Source-only Yggdrasil lineage and fresh-epoch native candidate preflight.

This does NOT activate F139, select an owner, admit a ticket, dispatch a
worker, retrieve or restore a checkpoint, train a learner, or authorize science.
It authenticates the accepted code baseline separately from the two DRAFT
research branches and rejects obvious old-work replay before future owner
admission. The central Yggdrasil Amalgam owner retains learned-state control.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from typing import Callable

from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_issue import NativeIssue
from f139.nci04_fresh_dev_exclusions import (
    candidate_violates_frozen_exclusions,
)

YGG = "spoonman136668-ai/Yggdrasil"
BASE = "repos/" + YGG
ACCEPTED = "5e74f8db85b2f5839c42148c0dfba69a88b1a2c9"
AMALGAM_PR = 1278
AMALGAM_HEAD = "86264b41a08d49f558418c0fba367f3a2636befa"
LINEAGE_PR = 1322
LINEAGE_HEAD = "6ab65282c3bd85ef1fd9571287aa88404a62d791"
LINEAGE_RECEIPT_PATH = (
    "research/contrib/chatgpt/YGG-LINEAGE01/recovered_research_archive.json"
)
LINEAGE_RECEIPT_BLOB = "bf43b222edcdce3437fd15d4754e4c763ea84c10"
ACCEPTED_NATIVE_PATH = "yggdrasil/public_causal_cells.py"
ACCEPTED_NATIVE_BLOB = "5c9a9904e31688bebc2e53723569e1fb988a981f"
RECEIPT_SCHEMA = "forge.f139.fresh-yggdrasil-research-source-boundary.v1"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")


class FreshYggdrasilBoundaryDenied(ValueError):
    pass


def need(condition: bool, code: str) -> None:
    if not condition:
        raise FreshYggdrasilBoundaryDenied(
            "F139_FRESH_YGGDRASIL_" + code)


def _content(get: Callable, path: str, ref: str, expected_blob: str) -> bytes:
    """Authenticated GitHub content identity, not merely a JSON body claim."""
    raw = get(BASE + "/contents/" + path + "?ref=" + ref)
    need(isinstance(raw, dict)
         and raw.get("type") == "file" and raw.get("sha") == expected_blob
         and raw.get("encoding") == "base64"
         and type(raw.get("size")) is int and 0 < raw["size"] < 300_000
         and isinstance(raw.get("content"), str),
         "FILE_IDENTITY_INVALID")
    encoded = raw["content"].replace("\n", "")
    try:
        payload = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise FreshYggdrasilBoundaryDenied(
            "F139_FRESH_YGGDRASIL_FILE_BASE64_INVALID") from exc
    need(base64.b64encode(payload).decode("ascii") == encoded
         and len(payload) == raw["size"]
         and hashlib.sha1(
            b"blob " + str(len(payload)).encode("ascii") +
            b"\0" + payload).hexdigest() == expected_blob,
         "FILE_BYTES_OR_GIT_BLOB_DRIFT")
    return payload


def read_yggdrasil_research_boundary(get: Callable[[str], object]) -> dict:
    """Verify current immutable references; no checkpoint state is imported."""
    need(callable(get), "GITHUB_READER_REQUIRED")
    branch = get(BASE + "/branches/main")
    need(isinstance(branch, dict)
         and branch.get("name") == "main"
         and branch.get("protected") is True
         and isinstance(branch.get("commit"), dict)
         and branch["commit"].get("sha") == ACCEPTED,
         "ACCEPTED_MAIN_MOVED")
    native_bytes = _content(
        get, ACCEPTED_NATIVE_PATH, ACCEPTED, ACCEPTED_NATIVE_BLOB)
    need(bool(native_bytes), "ACCEPTED_NATIVE_EMPTY")
    heads = {}
    for number, expected in (
        (AMALGAM_PR, AMALGAM_HEAD),
        (LINEAGE_PR, LINEAGE_HEAD),
    ):
        pr = get(BASE + "/pulls/" + str(number))
        need(isinstance(pr, dict)
             and pr.get("number") == number
             and pr.get("state") == "open"
             and pr.get("draft") is True
             and pr.get("merged_at") is None
             and isinstance(pr.get("head"), dict)
             and pr["head"].get("sha") == expected
             and pr["head"].get("repo", {}).get("full_name") == YGG
             and pr.get("base", {}).get("repo", {}).get("full_name") == YGG,
             "DRAFT_RESEARCH_OWNER_OR_HEAD_DRIFT")
        compare = get(BASE + "/compare/" + ACCEPTED + "..." + expected)
        need(isinstance(compare, dict)
             and compare.get("status") == "ahead"
             and type(compare.get("ahead_by")) is int
             and compare["ahead_by"] > 0
             and compare.get("behind_by") == 0
             and isinstance(compare.get("merge_base_commit"), dict)
             and compare["merge_base_commit"].get("sha") == ACCEPTED,
             "DRAFT_RESEARCH_NOT_DESCENDANT_OF_ACCEPTED")
        heads[number] = expected

    archived = _content(
        get, LINEAGE_RECEIPT_PATH, LINEAGE_HEAD, LINEAGE_RECEIPT_BLOB)
    try:
        audit = json.loads(archived)
    except (ValueError, UnicodeError) as exc:
        raise FreshYggdrasilBoundaryDenied(
            "F139_FRESH_YGGDRASIL_ARCHIVE_JSON_INVALID") from exc
    need(type(audit) is dict
         and audit.get("schema") ==
             "yggdrasil.lineage01.research-artifact-custody-audit.v1"
         and audit.get("status") ==
             "VERIFIED_ARCHIVED_DRAFT_EXPERIMENTAL_CHECKPOINT_ONLY"
         and isinstance(audit.get("git"), dict)
         and audit["git"].get("accepted_main_sha") == ACCEPTED
         and audit["git"].get("research_amalgam_pr") == AMALGAM_PR
         and audit["git"].get("research_amalgam_head_sha") == AMALGAM_HEAD
         and isinstance(audit.get("scientific_and_owner_limits"), dict)
         and audit["scientific_and_owner_limits"].get(
             "official_owner_checkpoint_identified") is False
         and audit["scientific_and_owner_limits"].get(
             "accepted_model_training_continuity") == "UNVERIFIED"
         and audit["scientific_and_owner_limits"].get(
             "original_amalgam_transfer_result") == "DEV_NO_GO"
         and audit["scientific_and_owner_limits"].get(
             "authorized_original_source_first_use") is False
         and audit["scientific_and_owner_limits"].get(
             "accepted_ref_changed") is False
         and audit["scientific_and_owner_limits"].get(
             "model_merged_or_deployed") is False,
         "DRAFT_ARCHIVE_MISCLASSIFIED_AS_ACCEPTED")
    return {
        "schema": RECEIPT_SCHEMA,
        "repository": YGG,
        "accepted_main_source_sha": ACCEPTED,
        "accepted_native_path": ACCEPTED_NATIVE_PATH,
        "accepted_native_blob_sha": ACCEPTED_NATIVE_BLOB,
        "amalgam_pr": AMALGAM_PR,
        "amalgam_draft_head_sha": heads[AMALGAM_PR],
        "lineage_pr": LINEAGE_PR,
        "lineage_draft_head_sha": heads[LINEAGE_PR],
        "lineage_archived_receipt_blob_sha": LINEAGE_RECEIPT_BLOB,
        "lineage_archived_receipt_sha256": digest(archived),
        "checkpoint_kind": "DRAFT_EXPERIMENTAL_ONLY",
        "official_cumulative_owner_checkpoint": "UNVERIFIED",
        "development_source_only": True,
        "new_canonical_learner": False,
        "checkpoint_imported": False,
        "model_continuation_authorized": False,
        "scientific_first_use": False,
        "new_training_actions": 0,
        "release_qualified": False,
        "owner_task_rebind_authorized": False,
        "worker_dispatched": False,
    }


def preflight_new_yggdrasil_development_issue(
    issue: NativeIssue, *, controller_source_sha: str,
    consumed_history: dict, research_boundary: dict,
    authenticated_remote_issue_floor: int | None,
) -> dict:
    """Reject only; returning this receipt never grants ticket admission.

    The issue itself must have already passed existing provider-backed
    inspect_owner_issue, including owner, current source, signed manifest
    and the independently authenticated target commit/tree.
    """
    need(type(issue) is NativeIssue
         and type(controller_source_sha) is str
         and SHA40.fullmatch(controller_source_sha) is not None
         and issue.source_sha == controller_source_sha
         and issue.lane == "Yggdrasil"
         and issue.candidate.lane == "Yggdrasil"
         and issue.candidate.target_commit == ACCEPTED
         and issue.candidate.path == ACCEPTED_NATIVE_PATH,
         "NOT_A_NEW_ACCEPTED_BASELINE_YGGDRASIL_ISSUE")
    need(type(research_boundary) is dict
         and set(research_boundary) == {
             "schema","repository","accepted_main_source_sha",
             "accepted_native_path","accepted_native_blob_sha",
             "amalgam_pr","amalgam_draft_head_sha",
             "lineage_pr","lineage_draft_head_sha",
             "lineage_archived_receipt_blob_sha",
             "lineage_archived_receipt_sha256","checkpoint_kind",
             "official_cumulative_owner_checkpoint",
             "development_source_only","new_canonical_learner",
             "checkpoint_imported","model_continuation_authorized",
             "scientific_first_use","new_training_actions",
             "release_qualified","owner_task_rebind_authorized",
             "worker_dispatched",
         }
         and research_boundary["schema"] == RECEIPT_SCHEMA
         and research_boundary["accepted_main_source_sha"] == ACCEPTED
         and research_boundary["amalgam_draft_head_sha"] == AMALGAM_HEAD
         and research_boundary["lineage_draft_head_sha"] == LINEAGE_HEAD
         and research_boundary["lineage_archived_receipt_blob_sha"] ==
             LINEAGE_RECEIPT_BLOB
         and research_boundary["checkpoint_kind"] == "DRAFT_EXPERIMENTAL_ONLY"
         and research_boundary["official_cumulative_owner_checkpoint"] ==
             "UNVERIFIED"
         and research_boundary["development_source_only"] is True
         and research_boundary["new_canonical_learner"] is False
         and research_boundary["checkpoint_imported"] is False
         and research_boundary["model_continuation_authorized"] is False
         and research_boundary["scientific_first_use"] is False
         and research_boundary["new_training_actions"] == 0
         and research_boundary["release_qualified"] is False
         and research_boundary["owner_task_rebind_authorized"] is False
         and research_boundary["worker_dispatched"] is False,
         "RESEARCH_BOUNDARY_NOT_AUTHENTICATED")
    need(type(authenticated_remote_issue_floor) is int
         and authenticated_remote_issue_floor >= 1,
         "CUTOVER_REMOTE_ISSUE_FLOOR_NOT_AUTHENTICATED")
    replay = candidate_violates_frozen_exclusions(
        consumed_history, issue_number=issue.number,
        issue_id=issue.issue_id, ticket=issue.ticket,
        lane=issue.lane, target_commit=issue.candidate.target_commit,
        path=issue.candidate.path, after_sha256=issue.candidate.after_sha256,
        authenticated_remote_issue_floor=authenticated_remote_issue_floor,
    )
    need(replay is False, "OLD_WORK_OR_UNVERIFIED_ISSUE_FLOOR")
    return {
        "schema": "forge.f139.fresh-yggdrasil-issue-preflight-only.v1",
        "source_sha": controller_source_sha,
        "issue_number": issue.number,
        "issue_id": issue.issue_id,
        "ticket": issue.ticket,
        "old_work_replay_rejected": True,
        "accepted_yggdrasil_main_sha": ACCEPTED,
        "draft_amalgam_not_accepted": True,
        "lineage_checkpoint_not_owner_accepted": True,
        "scientific_first_use": False,
        "new_canonical_learner": False,
        "owner_activation_authorized": False,
        "worker_dispatch_authorized": False,
    }
