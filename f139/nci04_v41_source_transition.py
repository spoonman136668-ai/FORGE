"""V41 cold source-transition verifier, inactive until separately approved release.

This module supplies strict event replay and proof construction ONLY. It has
no transition writer, live CLI, policy mutator, controller or dispatch route.
All original SQLite verification remains governed by Database.verify().
"""
import json
import re

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_ledger import verify_native_activation
from f139 import nci04_v40_source_transition as v40
from f139 import nci04_v41_catalog_recovery_preflight as preflight
from f139 import nci04_partial_publication_custody as partial
from f139 import nci04_ref_only_publication_custody as ref_only

SCHEMA = "forge.f139.source-transition.v36"
FROM_V40 = preflight.OWNER_SOURCE
REPAIR_MERGE = preflight.MERGED_REPAIR
MIN_HEAD = preflight.OBSERVED_SEQ
MIN_VERIFIED = 153
NEGATIVE_COUNT = 56
TOOLCHAIN = v40.TOOLCHAIN
QUALIFIED_WORKER_BLOB = v40.QUALIFIED_WORKER_BLOB
PURPOSE = "two-lane-catalog-repair-source-handoff"
HEX40 = re.compile(r"[a-f0-9]{40}\Z")
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
FIELDS = frozenset({
    "schema", "from_source_sha", "to_source_sha", "owner_event_id",
    "prior_event_head_sha256", "original_head_seq",
    "frozen_observed_seq", "frozen_observed_head_sha256",
    "verified_historical_tasks", "custodied_negative_tasks",
    "custodied_negative_tickets", "terminal_tasks_sha256",
    "history_sha256", "v40_transition_sha256", "preserved_counters",
    "negative_1239_sha256", "negative_1462_sha256",
    "genenv_executable_sha256", "genenv_toolchain",
    "generation_mechanism_sha256", "qualified_worker_blob",
    "qualifying_catalog_repair_sha", "source_lanes", "purpose",
    "new_dispatches", "scientific_first_use", "v2_receipt_authorized",
    "hybrid_admission",
})


class V41TransitionDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise V41TransitionDenied("F139_V41_" + reason)


def _terminal_tasks(db, historical_sources):
    tasks = [dict(row) for row in db.conn.execute(
        "SELECT ticket,stage,run_id,evidence_sha,evidence_dir,source_sha "
        "FROM tasks ORDER BY ticket") if row["source_sha"] in historical_sources]
    need(bool(tasks) and all(t["stage"] in ("VERIFIED", "QUARANTINED") for t in tasks),
         "ORIGINAL_TERMINAL_TASK_DRIFT")
    positive = [t for t in tasks if t["stage"] == "VERIFIED"]
    negative = [t for t in tasks if t["stage"] == "QUARANTINED"]
    need(len(positive) >= MIN_VERIFIED and len(negative) == NEGATIVE_COUNT,
         "ORIGINAL_TERMINAL_COUNTS_DRIFT")
    need(all(type(t["run_id"]) is int and t["run_id"] > 0
             and type(t["evidence_sha"]) is str and HEX64.fullmatch(t["evidence_sha"])
             and type(t["evidence_dir"]) is str and t["evidence_dir"] for t in positive)
         and all(t["run_id"] is None and t["evidence_sha"] is None
                 and not t["evidence_dir"] for t in negative),
         "ORIGINAL_POSITIVE_OR_NEGATIVE_CUSTODY_DRIFT")
    return tasks, positive, negative


def snapshot(db, row, previous):
    """Deterministic immutable prefix proof; never recursively call db.verify."""
    # This is a pure cold parser also called by the verified -m __main__
    # Database entrypoint. The canonical class identity is required only in
    # build_proof, where original-owner mutation authority is relevant.
    need(getattr(db, "conn", None) is not None
         and type(previous) is list and bool(previous)
         and type(row["seq"]) is int and row["seq"] >= MIN_HEAD + 1
         and type(row["prior_sha"]) is str and HEX64.fullmatch(row["prior_sha"]),
         "COLD_PREFIX_SHAPE")
    need(previous[-1].get("schema") == v40.SCHEMA
         and previous[-1].get("to_source_sha") == FROM_V40
         and previous[-1].get("from_source_sha") == v40.FROM_V39
         and previous[-1].get("qualified_worker_blob") == QUALIFIED_WORKER_BLOB
         and sum(t.get("schema") == v40.SCHEMA for t in previous) == 1
         and all(type(t.get("from_source_sha")) is str
                 and type(t.get("to_source_sha")) is str for t in previous),
         "UNIQUE_GENUINE_V40_PREDECESSOR")
    prior_seals = db.conn.execute(
        "SELECT seq,sha,payload FROM events "
        "WHERE kind='SOURCE_TRANSITION_ADMITTED' AND seq<? ORDER BY seq",
        (row["seq"],)).fetchall()
    selected = [t for t in prior_seals if json.loads(t["payload"]).get("schema") == v40.SCHEMA]
    need(len(selected) == 1 and
         json.loads(selected[0]["payload"]) == previous[-1]
         and HEX64.fullmatch(selected[0]["sha"])
         and selected[0]["seq"] > ref_only.SEQ,
         "COLD_V40_SEAL_DRIFT")
    observed = db.conn.execute(
        "SELECT sha FROM events WHERE seq=?", (MIN_HEAD,)).fetchone()
    need(observed is not None and observed["sha"] == preflight.OBSERVED_HEAD,
         "FROZEN_OWNER_HEAD_DRIFT")
    history = [dict(t) for t in db.conn.execute(
        "SELECT seq,kind,sha FROM events WHERE seq<? ORDER BY seq", (row["seq"],))]
    need(len(history) == row["seq"] - 1
         and all(t["seq"] == i + 1 for i, t in enumerate(history))
         and history[-1]["sha"] == row["prior_sha"],
         "ORIGINAL_PREFIX_LENGTH_OR_SHA_DRIFT")

    prior_sources = {s for t in previous
                     for s in (t["from_source_sha"], t["to_source_sha"])}
    tasks, positive, negative = _terminal_tasks(db, prior_sources)

    # Frozen negative prefixes must remain exactly consumed: no replay.
    need(partial.validate_original(db, partial.SEQ + 1) == partial.custody_packet()
         and ref_only.validate_original(db, ref_only.SEQ + 1) == ref_only.custody_packet(),
         "FROZEN_NEGATIVE_PREFIX_DRIFT")
    attempts, successes = partial._publication_prefix(db, row["seq"])
    need(len(attempts) >= 168 and len(successes) >= 166
         and set(attempts) - set(successes) == {partial.IDENTITY, ref_only.IDENTITY},
         "AUTHENTICATED_POST_V40_GROWTH_DRIFT")
    for event in db.conn.execute(
            "SELECT payload FROM events WHERE kind='MODEL_DRAFT_ATTEMPTED' "
            "AND seq>? AND seq<? ORDER BY seq", (selected[0]["seq"], row["seq"])):
        doc = json.loads(event["payload"])
        need(doc.get("source_sha") == FROM_V40,
             "POST_V40_MODEL_SOURCE_DRIFT")
    counters = {kind: db.conn.execute(
        "SELECT COUNT(*) AS n FROM events WHERE kind=? AND seq<?",
        (kind, row["seq"])).fetchone()["n"] for kind in (
        "G3_DRAFT_ATTEMPTED", "G3_DRAFT_AUTHENTICATED",
        "MODEL_DRAFT_ATTEMPTED", "MODEL_DRAFT_AUTHENTICATED",
        "FREE_REASONER_ATTEMPTED")}
    need(counters["G3_DRAFT_ATTEMPTED"] == counters["G3_DRAFT_AUTHENTICATED"] == 1
         and counters["FREE_REASONER_ATTEMPTED"] == 8
         and counters["MODEL_DRAFT_ATTEMPTED"] == len(attempts)
         and counters["MODEL_DRAFT_AUTHENTICATED"] == len(successes),
         "ORIGINAL_SPENT_COUNTER_DRIFT")
    return dict(
        frozen_observed_seq=MIN_HEAD,
        frozen_observed_head_sha256=preflight.OBSERVED_HEAD,
        verified_historical_tasks=len(positive),
        custodied_negative_tasks=len(negative),
        custodied_negative_tickets=sorted(t["ticket"] for t in negative),
        terminal_tasks_sha256=digest(canonical(tasks)),
        history_sha256=digest(canonical(history)),
        v40_transition_sha256=selected[0]["sha"],
        preserved_counters=counters,
        negative_1239_sha256=partial.EVENT,
        negative_1462_sha256=ref_only.EVENT)


def verify_cold_event(db, row, doc, previous):
    """Source-transition v36 is an exact, one-time original-owner cold event."""
    need(type(doc) is dict and set(doc) == FIELDS and doc.get("schema") == SCHEMA
         and doc.get("from_source_sha") == FROM_V40
         and type(doc.get("to_source_sha")) is str
         and HEX40.fullmatch(doc["to_source_sha"])
         and doc["to_source_sha"] != FROM_V40
         and type(doc.get("original_head_seq")) is int
         and doc["original_head_seq"] >= MIN_HEAD
         and row["seq"] == doc["original_head_seq"] + 1
         and doc.get("prior_event_head_sha256") == row["prior_sha"]
         and type(doc.get("owner_event_id")) is int and doc["owner_event_id"] > 0
         and doc.get("qualifying_catalog_repair_sha") == REPAIR_MERGE
         and doc.get("qualified_worker_blob") == QUALIFIED_WORKER_BLOB
         and doc.get("source_lanes") == ["Wingless", "Yggdrasil"]
         and doc.get("purpose") == PURPOSE
         and doc.get("genenv_toolchain") == TOOLCHAIN
         and type(doc.get("genenv_executable_sha256")) is str
         and HEX64.fullmatch(doc["genenv_executable_sha256"])
         and type(doc.get("generation_mechanism_sha256")) is str
         and HEX64.fullmatch(doc["generation_mechanism_sha256"])
         and type(doc.get("new_dispatches")) is int
         and doc["new_dispatches"] == 0
         and doc.get("scientific_first_use") is False
         and doc.get("v2_receipt_authorized") is False
         and doc.get("hybrid_admission") is False
         and not any(t.get("schema") == SCHEMA for t in previous),
         "EVENT_IDENTITY_OR_AUTHORITY_DRIFT")
    state = snapshot(db, row, previous)
    need(all(doc.get(k) == v for k, v in state.items()),
         "COLD_ORIGINAL_HISTORY_DRIFT")


def build_proof(db, target, event_id, binary_sha, toolchain):
    """Construction only. Does not append events or modify original sources."""
    need(type(db) is Database and
         SingleOwner.held(db.filename.with_suffix(".lock")),
         "ORIGINAL_MUTEX_REQUIRED")
    db.verify()
    meta = db.meta()
    need(meta["source_sha"] == FROM_V40 and meta["enabled"] == 1
         and meta["legacy_suspended"] == 1
         and meta["head_seq"] >= MIN_HEAD
         and db.ready() is None and not db.actives()
         and verify_native_activation(db),
         "ORIGINAL_IDLE_OWNER_REQUIRED")
    need(type(target) is str and HEX40.fullmatch(target) and target != FROM_V40
         and type(event_id) is int and event_id > 0
         and type(binary_sha) is str and HEX64.fullmatch(binary_sha)
         and toolchain == TOOLCHAIN,
         "CANDIDATE_SOURCE_BINARY_OR_TOOLCHAIN_DRIFT")
    previous = [json.loads(t["payload"]) for t in db.conn.execute(
        "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")]
    row = dict(seq=meta["head_seq"] + 1, prior_sha=meta["head_hash"])
    from f139.nci04_genenv_owner_backend import generation_mechanism
    doc = dict(schema=SCHEMA, from_source_sha=FROM_V40,
               to_source_sha=target, owner_event_id=event_id,
               prior_event_head_sha256=meta["head_hash"],
               original_head_seq=meta["head_seq"],
               **snapshot(db, row, previous),
               genenv_executable_sha256=binary_sha,
               genenv_toolchain=toolchain,
               generation_mechanism_sha256=digest(generation_mechanism()),
               qualified_worker_blob=QUALIFIED_WORKER_BLOB,
               qualifying_catalog_repair_sha=REPAIR_MERGE,
               source_lanes=["Wingless", "Yggdrasil"], purpose=PURPOSE,
               new_dispatches=0, scientific_first_use=False,
               v2_receipt_authorized=False, hybrid_admission=False)
    verify_cold_event(db, row, doc, previous)
    return doc
