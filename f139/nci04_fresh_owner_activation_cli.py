"""Single bounded Windows owner activation entry after INDEPENDENT task release.

This is NOT a task-stop/rebind, controller bootstrap, worker, or science route.
The original 1864-event database stays READ-ONLY. Exactly one cold archive
and separate fresh DB are create-only; ambiguous partial work is never replayed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

from f139.local_controller import Database, SingleOwner
from f139.nci04_fresh_activation_writer import (
    APPROVAL_ISSUE, APPROVAL_PREFIX, WORKFLOW,
    _owner_windows_quiesced, authenticate_source_bound_owner_comment,
    write_fresh_native_activation_once,
)
from f139.nci04_fresh_dev_epoch import prepare_inert_epoch
from f139.nci04_fresh_yggdrasil_boundary import (
    ACCEPTED, ACCEPTED_NATIVE_PATH, AMALGAM_HEAD, AMALGAM_PR,
    LINEAGE_HEAD, LINEAGE_PR, LINEAGE_RECEIPT_PATH,
    read_yggdrasil_research_boundary,
)
from f139.nci04_fresh_remote_floor import ISSUE_PAGE
from f139.nci04_v59_cold_backup_stage import stage_original_cold_backup
from f139.nci04_v59_owner_forward_readiness import (
    HEAD_SEQ, HEAD_SHA256, SOURCE, audit_frozen_original_readonly,
)

REPO = "spoonman136668-ai/FORGE"
OWNER = "spoonman136668-ai"
FORGE = "repos/" + REPO
YGG = "repos/spoonman136668-ai/Yggdrasil"
SHA = re.compile(r"[0-9a-f]{40}\Z")
NATIVE_PATHS = frozenset({
    FORGE + "/branches/main",
    FORGE + "/issues/807",
    ISSUE_PAGE,
    YGG + "/branches/main",
    YGG + "/pulls/" + str(AMALGAM_PR),
    YGG + "/pulls/" + str(LINEAGE_PR),
    YGG + "/compare/" + ACCEPTED + "..." + AMALGAM_HEAD,
    YGG + "/compare/" + ACCEPTED + "..." + LINEAGE_HEAD,
    YGG + "/contents/" + ACCEPTED_NATIVE_PATH + "?ref=" + ACCEPTED,
    YGG + "/contents/" + LINEAGE_RECEIPT_PATH + "?ref=" + LINEAGE_HEAD,
})
FOLDER = re.compile(r"f139-(?:v59-before|fresh-dev)-[1-9][0-9]{0,19}\Z")


class FreshOwnerActivationDenied(ValueError):
    """No partial or historical write creates retry or model-use authority."""


def need(ok: bool, why: str) -> None:
    if not ok:
        raise FreshOwnerActivationDenied("F139_FRESH_OWNER_ACTIVATE_" + why)


def allow_get(route: str, comment_id: int) -> bool:
    """Exact source-bound GET routes; no arbitrary URL, method or user input."""
    return (type(route) is str and type(comment_id) is int
            and comment_id > 0 and (
                route in NATIVE_PATHS
                or route == FORGE + "/issues/comments/" + str(comment_id)
                or re.fullmatch(FORGE + r"/issues/[1-9][0-9]{0,8}", route)
                    is not None))


def read_provider(route: str, comment_id: int):
    need(allow_get(route, comment_id), "PROVIDER_ROUTE_DENIED")
    need(bool(os.environ.get("GH_TOKEN")), "PROVIDER_READ_TOKEN_MISSING")
    try:
        result = subprocess.run(
            ["gh", "api", "--method", "GET", route],
            stdin=subprocess.DEVNULL, capture_output=True,
            timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FreshOwnerActivationDenied(
            "F139_FRESH_OWNER_ACTIVATE_PROVIDER_TRANSPORT_UNAVAILABLE"
        ) from exc
    need(result.returncode == 0 and 2 < len(result.stdout) <= 8_000_000,
         "PROVIDER_GET_FAILED")
    try:
        value = json.loads(result.stdout)
    except (ValueError, UnicodeError) as exc:
        raise FreshOwnerActivationDenied(
            "F139_FRESH_OWNER_ACTIVATE_PROVIDER_INVALID_JSON"
        ) from exc
    need(type(value) in (list, dict), "PROVIDER_RESPONSE_SHAPE_INVALID")
    return value


def event_and_source(event: dict, env: dict) -> tuple[str, int]:
    """Recheck every owner/runner identity before ANY create-only action."""
    need(type(env) is dict and type(event) is dict, "EVENT_MISSING")
    target = env.get("GITHUB_SHA")
    need(type(target) is str and SHA.fullmatch(target) is not None
         and target != SOURCE
         and os.name == "nt" and sys.platform == "win32"
         and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and env.get("GITHUB_REPOSITORY") == REPO
         and env.get("GITHUB_ACTOR") == OWNER
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_WORKFLOW_REF") == WORKFLOW
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and type(env.get("GITHUB_RUN_ID")) is str
         and env["GITHUB_RUN_ID"].isdigit()
         and int(env["GITHUB_RUN_ID"]) > 0
         and not env.get("OPENAI_API_KEY")
         and bool(env.get("GH_TOKEN")),
         "AUTHENTICATED_ORIGINAL_WINDOWS_OWNER_REQUIRED")
    authenticate_source_bound_owner_comment(event, target)
    comment = event["comment"]
    need(event["issue"]["number"] == APPROVAL_ISSUE
         and comment.get("author_association") == "OWNER"
         and comment.get("body") == f"{APPROVAL_PREFIX} {target}",
         "EXACT_OWNER_COMMENT_REQUIRED")
    return target, int(comment["id"])


def check_provider_source(target: str, event: dict, comment_id: int, get) -> None:
    remote = get(FORGE + "/issues/comments/" + str(comment_id))
    seen = event["comment"]
    need(type(remote) is dict and remote.get("id") == comment_id
         and remote.get("author_association") == "OWNER"
         and remote.get("user", {}).get("login") == OWNER
         and remote.get("body") == seen["body"]
         and remote.get("created_at") == seen.get("created_at")
         and remote.get("issue_url") ==
             "https://api.github.com/repos/" + REPO
             + "/issues/" + str(APPROVAL_ISSUE),
         "PROVIDER_OWNER_COMMENT_DRIFT")
    main = get(FORGE + "/branches/main")
    need(type(main) is dict and main.get("name") == "main"
         and main.get("protected") is True
         and main.get("commit", {}).get("sha") == target,
         "PROTECTED_MAIN_DRIFT")
    for command, want in (
        (["git", "rev-parse", "HEAD"], target.encode()),
        (["git", "status", "--porcelain", "--untracked-files=all"], b""),
    ):
        try:
            run = subprocess.run(command, stdin=subprocess.DEVNULL,
                                 capture_output=True, timeout=20,
                                 check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise FreshOwnerActivationDenied(
                "F139_FRESH_OWNER_ACTIVATE_CHECKOUT_UNAVAILABLE"
            ) from exc
        need(run.returncode == 0 and run.stdout.strip() == want,
             "CHECKOUT_SOURCE_OR_CLEANLINESS_DRIFT")


def no_previous_attempt(root: Path) -> None:
    need(root.is_dir() and not root.is_symlink()
         and not getattr(root, "is_junction", lambda: False)(),
         "ROOT_IDENTITY_INVALID")
    for folder in root.iterdir():
        if folder.name.startswith(("f139-v59-before-", "f139-fresh-dev-")):
            need(FOLDER.fullmatch(folder.name) is not None,
                 "UNEXPECTED_ATTEMPT_PATH")
            # A prior partial create is a SPENT attempt, not safe to replay.
            raise FreshOwnerActivationDenied(
                "F139_FRESH_OWNER_ACTIVATE_PRIOR_ATTEMPT_REQUIRES_OWNER_REVIEW")


def run_once() -> dict:
    env = dict(os.environ)
    event_path = Path(env.get("GITHUB_EVENT_PATH") or ".")
    need(event_path.is_file() and not event_path.is_symlink()
         and 0 < event_path.stat().st_size <= 64000,
         "GITHUB_EVENT_FILE_MISSING")
    try:
        event = json.loads(event_path.read_bytes())
    except (ValueError, UnicodeError) as exc:
        raise FreshOwnerActivationDenied(
            "F139_FRESH_OWNER_ACTIVATE_EVENT_JSON_INVALID"
        ) from exc
    target, comment_id = event_and_source(event, env)
    get = lambda route: read_provider(route, comment_id)
    check_provider_source(target, event, comment_id, get)
    owner_run_id = int(env["GITHUB_RUN_ID"])
    need(bool(env.get("LOCALAPPDATA")), "ORIGINAL_OWNER_PROFILE_MISSING")
    root = Path(env["LOCALAPPDATA"]) / "FORGE-F139"
    old_path = root / "state.sqlite"
    need(old_path.is_file() and not old_path.is_symlink(),
         "ORIGINAL_DATABASE_MISSING")
    # Genuine Windows scheduler/SID/process attestation. On an active old
    # controller this FAILS BEFORE any file creation.
    need(_owner_windows_quiesced(old_path, target, owner_run_id),
         "ORIGINAL_TASK_NOT_INDEPENDENTLY_DISABLED")
    with SingleOwner(old_path.with_suffix(".lock")):
        original = Database.open_readonly(old_path)
        try:
            original.verify()
            before = audit_frozen_original_readonly(original)
            need(before["source_sha"] == SOURCE
                 and before["head_seq"] == HEAD_SEQ
                 and before["head_sha256"] == HEAD_SHA256
                 and original.conn.total_changes == 0,
                 "ORIGINAL_1864_EVENT_CUSTODY_DRIFT")
            no_previous_attempt(root)
            # Check source boundary BEFORE create-only archive: a moved main,
            # merged research draft or invalid blob spends no host attempt.
            read_yggdrasil_research_boundary(get)
            witness = lambda: _owner_windows_quiesced(
                old_path, target, owner_run_id)
            need(witness() is True, "PRESTAGE_OWNER_RELEASE_MOVED")
            archive_path = root / ("f139-v59-before-" + str(owner_run_id))
            cold = stage_original_cold_backup(
                original, target=target, owner_run_id=owner_run_id)
            need(cold["original_mutations"] == 0
                 and cold["source_transition_authorized"] is False,
                 "ORIGINAL_ARCHIVE_UNSAFE")
            prepared = prepare_inert_epoch(
                original, archive_path, target=target,
                owner_run_id=owner_run_id,
                task_quiescence_witness=witness,
                yggdrasil_readonly_get=get,
            )
            need(prepared["fresh_database_enabled"] is False
                 and prepared["worker_dispatched"] is False,
                 "FRESH_INERT_STAGE_UNSAFE")
            fresh_path = root / ("f139-fresh-dev-" + str(owner_run_id)) / "state.sqlite"
            with SingleOwner(fresh_path.with_suffix(".lock")):
                fresh = Database(fresh_path)
                try:
                    activated = write_fresh_native_activation_once(
                        original, fresh, get=get)
                finally:
                    fresh.close()
            need(activated["worker_dispatched"] is False
                 and activated["scientific_first_use"] is False
                 and activated["original_sqlite_mutations"] == 0
                 and activated["head_seq"] == 2
                 and audit_frozen_original_readonly(original) == before
                 and original.conn.total_changes == 0
                 and witness() is True,
                 "POSTACTIVATION_ORIGINAL_OR_CUSTODY_DRIFT")
        finally:
            original.close()
    return dict(activated,
                original_task_mutations=0, new_controller=False,
                new_scheduler=False, old_work_replay_authorized=False,
                release_without_dispatch=True)


if __name__ == "__main__":
    print("F139_FRESH_ORIGINAL_OWNER_ACTIVATED=" +
          json.dumps(run_once(), sort_keys=True))
