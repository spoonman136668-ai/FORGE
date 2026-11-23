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
import textwrap

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


def parse_ls_tree(raw: bytes, expected_count: int = 62) -> list[tuple[bytes, bytes, str]]:
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
    verify(len(result) == expected_count and len({x[1] for x in result}) == len(result),
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


# Current-main successor is a distinct bounded qualification; historical
# P175/P177 reconstruction above remains available without replaying its ref.
CURRENT_MAIN = "c3d9019f48d9b6ab654ed7221e3802dfc81f41ad"
CURRENT_TOOLS = "c35a360bab92b96e60fd6c4ca6c76cf0a05ada5b"
FORGE_BASE = "a763aad603e6e89313c9608126f07d0990f8262e"
POLL = ".github/workflows/mind-palace-uq37-scheduled-poll.yml"
PIN_LINE_OLD = "            'e6e290d2fc77112769a0480d354a2c56be97c6d6'  # after MP #177\n"
PIN_LINE_NEW = "            'e6e290d2fc77112769a0480d354a2c56be97c6d6', # after MP #177\n            'c35a360bab92b96e60fd6c4ca6c76cf0a05ada5b'  # reviewed MP c3d9019f, unchanged inspection closure\n"
# Reverse exactly these seven independently read Git blob identities, then
# recompute the previously accepted tree. This proves every other entry,
# including the entire scheduled inspection closure, stayed byte-identical.
CURRENT_CHANGES = {
    b"chat-delta-cycle.ps1": ("b9f58010701d1da779294c4132f9f8d50f3927b5", "c56ee102110f0d6c6b029963e5e51b254b06e569"),
    b"context-pack-tiered.ps1": ("9bcf9debd6c7477ae2287fbdf7edcb16e11c0131", "1258b79d1d6c46637926e4745a45250e4744da01"),
    b"mindpalace_mcp.py": ("3a9cb7c41fd7ebbf96800d956589b422fc7b0fba", "104d1a4997856232c8913c20420b682224453ba9"),
    b"mindpalace_readonly.py": ("085e00c7bfc0d9f724874c93c75b7c4a79040dc0", "47d22f4bfe4587e9a868b23834e169c09c488261"),
    b"mpai_g316_private_phi_readonly_preflight.ps1": (None, "404ce2789a9f4a6b9340785993803022acfc8497"),
    b"mpai_local_phi_readonly.py": (None, "9efc3f61e4d91ef1af7f8ce1f1dac2c9f49da56a"),
    b"update-checkpoint.ps1": ("feb1b8573763ae2ed2e6150020742f4d7ed2c919", "dee8e7460a2545e9a73aa8e3a3519e5956bae1dd"),
}


def verify_current_entries(entries: list[tuple[bytes, bytes, str]]) -> None:
    verify(tree_digest(entries, {}) == CURRENT_TOOLS, "CURRENT_TREE_DIGEST")
    identities = {name: sha for _, name, sha in entries}
    for name, (_old, new) in CURRENT_CHANGES.items():
        verify(identities.get(name) == new, "CURRENT_CHANGED_BLOB")
    previous = [(mode, name, CURRENT_CHANGES[name][0] if name in CURRENT_CHANGES else sha)
                for mode, name, sha in entries
                if name not in CURRENT_CHANGES or CURRENT_CHANGES[name][0] is not None]
    verify(len(previous) == 62 and tree_digest(previous, {}) == PIN_FINAL,
           "CURRENT_UNREVIEWED_DEPENDENCY_CHANGE")


def approved_poll(previous: str, current: str) -> None:
    verify(previous.count(PIN_LINE_OLD) == 1 and
           current == previous.replace(PIN_LINE_OLD, PIN_LINE_NEW),
           "CURRENT_POLL_CHANGE_EXCEEDS_EXACT_PIN")


def poll_blocks(workflow: str) -> tuple[str, str]:
    # This parser accepts only the exact, source-pinned existing two-step
    # workflow layout. It never resolves arbitrary YAML or dispatch inputs.
    first = "        run: |\n"
    boundary = "      - name: Independently verify private scratch cleanup\n"
    verify(workflow.count(first) == 2 and workflow.count(boundary) == 1,
           "POLL_LAYOUT_DRIFT")
    body, cleanup = workflow.split(boundary)
    return (textwrap.dedent(body.split(first, 1)[1]),
            textwrap.dedent(cleanup.split(first, 1)[1]))


def current_source_checks() -> str:
    verify(os.environ.get("GITHUB_REPOSITORY") == "spoonman136668-ai/FORGE" and
           os.environ.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE" and
           os.environ.get("GITHUB_RUN_ATTEMPT") == "1", "RUNNER_IDENTITY")
    verify(git("rev-parse", "HEAD").decode() == os.environ["GITHUB_SHA"],
           "WORKFLOW_COMMIT_IDENTITY")
    allowed = {POLL, "tools/mpai16_mind_palace_tools_transition_check.py",
               "tools/test_mpai16_tools_transition_check.py",
               ".github/workflows/mpai16-uq37-transition-qualification-20261029.yml"}
    changed = set(git("diff", "--name-only", FORGE_BASE, "HEAD").decode().splitlines())
    verify(changed == allowed, "CURRENT_FORGE_SCOPE_DRIFT")
    workflow = Path(POLL).read_text(encoding="utf-8")
    previous = git("show", FORGE_BASE + ":" + POLL).decode() + "\n"
    approved_poll(previous, workflow)
    return workflow


def run_current() -> None:
    current_source_checks()
    verify(source_ref("main").decode() == CURRENT_MAIN, "CURRENT_MAIN_DRIFT")
    with tempfile.TemporaryDirectory(prefix="mpai16-current-tree-", dir=os.environ["RUNNER_TEMP"]) as d:
        path = Path(d) / "mp"
        git("clone", "--quiet", "--filter=blob:none", "--no-checkout", "--depth", "1",
            "--single-branch", "--branch", "main", REMOTE, str(path), timeout=120)
        verify(git("-C", str(path), "rev-parse", "HEAD").decode() == CURRENT_MAIN,
               "CURRENT_CHECKOUT_DRIFT")
        verify(git("-C", str(path), "config", "--get", "remote.origin.partialclonefilter") == b"blob:none",
               "CURRENT_BLOBLESS_FILTER")
        git("-C", str(path), "remote", "remove", "origin")
        verify_current_entries(parse_ls_tree(git("-C", str(path), "ls-tree", "-z", "HEAD:tools"), 64))
        pins = {"tools/guarded-unattended-intake.ps1": GUARD_SCRIPT,
                "schemas": SCHEMAS,
                "policies/chat-source-aliases.json": "a216e65d57061d57d07dc17fce45b9905234444e",
                ".ice/manifest.json": "37e0f5ffe301519e2ce7d564367cbfe9312017c1"}
        for item, identity in pins.items():
            verify(git("-C", str(path), "rev-parse", "HEAD:" + item).decode() == identity,
                   "CURRENT_PROTECTED_INPUT_DRIFT")
        verify(git("-C", str(path), "remote") == b"", "REMOTE_REATTACHED")
    verify(source_ref("main").decode() == CURRENT_MAIN, "CURRENT_MAIN_MOVED")
    print("MPAI16_CURRENT_TREE_AND_ACCEPTED_PREDECESSOR_RECONCILED=PASS")
    print("MPAI16_INSPECTION_CLOSURE_AND_PROTECTED_PINS_UNCHANGED=PASS")
    print("MPAI16_PRIVATE_METADATA_COPY_CLEAN=PASS")


def inspect_current_poll() -> None:
    workflow = current_source_checks()
    body, _cleanup = poll_blocks(workflow)
    # Execute the actual approved poll body, not a duplicate synthetic proof.
    # The poll itself protects all nine state hashes and finally removes its
    # private scratch. Workflow always() checks cleanup independently as well.
    with tempfile.TemporaryDirectory(prefix="mpai16-poll-body-", dir=os.environ["RUNNER_TEMP"]) as d:
        script = Path(d) / "inspect.ps1"
        script.write_text(body, encoding="utf-8")
        proc = subprocess.run(["pwsh", "-NoProfile", "-NonInteractive", "-File", str(script)], timeout=720)
        verify(proc.returncode == 0, "ACTUAL_POLL_FAILED")


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--current-tree"]:
            run_current()
        elif sys.argv[1:] == ["--inspect-current-poll"]:
            inspect_current_poll()
        elif not sys.argv[1:]:
            run()
        else:
            verify(False, "UNKNOWN_MODE")
    except Exception:
        print(FAIL_MARKER, file=sys.stderr)
        sys.exit(1)
