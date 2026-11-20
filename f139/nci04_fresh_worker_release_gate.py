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
