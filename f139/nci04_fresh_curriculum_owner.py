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
from f139.nci04_fresh_lifecycle import (
    PUBLISH_SCHEMA, PUBLISH_SCHEMA_STRUCTURED, PUBLISH_SCHEMA_HYPOTHESIS_V3,
    read_lifecycle,
)
from f139.nci04_native_contract import digest


# Every structured publication consumes exactly the same two DEV cost units
# advertised to the selector, including a committed POST without an ACK.
# This total is derived from the source-authenticated cold lifecycle; it is
# never reset on the next owner tick or replenished by a CI-only terminal.
STRUCTURED_DEV_COST_UNITS = 2
HYPOTHESIS_V3_COST_UNITS = 2
HYPOTHESIS_V3_BUDGET_CEILING = 64


def remaining_structured_dev_budget(entries: list[dict], ceiling: int) -> int:
    """Ledger-derived, monotone budget for the current fresh DEV epoch.

    The existing cold owner audits these publication attempts and signatures
    before calling this helper. It never measures scientific utility.
    """
    need(type(ceiling) is int and 0 <= ceiling <= 10000
         and type(entries) is list and 1 <= len(entries) <= 4096,
         "STRUCTURED_BUDGET_INPUT_INVALID")
    attempts = 0
    for entry in entries:
        need(type(entry) is dict
             and type(entry.get("record")) is dict,
             "STRUCTURED_BUDGET_ENTRY_INVALID")
        attempt = entry.get("publication_attempt")
        if attempt is None:
            continue
        need(type(attempt) is dict
             and attempt.get("schema") in (PUBLISH_SCHEMA,
                                            PUBLISH_SCHEMA_STRUCTURED,
                                            PUBLISH_SCHEMA_HYPOTHESIS_V3),
             "STRUCTURED_BUDGET_ATTEMPT_INVALID")
        if attempt["schema"] == PUBLISH_SCHEMA_STRUCTURED:
            attempts += 1
    used = attempts * STRUCTURED_DEV_COST_UNITS
    need(used <= ceiling, "STRUCTURED_BUDGET_ALREADY_EXCEEDED")
    return ceiling - used


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
    # Debit all previously committed V2 attempts, even on lost POST ACK.
    # Passing the original per-epoch ceiling again must not reset it.
    available_cost_units = remaining_structured_dev_budget(
        entries, remaining_cost_units)
    proposal = select_cold_owner_dev_candidate(
        db=db, owner_key=owner_key, proposals=[p["selection"] for p in pool],
        remaining_cost_units=available_cost_units)
    need((db.meta()["head_seq"], db.meta()["head_hash"],
          db.conn.total_changes) == original,
         "PLANNER_LEDGER_MUTATED")
    if proposal is None:
        return None
    return matching_plan(pool, proposal)


def remaining_hypothesis_v3_budget(entries: list[dict], ceiling: int) -> int:
    """Ledger-derived monotone budget for V3 preregistered hypothesis cycles."""
    need(type(ceiling) is int and 0 <= ceiling <= 10000
         and type(entries) is list and 1 <= len(entries) <= 4096,
         "HYPOTHESIS_V3_BUDGET_INPUT_INVALID")
    attempts = 0
    for entry in entries:
        need(type(entry) is dict and type(entry.get("record")) is dict,
             "HYPOTHESIS_V3_BUDGET_ENTRY_INVALID")
        attempt = entry.get("publication_attempt")
        if attempt is None:
            continue
        if attempt.get("schema") == PUBLISH_SCHEMA_HYPOTHESIS_V3:
            attempts += 1
    used = attempts * HYPOTHESIS_V3_COST_UNITS
    need(used <= ceiling, "HYPOTHESIS_V3_BUDGET_ALREADY_EXCEEDED")
    return ceiling - used


def plan_next_hypothesis_v3_from_original_owner(
        *, db: Database, api, owner_key: str,
        remaining_cost_units: int = HYPOTHESIS_V3_BUDGET_CEILING) -> dict | None:
    """Read-only authenticated V3 hypothesis planner using preregistered evaluator."""
    import base64
    import binascii
    from f139.nci04_fresh_lifecycle import authenticate_runtime_owner
    from f139.nci04_fresh_successor_producer import REPO
    from f139.nci04_fresh_yggdrasil_boundary import (
        ACCEPTED_NATIVE_BLOB, ACCEPTED_NATIVE_PATH, _content,
    )
    from f139.nci04_hypothesis_engine import generate_yggdrasil_hypothesis_pool
    from f139.nci04_hypothesis_engine_gen2 import generate_gen2_yggdrasil_pool
    from f139.nci04_receipt_feedback import rank_pool_with_receipt_feedback

    need(type(db) is Database
         and SingleOwner.held(db.filename.with_suffix(".lock")),
         "V3_PLANNER_ORIGINAL_MUTEX_REQUIRED")
    original = (db.meta()["head_seq"], db.meta()["head_hash"],
                db.conn.total_changes)
    release, entries = read_lifecycle(db, owner_key)
    authenticate_runtime_owner(db, api, release, owner_key)
    need(entries[-1]["stage"] == "VERIFIED"
         and entries[-1].get("negative") is None
         and entries[-1].get("publication_attempt") is None,
         "V3_PLANNER_MUST_FOLLOW_UNPUBLISHED_VERIFIED_TERMINAL")
    available = remaining_hypothesis_v3_budget(entries, remaining_cost_units)
    if available < HYPOTHESIS_V3_COST_UNITS:
        return None
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
         "V3_PLANNER_SEALED_CONSUMED_HISTORY_DRIFT")
    spent = set(old)
    for e in entries:
        spent.add(e["record"]["after_sha256"])
        publication = e.get("publication_attempt")
        if publication:
            spent.add(publication["after_sha256"])
    latest = entries[-1]["record"]["after_sha256"]
    need(latest in spent and len(spent) <= 10000,
         "V3_PLANNER_LAST_TERMINAL_NOT_CONSUMED")

    root_route = "repos/" + REPO
    branch_route = root_route + "/branches/main"
    main = api.native_repo_get(branch_route)
    commit = api.native_repo_get(root_route + "/git/commits/" + TARGET)
    need(type(main) is dict and main.get("name") == "main"
         and main.get("protected") is True
         and main.get("commit", {}).get("sha") == TARGET
         and type(commit) is dict and commit.get("sha") == TARGET
         and commit.get("tree", {}).get("sha") == TARGET_TREE,
         "V3_PLANNER_TARGET_PIN_DRIFT")
    before = _content(
        api.native_repo_get, ACCEPTED_NATIVE_PATH, TARGET, ACCEPTED_NATIVE_BLOB)
    need(api.native_repo_get(branch_route) == main, "V3_PLANNER_TARGET_MOVED")
    try:
        raw_seed = base64.b64decode(
            entries[0]["record"]["native_intent_base64"], validate=True)
    except (KeyError, ValueError, TypeError, binascii.Error) as exc:
        raise ValueError("F139_CURRICULUM_V3_SEED_INVALID") from exc
    pool = generate_yggdrasil_hypothesis_pool(
        before=before, seed_intent=raw_seed,
        consumed_after=spent, last_verified_after=latest)
    chosen_after = None
    if pool:
        decision = rank_pool_with_receipt_feedback(pool, entries)
        chosen_after = decision.get("selected_after_sha256")
    if chosen_after is None:
        gen2_pool = generate_gen2_yggdrasil_pool(
            before=before, seed_intent=raw_seed,
            consumed_after=spent, last_verified_after=latest)
        if not gen2_pool:
            return None
        pool = gen2_pool
        decision = rank_pool_with_receipt_feedback(pool, entries)
        chosen_after = decision.get("selected_after_sha256")
        if chosen_after is None:
            return None
    matched = [item for item in pool if item["plan"]["after_sha256"] == chosen_after]
    need(len(matched) == 1, "V3_PLANNER_SELECTED_PLAN_AMBIGUOUS")
    need((db.meta()["head_seq"], db.meta()["head_hash"],
          db.conn.total_changes) == original,
         "V3_PLANNER_LEDGER_MUTATED")
    return dict(matched[0]["plan"])
