"""Original-owner read-only FORGE issue-catalog cutoff for a fresh F139 epoch.

The cutoff is a *negative replay floor*, NEVER a positive authorization to
create, admit or dispatch any issue. This module reads authenticated GitHub
metadata while the ORIGINAL owner is separately quiesced and its kernel
mutex is held. It does not manipulate Windows tasks, SQLite, Git refs,
workers or learned Yggdrasil state. Recheck the floor at the true handoff.
"""
from __future__ import annotations

import re
from typing import Callable

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_v59_owner_forward_readiness import (
    SOURCE, HEAD_SEQ, HEAD_SHA256, audit_frozen_original_readonly,
)
from f139.nci04_fresh_dev_exclusions import SCHEMA as EXCLUSIONS_SCHEMA
from f139.nci04_autonomy_feed import inspect_policy, NativeFeedDenied

REPO = "spoonman136668-ai/FORGE"
ROOT = "repos/" + REPO
API = "https://api.github.com/" + ROOT
POLICY_ISSUE = 807
SCHEMA = "forge.f139.fresh-native-provider-cutover-floor.v1"
ISSUE_PAGE = (ROOT +
    "/issues?state=all&sort=created&direction=desc&per_page=1&page=1")
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
STAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")


class FreshRemoteCutoverDenied(ValueError):
    pass


def need(ok: bool, why: str) -> None:
    if not ok:
        raise FreshRemoteCutoverDenied("F139_FRESH_REMOTE_" + why)


def _head(get: Callable, source: str) -> dict:
    result = get(ROOT + "/branches/main")
    need(isinstance(result, dict) and result.get("name") == "main"
         and result.get("protected") is True
         and isinstance(result.get("commit"), dict)
         and result["commit"].get("sha") == source,
         "PROTECTED_MAIN_SOURCE_DRIFT")
    return result


def _latest_issue(get: Callable) -> dict:
    items = get(ISSUE_PAGE)
    need(type(items) is list and len(items) == 1,
         "NEWEST_ISSUE_PAGE_MISSING")
    item = items[0]
    need(type(item) is dict and type(item.get("number")) is int
         and item["number"] > 0
         and type(item.get("id")) is int and item["id"] > 0
         and type(item.get("created_at")) is str
         and STAMP.fullmatch(item["created_at"]) is not None
         and item.get("repository_url") == API
         and item.get("url") == API + "/issues/" + str(item["number"]),
         "NEWEST_ISSUE_PROVIDER_IDENTITY_INVALID")
    return {
        "number": item["number"],
        "id": item["id"],
        "created_at": item["created_at"],
    }


def prove_fresh_native_issue_cutover_floor(
    original: Database, *, target_source_sha: str,
    consumed_exclusions: dict, get: Callable[[str], object],
    original_task_quiesced: Callable[[], bool],
) -> dict:
    """Read-only high-water witness; never a new native-issue admission.

    A GitHub issue number includes PRs. Freeze a provider-verified latest
    repository issue/PR number and exclude ALL numbers <= that floor. Even
    an unconsumed old issue must never become a new-epoch task.

    The owner task's Windows SID, process, disabled state, and lease release
    must be independently qualified by the existing original-host route.
    Returning this receipt does not establish that independent evidence.
    """
    need(type(original) is Database
         and getattr(original, "_readonly_opened", False) is True
         and original.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and original.conn.total_changes == 0
         and original.filename.is_absolute()
         and original.filename.name == "state.sqlite"
         and original.filename.parent.name == "FORGE-F139"
         and SingleOwner.held(original.filename.with_suffix(".lock")) is True,
         "ORIGINAL_READONLY_MUTEX_REQUIRED")
    need(callable(get) and callable(original_task_quiesced)
         and original_task_quiesced() is True,
         "ORIGINAL_OWNER_QUIESCENCE_REQUIRED")
    need(type(target_source_sha) is str
         and SHA40.fullmatch(target_source_sha) is not None
         and target_source_sha != SOURCE,
         "TARGET_SOURCE_INVALID")
    need(type(consumed_exclusions) is dict
         and consumed_exclusions.get("schema") == EXCLUSIONS_SCHEMA
         and consumed_exclusions.get("source_sha") == SOURCE
         and consumed_exclusions.get("original_head_seq") == HEAD_SEQ
         and consumed_exclusions.get("original_head_sha256") == HEAD_SHA256
         and consumed_exclusions.get("release_qualified") is False
         and consumed_exclusions.get("fresh_activation_authorized") is False
         and consumed_exclusions.get("previous_work_replay_authorized") is False
         and consumed_exclusions.get("scientific_first_use") is False
         and consumed_exclusions.get("owner_task_mutations") == 0
         and type(consumed_exclusions.get("old_issue_numbers")) is list
         and all(type(n) is int and n > 0
                 for n in consumed_exclusions["old_issue_numbers"])
         and len(set(consumed_exclusions["old_issue_numbers"]))
             == len(consumed_exclusions["old_issue_numbers"]),
         "ORIGINAL_EXCLUSION_PREIMAGE_INVALID")
    original.verify()
    before = audit_frozen_original_readonly(original)
    meta = original.meta()
    need(before.get("source_sha") == SOURCE
         and before.get("head_seq") == HEAD_SEQ
         and before.get("head_sha256") == HEAD_SHA256
         and meta["source_sha"] == SOURCE
         and meta["head_seq"] == HEAD_SEQ
         and meta["head_hash"] == HEAD_SHA256,
         "ORIGINAL_EVENT_HEAD_DRIFT")
    _head(get, target_source_sha)
    owner_policy = get(ROOT + "/issues/" + str(POLICY_ISSUE))
    try:
        policy = inspect_policy(owner_policy, SOURCE)
    except NativeFeedDenied as exc:
        raise FreshRemoteCutoverDenied(
            "F139_FRESH_REMOTE_ORIGINAL_OWNER_POLICY_INVALID") from exc
    need(policy.get("enabled") is True
         and policy.get("scientific_first_use") is False
         and policy.get("paid_model_calls") == 0
         and policy.get("new_controller") is False
         and policy.get("new_scheduler") is False
         and policy.get("new_queue") is False,
         "ORIGINAL_OWNER_POLICY_OUT_OF_SCOPE")
    highest = _latest_issue(get)
    need(highest["number"] >= max(
        consumed_exclusions["old_issue_numbers"], default=0),
        "ISSUE_HIGH_WATER_BEHIND_CONSUMED")
    # A second exact issue GET binds provider metadata independently of the
    # potentially cached sorted index and catches a replaced/ambiguous ID.
    detail = get(ROOT + "/issues/" + str(highest["number"]))
    need(type(detail) is dict
         and detail.get("repository_url") == API
         and detail.get("url") == API + "/issues/" + str(highest["number"])
         and type(detail.get("number")) is int
         and type(detail.get("id")) is int
         and detail["number"] == highest["number"]
         and detail["id"] == highest["id"]
         and detail.get("created_at") == highest["created_at"],
         "ISSUE_DETAIL_RACE_OR_IDENTITY_DRIFT")
    need(_latest_issue(get) == highest,
         "ISSUE_CATALOG_MOVED_DURING_CUTOVER_READ")
    _head(get, target_source_sha)
    need(original_task_quiesced() is True
         and SingleOwner.held(
             original.filename.with_suffix(".lock")) is True
         and original.conn.total_changes == 0
         and audit_frozen_original_readonly(original) == before,
         "OWNER_TASK_ORIGINAL_PREIMAGE_MOVED")
    exclusions_sha = digest(canonical(consumed_exclusions))
    return {
        "schema": SCHEMA,
        "original_source_sha": SOURCE,
        "original_head_seq": HEAD_SEQ,
        "original_head_sha256": HEAD_SHA256,
        "target_forge_source_sha": target_source_sha,
        "consumed_exclusions_sha256": exclusions_sha,
        "remote_cutover_issue_number_floor": highest["number"],
        "remote_cutover_issue_id": highest["id"],
        "remote_cutover_issue_created_at": highest["created_at"],
        "remote_cutover_issue_provider_verified": True,
        "original_owner_policy_source_sha": SOURCE,
        "owner_task_name": "FORGE-F139-UnifiedController",
        "original_owner_preimage_verified": True,
        "source_main_unchanged_during_read": True,
        "original_task_quiescence_callback_satisfied": True,
        "task_sid_and_process_independently_qualified": False,
        "release_qualified": False,
        "fresh_activation_authorized": False,
        "owner_task_rebind_authorized": False,
        "issue_admission_authorized": False,
        "worker_dispatch_authorized": False,
        "new_controller": False,
        "new_scheduler": False,
        "new_queue": False,
        "scientific_first_use": False,
        "paid_model_calls": 0,
    }
