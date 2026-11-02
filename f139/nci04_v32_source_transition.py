"""One-shot V31 -> GenEnv owner source transition, never execution authority."""
import json
import re

from f139.local_controller import Database, SingleOwner, g54_original_canonical
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_ledger import verify_native_activation

FROM_V31 = "6fe5b70ed075cbd47fbb14b721e097dd4660c851"
ORIGINAL_SEQ = 401
ORIGINAL_HEAD = "fd8f92aaed512d7fcf1b761307edb57306ebf9ad5b65a43a9627c523db832cf8"
TOOLCHAIN = "go1.23.12 windows/amd64"
SCHEMA = "forge.f139.source-transition.v27"
FIELDS = frozenset({"schema", "from_source_sha", "to_source_sha", "owner_event_id",
    "prior_event_head_sha256", "verified_historical_tasks", "custodied_negative_tasks",
    "custodied_negative_tickets", "terminal_tasks_sha256", "history_sha256",
    "v31_transition_sha256", "genenv_executable_sha256", "genenv_toolchain",
    "new_dispatches", "scientific_first_use", "v2_receipt_authorized"})


class MaintenanceDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise MaintenanceDenied("F139_V32_" + reason)


def validate_idle(db):
    db.verify()
    meta = db.meta()
    need(meta["source_sha"] == FROM_V31 and meta["head_seq"] == ORIGINAL_SEQ
         and meta["head_hash"] == ORIGINAL_HEAD and meta["enabled"] == 1
         and meta["legacy_suspended"] == 1 and db.ready() is None
         and not db.actives() and verify_native_activation(db), "EXACT_IDLE_ORIGINAL_REQUIRED")


def snapshot(db, row, previous):
    need(previous and previous[-1]["schema"] == "forge.f139.source-transition.v26"
         and previous[-1]["to_source_sha"] == FROM_V31, "GENUINE_V31_PREDECESSOR_REQUIRED")
    seal = db.conn.execute("SELECT sha,payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' "
                           "AND seq<? ORDER BY seq DESC LIMIT 1", (row["seq"],)).fetchone()
    need(seal is not None and json.loads(seal["payload"]) == previous[-1], "V31_SEAL_DRIFT")
    sources = {s for tr in previous for s in (tr["from_source_sha"], tr["to_source_sha"])}
    tasks = [dict(t) for t in db.conn.execute("SELECT ticket,stage,run_id,evidence_sha,evidence_dir,"
             "source_sha FROM tasks ORDER BY ticket") if t["source_sha"] in sources]
    need(all(t["stage"] in ("VERIFIED", "QUARANTINED") for t in tasks), "HISTORICAL_TASK_NOT_TERMINAL")
    from f139.nci04_negative_owner_store import TICKET as FIRST
    from f139.nci04_split_negative_owner_store import TICKET as SECOND
    from f139.nci04_g49_prepost_negative import TICKET as PREPOST
    failures = db.verified_native_provider_failures(through_seq=row["seq"])
    negatives = sorted({FIRST, SECOND, PREPOST,
        g54_original_canonical(db, through_seq=row["seq"])["ticket"]} | set(failures))
    positive = [t for t in tasks if t["stage"] == "VERIFIED"]
    negative = [t for t in tasks if t["stage"] == "QUARANTINED"]
    need(len(positive) == 33 and len(negative) == 18
         and sorted(t["ticket"] for t in negative) == negatives, "ORIGINAL_TERMINAL_CUSTODY_DRIFT")
    history = [dict(e) for e in db.conn.execute(
        "SELECT seq,kind,sha FROM events WHERE seq<? ORDER BY seq", (row["seq"],))]
    need(len(history) == ORIGINAL_SEQ and history[-1]["sha"] == ORIGINAL_HEAD
         and sum(e["kind"] == "FREE_REASONER_ATTEMPTED" for e in history) == 8
         and sum(e["kind"] == "MODEL_DRAFT_ATTEMPTED" for e in history) == 7
         and sum(e["kind"] == "MODEL_DRAFT_AUTHENTICATED" for e in history) == 7,
         "SPENT_HISTORY_DRIFT")
    return dict(verified_historical_tasks=33, custodied_negative_tasks=18,
                custodied_negative_tickets=negatives, terminal_tasks_sha256=digest(canonical(tasks)),
                history_sha256=digest(canonical(history)), v31_transition_sha256=seal["sha"])


def verify_cold_event(db, row, doc, previous):
    need(type(doc) is dict and set(doc) == FIELDS and doc["schema"] == SCHEMA
         and row["seq"] == ORIGINAL_SEQ+1 and row["prior_sha"] == ORIGINAL_HEAD
         and doc["prior_event_head_sha256"] == ORIGINAL_HEAD and doc["from_source_sha"] == FROM_V31
         and type(doc["owner_event_id"]) is int and doc["owner_event_id"] > 0
         and type(doc["new_dispatches"]) is int and doc["new_dispatches"] == 0
         and doc["scientific_first_use"] is False and doc["v2_receipt_authorized"] is False
         and type(doc["to_source_sha"]) is str and re.fullmatch(r"[a-f0-9]{40}", doc["to_source_sha"])
         and doc["to_source_sha"] not in {s for tr in previous
             for s in (tr["from_source_sha"], tr["to_source_sha"])}
         and not any(tr["schema"] == SCHEMA for tr in previous)
         and type(doc["genenv_executable_sha256"]) is str
         and re.fullmatch(r"[a-f0-9]{64}", doc["genenv_executable_sha256"])
         and doc["genenv_toolchain"] == TOOLCHAIN, "EVENT_IDENTITY_OR_AUTHORITY_DRIFT")
    need(all(doc[k] == v for k, v in snapshot(db, row, previous).items()), "ORIGINAL_STATE_DRIFT")


def build_proof(db, target, event_id, binary_sha, toolchain):
    need(type(db) is Database and SingleOwner.held(db.filename.with_suffix(".lock")),
         "ORIGINAL_DATABASE_MUTEX_REQUIRED")
    validate_idle(db)
    previous = [json.loads(r["payload"]) for r in db.conn.execute(
        "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")]
    row = dict(seq=ORIGINAL_SEQ+1, prior_sha=ORIGINAL_HEAD)
    doc = dict(schema=SCHEMA, from_source_sha=FROM_V31, to_source_sha=target,
        owner_event_id=event_id, prior_event_head_sha256=ORIGINAL_HEAD,
        **snapshot(db, row, previous), genenv_executable_sha256=binary_sha,
        genenv_toolchain=toolchain, new_dispatches=0, scientific_first_use=False,
        v2_receipt_authorized=False)
    verify_cold_event(db, row, doc, previous)
    return doc


def commit_transition(db, proof, *, owner_witness):
    need(type(db) is Database and SingleOwner.held(db.filename.with_suffix(".lock"))
         and callable(owner_witness) and owner_witness() is True, "ORIGINAL_MUTEX_AND_DISABLED_OWNER_REQUIRED")
    need(type(proof) is dict and set(proof) == FIELDS, "EXACT_PROOF_REQUIRED")
    with db.transaction():
        expected = build_proof(db, proof["to_source_sha"], proof["owner_event_id"],
                               proof["genenv_executable_sha256"], proof["genenv_toolchain"])
        need(canonical(expected) == canonical(proof), "APPROVAL_OR_LEDGER_DRIFT")
        need(owner_witness() is True, "OWNER_REVOKED")
        db.conn.execute("UPDATE meta SET source_sha=? WHERE id=1", (proof["to_source_sha"],))
        db.event("SOURCE_TRANSITION_ADMITTED", proof)
        db.verify()
        need(owner_witness() is True and db.meta()["head_seq"] == ORIGINAL_SEQ+1, "POST_TRANSITION_DRIFT")
    return dict(source_sha=db.meta()["source_sha"], event_seq=db.meta()["head_seq"],
                event_head_sha256=db.meta()["head_hash"], new_dispatches=0, scientific_first_use=False)
