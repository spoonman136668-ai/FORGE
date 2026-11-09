"""R12-F: fixed, credential-free disposable FORGE-source worker rehearsal.

Only source-bound DEV staging and fixed Python syntax qualification.
Neither a supplied R12-A binding nor R12-B intent is owner admission.
No original SQLite, workflow, controller, original owner, network, protected
branch, research loop, first-use, promotion or unsupervised dispatch.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

from f139.local_controller import canonical
from f139.rsi_r12b_signed_job import (
    validate_intent, valid_binding,
)
from f139.rsi_r6_known_repair_cycle import PATH, MAX_SOURCE

SCHEMA = "forge.f139.rsi-r12f.disposable-source-rehearsal.v1"
CREDENTIAL_NAMES = (
    "F139_WORKER_HMAC_KEY", "GH_TOKEN", "GITHUB_TOKEN",
    "OPENAI_API_KEY", "CLOUDFLARE_API_TOKEN",
    "F139_RSI_ORIGINAL_OWNER_KEY",
)
STAGE_DIR = "rsi-r12f-disposable"
RECEIPT_NAME = "rsi-r12f-disposable-receipt.json"


class DisposableWorkerDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise DisposableWorkerDenied("F139_RSI_R12F_" + reason)


def digest(source: bytes) -> str:
    return sha256(source).hexdigest()


def git(repo: Path, *args: str) -> str:
    """Bounded local-only git, never shell or a network remote."""
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False, capture_output=True, text=True,
        timeout=45, stdin=subprocess.DEVNULL,
    )
    need(result.returncode == 0 and len(result.stdout) < 8192,
         "LOCAL_GIT_COMMAND_FAILED")
    return result.stdout.strip()


def rehearse(*, repo: Path, scratch: Path, binding: dict, intent: dict,
             candidate_source: bytes) -> dict:
    """Stage and compile a frozen candidate in a disjoint LOCAL Git clone.

    A successful return is neither original-owner signature nor executable
    worker authorization; the current production workflow must not call it.
    Its outputs are development artifacts only.
    """
    need(not any(os.environ.get(key) for key in CREDENTIAL_NAMES),
         "CREDENTIAL_INHERITANCE_DENIED")
    need(valid_binding(binding), "HISTORICAL_BINDING_SHAPE_INVALID")
    validate_intent(intent, binding)
    need(intent["development_only"] is True
         and intent["worker_admitted"] is False
         and intent["worker_dispatched"] is False
         and intent["source_promoted"] is False
         and intent["scientific_first_use"] is False
         and intent["autonomous_rsi_proven"] is False,
         "EXECUTION_AUTHORITY_FORBIDDEN")
    need(type(candidate_source) is bytes
         and 0 < len(candidate_source) <= MAX_SOURCE
         and digest(candidate_source) == intent["candidate_sha256"],
         "CANDIDATE_BYTES_DRIFT")
    path = intent["target_path"]
    need(type(path) is str and PATH.fullmatch(path) is not None
         and path.endswith(".py"), "FIXED_PYTHON_TARGET_ONLY")
    try:
        candidate_source.decode("ascii", "strict")
        compile(candidate_source, path, "exec")
    except (UnicodeError, SyntaxError) as exc:
        raise DisposableWorkerDenied(
            "F139_RSI_R12F_CANDIDATE_SOURCE_INVALID") from exc
    need(isinstance(repo, Path) and isinstance(scratch, Path)
         and repo.is_dir() and scratch.is_dir()
         and not repo.is_symlink() and not scratch.is_symlink()
         and not any(scratch.iterdir()), "ISOLATED_EMPTY_SCRATCH_REQUIRED")
    root = repo.resolve(strict=True)
    temp = scratch.resolve(strict=True)
    need(root != temp and root not in temp.parents
         and temp not in root.parents,
         "SOURCE_SCRATCH_OVERLAP_DENIED")
    need(git(root, "rev-parse", "--show-toplevel") and
         Path(git(root, "rev-parse", "--show-toplevel")).resolve(strict=True) == root,
         "NOT_EXACT_LOCAL_GIT_ROOT")
    need(git(root, "rev-parse", "HEAD") == intent["source_sha"]
         and git(root, "rev-parse", "HEAD^{tree}") == intent["source_tree_sha"]
         and git(root, "status", "--porcelain", "--untracked-files=all") == "",
         "PINNED_SOURCE_OR_CLEAN_TREE_DRIFT")
    original = root / path
    need(original.is_file() and not original.is_symlink()
         and original.resolve(strict=True).is_relative_to(root),
         "SOURCE_TARGET_SYMLINK_OR_MISSING")
    original_bytes = original.read_bytes()
    need(0 < len(original_bytes) <= MAX_SOURCE
         and digest(original_bytes) == intent["before_sha256"]
         and original_bytes != candidate_source,
         "PINNED_PREIMAGE_OR_NO_CHANGE")
    child = temp / STAGE_DIR
    result = subprocess.run(
        # On Windows a global core.autocrlf=true can silently checkout CRLF
        # even when the source Git blob is LF. Freeze local clone bytes to the
        # exact Git blob on both platforms; never waive the SHA256 preimage.
        ["git", "-c", "core.autocrlf=false", "clone",
         "-c", "core.autocrlf=false", "--quiet", "--no-hardlinks",
         "--", str(root), str(child)],
        check=False, capture_output=True, text=True,
        timeout=90, stdin=subprocess.DEVNULL,
    )
    need(result.returncode == 0, "DISPOSABLE_LOCAL_CLONE_FAILED")
    need(git(child, "rev-parse", "HEAD") == intent["source_sha"]
         and git(child, "rev-parse", "HEAD^{tree}") == intent["source_tree_sha"],
         "CLONE_SOURCE_DRIFT")
    if git(child, "remote"):
        git(child, "remote", "remove", "origin")
    target = child / path
    need(target.is_file() and not target.is_symlink()
         and digest(target.read_bytes()) == intent["before_sha256"],
         "CLONED_PREIMAGE_DRIFT")
    target.write_bytes(candidate_source)
    git(child, "diff", "--check")
    git(child, "add", "--", path)
    git(child, "-c", "user.name=FORGE-RSI-R12F-DEV",
        "-c", "user.email=forge-rsi-r12f-dev@invalid.local",
        "-c", "core.hooksPath=/dev/null",
        "commit", "-q", "-m", "dev: stage one source-only RSI repair", "--",
        path)
    staged_sha = git(child, "rev-parse", "HEAD")
    need(git(child, "diff-tree", "--no-commit-id", "--name-only",
             "-r", "HEAD") == path
         and git(child, "status", "--porcelain", "--untracked-files=all") == ""
         and target.read_bytes() == candidate_source,
         "STAGED_SOURCE_OR_WORKTREE_DRIFT")
    need(git(root, "rev-parse", "HEAD") == intent["source_sha"]
         and git(root, "status", "--porcelain", "--untracked-files=all") == "",
         "ORIGINAL_REPO_CHANGED")
    receipt = {
        "schema": SCHEMA,
        "protected_source_sha": intent["source_sha"],
        "protected_source_tree_sha": intent["source_tree_sha"],
        "original_failed_run_id": intent["failed_run_id"],
        "original_failed_job_id": intent["failed_job_id"],
        "reservation_event_sha256": intent["reservation_event_sha256"],
        "binding_sha256": intent["binding_sha256"],
        "target_path": path,
        "before_sha256": intent["before_sha256"],
        "candidate_sha256": intent["candidate_sha256"],
        "development_stage_commit_sha": staged_sha,
        "staged_source_sha256": digest(target.read_bytes()),
        "disposable_clone_only": True,
        "python_syntax_qualified": True,
        "full_regression_qualified": False,
        "original_owner_issued": False,
        "original_owner_admitted": False,
        "credentialed_original_signature_verified": False,
        "credential_free_worker_admitted": False,
        "worker_dispatched": False,
        "scientific_first_use": False,
        "source_promoted": False,
        "autonomous_rsi_proven": False,
        "network_calls": 0,
        "paid_model_calls": 0,
    }
    output = temp / RECEIPT_NAME
    with output.open("xb") as stream:
        stream.write(canonical(receipt) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    need(json.loads(output.read_text("ascii")) == receipt,
         "DISPOSABLE_TERMINAL_RECEIPT_DRIFT")
    return receipt
