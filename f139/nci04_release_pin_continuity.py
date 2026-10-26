"""Immutable original-owner release pin, independent of moving main.

A protected-main merge does not install code in the sole Windows task.
The authenticated original SQLite source and owner-authored policy decide what
the existing task may run. A later commit is NOT an implicit source promotion.
"""
from __future__ import annotations

import re
from typing import Callable
from f139.nci04_autonomy_feed import inspect_policy, POLICY_ISSUE, FORGE_REPO

_SHA = re.compile(r"[a-f0-9]{40}\Z")


class ReleaseContinuityDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise ReleaseContinuityDenied("F139_RELEASE_PIN_" + reason)


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
    policy = inspect_policy(raw, deployed_source)
    need(policy["enabled"] is True, "RELEASE_POLICY_DISABLED")
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
        "existing_owner_policy_authorized": True,
        "native_development_only": True,
        "scientific_first_use": False,
        "new_dispatcher": False,
        "source_transition_granted": False,
    }
