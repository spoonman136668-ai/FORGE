"""Read-only original PR provenance shared by FORGE's existing Go qualifiers.

No dispatch, authorization, workflow mutation, network access, secret, cache or
test filtering. Generic source PRs cannot rewrite original Go CI harnesses.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
from typing import Callable

REPO = "spoonman136668-ai/FORGE"
FROZEN_SCOPES = {
    "engineering/rar-g141-parallel-complete-go-suites-20261108": (
        "1a1ba98dc821131d8a14182f72243540d008aaae",
        {
            ".github/workflows/qualify.yml",
            "scripts/check_rar_g141_parallel_go.py",
        },
    ),
    "engineering/rar-g144-windows-native-go-vet-concurrent-20261108": (
        "0ea00f9b4587f5508dff39b65de2574f0b4fe681",
        {
            ".github/workflows/qualify.yml",
            "scripts/check_rar_g141_parallel_go.py",
            "scripts/check_rar_g144_windows_go.py",
        },
    ),
    "engineering/g145-generic-pr-original-qualification-20261108": (
        "69421a9d82bfb7b374d6635d3c60d7e41bfaf3b2",
        {
            "docs/FORGE-G145-GENERIC-PR-QUALIFICATION.md",
            "scripts/check_rar_g141_parallel_go.py",
            "scripts/check_rar_g144_windows_go.py",
            "scripts/check_rar_g145_pr_scope.py",
        },
    ),
    "engineering/rar-g148-main-safe-go-cache-20261108": (
        "ab2d239e2d079d2500ec5d91b253c11e6bd3b132",
        {
            "docs/FORGE-G148-GO-CACHE-RELEASE.md",
            ".github/workflows/qualify.yml",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
        },
    ),
    "engineering/rar-g156-dynamic-main-cache-release-20261108": (
        "a62f469de1d5316c04d063246c30a5812bc8857d",
        {
            "docs/FORGE-G156-DYNAMIC-MAIN-GO-CACHE-RELEASE.md",
            ".github/workflows/qualify.yml",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    "engineering/rar-g158-optional-helper-compat-20261108": (
        "6a9bd9b87bc8d12cb0e8237c1da606aecf28c39b",
        {
            "docs/FORGE-G158-OPTIONAL-HELPER-COMPAT.md",
            ".github/workflows/qualify.yml",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    "engineering/rar-g160-partial-go-diagnostics-20261109": (
        "21b8649569bd9577c325da1ea99ecac81ff5df89",
        {
            "docs/FORGE-G160-G141-PARTIAL-GO-DIAGNOSTICS.md",
            "scripts/check_rar_g141_parallel_go.py",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    "engineering/rar-g161-verified-pr-ancestry-20261109": (
        "ad9026d2e551b054fc944d536ded37fe20a1aaa4",
        {
            "docs/FORGE-G161-G145-PR-ANCESTRY.md",
            ".github/workflows/qualify.yml",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    "engineering/rar-g166-f23-race-profile-20261109": (
        "0e122eb8e571ddddee1dea4168cf18cfc7dc019d",
        {
            "docs/FORGE-G166-PINNED-F23-RACE-PROFILE.md",
            ".github/workflows/qualify.yml",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
}


def is_sha(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) is not None


def generic_paths_safe(paths: list[str]) -> bool:
    if not paths or len(paths) > 128 or len(set(paths)) != len(paths):
        return False
    for path in paths:
        if (
            not isinstance(path, str)
            or not path
            or path.startswith("/")
            or "\\" in path
            or any(part in ("", ".", "..") for part in path.split("/"))
            or any(ord(ch) < 32 for ch in path)
            or path.startswith(".github/workflows/")
            or path.startswith("scripts/check_rar_")
        ):
            return False
    return True


def negative_controls() -> None:
    valid = ["docs/EUREKA.md", "nativediscovery/f6_repair.go"]
    invalid = [
        [],
        ["nativediscovery/f6_repair.go"] * 2,
        ["nativediscovery/f6_repair.go"] * 129,
        [".github/workflows/qualify.yml"],
        ["scripts/check_rar_g141_parallel_go.py"],
        ["scripts/check_rar_g144_windows_go.py"],
        ["scripts/check_rar_g999_new_harness.py"],
        ["../unsafe.go"],
        ["/unsafe.go"],
        ["safe//unsafe.go"],
        ["safe\\unsafe.go"],
    ]
    if not generic_paths_safe(valid) or any(generic_paths_safe(x) for x in invalid):
        raise ValueError("G145_ADMISSION_NEGATIVE_CONTROL_FAILED")


def github_event_base(head_sha: str) -> str:
    """Read exact GitHub-hosted pull request event identity. No remote fetch."""
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if (
        not event_path
        or not Path(event_path).is_file()
        or Path(event_path).stat().st_size > (1 << 20)
    ):
        raise ValueError("G145_EVENT_PATH_INVALID")
    try:
        payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
        request = payload["pull_request"]
        head, base = request["head"], request["base"]
        base_sha = base["sha"]
        if (
            not is_sha(base_sha)
            or not is_sha(head_sha)
            or head["sha"] != head_sha
            or base["ref"] != "main"
            or base["repo"]["full_name"] != REPO
            or head["repo"]["full_name"] != REPO
            or head["ref"] != os.environ.get("GITHUB_HEAD_REF")
            or os.environ.get("GITHUB_BASE_REF") != "main"
        ):
            raise ValueError("G145_EVENT_IDENTITY_MISMATCH")
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise ValueError("G145_EVENT_IDENTITY_INVALID") from exc
    return base_sha


def admit_original_pr(head_sha: str, git: Callable[..., str]) -> str:
    """Engineering CI admission only; never research, merge or FSA authority."""
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request" or not callable(git):
        raise ValueError("G145_NOT_GITHUB_PR")
    branch = os.environ.get("GITHUB_HEAD_REF", "")
    base_sha = github_event_base(head_sha)
    if branch in FROZEN_SCOPES:
        frozen_base, expected = FROZEN_SCOPES[branch]
        try:
            changed = git(
                "diff", "--no-renames", "--name-only", frozen_base, head_sha
            ).splitlines()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise ValueError("G145_FROZEN_SCOPE_SOURCE_UNAVAILABLE") from exc
        if base_sha != frozen_base or set(changed) != expected or len(changed) != len(expected):
            raise ValueError("G145_FROZEN_BRANCH_SCOPE_CHANGED")
        return "FROZEN_G141_G144_OR_G145_HARNESS_DEVELOPMENT"
    # No arbitrary external PR can edit the runner's workflow or source guards.
    # The GitHub event's base must be a locally available exact ancestor of HEAD;
    # this fails closed for stale/unrelated checkouts, requiring a source sync.
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        changed = git(
            "diff", "--no-renames", "--name-only", base_sha, head_sha
        ).splitlines()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_GENERIC_PR_BASE_SOURCE_UNAVAILABLE") from exc
    if ancestor != base_sha or not generic_paths_safe(changed):
        raise ValueError("G145_GENERIC_PR_CHANGED_OR_UNRELATED_HARNESS")
    return "EXACT_MAIN_ANCESTOR_GENERIC_SOURCE_PR"
