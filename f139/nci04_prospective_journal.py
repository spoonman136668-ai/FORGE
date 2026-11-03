"""Pre-dispatch native READY-menu custody in the EXISTING owner transaction.

This is the dispatch decision, not the upstream source-generation decision.
It proves local ledger ordering only. External clock accuracy, independently
archived custody, randomization, scientific quality and training remain unproven.
The caller retains the existing original-owner mutex and release authority.
"""
from __future__ import annotations

import json

from f139.nci04_prospective_assignment import (
    SCHEMA as ASSIGNMENT_SCHEMA, canonical, sha256, validate_assignment,
)

KIND = "NATIVE_PROSPECTIVE_ASSIGNMENT"
SCHEMA = "forge.f139.owner-prospective-assignment.v1"
POLICY = {
    "schema": "forge.f139.native-ready-dispatch-policy.v1",
    "selection": "FIRST_READY_TICKET_LEXICOGRAPHIC",
    "menu_scope": "ADMITTED_NATIVE_READY_TICKETS",
    "phase": "DISPATCH_NOT_CANDIDATE_GENERATION",
    "randomized": False,
}
FENCES = {
    "development_only": True,
    "decision_time_independently_proven": False,
    "randomization_independently_proven": False,
    "scientific_accepted": False,
    "optimizer_training_authorized": False,
    "dispatch_authorized": False,
    "scientific_first_use": False,
}


def need(condition, reason):
    if not condition:
        raise ValueError("F139_PROSPECTIVE_JOURNAL_" + reason)


def _ready_menu_at(db, before_seq):
    """Replay native admission/start/quarantine history, retaining all negatives."""
    admitted, spent = {}, set()
    for row in db.conn.execute(
            "SELECT seq,kind,payload,sha FROM events WHERE seq<? ORDER BY seq",
            (before_seq,)):
        doc = json.loads(row["payload"])
        if row["kind"] == "NATIVE_DEVELOPMENT_ADMITTED":
            ticket = doc["ticket"]
            need(ticket not in admitted, "DUPLICATE_ADMISSION")
            admitted[ticket] = {
                "ticket": ticket, "lane": doc["lane"],
                "owner_source_sha": doc["source_sha"],
                "candidate_sha256": doc["after_sha256"],
                "target_commit": doc["native_target_commit"],
                "target_tree": doc["native_target_tree"],
                "path": doc["native_path"],
                "intent_sha256": doc["native_intent_sha256"],
                "admission_event_sha256": row["sha"],
                "manifest_sha256": doc["manifest_sha256"],
            }
        elif row["kind"] in ("BEFORE_DISPATCH_INTENT", "ATTEMPT_QUARANTINED"):
            spent.add(doc["ticket"])
    return [admitted[t] for t in sorted(admitted) if t not in spent]


def _envelope(menu, ticket, timestamp, prior):
    need(bool(menu) and menu[0]["ticket"] == ticket, "SELECTION_ORDER")
    selected = menu[0]
    source, lane = selected["owner_source_sha"], selected["lane"]
    need(all(item["owner_source_sha"] == source for item in menu), "SOURCE_DRIFT")
    # This digest binds the pre-start context, NOT its own enclosing event hash.
    # The actual event SHA/sequence is supplied by the existing owner SHA chain.
    context = {"menu": menu, "policy": POLICY, "ticket": ticket,
               "decision_utc": timestamp, "prior_event_head_sha256": prior}
    assignment = {
        "schema": ASSIGNMENT_SCHEMA, "lane": lane, "ticket": ticket,
        "owner_source_sha": source,
        "candidate_sha256": selected["candidate_sha256"],
        "eligible_candidate_sha256": sorted({
            item["candidate_sha256"] for item in menu if item["lane"] == lane}),
        "policy_sha256": sha256(canonical(POLICY)),
        "selection_mode": "DETERMINISTIC", "selection_probability_bp": 10000,
        "assignment_event_sha256": sha256(canonical(context)),
        "decision_utc": timestamp, "outcome_available_at_decision": False,
    }
    validate_assignment(
        assignment, expected_ticket=ticket, expected_source_sha=source,
        expected_candidate_sha256=selected["candidate_sha256"],
        expected_eligible_hashes=assignment["eligible_candidate_sha256"])
    return {"schema": SCHEMA, "assignment": assignment,
            "eligible_native_ready": menu, "policy": dict(POLICY),
            "prior_event_head_sha256": prior, **FENCES}


def journal_native_assignment(db, ticket, timestamp):
    """Called only INSIDE Database.claim; never commits or dispatches itself."""
    need(db.conn.in_transaction, "CLAIM_TRANSACTION_REQUIRED")
    meta = db.meta()
    menu = _ready_menu_at(db, meta["head_seq"] + 1)
    ready = [dict(row) for row in db.conn.execute(
        "SELECT ticket,lane,source_sha,manifest_sha FROM tasks "
        "WHERE stage='READY' ORDER BY ticket")]
    need(bool(ready) and ready[0]["ticket"] == ticket, "SELECTION_ORDER")
    actual = [row for row in ready if row["ticket"].startswith("f139-nci04-")]
    need([(r["ticket"], r["lane"], r["source_sha"], r["manifest_sha"])
          for r in actual] ==
         [(r["ticket"], r["lane"], r["owner_source_sha"], r["manifest_sha256"])
          for r in menu], "READY_MENU_HISTORY_MISMATCH")
    need(bool(menu) and menu[0]["owner_source_sha"] == meta["source_sha"],
         "SOURCE_DRIFT")
    payload = _envelope(menu, ticket, timestamp, meta["head_hash"])
    db.event(KIND, payload)
    return payload


def audit_assignment_event(db, row, *, ready_menu=None):
    """Cold-check the historical menu and adjacent claim without rewriting it."""
    payload = json.loads(row["payload"])
    need(isinstance(payload, dict) and isinstance(payload.get("assignment"), dict),
         "FIELDS")
    assignment = payload["assignment"]
    need(isinstance(assignment.get("ticket"), str) and
         isinstance(assignment.get("decision_utc"), str), "FIELDS")
    menu = _ready_menu_at(db, row["seq"]) if ready_menu is None else ready_menu
    expected = _envelope(menu, assignment["ticket"], assignment["decision_utc"],
                         row["prior_sha"])
    need(canonical(payload) == canonical(expected), "HISTORICAL_MENU_OR_POLICY_DRIFT")
    following = db.conn.execute(
        "SELECT kind,payload FROM events WHERE seq=?", (row["seq"] + 1,)).fetchone()
    need(following is not None and following["kind"] == "BEFORE_DISPATCH_INTENT",
         "ADJACENT_CLAIM_REQUIRED")
    claim = json.loads(following["payload"])
    need(claim.get("ticket") == assignment["ticket"] and
         claim.get("started_at") == assignment["decision_utc"],
         "ADJACENT_CLAIM_IDENTITY")
    return {"local_prestart_order_verified": True,
            "assignment_sha256": sha256(canonical(assignment)), **FENCES}


def audit_assignment_events(db):
    """Audit all captures with one prefix replay, rather than one scan per capture."""
    if db.conn.execute("SELECT 1 FROM events WHERE kind=? LIMIT 1", (KIND,)).fetchone() is None:
        return
    ready = {}
    for row in db.conn.execute("SELECT * FROM events ORDER BY seq"):
        if row["kind"] == KIND:
            audit_assignment_event(
                db, row, ready_menu=[ready[t] for t in sorted(ready)])
        elif row["kind"] == "NATIVE_DEVELOPMENT_ADMITTED":
            doc = json.loads(row["payload"])
            ready[doc["ticket"]] = {
                "ticket": doc["ticket"], "lane": doc["lane"],
                "owner_source_sha": doc["source_sha"],
                "candidate_sha256": doc["after_sha256"],
                "target_commit": doc["native_target_commit"],
                "target_tree": doc["native_target_tree"],
                "path": doc["native_path"],
                "intent_sha256": doc["native_intent_sha256"],
                "admission_event_sha256": row["sha"],
                "manifest_sha256": doc["manifest_sha256"],
            }
        elif row["kind"] in ("BEFORE_DISPATCH_INTENT", "ATTEMPT_QUARANTINED"):
            ready.pop(json.loads(row["payload"])["ticket"], None)
