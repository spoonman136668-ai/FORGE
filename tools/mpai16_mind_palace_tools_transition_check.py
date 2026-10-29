"""MP-AI16: fail-closed MP #175/#176/#177 tools-tree transition custody.

No FORGE controller, scheduler, Mind-Palace accepted main, memory writer or
production setting is changed. Original Windows runner authenticates PR source
identities, recomputes all relevant actual Git tree SHA1 objects, verifies
scheduled poll guard hasn't relaxed other protected identity/no-write fences,
and disposes the unconnected source repository. Dev/test evidence only.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

REMOTE = "https://github.com/spoonman136668-ai/Mind-Palace.git"
MAIN = "f31e4203892730ddbe24d44ce5674f5678d498aa"
PIN_OLD = "0142060579dfd1c7c1b8f73678ec8afe903b3573"
PIN_AFTER_175 = "a081fa108b6f4652d76c2aa188a6e6808a5a55a9"
PIN_AFTER_177_ONLY = "61e0a89f105c03a9d8590297ab65333b8b37940e"
PIN_FINAL = "e6e290d2fc77112769a0480d354a2c56be97c6d6"
P175 = ("review/mpai-usage-continuity-20261029",
        "638bc9b2883c6b01f81383a5c4afa87738641047",
        "mindpalace_readonly.py", "085e00c7bfc0d9f724874c93c75b7c4a79040dc0")
P177 = ("proposal/mpai13-feedback-review-handoff-20261029",
        "f79462d25629bc09be87f3c2b64d36b365fb0335",
        "mindpalace_mcp.py", "3a9cb7c41fd7ebbf96800d956589b422fc7b0fba")
GUARD_SCRIPT = "efee36f895d9163f68cd88b372b27897557a1e6f"
SCHEMAS = "3a88cdabbe11d4cd8f95a074860f08845b1cce4a"
FAIL_MARKER = "MPAI16_TRANSITION_PROTECTION_FAILURE"


def verify(ok: bool, code: str) -> None:
    if not ok:
        raise RuntimeError(FAIL_MARKER + "_" + code)


def git(*args: str, timeout: int = 90) -> bytes:
    proc = subprocess.run(["git", *args], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=timeout)
    verify(proc.returncode == 0, "GIT_OPERATION")
    return proc.stdout.strip()


def tree_digest(items: list[tuple[bytes, bytes, str]], changes: dict[bytes, str]) -> str:
    encoded = bytearray()
    for mode, path, identity in sorted(items, key=lambda item: item[1]):
        digest = changes.get(path, identity)
        verify(re.fullmatch("[0-9a-f]{40}", digest) is not None,
               "TREE_ENTRY_HEX")
        encoded.extend(mode + b" " + path + b"\x00" + bytes.fromhex(digest))
    raw = bytes(encoded)
    return hashlib.sha1(b"tree " + str(len(raw)).encode("ascii") + b"\x00" + raw).hexdigest()


def parse_ls_tree(raw: bytes) -> list[tuple[bytes, bytes, str]]:
    result = []
    for line in raw.split(b"\x00"):
        if not line:
            continue
        try:
            meta, path = line.split(b"\t", 1)
            mode, kind, sha = meta.split(b" ")
            sha_text = sha.decode("ascii")
            verify(kind in (b"blob", b"tree") and
                   re.fullmatch("[0-9a-f]{40}", sha_text) is not None,
                   "TREE_ENTRY_CONTRACT")
        except (ValueError, UnicodeError) as exc:
            raise RuntimeError(FAIL_MARKER + "_TREE_PARSE") from exc
        # The original tools/ tree has only flat files.
        verify(kind == b"blob" and mode == b"100644", "UNPLANNED_TOOL_DIRECTORY")
        result.append((mode, path, sha_text))
    verify(len(result) == 62 and len({x[1] for x in result}) == len(result),
           "ORIGINAL_TOOL_ENTRY_COUNT")
    return result


def source_ref(ref: str) -> bytes:
    return git("ls-remote", "--exit-code", REMOTE, "refs/heads/" + ref).split()[0]


def run() -> None:
    verify(os.environ.get("GITHUB_REPOSITORY") == "spoonman136668-ai/FORGE"
           and os.environ.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
           and os.environ.get("GITHUB_RUN_ATTEMPT") == "1", "RUNNER_IDENTITY")
    verify(git("rev-parse", "HEAD").decode() == os.environ["GITHUB_SHA"],
           "WORKFLOW_COMMIT_IDENTITY")
    repo = Path.cwd()
    workflow = (repo / ".github/workflows/mind-palace-uq37-scheduled-poll.yml").read_text(
        encoding="utf-8")
    for token in (
        PIN_OLD, PIN_AFTER_175, PIN_FINAL, GUARD_SCRIPT, SCHEMAS,
        "TOOLS_DEPENDENCY_TREE_DRIFT", "SCHEMA_DEPENDENCY_TREE_DRIFT",
        "ENGINE_SOURCE_DRIFT_NOT_APPROVED", "SOURCE_ALIAS_POLICY_DRIFT",
        "MANIFEST_POLICY_DRIFT", "NO_WRITE_BOUNDARY_VIOLATED",
        "UQ37_PRODUCTION_MEMORY_WRITES=0", "UQ37_CODEX_AND_PAID_INFERENCE=0",
        "UQ37_SCHEDULED_READONLY_INSPECTION=PASS",
    ):
        verify(token in workflow, "UNAPPROVED_GUARD_CHANGE")
    verify(workflow.count("PIN_AFTER_177_ONLY") == 0, "UNAPPROVED_ORDER")

    verify(source_ref("main").decode() == MAIN, "ACCEPTED_MAIN_DRIFT")
    for ref, commit, _name, _blob in (P175, P177):
        verify(source_ref(ref).decode() == commit, "REVIEW_HEAD_DRIFT")

    with tempfile.TemporaryDirectory(prefix="mpai16-tool-transition-", dir=os.environ["RUNNER_TEMP"]) as d:
        path = Path(d) / "mp"
        git("clone", "--quiet", "--filter=blob:none", "--no-checkout", "--depth", "1",
            "--single-branch", "--branch", "main", REMOTE, str(path), timeout=120)
        verify(git("-C", str(path), "rev-parse", "HEAD").decode() == MAIN,
               "PRIVATE_MAIN_CHECKOUT_DRIFT")
        for index, (ref, commit, _name, _blob) in enumerate((P175, P177)):
            target = "refs/heads/" + ref
            git("-C", str(path), "fetch", "--quiet", "--no-tags", "--depth", "1",
                "origin", target + ":refs/heads/mpai16-p" + str(index), timeout=120)
            verify(git("-C", str(path), "rev-parse", "mpai16-p" + str(index)).decode() == commit,
                   "PR_BRANCH_FETCH_DRIFT")
        # Disconnect before any further processing. This is strictly read-only.
        git("-C", str(path), "remote", "remove", "origin")
        verify(git("-C", str(path), "remote") == b"", "GIT_REMOTE_PRESENT")
        verify(git("-C", str(path), "rev-parse", "HEAD:tools").decode() == PIN_OLD,
               "REAL_BASE_TOOL_TREE_MISMATCH")
        verify(git("-C", str(path), "rev-parse", "HEAD:schemas").decode() == SCHEMAS,
               "SCHEMA_TREE_MISMATCH")
        verify(git("-C", str(path), "rev-parse",
                   "HEAD:tools/guarded-unattended-intake.ps1").decode() == GUARD_SCRIPT,
               "ENGINE_TOOL_BLOB_MISMATCH")
        for ref, commit, name, blob in (P175, P177):
            verify(git("-C", str(path), "rev-parse", commit + ":tools/" + name).decode() == blob,
                   "NEW_TOOL_BLOB_MISMATCH")
        entries = parse_ls_tree(git("-C", str(path), "ls-tree", "-z", "HEAD:tools"))
        verify(tree_digest(entries, {}) == PIN_OLD, "OLD_TREE_RECALC_MISMATCH")
        choice1 = {P175[2].encode(): P175[3]}
        choice2 = {P177[2].encode(): P177[3]}
        combined = {**choice1, **choice2}
        verify(tree_digest(entries, choice1) == PIN_AFTER_175,
               "INTERMEDIATE_TREE_RECALC_MISMATCH")
        verify(tree_digest(entries, choice2) == PIN_AFTER_177_ONLY,
               "UNAPPROVED_ALTERNATE_TREE_RECALC_MISMATCH")
        verify(tree_digest(entries, combined) == PIN_FINAL,
               "FINAL_TREE_RECALC_MISMATCH")
        verify(PIN_AFTER_177_ONLY not in workflow,
               "UNAPPROVED_MERGE_ORDER_PERMITTED")
        bad = tree_digest(entries, {P175[2].encode(): "0" * 40})
        verify(bad not in {PIN_OLD, PIN_AFTER_175, PIN_FINAL},
               "NEGATIVE_SOURCE_MUTATION_PERMITTED")
        verify(git("-C", str(path), "remote") == b"", "REMOTE_REATTACHED")
    print("MPAI16_EXACT_MAIN_AND_PR_HEADS=PASS")
    print("MPAI16_SOURCE_TOOL_TREE_RECALC_OLD=PASS")
    print("MPAI16_SOURCE_TOOL_TREE_RECALC_AFTER_175=PASS")
    print("MPAI16_SOURCE_TOOL_TREE_RECALC_AFTER_177=PASS")
    print("MPAI16_NEGATIVE_TOOL_BLOB_TAMPER_REJECTED=PASS")
    print("MPAI16_ORIGINAL_UQ37_FENCES_RETAINED=PASS")
    print("MPAI16_ONLY_DECLARED_ROLLOUT_ORDER=PASS")
    print("MPAI16_PRODUCTION_MEMORY_WRITES=0")
    print("MPAI16_FORGE_CONTROLLER_CHANGES=0")
    print("MPAI16_PRIVATE_SCRATCH_CLEAN=TRUE")
    print("MPAI16_ROLLOUT_GUARD_DEVELOPMENT_ONLY=TRUE")


if __name__ == "__main__":
    try:
        run()
    except Exception:
        print(FAIL_MARKER, file=sys.stderr)
        sys.exit(1)
