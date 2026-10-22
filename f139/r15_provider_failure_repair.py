"""R15B: classify one genuine GitHub engineering failure before selecting a repair.

Read-only, source-only replay of original R13 Windows SQLite cleanup failure.
Provider evidence is acquired by a separate credential-scoped workflow step.
No arbitrary commands, owner dispatch, model calls or main writes.
The bounded AST synthesizer generates a candidate from the failure class.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
import sys
import tempfile

from r16_semantic_repair import synthesize_workflow_repair, FAILURE_CLASS

REPO = "spoonman136668-ai/FORGE"
PATH = ".github/workflows/forge-f139-r13-owner-continuity-cold-audit.yml"
BRANCH = "proposal/f139-r13-owner-cold-continuity-20261022"
BAD_SHA = "6909880012bcd7161c24c6de1877046ce97bdb7f"
GOOD_SHA = "382a6668ca3e63bd4f16b7043bf5f9a7749886f7"
BAD_BLOB = "e42a98c4154502cb627aa2463b8a88e073903461"
GOOD_BLOB = "c6ece6e8bc4e68c6359632abf075498318371a52"
FAIL_RUN, GOOD_RUN = 39782884958, 39783112103
FAIL_JOB = 119838389983
NAME = "FORGE F139 R13 genuine unattended two-worker custody verification"
JOB_NAME = "original-owner-cold-audit"
def need(condition: bool, reason: str) -> None:
    if not condition:
        raise RuntimeError("R15_PROVIDER_REPAIR_" + reason)


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def read_json(path: Path) -> dict:
    raw = path.read_bytes()
    need(0 < len(raw) <= 200000, "PROVIDER_JSON_SIZE")
    doc = json.loads(raw)
    need(type(doc) is dict, "PROVIDER_JSON_STRUCTURE")
    return doc


def check_provider(evidence: Path) -> None:
    failed = read_json(evidence / "failed-run.json")
    passed = read_json(evidence / "passed-run.json")
    for record, run_id, sha, outcome in (
        (failed, FAIL_RUN, BAD_SHA, "failure"),
        (passed, GOOD_RUN, GOOD_SHA, "success"),
    ):
        need(record.get("id") == run_id
             and record.get("name") == NAME
             and record.get("head_sha") == sha
             and record.get("head_branch") == BRANCH
             and record.get("path") == PATH
             and record.get("event") == "push"
             and record.get("run_attempt") == 1
             and record.get("status") == "completed"
             and record.get("conclusion") == outcome
             and record.get("repository", {}).get("full_name") == REPO,
             "RUN_PROVENANCE_REJECTED")
    first = read_json(evidence / "failed-jobs.json")
    second = read_json(evidence / "passed-jobs.json")
    for data, run_id, expected in (
        (first, FAIL_RUN, "failure"),
        (second, GOOD_RUN, "success"),
    ):
        jobs = data.get("jobs")
        need(type(jobs) is list and len(jobs) == 1 and
             jobs[0].get("run_id") == run_id and
             jobs[0].get("name") == JOB_NAME and
             jobs[0].get("conclusion") == expected and
             jobs[0].get("status") == "completed" and
             jobs[0].get("runner_name") == "FORGE-CODEX-REMOTE",
             "JOB_PROVENANCE_REJECTED")
    need(first["jobs"][0].get("id") == FAIL_JOB, "ORIGINAL_FAILED_JOB_ID")
    raw_log = (evidence / "failed-log.txt").read_bytes()
    need(200 < len(raw_log) < 300000, "FAILURE_LOG_SIZE")
    log = raw_log.decode("utf-8-sig", "replace")
    need(all(x in log for x in (
        "PermissionError: [WinError 32]",
        "f139-r14-transition-rehearsal-",
        "state.sqlite",
        "tempfile.py",
        "Process completed with exit code 1",
    )), "WINDOWS_SQLITE_FAILURE_SIGNATURE_NOT_CONFIRMED")
    print("R15_AUTHENTIC_FAILURE_CLASS=WINDOWS_SQLITE_OPEN_HANDLE_CLEANUP")
    print("R15_FAILED_PROVIDER_RUN="+str(FAIL_RUN))
    print("R15_QUALIFIED_REPAIR_PROVIDER_RUN="+str(GOOD_RUN))


def inspect_checkout(root: Path, expected_sha: str, expected_blob: str) -> bytes:
    need(root.is_dir() and not root.is_symlink(), "CHECKOUT_DIRECTORY")
    import subprocess
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            timeout=15, check=False)
    need(result.returncode == 0 and result.stdout.decode().strip() == expected_sha,
         "CHECKOUT_COMMIT_DRIFT")
    result = subprocess.run(["git", "-C", str(root), "status", "--porcelain",
                             "--untracked-files=all"], stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, timeout=15, check=False)
    need(result.returncode == 0 and result.stdout == b"", "CHECKOUT_DIRTY")
    source = (root / PATH).resolve(strict=True)
    need(source.is_relative_to(root.resolve()) and source.is_file()
         and not source.is_symlink(), "WORKFLOW_PATH_ESCAPE")
    # Windows autocrlf changes checked-out working bytes even though the
    # committed tree is immutable. Authenticate and read the Git *blob*,
    # rather than treating a platform-dependent checkout as primary evidence.
    entry = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD:" + PATH],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           timeout=15, check=False)
    need(entry.returncode == 0 and entry.stdout.decode().strip() == expected_blob,
         "SOURCE_COMMITTED_BLOB_DRIFT")
    content = subprocess.run(["git", "-C", str(root), "show", "HEAD:" + PATH],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             timeout=15, check=False)
    need(content.returncode == 0 and len(content.stdout) <= 100000
         and blob(content.stdout) == expected_blob, "SOURCE_BLOB_DRIFT")
    return content.stdout



def adversarial_provider_tests(evidence: Path) -> None:
    """Tampered evidence and unfamiliar failure cannot select any repair."""
    names = ("failed-run.json", "passed-run.json", "failed-jobs.json",
             "passed-jobs.json", "failed-log.txt")
    cases = (
        ("wrong_failed_commit", "failed-run.json", "head_sha", "0" * 40),
        ("wrong_success_outcome", "passed-run.json", "conclusion", "failure"),
        ("wrong_owner_runner", "failed-jobs.json", "runner_name", "UNKNOWN"),
        ("unrecognized_failure", "failed-log.txt", "signature", ""),
    )
    for label, filename, field, replacement in cases:
        with tempfile.TemporaryDirectory(prefix="forge-r15-untrusted-provider-") as t:
            scratch = Path(t)
            for name in names:
                shutil.copyfile(evidence / name, scratch / name)
            target = scratch / filename
            if filename.endswith(".json"):
                obj = json.loads(target.read_text(encoding="utf-8-sig"))
                if field == "runner_name":
                    obj["jobs"][0][field] = replacement
                else:
                    obj[field] = replacement
                target.write_text(json.dumps(obj), encoding="utf-8")
            else:
                text = target.read_text(encoding="utf-8-sig", errors="replace")
                need("PermissionError: [WinError 32]" in text,
                     "ORIGINAL_FAILURE_SIGNATURE_ABSENT")
                target.write_text(
                    text.replace("PermissionError: [WinError 32]", replacement),
                    encoding="utf-8")
            try:
                check_provider(scratch)
            except RuntimeError as exc:
                need(str(exc).startswith("R15_PROVIDER_REPAIR_"),
                     "UNEXPECTED_NEGATIVE_CLASS")
            else:
                raise RuntimeError("R15_PROVIDER_REPAIR_FALSE_POSITIVE_" + label)
    print("R15_FOUR_ADVERSARIAL_PROVIDER_FORGERIES=REJECTED")

def repair_failure(evidence: Path, failed: Path, qualified: Path) -> None:
    check_provider(evidence)
    adversarial_provider_tests(evidence)
    original = inspect_checkout(failed, BAD_SHA, BAD_BLOB)
    expected = inspect_checkout(qualified, GOOD_SHA, GOOD_BLOB)
    # No frozen text-replacement list is supplied to the synthesizer.
    # The fault class comes from verified provider logs, while the source
    # transformation follows bounded Python AST contexts in the culprit.
    proposal, contexts = synthesize_workflow_repair(
        original.decode("utf-8"), FAILURE_CLASS)
    need(1 <= contexts <= 6, "SEMANTIC_SCOPE_DRIFT")
    updated = proposal.encode("utf-8")
    need(blob(updated) == GOOD_BLOB and updated == expected,
         "REPAIR_CANDIDATE_NOT_INDEPENDENTLY_QUALIFIED")
    with tempfile.TemporaryDirectory(prefix="forge-r15-provider-repair-") as temporary:
        dest = Path(temporary) / "repaired-workflow.yml"
        dest.write_bytes(updated)
        need(blob(dest.read_bytes()) == GOOD_BLOB, "SANDBOX_REPAIR_BYTES_DRIFT")
    need(inspect_checkout(failed, BAD_SHA, BAD_BLOB) == original,
         "ORIGINAL_FAILURE_SOURCE_MUTATED")
    need(inspect_checkout(qualified, GOOD_SHA, GOOD_BLOB) == expected,
         "QUALIFIED_REPAIR_SOURCE_MUTATED")
    print("R16_AST_SYNTHESIZED_CONTEXTS="+str(contexts))
    print("R16_GENERATED_SOURCE_MATCHES_INDEPENDENT_QUALIFICATION=PASS")
    print("R15_AUTHENTIC_PROVIDER_DIAGNOSIS=PASS")
    print("R15_EVIDENCE_SELECTED_REPAIR_SHA="+GOOD_BLOB)
    print("R15_SANDBOX_REPAIR_EXACT_QUALIFIED_BYTES=PASS")
    print("R15_UNKNOWN_FAILURES_AND_SOURCE_DRIFT=FAIL_CLOSED")
    print("R15_OWNER_DATABASE_WRITES=0")
    print("R15_CONTROLLER_RESTARTS=0")
    print("R15_AUTONOMOUS_UNFAMILIAR_PATCH_SYNTHESIS=NOT_PROVEN")


if __name__ == "__main__":
    need(len(sys.argv) == 4, "ARGUMENT_COUNT")
    repair_failure(*(Path(v).resolve(strict=True) for v in sys.argv[1:]))
