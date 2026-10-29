"""MP-AI15: original Windows three-PR integration and cold-retention rehearsal.

All git merges/checkpoints happen in a temporary repo whose remote is removed
before source modifications. No accepted Mind-Palace source, FORGE main,
controller, production memory, independent reviewer state, or model weights
are changed. Public log is limited to non-sensitive PASS markers and stage codes.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

MAIN = "f31e4203892730ddbe24d44ce5674f5678d498aa"
ICE = "842b8c1318db3b826bdb7243b0cdf0d5d8efedc2"
REMOTE = "https://github.com/spoonman136668-ai/Mind-Palace.git"
REVIEWS = (
    ("175", "review/mpai-usage-continuity-20261029", "638bc9b2883c6b01f81383a5c4afa87738641047"),
    ("176", "review/mpai05-usage-feedback-20261029", "f15810a16b3b31d72f0f9639f167c854ea6de52f"),
    ("177", "proposal/mpai13-feedback-review-handoff-20261029", "f79462d25629bc09be87f3c2b64d36b365fb0335"),
)
BATCH = "pilots/mixed-source/2026-10-29-mpai05-authenticated-usage-feedback.batch.json"
BATCH_BLOB = "6048ca181c66afcce179ec07af3d7f4e6d20b896"
PROTECTED = (
    ".ice/records.json", ".ice/source-ledger.json", "archive/index.json",
    ".ice/remote-bootstrap.json", ".ice/remote-catalog.json",
    ".ice/remote-index.ndjson", ".ice/chat-delta-state.json",
    ".ice/project-state-capsules.json", ".ice/project-dependency-graph.json",
)
ALLOWED = (
    ".ice/records.json", ".ice/source-ledger.json",
    ".ice/remote-bootstrap.json", ".ice/remote-catalog.json",
    ".ice/remote-index.ndjson", ".ice/project-state-capsules.json",
    ".ice/project-dependency-graph.json",
)
LESSONS = (
    "lesson/mpai05-uq37-original-scheduled-inspection-repaired-but-idle-20261029",
    "lesson/mpai05-p16-p17-memory-retriever-model-accuracy-no-gain-20261029",
)
OLD = "lesson/mpai-hindsight-h2-development-context-efficiency-20261028"
STAGE = "BOOTSTRAP"


def require(ok: bool, code: str) -> None:
    if not ok:
        raise RuntimeError("MPAI15_" + code)


def call(args: list[str], *, cwd: Path | None = None, timeout: int = 120,
         env: dict[str, str] | None = None) -> str:
    proc = subprocess.run(args, cwd=str(cwd) if cwd else None,
                          capture_output=True, text=True, timeout=timeout,
                          env=env, encoding="utf-8", errors="replace")
    if proc.returncode:
        raise RuntimeError("MPAI15_TOOL_EXIT_" + re.sub(r"[^A-Z0-9]+", "_", str(args[0]).upper())[:25])
    return proc.stdout.strip()


def git(root: Path, *args: str, timeout: int = 120) -> str:
    return call(["git", "-C", str(root), *args], timeout=timeout)


def sha256(root: Path, name: str) -> str:
    return hashlib.sha256((root / name).read_bytes()).hexdigest()


def safe_main() -> None:
    global STAGE
    require(os.environ.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
            and os.environ.get("GITHUB_REPOSITORY") == "spoonman136668-ai/FORGE"
            and os.environ.get("GITHUB_RUN_ATTEMPT") == "1",
            "ORIGINAL_WINDOWS_OWNER_REQUIRED")
    require(re.fullmatch(r"[0-9a-f]{40}", os.environ.get("GITHUB_SHA", "")) is not None,
            "FORGE_WORKFLOW_SOURCE_REQUIRED")
    require(call(["git", "rev-parse", "HEAD"]) == os.environ["GITHUB_SHA"],
            "FORGE_CHECKOUT_DRIFT")
    env = dict(os.environ)
    for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY",
                 "HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        env.pop(name, None)
    # Also remove them from this process before any child starts.
    for name in tuple(os.environ):
        if name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                    "OPENROUTER_API_KEY", "HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
            os.environ.pop(name, None)

    with tempfile.TemporaryDirectory(prefix="mpai15-private-", dir=os.environ["RUNNER_TEMP"]) as tmp:
        root = Path(tmp) / "source"
        STAGE = "PIN_REMOTE"
        remote_main = call(["git", "ls-remote", "--exit-code", REMOTE, "refs/heads/main"])
        require(remote_main.split()[0] == MAIN, "ACCEPTED_MAIN_DRIFT")
        call(["git", "clone", "--quiet", "--no-checkout", "--branch", "main", REMOTE, str(root)],
             timeout=150)
        require(git(root, "rev-parse", "refs/heads/main") == MAIN, "CLONE_BASE_DRIFT")
        for number, ref, head in REVIEWS:
            remote_line = call(["git", "ls-remote", "--exit-code", REMOTE, "refs/heads/" + ref])
            require(remote_line.split()[0] == head, "PR_" + number + "_REMOTE_DRIFT")
            git(root, "fetch", "--quiet", "--no-tags", "origin",
                "refs/heads/" + ref + ":refs/heads/mpai15-" + number, timeout=150)
            require(git(root, "rev-parse", "refs/heads/mpai15-" + number) == head,
                    "PR_" + number + "_FETCH_DRIFT")
            require(git(root, "merge-base", MAIN, head) == MAIN,
                    "PR_" + number + "_BASE_NOT_ACCEPTED")
        git(root, "remote", "remove", "origin")
        require(git(root, "remote") == "", "GIT_REMOTE_REMOVE_FAILED")
        git(root, "checkout", "--quiet", "-B", "mpai15-disposable", MAIN)
        STAGE = "DISCONNECTED_THREE_PR_MERGE"
        for number, _ref, head in REVIEWS:
            git(root, "-c", "user.name=MPAI15-Fixture", "-c",
                "user.email=fixture@invalid.example", "-c",
                "core.hooksPath=NUL", "merge", "--quiet", "--no-edit",
                "--no-ff", "mpai15-" + number, timeout=120)
            require(git(root, "merge-base", "--is-ancestor", head,
                        "HEAD") == "", "PR_" + number + "_NOT_IN_MERGED_ANCESTRY")
            print("MPAI15_DISPOSABLE_PR_" + number + "_MERGE=PASS")
        require(git(root, "rev-parse", "HEAD:.ice") == ICE,
                "PR_MERGE_MODIFIED_ACCEPTED_ICE")
        require(git(root, "rev-parse", "HEAD:" + BATCH) == BATCH_BLOB,
                "AUTHENTIC_BATCH_IDENTITY_DRIFT")
        hashes = {file: sha256(root, file) for file in PROTECTED}
        require(git(root, "status", "--porcelain=v1", "--untracked-files=all") == "",
                "MERGED_SOURCE_DIRTY")

        STAGE = "CANONICAL_WINDOWS_REGRESSION"
        suite = call(["pwsh", "-NoProfile", "-NonInteractive", "-File",
                      str(root / "tests" / "Test-All.ps1")], cwd=root, timeout=800,
                     env=env)
        require("Mind-Palace regression suite passed" in suite,
                "CANONICAL_SUITE_RECEIPT_MISSING")
        require(all(sha256(root, file) == expected for file, expected in hashes.items()),
                "TESTS_CHANGED_ACCEPTED_ICE")
        require(git(root, "status", "--porcelain=v1", "--untracked-files=all") == "",
                "TESTS_DIRTIED_SOURCE")
        print("MPAI15_COMBINED_CANONICAL_WINDOWS_REGRESSION=PASS")

        STAGE = "COLLECT_AND_CHECKPOINT"
        classification = json.loads(call(["pwsh", "-NoProfile", "-NonInteractive",
            "-File", str(root / "tools/collect.ps1"), "classify",
            "-InputPath", str(root / BATCH)], cwd=root, timeout=80))
        counts = classification["result"]["counts"]
        require(classification["schema"] == "mind-palace.collector-result.v1"
                and counts["new"] == 2 and counts["review"] == 0
                and counts["merge"] == 0 and counts["ignore"] == 0,
                "CLASSIFICATION_NOT_TWO_UNCONFLICTED")
        staged = json.loads(call(["pwsh", "-NoProfile", "-NonInteractive",
            "-File", str(root / "tools/collect.ps1"), "stage",
            "-InputPath", str(root / BATCH)], cwd=root, timeout=80))
        require(staged["result"]["counts"]["new"] == 2, "STAGING_FAILURE")
        checkpoint = call(["pwsh", "-NoProfile", "-NonInteractive",
            "-File", str(root / "tools/mind.ps1"), "checkpoint"],
            cwd=root, timeout=150)
        require("promoted=2" in checkpoint and "retired=0" in checkpoint,
                "DISPOSABLE_CHECKPOINT_NOT_TWO")
        print("MPAI15_DISPOSABLE_TWO_LESSONS_CHECKPOINT=PASS")

        classification_path = Path(tmp) / "private-classification.json"
        classification_path.write_text(json.dumps(classification), encoding="utf-8")
        ledger = json.loads(call(["pwsh", "-NoProfile", "-NonInteractive",
            "-File", str(root / "tools/source-ledger.ps1"), "record",
            "-BatchPath", str(root / BATCH),
            "-ClassificationPath", str(classification_path)], cwd=root, timeout=80))
        require(ledger["entries_added"] == 2, "SOURCE_LEDGER_COUNT_MISMATCH")
        call(["pwsh", "-NoProfile", "-NonInteractive",
              "-File", str(root / "tools/remote-snapshot.ps1")],
             cwd=root, timeout=180)
        git(root, "add", "--", *ALLOWED)
        staged_files = git(root, "diff", "--cached", "--name-only").splitlines()
        require(len(staged_files) >= 4 and all(f in ALLOWED for f in staged_files),
                "UNEXPECTED_PERSISTENT_FILE_MUTATION")
        git(root, "-c", "user.name=MPAI15-Fixture", "-c",
            "user.email=fixture@invalid.example", "-c",
            "core.hooksPath=NUL", "commit", "--quiet",
            "-m", "fixture: disconnected three-PR checkpoint with negative feedback")
        local_sha = git(root, "rev-parse", "HEAD")
        STAGE = "COLD_READONLY_CONSUMER"
        reader = r'''
import os,sys,hashlib
from pathlib import Path
root=Path(os.environ["MPAI15_PRIVATE_ROOT"])
source=os.environ["MPAI15_PRIVATE_COMMIT"]
sys.path.insert(0,str(root/"tools"))
from mindpalace_readonly import MemorySnapshot
snap=MemorySnapshot(root,source,["Mind-Palace"])
ids=(
"lesson/mpai05-uq37-original-scheduled-inspection-repaired-but-idle-20261029",
"lesson/mpai05-p16-p17-memory-retriever-model-accuracy-no-gain-20261029")
for rec_id in ids:
    item=snap.get_record(source,rec_id,["Mind-Palace"])
    assert item["found"] and item["record"]["status"]=="observed"
    assert len(item["record"]["source_refs"])>=2
print("MPAI15_NEW_COLLECTOR_LESSONS_COLD_READBACK=2_PASS")
old="lesson/mpai-hindsight-h2-development-context-efficiency-20261028"
recall=snap.recall(source,"Hindsight Harness2 development context efficiency accuracy unproven",["Mind-Palace"])
pointer=next(x for x in recall["matches"] if x["id"]==old)
assert pointer["retrieval_preview_kind"]=="reference_only"
assert pointer["full_record_required"] is True
full=snap.get_record(source,old,["Mind-Palace"])["record"]
assert hashlib.sha256(full["statement"].encode("utf-8")).hexdigest()==pointer["source_statement_sha256"]
assert full["source_refs"]==pointer["source_refs"]
print("MPAI15_OVERSIZED_LESSON_REFERENCE_FOLLOWUP=PASS")
print("MPAI15_EXACT_PIN_NEW_PYTHON_PROCESS=PASS")
'''
        env["MPAI15_PRIVATE_ROOT"] = str(root)
        env["MPAI15_PRIVATE_COMMIT"] = local_sha
        cold = call([sys.executable, "-B", "-c", reader], cwd=root, timeout=80, env=env)
        for marker in ("MPAI15_NEW_COLLECTOR_LESSONS_COLD_READBACK=2_PASS",
                       "MPAI15_OVERSIZED_LESSON_REFERENCE_FOLLOWUP=PASS",
                       "MPAI15_EXACT_PIN_NEW_PYTHON_PROCESS=PASS"):
            require(marker in cold, "COLD_CONSUMER_RECEIPT_MISSING")
            print(marker)
        require(git(root, "remote") == "", "GIT_ORIGIN_REATTACHED")
        require(git(root, "status", "--porcelain=v1", "--untracked-files=all") == "",
                "FINAL_DISCONNECTED_SOURCE_DIRTY")
        print("MPAI15_THREE_PR_INTEGRATION=PASS")
        print("MPAI15_GIT_REMOTE_COUNT=0")
        print("MPAI15_ACCEPTED_MEMORY_AND_FORGE_MAIN_WRITES=0")
        print("MPAI15_INDEPENDENT_PR_APPROVAL=FALSE")
        print("MPAI15_VERIFIED_AGENT_LEARNING_GAIN=FALSE")
    print("MPAI15_DISPOSABLE_SCRATCH_CLEAN=TRUE")


if __name__ == "__main__":
    try:
        safe_main()
    except Exception:
        # Private paths, source refs and textual records cannot enter public logs.
        print("MPAI15_STAGE_FAILURE=" + STAGE, file=sys.stderr)
        sys.exit(1)
