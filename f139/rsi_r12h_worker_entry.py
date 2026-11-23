"""R12-H: credentialed GitHub worker verification, NEVER original admission.

R12-G's pre-dispatch HMAC is necessary but insufficient: the same worker
secret is also available to the GitHub authorizer. An input-provided original
event SHA cannot prove original Windows SQLite lifetime-one spend. The
credential-free execution route is therefore forbidden until a distinct,
independently authenticated, once-only ORIGINAL OWNER terminal claim exists.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import re

from f139.local_controller import canonical
from f139.rsi_r12b_signed_job import REPO, WORKFLOW, valid_binding, sha40, sha64
from f139.rsi_r12c_original_spend import owner_self_policy_allows
from f139.rsi_r12g_pre_dispatch import (
    validate_bundle, sign as preissue_signature, PreDispatchDenied,
)
from f139.rsi_r6_known_repair_cycle import MAX_SOURCE

SCHEMA = "forge.f139.rsi-r12h.credentialed-origin-check.v1"
PACKET_SCHEMA = "forge.f139.rsi-r12h.dispatched-inputs.v1"
PACKET_KEYS = frozenset({
    "schema", "binding", "intent", "original_signature",
    "original_event_seq", "original_event_sha256",
    "candidate_source_base64",
})
AUTH_KEYS = frozenset({
    "F139_RSI_NATIVE_BUNDLE", "F139_WORKER_HMAC_KEY", "F139_RSI_POLICY_BASE64",
    "F139_RSI_SOURCE_TREE_SHA", "F139_TICKET", "F139_LANE",
    "F139_TARGET_PACKAGE", "F139_SOURCE_SHA", "GITHUB_SHA",
    "GITHUB_REPOSITORY", "GITHUB_REF", "GITHUB_EVENT_NAME",
    "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_ACTOR",
    "GITHUB_JOB",
})
B64 = re.compile(r"[A-Za-z0-9+/]+={0,2}\Z")
DECIMAL = re.compile(r"[1-9][0-9]*\Z")


class CredentialedRSIDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise CredentialedRSIDenied("F139_RSI_R12H_" + reason)


def unique_pairs(pairs):
    result = {}
    for k, v in pairs:
        need(k not in result, "DUPLICATE_JSON_KEY")
        result[k] = v
    return result


def decode_bounded64(value, *, max_encoded: int, max_raw: int) -> bytes:
    need(type(value) is str and 0 < len(value) <= max_encoded
         and B64.fullmatch(value) is not None,
         "UNTRUSTED_BASE64_SHAPE")
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise CredentialedRSIDenied(
            "F139_RSI_R12H_BASE64_INVALID") from exc
    need(0 < len(raw) <= max_raw
         and base64.b64encode(raw).decode("ascii") == value,
         "NONCANONICAL_OR_UNBOUNDED_BASE64")
    return raw


def packet_from_base64(value):
    raw = decode_bounded64(value, max_encoded=60000, max_raw=45000)
    try:
        packet = json.loads(raw, object_pairs_hook=unique_pairs)
    except (ValueError, UnicodeError) as exc:
        raise CredentialedRSIDenied(
            "F139_RSI_R12H_PACKET_NOT_JSON") from exc
    need(type(packet) is dict and set(packet) == PACKET_KEYS
         and packet["schema"] == PACKET_SCHEMA,
         "UNTRUSTED_PACKET_FIELDS")
    need(raw == canonical(packet), "NONCANONICAL_PACKET")
    return packet


def exact_github_context(env, intent) -> None:
    need(type(env) is dict and type(intent) is dict,
         "GITHUB_CONTEXT_TYPE")
    need(type(env.get("GITHUB_RUN_ID")) is str
         and DECIMAL.fullmatch(env["GITHUB_RUN_ID"]) is not None
         and int(env["GITHUB_RUN_ID"]) > intent["failed_run_id"]
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("GITHUB_REPOSITORY") == REPO
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_SHA") == intent["source_sha"]
         and env.get("F139_SOURCE_SHA") == intent["source_sha"]
         and env.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
         and env.get("GITHUB_ACTOR") == "spoonman136668-ai"
         and env.get("GITHUB_JOB") == "rsi-authorize"
         and env.get("F139_TICKET") == intent["ticket"]
         and env.get("F139_LANE") == "Qualification"
         and env.get("F139_TARGET_PACKAGE") == "f139-rsi-self-v1"
         and env.get("F139_RSI_SOURCE_TREE_SHA") == intent["source_tree_sha"],
         "GITHUB_JOB_OR_PROTECTED_SOURCE_DRIFT")


def owner_scope_issue(policy_issue, original_source_sha: str) -> None:
    need(type(policy_issue) is dict
         and policy_issue.get("number") == 807
         and policy_issue.get("state") == "open"
         and policy_issue.get("author_association") == "OWNER"
         and "pull_request" not in policy_issue
         and type(policy_issue.get("user")) is dict
         and policy_issue["user"].get("login") == "spoonman136668-ai"
         and type(policy_issue.get("body")) is str,
         "ORIGINAL_OPERATOR_ISSUE_NOT_AUTHENTICATED")
    try:
        policy = json.loads(policy_issue["body"],
                            object_pairs_hook=unique_pairs)
    except (ValueError, UnicodeError) as exc:
        raise CredentialedRSIDenied(
            "F139_RSI_R12H_OPERATOR_POLICY_JSON_INVALID") from exc
    need(owner_self_policy_allows(
        policy, original_source_sha=original_source_sha),
        "THREE_LANE_ORIGINAL_SOURCE_NOT_ACTIVATED")


def authorize_packet(*, packet: dict, key: str, environment: dict,
                     provider_issue: dict) -> dict:
    """Verify one credentialed HMAC and GitHub origin; DO NOT admit worker.

    The caller MUST independently fetch issue #807 and source tree using
    authenticated GitHub API, never trust data from packet as provider proof.
    Even a valid HMAC and owner policy do NOT reveal original owner's ledger.
    """
    need(type(packet) is dict and set(packet) == PACKET_KEYS
         and packet.get("schema") == PACKET_SCHEMA,
         "PACKET_FIELDS_OR_SCHEMA")
    binding, intent = packet["binding"], packet["intent"]
    need(valid_binding(binding), "UNTRUSTED_R12A_BINDING")
    try:
        validate_bundle(intent, binding)
    except (PreDispatchDenied, KeyError, TypeError) as exc:
        raise CredentialedRSIDenied(
            "F139_RSI_R12H_ORIGINAL_PREDISPATCH_BUNDLE_INVALID") from exc
    exact_github_context(environment, intent)
    owner_scope_issue(provider_issue, intent["owner_source_sha"])
    signature = packet["original_signature"]
    need(sha64(signature) and type(key) is str and len(key) >= 32,
         "SIGNATURE_OR_CREDENTIAL_INVALID")
    try:
        expected = preissue_signature(key, intent)
    except (PreDispatchDenied, TypeError, ValueError) as exc:
        raise CredentialedRSIDenied(
            "F139_RSI_R12H_SIGNING_PRIMITIVE_INVALID") from exc
    need(hmac.compare_digest(signature, expected),
         "HMAC_NOT_ORIGINAL_PREISSUE")
    event_seq = packet["original_event_seq"]
    event_sha = packet["original_event_sha256"]
    need(type(event_seq) is int
         and event_seq > intent["reservation_seq"]
         and sha64(event_sha),
         "UNVERIFIED_ORIGINAL_EVENT_SHAPE")
    raw = decode_bounded64(
        packet["candidate_source_base64"],
        max_encoded=4 * ((MAX_SOURCE + 2) // 3),
        max_raw=MAX_SOURCE)
    need(hashlib.sha256(raw).hexdigest() == intent["candidate_sha256"],
         "CANDIDATE_SOURCE_BYTES_DRIFT")
    # No source execution here (including import/exec/eval). Any arbitrary
    # signed candidate remains untrusted development data until independent
    # original-issuance custody and isolated qualification.
    digest = hashlib.sha256(canonical({
        "ticket": intent["ticket"],
        "source_sha": intent["source_sha"],
        "source_tree_sha": intent["source_tree_sha"],
        "original_event_seq": event_seq,
        "original_event_sha256": event_sha,
        "reservation_event_sha256": intent["reservation_event_sha256"],
        "preissue_sha256": hashlib.sha256(canonical(intent)).hexdigest(),
        "candidate_sha256": intent["candidate_sha256"],
        "run_id": int(environment["GITHUB_RUN_ID"]),
    })).hexdigest()
    return {
        "schema": SCHEMA,
        "ticket": intent["ticket"],
        "source_sha": intent["source_sha"],
        "authorization_sha256": digest,
        "credentialed_hmac_verified": True,
        "owner_policy_shape_verified": True,
        "original_owner_sqlite_ledger_verified": False,
        "one_use_original_terminal_receipt_verified": False,
        "credential_free_worker_admitted": False,
        "worker_dispatched_by_authorizer": False,
        "scientific_first_use": False,
        "source_promoted": False,
        "autonomous_rsi_proven": False,
    }


def cli():
    import sys
    try:
        packet = packet_from_base64(
            os.environ.get("F139_RSI_NATIVE_BUNDLE", ""))
        issue_raw = decode_bounded64(
            os.environ.get("F139_RSI_POLICY_BASE64", ""),
            max_encoded=50000, max_raw=32000)
        issue = json.loads(issue_raw, object_pairs_hook=unique_pairs)
        env = {k: os.environ.get(k, "") for k in AUTH_KEYS}
        report = authorize_packet(
            packet=packet, key=os.environ.get("F139_WORKER_HMAC_KEY", ""),
            environment=env, provider_issue=issue)
    except (CredentialedRSIDenied, ValueError, KeyError,
            TypeError, UnicodeError) as exc:
        raise SystemExit("F139_RSI_R12H_CREDENTIALLED_FAIL_CLOSED "
                         + str(exc)) from exc
    sys.stdout.write(canonical(report).decode("ascii") + "\n")


if __name__ == "__main__":
    cli()
