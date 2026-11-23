"""Read-only V56 admission fence for the single V55 original-owner READY ticket.

This is NOT a release, worker retry, source transition, dispatch, or approval.
An eventual V46 transition may consume this *source-authenticated* snapshot,
but only after independent original-owner release custody and detached tests.
The ticket retains its original source, immutable native issue and manifest.
"""
from __future__ import annotations

import json
import re

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_ledger import verify_native_activation

SOURCE = "1e3a3b7d63d7dce13924e279cfb61f3d975bd9aa"
TICKET = "f139-nci04-i1812-1e3a3b7d63d7-cd0ee29f"
READY_SOURCE_TRANSITION_SEQ = 1850
READY_SOURCE_TRANSITION_SHA = "c341abf1cbb57ee7c3f05e43ebb8e1ee011423e75e852440bb9f80e53e52ae54"
NATIVE_ACTIVATION_SEQ = 1851
NATIVE_ACTIVATION_SHA = "36dc059bbc8e9e14b13d8f328c926575405bc60348e84bd2c7c7157875614f37"
ADMISSION_SEQ = 1854
ADMISSION_SHA = "e9bd52ce43767d9566708dce5415c6ebda60c9a1265d3600a98f01b2a30472b7"
ANCHOR_SEQ = 1855
ANCHOR_SHA = "4223174995813a74a19fb89af6591dea66d12206f0c2e91600edbdb582495344"

SCHEMA = "forge.f139.v56.original-ready-carry-readonly.v1"
SHA64 = re.compile(r"[a-f0-9]{64}\Z")


class V56ReadOnlyDenied(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise V56ReadOnlyDenied("F139_V56_" + code)


def original_pending_snapshot(db: Database, *, require_mutex: bool = True) -> dict:
    """Attest the exact *unclaimed* original ticket. No state mutation.

    The caller must already own the original controller mutex, or work on a
    separately authenticated detached copy. Any later owner tick changing the
    anchor or ticket state invalidates this snapshot rather than permitting a
    stale launch or an ambiguous-effect replay.
    """
    need(type(db) is Database and type(require_mutex) is bool,
         "DATABASE_IDENTITY")
    if require_mutex:
        need(SingleOwner.held(db.filename.with_suffix(".lock")),
             "EXCLUSIVE_OWNER_OR_DETACHED_MUTEX_REQUIRED")
    db.verify()
    m = db.meta()
    need(m["source_sha"] == SOURCE and m["enabled"] == 1
         and m["legacy_suspended"] == 1
         and m["head_seq"] == ANCHOR_SEQ
         and m["head_hash"] == ANCHOR_SHA,
         "SOURCE_OR_LEDGER_HEAD_DRIFT")
    need(verify_native_activation(db, expected_source=SOURCE) is True,
         "NATIVE_ACTIVATION_NOT_VERIFIED")

    anchors = {
        row["seq"]: row for row in db.conn.execute(
            "SELECT seq,kind,sha,payload FROM events "
            "WHERE seq IN (1850,1851,1854,1855) ORDER BY seq"
        )
    }
    need(set(anchors) == {1850,1851,1854,1855}
         and anchors[READY_SOURCE_TRANSITION_SEQ]["kind"]
             == "SOURCE_TRANSITION_ADMITTED"
         and anchors[READY_SOURCE_TRANSITION_SEQ]["sha"]
             == READY_SOURCE_TRANSITION_SHA
         and anchors[NATIVE_ACTIVATION_SEQ]["kind"]
             == "NATIVE_DEVELOPMENT_ACTIVATED"
         and anchors[NATIVE_ACTIVATION_SEQ]["sha"] == NATIVE_ACTIVATION_SHA
         and anchors[ADMISSION_SEQ]["kind"] == "NATIVE_DEVELOPMENT_ADMITTED"
         and anchors[ADMISSION_SEQ]["sha"] == ADMISSION_SHA
         and anchors[ANCHOR_SEQ]["kind"] == "TASK_INTAKE"
         and anchors[ANCHOR_SEQ]["sha"] == ANCHOR_SHA,
         "ORIGINAL_EVENT_ANCHOR_DRIFT")

    transition = json.loads(anchors[READY_SOURCE_TRANSITION_SEQ]["payload"])
    activation = json.loads(anchors[NATIVE_ACTIVATION_SEQ]["payload"])
    admission = json.loads(anchors[ADMISSION_SEQ]["payload"])
    intake = json.loads(anchors[ANCHOR_SEQ]["payload"])
    need(transition.get("schema") == "forge.f139.source-transition.v45"
         and transition.get("to_source_sha") == SOURCE
         and activation.get("source_sha") == SOURCE
         and activation.get("scientific_first_use") is False
         and admission.get("ticket") == TICKET
         and admission.get("lane") == "Yggdrasil"
         and admission.get("source_sha") == SOURCE
         and admission.get("scientific_first_use") is False,
         "ORIGINAL_NATIVE_CUSTODY_DRIFT")

    ready = list(db.conn.execute("SELECT * FROM tasks WHERE stage='READY'"))
    need(len(ready) == 1 and ready[0]["ticket"] == TICKET
         and not db.actives(), "READY_EXCLUSIVITY_OR_DISPATCH_RISK")
    r = ready[0]
    need(r["lane"] == "Yggdrasil" and r["source_sha"] == SOURCE
         and r["stage"] == "READY"
         and type(r["manifest_sha"]) is str
         and SHA64.fullmatch(r["manifest_sha"]) is not None
         and r["run_id"] is None and r["started_at"] is None
         and r["evidence_dir"] is None and r["evidence_sha"] is None
         and r["quarantine_reason"] is None
         and admission.get("manifest_sha256") == r["manifest_sha"]
         and intake == {"ticket": TICKET, "lane": r["lane"],
                        "manifest_sha": r["manifest_sha"]},
         "READY_TASK_OR_ADMISSION_DRIFT")
    rows = db.conn.execute(
        "SELECT COUNT(*) FROM events "
        "WHERE kind='BEFORE_DISPATCH_INTENT' AND "
        "json_extract(payload,'$.ticket')=?", (TICKET,)
    ).fetchone()
    need(rows is not None and rows[0] == 0, "DISPATCH_ALREADY_SPENT")
    identity = {
        "ticket": TICKET, "lane": r["lane"], "source_sha": r["source_sha"],
        "manifest_sha": r["manifest_sha"]
    }
    return {
        "schema": SCHEMA,
        "source_sha": SOURCE,
        "head_seq": ANCHOR_SEQ,
        "head_sha256": ANCHOR_SHA,
        "admission_event_sha256": ADMISSION_SHA,
        "intake_event_sha256": ANCHOR_SHA,
        "native_activation_event_sha256": NATIVE_ACTIVATION_SHA,
        "source_transition_event_sha256": READY_SOURCE_TRANSITION_SHA,
        "ticket": TICKET,
        "ticket_identity_sha256": digest(canonical(identity)),
        "ticket_source_sha": SOURCE,
        "ticket_stage": "READY",
        "ticket_run_id": None,
        "new_dispatches": 0,
        "scientific_first_use": False,
        "new_controller": False,
        "new_scheduler": False,
        "new_queue": False,
        "paid_api_calls": 0,
        "release_authorized": False,
    }
