"""Source-pinned, once-only G3 draft publication inside original F139 owner.

This module is inert except for original run_once, requires a running Windows
owner witness and the caller-held original kernel SQLite mutex. One immutable
attempt is recorded BEFORE any GitHub write; ambiguous outcomes cannot retry.
No extra controller, queue, scheduler, native dispatch, or scientific first-use.
"""
from __future__ import annotations

import json
import re
from typing import Callable

from f139.nci04_autonomy_feed import candidate_identity_from_intent_base64
from f139.nci04_candidate_producer import candidate_mechanism_identity
from f139.nci04_candidate_publisher import (
    RECIPE_G3, PublisherDenied, publisher_preflight, publish_single_draft,
)
from f139.nci04_owner_ledger import native_events

G1_ISSUE_NUMBER = 840
G1_ORIGINAL_PARENT = "992ef142aaa551156749a1de484a971b9a0c092f"
SOURCE_PATH = "yggdrasil/public_causal_cells.py"
ATTEMPT_KIND = "G3_DRAFT_ATTEMPTED"
SUCCESS_KIND = "G3_DRAFT_AUTHENTICATED"
SHA64 = re.compile(r"[a-f0-9]{64}\\Z")


class OwnerPublicationDenied(ValueError):
    pass


def need(value: bool, reason: str) -> None:
    if not value:
        raise OwnerPublicationDenied("F139_G3_" + reason)


def history_proof(db) -> tuple[set[str], set[str]]:
    """Obtain consumed identities from ORIGINAL SHA-chained SQLite custody."""
    db.verify()
    records = native_events(db)
    g1 = [record for record in records
          if record["issue_number"] == G1_ISSUE_NUMBER]
    need(len(g1) == 1, "CONSUMED_G1_ORIGINAL_ADMISSION_MISSING")
    event = g1[0]
    need(event["lane"] == "Yggdrasil" and
         event["native_path"] == SOURCE_PATH and
         event["native_target_commit"] == G1_ORIGINAL_PARENT and
         event["scientific_first_use"] is False,
         "CONSUMED_G1_SOURCE_IDENTITY_DRIFT")
    row = db.conn.execute("SELECT stage,source_sha FROM tasks WHERE ticket=?",
                          (event["ticket"],)).fetchone()
    need(row is not None and row["stage"] == "QUARANTINED"
         and row["source_sha"] == event["source_sha"],
         "CONSUMED_G1_ORIGINAL_NEGATIVE_NOT_RETAINED")
    failures = db.verified_native_provider_failures()
    need(event["ticket"] in failures and
         failures[event["ticket"]][0] == event["source_sha"],
         "CONSUMED_G1_FAILED_PROVIDER_CUSTODY_MISSING")
    candidates = {
        candidate_identity_from_intent_base64(e["native_intent_base64"])
        for e in records
    }
    need(len(candidates) == len(records),
         "CONSUMED_CANDIDATE_IDENTITY_DUPLICATE")
    return {candidate_mechanism_identity()}, candidates


def publish_once(db, get: Callable, write: Callable, source_sha: str,
                 *, owner_witness: Callable[[], bool]) -> dict:
    """One preflight and at most one draft publication; no remote retries."""
    need(callable(get) and callable(write) and callable(owner_witness)
         and owner_witness() is True,
         "ORIGINAL_RUNNING_OWNER_WITNESS_REQUIRED")
    db.verify()
    meta = db.meta()
    need(meta["enabled"] == 1 and meta["legacy_suspended"] == 1
         and meta["source_sha"] == source_sha
         and db.ready() is None and not db.actives(),
         "ORIGINAL_OWNER_NOT_IDLE")
    previous = list(db.conn.execute(
        "SELECT payload FROM events WHERE kind=?", (ATTEMPT_KIND,)))
    need(len(previous) <= 1, "ATTEMPT_CUSTODY_DUPLICATE")
    if previous:
        return {"disposition": "G3_DRAFT_ALREADY_ATTEMPTED_NO_REPLAY",
                "science_authorized": False}
    mechanisms, candidates = history_proof(db)
    historical_sha = db.meta()["head_hash"]
    need(isinstance(historical_sha, str)
         and SHA64.fullmatch(historical_sha) is not None,
         "HISTORY_SHA_INVALID")
    try:
        plan = publisher_preflight(
            get, source_sha=source_sha,
            parent_commit=G1_ORIGINAL_PARENT,
            historical_sha256=historical_sha,
            consumed_mechanisms=mechanisms,
            existing_candidate_identities=candidates,
            recipe=RECIPE_G3)
    except (PublisherDenied, ValueError) as exc:
        return {"disposition": "G3_PREFLIGHT_BLOCKED",
                "science_authorized": False,
                "reason": type(exc).__name__}
    # Persistent fail-closed intent BEFORE branch creation: loss of network,
    # power or controller process never resurrects an ambiguous attempt.
    with db.transaction():
        db.verify()
        need(db.meta()["head_hash"] == historical_sha
             and not db.actives() and db.ready() is None,
             "PREWRITE_LEDGER_MOVED")
        db.event(ATTEMPT_KIND, {
            "schema": "forge.f139.g4.original-owner-g3-attempt.v1",
            "source_sha": source_sha,
            "prior_event_head_sha256": historical_sha,
            "candidate_identity": plan["candidate_identity"],
            "mechanism_sha256": plan["mechanism_sha256"],
            "parent_commit": plan["parent_commit"],
            "source_before_sha256": plan["before_blob"],
            "source_after_sha256": plan["source_sha256"],
            "scientific_first_use": False, "retry_allowed": False,
        })
        db.verify()
    try:
        outcome = publish_single_draft(
            get, write, plan, owner_witness=owner_witness,
            consumed_mechanisms=mechanisms,
            existing_candidate_identities=candidates)
    except Exception:
        # No attempt replay, even if first POST/PUT/PR response was lost.
        # Exact original-owner ledger and remote refs require manual custody
        # reconciliation; never infer failure from an ambiguous API error.
        return {"disposition": "G3_DRAFT_OUTCOME_AMBIGUOUS_NO_RETRY",
                "science_authorized": False}
    need(outcome["authentic_single_commit_owner_draft"] is True
         and outcome["source_qualified_for_existing_feeder"] is True
         and outcome["worker_dispatched"] is False,
         "PUBLISHER_OUTCOME_NOT_AUTHENTICATED")
    with db.transaction():
        db.event(SUCCESS_KIND, {
            "schema": "forge.f139.g4.original-owner-g3-draft.v1",
            "candidate_identity": plan["candidate_identity"],
            "pr_number": outcome["pr_number"],
            "head_commit": outcome["head_commit"],
            "scientific_first_use": False, "worker_dispatched": False,
        })
        db.verify()
    return {"disposition": "G3_DRAFT_PUBLISHED",
            "pr_number": outcome["pr_number"],
            "worker_dispatched": False, "science_authorized": False}
