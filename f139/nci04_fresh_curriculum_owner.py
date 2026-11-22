"""Read-only original-owner history projection for F139 DEV selection.

No proposed candidate is authenticated by this adapter. Only a separately
source-qualified native candidate can be used by a future publication route.
This function cannot create issues, dispatch work, or modify controller state.
"""
from __future__ import annotations

from f139.local_controller import Database, SingleOwner
from f139.nci04_fresh_curriculum import need, select_next, sha
from f139.nci04_fresh_dev_exclusions import SCHEMA as EXCLUSION_SCHEMA
from f139.nci04_fresh_native_activation import audit_fresh_native_activation
from f139.nci04_fresh_native_owner_route import _sealed_json
from f139.nci04_fresh_worker_protocol import SOURCE, TARGET, TARGET_TREE
from f139.nci04_fresh_lifecycle import read_lifecycle
from f139.nci04_native_contract import digest


def select_cold_owner_dev_candidate(*, db: Database, owner_key: str,
                                    proposals: list[dict],
                                    remaining_cost_units: int) -> dict | None:
    """Advisory selection from authenticated original SQLite and sealed history.

    The existing single Windows owner must hold the lock; read_lifecycle
    independently audits source, activation, event chain, signature, task rows,
    terminal evidence ZIPs and provider receipts. All pre-epoch consumed after
    hashes remain excluded. A committed uncertain publication blocks selection.
    """
    need(type(db) is Database
         and SingleOwner.held(db.filename.with_suffix(".lock")),
         "COLD_ORIGINAL_OWNER_MUTEX_REQUIRED")
    previous = (db.meta()["head_seq"], db.meta()["head_hash"],
                db.conn.total_changes)
    release, entries = read_lifecycle(db, owner_key)
    activation = audit_fresh_native_activation(db)
    need(release["admission_source_sha"] == SOURCE
         and activation["source_sha"] == SOURCE
         and activation["accepted_yggdrasil_main_sha"] == TARGET
         and 1 <= len(entries) <= 4096,
         "ORIGINAL_SOURCE_OR_HISTORY_DRIFT")
    consumed, raw = _sealed_json(
        db.filename.parent / "consumed-development-identities.json")
    old = consumed.get("old_source_after_sha256")
    need(digest(raw) == activation["consumed_exclusions_sha256"]
         and consumed.get("schema") == EXCLUSION_SCHEMA
         and consumed.get("previous_work_replay_authorized") is False
         and type(old) is list and len(old) <= 10000
         and len(old) == len(set(old))
         and all(sha(x) for x in old),
         "SEALED_PRE_EPOCH_CONSUMED_DRIFT")
    need(entries[-1].get("publication_attempt") is None,
         "PRIOR_PUBLICATION_ALREADY_COMMITTED")

    spent_after = set(old)
    spent_intent = set()
    history = []
    for entry in entries:
        record = entry["record"]
        need(record["source_sha"] == SOURCE
             and record["native_target_tree"] == TARGET_TREE,
             "COLD_ENTRY_SOURCE_DRIFT")
        publication = entry.get("publication_attempt")
        if publication is not None:
            # A committed POST is spent even if its remote acknowledgment
            # disappeared. The event chain was already audited above.
            need(sha(publication["after_sha256"])
                 and sha(publication["intent_sha256"]),
                 "PUBLICATION_SPENT_IDENTITY_INVALID")
            spent_after.add(publication["after_sha256"])
            spent_intent.add(publication["intent_sha256"])
        stage = ("NEGATIVE" if entry.get("negative")
                 else entry["stage"])
        custody = entry.get("custody")
        terminal = (custody["evidence_manifest_sha256"]
                    if stage == "VERIFIED" else None)
        history.append({
            "after_sha256": record["after_sha256"],
            "intent_sha256": record["native_intent_sha256"],
            "stage": stage,
            "terminal_evidence_sha256": terminal,
        })
    selection = select_next(
        history=history, proposals=proposals, source_sha=SOURCE,
        target_tree_sha=TARGET_TREE,
        remaining_cost_units=remaining_cost_units,
        spent_after_sha256=frozenset(spent_after),
        spent_intent_sha256=frozenset(spent_intent))
    need((db.meta()["head_seq"], db.meta()["head_hash"],
          db.conn.total_changes) == previous,
         "READONLY_LEDGER_MUTATED")
    return selection


def plan_next_structured_dev_from_original_owner(
        *, db: Database, api, owner_key: str,
        remaining_cost_units: int) -> dict | None:
    """Read-only authenticated planning; intentionally NEVER publish/dispatch.

    The original source-bound Windows owner must hold the kernel lock. First
    authenticate its actual installed source, SID, Task Scheduler process,
    source release and provider policy. Then re-read the signed SQLite history,
    frozen pre-epoch exclusions, and accepted Yggdrasil Git tree/blob before
    authoring a bounded source candidate. Re-select against the independently
    reaudited ledger. The eventual one-shot publisher (NOT this function) must
    durably commit a versioned attempt before remote POST and read back the
    provider result. CI cannot authorize that publisher or owner rebind.
    """
    from f139.nci04_fresh_lifecycle import authenticate_runtime_owner
    from f139.nci04_fresh_structured_dev import (
        generate_from_original_owner, matching_plan,
    )

    need(type(db) is Database
         and SingleOwner.held(db.filename.with_suffix(".lock")),
         "PLANNER_ORIGINAL_MUTEX_REQUIRED")
    original = (db.meta()["head_seq"], db.meta()["head_hash"],
                db.conn.total_changes)
    release, entries = read_lifecycle(db, owner_key)
    authenticate_runtime_owner(db, api, release, owner_key)
    need(entries[-1]["stage"] == "VERIFIED"
         and entries[-1].get("negative") is None
         and entries[-1].get("publication_attempt") is None,
         "PLANNER_MUST_FOLLOW_UNPUBLISHED_VERIFIED_TERMINAL")
    activation = audit_fresh_native_activation(db)
    consumed, consumed_raw = _sealed_json(
        db.filename.parent / "consumed-development-identities.json")
    old = consumed.get("old_source_after_sha256")
    need(activation is not None
         and consumed.get("schema") == EXCLUSION_SCHEMA
         and consumed.get("previous_work_replay_authorized") is False
         and digest(consumed_raw) == activation["consumed_exclusions_sha256"]
         and type(old) is list and len(old) <= 10000
         and len(old) == len(set(old)) and all(sha(v) for v in old),
         "PLANNER_SEALED_CONSUMED_HISTORY_DRIFT")
    spent = set(old)
    for e in entries:
        spent.add(e["record"]["after_sha256"])
        publication = e.get("publication_attempt")
        if publication:
            spent.add(publication["after_sha256"])
    latest = entries[-1]["record"]["after_sha256"]
    need(latest in spent and len(spent) <= 10000,
         "PLANNER_LAST_TERMINAL_NOT_CONSUMED")
    pool = generate_from_original_owner(
        api=api, initial_record=entries[0]["record"],
        consumed_after=spent, last_verified_after=latest)
    proposal = select_cold_owner_dev_candidate(
        db=db, owner_key=owner_key, proposals=[p["selection"] for p in pool],
        remaining_cost_units=remaining_cost_units)
    need((db.meta()["head_seq"], db.meta()["head_hash"],
          db.conn.total_changes) == original,
         "PLANNER_LEDGER_MUTATED")
    if proposal is None:
        return None
    return matching_plan(pool, proposal)
