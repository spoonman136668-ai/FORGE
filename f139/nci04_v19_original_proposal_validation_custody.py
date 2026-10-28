"""V19 original-owner proposed-source validation custody; NO publication.

A returned free-model response is untrusted input. Only the independently
validated single-file *candidate identity* and bounded experimental question,
hypothesis and control are sealed in the existing original SQLite SHA chain.
No transport, GitHub writer, F139 tick, training, merge or science authority.
"""
from __future__ import annotations

import hashlib
import json
from typing import Callable

from f139.local_controller import Database, SingleOwner, canonical
from f139.nci04_autonomy_feed import candidate_identity
from f139.nci04_model_proposal import validate as validate_untrusted_proposal
from f139.nci04_v19_original_one_shot_free_send import (
    KIND as SEND_KIND, SCHEMA as SEND_SCHEMA,
)
from f139.nci04_v19_original_one_post_handoff import (
    KIND as HANDOFF_KIND, SCHEMA as HANDOFF_SCHEMA,
)
from f139.nci04_free_reasoner_provider import (
    MODEL, make_body,
)
from f139.nci04_v19_research_renewal_shadow import (
    ShadowDenied, is_sha40, is_sha64,
)

KIND = "NATIVE_RENEWAL_PROPOSAL_VALIDATED"
SCHEMA = "forge.f139.v19.original-proposal-validation.v1"
FIELDS = frozenset({
    "schema", "owner_source_sha", "send_seq", "send_sha256",
    "terminal_ticket", "lane", "scope_sha256", "target_commit",
    "native_path", "public_packet_sha256", "request_body_sha256",
    "history_sha256", "source_before_sha256", "source_after_sha256",
    "candidate_identity", "proposal_sha256", "validation_record_sha256",
    "question", "hypothesis", "control", "prior_event_head_sha256",
    "publication_authorized", "worker_dispatched", "paid_model_calls",
    "scientific_first_use",
})


def deny(reason: str) -> None:
    raise ShadowDenied("F139_V19_PROPOSAL_CUSTODY_" + reason)


def _packet_sha256(packet: dict) -> str:
    return hashlib.sha256(json.dumps(
        packet, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()


def _record(doc: dict) -> dict:
    return {
        "schema": "forge.f139.model-proposal.v1",
        "lane": doc["lane"], "target_commit": doc["target_commit"],
        "path": doc["native_path"], "history_sha256": doc["history_sha256"],
        "before_sha256": doc["source_before_sha256"],
        "after_sha256": doc["source_after_sha256"],
        "candidate_identity": doc["candidate_identity"],
        "question": doc["question"], "hypothesis": doc["hypothesis"],
        "control": doc["control"], "scientific_first_use": False,
        "publication_authorized": False,
    }


def audit_original_validated_proposals(db: Database) -> None:
    """Cold-verify exact data-only candidate ancestry from original chain."""
    events = list(db.conn.execute(
        "SELECT seq,kind,payload,prior_sha,sha FROM events ORDER BY seq"))
    if not any(e["kind"] == KIND for e in events):
        return
    handoffs, sends, seen_send, seen_identity, seen_after = {}, {}, set(), set(), set()
    for row in events:
        kind = row["kind"]
        if kind == HANDOFF_KIND:
            h = json.loads(row["payload"])
            if h.get("schema") != HANDOFF_SCHEMA:
                deny("HANDOFF_SCHEMA")
            handoffs[row["seq"]] = (row, h)
        elif kind == SEND_KIND:
            s = json.loads(row["payload"])
            if s.get("schema") != SEND_SCHEMA:
                deny("SEND_SCHEMA")
            sends[row["seq"]] = (row, s)
        if kind != KIND:
            continue
        doc = json.loads(row["payload"])
        if (type(doc) is not dict or set(doc) != FIELDS
                or doc["schema"] != SCHEMA
                or not is_sha40(doc["owner_source_sha"])
                or type(doc["send_seq"]) is not int or doc["send_seq"] < 1
                or not is_sha64(doc["send_sha256"])
                or type(doc["terminal_ticket"]) is not str
                or doc["lane"] not in ("Wingless", "Yggdrasil")
                or not is_sha64(doc["scope_sha256"])
                or not is_sha40(doc["target_commit"])
                or type(doc["native_path"]) is not str
                or not all(is_sha64(doc[k]) for k in (
                    "public_packet_sha256", "request_body_sha256",
                    "history_sha256", "source_before_sha256",
                    "source_after_sha256", "candidate_identity",
                    "proposal_sha256", "validation_record_sha256"))
                or any(type(doc[k]) is not str
                       or not 1 <= len(doc[k]) <= 600
                       or any(ord(ch) < 32 for ch in doc[k])
                       for k in ("question", "hypothesis", "control"))
                or doc["source_before_sha256"] == doc["source_after_sha256"]
                or doc["prior_event_head_sha256"] != row["prior_sha"]
                or doc["publication_authorized"] is not False
                or doc["worker_dispatched"] is not False
                or type(doc["paid_model_calls"]) is not int
                or doc["paid_model_calls"] != 0
                or doc["scientific_first_use"] is not False):
            deny("VALIDATED_FIELDS_OR_AUTHORITY")
        send = sends.get(doc["send_seq"])
        if send is None or doc["send_seq"] in seen_send:
            deny("SEND_MISSING_OR_REPLAYED")
        s_row, s_doc = send
        handoff = handoffs.get(s_doc["handoff_seq"])
        if handoff is None:
            deny("PUBLIC_HANDOFF_MISSING")
        _, h_doc = handoff
        if (s_row["seq"] + 1 != row["seq"]
                or s_row["sha"] != row["prior_sha"]
                or s_row["sha"] != doc["send_sha256"]
                or s_doc["owner_source_sha"] != doc["owner_source_sha"]
                or s_doc["terminal_ticket"] != doc["terminal_ticket"]
                or s_doc["lane"] != doc["lane"]
                or s_doc["scope_sha256"] != doc["scope_sha256"]
                or h_doc["target_commit"] != doc["target_commit"]
                or h_doc["native_path"] != doc["native_path"]
                or s_doc["request_body_sha256"] != doc["request_body_sha256"]
                or s_doc["public_packet_sha256"] != doc["public_packet_sha256"]
                or h_doc["public_source_sha256"] != doc["source_before_sha256"]
                or h_doc["public_history_sha256"] != doc["history_sha256"]
                or candidate_identity(doc["lane"], doc["target_commit"],
                                      doc["native_path"],
                                      doc["source_after_sha256"])
                   != doc["candidate_identity"]
                or hashlib.sha256(canonical(_record(doc))).hexdigest()
                   != doc["validation_record_sha256"]
                or doc["candidate_identity"] in seen_identity
                or doc["source_after_sha256"] in seen_after):
            deny("ORIGINAL_SEND_BINDING_OR_CANDIDATE_REPLAY")
        seen_send.add(doc["send_seq"])
        seen_identity.add(doc["candidate_identity"])
        seen_after.add(doc["source_after_sha256"])


def result(disposition: str, *, seq: int | None = None,
           sha: str | None = None, candidate: dict | None = None) -> dict:
    return {
        "schema": SCHEMA, "disposition": disposition,
        "validation_event_seq": seq, "validation_event_sha256": sha,
        "candidate": candidate, "publication_authorized": False,
        "worker_dispatched": False, "scientific_first_use": False,
        "paid_model_calls": 0, "provider_requests": 0,
        "accepted_ref_mutations": 0,
    }


def validate_original_response_without_publication(
    db: Database, *, send_receipt: dict, public_packet: dict,
    owner_witness: Callable[[], bool],
    fault_after_append: bool = False,
) -> dict:
    """Seal one model proposal on ORIGINAL SQLite after independent checks.

    Caller presents the untrusted in-memory result of the *single* V19
    owner send. No response can reissue a POST or authorize a GitHub write.
    """
    if (type(db) is not Database or not SingleOwner.held(
            db.filename.with_suffix(".lock"))
            or not callable(owner_witness) or owner_witness() is not True):
        deny("ORIGINAL_OWNER_MUTEX_AND_WITNESS")
    if (type(send_receipt) is not dict
            or send_receipt.get("disposition") !=
                "ONE_MODEL_RESPONSE_UNTRUSTED_NO_PUBLICATION"
            or send_receipt.get("provider_calls_in_this_invocation") != 1
            or send_receipt.get("provider_attempt_history_spent") is not True
            or send_receipt.get("publication_authorized") is not False
            or send_receipt.get("scientific_first_use") is not False
            or send_receipt.get("paid_model_calls") != 0
            or type(send_receipt.get("send_attempt_event_seq")) is not int
            or not is_sha64(send_receipt.get("send_attempt_event_sha256"))
            or type(public_packet) is not dict
            or type(fault_after_append) is not bool):
        deny("UNTRUSTED_OR_MISSING_SEND_RECEIPT")
    response = send_receipt.get("untrusted_response")
    if (type(response) is not dict
            or response.get("schema") !=
                "forge.f139.free-model-untrusted-response.v1"
            or response.get("model_requested") != MODEL
            or response.get("remote_response_trusted") is not False
            or response.get("publication_authorized") is not False
            or response.get("scientific_first_use") is not False
            or type(response.get("paid_model_calls")) is not int
            or response["paid_model_calls"] != 0
            or type(response.get("proposal_bytes")) is not bytes
            or not is_sha64(response.get("proposal_sha256"))
            or hashlib.sha256(response["proposal_bytes"]).hexdigest() !=
                response["proposal_sha256"]):
        deny("MODEL_REPLY_AUTHORITY_OR_HASH_INVALID")
    db.verify()
    pre = db.meta()
    seq = send_receipt["send_attempt_event_seq"]
    if (pre["head_seq"] != seq
            or pre["head_hash"] != send_receipt["send_attempt_event_sha256"]):
        return result("BLOCKED_SEND_ALREADY_CUSTODIED_OR_HEAD_MOVED")
    s_row = db.conn.execute(
        "SELECT kind,payload,sha FROM events WHERE seq=?", (seq,)
    ).fetchone()
    if s_row is None or s_row["kind"] != SEND_KIND:
        deny("ORIGINAL_SEND_EVENT_MISSING")
    send = json.loads(s_row["payload"])
    h_row = db.conn.execute(
        "SELECT kind,payload FROM events WHERE seq=?",
        (send["handoff_seq"],)).fetchone()
    if h_row is None or h_row["kind"] != HANDOFF_KIND:
        deny("ORIGINAL_HANDOFF_EVENT_MISSING")
    handoff = json.loads(h_row["payload"])
    packet_digest = _packet_sha256(public_packet)
    body_digest = hashlib.sha256(make_body(public_packet)).hexdigest()
    if (packet_digest != send["public_packet_sha256"]
            or body_digest != send["request_body_sha256"]
            or send["owner_source_sha"] != pre["source_sha"]
            or public_packet["lane"] != send["lane"]
            or public_packet["path"] != handoff["native_path"]
            or public_packet["target_commit"] != handoff["target_commit"]
            or public_packet["before_sha256"] != handoff["public_source_sha256"]
            or public_packet["history_sha256"] != handoff["public_history_sha256"]
            or public_packet["target_tree_sha"] != handoff["public_tree_sha"]):
        deny("MODEL_PUBLIC_SOURCE_OR_ORIGINAL_SEND_DRIFT")
    consumed = []
    for row in db.conn.execute(
            "SELECT payload FROM events WHERE kind=? ORDER BY seq", (KIND,)):
        consumed.append(json.loads(row["payload"]))
    for row in db.conn.execute(
            "SELECT payload FROM events WHERE kind='MODEL_DRAFT_ATTEMPTED' ORDER BY seq"):
        item = json.loads(row["payload"])
        consumed.append({"candidate_identity": item["candidate_identity"],
                         "source_after_sha256": item["source_after_sha256"]})
    candidate = validate_untrusted_proposal(
        response["proposal_bytes"], lane=send["lane"],
        target_commit=handoff["target_commit"],
        path=handoff["native_path"],
        before=public_packet["public_source"].encode("utf-8"),
        before_sha256=handoff["public_source_sha256"],
        history_sha256=handoff["public_history_sha256"],
        consumed_candidates={x["candidate_identity"] for x in consumed},
        consumed_after_hashes={x["source_after_sha256"] for x in consumed},
    )
    record = candidate["record"]
    with db.transaction():
        db.verify()
        current = db.meta()
        if (current != pre or current["enabled"] != 1
                or current["legacy_suspended"] != 1
                or db.ready() is not None or db.actives()
                or owner_witness() is not True
                or not SingleOwner.held(db.filename.with_suffix(".lock"))):
            return result("BLOCKED_ORIGINAL_OWNER_MOVED_PRECOMMIT")
        doc = {
            "schema": SCHEMA, "owner_source_sha": current["source_sha"],
            "send_seq": seq, "send_sha256": s_row["sha"],
            "terminal_ticket": send["terminal_ticket"],
            "lane": send["lane"], "scope_sha256": send["scope_sha256"],
            "target_commit": handoff["target_commit"],
            "native_path": handoff["native_path"],
            "public_packet_sha256": packet_digest,
            "request_body_sha256": body_digest,
            "history_sha256": handoff["public_history_sha256"],
            "source_before_sha256": record["before_sha256"],
            "source_after_sha256": record["after_sha256"],
            "candidate_identity": record["candidate_identity"],
            "proposal_sha256": response["proposal_sha256"],
            "validation_record_sha256": candidate["record_sha256"],
            "question": record["question"], "hypothesis": record["hypothesis"],
            "control": record["control"],
            "prior_event_head_sha256": current["head_hash"],
            "publication_authorized": False, "worker_dispatched": False,
            "paid_model_calls": 0, "scientific_first_use": False,
        }
        db.event(KIND, doc)
        db.verify()
        if fault_after_append:
            deny("INJECTED_PRECOMMIT_ROLLBACK")
        final = db.conn.execute(
            "SELECT seq,sha FROM events WHERE seq=? AND kind=?",
            (seq + 1, KIND)).fetchone()
        if (final is None or owner_witness() is not True
                or db.meta()["head_hash"] != final["sha"]):
            deny("ORIGINAL_OWNER_REVOKED_PRECOMMIT")
        return result("ORIGINAL_PROPOSAL_VALIDATED_DATA_ONLY",
                      seq=final["seq"], sha=final["sha"],
                      candidate={
                          "candidate_identity": record["candidate_identity"],
                          "source_after_sha256": record["after_sha256"],
                          "validation_record_sha256": candidate["record_sha256"],
                          "candidate_source": candidate["candidate_source"],
                      })
