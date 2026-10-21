"""F139-NCI04-A5: owner-authenticated, source-frozen native issue intake.

INERT qualification-only contract. This does not enqueue, claim, dispatch, store
receipts, transition source, modify a checkout, start a controller, or authorize
scientific first-use. The one existing F139 controller will require separate
source qualification and owner-side custody admission before invoking it.

Existing D2K remains *unchanged*: distinct issue label, kind, schema and ticket.
"""
from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
import json
import re

from f139.nci04_native_contract import Candidate, canonical, digest, parse_intent
from f139.nci04_signed_native import sign_native_intent, NATIVE_TICKET
from f139.verify_ticket import signature as legacy_signature

OWNER = "spoonman136668-ai"
LABEL = "f139-native-development-eligible"
SCHEMA = "forge.f139.nci04.owner-native-development.v1"
KIND = "native-cognitive-candidate"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
BODY_KEYS = frozenset({
    "schema", "source_sha", "lane", "kind", "intent_base64",
    "scientific_first_use", "paid_model_calls",
})
MAX_BODY_BYTES = 60000
MAX_INTENT_BYTES = 44000
LANES = frozenset({"Wingless", "Yggdrasil"})


class NativeIssueDenied(ValueError):
    pass


def require(ok: bool, why: str) -> None:
    if not ok:
        raise NativeIssueDenied("F139_NCI04_A5_" + why)


def decode_unique(pairs: list[tuple[str, object]]) -> dict:
    doc = {}
    for name, value in pairs:
        require(name not in doc, "DUPLICATE_KEY")
        doc[name] = value
    return doc


@dataclass(frozen=True)
class NativeIssue:
    number: int
    issue_id: int
    ticket: str
    lane: str
    source_sha: str
    issue_body_sha256: str
    native_intent_sha256: str
    qualification_key: str
    intent_raw: bytes
    candidate: Candidate


def inspect_owner_issue(raw: dict, *, protected_main: str,
                        authenticated_target_commit: str,
                        authenticated_target_tree: str) -> NativeIssue:
    """Return data, never execution authority.

    The caller must independently establish both the current protected main
    and exact *native target* commit/tree from the authenticated provider,
    not from issue-supplied candidate bytes or a moving PR branch.
    """
    require(isinstance(protected_main, str)
            and SHA40.fullmatch(protected_main) is not None, "MAIN_UNVERIFIED")
    require(isinstance(raw, dict), "ISSUE_NOT_OBJECT")
    require(raw.get("state") == "open" and "pull_request" not in raw
            and isinstance(raw.get("user"), dict)
            and raw["user"].get("login") == OWNER
            and raw.get("author_association") == "OWNER",
            "ISSUE_OWNER_NOT_AUTHENTICATED")
    require(type(raw.get("number")) is int and raw["number"] > 0
            and type(raw.get("id")) is int and raw["id"] > 0,
            "ISSUE_IDENTITY_INVALID")
    labels = raw.get("labels")
    require(isinstance(labels, list)
            and all(isinstance(item, dict) and isinstance(item.get("name"), str)
                    for item in labels)
            and LABEL in [item["name"] for item in labels]
            and "f139-development-eligible" not in [item["name"] for item in labels],
            "NATIVE_LABEL_MISSING_OR_LEGACY_MIXED")
    body = raw.get("body")
    require(isinstance(body, str)
            and 0 < len(body.encode("utf-8")) <= MAX_BODY_BYTES,
            "ISSUE_BODY_SIZE_INVALID")
    try:
        record = json.loads(body, object_pairs_hook=decode_unique)
    except (ValueError, UnicodeError) as exc:
        raise NativeIssueDenied("F139_NCI04_A5_BODY_JSON_INVALID") from exc
    require(isinstance(record, dict) and set(record) == BODY_KEYS
            and record.get("schema") == SCHEMA
            and record.get("source_sha") == protected_main
            and record.get("lane") in LANES
            and record.get("kind") == KIND
            and record.get("scientific_first_use") is False
            and type(record.get("paid_model_calls")) is int
            and record["paid_model_calls"] == 0,
            "ISSUE_NATIVE_SCHEMA_OR_AUTHORITY")
    encoded = record.get("intent_base64")
    require(isinstance(encoded, str)
            and 0 < len(encoded) <= (MAX_INTENT_BYTES * 4 // 3 + 8),
            "INTENT_FIELD_INVALID")
    try:
        intent_raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise NativeIssueDenied("F139_NCI04_A5_INTENT_ENCODING") from exc
    require(len(intent_raw) <= MAX_INTENT_BYTES
            and base64.b64encode(intent_raw).decode("ascii") == encoded,
            "INTENT_UNQUALIFIED_BYTES")
    candidate = parse_intent(intent_raw, protected_main=protected_main,
                             target_commit=authenticated_target_commit,
                             target_tree_sha=authenticated_target_tree)
    require(candidate.lane == record["lane"], "INTENT_ISSUE_LANE_DRIFT")
    ticket = ("f139-nci04-i" + str(raw["number"]) + "-" +
              protected_main[:12] + "-" + candidate.intent_sha256[:8])
    require(NATIVE_TICKET.fullmatch(ticket) is not None, "NATIVE_TICKET_INVALID")
    return NativeIssue(
        number=raw["number"], issue_id=raw["id"], ticket=ticket,
        lane=candidate.lane, source_sha=protected_main,
        issue_body_sha256=digest(canonical(record)),
        native_intent_sha256=candidate.intent_sha256,
        qualification_key=candidate.qualification_key,
        intent_raw=intent_raw, candidate=candidate,
    )


def make_signed_dispatch_inputs(issue: NativeIssue, *, owner_hmac_key: str,
                                epoch: int) -> dict[str, str]:
    """Construct source-only native authorization; caller must still atomically
    admit under original owner lock and append source-bound event before POST.

    This must never execute in a candidate-code worker (key isolation).
    """
    require(isinstance(issue, NativeIssue)
            and type(epoch) is int and 0 < epoch < 2**31,
            "OWNER_EPOCH_INVALID")
    require(isinstance(owner_hmac_key, str) and len(owner_hmac_key) >= 32,
            "OWNER_SECRET_MISSING")
    controller_sig = legacy_signature(owner_hmac_key, issue.ticket, issue.lane,
                                      issue.source_sha, str(epoch))
    inputs = {
        "key": owner_hmac_key, "ticket": issue.ticket, "lane": issue.lane,
        "source_sha": issue.source_sha, "epoch": str(epoch),
        "signature": controller_sig,
    }
    native_signature = sign_native_intent(
        inputs, issue.candidate, issue_number=str(issue.number),
        issue_id=str(issue.issue_id),
        issue_body_sha256=issue.issue_body_sha256)
    return {
        "ticket": issue.ticket, "lane": issue.lane,
        "source_sha": issue.source_sha, "epoch": str(epoch),
        "signature": controller_sig, "native_signature": native_signature,
        "issue_number": str(issue.number), "issue_id": str(issue.issue_id),
        "body_sha256": issue.issue_body_sha256,
        "intent_sha256": issue.native_intent_sha256,
        "target_commit": issue.candidate.target_commit,
        "target_tree_sha": issue.candidate.target_tree_sha,
        "qualification_key": issue.qualification_key,
        # Secret never returned in dispatch fields.
    }
