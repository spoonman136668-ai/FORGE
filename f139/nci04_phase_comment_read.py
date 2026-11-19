"""Read-only, bounded GitHub issue/comment steering *discovery* adapter.

Uses the pre-existing F139 GitHub GET route and hardcoded owner policy issue.
GitHub transport authenticates the returned metadata but cannot prove that
a comment alone authorizes an owner-mode transition. This module NEVER writes
a mode event, chooses a runtime phase, runs work or changes operator policy.
The caller must independently verify source/epoch and the *complete* original
SQLite consumed-comment history. Do not call automatically from run_once().
"""
from __future__ import annotations

import json

from f139.nci04_phase_manual_intent import (
    ISSUE_URL, OWNER, OWNER_ID, PREFIX, SCHEMA, ManualPhaseDenied,
    _unique_object, inspect_comment,
)

REPO_ROUTE = "repos/spoonman136668-ai/FORGE"
ISSUE_ROUTE = REPO_ROUTE + "/issues/807"
COMMENT_ROUTE = ISSUE_ROUTE + "/comments?per_page=100&page="
POLICY_SCHEMA = "forge.f139.native-autonomy-feed-owner-policy.v1"
POLICY_FIELDS = frozenset({
    "schema", "enabled", "source_sha", "title_prefix", "lanes",
    "max_issue_creations_per_cycle", "require_owner_authored_pr",
    "require_single_head_commit_delta", "require_single_allowed_source_file",
    "scientific_first_use", "paid_model_calls", "accepted_ref_mutations",
    "new_controller", "new_scheduler", "new_queue",
})
PAGE_SIZE = 100
MAX_PAGES = 8
MAX_PENDING = 16
MAX_ISSUE_BODY = 4096


class PhaseCommentReadDenied(ValueError):
    pass


def require(ok: bool, code: str) -> None:
    if not ok:
        raise PhaseCommentReadDenied("F139_PHASE_COMMENT_" + code)


def _issue_policy(provider, source_sha: str) -> dict:
    issue = provider.get(ISSUE_ROUTE)
    require(type(issue) is dict
            and type(issue.get("number")) is int and issue["number"] == 807
            and type(issue.get("id")) is int and issue["id"] > 0
            and issue.get("state") == "open"
            and "pull_request" not in issue
            and type(issue.get("user")) is dict
            and issue["user"].get("login") == OWNER
            and type(issue["user"].get("id")) is int
            and issue["user"]["id"] == OWNER_ID
            and issue.get("author_association") == "OWNER",
            "ISSUE_NOT_ORIGINAL_POLICY_OWNER")
    body = issue.get("body")
    require(type(body) is str and len(body) <= MAX_ISSUE_BODY,
            "POLICY_BODY_INVALID")
    try:
        policy = json.loads(body, object_pairs_hook=_unique_object)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise PhaseCommentReadDenied("F139_PHASE_COMMENT_POLICY_JSON_INVALID") from exc
    require(type(policy) is dict and set(policy) == POLICY_FIELDS
            and policy["schema"] == POLICY_SCHEMA
            and policy["enabled"] is True
            and type(policy["source_sha"]) is str
            and policy["source_sha"] == source_sha
            and policy["title_prefix"] == "F139 autonomy DEV:"
            and type(policy["lanes"]) is list
            and policy["lanes"] == ["Wingless", "Yggdrasil", "TTT-Hybrid"]
            and type(policy["max_issue_creations_per_cycle"]) is int
            and 0 <= policy["max_issue_creations_per_cycle"] <= 2
            and policy["require_owner_authored_pr"] is True
            and policy["require_single_head_commit_delta"] is True
            and policy["require_single_allowed_source_file"] is True
            and all(policy[field] is False for field in (
                "scientific_first_use", "new_controller", "new_scheduler", "new_queue"))
            and type(policy["paid_model_calls"]) is int
            and policy["paid_model_calls"] == 0
            and type(policy["accepted_ref_mutations"]) is int
            and policy["accepted_ref_mutations"] == 0,
            "POLICY_SOURCE_OR_FENCE_DRIFT")
    return policy


def inspect_pending_owner_intents(*, provider, installed_source_sha: str,
                                   protected_main_sha: str,
                                   owner_epoch: int,
                                   consumed_comment_ids: frozenset[int]) -> dict:
    """Cold read-only discovery of unconsumed, owner-authored candidate intents.

    This never consumes a comment and DOES NOT establish permission to alter
    the live owner. A separately source-qualified original owner would need
    to re-fetch and verify each selected exact comment before atomic admission.
    """
    from f139.local_controller import GitHub
    require(type(provider) is GitHub, "ORIGINAL_GITHUB_PROVIDER_REQUIRED")
    require(type(installed_source_sha) is str
            and installed_source_sha == protected_main_sha
            and len(installed_source_sha) == 40
            and all(c in "0123456789abcdef" for c in installed_source_sha)
            and type(owner_epoch) is int and 1 <= owner_epoch < 2**31
            and type(consumed_comment_ids) is frozenset
            and len(consumed_comment_ids) <= 100000
            and all(type(n) is int and n > 0 for n in consumed_comment_ids),
            "OWNER_SOURCE_EPOCH_OR_CONSUMPTION_UNVERIFIED")
    _issue_policy(provider, installed_source_sha)
    pending = []
    total_comments = 0
    last_id = 0
    exhausted = False
    for page in range(1, MAX_PAGES + 1):
        rows = provider.get(COMMENT_ROUTE + str(page))
        require(type(rows) is list and len(rows) <= PAGE_SIZE,
                "PAGINATION_UNVERIFIED")
        for raw in rows:
            require(type(raw) is dict and type(raw.get("id")) is int
                    and raw["id"] > last_id
                    and raw.get("issue_url") == ISSUE_URL
                    and type(raw.get("body")) is str,
                    "COMMENT_SEQUENCE_OR_ISSUE_DRIFT")
            last_id = raw["id"]
            total_comments += 1
            if not raw["body"].startswith(PREFIX):
                continue  # Unrelated discussion is not a mode request.
            # All prefixed comments, even from nonowners, are checked so a
            # forged command cannot silently disappear from the catalog.
            if raw["id"] in consumed_comment_ids:
                # Original SQLite is authoritative for already-consumed IDs.
                # Deleted/changed historical comments require separate
                # provider/ledger revalidation before any live mode writer.
                continue
            try:
                candidate = inspect_comment(
                    comment=raw, installed_source_sha=installed_source_sha,
                    protected_main_sha=protected_main_sha,
                    owner_epoch=owner_epoch,
                    consumed_comment_ids=consumed_comment_ids)
            except ManualPhaseDenied as exc:
                raise PhaseCommentReadDenied(
                    "F139_PHASE_COMMENT_UNAUTHENTICATED_INTENT") from exc
            pending.append(candidate)
            require(len(pending) <= MAX_PENDING, "PENDING_BUDGET_EXCEEDED")
        if len(rows) < PAGE_SIZE:
            exhausted = True
            break
    require(exhausted, "COMMENT_CATALOG_NOT_EXHAUSTIVE")
    # Returning multiple candidates is observational. Only a separately
    # verified original owner can choose and commit the oldest one under lock.
    return {
        "schema": "forge.f139.owner-phase-comment-preview.v1",
        "policy_source_sha": installed_source_sha,
        "owner_epoch": owner_epoch,
        "issue_number": 807,
        "comments_scanned": total_comments,
        "pending": tuple(pending),
        "advisory_only": True,
        "authenticated_provider_read": True,
        "owner_admitted": False,
        "dispatch_authorized": False,
        "scientific_first_use": False,
        "self_source_mutation": False,
        "accepted_ref_mutation": False,
        "new_controller": False,
    }
