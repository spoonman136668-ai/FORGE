"""F139 V42 successor source evidence and cold owner predicate (read-only).

The original Windows owner remains installed at V41 successor af204acc.
This helper proves what a *future* separately authorized native installer
must reauthenticate before an af204acc -> repaired successor handoff.
It cannot pause, install, migrate, dispatch, update issue #807 or permit science.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re

from f139.local_controller import Database, SingleOwner
from f139.nci04_owner_issue import decode_unique
from f139.nci04_v41_pending_escrow import audit_committed_escrow

REPO = "spoonman136668-ai/FORGE"
OWNER = "spoonman136668-ai"
BEFORE = "af204acc983719b382bc8daf2216ec6733ca3ee7"
REPAIR = "3de3047abe855b4eb321a43ac6074b0056910113"
REPAIR_HEAD = "d393d43a28365a54c38554caea870e1ff4b9d092"
REPAIR_TREE = "70702d97771b1a6f32f468868509a2ef32121036"
REPAIR_PR = 1780
FROZEN_SEQ = 1835
FROZEN_HEAD = "2c06bb327ee8e6dd8e6d9b766d3673170dc80e93fca6e7497f89b466d19c1c83"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
EIGHT = frozenset({
    "windows_f139", "linux_genenv", "linux_native", "linux_f139",
    "windows_genenv", "windows_native", "linux", "windows",
})
SCHEMA = "forge.f139.v42.original-source-readonly-candidate.v1"


class SourceReadinessDenied(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise SourceReadinessDenied("F139_V42_READONLY_" + code)


def _get(get, name):
    need(callable(get) and type(name) is str
         and name.startswith("repos/" + REPO + "/"), "PROVIDER_SCOPE")
    value = get(name)
    need(type(value) is dict, "PROVIDER_OBJECT")
    return value


def _policy(get):
    issue = _get(get, "repos/" + REPO + "/issues/807")
    need(issue.get("state") == "open"
         and issue.get("user", {}).get("login") == OWNER
         and type(issue.get("body")) is str, "ORIGINAL_POLICY_ISSUE")
    try:
        p = json.loads(issue["body"], object_pairs_hook=decode_unique)
    except (TypeError, ValueError, UnicodeError) as exc:
        raise SourceReadinessDenied("F139_V42_READONLY_POLICY_JSON") from exc
    expected = {
        "schema": "forge.f139.native-autonomy-feed-owner-policy.v1",
        "enabled": True,
        "source_sha": BEFORE,
        "title_prefix": "F139 autonomy DEV:",
        "lanes": ["Wingless", "Yggdrasil", "TTT-Hybrid"],
        "max_issue_creations_per_cycle": 2,
        "require_owner_authored_pr": True,
        "require_single_head_commit_delta": True,
        "require_single_allowed_source_file": True,
        "scientific_first_use": False,
        "paid_model_calls": 0,
        "accepted_ref_mutations": 0,
        "new_controller": False,
        "new_scheduler": False,
        "new_queue": False,
    }
    need(type(p) is dict and set(p) == set(expected)
         and all(type(p[k]) is type(v) and p[k] == v
                 for k, v in expected.items()), "OWNER_POLICY_DRIFT")
    pending = _get(get, "repos/" + REPO + "/issues/1715")
    need(pending.get("number") == 1715 and pending.get("state") == "open"
         and pending.get("user", {}).get("login") == OWNER,
         "HISTORICAL_ESCROW_ISSUE_MISSING")
    return True


def release_source(get, target):
    """Check protected-main repair ancestry, exact Git tree, and real eight-job CI.

    This is a source-candidate proof, not an owner installer/restart permit.
    The next merge may change target, but cannot erase the authenticated
    PR1780 repair ancestry. CI is checked at *that exact* target.
    """
    need(type(target) is str and SHA40.fullmatch(target) is not None,
         "TARGET_SHA")
    p = "repos/" + REPO + "/"
    first = _get(get, p + "branches/main")
    need(first.get("name") == "main" and first.get("protected") is True
         and first.get("commit", {}).get("sha") == target,
         "PROTECTED_MAIN_NOT_TARGET")
    pr = _get(get, p + "pulls/1780")
    need(pr.get("number") == REPAIR_PR and pr.get("merged") is True
         and pr.get("state") == "closed"
         and pr.get("merge_commit_sha") == REPAIR
         and pr.get("user", {}).get("login") == OWNER
         and pr.get("head", {}).get("sha") == REPAIR_HEAD
         and pr.get("base", {}).get("ref") == "main",
         "ORIGINAL_REPAIR_PR_NOT_VERIFIED")
    merged = _get(get, p + "git/commits/" + REPAIR)
    head = _get(get, p + "git/commits/" + REPAIR_HEAD)
    need(merged.get("sha") == REPAIR and head.get("sha") == REPAIR_HEAD
         and merged.get("tree", {}).get("sha") == REPAIR_TREE
         and head.get("tree", {}).get("sha") == REPAIR_TREE
         and merged.get("parents", [{}])[0].get("sha") == BEFORE,
         "ORIGINAL_REPAIR_TREE_OR_PARENT_DRIFT")
    for ancestor in (BEFORE, REPAIR):
        cmp = _get(get, p + "compare/" + ancestor + "..." + target
                   + "?per_page=1&page=2")
        need(cmp.get("status") in ("ahead", "identical")
             and cmp.get("behind_by") == 0
             and cmp.get("merge_base_commit", {}).get("sha") == ancestor,
             "PROTECTED_RELEASE_ANCESTRY_DRIFT")
    _policy(get)
    inventory = _get(get, p + "actions/runs?head_sha=" + target
                     + "&event=push&branch=main&per_page=100")
    runs = inventory.get("workflow_runs")
    need(type(runs) is list and len(runs) <= 100, "CI_INVENTORY")
    selected = [r for r in runs if type(r) is dict and
                r.get("name") == "FORGE public Linux and Windows qualification"]
    need(len(selected) == 1, "EXACT_ONE_MAIN_QUALIFICATION")
    run = selected[0]
    need(run.get("head_sha") == target and run.get("head_branch") == "main"
         and run.get("event") == "push"
         and run.get("status") == "completed"
         and run.get("conclusion") == "success"
         and type(run.get("id")) is int and run["id"] > 0
         and type(run.get("run_attempt")) is int
         and run["run_attempt"] == 1
         and run.get("actor", {}).get("login") == OWNER,
         "MAIN_CI_NOT_QUALIFIED")
    jobs = _get(get, p + "actions/runs/" + str(run["id"]) + "/jobs?per_page=100")
    rows = jobs.get("jobs")
    need(type(rows) is list and len(rows) == len(EIGHT)
         and {row.get("name") for row in rows if type(row) is dict} == EIGHT
         and all(type(row) is dict and row.get("status") == "completed"
                 and row.get("conclusion") == "success" for row in rows),
         "MANDATORY_EIGHT_JOB_REGRESSION_FAILED")
    last = _get(get, p + "branches/main")
    need(last.get("commit", {}).get("sha") == target, "MAIN_MOVED")
    return {
        "schema": SCHEMA, "target_source_sha": target,
        "repaired_ancestor_sha": REPAIR, "repaired_tree_sha": REPAIR_TREE,
        "original_source_sha": BEFORE, "main_qualification_run_id": run["id"],
        "main_qualification_job_count": len(rows),
        "live_owner_verified": False, "source_transition_authorized": False,
        "owner_task_mutations": 0, "scientific_first_use": False,
        "hybrid_scientific_admission": False, "new_dispatches": 0,
    }


def original_owner_cold_read(db):
    """Inspect *actual* original SQLite under the pre-acquired original mutex.

    No lock is acquired here because the native owner caller must validate
    the original Windows task, SID and mutex itself before entering.
    Reject historical replay, any new source event, and orphaned #1715.
    """
    need(type(db) is Database
         and getattr(db, "_readonly_opened", False) is True
         and isinstance(db.filename, Path)
         and db.filename.is_absolute() and db.filename.name == "state.sqlite"
         and not db.filename.is_symlink()
         and SingleOwner.held(db.filename.with_suffix(".lock"))
         and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1,
         "REAL_ORIGINAL_MUTEX_AND_READONLY_REQUIRED")
    before = db.meta().copy()
    changed = db.conn.total_changes
    db.verify()
    need(db.meta() == before and db.conn.total_changes == changed
         and changed == 0 and before.get("source_sha") == BEFORE
         and before.get("head_seq") == FROZEN_SEQ
         and before.get("head_hash") == FROZEN_HEAD
         and before.get("enabled") == 1
         and before.get("legacy_suspended") == 1
         and db.dual_native_schema()
         and db.ready() is None and not db.actives(),
         "ORIGINAL_ACTIVATED_HEAD_DRIFT")
    kinds = Counter(row["stage"] for row in db.conn.execute(
        "SELECT stage FROM tasks"))
    need(kinds == Counter({"VERIFIED": 153, "QUARANTINED": 56}),
         "ORIGINAL_153_56_TASK_CUSTODY")
    need(audit_committed_escrow(db) == "PAIRED_V41_TRANSITION",
         "ESCROW_CHAIN_NOT_PAIRED")
    # The original #1715 was escrowed only; do not reinterpret as admitted.
    for row in db.conn.execute(
            "SELECT payload FROM events WHERE kind='NATIVE_DEVELOPMENT_ADMITTED'"):
        try:
            event = json.loads(row["payload"])
        except (ValueError, UnicodeError) as exc:
            raise SourceReadinessDenied(
                "F139_V42_READONLY_ADMISSION_EVENT_UNREADABLE") from exc
        need(event.get("issue_number") != 1715
             and event.get("issue_id") != 6333201763,
             "ESCROWED_1715_WAS_ADMITTED")
    need(db.meta() == before and db.conn.total_changes == 0,
         "ORIGINAL_READ_MUTATED")
    return {
        "schema": SCHEMA, "original_source_sha": BEFORE,
        "original_head_seq": FROZEN_SEQ,
        "original_head_sha256": FROZEN_HEAD,
        "verified_tasks": 153, "quarantined_tasks": 56,
        "pending_issue_number": 1715, "pending_issue_admitted": False,
        "original_owner_mutations": 0, "source_transition_authorized": False,
        "new_dispatches": 0, "scientific_first_use": False,
    }
