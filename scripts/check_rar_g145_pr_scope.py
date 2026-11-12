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
HYBRID_RELEASE_BRANCH = "release/f139-hybrid-qualified-worker-governance-20261109"
HYBRID_RELEASE_PR = 1642
HYBRID_RELEASE_ANCHOR = "0e122eb8e571ddddee1dea4168cf18cfc7dc019d"
HYBRID_WORKER_PATH = ".github/workflows/forge-f139-development-worker.yml"
HYBRID_WORKER_BEFORE = "8eab7972ba1b30eabf1e38477aff60b598cdeb2f"
HYBRID_WORKER_AFTER = "74dd90e6d71da6b53898c7a80d5362f1b0e6af27"
V41_PAUSE_BRANCH = "engineering/f139-v41-original-pause-backup-resume-20261112"
V41_PAUSE_PR = 1735
V41_PAUSE_BASE = "89f283492fd7ef171b4482b78baae88772880e51"
V41_PAUSE_WORKFLOW = ".github/workflows/f139-g54-v9-owner-cutover.yml"
V41_PAUSE_BEFORE = "5858519fbd335445d5a4518bb3c2fcc4d82b4b5e"
V41_PAUSE_AFTER = "b0dfd96bb86cdb834dd908a7518027d12cc9ad95"
V41_PAUSE_RESULT = "EXACT_PR1735_OWNER_SAME_TASK_PAUSE_BACKUP_RESUME_ONLY"
V41_PAUSE_FILES = frozenset({
    V41_PAUSE_WORKFLOW,
    "f139/v41_owner_pause_backup_resume.ps1",
    "f139/nci04_v41_owner_cold_backup.py",
    "f139/test_nci04_v41_owner_cold_backup.py",
    "docs/F139-V41-ORIGINAL-HOST-BACKUP-ONLY.md",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
})

V41_BACKUP_BRANCH = "dev/f139-v41-original-cold-backup-only-20261112"
V41_BACKUP_PR = 1734
V41_BACKUP_BASE = "2ee1d2e3894558a92231e5922980f8c96e731b36"
V41_BACKUP_WORKFLOW = ".github/workflows/f139-g54-v9-owner-cutover.yml"
V41_BACKUP_BEFORE = "fd5de64d7a8b44b6e8ac28a98c0c4fc33afbd9f3"
V41_BACKUP_AFTER = "5858519fbd335445d5a4518bb3c2fcc4d82b4b5e"
V41_BACKUP_RESULT = "EXACT_PR1734_OWNER_BACKUP_ONLY_WORKFLOW_SCOPE"
V41_BACKUP_FILES = frozenset({
    V41_BACKUP_WORKFLOW,
    "f139/nci04_v41_owner_cold_backup.py",
    "f139/test_nci04_v41_owner_cold_backup.py",
    "docs/F139-V41-ORIGINAL-HOST-BACKUP-ONLY.md",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
})

V41_STATUS_BRANCH = "dev/f139-v41-original-locked-readonly-acceptance-20261112"
V41_STATUS_PR = 1731
V41_STATUS_BASE = "3edc2f930d915fddf040effda68b1a4770a4bb32"
V41_STATUS_WORKFLOW = ".github/workflows/f139-g54-v9-owner-cutover.yml"
V41_STATUS_BEFORE = "c8e6616d8203d27caccdb06084862bf8cfdbbd4c"
V41_STATUS_AFTER = "fd5de64d7a8b44b6e8ac28a98c0c4fc33afbd9f3"
V41_STATUS_RESULT = "EXACT_PR1731_V41_READONLY_OWNER_SCOPE_ONLY"
V41_STATUS_FILES = frozenset({
    V41_STATUS_WORKFLOW,
    "f139/nci04_v41_original_owner_status.py",
    "f139/test_nci04_v41_original_owner_status.py",
    "f139/test_v40_readonly_workflow_scope.py",
    "docs/F139-V41-ORIGINAL-LOCKED-READONLY-STATUS.md",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
})

FROZEN_SCOPES = {
    # Exact owner-approved V40 handoff engineering source; no live approval inferred.
    'engineering/f139-v40-explicit-owner-handoff-20261109': (
        'feb75e7490256a6930698742a43b8d12384fbbca',
        {'docs/F139-V40-EXPLICIT-OWNER-HANDOFF.md', 'f139/nci04_v40_guarded_owner_handoff.py', '.github/workflows/f139-v38-original-owner-release.yml', 'f139/test_nci04_v38_source_transition.py', 'f139/nci04_v32_original_owner_transition_cli.py', 'scripts/check_rar_g148_go_cache.py', 'scripts/check_rar_g145_pr_scope.py', 'f139/check_v40_release_source.py', 'scripts/check_rar_g156_dynamic_base_cache.py', 'f139/test_nci04_v40_owner_handoff.py', 'f139/nci04_v40_owner_handoff_approval.py'},
    ),
    # Operator-authorized source-bound build and disposable-copy qualification only.
    'engineering/f139-v40-source-bound-copy-qualification-20261109': (
        'fa1a0477996bf1fb0568290a3692c57ee8b29b91',
        {'docs/F139-V40-SOURCE-BOUND-COPY-QUALIFICATION.md', 'f139/test_v40_readonly_workflow_scope.py', 'scripts/check_rar_g145_pr_scope.py', '.github/workflows/f139-g54-v9-owner-cutover.yml', 'scripts/check_rar_g148_go_cache.py', 'scripts/check_rar_g156_dynamic_base_cache.py'},
    ),
    # Operator-authorized exact V40 read-only invocation qualification.
    'engineering/f139-v40-qualified-readonly-route-20261109': (
        '32de33753c874102de9672d2768e4b7c0b866b25',
        {'scripts/check_rar_g145_pr_scope.py', 'f139/test_v40_readonly_workflow_scope.py', '.github/workflows/f139-g54-v9-owner-cutover.yml', 'docs/F139-V40-QUALIFIED-READONLY-ROUTE.md', 'scripts/check_rar_g148_go_cache.py', 'scripts/check_rar_g156_dynamic_base_cache.py'},
    ),
    # Explicit operator-authorized governance qualification, not a generic
    # workflow/harness allowance. The worker itself is a separate PR below.
    "engineering/f139-exact-worker-release-scope-20261109": (
        "0e122eb8e571ddddee1dea4168cf18cfc7dc019d",
        {
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
            "f139/test_hybrid_workflow_release_scope.py",
            "docs/F139-EXACT-HYBRID-WORKFLOW-RELEASE.md",
        },
    ),
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
    hybrid_release_negative_controls()
    v41_status_negative_controls()
    v41_backup_negative_controls()
    v41_pause_negative_controls()


def admit_hybrid_workflow_release(head_sha: str, base_sha: str,
                                  request: dict, git: Callable[..., str]) -> str:
    """Qualify only #1642's exact old-to-new worker blob, never release it.

    Event head/base repository/ref identities are checked by github_event_base
    before this helper is called. No other file, harness, workflow, source
    allowlist, permission or task transition is admitted by this route.
    """
    if (not is_sha(head_sha) or not is_sha(base_sha)
            or not isinstance(request, dict)
            or not isinstance(request.get("user"), dict)
            or request.get("number") != HYBRID_RELEASE_PR
            or type(request.get("number")) is not int
            or request.get("user", {}).get("login") != "spoonman136668-ai"
            or request.get("author_association") != "OWNER"):
        raise ValueError("G145_HYBRID_RELEASE_ORIGINAL_PR_REQUIRED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        anchor = git("merge-base", HYBRID_RELEASE_ANCHOR, base_sha)
        changed = git("diff", "--no-renames", "--name-only", base_sha, head_sha).splitlines()
        before = git("ls-tree", base_sha, "--", HYBRID_WORKER_PATH)
        after = git("ls-tree", head_sha, "--", HYBRID_WORKER_PATH)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_HYBRID_RELEASE_SOURCE_UNAVAILABLE") from exc
    def entry(blob):
        return "100644 blob " + blob + "\t" + HYBRID_WORKER_PATH
    if (ancestor != base_sha or anchor != HYBRID_RELEASE_ANCHOR
            or changed != [HYBRID_WORKER_PATH]
            or before != entry(HYBRID_WORKER_BEFORE)
            or after != entry(HYBRID_WORKER_AFTER)):
        raise ValueError("G145_HYBRID_RELEASE_EXACT_SOURCE_REQUIRED")
    return "EXACT_PR1642_HYBRID_WORKER_BLOB_QUALIFICATION_ONLY"


def hybrid_release_negative_controls() -> None:
    """Run in both unchanged original full-Go qualifiers, without network."""
    head, base = "c" * 40, "b" * 40
    request = {"number": HYBRID_RELEASE_PR,
               "user": {"login": "spoonman136668-ai"},
               "author_association": "OWNER"}
    def git(*args):
        if args == ("merge-base", base, head):
            return base
        if args == ("merge-base", HYBRID_RELEASE_ANCHOR, base):
            return HYBRID_RELEASE_ANCHOR
        if args == ("diff", "--no-renames", "--name-only", base, head):
            return HYBRID_WORKER_PATH
        if args in (("ls-tree", base, "--", HYBRID_WORKER_PATH),
                    ("ls-tree", head, "--", HYBRID_WORKER_PATH)):
            blob = HYBRID_WORKER_BEFORE if args[1] == base else HYBRID_WORKER_AFTER
            return "100644 blob " + blob + "\t" + HYBRID_WORKER_PATH
        raise AssertionError("unexpected frozen source read")
    admit_hybrid_workflow_release(head, base, request, git)
    bad_reads = (
        (("merge-base", base, head), "f" * 40),
        (("merge-base", HYBRID_RELEASE_ANCHOR, base), "f" * 40),
        (("diff", "--no-renames", "--name-only", base, head),
         HYBRID_WORKER_PATH + "\nscripts/check_rar_g145_pr_scope.py"),
        (("ls-tree", base, "--", HYBRID_WORKER_PATH),
         "100644 blob " + "f" * 40 + "\t" + HYBRID_WORKER_PATH),
        (("ls-tree", head, "--", HYBRID_WORKER_PATH),
         "100644 blob " + "f" * 40 + "\t" + HYBRID_WORKER_PATH),
        (("ls-tree", head, "--", HYBRID_WORKER_PATH),
         "100755 blob " + HYBRID_WORKER_AFTER + "\t" + HYBRID_WORKER_PATH),
    )
    for call, result in bad_reads:
        def changed_git(*args):
            return result if args == call else git(*args)
        try:
            admit_hybrid_workflow_release(head, base, request, changed_git)
        except ValueError:
            continue
        raise ValueError("G145_HYBRID_RELEASE_NEGATIVE_FAILED")
    try:
        admit_hybrid_workflow_release(head, base, dict(request, number=1643), git)
    except ValueError:
        return
    raise ValueError("G145_HYBRID_RELEASE_PR_NEGATIVE_FAILED")



def admit_v41_owner_pause(head_sha: str, base_sha: str,
                          request: dict, git: Callable[..., str]) -> str:
    """Owner PR#1735 source admission, not maintenance or deployment authority.

    Verify exact original base, owner-authored PR, 8 frozen files and the
    before/after G54 workflow blobs. No generic workflow or harness edit.
    """
    if (not is_sha(head_sha) or base_sha != V41_PAUSE_BASE
            or type(request) is not dict
            or type(request.get("number")) is not int
            or request["number"] != V41_PAUSE_PR
            or request.get("user", {}).get("login") != "spoonman136668-ai"
            or request.get("author_association") != "OWNER"):
        raise ValueError("G145_V41_PAUSE_EXACT_OWNER_PR_REQUIRED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        changed = git("diff", "--no-renames", "--name-only",
                      base_sha, head_sha).splitlines()
        before = git("ls-tree", base_sha, "--", V41_PAUSE_WORKFLOW)
        after = git("ls-tree", head_sha, "--", V41_PAUSE_WORKFLOW)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_V41_PAUSE_PINNED_SOURCE_MISSING") from exc
    if (ancestor != base_sha
            or len(changed) != len(V41_PAUSE_FILES)
            or len(set(changed)) != len(changed)
            or set(changed) != V41_PAUSE_FILES
            or before != "100644 blob " + V41_PAUSE_BEFORE + "\t" + V41_PAUSE_WORKFLOW
            or after != "100644 blob " + V41_PAUSE_AFTER + "\t" + V41_PAUSE_WORKFLOW):
        raise ValueError("G145_V41_PAUSE_EXACT_WORKFLOW_OR_FILES_DRIFT")
    return V41_PAUSE_RESULT


def v41_pause_negative_controls() -> None:
    base, head = V41_PAUSE_BASE, "a"*40
    owner = {"number": V41_PAUSE_PR,
             "user": {"login": "spoonman136668-ai"},
             "author_association": "OWNER"}
    def read(*args):
        if args == ("merge-base", base, head):
            return base
        if args == ("diff", "--no-renames", "--name-only", base, head):
            return "\n".join(sorted(V41_PAUSE_FILES))
        if args == ("ls-tree", base, "--", V41_PAUSE_WORKFLOW):
            return "100644 blob " + V41_PAUSE_BEFORE + "\t" + V41_PAUSE_WORKFLOW
        if args == ("ls-tree", head, "--", V41_PAUSE_WORKFLOW):
            return "100644 blob " + V41_PAUSE_AFTER + "\t" + V41_PAUSE_WORKFLOW
        raise AssertionError("unexpected original source lookup")
    if admit_v41_owner_pause(head, base, owner, read) != V41_PAUSE_RESULT:
        raise ValueError("G145_V41_PAUSE_POSITIVE_CONTROL_FAILED")
    def reject(req=owner, candidate_base=base, override=None):
        def source(*args):
            return override[1] if override and args == override[0] else read(*args)
        try:
            admit_v41_owner_pause(head, candidate_base, req, source)
        except ValueError:
            return
        raise ValueError("G145_V41_PAUSE_NEGATIVE_ADMITTED")
    reject(dict(owner, number=1734))
    reject(dict(owner, user={"login": "other"}))
    reject(dict(owner, author_association="CONTRIBUTOR"))
    reject(candidate_base="f"*40)
    reject(override=(("merge-base", base, head), "f"*40))
    reject(override=(("diff", "--no-renames", "--name-only", base, head),
                     V41_PAUSE_WORKFLOW))
    reject(override=(("ls-tree", base, "--", V41_PAUSE_WORKFLOW),
                     "100644 blob " + "f"*40 + "\t" + V41_PAUSE_WORKFLOW))
    reject(override=(("ls-tree", head, "--", V41_PAUSE_WORKFLOW),
                     "100644 blob " + "f"*40 + "\t" + V41_PAUSE_WORKFLOW))
    reject(override=(("ls-tree", head, "--", V41_PAUSE_WORKFLOW),
                     "100755 blob " + V41_PAUSE_AFTER + "\t" + V41_PAUSE_WORKFLOW))


def admit_v41_owner_backup(head_sha: str, base_sha: str,
                           request: dict, git: Callable[..., str]) -> str:
    """Exact owner PR #1734 admission only; never authorizes maintenance.

    Pin old/new G54 workflow bytes, PR number/owner, exact protected base,
    and the entire seven-file change set. A generic workflow rewrite remains
    inadmissible. No task runner, science, cutover or backup is executed here.
    """
    if (not is_sha(head_sha) or base_sha != V41_BACKUP_BASE
            or type(request) is not dict
            or type(request.get("number")) is not int
            or request["number"] != V41_BACKUP_PR
            or request.get("user", {}).get("login") != "spoonman136668-ai"
            or request.get("author_association") != "OWNER"):
        raise ValueError("G145_V41_BACKUP_EXACT_OWNER_PR_REQUIRED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        changed = git("diff", "--no-renames", "--name-only",
                      base_sha, head_sha).splitlines()
        before = git("ls-tree", base_sha, "--", V41_BACKUP_WORKFLOW)
        after = git("ls-tree", head_sha, "--", V41_BACKUP_WORKFLOW)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_V41_BACKUP_SOURCE_MISSING") from exc
    expected_before = ("100644 blob " + V41_BACKUP_BEFORE + "\t" +
                       V41_BACKUP_WORKFLOW)
    expected_after = ("100644 blob " + V41_BACKUP_AFTER + "\t" +
                      V41_BACKUP_WORKFLOW)
    if (ancestor != base_sha
            or len(changed) != len(V41_BACKUP_FILES)
            or len(set(changed)) != len(changed)
            or set(changed) != V41_BACKUP_FILES
            or before != expected_before or after != expected_after):
        raise ValueError("G145_V41_BACKUP_EXACT_SOURCE_OR_BLOB_REQUIRED")
    return V41_BACKUP_RESULT


def v41_backup_negative_controls() -> None:
    base, head = V41_BACKUP_BASE, "a" * 40
    owner = {"number": V41_BACKUP_PR,
             "user": {"login": "spoonman136668-ai"},
             "author_association": "OWNER"}
    def original(*args):
        if args == ("merge-base", base, head):
            return base
        if args == ("diff", "--no-renames", "--name-only", base, head):
            return "\n".join(sorted(V41_BACKUP_FILES))
        if args == ("ls-tree", base, "--", V41_BACKUP_WORKFLOW):
            return ("100644 blob " + V41_BACKUP_BEFORE +
                    "\t" + V41_BACKUP_WORKFLOW)
        if args == ("ls-tree", head, "--", V41_BACKUP_WORKFLOW):
            return ("100644 blob " + V41_BACKUP_AFTER +
                    "\t" + V41_BACKUP_WORKFLOW)
        raise AssertionError("unexpected git read")
    if admit_v41_owner_backup(head, base, owner, original) != V41_BACKUP_RESULT:
        raise ValueError("G145_V41_BACKUP_POSITIVE_NEGATIVE_CONTROL")
    def must_reject(req, start, overridden=None):
        def source(*args):
            if overridden and args == overridden[0]:
                return overridden[1]
            return original(*args)
        try:
            admit_v41_owner_backup(head, start, req, source)
        except ValueError:
            return
        raise ValueError("G145_V41_BACKUP_BAD_PR_OR_SOURCE_ACCEPTED")
    must_reject(dict(owner, number=1735), base)
    must_reject(dict(owner, author_association="CONTRIBUTOR"), base)
    must_reject(dict(owner, user={"login": "other"}), base)
    must_reject(owner, "f" * 40)
    must_reject(owner, base, (("merge-base", base, head), "f" * 40))
    must_reject(owner, base, (("diff", "--no-renames", "--name-only", base, head),
                             V41_BACKUP_WORKFLOW))
    must_reject(owner, base, (("ls-tree", head, "--", V41_BACKUP_WORKFLOW),
                             "100644 blob " + "f" * 40 + "\t" + V41_BACKUP_WORKFLOW))
    must_reject(owner, base, (("ls-tree", head, "--", V41_BACKUP_WORKFLOW),
                             "100755 blob " + V41_BACKUP_AFTER +
                             "\t" + V41_BACKUP_WORKFLOW))


def admit_v41_status(head_sha: str, base_sha: str,
                     request: dict, git: Callable[..., str]) -> str:
    """One original-owner-authored #1731 PR; no general workflow admission.

    Pin both the old and candidate workflow blob. The one inserted step is
    GET/query-only original owner evidence, never a task controller or release.
    This is ENGINEERING CI permission only, not execution or owner approval.
    """
    if (not is_sha(head_sha) or base_sha != V41_STATUS_BASE
            or type(request) is not dict
            or type(request.get("number")) is not int
            or request["number"] != V41_STATUS_PR
            or request.get("user", {}).get("login") != "spoonman136668-ai"
            or request.get("author_association") != "OWNER"):
        raise ValueError("G145_V41_EXACT_OWNER_PR_AND_BASE_REQUIRED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        changed = git("diff", "--no-renames", "--name-only",
                      base_sha, head_sha).splitlines()
        before = git("ls-tree", base_sha, "--", V41_STATUS_WORKFLOW)
        after = git("ls-tree", head_sha, "--", V41_STATUS_WORKFLOW)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_V41_PINNED_SOURCE_UNREADABLE") from exc
    if (ancestor != base_sha
            or len(changed) != len(V41_STATUS_FILES)
            or len(set(changed)) != len(changed)
            or set(changed) != V41_STATUS_FILES
            or before != "100644 blob " + V41_STATUS_BEFORE + "\t" + V41_STATUS_WORKFLOW
            or after != "100644 blob " + V41_STATUS_AFTER + "\t" + V41_STATUS_WORKFLOW):
        raise ValueError("G145_V41_EXACT_WORKFLOW_BLOB_OR_FILES_DRIFT")
    return V41_STATUS_RESULT


def v41_status_negative_controls() -> None:
    base, head = V41_STATUS_BASE, "a"*40
    owner = {"number": V41_STATUS_PR,
             "user": {"login": "spoonman136668-ai"},
             "author_association": "OWNER"}
    def git(*args):
        if args == ("merge-base", base, head):
            return base
        if args == ("diff", "--no-renames", "--name-only", base, head):
            return "\n".join(sorted(V41_STATUS_FILES))
        if args == ("ls-tree", base, "--", V41_STATUS_WORKFLOW):
            return "100644 blob " + V41_STATUS_BEFORE + "\t" + V41_STATUS_WORKFLOW
        if args == ("ls-tree", head, "--", V41_STATUS_WORKFLOW):
            return "100644 blob " + V41_STATUS_AFTER + "\t" + V41_STATUS_WORKFLOW
        raise AssertionError("unexpected frozen source lookup")
    if admit_v41_status(head, base, owner, git) != V41_STATUS_RESULT:
        raise ValueError("G145_V41_STATUS_POSITIVE_CONTROL_FAILED")
    bad = (
        (dict(owner, number=1732), None, None),
        (dict(owner, author_association="CONTRIBUTOR"), None, None),
        (dict(owner, user={"login":"other"}), None, None),
        (owner, "f"*40, None),
        (owner, None, (("merge-base", base, head), "f"*40)),
        (owner, None, (("diff", "--no-renames", "--name-only", base, head),
                        "scripts/check_rar_g145_pr_scope.py")),
        (owner, None, (("ls-tree", base, "--", V41_STATUS_WORKFLOW),
                        "100644 blob " + "f"*40 + "\t" + V41_STATUS_WORKFLOW)),
        (owner, None, (("ls-tree", head, "--", V41_STATUS_WORKFLOW),
                        "100644 blob " + "f"*40 + "\t" + V41_STATUS_WORKFLOW)),
        (owner, None, (("ls-tree", head, "--", V41_STATUS_WORKFLOW),
                        "100755 blob " + V41_STATUS_AFTER + "\t" + V41_STATUS_WORKFLOW)),
    )
    for request, new_base, replacement in bad:
        def altered(*args):
            return replacement[1] if replacement and args == replacement[0] else git(*args)
        try:
            admit_v41_status(head, base if new_base is None else new_base,
                             request, altered)
        except ValueError:
            continue
        raise ValueError("G145_V41_STATUS_NEGATIVE_ACCEPTED")


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
    if branch == V41_PAUSE_BRANCH:
        request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                             .read_text(encoding="utf-8"))["pull_request"]
        return admit_v41_owner_pause(head_sha, base_sha, request, git)
    if branch == V41_BACKUP_BRANCH:
        request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                             .read_text(encoding="utf-8"))["pull_request"]
        return admit_v41_owner_backup(head_sha, base_sha, request, git)
    if branch == V41_STATUS_BRANCH:
        payload = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        return admit_v41_status(head_sha, base_sha, payload["pull_request"], git)
    if branch == HYBRID_RELEASE_BRANCH:
        payload = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        request = payload["pull_request"]
        if payload.get("number") != HYBRID_RELEASE_PR:
            raise ValueError("G145_HYBRID_RELEASE_ORIGINAL_PR_REQUIRED")
        return admit_hybrid_workflow_release(head_sha, base_sha, request, git)
    if branch in {'engineering/f139-v40-explicit-owner-handoff-20261109', 'engineering/f139-v40-qualified-readonly-route-20261109', 'engineering/f139-v40-source-bound-copy-qualification-20261109'}:
        request = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text(encoding='utf-8'))['pull_request']
        if (request.get('user', {}).get('login') != 'spoonman136668-ai'
                or request.get('author_association') != 'OWNER'):
            raise ValueError('G145_V40_ORIGINAL_OWNER_PR_REQUIRED')
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
