"""V19 read-only original-owner release readiness witness; NEVER a cutover.

A source/CI/owner/ledger snapshot is not a release permit. In particular,
the V18 original CLI has no qualified V19 source-transition verb. This helper
cannot alter protected main, owner policy, running task, SQLite or Git refs.
"""
from __future__ import annotations

import json
import re
from typing import Callable

from f139.local_controller import Database, SingleOwner
from f139.nci04_autonomy_feed import inspect_policy

SCHEMA = "forge.f139.v19.original-owner-release-readiness-nowrite.v1"
SOURCE = "d8bccc604f8607bf10f9d8bc6aa568d1f98af559"
TARGET = "ea2d1c99d7afc1e991510d51168dd010a0b56ec5"
FORGE = "spoonman136668-ai/FORGE"
PR = 1052
REQUIRED_RUNS = (40845080882, 40845080869, 40845080913)
SHA64 = re.compile(r"[a-f0-9]{64}\Z")


class V19ReleasePreflightDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise V19ReleasePreflightDenied("F139_V19_RELEASE_NOWRITE_" + reason)


def _original_state(db: Database) -> dict:
    """Read original SQLite under its existing owner mutex; never mutate it."""
    need(type(db) is Database, "ORIGINAL_DATABASE_REQUIRED")
    need(SingleOwner.held(db.filename.with_suffix(".lock")),
         "EXISTING_ORIGINAL_MUTEX_REQUIRED")
    need(getattr(db, "_readonly_opened", False) is True
         and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1,
         "SQLITE_MODE_RO_REQUIRED")
    db.verify()
    meta = db.meta().copy()
    need(meta["source_sha"] == SOURCE
         and meta["enabled"] == 1 and meta["legacy_suspended"] == 1
         and type(meta["head_seq"]) is int and meta["head_seq"] > 0
         and type(meta["head_hash"]) is str
         and SHA64.fullmatch(meta["head_hash"]) is not None,
         "ORIGINAL_V18_SOURCE_OR_LEDGER_HEAD_DRIFT")
    need(db.ready() is None and not db.actives(),
         "ORIGINAL_NATIVE_WORK_STILL_IN_FLIGHT")
    events = list(db.conn.execute(
        "SELECT seq,sha,payload FROM events "
        "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq"))
    need(bool(events), "ORIGINAL_V18_TRANSITION_NOT_CUSTODIED")
    transitions = [json.loads(row["payload"]) for row in events]
    v18 = [(row, doc) for row, doc in zip(events, transitions)
           if doc.get("schema") == "forge.f139.source-transition.v18"]
    need(len(v18) == 1 and v18[-1][0]["seq"] == events[-1]["seq"]
         and v18[-1][1].get("to_source_sha") == SOURCE
         and v18[-1][1].get("v2_receipt_authorized") is False,
         "ORIGINAL_TERMINAL_V18_TRANSITION_DRIFT")
    return {
        "source_sha": SOURCE,
        "head_seq": meta["head_seq"],
        "head_sha256": meta["head_hash"],
        "v18_transition_sha256": v18[-1][0]["sha"],
    }


def _remote_release_state(get: Callable[[str], object]) -> dict:
    """Independently read original GitHub authority; no remote POST/PUT."""
    policy = inspect_policy(get(f"repos/{FORGE}/issues/807"), SOURCE)
    need(policy["enabled"] is True, "ORIGINAL_V18_OWNER_POLICY_DISABLED")
    protected = get(f"repos/{FORGE}/branches/main")
    need(type(protected) is dict and protected.get("protected") is True
         and type(protected.get("commit")) is dict
         and protected["commit"].get("sha") == SOURCE,
         "PROTECTED_MAIN_MOVED_FROM_RUNNING_V18")
    pr = get(f"repos/{FORGE}/pulls/{PR}")
    need(type(pr) is dict and pr.get("number") == PR
         and pr.get("state") == "open"
         and pr.get("draft") is False and pr.get("merged_at") is None
         and type(pr.get("head")) is dict
         and pr["head"].get("sha") == TARGET
         and pr["head"].get("ref") ==
             "release/f139-v19-mainline-source-integration-20261028"
         and type(pr.get("base")) is dict
         and pr["base"].get("ref") == "main"
         and pr["base"].get("sha") == SOURCE
         and type(pr.get("user")) is dict
         and pr["user"].get("login") == "spoonman136668-ai",
         "REVIEWED_SOURCE_PR_IDENTITY_OR_TARGET_DRIFT")
    for run_id in REQUIRED_RUNS:
        run = get(f"repos/{FORGE}/actions/runs/{run_id}")
        need(type(run) is dict and run.get("id") == run_id
             and run.get("head_sha") == TARGET
             and run.get("status") == "completed"
             and run.get("conclusion") == "success",
             "EXACT_HEAD_QUALIFICATION_RUN_NOT_SUCCESS")
    # Repeat authority reads to deny a branch/policy drift during snapshot.
    second = get(f"repos/{FORGE}/branches/main")
    need(second == protected, "PROTECTED_MAIN_CHANGED_DURING_READ")
    again = inspect_policy(get(f"repos/{FORGE}/issues/807"), SOURCE)
    need(again == policy and again["enabled"] is True,
         "ORIGINAL_OWNER_POLICY_CHANGED_DURING_READ")
    return {"pr_number": PR, "reviewed_target_sha": TARGET,
            "qualified_run_ids": list(REQUIRED_RUNS)}


def v19_original_release_readonly_preflight(
    db: Database, *, original_get: Callable[[str], object],
    owner_witness: Callable[[], bool],
) -> dict:
    """No transition or deployment authority, even when all reads pass.

    Must be called under the genuine existing SingleOwner in the original
    Windows process. Hosted tests inject only fakes/disposable ledger state.
    """
    need(callable(original_get) and callable(owner_witness)
         and owner_witness() is True,
         "ORIGINAL_OWNER_OR_AUTHENTICATED_GET_REQUIRED")
    first = _original_state(db)
    source = _remote_release_state(original_get)
    second = _original_state(db)
    need(first == second and owner_witness() is True,
         "ORIGINAL_HEAD_OR_OWNER_MOVED_AFTER_READ")
    return {
        "schema": SCHEMA,
        "disposition": "ORIGINAL_V18_AND_V19_RELEASE_SOURCE_READONLY_ONLY",
        "from_source_sha": SOURCE,
        "candidate_source_sha": TARGET,
        "original_head_seq": first["head_seq"],
        "original_head_sha256": first["head_sha256"],
        "original_v18_transition_sha256": first["v18_transition_sha256"],
        "reviewed_pr": source["pr_number"],
        "qualified_run_ids": source["qualified_run_ids"],
        "read_only": True,
        "source_transition_to_v19_implemented": False,
        "installed_checkout_verified": False,
        "scheduled_task_quiescence_verified": False,
        "immutable_original_backup_verified": False,
        "rollback_rehearsal_verified": False,
        "runtime_cutover_authorized": False,
        "original_sqlite_writes": 0,
        "github_writes": 0,
        "provider_requests": 0,
        "paid_api_calls": 0,
        "scientific_first_use": False,
        "accepted_ref_mutations": 0,
        "new_controller": False,
        "new_scheduler": False,
        "new_queue": False,
    }
