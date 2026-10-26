"""Immutable original-owner release pin, independent of moving main.

A protected-main merge does not install code in the sole Windows task.
The authenticated original SQLite source and owner-authored policy decide what
the existing task may run. A later commit is NOT an implicit source promotion.
"""
from __future__ import annotations

import re
from typing import Callable
from f139.nci04_autonomy_feed import (
    NativeFeedDenied, inspect_policy, POLICY_ISSUE, FORGE_REPO,
)

_SHA = re.compile(r"[a-f0-9]{40}\Z")


class ReleaseContinuityDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise ReleaseContinuityDenied("F139_RELEASE_PIN_" + reason)


def release_worker_branch(source_sha: str) -> str:
    """A distinct exact-commit worker ref for each owner-approved release."""
    need(isinstance(source_sha, str) and _SHA.fullmatch(source_sha) is not None,
         "RELEASE_REF_SOURCE_INVALID")
    return "f139-owner-release-" + source_sha


def verify_release_worker_branch(get: Callable[[str], object],
                                 source_sha: str) -> str:
    branch_name = release_worker_branch(source_sha)
    doc = get(f"repos/{FORGE_REPO}/branches/{branch_name}")
    need(isinstance(doc, dict)
         and doc.get("name") == branch_name
         and isinstance(doc.get("commit"), dict)
         and doc["commit"].get("sha") == source_sha,
         "WORKER_BRANCH_NOT_IMMUTABLE_EXACT_SOURCE")
    return branch_name


def prove_deployed_release_pin(get: Callable[[str], object], *,
                               deployed_source: str,
                               protected_source: str) -> dict:
    """Bounded read-only proof that main still contains the released ancestor.

    The currently installed source must independently be the exact clean
    original owner checkout, and original Database.verify and activation
    must independently pass before the caller uses this proof. No rights
    are conferred on post-release changes to main.
    """
    need(callable(get) and isinstance(deployed_source, str)
         and isinstance(protected_source, str)
         and _SHA.fullmatch(deployed_source) is not None
         and _SHA.fullmatch(protected_source) is not None
         and deployed_source != protected_source, "SOURCE_SHA_INVALID")
    branch = get(f"repos/{FORGE_REPO}/branches/main")
    need(isinstance(branch, dict) and branch.get("protected") is True
         and isinstance(branch.get("commit"), dict)
         and branch["commit"].get("sha") == protected_source,
         "PROTECTED_MAIN_IDENTITY_DRIFT")
    raw = get(f"repos/{FORGE_REPO}/issues/{POLICY_ISSUE}")
    try:
        policy = inspect_policy(raw, deployed_source)
    except NativeFeedDenied as exc:
        # Reuse the existing exact owner-policy verifier, retain only its
        # bounded non-sensitive denial code, never silently accept drift.
        raise ReleaseContinuityDenied(
            "F139_RELEASE_PIN_" + str(exc)) from exc
    need(policy["enabled"] is True, "RELEASE_POLICY_DISABLED")
    # The moving protected default branch is for development only. Before
    # releasing new work, a separate exact-commit workflow ref MUST exist;
    # otherwise Actions would silently run the wrong worker code from main.
    verify_release_worker_branch(get, deployed_source)
    comparison = get(f"repos/{FORGE_REPO}/compare/"
                     f"{deployed_source}...{protected_source}")
    need(isinstance(comparison, dict)
         and comparison.get("status") == "ahead"
         and type(comparison.get("ahead_by")) is int
         and comparison["ahead_by"] >= 1
         and comparison.get("behind_by") == 0
         and isinstance(comparison.get("merge_base_commit"), dict)
         and comparison["merge_base_commit"].get("sha") == deployed_source,
         "NOT_RELEASE_ANCESTRY")
    # Detect a moving protected branch between policy and ancestry checks.
    final = get(f"repos/{FORGE_REPO}/branches/main")
    need(isinstance(final, dict)
         and final.get("protected") is True
         and isinstance(final.get("commit"), dict)
         and final["commit"].get("sha") == protected_source,
         "PROTECTED_MAIN_MOVED")
    return {
        "schema": "forge.f139.authenticated-deployed-release-continuity.v1",
        "released_source_sha": deployed_source,
        "latest_protected_main_sha": protected_source,
        "new_commits_are_uninstalled": True,
        "worker_ref_is_exact_release": True,
        "existing_owner_policy_authorized": True,
        "native_development_only": True,
        "scientific_first_use": False,
        "new_dispatcher": False,
        "source_transition_granted": False,
    }
