"""Original F139 SQLite custody for R6/R7 failure observations: DEV OFF by default.

This module reuses the existing F139 owner mutex, event hash chain, DB and
authenticated GitHub readback. It cannot dispatch, install or approve FORGE
self-source repairs. The only writer is restricted to a NEW, DISABLED, EMPTY
development ledger. The live original owner's enabled database is refused.
"""
from __future__ import annotations

import json
import re
from hashlib import sha256

from f139.rsi_r6_known_repair_cycle import (
    DIGEST, HEAD, PATH, FAILURE, RepairDenied,
)

KIND = "RSI_FAILURE_OBSERVED"
SCHEMA = "forge.f139.rsi-r8.owner-failure-observation.v1"
MAX_OBSERVATIONS = 8
FIELDS = frozenset({
    "schema", "owner_source_sha", "failed_head_sha", "failed_run_id",
    "failed_job_id", "run_attempt", "failure_class", "target_path",
    "original_sha256", "candidate_sha256", "source_git_blob_sha",
    "failed_log_sha256", "task_scope_sha256", "mechanism",
    "prior_event_head_sha256", "worker_dispatched", "owner_self_scope_authorized",
    "scientific_first_use", "source_promoted", "paid_model_calls",
})


class R8CustodyDenied(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise R8CustodyDenied("F139_RSI_R8_" + code)


def _sha40(value) -> bool:
    return type(value) is str and HEAD.fullmatch(value) is not None


def _sha64(value) -> bool:
    return type(value) is str and DIGEST.fullmatch(value) is not None


def _payload(readback, *, owner_source_sha: str, prior_hash: str) -> dict:
    from f139.rsi_r6_provider_readback import Readback, git_blob
    need(type(readback) is Readback
         and readback.schema == "forge.f139.rsi-r6.readonly-github-evidence.v1"
         and _sha40(owner_source_sha) and _sha64(prior_hash),
         "READBACK_TYPE_OR_OWNER_SOURCE")
    p = readback.proposal
    need(p.schema == "forge.f139.rsi-r6.source-only-known-repair.v1"
         and p.parent_sha == readback.original_head_sha
         and p.path == readback.path
         and p.original_sha256 != p.candidate_sha256
         and type(p.source) is bytes
         and sha256(p.source).hexdigest() == p.candidate_sha256
         and p.eligible_for_owner is False and p.qualified is False
         and p.scientific_first_use is False and p.deployed is False
         and p.autonomous_rsi_proven is False
         and _sha64(p.task_scope_sha256)
         and _sha64(readback.log_sha256)
         and _sha40(readback.source_git_blob_sha)
         and _sha40(readback.original_head_sha)
         and readback.original_owner_admitted is False
         and readback.source_regression_pass is False
         and readback.scientific_first_use is False
         and readback.production_release is False,
         "SOURCE_ONLY_READBACK_INVALID")
    need(type(p.mechanism) is str and
         re.fullmatch(r"[a-z0-9-]{3,60}", p.mechanism) is not None,
         "MECHANISM_INVALID")
    return {
        "schema": SCHEMA,
        "owner_source_sha": owner_source_sha,
        "failed_head_sha": readback.original_head_sha,
        "failed_run_id": readback.run_id,
        "failed_job_id": readback.job_id,
        "run_attempt": 1,
        "failure_class": FAILURE,
        "target_path": p.path,
        "original_sha256": p.original_sha256,
        "candidate_sha256": p.candidate_sha256,
        "source_git_blob_sha": readback.source_git_blob_sha,
        "failed_log_sha256": readback.log_sha256,
        "task_scope_sha256": p.task_scope_sha256,
        "mechanism": p.mechanism,
        "prior_event_head_sha256": prior_hash,
        "worker_dispatched": False,
        "owner_self_scope_authorized": False,
        "scientific_first_use": False,
        "source_promoted": False,
        "paid_model_calls": 0,
    }


def audit_observed_scopes(db) -> frozenset[str]:
    """Cold verification without caller permission, GitHub or recursion.

    Database.verify() first checks every SHA-chained event and all existing
    owner invariants, then calls this additional observation-only verifier.
    """
    # Python -m executes the original controller as __main__ rather than
    # f139.local_controller. Verify either ORIGINAL Database class identity,
    # without permitting a forged writer or broadening owner execution.
    import sqlite3
    need(type(db).__name__ == "Database"
         and type(db).__module__ in ("f139.local_controller", "__main__")
         and type(getattr(db, "conn", None)) is sqlite3.Connection
         and callable(getattr(db, "meta", None)), "DATABASE_TYPE")
    meta = db.meta()
    rows = list(db.conn.execute(
        "SELECT seq,kind,payload,prior_sha FROM events "
        "WHERE kind IN (?,?) ORDER BY seq",
        ("SOURCE_TRANSITION_ADMITTED", KIND)))
    transitions = [json.loads(row["payload"]) for row in rows
                   if row["kind"] == "SOURCE_TRANSITION_ADMITTED"]
    # The initial source is sealed by the original controller's independently
    # verified source-transition chain, not guessed from mutable current main.
    source = transitions[0]["from_source_sha"] if transitions else meta["source_sha"]
    seen_scopes: set[str] = set()
    seen_jobs: set[tuple[int, int]] = set()
    for row in rows:
        doc = json.loads(row["payload"])
        if row["kind"] == "SOURCE_TRANSITION_ADMITTED":
            need(doc["from_source_sha"] == source, "SOURCE_CHAIN_DRIFT")
            source = doc["to_source_sha"]
            continue
        need(len(seen_scopes) < MAX_OBSERVATIONS, "OBSERVATION_BUDGET")
        need(type(doc) is dict and set(doc) == FIELDS
             and doc["schema"] == SCHEMA
             and doc["owner_source_sha"] == source
             and _sha40(doc["failed_head_sha"])
             and type(doc["failed_run_id"]) is int
             and doc["failed_run_id"] > 0
             and type(doc["failed_job_id"]) is int
             and doc["failed_job_id"] > 0
             and type(doc["run_attempt"]) is int
             and doc["run_attempt"] == 1
             and doc["failure_class"] == FAILURE
             and type(doc["target_path"]) is str
             and PATH.fullmatch(doc["target_path"]) is not None
             and _sha64(doc["original_sha256"])
             and _sha64(doc["candidate_sha256"])
             and doc["original_sha256"] != doc["candidate_sha256"]
             and _sha40(doc["source_git_blob_sha"])
             and _sha64(doc["failed_log_sha256"])
             and _sha64(doc["task_scope_sha256"])
             and type(doc["mechanism"]) is str
             and re.fullmatch(r"[a-z0-9-]{3,60}", doc["mechanism"]) is not None
             and doc["prior_event_head_sha256"] == row["prior_sha"]
             and doc["worker_dispatched"] is False
             and doc["owner_self_scope_authorized"] is False
             and doc["scientific_first_use"] is False
             and doc["source_promoted"] is False
             and type(doc["paid_model_calls"]) is int
             and doc["paid_model_calls"] == 0,
             "OBSERVATION_FIELDS_OR_AUTHORITY_DRIFT")
        job = (doc["failed_run_id"], doc["failed_job_id"])
        need(doc["task_scope_sha256"] not in seen_scopes
             and job not in seen_jobs, "DUPLICATE_OR_REPLAYED_FAILURE")
        seen_scopes.add(doc["task_scope_sha256"])
        seen_jobs.add(job)
    need(source == meta["source_sha"], "CURRENT_SOURCE_DRIFT")
    return frozenset(seen_scopes)


def recorded_scopes(db) -> frozenset[str]:
    """Read-only consumed-set for R7; never an owner permit."""
    db.verify()
    return audit_observed_scopes(db)


def observe_disabled_development(*, db, provider, run_id: int,
                                 job_id: int, path: str,
                                 failed_head: str) -> str:
    """Commit an authenticated R6 failure once to EXISTING disposable WAL.

    Requires the original SingleOwner lock on a disabled/empty development
    database. Not connected to the live run_once(), worker or any policy.
    The original enabled F139 owner cannot be altered by this function.
    """
    from f139.local_controller import Database, GitHub, SingleOwner
    from f139.rsi_r6_provider_readback import acquire
    need(type(db) is Database and type(provider) is GitHub,
         "PROVIDER_OR_DATABASE_TYPE")
    need(SingleOwner.held(db.filename.with_suffix(".lock")),
         "ORIGINAL_MUTEX_NOT_HELD")
    db.verify()
    m = db.meta()
    need(m["enabled"] == 0 and m["legacy_suspended"] == 0
         and db.conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0,
         "LIVE_OR_NONEMPTY_OWNER_DENIED")
    previous = audit_observed_scopes(db)
    need(len(previous) < MAX_OBSERVATIONS, "OBSERVATION_BUDGET")
    try:
        result = acquire(
            provider=provider, run_id=run_id, job_id=job_id,
            path=path, expected_head=failed_head, consumed_scopes=previous)
    except RepairDenied as exc:
        raise R8CustodyDenied("F139_RSI_R8_AUTHENTIC_READBACK_DENIED") from exc
    payload = _payload(result, owner_source_sha=m["source_sha"],
                       prior_hash=m["head_hash"])
    with db.transaction():
        db.verify()
        current = db.meta()
        need(current["head_hash"] == m["head_hash"]
             and current["source_sha"] == m["source_sha"]
             and current["enabled"] == 0 and current["legacy_suspended"] == 0
             and db.conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0
             and payload["task_scope_sha256"] not in audit_observed_scopes(db)
             and len(audit_observed_scopes(db)) < MAX_OBSERVATIONS,
             "CONCURRENT_CUSTODY_OR_OWNER_DRIFT")
        db.event(KIND, payload)
        db.verify()
        return db.meta()["head_hash"]
