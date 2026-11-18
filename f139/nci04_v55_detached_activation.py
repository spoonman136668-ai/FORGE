"""V55 original-owner v45 transition + activation on DETACHED COPIES ONLY.

Exercises the genuine Database.event/transaction and existing SHA verifier
without adding ANY live owner entrypoint, task change, schedule, queue or
native first-use. The production activate_native function remains the only source activation
authority, and v45 compatibility requires a separately authenticated release.

Passing this simulation DOES NOT authorize a source cutover: a later
independently authenticated owner-owned release must bind protected-main
source, original SID/task and runner, evidence, backup and rollback.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re

from f139.local_controller import Database, SingleOwner
from f139.nci04_owner_ledger import (
    ACTIVATION_KIND, ACTIVATION_SCHEMA, SEALED_OWNER_PREFIX_HEAD,
    verified_historical_foundation, verify_native_activation,
)
from f139.nci04_v55_forward_transition import (
    SOURCE, SCHEMA, make_proof, need, verify_cold_event,
)


_DETACHED_NAME = re.compile(r"f139-v55-original-rehearsal-[1-9][0-9]*\.sqlite\Z")


def _require_detached(db):
    need(type(db) is Database and not getattr(db, "_readonly_opened", False),
         "REHEARSAL_REQUIRES_WRITABLE_DATABASE_CLASS")
    p = Path(db.filename).absolute()
    root = os.environ.get("RUNNER_TEMP")
    need(type(root) is str and bool(root), "RUNNER_TEMP_REQUIRED")
    temp = Path(root).absolute()
    need(temp.is_dir() and not temp.is_symlink()
         and p.is_file() and not p.is_symlink()
         and _DETACHED_NAME.fullmatch(p.name) is not None
         and p.parent.resolve() == temp.resolve()
         and p.resolve() != temp.resolve()
         and p.parent.name != "FORGE-F139"
         and SingleOwner.held(p.with_suffix(".lock"))
         and db.conn.execute("PRAGMA query_only").fetchone()[0] == 0,
         "DETACHED_COPY_IDENTITY_OR_MUTEX_REQUIRED")


def rehearse_v45_source_and_activation(
        db, *, target, owner_run_id, qualified_main_run_id,
        rehearsal_run_id, backup_sqlite_sha256,
        genenv_executable_sha256, generation_mechanism_sha256):
    """Commit both simulated owner events as ONE rollback-safe transaction.

    This function cannot run on the real original 'state.sqlite', outside
    RUNNER_TEMP, without an original-compatible file mutex, or after reuse.
    No subprocess, network, GitHub write, provider dispatch or owner task API.
    """
    _require_detached(db)
    db.verify()
    verified_historical_foundation(db)
    proof = make_proof(
        db, target=target, owner_run_id=owner_run_id,
        qualified_main_run_id=qualified_main_run_id,
        rehearsal_run_id=rehearsal_run_id,
        backup_sqlite_sha256=backup_sqlite_sha256,
        genenv_executable_sha256=genenv_executable_sha256,
        generation_mechanism_sha256=generation_mechanism_sha256,
    )
    before = db.meta()
    need(before["source_sha"] == SOURCE and
         before["enabled"] == 1 and before["legacy_suspended"] == 1 and
         db.ready() is None and not db.actives() and
         verify_native_activation(db, expected_source=SOURCE) is True,
         "PRECOMMIT_ORIGINAL_ACTIVATION_OR_PENDING_DRIFT")
    older = [json.loads(row["payload"]) for row in db.conn.execute(
        "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED'"
        " ORDER BY seq")]
    count = db.conn.execute(
        "SELECT COUNT(*) FROM events WHERE kind='NATIVE_DEVELOPMENT_ACTIVATED'"
    ).fetchone()[0]
    transitions = len(older)
    # Historic source transitions and activation receipts are not 1:1.
    # The existing verifier authenticates every activation's historical source;
    # require a current original-source activation without inventing receipts.
    need(1 <= count <= transitions + 1
         and older[-1]["to_source_sha"] == SOURCE
         and proof["schema"] == SCHEMA
         and verify_native_activation(db, expected_source=SOURCE) is True,
         "EXACT_ONE_ACTIVATION_PER_SOURCE_REQUIRED")
    with db.transaction():
        _require_detached(db)
        db.verify()
        m = db.meta()
        need(all(m[k] == before[k]
                 for k in ("head_seq", "head_hash", "source_sha"))
             and db.ready() is None and not db.actives(),
             "PRECOMMIT_LEDGER_OR_PENDING_DRIFT")
        verify_cold_event(db,
            {"seq":m["head_seq"] + 1, "prior_sha":m["head_hash"]},
            proof, older)
        db.conn.execute("UPDATE meta SET source_sha=? WHERE id=1", (target,))
        db.event("SOURCE_TRANSITION_ADMITTED", proof)
        db.verify()
        need(verify_native_activation(db, expected_source=SOURCE) is True,
             "OLD_ACTIVATION_HISTORY_CHANGED")
        prior = db.meta()["head_hash"]
        # Preserve the exact existing, verified activation event schema.
        db.event(ACTIVATION_KIND, {
            "schema": ACTIVATION_SCHEMA,
            "source_sha": target,
            "prior_event_head_sha256": prior,
            "sealed_original_prefix_sha256": SEALED_OWNER_PREFIX_HEAD,
            "verified_original_tasks": 4,
            "verified_d2k_tasks": 2,
            "new_dispatches": 0,
            "scientific_first_use": False,
            "development_only": True,
        })
        db.verify()
        need(verify_native_activation(db) is True
             and db.meta()["source_sha"] == target,
             "POSTCOMMIT_DETACHED_ACTIVATION_NOT_AUTHENTIC")
    after = db.meta()
    need(after["head_seq"] == before["head_seq"] + 2
         and after["source_sha"] == target,
         "DETACHED_SOURCE_OR_EVENT_COUNT_CHANGED")
    return {
        "schema": "forge.f139.v55.detached-source-activation-rehearsal.v1",
        "detached_only": True, "deployment_authorized": False,
        "source_sha": target, "head_seq": after["head_seq"],
        "head_sha256": after["head_hash"],
        "historical_events_added": 2,
        "worker_dispatches": 0, "scientific_first_use": False,
        "new_controller": False, "new_scheduler": False,
        "new_queue": False, "paid_api_calls": 0,
    }
