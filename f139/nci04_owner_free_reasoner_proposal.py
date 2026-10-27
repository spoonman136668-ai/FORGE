"""Bounded real free Nemotron proposal under the ONE original F139 owner.

Source-only integration. It does not schedule itself, install new credentials,
dispatch workers, open private repositories, run science, or bypass the V12
original owner's once-only draft publisher. The future native owner hook must
hold SingleOwner, attest the Windows scheduled-task/Python-child identity, and
supply an already available credential. No Codex or paid fallback exists.

An immutable original SQLite event precedes EVERY attempted external model
POST. Model requests can advance only when genuine native terminal outcomes
change. Uncertain network results can never replay the same history scope.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
from typing import Callable

from f139.local_controller import Database
from f139.nci04_free_reasoner_provider import (
    FreeReasonerDenied, MODEL, infer_free_once, public_packet,
    verify_anonymous_public_source,
)
from f139.nci04_model_owner_bridge import owner_request
from f139.nci04_model_owner_publication import publish_model_once
from f139.nci04_native_contract import canonical, digest

ATTEMPT = "FREE_REASONER_ATTEMPTED"
SCHEMA = "forge.f139.owner-free-reasoner-attempt.v1"
MAX_DAILY_REQUESTS = 1
MAX_LIFETIME_REQUESTS = 8
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
DAY = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


class FreeOwnerDenied(ValueError):
    pass


def need(ok: bool, why: str) -> None:
    if not ok:
        raise FreeOwnerDenied("F139_FREE_OWNER_" + why)


def original_outcome_fingerprint(db: Database) -> str:
    """Retained original task outcomes, independent of the model-attempt head."""
    need(type(db) is Database, "ORIGINAL_DATABASE_REQUIRED")
    db.verify()
    rows = [dict(r) for r in db.conn.execute(
        "SELECT ticket,lane,source_sha,stage,run_id,evidence_sha,"
        "quarantine_reason FROM tasks ORDER BY ticket")]
    need(bool(rows) and
         all(row["stage"] in {"VERIFIED", "QUARANTINED"} for row in rows)
         and any(row["stage"] == "VERIFIED" for row in rows),
         "NO_TERMINAL_NATIVE_LEARNING_HISTORY")
    return digest(canonical({
        "schema": "forge.f139.owner-terminal-feedback.v1",
        "original_terminal_tasks": rows,
    }))


def reasoner_scope(*, source_sha: str, lane: str, target_commit: str,
                   path: str, original_feedback_sha256: str) -> str:
    need(type(source_sha) is str and SHA40.fullmatch(source_sha) is not None
         and type(target_commit) is str
         and SHA40.fullmatch(target_commit) is not None
         and lane in ("Yggdrasil", "Wingless")
         and type(path) is str and 1 <= len(path) <= 200
         and type(original_feedback_sha256) is str
         and SHA64.fullmatch(original_feedback_sha256) is not None,
         "SCOPE_INVALID")
    return digest(canonical({
        "schema": "forge.f139.owner-free-reasoner-scope.v1",
        "model": MODEL,
        "source_sha": source_sha, "lane": lane,
        "target_commit": target_commit, "path": path,
        "original_feedback_sha256": original_feedback_sha256,
    }))


def _attempts(db: Database) -> list[dict]:
    attempts = []
    for row in db.conn.execute(
        "SELECT payload FROM events WHERE kind=? ORDER BY seq", (ATTEMPT,)):
        item = json.loads(row["payload"])
        need(type(item) is dict and
             set(item) == {"schema", "source_sha", "model", "scope_sha256",
                           "original_feedback_sha256", "lane", "target_commit",
                           "path", "utc_day", "prior_event_head_sha256",
                           "remote_request_retry_authorized", "paid_model_calls",
                           "scientific_first_use"}
             and item["schema"] == SCHEMA and item["model"] == MODEL
             and type(item["scope_sha256"]) is str
             and SHA64.fullmatch(item["scope_sha256"]) is not None
             and item["remote_request_retry_authorized"] is False
             and type(item["paid_model_calls"]) is int
             and item["paid_model_calls"] == 0
             and item["scientific_first_use"] is False,
             "ORIGINAL_ATTEMPT_HISTORY_INVALID")
        attempts.append(item)
    need(len(attempts) <= MAX_LIFETIME_REQUESTS
         and len({x["scope_sha256"] for x in attempts}) == len(attempts),
         "ORIGINAL_ATTEMPT_DUPLICATE_OR_BUDGET")
    return attempts


def reasoner_proposal_once(
    db: Database, get: Callable, steering_get: Callable, write: Callable,
    *, source_sha: str, lane: str, target_commit: str, path: str,
    owner_witness: Callable[[], bool],
    token: str | None = None,
    transport: Callable[[bytes, str], bytes] | None = None,
    public_reader: Callable[[str], dict] | None = None,
    utc_day: str | None = None,
) -> dict:
    """One scoped public/free proposal; no automatic retry or new authority.

    A request attempt is committed before any inference call. No token is
    stored, printed, placed in a GitHub issue, or sent to the owner's journal.
    The external model sees only the independently public, minimal packet.
    """
    need(type(db) is Database
         and callable(get) and callable(steering_get) and callable(write)
         and callable(owner_witness) and owner_witness() is True,
         "ORIGINAL_OWNER_NOT_ATTESTED")
    db.verify()
    if token is None:
        token = os.environ.get("OPENROUTER_API_KEY")
    if not isinstance(token, str) or not token.strip():
        return {"disposition": "FREE_REASONER_NO_CREDENTIAL_NO_REQUEST",
                "scientific_first_use": False,
                "worker_dispatched": False, "paid_model_calls": 0}
    # No model request is attempted if the signed owner session/steering,
    # public file or current source is stale.
    initial = owner_request(
        db, get, steering_get, source_sha=source_sha,
        lane=lane, target_commit=target_commit, path=path,
        owner_witness=owner_witness)
    request = initial["request"]
    public = public_packet(request, public_source_verified=True)
    need(verify_anonymous_public_source(public, public_reader) is True,
         "PUBLIC_SOURCE_NOT_INDEPENDENTLY_VERIFIED")
    feedback = original_outcome_fingerprint(db)
    scope = reasoner_scope(source_sha=source_sha, lane=lane,
                           target_commit=target_commit, path=path,
                           original_feedback_sha256=feedback)
    today = utc_day if utc_day is not None else dt.datetime.now(
        dt.timezone.utc).strftime("%Y-%m-%d")
    need(type(today) is str and DAY.fullmatch(today) is not None,
         "UTC_DAY_INVALID")
    prior = _attempts(db)
    if scope in {x["scope_sha256"] for x in prior}:
        return {"disposition": "FREE_REASONER_SCOPE_ALREADY_ATTEMPTED_NO_REPLAY",
                "scientific_first_use": False,
                "worker_dispatched": False, "paid_model_calls": 0}
    if (len(prior) >= MAX_LIFETIME_REQUESTS
        or sum(row["utc_day"] == today for row in prior) >= MAX_DAILY_REQUESTS):
        return {"disposition": "FREE_REASONER_BOUNDED_BUDGET_EXHAUSTED",
                "scientific_first_use": False,
                "worker_dispatched": False, "paid_model_calls": 0}
    if prior:
        need(today >= prior[-1]["utc_day"], "UTC_CLOCK_ROLLBACK")
    with db.transaction():
        db.verify()
        need(db.meta()["head_seq"] == initial["session"]["owner_head_seq"]
             and db.meta()["head_hash"] == initial["session"]["owner_head_sha256"]
             and original_outcome_fingerprint(db) == feedback
             and owner_witness() is True,
             "ORIGINAL_PRE_REQUEST_STATE_MOVED")
        need(scope not in {x["scope_sha256"] for x in _attempts(db)},
             "ORIGINAL_ATTEMPT_REPLAY_DENIED")
        db.event(ATTEMPT, {
            "schema": SCHEMA, "source_sha": source_sha, "model": MODEL,
            "scope_sha256": scope,
            "original_feedback_sha256": feedback,
            "lane": lane, "target_commit": target_commit,
            "path": path, "utc_day": today,
            "prior_event_head_sha256": initial["session"]["owner_head_sha256"],
            "remote_request_retry_authorized": False,
            "paid_model_calls": 0, "scientific_first_use": False,
        })
        db.verify()
    # The stored at-most-once request changes the hash head, therefore a
    # NEW owner session is mandatory before model inference/publication.
    prepared = owner_request(
        db, get, steering_get, source_sha=source_sha,
        lane=lane, target_commit=target_commit, path=path,
        owner_witness=owner_witness)
    new_request = prepared["request"]
    need(new_request["source"] == request["source"]
         and new_request["before_sha256"] == request["before_sha256"]
         and new_request["target_tree_sha"] == request["target_tree_sha"]
         and original_outcome_fingerprint(db) == feedback,
         "SOURCE_OR_ORIGINAL_FEEDBACK_CHANGED_AFTER_ATTEMPT")
    # infer_free_once repeats the anonymous Git proof before the one HTTP
    # POST and never falls back to a paid model. A provider 429/timeout is
    # sticky: the original request attempt already exists, so no replay.
    result = infer_free_once(
        public_packet(new_request, public_source_verified=True),
        token=token, transport=transport, public_reader=public_reader)
    need(result["paid_model_calls"] == 0
         and result["publication_authorized"] is False
         and result["scientific_first_use"] is False,
         "FREE_MODEL_UNTRUSTED_RESPONSE_AUTHORITY_DRIFT")
    final = publish_model_once(
        db, get, steering_get, write,
        session=prepared["session"],
        raw_response=result["proposal_bytes"],
        owner_witness=owner_witness)
    return {**final, "generator": "PUBLIC_FREE_NEMOTRON_HISTORY_GROUNDED",
            "remote_request_scope_sha256": scope,
            "paid_model_calls": 0, "scientific_first_use": False}
