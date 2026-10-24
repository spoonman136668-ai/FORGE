"""Bounded read-only continuity across protected research-only FORGE merges.

The original F139 controller remains the ONLY execution authority and retains
its exact source SHA in its immutable SQLite ledger. Unrelated protected research
evidence packages can advance without changing the controller runtime.

This is a narrow, fail-closed *file-delta* proof, NOT implicit approval to
change native workers, authentication, controller code, dependencies, policies,
or scientific first-use. All mutable and unknown paths remain blocked pending
the existing explicit owner source-transition acceptance.
"""
from __future__ import annotations

import re
from typing import Callable

REPOSITORY = "spoonman136668-ai/FORGE"
_SHA = re.compile(r"[a-f0-9]{40}\Z")
_RESEARCH_GO = re.compile(r"researchfeed/[A-Za-z0-9][A-Za-z0-9_-]*\.go\Z")
_RESEARCH_DOC = re.compile(r"docs/RSH-[0-9A-Za-z][0-9A-Za-z_.-]*\.md\Z")
_FSA_READONLY_TEST = re.compile(r"fsaservice/rsh[0-9][0-9a-z_-]*_readonly_bridge_test\.go\Z")
_RESEARCH_RECEIPT = re.compile(r"reference/research-originals/[0-9]{8}-[a-z0-9][a-z0-9_-]{0,63}-(?:raw-integrity-receipt|manifest)\.json\Z")
MAX_COMMITS = 80
MAX_CHANGED_FILES = 48
MAX_TOTAL_CHANGED_LINES = 7000


class SourceContinuityDenied(ValueError):
    pass


def require(ok: bool, label: str) -> None:
    if not ok:
        raise SourceContinuityDenied("F139_SOURCE_CONTINUITY_" + label)


def _sha(value: object) -> bool:
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def _research_only_path(path: object) -> bool:
    return isinstance(path, str) and (
        _RESEARCH_DOC.fullmatch(path) is not None
        or _RESEARCH_GO.fullmatch(path) is not None
        or _FSA_READONLY_TEST.fullmatch(path) is not None
        or _RESEARCH_RECEIPT.fullmatch(path) is not None
    )


def prove_protected_research_only_advance(
    get: Callable[[str], object], *, deployed_source: str,
    protected_source: str
) -> dict:
    """Return a bounded provenance receipt, not a new authority or SHA pin.

    Read-only GitHub GET must be owned by the current original F139 identity.
    No paths in f139/, scripts/, native worker workflows, policy files, module
    files, app code or hidden directories can qualify.
    """
    require(callable(get) and _sha(deployed_source) and
            _sha(protected_source) and deployed_source != protected_source,
            "SOURCE_SHA_INVALID")
    remote = get(f"repos/{REPOSITORY}/branches/main")
    require(isinstance(remote, dict) and remote.get("protected") is True
            and isinstance(remote.get("commit"), dict)
            and remote["commit"].get("sha") == protected_source,
            "PROTECTED_MAIN_MOVED_OR_UNPROTECTED")
    comparison = get(f"repos/{REPOSITORY}/compare/"
                     f"{deployed_source}...{protected_source}")
    require(isinstance(comparison, dict)
            and comparison.get("status") == "ahead"
            and type(comparison.get("ahead_by")) is int
            and 1 <= comparison["ahead_by"] <= MAX_COMMITS
            and comparison.get("behind_by") == 0
            and comparison.get("total_commits") == comparison["ahead_by"]
            and isinstance(comparison.get("merge_base_commit"), dict)
            and comparison["merge_base_commit"].get("sha") == deployed_source,
            "NOT_BOUNDED_FORWARD_ANCESTRY")
    commits = comparison.get("commits")
    require(isinstance(commits, list) and
            len(commits) == comparison["ahead_by"] and
            all(isinstance(commit, dict) and _sha(commit.get("sha"))
                for commit in commits) and
            len({commit["sha"] for commit in commits}) == len(commits)
            and commits[-1]["sha"] == protected_source,
            "COMMIT_HISTORY_TRUNCATED_OR_MOVED")
    files = comparison.get("files")
    require(isinstance(files, list)
            and 1 <= len(files) <= MAX_CHANGED_FILES,
            "DIFF_TRUNCATED_OR_EMPTY")
    paths = set()
    count = 0
    for f in files:
        require(isinstance(f, dict)
                and f.get("status") in ("added", "modified")
                and _research_only_path(f.get("filename"))
                and _sha(f.get("sha"))
                and type(f.get("changes")) is int
                and 1 <= f["changes"] <= 2000
                and isinstance(f.get("patch"), str)
                and 0 < len(f["patch"]) <= 120000,
                "RUNTIME_OR_UNTRUSTED_FILE_CHANGED")
        if _RESEARCH_RECEIPT.fullmatch(f["filename"]) is not None:
            # Immutable data-only custody receipts may be ADDED, never
            # rewritten or removed under a live owner source pin.
            require(f["status"] == "added",
                    "ORIGINAL_EVIDENCE_REWRITTEN")
        require(f["filename"] not in paths, "DUPLICATE_CHANGED_FILE")
        paths.add(f["filename"])
        count += f["changes"]
    require(count <= MAX_TOTAL_CHANGED_LINES, "EXCESSIVE_RESEARCH_DELTA")
    # Re-read the protected head to avoid an ambiguous moving ref.
    again = get(f"repos/{REPOSITORY}/branches/main")
    require(isinstance(again, dict) and
            again.get("protected") is True and
            isinstance(again.get("commit"), dict) and
            again["commit"].get("sha") == protected_source,
            "PROTECTED_HEAD_MOVED_DURING_ATTESTATION")
    return {
        "schema": "forge.f139.source-continuity.readonly.v1",
        "deployed_source": deployed_source,
        "protected_source": protected_source,
        "forward_commits": len(commits),
        "file_count": len(files),
        "changed_lines": count,
        "runtime_source_unchanged": True,
        "scientific_first_use": False,
        "new_controller": False,
        "source_transition_granted": False,
    }
