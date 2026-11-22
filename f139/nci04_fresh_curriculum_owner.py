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
