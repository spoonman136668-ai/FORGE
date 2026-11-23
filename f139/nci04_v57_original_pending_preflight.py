"""Read-only event1857 original-owner READY witness before one V47 forward repair.

The original V46 event and activation were installed, but the next owner tick
failed before claim and rolled back. This does not authorize a worker retry,
new controller or scientific first-use. Fail closed on ANY original drift.
"""
from __future__ import annotations

import json
import re
from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_ledger import verify_native_activation
from f139.nci04_v56_forward_transition import (
    carried_v46_source, _sealed_ticket as original_ticket_identity,
)

SOURCE = "f4d0eeebe18894ce2d16f63e915f356def692e17"
ORIGINAL_SOURCE = "1e3a3b7d63d7dce13924e279cfb61f3d975bd9aa"
TICKET = "f139-nci04-i1812-1e3a3b7d63d7-cd0ee29f"
ANCHOR_SEQ = 1857
ANCHOR_SHA = "bdf0e4cdb08902ad4e562552f1617922eaa9ad7107a58035bbfc1ae886e069b3"
READY_SOURCE_TRANSITION_SEQ = 1856
READY_SOURCE_TRANSITION_SHA = "f9adc29942d6ede030c59756e5b6d4908b10faa233d73fb749877626efc35611"
NATIVE_ACTIVATION_SEQ = 1857
NATIVE_ACTIVATION_SHA = ANCHOR_SHA
ADMISSION_SEQ = 1854
ADMISSION_SHA = "e9bd52ce43767d9566708dce5415c6ebda60c9a1265d3600a98f01b2a30472b7"
INTAKE_SEQ = 1855
INTAKE_SHA = "4223174995813a74a19fb89af6591dea66d12206f0c2e91600edbdb582495344"
SCHEMA = "forge.f139.v57.original-v46-ready-carry-readonly.v1"
SHA64 = re.compile(r"[a-f0-9]{64}\Z")


class V57ReadOnlyDenied(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise V57ReadOnlyDenied("F139_V57_" + code)


def original_pending_snapshot(db: Database, *, require_mutex: bool = True):
    """Pin exact original event1857 and old-source READY identity without writes."""
    need(type(db) is Database and type(require_mutex) is bool,
         "DATABASE_IDENTITY")
    if require_mutex:
        need(SingleOwner.held(db.filename.with_suffix(".lock")),
             "EXCLUSIVE_OR_DETACHED_OWNER_MUTEX_REQUIRED")
    db.verify()
    m = db.meta()
    need(m["source_sha"] == SOURCE and m["enabled"] == 1
         and m["legacy_suspended"] == 1
         and m["head_seq"] == ANCHOR_SEQ
         and m["head_hash"] == ANCHOR_SHA,
         "SOURCE_OR_ANCHOR_DRIFT")
    need(verify_native_activation(db, expected_source=SOURCE) is True,
         "CURRENT_NATIVE_ACTIVATION_UNVERIFIED")
    anchors = {
        row["seq"]: row for row in db.conn.execute(
            "SELECT seq,kind,sha,payload FROM events "
            "WHERE seq IN (1854,1855,1856,1857) ORDER BY seq"
        )
    }
    need(set(anchors) == {1854,1855,1856,1857}
         and anchors[1854]["kind"] == "NATIVE_DEVELOPMENT_ADMITTED"
         and anchors[1854]["sha"] == ADMISSION_SHA
         and anchors[1855]["kind"] == "TASK_INTAKE"
         and anchors[1855]["sha"] == INTAKE_SHA
         and anchors[1856]["kind"] == "SOURCE_TRANSITION_ADMITTED"
         and anchors[1856]["sha"] == READY_SOURCE_TRANSITION_SHA
         and anchors[1857]["kind"] == "NATIVE_DEVELOPMENT_ACTIVATED"
         and anchors[1857]["sha"] == NATIVE_ACTIVATION_SHA,
         "EXACT_PREDECESSOR_EVENT_DRIFT")
    transition = json.loads(anchors[1856]["payload"])
    activation = json.loads(anchors[1857]["payload"])
    admission = json.loads(anchors[1854]["payload"])
    intake = json.loads(anchors[1855]["payload"])
    need(transition.get("schema") == "forge.f139.source-transition.v46"
         and transition.get("from_source_sha") == ORIGINAL_SOURCE
         and transition.get("to_source_sha") == SOURCE
         and transition.get("original_ready_ticket") == TICKET
         and transition.get("original_ready_source_sha") == ORIGINAL_SOURCE
         and transition.get("original_admission_sha256") == ADMISSION_SHA
         and transition.get("original_intake_sha256") == INTAKE_SHA
         and transition.get("scientific_first_use") is False
         and activation.get("source_sha") == SOURCE
         and activation.get("scientific_first_use") is False
         and admission.get("ticket") == TICKET
         and admission.get("source_sha") == ORIGINAL_SOURCE
         and admission.get("lane") == "Yggdrasil"
         and admission.get("scientific_first_use") is False,
         "V46_OR_NATIVE_ADMISSION_DRIFT")

    ready = list(db.conn.execute("SELECT * FROM tasks WHERE stage='READY'"))
    need(len(ready) == 1 and ready[0]["ticket"] == TICKET
         and not db.actives(), "ORIGINAL_READY_EXCLUSIVITY")
    r = ready[0]
    need(r["lane"] == "Yggdrasil"
         and r["source_sha"] == ORIGINAL_SOURCE
         and r["run_id"] is None and r["started_at"] is None
         and r["evidence_dir"] is None and r["evidence_sha"] is None
         and r["quarantine_reason"] is None
         and type(r["manifest_sha"]) is str
         and SHA64.fullmatch(r["manifest_sha"]) is not None
         and admission.get("manifest_sha256") == r["manifest_sha"]
         and intake == {"ticket": TICKET, "lane": "Yggdrasil",
                        "manifest_sha": r["manifest_sha"]},
         "ORIGINAL_READY_TASK_DRIFT")
    identity = original_ticket_identity(db)
    need(identity == transition.get("original_ready_identity_sha256")
         and carried_v46_source(db,TICKET) == ORIGINAL_SOURCE,
         "V46_CARRIED_IDENTITY_NOT_VERIFIED")
    spent = db.conn.execute(
        "SELECT COUNT(*) FROM events WHERE kind='BEFORE_DISPATCH_INTENT' "
        "AND json_extract(payload,'$.ticket')=?", (TICKET,)
    ).fetchone()[0]
    need(spent == 0, "ORIGINAL_DISPATCH_ALREADY_SPENT")
    return {
        "schema": SCHEMA,
        "source_sha": SOURCE,
        "head_seq": ANCHOR_SEQ,
        "head_sha256": ANCHOR_SHA,
        "ticket": TICKET,
        "ticket_stage": "READY",
        "ticket_run_id": None,
        "ticket_source_sha": ORIGINAL_SOURCE,
        "ticket_identity_sha256": identity,
        "source_transition_event_sha256": READY_SOURCE_TRANSITION_SHA,
        "native_activation_event_sha256": NATIVE_ACTIVATION_SHA,
        "original_admission_sha256": ADMISSION_SHA,
        "original_intake_sha256": INTAKE_SHA,
        "new_dispatches": 0,
        "scientific_first_use": False,
        "release_authorized": False,
    }
