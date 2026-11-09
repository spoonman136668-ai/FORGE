"""One-shot installed V39 -> three-lane DEV source handoff, preserving original custody.

No controller, inference, dispatch, scientific first-use or implicit activation.
Original custody checks remain mandatory; a growing ledger is not a reset.
"""
import json
import re

from f139.local_controller import Database, SingleOwner, g54_original_canonical
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_ledger import verify_native_activation

FROM_V39 = "42c70d74dd93ef90d0f4618fefefe2206b81eafe"
MIN_HEAD = 1462
MIN_VERIFIED = 113
QUALIFIED_WORKER_BLOB = "74dd90e6d71da6b53898c7a80d5362f1b0e6af27"
TOOLCHAIN = "go1.23.12 windows/amd64"
SCHEMA = "forge.f139.source-transition.v35"
FIELDS = frozenset({"schema", "from_source_sha", "to_source_sha", "owner_event_id",
    "prior_event_head_sha256", "original_head_seq", "verified_historical_tasks",
    "custodied_negative_tasks", "custodied_negative_tickets", "terminal_tasks_sha256",
    "history_sha256", "v39_transition_sha256", "preserved_counters",
    "i1464_negative_event_sha256", "i1464_original_receipt_sha256",
    "genenv_executable_sha256", "genenv_toolchain", "generation_mechanism_sha256", "partial_publication_custody", "qualified_worker_blob",
    "new_dispatches", "scientific_first_use", "v2_receipt_authorized",
    "purpose"})


from f139.nci04_v36_source_transition import (
    I1464_TICKET, I1464_EVENT, I1464_RECEIPT, i1464_negative_anchor, MaintenanceDenied)


def need(ok, reason):
    if not ok:
        raise MaintenanceDenied("F139_V40_" + reason)


def preserved_counters_valid(counts):
    keys = {"G3_DRAFT_ATTEMPTED", "G3_DRAFT_AUTHENTICATED", "MODEL_DRAFT_ATTEMPTED",
            "MODEL_DRAFT_AUTHENTICATED", "FREE_REASONER_ATTEMPTED"}
    return (type(counts) is dict and set(counts) == keys
            and all(type(n) is int and n >= 0 for n in counts.values())
            and counts["G3_DRAFT_ATTEMPTED"] == counts["G3_DRAFT_AUTHENTICATED"] == 1
            and counts["FREE_REASONER_ATTEMPTED"] == 8
            and counts["MODEL_DRAFT_ATTEMPTED"] >= 127
            and counts["MODEL_DRAFT_AUTHENTICATED"] >= 126
            and counts["MODEL_DRAFT_ATTEMPTED"] ==
                counts["MODEL_DRAFT_AUTHENTICATED"] + 1)



def idle_gate_predicates(db):
    """Read-only guard evidence only; NEVER admission or owner authority."""
    need(type(db) is Database
         and SingleOwner.held(db.filename.with_suffix(".lock")),
         "ORIGINAL_DATABASE_MUTEX_REQUIRED")
    db.verify()
    meta = db.meta()
    return {
        "v39_source": meta["source_sha"] == FROM_V39,
        "history_floor": meta["head_seq"] >= MIN_HEAD,
        "owner_enabled": meta["enabled"] == 1,
        "legacy_suspended": meta["legacy_suspended"] == 1,
        "no_ready": db.ready() is None,
        "no_active": not db.actives(),
        "native_activation": verify_native_activation(db),
    }


def validate_idle(db):
    db.verify()
    meta = db.meta()
    need(meta["source_sha"] == FROM_V39 and meta["head_seq"] >= MIN_HEAD
         and meta["enabled"] == 1 and meta["legacy_suspended"] == 1
         and db.ready() is None and not db.actives() and verify_native_activation(db),
         "IDLE_GENUINE_V39_REQUIRED")


def snapshot(db, row, previous):
    need(bool(previous) and previous[-1]["schema"] == "forge.f139.source-transition.v34"
         and previous[-1]["to_source_sha"] == FROM_V39, "GENUINE_V39_PREDECESSOR_REQUIRED")
    seal = db.conn.execute(
        "SELECT seq,sha,payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' "
        "AND seq<? ORDER BY seq DESC LIMIT 1", (row["seq"],)).fetchone()
    need(seal is not None and re.fullmatch(r"[a-f0-9]{64}", seal["sha"]) is not None
         and json.loads(seal["payload"]) == previous[-1], "V39_SEAL_DRIFT")
    sources = {s for tr in previous for s in (tr["from_source_sha"], tr["to_source_sha"])}
    tasks = [dict(t) for t in db.conn.execute(
        "SELECT ticket,stage,run_id,evidence_sha,evidence_dir,source_sha FROM tasks ORDER BY ticket")
        if t["source_sha"] in sources]
    need(all(t["stage"] in ("VERIFIED", "QUARANTINED") for t in tasks),
         "HISTORICAL_TASK_NOT_TERMINAL")
    from f139.nci04_negative_owner_store import TICKET as FIRST
    from f139.nci04_split_negative_owner_store import TICKET as SECOND
    from f139.nci04_g49_prepost_negative import TICKET as PREPOST
    failures = db.verified_native_provider_failures(through_seq=row["seq"])
    negatives = sorted({FIRST, SECOND, PREPOST,
        g54_original_canonical(db, through_seq=row["seq"])["ticket"],
        i1464_negative_anchor(db, row["seq"])} | set(failures))
    positive = [t for t in tasks if t["stage"] == "VERIFIED"]
    negative = [t for t in tasks if t["stage"] == "QUARANTINED"]
    need(len(positive) >= MIN_VERIFIED and 56 <= len(negative) <= 100
         and sorted(t["ticket"] for t in negative) == negatives,
         "ORIGINAL_TERMINAL_CUSTODY_DRIFT")
    history = [dict(e) for e in db.conn.execute(
        "SELECT seq,kind,sha FROM events WHERE seq<? ORDER BY seq", (row["seq"],))]
    need(len(history) == row["seq"] - 1 and len(history) >= MIN_HEAD
         and history[-1]["sha"] == row["prior_sha"], "EXACT_PREFIX_DRIFT")
    from f139.nci04_partial_publication_custody import validate_retained, PartialPublicationDenied
    from f139.nci04_v38_source_transition import FROM_V37
    from f139.nci04_v39_source_transition import FROM_V38
    try:
        need(type(previous[-1].get("original_head_seq")) is int
             and seal["seq"] == previous[-1]["original_head_seq"] + 1,
             "V39_SEAL_BOUNDARY_DRIFT")
        v38 = db.conn.execute(
            "SELECT seq,payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' "
            "AND sha=? AND seq<?", (previous[-1]["v38_transition_sha256"], seal["seq"])).fetchall()
        need(len(v38) == 1 and json.loads(v38[0]["payload"])["schema"] ==
             "forge.f139.source-transition.v33" and
             json.loads(v38[0]["payload"])["to_source_sha"] == FROM_V38,
             "ORIGINAL_V38_SEAL_DRIFT")
        v38_doc = json.loads(v38[0]["payload"])
        v37 = db.conn.execute(
            "SELECT seq,payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' "
            "AND sha=? AND seq<?", (v38_doc["v37_transition_sha256"], v38[0]["seq"])).fetchall()
        need(len(v37) == 1 and json.loads(v37[0]["payload"])["schema"] ==
             "forge.f139.source-transition.v32" and
             json.loads(v37[0]["payload"])["to_source_sha"] == FROM_V37,
             "ORIGINAL_V37_SEAL_DRIFT")
        partial = validate_retained(db, row["seq"], v37[0]["seq"], FROM_V37,
            successor_boundary=v38[0]["seq"], successor_source=FROM_V38,
            second_successor_boundary=seal["seq"], second_successor_source=FROM_V39)
    except PartialPublicationDenied as exc:
        raise MaintenanceDenied("F139_V40_PARTIAL_PUBLICATION_CUSTODY_DRIFT") from exc
    counters = {k:sum(e["kind"] == k for e in history) for k in (
        "G3_DRAFT_ATTEMPTED", "G3_DRAFT_AUTHENTICATED", "MODEL_DRAFT_ATTEMPTED",
        "MODEL_DRAFT_AUTHENTICATED", "FREE_REASONER_ATTEMPTED")}
    need(preserved_counters_valid(counters), "SPENT_HISTORY_DRIFT")
    return dict(verified_historical_tasks=len(positive), custodied_negative_tasks=len(negative),
        custodied_negative_tickets=negatives, terminal_tasks_sha256=digest(canonical(tasks)),
        history_sha256=digest(canonical(history)), v39_transition_sha256=seal["sha"],
        preserved_counters=counters,
        i1464_negative_event_sha256=I1464_EVENT,
        i1464_original_receipt_sha256=I1464_RECEIPT,
        partial_publication_custody=partial)


def verify_cold_event(db, row, doc, previous):
    # Confirm a UNIQUE genuine V39 predecessor before iterating source
    # identities or relying on a later snapshot. This also prevents malformed
    # historical data from raising an unclassified KeyError.
    need(type(previous) is list and len(previous) > 0
         and all(type(item) is dict
                 and type(item.get("from_source_sha")) is str
                 and type(item.get("to_source_sha")) is str
                 and type(item.get("schema")) is str
                 for item in previous)
         and previous[-1]["schema"] == "forge.f139.source-transition.v34"
         and previous[-1]["to_source_sha"] == FROM_V39
         and previous[-1].get("from_source_sha") == "54d556c3fdf1023d650f76c48ffb1bdc5ccc9135"
         and sum(item["schema"] == "forge.f139.source-transition.v34"
                 for item in previous) == 1,
         "GENUINE_UNIQUE_V39_PREDECESSOR_REQUIRED")
    need(type(doc) is dict and set(doc) == FIELDS and doc["schema"] == SCHEMA
         and type(doc["original_head_seq"]) is int and doc["original_head_seq"] >= MIN_HEAD
         and row["seq"] == doc["original_head_seq"] + 1
         and doc["prior_event_head_sha256"] == row["prior_sha"]
         and doc["from_source_sha"] == FROM_V39
         and type(doc["owner_event_id"]) is int and doc["owner_event_id"] > 0
         and type(doc["new_dispatches"]) is int and doc["new_dispatches"] == 0
         and doc["scientific_first_use"] is False and doc["v2_receipt_authorized"] is False
         and doc["purpose"] == "three-lane-development-source-handoff"
         and doc["qualified_worker_blob"] == QUALIFIED_WORKER_BLOB
         and type(doc["to_source_sha"]) is str
         and re.fullmatch(r"[a-f0-9]{40}", doc["to_source_sha"])
         and doc["to_source_sha"] not in {s for tr in previous
             for s in (tr["from_source_sha"], tr["to_source_sha"])}
         and not any(tr["schema"] == SCHEMA for tr in previous)
         and preserved_counters_valid(doc["preserved_counters"])
         and type(doc["genenv_executable_sha256"]) is str
         and re.fullmatch(r"[a-f0-9]{64}", doc["genenv_executable_sha256"])
         and type(doc["generation_mechanism_sha256"]) is str
         and re.fullmatch(r"[a-f0-9]{64}", doc["generation_mechanism_sha256"])
         and doc["genenv_toolchain"] == TOOLCHAIN, "EVENT_IDENTITY_OR_AUTHORITY_DRIFT")
    need(all(doc[k] == v for k, v in snapshot(db, row, previous).items()), "ORIGINAL_STATE_DRIFT")


def build_proof(db, target, event_id, binary_sha, toolchain):
    need(type(db) is Database and SingleOwner.held(db.filename.with_suffix(".lock")),
         "ORIGINAL_DATABASE_MUTEX_REQUIRED")
    validate_idle(db)
    meta = db.meta()
    previous = [json.loads(r["payload"]) for r in db.conn.execute(
        "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")]
    row = dict(seq=meta["head_seq"] + 1, prior_sha=meta["head_hash"])
    from f139.nci04_genenv_owner_backend import generation_mechanism
    doc = dict(schema=SCHEMA, from_source_sha=FROM_V39, to_source_sha=target,
        owner_event_id=event_id, prior_event_head_sha256=meta["head_hash"],
        original_head_seq=meta["head_seq"], **snapshot(db, row, previous),
        genenv_executable_sha256=binary_sha, genenv_toolchain=toolchain,
        generation_mechanism_sha256=digest(generation_mechanism()),
        new_dispatches=0, scientific_first_use=False,
         v2_receipt_authorized=False, purpose="three-lane-development-source-handoff",
         qualified_worker_blob=QUALIFIED_WORKER_BLOB)
    verify_cold_event(db, row, doc, previous)
    return doc


def readonly_snapshot(db):
    """A readiness witness only. The caller's kernel lease grants no admission."""
    need(type(db) is Database and getattr(db, "_readonly_opened", False) is True
         and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and SingleOwner.held(db.filename.with_suffix(".lock")),
         "READONLY_ORIGINAL_REQUIRED")
    validate_idle(db)
    before = db.meta().copy()
    previous = [json.loads(r["payload"]) for r in db.conn.execute(
        "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")]
    state = snapshot(db, dict(seq=before["head_seq"]+1, prior_sha=before["head_hash"]), previous)
    need(db.meta() == before, "READONLY_HEAD_MOVED")
    from f139.hybrid_owner_admission import is_migrated
    return dict(schema="forge.f139.v40.readonly-preflight.v1", source_sha=FROM_V39,
        original_head_seq=before["head_seq"], original_head_sha256=before["head_hash"],
        **state, source_transition_authorized=False, scientific_first_use=False,
        owner_mutations=0, new_dispatches=0, native_two_slot_schema=db.dual_native_schema(),
        hybrid_lane_schema_admitted=is_migrated(db), live_migration_enabled=False)


def commit_transition(db, proof, *, owner_witness):
    need(type(db) is Database and SingleOwner.held(db.filename.with_suffix(".lock"))
         and callable(owner_witness) and owner_witness() is True,
         "ORIGINAL_MUTEX_AND_DISABLED_OWNER_REQUIRED")
    need(type(proof) is dict and set(proof) == FIELDS, "EXACT_PROOF_REQUIRED")
    with db.transaction():
        expected = build_proof(db, proof["to_source_sha"], proof["owner_event_id"],
                               proof["genenv_executable_sha256"], proof["genenv_toolchain"])
        need(canonical(expected) == canonical(proof), "APPROVAL_OR_LEDGER_DRIFT")
        need(owner_witness() is True, "OWNER_REVOKED")
        db.conn.execute("UPDATE meta SET source_sha=? WHERE id=1", (proof["to_source_sha"],))
        db.event("SOURCE_TRANSITION_ADMITTED", proof)
        db.verify()
        need(owner_witness() is True and db.meta()["head_seq"] == proof["original_head_seq"]+1,
             "POST_TRANSITION_DRIFT")
    return dict(source_sha=db.meta()["source_sha"], event_seq=db.meta()["head_seq"],
                event_head_sha256=db.meta()["head_hash"], new_dispatches=0, scientific_first_use=False)
