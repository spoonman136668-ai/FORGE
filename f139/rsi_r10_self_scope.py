"""One-shot, authenticated FORGE-self DEVELOPMENT scope reservation.

This is deliberately NOT original owner task admission or worker execution.
User authorized one bounded development attempt, conditioned on a genuinely
fresh, unconsumed failure; this source does not treat that permission as a
self-issued owner signature. It only reuses R7, R8, the original owner mutex
and original SQLite event chain, in a DISABLED EMPTY disposable development DB.
"""
from __future__ import annotations

import json
import re

from f139.rsi_r8_owner_custody import (
    KIND as OBSERVED, SCHEMA as OBSERVED_SCHEMA,
    audit_observed_scopes,
)
from f139.rsi_r7_fresh_failure import scan, DiscoveryDenied
from f139.rsi_r6_known_repair_cycle import DIGEST, HEAD, PATH

KIND = "RSI_SELF_SCOPE_RESERVED"
SCHEMA = "forge.f139.rsi-r10.one-shot-self-development-reservation.v1"
# A source-verified passing original Linux+Windows main run, after R9's
# protected-main merge. Older failed runs are historical, not new tasks.
AFTER_RUN = 42540664890
NOT_BEFORE_UTC = "2026-11-09T00:31:39Z"
MAX_RESERVATIONS = 1
FIELDS = frozenset({
    "schema", "owner_source_sha", "failed_head_sha", "failed_run_id",
    "failed_job_id", "task_scope_sha256", "candidate_sha256",
    "target_path", "prior_event_head_sha256", "operator_scope",
    "development_only", "forged_owner_authority",
    "owner_self_scope_authorized", "worker_dispatched",
    "source_promoted", "scientific_first_use", "paid_model_calls",
})


class SelfScopeDenied(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise SelfScopeDenied("F139_RSI_R10_" + code)


def audit_self_scope(db) -> tuple[dict, ...]:
    """Cold-check the entire original SHA-chained event history, read-only.

    Called AFTER original Database.verify's hash-chain and R8 audit. A new
    source transition does not magically upgrade a reserved development scope.
    """
    import sqlite3
    need(type(db).__name__ == "Database"
         and type(db).__module__ in (
             "f139.local_controller", "local_controller", "__main__")
         and type(getattr(db, "conn", None)) is sqlite3.Connection,
         "DATABASE_TYPE")
    observed = {}
    reserved = []
    for row in db.conn.execute(
            "SELECT seq,kind,payload,prior_sha FROM events ORDER BY seq"):
        if row["kind"] == OBSERVED:
            doc = json.loads(row["payload"])
            need(type(doc) is dict and doc.get("schema") == OBSERVED_SCHEMA,
                 "OBSERVATION_IDENTITY_DRIFT")
            observed[doc["task_scope_sha256"]] = (row["seq"], doc)
        if row["kind"] != KIND:
            continue
        doc = json.loads(row["payload"])
        need(len(reserved) < MAX_RESERVATIONS, "ONE_SHOT_ALREADY_SPENT")
        need(type(doc) is dict and set(doc) == FIELDS
             and doc["schema"] == SCHEMA
             and type(doc["owner_source_sha"]) is str
             and HEAD.fullmatch(doc["owner_source_sha"]) is not None
             and type(doc["failed_head_sha"]) is str
             and HEAD.fullmatch(doc["failed_head_sha"]) is not None
             and type(doc["failed_run_id"]) is int
             and doc["failed_run_id"] > AFTER_RUN
             and type(doc["failed_job_id"]) is int
             and doc["failed_job_id"] > 0
             and type(doc["task_scope_sha256"]) is str
             and DIGEST.fullmatch(doc["task_scope_sha256"]) is not None
             and type(doc["candidate_sha256"]) is str
             and DIGEST.fullmatch(doc["candidate_sha256"]) is not None
             and type(doc["target_path"]) is str
             and PATH.fullmatch(doc["target_path"]) is not None
             and doc["prior_event_head_sha256"] == row["prior_sha"]
             and doc["operator_scope"] ==
                 "one-fresh-forge-self-development-attempt"
             and doc["development_only"] is True
             and doc["forged_owner_authority"] is False
             and doc["owner_self_scope_authorized"] is False
             and doc["worker_dispatched"] is False
             and doc["source_promoted"] is False
             and doc["scientific_first_use"] is False
             and type(doc["paid_model_calls"]) is int
             and doc["paid_model_calls"] == 0,
             "RESERVATION_FIELDS_OR_AUTHORITY_INVALID")
        witness = observed.get(doc["task_scope_sha256"])
        need(witness is not None and witness[0] < row["seq"],
             "UNOBSERVED_OR_REORDERED_FAILURE")
        prior = witness[1]
        need(prior["owner_source_sha"] == doc["owner_source_sha"]
             and prior["failed_head_sha"] == doc["failed_head_sha"]
             and prior["failed_run_id"] == doc["failed_run_id"]
             and prior["failed_job_id"] == doc["failed_job_id"]
             and prior["target_path"] == doc["target_path"]
             and prior["candidate_sha256"] == doc["candidate_sha256"],
             "FAILURE_SOURCE_OR_CANDIDATE_DRIFT")
        reserved.append(doc)
    # A reserved DEV scope cannot become an executable task through
    # SQLite edits or a metadata flip. Original owner worker lanes stay closed.
    if reserved:
        meta = db.meta()
        need(meta["enabled"] == 0 and meta["legacy_suspended"] == 0
             and db.conn.execute(
                 "SELECT COUNT(*) FROM tasks").fetchone()[0] == 0,
             "OWNER_OR_TASK_ACTIVATION_DENIED")
        need(not any(
            row["lane"] == "FORGE-self" for row in db.conn.execute(
                "SELECT lane FROM tasks")), "OWNER_SELF_TASK_DENIED")
    return tuple(reserved)


def reserve_disabled_development(*, db, provider,
                                 failed_run_id: int, failed_job_id: int,
                                 target_path: str) -> str:
    """Spend exactly one fresh, previously observed self-development scope.

    Strictly zero owner dispatch. A genuinely new main/push failure must
    FIRST have been authenticated and observed by R8 in this same ledger.
    R7 independently checks the provider's bounded fresh-run feed again.
    """
    from f139.local_controller import Database, GitHub, SingleOwner
    need(type(db) is Database and type(provider) is GitHub,
         "ORIGINAL_TYPES_REQUIRED")
    need(SingleOwner.held(db.filename.with_suffix(".lock")),
         "ORIGINAL_MUTEX_NOT_HELD")
    db.verify()
    meta = db.meta()
    need(meta["enabled"] == 0 and meta["legacy_suspended"] == 0
         and db.conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0,
         "LIVE_OR_NONEMPTY_OWNER_DENIED")
    need(type(failed_run_id) is int and failed_run_id > AFTER_RUN
         and type(failed_job_id) is int and failed_job_id > 0
         and type(target_path) is str
         and PATH.fullmatch(target_path) is not None,
         "FRESH_RUN_OR_PATH_REQUIRED")
    need(not audit_self_scope(db), "ONE_SHOT_ALREADY_SPENT")
    scopes = audit_observed_scopes(db)
    need(len(scopes) == 1, "EXACTLY_ONE_ORIGINAL_OBSERVATION_REQUIRED")
    witness = [json.loads(row["payload"]) for row in db.conn.execute(
        "SELECT payload FROM events WHERE kind=?", (OBSERVED,))]
    need(len(witness) == 1
         and witness[0]["task_scope_sha256"] in scopes
         and witness[0]["failed_run_id"] == failed_run_id
         and witness[0]["failed_job_id"] == failed_job_id
         and witness[0]["target_path"] == target_path
         and witness[0]["owner_source_sha"] == meta["source_sha"],
         "R8_SCOPE_OR_SOURCE_MISMATCH")
    try:
        verified = scan(
            provider=provider, after_run_id=AFTER_RUN,
            not_before_utc=NOT_BEFORE_UTC, target_path=target_path,
            consumed_scopes=frozenset())
    except DiscoveryDenied as exc:
        raise SelfScopeDenied("F139_RSI_R10_FRESH_PROVIDER_REJECTED") from exc
    matches = [p for p in verified.proposals
               if p.run_id == failed_run_id and p.job_id == failed_job_id
               and p.proposal.task_scope_sha256 == witness[0]["task_scope_sha256"]
               and p.proposal.candidate_sha256 == witness[0]["candidate_sha256"]
               and p.original_head_sha == witness[0]["failed_head_sha"]]
    need(len(matches) == 1, "UNVERIFIED_NEW_FAILURE_OR_DRIFT")
    payload = {
        "schema": SCHEMA, "owner_source_sha": meta["source_sha"],
        "failed_head_sha": witness[0]["failed_head_sha"],
        "failed_run_id": failed_run_id, "failed_job_id": failed_job_id,
        "task_scope_sha256": witness[0]["task_scope_sha256"],
        "candidate_sha256": witness[0]["candidate_sha256"],
        "target_path": target_path,
        "prior_event_head_sha256": meta["head_hash"],
        "operator_scope": "one-fresh-forge-self-development-attempt",
        "development_only": True, "forged_owner_authority": False,
        "owner_self_scope_authorized": False, "worker_dispatched": False,
        "source_promoted": False, "scientific_first_use": False,
        "paid_model_calls": 0,
    }
    with db.transaction():
        db.verify()
        current = db.meta()
        need(current["head_hash"] == meta["head_hash"]
             and current["source_sha"] == meta["source_sha"]
             and current["enabled"] == 0
             and current["legacy_suspended"] == 0
             and not audit_self_scope(db)
             and db.conn.execute(
                 "SELECT COUNT(*) FROM tasks").fetchone()[0] == 0,
             "OWNER_RACE_OR_REPLAY")
        db.event(KIND, payload)
        db.verify()
        return db.meta()["head_hash"]
