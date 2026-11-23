"""Owner-comment entry for the EXISTING F139 Windows owner, admission only.

This entry never disables/rebinds the scheduled task, starts a controller,
dispatches workers, calls paid models, or changes the archived SQLite.
The one permitted write is an already activated fresh DB's first READY intake.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess

from f139.local_controller import Database, SingleOwner
from f139.nci04_fresh_native_intake import (
    OWNER_PREFIX, OWNER_WORKFLOW, stage_one_fresh_development_issue,
)
from f139.nci04_fresh_native_owner_route import inspect_staged_fresh_native_mode
from f139.nci04_fresh_native_provider_issue import FORGE, YGG

REPO = "spoonman136668-ai/FORGE"
OWNER = "spoonman136668-ai"
COMMENT = re.compile(
    r"F139-FRESH-DEV-ADMIT ([a-f0-9]{40}) ([1-9][0-9]{0,8})\Z")
FOLDER = re.compile(r"f139-fresh-dev-[1-9][0-9]{0,19}\Z")


class OwnerAdmissionDenied(ValueError):
    pass


def need(ok: bool, why: str) -> None:
    if not ok:
        raise OwnerAdmissionDenied("F139_FRESH_OWNER_ADMISSION_" + why)


def inspect_event(event: dict, env: dict) -> tuple[int, int]:
    """Inspect trigger metadata without interpreting comment as a command."""
    need(type(event) is dict and type(env) is dict,
         "OWNER_EVENT_OR_ENV_INVALID")
    need(env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and env.get("GITHUB_REPOSITORY") == REPO
         and env.get("GITHUB_ACTOR") == OWNER
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_WORKFLOW_REF") == OWNER_WORKFLOW
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and type(env.get("GITHUB_SHA")) is str
         and re.fullmatch(r"[a-f0-9]{40}", env["GITHUB_SHA"]) is not None
         and str(env.get("GITHUB_RUN_ID", "")).isdigit()
         and int(env["GITHUB_RUN_ID"]) > 0
         and not env.get("OPENAI_API_KEY"),
         "AUTHENTICATED_RUN_CONTEXT_REQUIRED")
    comment = event.get("comment") or {}
    issue = event.get("issue") or {}
    need(event.get("action") == "created"
         and event.get("repository", {}).get("full_name") == REPO
         and event.get("sender", {}).get("login") == OWNER
         and issue.get("number") == 1830 and issue.get("state") == "open"
         and issue.get("user", {}).get("login") == OWNER
         and not issue.get("pull_request")
         and type(comment.get("id")) is int and comment["id"] > 0
         and comment.get("author_association") == "OWNER"
         and comment.get("user", {}).get("login") == OWNER
         and comment.get("url") ==
         f"https://api.github.com/repos/{REPO}/issues/comments/{comment['id']}"
         and type(comment.get("body")) is str,
         "OWNER_COMMENT_NOT_AUTHENTICATED")
    matched = COMMENT.fullmatch(comment["body"])
    need(matched is not None
         and matched.group(1) == env["GITHUB_SHA"]
         and comment["body"] ==
         f"{OWNER_PREFIX} {env['GITHUB_SHA']} {matched.group(2)}",
         "COMMENT_SOURCE_OR_ISSUE_MISMATCH")
    return int(matched.group(2)), comment["id"]


def allowed_read(route: str, issue_number: int,
                 comment_id: int) -> bool:
    """Reject all provider POSTs, unrelated repositories and arbitrary paths."""
    return route in {
        FORGE + "/branches/main",
        YGG + "/branches/main",
        FORGE + "/issues/" + str(issue_number),
        FORGE + "/issues/comments/" + str(comment_id),
    } or re.fullmatch(
        r"repos/spoonman136668-ai/Yggdrasil/git/commits/[a-f0-9]{40}",
        route) is not None


def github_read(route: str, issue_number: int, comment_id: int) -> dict:
    need(allowed_read(route, issue_number, comment_id),
         "PROVIDER_ROUTE_OUT_OF_SCOPE")
    need(bool(os.environ.get("GH_TOKEN")),
         "GITHUB_READ_CREDENTIAL_MISSING")
    result = subprocess.run(
        ["gh", "api", "--method", "GET", route],
        stdin=subprocess.DEVNULL, capture_output=True,
        timeout=25, check=False)
    need(result.returncode == 0 and 2 < len(result.stdout) < 512000,
         "PROVIDER_READ_FAILED")
    try:
        doc = json.loads(result.stdout)
    except (ValueError, UnicodeError) as exc:
        raise OwnerAdmissionDenied(
            "F139_FRESH_OWNER_ADMISSION_PROVIDER_JSON_INVALID") from exc
    need(type(doc) is dict, "PROVIDER_DOCUMENT_INVALID")
    return doc


def find_one_activated(root: Path, source: str) -> Path:
    """Only choose a cold-verified activation; ignore inert staged folders."""
    need(root.is_dir() and not root.is_symlink()
         and not getattr(root, "is_junction", lambda: False)(),
         "OWNER_ROOT_INVALID")
    found = []
    for folder in sorted(root.glob("f139-fresh-dev-*")):
        need(FOLDER.fullmatch(folder.name) is not None
             and folder.is_dir() and not folder.is_symlink()
             and not getattr(folder, "is_junction", lambda: False)(),
             "FRESH_FOLDER_NAME_OR_LINK_INVALID")
        path = folder / "state.sqlite"
        if not path.is_file():
            continue
        need(not path.is_symlink(), "FRESH_DATABASE_SYMLINK")
        readonly = Database.open_readonly(path)
        try:
            status = inspect_staged_fresh_native_mode(readonly, path)
            need(status is not None and status["source_sha"] == source,
                 "FRESH_SOURCE_MISMATCH")
            if status["disposition"] == (
                    "FRESH_ACTIVATION_RECORDED_DISPATCH_BLOCKED"):
                found.append(path)
            else:
                need(status["disposition"] ==
                     "FRESH_DEVELOPMENT_STAGED_DISABLED_NO_DISPATCH",
                     "FRESH_ATTEMPT_ALREADY_SPENT")
        finally:
            readonly.close()
    need(len(found) == 1, "EXACTLY_ONE_ACTIVATED_FRESH_DB_REQUIRED")
    return found[0]


def run_once() -> dict:
    env = dict(os.environ)
    event_path = Path(env.get("GITHUB_EVENT_PATH", ""))
    need(event_path.is_file() and not event_path.is_symlink()
         and 0 < event_path.stat().st_size <= 64000,
         "EVENT_FILE_NOT_AUTHENTICATED")
    try:
        event = json.loads(event_path.read_bytes())
    except (ValueError, UnicodeError) as exc:
        raise OwnerAdmissionDenied(
            "F139_FRESH_OWNER_ADMISSION_EVENT_JSON_INVALID") from exc
    issue_number, comment_id = inspect_event(event, env)
    get = lambda route: github_read(route, issue_number, comment_id)
    remote = get(FORGE + "/issues/comments/" + str(comment_id))
    comment = event["comment"]
    need(remote.get("id") == comment_id
         and remote.get("user", {}).get("login") == OWNER
         and remote.get("author_association") == "OWNER"
         and remote.get("body") == comment["body"]
         and remote.get("created_at") == comment.get("created_at"),
         "OWNER_COMMENT_PROVIDER_READBACK_DRIFT")
    branch = get(FORGE + "/branches/main")
    need(branch.get("protected") is True
         and branch.get("commit", {}).get("sha") == env["GITHUB_SHA"],
         "PROTECTED_MAIN_DRIFT")
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True,
        timeout=15, check=False)
    need(result.returncode == 0
         and result.stdout.decode().strip() == env["GITHUB_SHA"],
         "CHECKOUT_SOURCE_DRIFT")
    clean = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        capture_output=True, timeout=15, check=False)
    need(clean.returncode == 0 and not clean.stdout,
         "CHECKOUT_DIRTY")
    profile = env.get("LOCALAPPDATA", "")
    need(bool(profile), "WINDOWS_PROFILE_MISSING")
    root = Path(profile) / "FORGE-F139"
    old = root / "state.sqlite"
    need(old.is_file() and not old.is_symlink(),
         "ORIGINAL_DATABASE_NOT_FOUND")
    with SingleOwner(old.with_suffix(".lock")):
        path = find_one_activated(root, env["GITHUB_SHA"])
        with SingleOwner(path.with_suffix(".lock")):
            original = Database.open_readonly(old)
            try:
                fresh = Database(path)
                try:
                    report = stage_one_fresh_development_issue(
                        fresh, original, issue_number=issue_number, get=get)
                finally:
                    fresh.close()
            finally:
                original.close()
    need(report["worker_dispatched"] is False
         and report["original_mutations"] == 0
         and report["scientific_first_use"] is False
         and report["paid_model_calls"] == 0,
         "ADMISSION_RECEIPT_UNSAFE")
    return report


if __name__ == "__main__":
    print("F139_FRESH_ONE_READY=" + json.dumps(run_once(), sort_keys=True))
