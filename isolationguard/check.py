#!/usr/bin/env python3
"""Reject new active-source coupling to private CKB-plane.

Only committed additions in executable/config source are inspected.
Historical provenance and policy prose can retain their original references.
This is defense-in-depth, not a substitute for independent code review.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

EXACT_REPO = "spoonman136668-ai/ckb-plane"
ACTIVE_SUFFIXES = {".go", ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx",
                   ".sh", ".ps1", ".yml", ".yaml", ".rb", ".rs",
                   ".bash", ".zsh", ".json", ".toml", ".sql"}
ACTIVE_NAMES = {"Dockerfile", "Makefile", "Justfile", "Procfile"}
HEX40 = re.compile(r"^[0-9a-f]{40}$")

class GateError(ValueError):
    pass

def run_git(root: pathlib.Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=root, capture_output=True,
                          text=True, encoding="utf-8", errors="strict",
                          check=False, timeout=30)
    if proc.returncode:
        raise GateError("GIT_NOT_QUALIFIED")
    return proc.stdout

def is_active(path: str) -> bool:
    if path.startswith(("docs/", "reference/", "archive/")):
        return False
    if path in ("isolationguard/check.py", "isolationguard/test_check.py"):
        # Adversarial fixtures contain the forbidden literal by design.
        # Both files require this same GitHub-hosted test and review.
        return False
    p = pathlib.PurePosixPath(path)
    if p.is_absolute() or ".." in p.parts:
        raise GateError("UNSAFE_SOURCE_PATH")
    return path.startswith((".github/workflows/", ".github/actions/")) or (
        p.suffix.lower() in ACTIVE_SUFFIXES or p.name in ACTIVE_NAMES
    )

def unsafe_line(added: str) -> bool:
    # Do not ban legitimate legacy "ckb_plane_role" metadata, or
    # documentation explaining *why* no controller link is allowed.
    # Normalize simple quote splitting and Python/JS unicode escapes.
    normalized = re.sub(r"\\(?:u002d|x2d)", "-", added, flags=re.I)
    normalized = re.sub(r"\\(?:u002f|x2f)", "/", normalized, flags=re.I)
    normalized = re.sub(r"[\\\"'\x60+\s]", "", normalized).lower()
    return EXACT_REPO in normalized

def audit_patch(patch: str) -> list[tuple[str, str]]:
    failures = []
    path = None
    have_header = False
    for line in patch.splitlines():
        if line.startswith("+++ "):
            have_header = True
            path = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("diff --git "):
            have_header = False
            path = None
        elif line.startswith("+") and not line.startswith("+++"):
            if not have_header or path is None:
                raise GateError("UNBOUND_PATCH_ADDITION")
            if is_active(path) and unsafe_line(line[1:]):
                failures.append((path, "PROHIBITED_PRIVATE_REPO_DEPENDENCY"))
    return failures

def verify_policy_files(root: pathlib.Path) -> None:
    expected = {
        "AGENTS.md": "FORGE MUST NOT connect to or depend on CKB-plane",
        "docs/ADR-0002-MIND-PALACE-ONLY-NO-CKB-DEPENDENCY.md":
            "FORGE must not connect to CKB-plane",
        "README.md": "FORGE must not connect to or depend on CKB-plane",
    }
    for path, literal in expected.items():
        p = root / path
        if not p.is_file() or literal not in p.read_text(encoding="utf-8"):
            raise GateError("MISSING_OPERATOR_BOUNDARY:" + path)
    # ISO-02: Old dispatchable cross-system workflow must be absent, not merely
    # unscheduled. Check every extant workflow, not only the newest patch.
    workflows = root / ".github" / "workflows"
    if not workflows.is_dir():
        raise GateError("MISSING_GITHUB_WORKFLOWS")
    legacy = workflows / "forge-ckb-s14-readonly-history.yml"
    if legacy.exists():
        raise GateError("LEGACY_CKB_WORKFLOW_NOT_RETIRED")
    for workflow in sorted(workflows.glob("*")):
        if workflow.is_file() and workflow.suffix in (".yml", ".yaml"):
            for line in workflow.read_text(encoding="utf-8").splitlines():
                if unsafe_line(line):
                    raise GateError("ACTIVE_PRIVATE_REPO_WORKFLOW:" + workflow.name)
    # The historical Go CLI is intentionally retained only as a guaranteed
    # offline, fail-closed stub. The historical library is not an entrypoint.
    legacy_cli = root / "cmd" / "forge-ckb-s14-history" / "main.go"
    if not legacy_cli.is_file():
        raise GateError("MISSING_RETIRED_COMMAND_SENTINEL")
    body = legacy_cli.read_text(encoding="utf-8")
    if ("const FORGE_CKB_LEGACY_COMMAND_RETIRED = true" not in body or
        "return errRetired" not in body or
        "ckbhistory" in body or "http." in body or "InspectS14(" in body):
        raise GateError("LEGACY_CKB_COMMAND_NOT_FAIL_CLOSED")

def audit_repo(root: pathlib.Path) -> list[tuple[str, str]]:
    verify_policy_files(root)
    head = run_git(root, "rev-parse", "HEAD").strip()
    # A synthetic PR merge and protected-main merge use the first parent
    # as the target branch; a branch push uses the immediately prior commit.
    base = run_git(root, "rev-parse", "HEAD^1").strip()
    if not (HEX40.fullmatch(head) and HEX40.fullmatch(base) and head != base):
        raise GateError("SOURCE_IDENTITY_UNQUALIFIED")
    run_git(root, "merge-base", "--is-ancestor", base, head)
    run_git(root, "diff", "--check", base, head)
    patch = run_git(root, "diff", "--no-ext-diff", "--no-color",
                    "--no-renames", "--unified=0", base, head, "--")
    return audit_patch(patch)

def main() -> int:
    root = pathlib.Path(__file__).resolve().parents[1]
    try:
        failures = audit_repo(root)
    except (GateError, OSError, UnicodeError, subprocess.TimeoutExpired) as exc:
        print("FORGE_ISOLATION_GATE=BLOCKED " + str(exc), file=sys.stderr)
        return 1
    if failures:
        for path, reason in failures:
            print("FORGE_ISOLATION_GATE=BLOCKED " + path + " " + reason,
                  file=sys.stderr)
        return 1
    print("FORGE_ISOLATION_GATE=PASS")
    print("FORGE_NEW_PRIVATE_CKB_DEPENDENCIES=ZERO")
    print("MIND_PALACE_ONLY_ADVISORY_BOUNDARY=PRESERVED")
    return 0

if __name__ == "__main__":
    sys.exit(main())
