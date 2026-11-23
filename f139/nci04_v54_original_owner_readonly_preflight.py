"""V54: read-only, event-1847-anchored original F139 owner preflight.

Advisory only. No source transition, new task, schedule, GitHub mutation,
owner ledger write, scientific first-use, or owner release authorization.
The eventual original-owner release must separately qualify main, backup,
task identity and fresh in-mutex precommit state.
"""
from __future__ import annotations

from collections import Counter
import json
import re

from f139.local_controller import Database, canonical, hash_bytes
from f139.nci04_owner_ledger import verify_native_activation
from f139.nci04_partial_publication_custody import custodied_ids

SOURCE = "2d6ca3ea8852f6c70ee0981da3f222d0b982c279"
ANCHOR_SEQ = 1847
ANCHOR_SHA = "d80f375d450495d5897e2510c6fac0d07309f4ef4986690e77fdfedb79ffe2dd"
PREVIOUS_SCHEMA = "forge.f139.source-transition.v43"
SCHEMA = "forge.f139.v54.readonly-owner-preflight.v1"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")


class ReadonlyPreflightDenied(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise ReadonlyPreflightDenied("F139_V54_" + code)


def inspect_owner(db: Database, *, proposed_source: str) -> dict:
    """Authenticate an idle, consistent, read-only snapshot without a writer.

    Only a genuine Database.open_readonly() instance is eligible. Later normal
    owner events are allowed if Database.verify authenticates the complete
    chain; immutable 1847 must still be an exact historical ancestor.
    This receipt is NEVER execution authority.
    """
    need(type(db) is Database
         and getattr(db, "_readonly_opened", False) is True,
         "ORIGINAL_READONLY_DATABASE_REQUIRED")
    conn = db.conn
    need(conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and not conn.in_transaction, "READONLY_TRANSACTION_REQUIRED")
    need(type(proposed_source) is str
         and SHA40.fullmatch(proposed_source) is not None
         and proposed_source != SOURCE, "NEW_SOURCE_IDENTITY_REQUIRED")
    conn.execute("BEGIN")
    try:
        db.verify()
        m = db.meta()
        need(m["source_sha"] == SOURCE and m["enabled"] == 1
             and m["legacy_suspended"] == 1
             and type(m["head_seq"]) is int and m["head_seq"] >= ANCHOR_SEQ,
             "ORIGINAL_OWNER_SOURCE_OR_STATE_DRIFT")
        anchor = conn.execute(
            "SELECT seq,kind,sha FROM events WHERE seq=?", (ANCHOR_SEQ,)
        ).fetchone()
        need(anchor is not None and anchor["seq"] == ANCHOR_SEQ
             and anchor["kind"] == "PROVIDER_VERIFIED_TERMINAL"
             and anchor["sha"] == ANCHOR_SHA,
             "EVENT1847_AUTHENTIC_ANCESTOR_MISSING")
        originals = [
            json.loads(row["payload"]) for row in conn.execute(
                "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED'"
                " ORDER BY seq")]
        last = conn.execute(
            "SELECT seq,sha,payload FROM events "
            "WHERE kind='SOURCE_TRANSITION_ADMITTED' "
            "ORDER BY seq DESC LIMIT 1").fetchone()
        need(last is not None and last["seq"] < ANCHOR_SEQ
             and originals and originals[-1] == json.loads(last["payload"])
             and originals[-1].get("schema") == PREVIOUS_SCHEMA
             and originals[-1].get("to_source_sha") == SOURCE
             and proposed_source not in {
                 x.get(key) for x in originals
                 for key in ("from_source_sha", "to_source_sha")},
             "V43_SOURCE_LINEAGE_OR_TARGET_DRIFT")
        need(verify_native_activation(db) is True,
             "ORIGINAL_NATIVE_ACTIVATION_MISSING")
        tasks = [dict(row) for row in conn.execute(
            "SELECT ticket,lane,source_sha,stage,manifest_sha,run_id,"
            "evidence_dir,evidence_sha,quarantine_reason "
            "FROM tasks ORDER BY ticket")]
        counts = Counter(row["stage"] for row in tasks)
        need(bool(tasks) and set(counts).issubset({"VERIFIED", "QUARANTINED"})
             and db.ready() is None and not db.actives(),
             "ACTIVE_READY_OR_UNSEALED_TASK")
        attempts = conn.execute(
            "SELECT COUNT(*) FROM events WHERE kind='MODEL_DRAFT_ATTEMPTED'"
        ).fetchone()[0]
        successes = conn.execute(
            "SELECT COUNT(*) FROM events WHERE kind='MODEL_DRAFT_AUTHENTICATED'"
        ).fetchone()[0]
        negatives = custodied_ids(db)
        need(type(negatives) is frozenset
             and all(type(x) is str and SHA64.fullmatch(x) is not None
                     for x in negatives)
             and successes <= attempts
             and attempts == successes + len(negatives),
             "AMBIGUOUS_MODEL_PUBLICATION_NO_REPLAY")
        after = db.meta()
        need(all(after[key] == m[key]
                 for key in ("source_sha", "head_seq", "head_hash")),
             "OWNER_READ_SNAPSHOT_MOVED")
        return {
            "schema": SCHEMA, "advisory_only": True,
            "release_authorized": False, "owner_mutations": 0,
            "worker_dispatches": 0, "scientific_first_use": False,
            "existing_source_sha": SOURCE, "proposed_source_sha": proposed_source,
            "verified_ancestor_seq": ANCHOR_SEQ,
            "verified_ancestor_sha256": ANCHOR_SHA,
            "observed_event_head_seq": m["head_seq"],
            "observed_event_head_sha256": m["head_hash"],
            "latest_transition_sha256": last["sha"],
            "terminal_task_count": len(tasks),
            "verified_task_count": counts["VERIFIED"],
            "quarantined_task_count": counts["QUARANTINED"],
            "terminal_task_rows_sha256": hash_bytes(canonical(tasks)),
            "model_publications_authenticated": successes,
            "model_publications_custodied_negative": len(negatives),
        }
    finally:
        conn.execute("ROLLBACK")
