"""Exact original Windows F139 V57->V59 idle-owner read-only cold preflight.

This is a negative/continuity *readiness witness*, NOT an installer or
source-transition proof. Never infer source promotion, remote-write retry,
scientific first-use or task authority from a passing report.

Every value is anchored to the authenticated 2026-11-19 original-host
F139-G54 V9 read-only status, GitHub run 44518016720, job 135539001286.
No historical source or ledger field is backfilled or reset.
"""
from __future__ import annotations

import json

from f139.local_controller import Database
from f139.nci04_owner_ledger import verify_native_activation
from f139.nci04_partial_publication_custody import custodied_ids

SOURCE = "c06403c8b6035c6c7013866a7ea08cef1244b507"
HEAD_SEQ = 1864
HEAD_SHA256 = "e10be7151e19f2104ef2659ae04bef89b2711eea1659decb1477fd7354ff24ec"
TRANSITION_SEQ = 1858
TRANSITION_SHA256 = "dd2b4d86d55e7dce44f82124df60aa2840f2470566d4bb639747db5d6ad2cfc0"
ACTIVATION_SEQ = 1859
ACTIVATION_SHA256 = "1fc1740a1fa2f931f92e9c3bad63f552c049a89e9e200361e61a5a47177a9009"
ATTEMPTS = 169
AUTHENTICATED = 167
HISTORICAL_NEGATIVES = 56
MIN_VERIFIED = 155
PREDECESSOR_SCHEMA = "forge.f139.source-transition.v47"


class FrozenOwnerReadinessDenied(ValueError):
    """A source-anchored read-only refusal, not an execution instruction."""


def require(ok: bool, code: str) -> None:
    if not ok:
        raise FrozenOwnerReadinessDenied("F139_V59_" + code)


def audit_frozen_original_readonly(db: Database) -> dict:
    """Audit the *same* original SQLite on a read-only connection.

    A passing result proves a cold preimage only. It never permits stopping,
    retargeting, launching, replaying, or writing the original owner task.
    """
    require(type(db) is Database and
            getattr(db, "_readonly_opened", False) is True,
            "ORIGINAL_READONLY_DATABASE_REQUIRED")
    require(db.conn.execute("PRAGMA query_only").fetchone()[0] == 1,
            "SQLITE_QUERY_ONLY_REQUIRED")
    db.verify()  # Full existing source/event/negative-provider replay checks.
    before_changes = db.conn.total_changes
    meta = db.meta()
    require(meta["source_sha"] == SOURCE and
            meta["head_seq"] == HEAD_SEQ and
            meta["head_hash"] == HEAD_SHA256 and
            meta["enabled"] == 1 and meta["legacy_suspended"] == 1,
            "EXACT_OWNER_SOURCE_OR_HEAD_DRIFT")
    require(verify_native_activation(db, expected_source=SOURCE) is True,
            "NATIVE_DEVELOPMENT_ACTIVATION_UNVERIFIED")
    require(db.ready() is None and not db.actives(),
            "ORIGINAL_TASK_NOT_IDLE")
    anchors = {row["seq"]: row for row in db.conn.execute(
        "SELECT seq,kind,sha,payload FROM events WHERE seq IN (?,?,?)",
        (TRANSITION_SEQ, ACTIVATION_SEQ, HEAD_SEQ))}
    require(set(anchors) == {TRANSITION_SEQ, ACTIVATION_SEQ, HEAD_SEQ} and
            anchors[TRANSITION_SEQ]["kind"] == "SOURCE_TRANSITION_ADMITTED" and
            anchors[TRANSITION_SEQ]["sha"] == TRANSITION_SHA256 and
            anchors[ACTIVATION_SEQ]["kind"] == "NATIVE_DEVELOPMENT_ACTIVATED" and
            anchors[ACTIVATION_SEQ]["sha"] == ACTIVATION_SHA256 and
            anchors[HEAD_SEQ]["sha"] == HEAD_SHA256,
            "IMMUTABLE_V47_OR_ORIGINAL_HEAD_DRIFT")
    transition = json.loads(anchors[TRANSITION_SEQ]["payload"])
    activation = json.loads(anchors[ACTIVATION_SEQ]["payload"])
    require(transition.get("schema") == PREDECESSOR_SCHEMA and
            transition.get("to_source_sha") == SOURCE and
            transition.get("scientific_first_use") is False and
            activation.get("source_sha") == SOURCE and
            activation.get("scientific_first_use") is False,
            "V47_SOURCE_OR_ACTIVATION_DRIFT")
    last = db.conn.execute(
        "SELECT seq,sha FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' "
        "ORDER BY seq DESC LIMIT 1").fetchone()
    require(last is not None and last["seq"] == TRANSITION_SEQ and
            last["sha"] == TRANSITION_SHA256,
            "UNREVIEWED_SOURCE_TRANSITION_PRESENT")
    stages = {row["stage"]: row["n"] for row in db.conn.execute(
        "SELECT stage,COUNT(*) AS n FROM tasks GROUP BY stage")}
    require(set(stages).issubset({"VERIFIED", "QUARANTINED"}) and
            stages.get("VERIFIED", 0) >= MIN_VERIFIED and
            stages.get("QUARANTINED", 0) >= HISTORICAL_NEGATIVES,
            "NONTERMINAL_OR_HISTORICAL_TASK_DRIFT")
    counts = {row["kind"]: row["n"] for row in db.conn.execute(
        "SELECT kind,COUNT(*) AS n FROM events WHERE kind IN (?,?) GROUP BY kind",
        ("MODEL_DRAFT_ATTEMPTED", "MODEL_DRAFT_AUTHENTICATED"))}
    attempts = counts.get("MODEL_DRAFT_ATTEMPTED", 0)
    authenticated = counts.get("MODEL_DRAFT_AUTHENTICATED", 0)
    # Unknown-effect writes stay irrevocably consumed. Never infer a free
    # budget, an execution permit or safe replay from an idle controller.
    consumed_negatives = custodied_ids(db)
    require(attempts == ATTEMPTS and authenticated == AUTHENTICATED and
            len(consumed_negatives) == attempts - authenticated and
            len(consumed_negatives) == 2,
            "MODEL_DRAFT_AND_NEGATIVE_CUSTODY_DRIFT")
    require(db.conn.total_changes == before_changes and
            db.conn.execute("PRAGMA query_only").fetchone()[0] == 1,
            "READONLY_AUDIT_MUTATED_DATABASE")
    return {
        "schema": "forge.f139.v59.original-forward-cold-readiness.v1",
        "source_sha": SOURCE, "head_seq": HEAD_SEQ,
        "head_sha256": HEAD_SHA256, "verified_tasks": stages["VERIFIED"],
        "quarantined_tasks": stages["QUARANTINED"],
        "model_draft_attempts": attempts,
        "model_draft_authenticated": authenticated,
        "negative_publication_custodies": len(consumed_negatives),
        "owner_mutations": 0, "source_transition_authorized": False,
        "scientific_first_use": False, "worker_dispatched": False,
        "controller_created": False, "new_scheduler": False,
        "replay_authorized": False,
    }
