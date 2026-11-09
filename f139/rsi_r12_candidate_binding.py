"""R12: read-only bind an R6 candidate to the R11 ORIGINAL reservation.

This is NOT a signed worker ticket, authorization, worker dispatch, replay
permission, qualification result, source promotion, or scientific first-use.
The existing signed FORGE-self lane remains closed.  Never treat an
untrusted fixture or this candidate envelope as authority to execute.
"""
from __future__ import annotations

from hashlib import sha256
import json
import sqlite3

from f139.local_controller import Database, canonical
from f139.rsi_r11_owner_once import KIND, SCHEMA as R11_SCHEMA, audit_owner_once
from f139.rsi_r6_provider_readback import Readback
from f139.rsi_r6_known_repair_cycle import (
    SCHEMA as R6_SCHEMA, FAILURE, HEAD, DIGEST, PATH, digest,
)

SCHEMA = "forge.f139.rsi-r12.original-candidate-readonly-binding.v1"


class CandidateBindingDenied(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise CandidateBindingDenied("F139_RSI_R12_" + code)


def original_owner_database(db) -> bool:
    """Match the actual Python -m owner entrypoint without trusting lookalikes.

    The original owner's f139.local_controller is executed as __main__ by
    its installed task. R11/R12-C already support that Python module split.
    Both this predicate AND the complete cold ledger verification are required.
    """
    return (
        type(db).__name__ == "Database"
        and type(db).__module__ in (
            "f139.local_controller", "local_controller", "__main__")
        and type(getattr(db, "conn", None)) is sqlite3.Connection
    )


def matches_reserved_candidate(reservation: dict, candidate: Readback) -> bool:
    """Compare all relevant candidate/source identities, without granting trust."""
    if type(reservation) is not dict or type(candidate) is not Readback:
        return False
    p = candidate.proposal
    try:
        return (
            reservation["schema"] == R11_SCHEMA
            and reservation["failure_class"] == FAILURE
            and candidate.schema == "forge.f139.rsi-r6.readonly-github-evidence.v1"
            and p.schema == R6_SCHEMA
            and candidate.run_id == reservation["failed_run_id"]
            and candidate.job_id == reservation["failed_job_id"]
            and candidate.original_head_sha == reservation["failed_head_sha"]
            and candidate.path == reservation["target_path"] == p.path
            and candidate.source_git_blob_sha == reservation["source_git_blob_sha"]
            and candidate.log_sha256 == reservation["failed_log_sha256"]
            and p.parent_sha == candidate.original_head_sha
            and p.original_sha256 == reservation["before_sha256"]
            and p.candidate_sha256 == reservation["candidate_sha256"]
            and p.task_scope_sha256 == reservation["task_scope_sha256"]
            and p.original_failure_class == FAILURE
            and p.mechanism == reservation["mechanism"]
            and type(p.source) is bytes
            and digest(p.source) == p.candidate_sha256
            and not candidate.original_owner_admitted
            and not candidate.source_regression_pass
            and not candidate.scientific_first_use
            and not candidate.production_release
            and not p.eligible_for_owner
            and not p.qualified
            and not p.scientific_first_use
            and not p.deployed
            and not p.autonomous_rsi_proven
        )
    except (KeyError, AttributeError, TypeError, ValueError):
        return False


def binding_from_reservation_event(*, reservation: dict, row,
                                   expected_owner_source_sha: str) -> dict:
    """Pure historical data projection; NOT original-owner authentication.

    Call only AFTER a cold R11 audit and the owner's complete ledger verifier.
    The immutable reservation event SHA, not mutable current ledger head, must
    survive an issuance append, unrelated events, and cold restart.
    """
    need(type(reservation) is dict
         and type(expected_owner_source_sha) is str
         and HEAD.fullmatch(expected_owner_source_sha) is not None,
         "HISTORICAL_BINDING_INPUT_INVALID")
    try:
        need(reservation["schema"] == R11_SCHEMA
             and reservation["owner_source_sha"] == expected_owner_source_sha
             and type(row["seq"]) is int and row["seq"] > 0
             and type(row["sha"]) is str and DIGEST.fullmatch(row["sha"])
             and row["prior_sha"] == reservation["prior_event_head_sha256"]
             and json.loads(row["payload"]) == reservation,
             "HISTORICAL_RESERVATION_ROW_DRIFT")
        packet = {
            "schema": SCHEMA,
            "owner_source_sha": expected_owner_source_sha,
            "reservation_seq": row["seq"],
            "reservation_event_sha256": row["sha"],
            # Historical head AT reservation, never mutable current meta head.
            "original_owner_ledger_head_sha256": row["sha"],
            "failed_head_sha": reservation["failed_head_sha"],
            "failed_run_id": reservation["failed_run_id"],
            "failed_job_id": reservation["failed_job_id"],
            "failed_log_sha256": reservation["failed_log_sha256"],
            "source_git_blob_sha": reservation["source_git_blob_sha"],
            "target_path": reservation["target_path"],
            "before_sha256": reservation["before_sha256"],
            "candidate_sha256": reservation["candidate_sha256"],
            "task_scope_sha256": reservation["task_scope_sha256"],
            "mechanism": reservation["mechanism"],
            "development_only": True,
            "original_owner_signed": False,
            "worker_admitted": False,
            "worker_dispatched": False,
            "original_regression_qualified": False,
            "scientific_first_use": False,
            "source_promoted": False,
            "autonomous_rsi_proven": False,
        }
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise CandidateBindingDenied(
            "F139_RSI_R12_HISTORICAL_RESERVATION_INVALID") from exc
    packet["candidate_binding_sha256"] = sha256(canonical(packet)).hexdigest()
    return packet


def bind_original_candidate(*, db: Database, candidate: Readback,
                            expected_owner_source_sha: str) -> dict:
    """Produce a stable, non-executable identifier after a *cold* R11 audit.

    No owner lane, original SQLite event, ticket, signature, workflow, or Git
    ref is changed.  This call cannot be used to admit a development job.
    """
    need(original_owner_database(db)
         and type(expected_owner_source_sha) is str
         and HEAD.fullmatch(expected_owner_source_sha) is not None,
         "ORIGINAL_DATABASE_OR_SOURCE_INVALID")
    db.verify()
    reservations = audit_owner_once(db)
    need(len(reservations) == 1, "ONE_AUTHENTIC_RESERVATION_REQUIRED")
    reserved = reservations[0]
    need(reserved["owner_source_sha"] == expected_owner_source_sha
         and matches_reserved_candidate(reserved, candidate),
         "RESERVATION_OR_CANDIDATE_DRIFT")
    need(type(reserved["task_scope_sha256"]) is str
         and DIGEST.fullmatch(reserved["task_scope_sha256"]) is not None
         and type(reserved["target_path"]) is str
         and PATH.fullmatch(reserved["target_path"]) is not None,
         "TARGET_SCOPE_INVALID")
    rows = list(db.conn.execute(
        "SELECT seq,prior_sha,sha,payload FROM events WHERE kind=? "
        "ORDER BY seq", (KIND,)))
    need(len(rows) == 1, "RESERVATION_LEDGER_CARDINALITY")
    row = rows[0]
    need(row["seq"] > 0
         and row["prior_sha"] == reserved["prior_event_head_sha256"]
         and type(row["sha"]) is str and DIGEST.fullmatch(row["sha"]) is not None
         and json.loads(row["payload"]) == reserved,
         "RESERVATION_LEDGER_ROW_DRIFT")
    before_head = db.meta()["head_hash"]
    result = binding_from_reservation_event(
        reservation=reserved, row=row,
        expected_owner_source_sha=expected_owner_source_sha)
    need(db.meta()["head_hash"] == before_head,
         "OWNER_HEAD_CHANGED_DURING_READ")
    return result
