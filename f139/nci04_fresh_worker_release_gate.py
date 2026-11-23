"""GET-only exact release-ref qualification for a freshly admitted F139 DEV ticket.

This is deliberately narrower than owner release.  It never signs, claims,
schedules, dispatches, retargets a task, mutates a ref or authorizes science.
The genuine original Windows owner must independently revalidate SID, task,
source, immutable old custody and fresh SQLite under the original mutex.
"""
from __future__ import annotations

from typing import Callable

from f139.nci04_native_contract import canonical
from f139.nci04_owner_issue import inspect_owner_issue
from f139.nci04_fresh_native_activation import ACTIVATION_SCHEMA
from f139.nci04_fresh_native_intake import SCHEMA as INTAKE_SCHEMA

FORGE = "repos/spoonman136668-ai/FORGE"
YGG = "repos/spoonman136668-ai/Yggdrasil"
SOURCE = "408139c0a10fd4836a22422c8df041aa64dfa001"
SOURCE_TREE = "4f35d3965bfd2d8688586600926445008e16f5b9"
WORKER_BLOB = "74dd90e6d71da6b53898c7a80d5362f1b0e6af27"
TARGET = "5e74f8db85b2f5839c42148c0dfba69a88b1a2c9"
TARGET_TREE = "180008502f6bdfe5a06c3d0d6f47f941dd01f20b"
TICKET_ISSUE = 1849
WORKER_PATH = ".github/workflows/forge-f139-development-worker.yml"
WORKER_REF = "f139-owner-release-" + SOURCE
SCHEMA = "forge.f139.fresh-development-worker-release-readonly.v1"


class FreshWorkerReleaseDenied(ValueError):
    pass


def need(condition: bool, why: str) -> None:
    if not condition:
        raise FreshWorkerReleaseDenied("F139_FRESH_WORKER_RELEASE_" + why)


def _read(get: Callable, route: str) -> dict:
    """The caller must supply an authenticated, strictly GET-only provider."""
    try:
        doc = get(route)
    except (OSError, ValueError, KeyError) as exc:
        raise FreshWorkerReleaseDenied(
            "F139_FRESH_WORKER_RELEASE_PROVIDER_UNAVAILABLE"
        ) from exc
    need(type(doc) is dict, "PROVIDER_NOT_OBJECT")
    return doc


def inspect_fresh_worker_release(
    activation: dict, intake: dict, *, get: Callable[[str], dict],
) -> dict:
    """Reject moved/unprotected worker refs and altered once-only issue bytes.

    Positive results attest ONLY public source and issue metadata. Even a
    genuine original-owner SQLite record cannot be inferred from caller-supplied
    dicts. This helper must never be used as a permission to dispatch or rebind.
    """
    need(callable(get) and type(activation) is dict and type(intake) is dict,
         "ARGUMENTS_INVALID")
    need(activation.get("schema") == ACTIVATION_SCHEMA
         and activation.get("source_sha") == SOURCE
         and activation.get("development_only") is True
         and activation.get("scientific_first_use") is False
         and activation.get("worker_dispatch_authorized") is False
         and activation.get("model_continuation_authorized") is False
         and activation.get("paid_model_calls") == 0
         and type(activation.get("remote_issue_number_floor")) is int
         and activation["remote_issue_number_floor"] < TICKET_ISSUE,
         "FRESH_ACTIVATION_NOT_PINNED")
    need(intake.get("schema") == INTAKE_SCHEMA
         and intake.get("source_sha") == SOURCE
         and intake.get("owner_run_id") == activation.get("owner_run_id")
         and intake.get("issue_number") == TICKET_ISSUE
         and type(intake.get("issue_id")) is int
         and intake["issue_id"] > 0
         and intake.get("lane") == "Yggdrasil"
         and intake.get("native_target_commit") == TARGET
         and intake.get("native_target_tree") == TARGET_TREE
         and intake.get("native_path") == "yggdrasil/public_causal_cells.py"
         and intake.get("scientific_first_use") is False
         and intake.get("worker_dispatch_authorized") is False
         and intake.get("model_continuation_authorized") is False
         and intake.get("paid_model_calls") == 0
         and intake.get("remote_issue_number_floor") ==
             activation["remote_issue_number_floor"],
         "FRESH_READY_TICKET_INVALID")

    ref_route = FORGE + "/branches/" + WORKER_REF
    def verify_ref() -> None:
        branch = _read(get, ref_route)
        need(branch.get("name") == WORKER_REF
             and branch.get("protected") is True
             and type(branch.get("commit")) is dict
             and branch["commit"].get("sha") == SOURCE,
             "WORKER_REF_MISSING_UNPROTECTED_OR_MOVED")

    verify_ref()
    commit = _read(get, FORGE + "/git/commits/" + SOURCE)
    need(commit.get("sha") == SOURCE
         and type(commit.get("tree")) is dict
         and commit["tree"].get("sha") == SOURCE_TREE,
         "WORKER_COMMIT_TREE_DRIFT")

    path = _read(
        get, FORGE + "/contents/" + WORKER_PATH + "?ref=" + SOURCE)
    need(path.get("path") == WORKER_PATH
         and path.get("type") == "file"
         and path.get("sha") == WORKER_BLOB
         and type(path.get("size")) is int and path["size"] > 0,
         "WORKER_WORKFLOW_BLOB_DRIFT")

    target = _read(get, YGG + "/branches/main")
    need(target.get("name") == "main"
         and target.get("protected") is True
         and target.get("commit", {}).get("sha") == TARGET,
         "YGGDRASIL_ACCEPTED_MAIN_DRIFT")
    native_commit = _read(get, YGG + "/git/commits/" + TARGET)
    need(native_commit.get("sha") == TARGET
         and native_commit.get("tree", {}).get("sha") == TARGET_TREE,
         "YGGDRASIL_ACCEPTED_TREE_DRIFT")

    issue_route = FORGE + "/issues/" + str(TICKET_ISSUE)
    issue = _read(get, issue_route)
    native = inspect_owner_issue(
        issue, protected_main=SOURCE,
        authenticated_target_commit=TARGET,
        authenticated_target_tree=TARGET_TREE)
    need(native.number == TICKET_ISSUE
         and native.issue_id == intake["issue_id"]
         and native.ticket == intake.get("ticket")
         and native.issue_body_sha256 == intake.get("issue_body_sha256")
         and native.native_intent_sha256 == intake.get("native_intent_sha256")
         and native.qualification_key == intake.get("qualification_key")
         and native.candidate.path == intake["native_path"]
         and native.candidate.before_sha256 == intake.get("before_sha256")
         and native.candidate.after_sha256 == intake.get("after_sha256"),
         "ADMITTED_ISSUE_SOURCE_IDENTITY_DRIFT")

    # Do not accept a ref/issue changed during the bounded provider read.
    need(canonical(issue) == canonical(_read(get, issue_route)),
         "ISSUE_CHANGED_DURING_READ")
    verify_ref()
    need(_read(get, YGG + "/branches/main") == target,
         "YGGDRASIL_MAIN_MOVED")
    return {
        "schema": SCHEMA,
        "source_sha": SOURCE,
        "source_tree_sha": SOURCE_TREE,
        "issue_number": TICKET_ISSUE,
        "ticket": native.ticket,
        "worker_release_branch": WORKER_REF,
        "worker_workflow_blob": WORKER_BLOB,
        "worker_ref_source_verified": True,
        "issue_source_verified": True,
        "original_windows_owner_release_verified": False,
        "fresh_sqlite_cold_custody_verified": False,
        "owner_task_rebind_authorized": False,
        "worker_dispatch_authorized": False,
        "scientific_first_use": False,
        "paid_model_calls": 0,
    }


# Actual owner rebind was separately executed on the original Windows host.
# This read-only provider cross-check does NOT authenticate caller-supplied
# local bytes as a live Task Scheduler snapshot, nor grant worker dispatch.
REBIND_SCHEMA = "forge.f139.fresh-existing-task-rebound-disabled.v1"
REBIND_MERGE = "0f37922c8ccd9b218ef82987ef62d80087374937"
REBIND_RUN_ID = 44852932511
REBIND_JOB_ID = 136688296118
REBIND_COMMENT_ID = 7055483732
REBIND_FRESH_RUN_ID = 44831323193
REBIND_FRESH_HEAD = "b099aba6750a4ae323ffd5291ea0ae940b1403b4063aa89f34521fe513383337"
REBIND_FIELDS = frozenset((
    "schema", "source_sha", "owner_workflow_source_sha", "owner_run_id",
    "fresh_activation_run_id", "new_database_path", "task_name",
    "original_head_seq", "fresh_head_seq", "fresh_head_sha256",
    "existing_task_only", "task_disabled", "worker_dispatched",
    "scientific_first_use", "model_continuation_authorized",
    "paid_model_calls", "original_sqlite_mutations",
))


def inspect_rebound_disabled_source(activation: dict, intake: dict,
                                    local_receipt: dict, *,
                                    get: Callable[[str], dict]) -> dict:
    """Independently re-read original owner run and immutable issue source.

    The passed local JSON is untrusted input: this function verifies its exact
    format and source consistency but CANNOT verify current Windows SID/task
    state or grant dispatch authority. No GET here mutates SQLite or tasks.
    """
    import ntpath
    need(type(local_receipt) is dict
         and set(local_receipt) == REBIND_FIELDS,
         "REBIND_RECEIPT_FIELDS_DRIFT")
    p = local_receipt.get("new_database_path")
    need(type(p) is str and len(p) < 512
         and ntpath.isabs(p)
         and not any(part in (".", "..") for part in p.replace("/", "\\").split("\\"))
         and ntpath.normpath(p).lower().endswith(
             "\\forge-f139\\f139-fresh-dev-" + str(REBIND_FRESH_RUN_ID)
             + "\\state.sqlite"),
         "REBIND_LOCAL_PATH_INVALID")
    need(local_receipt.get("schema") == REBIND_SCHEMA
         and local_receipt.get("source_sha") == SOURCE
         and local_receipt.get("owner_workflow_source_sha") == REBIND_MERGE
         and type(local_receipt.get("owner_run_id")) is int
         and local_receipt["owner_run_id"] == REBIND_RUN_ID
         and type(local_receipt.get("fresh_activation_run_id")) is int
         and local_receipt["fresh_activation_run_id"] == REBIND_FRESH_RUN_ID
         and local_receipt.get("task_name") == "FORGE-F139-UnifiedController"
         and type(local_receipt.get("original_head_seq")) is int
         and local_receipt["original_head_seq"] == 1864
         and type(local_receipt.get("fresh_head_seq")) is int
         and local_receipt["fresh_head_seq"] == 4
         and local_receipt.get("fresh_head_sha256") == REBIND_FRESH_HEAD
         and local_receipt.get("existing_task_only") is True
         and local_receipt.get("task_disabled") is True
         and local_receipt.get("worker_dispatched") is False
         and local_receipt.get("scientific_first_use") is False
         and local_receipt.get("model_continuation_authorized") is False
         and type(local_receipt.get("paid_model_calls")) is int
         and local_receipt["paid_model_calls"] == 0
         and type(local_receipt.get("original_sqlite_mutations")) is int
         and local_receipt["original_sqlite_mutations"] == 0,
         "REBIND_RECEIPT_UNTRUSTED_OR_MUTATED")
    release = inspect_fresh_worker_release(activation, intake, get=get)
    run_route = FORGE + "/actions/runs/" + str(REBIND_RUN_ID)
    run = _read(get, run_route)
    need(run.get("id") == REBIND_RUN_ID
         and run.get("event") == "issue_comment"
         and run.get("run_attempt") == 1
         and run.get("status") == "completed"
         and run.get("conclusion") == "success"
         and run.get("head_sha") == REBIND_MERGE
         and run.get("path") ==
             ".github/workflows/f139-fresh-original-owner-rebind.yml"
         and run.get("actor", {}).get("login") == "spoonman136668-ai"
         and run.get("repository", {}).get("full_name") ==
             "spoonman136668-ai/FORGE",
         "REBIND_ORIGINAL_OWNER_RUN_NOT_PROVEN")
    jobs_route = run_route + "/jobs?per_page=100"
    jobs = _read(get, jobs_route)
    rows = jobs.get("jobs")
    need(jobs.get("total_count") == 1
         and type(rows) is list and len(rows) == 1
         and rows[0].get("id") == REBIND_JOB_ID
         and rows[0].get("name") == "rebind-disabled-original-task"
         and rows[0].get("runner_name") == "FORGE-CODEX-REMOTE"
         and rows[0].get("status") == "completed"
         and rows[0].get("conclusion") == "success"
         and any(step.get("name") ==
                 "Independently rebind existing disabled original task once"
                 and step.get("conclusion") == "success"
                 for step in rows[0].get("steps", [])),
         "REBIND_ORIGINAL_WINDOWS_JOB_NOT_PROVEN")
    comment_route = FORGE + "/issues/comments/" + str(REBIND_COMMENT_ID)
    comment = _read(get, comment_route)
    need(comment.get("id") == REBIND_COMMENT_ID
         and comment.get("body") ==
             "F139-FRESH-DEV-TASK-REBIND " + REBIND_MERGE
             + " " + str(REBIND_FRESH_RUN_ID)
         and comment.get("author_association") == "OWNER"
         and comment.get("user", {}).get("login") == "spoonman136668-ai",
         "REBIND_OWNER_COMMENT_NOT_AUTHENTICATED")
    need(_read(get, run_route) == run
         and _read(get, comment_route) == comment,
         "REBIND_PROVIDER_CHANGED_DURING_READ")
    return {
        **release,
        "schema": "forge.f139.fresh-post-rebind-source-preflight.v1",
        "original_rebind_run_verified": True,
        "owner_comment_verified": True,
        "rebind_receipt_source_consistent": True,
        "live_windows_task_state_verified": False,
        "owner_task_rebind_authorized": False,
        "worker_dispatch_authorized": False,
        "scientific_first_use": False,
    }
