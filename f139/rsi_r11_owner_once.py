"""R11: lifetime-once FORGE-self DEV reservation in the ORIGINAL owner ledger.

Only an authentic original F139 Windows owner can reserve. No new scheduler,
queue, workflow, ticket, worker, science or source promotion is introduced.
R10's disposable SQLite observations remain non-authorizing development data.
"""
from __future__ import annotations

import json
import os
from hashlib import sha256
from pathlib import Path

from f139.rsi_r10_self_scope import AFTER_RUN, NOT_BEFORE_UTC
from f139.rsi_r7_fresh_failure import scan, DiscoveryDenied
from f139.rsi_r6_known_repair_cycle import (
    DIGEST, HEAD, PATH, FAILURE,
)
from f139.rsi_r6_provider_readback import Readback
from f139.nci04_owner_ledger import (
    SEALED_OWNER_PREFIX_HEAD, ACTIVATION_KIND,
    verified_historical_foundation, verify_native_activation,
)

KIND = "RSI_SELF_ORIGINAL_RESERVED"
SCHEMA = "forge.f139.rsi-r11.original-owner-one-shot-dev.v1"
SCOPE = "one-forge-self-original-owner-dev-attempt-20261108"
MAX_RESERVATIONS = 1
FIELDS = frozenset({
    "schema", "owner_source_sha", "original_owner_prefix_sha256",
    "failed_head_sha", "failed_run_id", "failed_job_id",
    "failed_log_sha256", "source_git_blob_sha", "target_path",
    "before_sha256", "candidate_sha256", "task_scope_sha256",
    "failure_class", "mechanism", "prior_event_head_sha256",
    "operator_scope", "development_only", "new_worker_created",
    "owner_self_worker_admitted", "worker_dispatched", "source_promoted",
    "scientific_first_use", "paid_model_calls", "autonomous_rsi_proven",
})


class OriginalOnceDenied(ValueError):
    pass


def need(condition: bool, code: str) -> None:
    if not condition:
        raise OriginalOnceDenied("F139_RSI_R11_" + code)


def _sha40(value) -> bool:
    return type(value) is str and HEAD.fullmatch(value) is not None


def _sha64(value) -> bool:
    return type(value) is str and DIGEST.fullmatch(value) is not None


def _source_at_event(rows, initial: str):
    source = initial
    for row in rows:
        if row["kind"] == "SOURCE_TRANSITION_ADMITTED":
            doc = json.loads(row["payload"])
            need(type(doc) is dict
                 and doc["from_source_sha"] == source
                 and _sha40(doc["to_source_sha"]),
                 "SOURCE_HISTORY_DRIFT")
            source = doc["to_source_sha"]
        yield row, source


def audit_owner_once(db) -> tuple[dict, ...]:
    """Cold audit of the actual ORIGINAL owner event chain, lifetime-once.

    Called by the existing Database.verify() after its SHA-chain and native
    historical auditors. A synthetically initialized disposable ledger cannot
    acquire an original-owner reservation merely by writing a matching event.
    """
    import sqlite3
    need(type(db).__name__ == "Database"
         and type(db).__module__ in (
             "f139.local_controller", "local_controller", "__main__")
         and type(getattr(db, "conn", None)) is sqlite3.Connection,
         "ORIGINAL_DATABASE_TYPE")
    rows = list(db.conn.execute(
        "SELECT seq,kind,payload,prior_sha FROM events ORDER BY seq"))
    transitions = [json.loads(row["payload"]) for row in rows
                   if row["kind"] == "SOURCE_TRANSITION_ADMITTED"]
    source = (transitions[0]["from_source_sha"]
              if transitions else db.meta()["source_sha"])
    reserved = []
    for row, current_source in _source_at_event(rows, source):
        if row["kind"] != KIND:
            continue
        need(len(reserved) < MAX_RESERVATIONS, "LIFETIME_RESERVATION_EXHAUSTED")
        doc = json.loads(row["payload"])
        need(type(doc) is dict and set(doc) == FIELDS
             and doc["schema"] == SCHEMA
             and doc["operator_scope"] == SCOPE
             and doc["original_owner_prefix_sha256"] ==
                 SEALED_OWNER_PREFIX_HEAD
             and doc["owner_source_sha"] == current_source
             and _sha40(doc["owner_source_sha"])
             and _sha40(doc["failed_head_sha"])
             and type(doc["failed_run_id"]) is int
             and doc["failed_run_id"] > AFTER_RUN
             and type(doc["failed_job_id"]) is int
             and doc["failed_job_id"] > 0
             and _sha64(doc["failed_log_sha256"])
             and _sha40(doc["source_git_blob_sha"])
             and type(doc["target_path"]) is str
             and PATH.fullmatch(doc["target_path"]) is not None
             and _sha64(doc["before_sha256"])
             and _sha64(doc["candidate_sha256"])
             and doc["before_sha256"] != doc["candidate_sha256"]
             and _sha64(doc["task_scope_sha256"])
             and doc["failure_class"] == FAILURE
             and type(doc["mechanism"]) is str
             and len(doc["mechanism"]) in range(3, 61)
             and all(c.isascii() and (c.islower() or c.isdigit()
                                      or c == "-")
                     for c in doc["mechanism"])
             and doc["prior_event_head_sha256"] == row["prior_sha"]
             and doc["development_only"] is True
             and doc["new_worker_created"] is False
             and doc["owner_self_worker_admitted"] is False
             and doc["worker_dispatched"] is False
             and doc["source_promoted"] is False
             and doc["scientific_first_use"] is False
             and type(doc["paid_model_calls"]) is int
             and doc["paid_model_calls"] == 0
             and doc["autonomous_rsi_proven"] is False,
             "ORIGINAL_RESERVATION_FIELDS_OR_AUTHORITY")
        reserved.append(doc)
        reserved_seq = row["seq"]
    if reserved:
        # Cold source transitions are permitted AFTER a reservation.
        # Bind activation to the historical source and sequence that
        # authored the reservation, not the mutable current source.
        verified_historical_foundation(db)
        verify_native_activation(db)  # independently verify each old activation
        source_activated_earlier = [
            json.loads(row["payload"])["source_sha"] for row in
            db.conn.execute(
                "SELECT payload FROM events WHERE kind=? AND seq<? "
                "ORDER BY seq", (ACTIVATION_KIND, reserved_seq))]
        need(reserved[0]["owner_source_sha"] in source_activated_earlier,
             "SOURCE_NOT_ACTIVATED_AT_RESERVATION")
    return tuple(reserved)


def _authentic_original_owner(db, provider, *, allow_used_reservation: bool = False) -> str:
    """Fail closed unless operating the real Windows owner/release checkout."""
    import sqlite3
    import sys
    from f139 import local_controller as native
    # The original CLI executes as __main__ under python -m. Reconcile the
    # exact source FILE and TYPE identity; untrusted lookalike classes cannot
    # become a verified GitHub adapter or write into the owner ledger.
    cli = sys.modules.get("__main__")
    original_cli = (
        cli is not None and
        getattr(cli, "__file__", None) is not None and
        Path(cli.__file__).resolve() == Path(native.__file__).resolve() and
        type(db) is getattr(cli, "Database", None) and
        type(provider) is getattr(cli, "GitHub", None))
    canonical_cli = (
        type(db) is native.Database and type(provider) is native.GitHub)
    need((original_cli or canonical_cli)
         and type(getattr(db, "conn", None)) is sqlite3.Connection,
         "ORIGINAL_OWNER_INSTANCE_REQUIRED")
    # Do not accept arbitrary runner injection or shadowed release verifier
    # when the method is called from a future authenticated owner source.
    need(type(provider).__dict__.get("_command") is not None
         and getattr(provider, "runner", None) is type(provider)._command
         and vars(provider) == {"runner": type(provider)._command},
         "ORIGINAL_GITHUB_ADAPTER_DRIFT")
    SingleOwner = native.SingleOwner
    need(os.name == "nt", "WINDOWS_ORIGINAL_ONLY")
    home = os.environ.get("LOCALAPPDATA", "")
    need(bool(home) and
         db.filename.resolve() ==
             (Path(home) / "FORGE-F139" / "state.sqlite").resolve(),
         "ORIGINAL_DATABASE_PATH_REQUIRED")
    need(SingleOwner.held(db.filename.with_suffix(".lock")),
         "ORIGINAL_KERNEL_MUTEX_REQUIRED")
    db.verify()
    meta = db.meta()
    need(meta["enabled"] == 1 and meta["legacy_suspended"] == 1,
         "ORIGINAL_OWNER_NOT_ENABLED")
    verified_historical_foundation(db)
    need(verify_native_activation(db) is True,
         "NATIVE_SOURCE_ACTIVATION_MISSING")
    need(db.ready() is None and not db.actives(),
         "ORIGINAL_NATIVE_WORK_BUSY")
    need(type(allow_used_reservation) is bool, "ORIGINAL_OWNER_SCOPE_INVALID")
    if not allow_used_reservation:
        need(not audit_owner_once(db), "ONE_SHOT_ALREADY_SPENT")
    protected_source = provider.protected_main()
    need(_sha40(protected_source)
         and provider.deployed_release_continuity(
             db, meta["source_sha"], protected_source) is True,
         "INSTALLED_RELEASE_OR_OWNER_POLICY_UNVERIFIED")
    return meta["source_sha"]


def _payload(row: Readback, *, source: str, prior: str) -> dict:
    p = row.proposal
    need(type(row) is Readback
         and row.original_owner_admitted is False
         and row.source_regression_pass is False
         and row.scientific_first_use is False
         and row.production_release is False
         and _sha40(source)
         and _sha40(row.original_head_sha)
         and type(row.run_id) is int and row.run_id > AFTER_RUN
         and type(row.job_id) is int and row.job_id > 0
         and _sha64(row.log_sha256)
         and _sha40(row.source_git_blob_sha)
         and p.schema == "forge.f139.rsi-r6.source-only-known-repair.v1"
         and p.original_failure_class == FAILURE
         and p.parent_sha == row.original_head_sha
         and p.path == row.path
         and type(p.source) is bytes
         and sha256(p.source).hexdigest() == p.candidate_sha256
         and _sha64(p.task_scope_sha256)
         and _sha64(p.original_sha256)
         and _sha64(p.candidate_sha256)
         and p.original_sha256 != p.candidate_sha256
         and p.eligible_for_owner is False
         and p.qualified is False
         and p.scientific_first_use is False
         and p.deployed is False
         and p.autonomous_rsi_proven is False
         and _sha64(prior), "UNTRUSTED_PROVIDER_PROPOSAL")
    return {
        "schema": SCHEMA, "owner_source_sha": source,
        "original_owner_prefix_sha256": SEALED_OWNER_PREFIX_HEAD,
        "failed_head_sha": row.original_head_sha,
        "failed_run_id": row.run_id, "failed_job_id": row.job_id,
        "failed_log_sha256": row.log_sha256,
        "source_git_blob_sha": row.source_git_blob_sha,
        "target_path": p.path, "before_sha256": p.original_sha256,
        "candidate_sha256": p.candidate_sha256,
        "task_scope_sha256": p.task_scope_sha256,
        "failure_class": FAILURE, "mechanism": p.mechanism,
        "prior_event_head_sha256": prior,
        "operator_scope": SCOPE, "development_only": True,
        "new_worker_created": False,
        "owner_self_worker_admitted": False,
        "worker_dispatched": False,
        "source_promoted": False, "scientific_first_use": False,
        "paid_model_calls": 0, "autonomous_rsi_proven": False,
    }


def reserve_original_owner_once(*, db, provider, target_path: str) -> str:
    """Reserve a single genuine new failure in original owner's WAL.

    No automatic caller, owner tick, dispatch or promotion. Only a future
    explicitly qualified original-source transition can make this code run
    on the actual Windows owner's pinned source checkout.
    """
    source = _authentic_original_owner(db, provider)
    need(type(target_path) is str and
         PATH.fullmatch(target_path) is not None,
         "TARGET_PATH_NOT_ALLOWLISTED")
    meta = db.meta()
    consumed = {
        d["task_scope_sha256"] for d in audit_owner_once(db)
    }
    try:
        report = scan(
            provider=provider, after_run_id=AFTER_RUN,
            not_before_utc=NOT_BEFORE_UTC, target_path=target_path,
            consumed_scopes=frozenset(consumed))
    except DiscoveryDenied as exc:
        raise OriginalOnceDenied("F139_RSI_R11_GITHUB_FAILURE_UNVERIFIED") from exc
    need(len(report.proposals) == 1,
         "EXACTLY_ONE_AUTHENTIC_FRESH_PROPOSAL_REQUIRED")
    payload = _payload(report.proposals[0],
                       source=source, prior=meta["head_hash"])
    # The original SQLite exclusive writer/mutex is still owned. A changed
    # head, queued research work, source transition or replay aborts atomically.
    with db.transaction():
        db.verify()
        current = db.meta()
        need(current["head_hash"] == meta["head_hash"]
             and current["source_sha"] == source
             and current["enabled"] == 1
             and current["legacy_suspended"] == 1
             and not db.actives() and db.ready() is None
             and not audit_owner_once(db),
             "OWNER_EPOCH_HEAD_OR_WORK_DRIFT")
        db.event(KIND, payload)
        db.verify()
        return db.meta()["head_hash"]
