"""V59/V48 source-transition event *verifier*, no original-owner writer.

The previous source transition is authentically event 1858; the original
source remained active through event 1864, at which point every ticket was
terminal. This module seals historical terminal/negative and publication
custody into a proposed v48 successor document. A source-only merge does NOT
run a controller, stop a task, write a ledger, approve science or promote
an executable. Separate owner-authenticated cold backup, rehearsal and
one-shot release code is still required before an original-host transition.
"""
from __future__ import annotations

from collections import Counter
import json
import re

from f139.nci04_native_contract import canonical, digest
from f139.nci04_partial_publication_custody import IDENTITY as FIRST_NEGATIVE
from f139.nci04_ref_only_publication_custody import IDENTITY as SECOND_NEGATIVE
from f139.nci04_v59_owner_forward_readiness import (
    SOURCE, HEAD_SEQ, HEAD_SHA256, TRANSITION_SEQ, TRANSITION_SHA256,
    ACTIVATION_SEQ, ACTIVATION_SHA256, ATTEMPTS, AUTHENTICATED,
    PREDECESSOR_SCHEMA, audit_frozen_original_readonly,
)

SCHEMA = "forge.f139.source-transition.v48"
PURPOSE = "frozen-event1864-idle-original-owner-development-only"
EVENT_SEQ = HEAD_SEQ + 1
FROZEN_IDS = tuple(sorted((FIRST_NEGATIVE, SECOND_NEGATIVE)))
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
MIN_OWNER_RUN = 44518016720

FIELDS = frozenset({
    "schema", "from_source_sha", "to_source_sha",
    "prior_event_head_sha256", "event1864_ancestor_sha256",
    "prior_source_transition_sha256", "prior_activation_sha256",
    "owner_run_id", "qualified_main_run_id", "rehearsal_run_id",
    "backup_sqlite_sha256", "genenv_executable_sha256",
    "generation_mechanism_sha256", "terminal_tasks_sha256",
    "verified_historical_tasks", "custodied_negative_tasks",
    "custodied_negative_tickets", "model_draft_attempts",
    "model_draft_authenticated", "unresolved_publication_identities",
    "source_transition_purpose", "native_development_approved",
    "scientific_first_use", "new_dispatches", "new_controller",
    "new_scheduler", "new_queue", "paid_api_calls",
})

class V48TransitionDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise V48TransitionDenied("F139_V48_" + reason)


def frozen_historical_preimage(db, previous: list[dict]) -> dict:
    """Read-only immutable old-source view; never count successor work.

    The verifier can call this from Database.verify without recursive
    Database.verify(), owner privileges or any network calls.
    """
    old_sources = {
        x for t in previous for x in (t["from_source_sha"], t["to_source_sha"])
    }
    need(SOURCE in old_sources and bool(old_sources),
         "HISTORICAL_SOURCES_UNBOUND")
    history = [
        dict(row) for row in db.conn.execute(
            "SELECT ticket,lane,source_sha,stage,manifest_sha,run_id,"
            "evidence_dir,evidence_sha,quarantine_reason "
            "FROM tasks ORDER BY ticket")
        if row["source_sha"] in old_sources
    ]
    stages = Counter(x["stage"] for x in history)
    need(bool(history) and
         set(stages).issubset({"VERIFIED", "QUARANTINED"}) and
         stages["VERIFIED"] >= 155 and stages["QUARANTINED"] >= 56,
         "HISTORICAL_TASKS_NOT_TERMINAL")
    negatives = sorted(x["ticket"] for x in history
                       if x["stage"] == "QUARANTINED")
    kinds = {"MODEL_DRAFT_ATTEMPTED", "MODEL_DRAFT_AUTHENTICATED"}
    attempts: set[str] = set()
    successes: set[str] = set()
    attempt_count = 0
    success_count = 0
    for row in db.conn.execute(
            "SELECT kind,payload FROM events WHERE seq < ? AND "
            "kind IN (?,?) ORDER BY seq",
            (EVENT_SEQ, "MODEL_DRAFT_ATTEMPTED", "MODEL_DRAFT_AUTHENTICATED")):
        doc = json.loads(row["payload"])
        identity = doc.get("candidate_identity") if type(doc) is dict else None
        need(type(identity) is str and SHA64.fullmatch(identity) is not None,
             "MODEL_DRAFT_IDENTITY_INVALID")
        if row["kind"] == "MODEL_DRAFT_ATTEMPTED":
            attempt_count += 1
            need(identity not in attempts, "DUPLICATE_DRAFT_ATTEMPT")
            attempts.add(identity)
        else:
            success_count += 1
            need(identity not in successes, "DUPLICATE_DRAFT_PUBLICATION")
            successes.add(identity)
    need(attempt_count == ATTEMPTS and success_count == AUTHENTICATED
         and successes.issubset(attempts)
         and attempts - successes == set(FROZEN_IDS),
         "ORIGINAL_MODEL_DRAFT_CUSTODY_CHANGED")
    return {
        "terminal_tasks_sha256": digest(canonical(history)),
        "verified_historical_tasks": stages["VERIFIED"],
        "custodied_negative_tasks": stages["QUARANTINED"],
        "custodied_negative_tickets": negatives,
        "model_draft_attempts": attempt_count,
        "model_draft_authenticated": success_count,
        "unresolved_publication_identities": list(FROZEN_IDS),
    }


def verify_cold_event(db, row, doc, previous) -> bool:
    """Replay exactly one v48 source event after authentic event1864.

    This is NOT owner approval. It is called under the existing full
    Database.verify event hash chain; it never calls db.verify itself.
    """
    need(type(previous) is list and bool(previous)
         and type(doc) is dict and set(doc) == FIELDS,
         "EVENT_FIELDS_INVALID")
    need(previous[-1].get("schema") == PREDECESSOR_SCHEMA
         and previous[-1].get("to_source_sha") == SOURCE
         and doc["schema"] == SCHEMA
         and doc["from_source_sha"] == SOURCE
         and doc["source_transition_purpose"] == PURPOSE
         and row["seq"] == EVENT_SEQ
         and row["prior_sha"] == HEAD_SHA256
         and doc["prior_event_head_sha256"] == HEAD_SHA256
         and doc["event1864_ancestor_sha256"] == HEAD_SHA256
         and doc["prior_source_transition_sha256"] == TRANSITION_SHA256
         and doc["prior_activation_sha256"] == ACTIVATION_SHA256
         and type(doc["to_source_sha"]) is str
         and SHA40.fullmatch(doc["to_source_sha"]) is not None
         and doc["to_source_sha"] != SOURCE
         and doc["to_source_sha"] not in {
             x for t in previous for x in
             (t["from_source_sha"], t["to_source_sha"])
         }
         and not any(t.get("schema") == SCHEMA for t in previous),
         "SOURCE_ANCESTRY_OR_REPLAY_INVALID")
    original = db.conn.execute(
        "SELECT seq,kind,sha,payload FROM events WHERE seq=?",
        (HEAD_SEQ,)).fetchone()
    prior_source = db.conn.execute(
        "SELECT seq,sha FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' "
        "AND seq < ? ORDER BY seq DESC LIMIT 1",
        (EVENT_SEQ,)).fetchone()
    prior_activation = db.conn.execute(
        "SELECT seq,sha,payload FROM events WHERE "
        "kind='NATIVE_DEVELOPMENT_ACTIVATED' "
        "AND seq < ? ORDER BY seq DESC LIMIT 1",
        (EVENT_SEQ,)).fetchone()
    need(original is not None
         and original["seq"] == HEAD_SEQ
         and original["kind"] == "NATIVE_V_TWO_PROVIDER_CUSTODY"
         and original["sha"] == HEAD_SHA256
         and prior_source is not None
         and prior_source["seq"] == TRANSITION_SEQ
         and prior_source["sha"] == TRANSITION_SHA256
         and prior_activation is not None
         and prior_activation["seq"] == ACTIVATION_SEQ
         and prior_activation["sha"] == ACTIVATION_SHA256
         and json.loads(prior_activation["payload"])["source_sha"] == SOURCE,
         "ORIGINAL_EVENT1864_OR_ACTIVATION_DRIFT")
    need(type(doc["owner_run_id"]) is int
         and doc["owner_run_id"] > MIN_OWNER_RUN
         and type(doc["qualified_main_run_id"]) is int
         and doc["qualified_main_run_id"] > 0
         and type(doc["rehearsal_run_id"]) is int
         and doc["rehearsal_run_id"] > 0
         and doc["rehearsal_run_id"] != doc["qualified_main_run_id"]
         and all(type(doc[k]) is str and SHA64.fullmatch(doc[k]) is not None
                 for k in ("backup_sqlite_sha256",
                           "genenv_executable_sha256",
                           "generation_mechanism_sha256"))
         and doc["native_development_approved"] is True
         and doc["scientific_first_use"] is False
         and type(doc["new_dispatches"]) is int
         and doc["new_dispatches"] == 0
         and doc["new_controller"] is False
         and doc["new_scheduler"] is False
         and doc["new_queue"] is False
         and type(doc["paid_api_calls"]) is int
         and doc["paid_api_calls"] == 0,
         "QUALIFICATION_OR_AUTHORITY_SCOPE_INVALID")
    snapshot = frozen_historical_preimage(db, previous)
    need(all(doc.get(k) == value for k, value in snapshot.items()),
         "FROZEN_NEGATIVES_OR_TERMINAL_CUSTODY_CHANGED")
    need(type(doc["terminal_tasks_sha256"]) is str and
         SHA64.fullmatch(doc["terminal_tasks_sha256"]) is not None,
         "HISTORICAL_TASKS_SHA_INVALID")
    return True


def proposed_cold_proof(db, *, target: str, owner_run_id: int,
                        qualified_main_run_id: int, rehearsal_run_id: int,
                        backup_sqlite_sha256: str,
                        genenv_executable_sha256: str,
                        generation_mechanism_sha256: str) -> dict:
    """Propose a successor from a read-only DB, without admission or writing.

    Requires original owner-host source/policy/custody validation outside this
    function. The returned dictionary is not a dispatch or transition grant.
    """
    audit = audit_frozen_original_readonly(db)
    need(audit["owner_mutations"] == 0
         and audit["source_transition_authorized"] is False
         and audit["scientific_first_use"] is False,
         "V59_COLD_AUTHORITY_DRIFT")
    previous = [
        json.loads(x["payload"]) for x in db.conn.execute(
            "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED'"
            " ORDER BY seq")
    ]
    doc = {
        "schema": SCHEMA, "from_source_sha": SOURCE,
        "to_source_sha": target,
        "prior_event_head_sha256": HEAD_SHA256,
        "event1864_ancestor_sha256": HEAD_SHA256,
        "prior_source_transition_sha256": TRANSITION_SHA256,
        "prior_activation_sha256": ACTIVATION_SHA256,
        "owner_run_id": owner_run_id,
        "qualified_main_run_id": qualified_main_run_id,
        "rehearsal_run_id": rehearsal_run_id,
        "backup_sqlite_sha256": backup_sqlite_sha256,
        "genenv_executable_sha256": genenv_executable_sha256,
        "generation_mechanism_sha256": generation_mechanism_sha256,
        "source_transition_purpose": PURPOSE,
        "native_development_approved": True,
        "scientific_first_use": False, "new_dispatches": 0,
        "new_controller": False, "new_scheduler": False,
        "new_queue": False, "paid_api_calls": 0,
        **frozen_historical_preimage(db, previous),
    }
    verify_cold_event(db, {"seq": EVENT_SEQ,
                           "prior_sha": HEAD_SHA256}, doc, previous)
    return doc
