"""R12-J: independently verifiable pre-execution Ed25519 owner evidence.

This is a cryptographic validator, NOT an enrolled original-owner signer or
original Windows owner authorization. The pinned source trust registry is
disabled until separately authorized key enrollment and qualification.
GitHub's shared F139_WORKER_HMAC_KEY must never substitute for this key.
No workflow/owner tick, dispatch, worker access or scientific first use.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from f139.local_controller import canonical
from f139.rsi_r11_owner_once import _sha40 as sha40
from f139.rsi_r12b_signed_job import REPO, WORKFLOW, sha64
from f139.rsi_r12g_pre_dispatch import (
    validate_bundle, validate_event as validate_preissue_event,
    observe_provider_job,
)

SCHEMA = "forge.f139.rsi-r12j.original-preexecution-signature.v1"
SIGNED_SCHEMA = "forge.f139.rsi-r12j.signed-original-preexecution.v1"
ROOT_SCHEMA = "forge.f139.rsi-r12j.original-trust-root.v1"
DOMAIN = b"FORGE-F139-RSI-ORIGINAL-PREEXECUTION-V1\n"
ROOT = Path(__file__).with_name("rsi_r12j_owner_trust.json")
SOURCE = Path(__file__).with_name("rsi_r12j_ed25519.go")
BASE64 = re.compile(r"[A-Za-z0-9+/]+={0,2}\Z")
STATEMENT_FIELDS = frozenset({
    "schema", "repository", "workflow", "owner_source_sha",
    "source_sha", "source_tree_sha", "ticket", "runner_os",
    "reservation_seq", "reservation_event_sha256",
    "preissue_seq", "preissue_event_sha256",
    "preissue_intent_sha256", "candidate_sha256",
    "run_id", "job_id", "run_attempt", "original_ledger_head_sha256",
    "one_signed_job", "retry_allowed", "development_only",
    "original_ledger_independently_verified",
    "credential_free_worker_admitted", "scientific_first_use",
    "source_promoted", "autonomous_rsi_proven",
})


class OriginalSignerDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise OriginalSignerDenied("F139_RSI_R12J_" + reason)


def decode64(value: str, size: int) -> bytes:
    need(type(value) is str and size <= len(value) <= 2 * size + 4
         and BASE64.fullmatch(value) is not None,
         "BASE64_SHAPE")
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise OriginalSignerDenied("F139_RSI_R12J_BASE64_INVALID") from exc
    need(len(raw) == size
         and base64.b64encode(raw).decode("ascii") == value,
         "KEY_OR_SIGNATURE_BYTES_DRIFT")
    return raw


def statement(*, preissue: dict, preissue_row, binding: dict,
              run: dict, job: dict, ledger_head: str) -> dict:
    """Pure source projection, not independent original ledger custody."""
    need(type(preissue) is dict and type(binding) is dict
         and type(preissue_row) is dict
         and type(ledger_head) is str and sha64(ledger_head)
         and type(preissue_row.get("seq")) is int
         and preissue_row["seq"] > binding["reservation_seq"]
         and sha64(preissue_row.get("sha"))
         and sha64(preissue_row.get("prior_sha")),
         "HISTORICAL_PREISSUE_SHAPE")
    validate_bundle(preissue["intent"], binding)
    validate_preissue_event(
        payload=preissue, row=preissue_row,
        binding=binding, source_at_event=binding["owner_source_sha"])
    checked = observe_provider_job(
        bundle=preissue["intent"], run=run, job=job)
    need(preissue["intent_sha256"] ==
         hashlib.sha256(canonical(preissue["intent"])).hexdigest(),
         "INTENT_DIGEST_DRIFT")
    intent = preissue["intent"]
    return {
        "schema": SCHEMA,
        "repository": REPO, "workflow": WORKFLOW,
        "owner_source_sha": intent["owner_source_sha"],
        "source_sha": intent["source_sha"],
        "source_tree_sha": intent["source_tree_sha"],
        "ticket": intent["ticket"], "runner_os": intent["runner_os"],
        "reservation_seq": intent["reservation_seq"],
        "reservation_event_sha256": intent["reservation_event_sha256"],
        "preissue_seq": preissue_row["seq"],
        "preissue_event_sha256": preissue_row["sha"],
        "preissue_intent_sha256": preissue["intent_sha256"],
        "candidate_sha256": intent["candidate_sha256"],
        "run_id": checked["run_id"], "job_id": checked["job_id"],
        "run_attempt": 1,
        "original_ledger_head_sha256": ledger_head,
        "one_signed_job": 1, "retry_allowed": False,
        "development_only": True,
        # False until actual original-only signature and custody verified.
        "original_ledger_independently_verified": False,
        "credential_free_worker_admitted": False,
        "scientific_first_use": False, "source_promoted": False,
        "autonomous_rsi_proven": False,
    }


def validate_statement(doc: dict) -> None:
    need(type(doc) is dict and set(doc) == STATEMENT_FIELDS
         and doc["schema"] == SCHEMA
         and doc["repository"] == REPO
         and doc["workflow"] == WORKFLOW
         and sha40(doc["owner_source_sha"])
         and sha40(doc["source_sha"])
         and sha40(doc["source_tree_sha"])
         and type(doc["ticket"]) is str
         and re.fullmatch(r"f139-rsi-[a-f0-9]{32}", doc["ticket"]) is not None
         and doc["runner_os"] in ("ubuntu-latest", "windows-latest")
         and type(doc["reservation_seq"]) is int
         and doc["reservation_seq"] > 0
         and sha64(doc["reservation_event_sha256"])
         and type(doc["preissue_seq"]) is int
         and doc["preissue_seq"] > doc["reservation_seq"]
         and sha64(doc["preissue_event_sha256"])
         and sha64(doc["preissue_intent_sha256"])
         and sha64(doc["candidate_sha256"])
         and type(doc["run_id"]) is int and doc["run_id"] > 0
         and type(doc["job_id"]) is int and doc["job_id"] > 0
         and type(doc["run_attempt"]) is int and doc["run_attempt"] == 1
         and sha64(doc["original_ledger_head_sha256"])
         and type(doc["one_signed_job"]) is int
         and doc["one_signed_job"] == 1
         and doc["retry_allowed"] is False
         and doc["development_only"] is True
         and all(doc[k] is False for k in (
             "original_ledger_independently_verified",
             "credential_free_worker_admitted", "scientific_first_use",
             "source_promoted", "autonomous_rsi_proven")),
         "SIGNED_STATEMENT_FIELDS_OR_PERMISSION_DRIFT")


def verify_ed25519(*, statement_data: dict, signature_b64: str,
                   public_key_b64: str) -> bool:
    """Ed25519 RFC8032 via Go stdlib, not a custom Python implementation.

    This low-level helper proves ONLY possession of the corresponding
    private key. It cannot establish that the signer was the original owner.
    Production enrollment is checked separately by verify_enrolled().
    """
    validate_statement(statement_data)
    signature = decode64(signature_b64, 64)
    public_key = decode64(public_key_b64, 32)
    need(SOURCE.is_file() and not SOURCE.is_symlink(),
         "SOURCE_VERIFIER_NOT_PINNED")
    go = shutil.which("go")
    need(type(go) is str and bool(go), "GO_VERIFIER_UNAVAILABLE")
    body = DOMAIN + canonical(statement_data)
    need(len(body) <= 8192, "SIGNATURE_MESSAGE_OVERSIZED")
    environment = dict(os.environ)
    # The verifier imports only Go stdlib and must not fetch modules/tools.
    environment.update({
        "GO111MODULE": "off", "GOTOOLCHAIN": "local",
        "GOPROXY": "off", "GOSUMDB": "off", "GOWORK": "off",
    })
    try:
        response = subprocess.run(
            [go, "run", str(SOURCE), "--public-key",
             base64.b64encode(public_key).decode("ascii"),
             "--signature", base64.b64encode(signature).decode("ascii")],
            input=body, capture_output=True, text=False,
            timeout=90, check=False, env=environment,
            cwd=str(SOURCE.parent),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OriginalSignerDenied(
            "F139_RSI_R12J_CRYPTOGRAPHIC_VERIFIER_UNAVAILABLE") from exc
    need(response.returncode == 0
         and response.stdout == b"F139_RSI_R12J_ED25519_VERIFIED\n",
         "ED25519_SIGNATURE_INVALID")
    return True


def verify_enrolled(*, signed_receipt: dict) -> dict:
    """Entrypoint for a future worker; always denies while root is disabled.

    Real key material, private key enrollment, original-owner transition,
    workflow qualification and one-use original claim are NOT performed.
    """
    need(type(signed_receipt) is dict
         and set(signed_receipt) == {
             "schema", "statement", "key_id", "signature_base64"}
         and signed_receipt["schema"] == SIGNED_SCHEMA,
         "SIGNED_RECEIPT_FIELDS")
    doc = signed_receipt["statement"]
    validate_statement(doc)
    need(ROOT.is_file() and not ROOT.is_symlink(), "TRUST_ROOT_MISSING")
    try:
        root = json.loads(ROOT.read_text("ascii"))
    except (ValueError, UnicodeError, OSError) as exc:
        raise OriginalSignerDenied(
            "F139_RSI_R12J_TRUST_ROOT_UNREADABLE") from exc
    need(type(root) is dict and set(root) == {
        "schema", "enabled", "owner_source_sha", "keys",
        "allow_worker_admission"}
         and root["schema"] == ROOT_SCHEMA
         and sha40(root["owner_source_sha"])
         and root["owner_source_sha"] == doc["owner_source_sha"]
         and root["allow_worker_admission"] is False
         and type(root["keys"]) is list
         and len(root["keys"]) <= 1,
         "TRUST_ROOT_SOURCE_OR_POLICY_DRIFT")
    # The current checked-in trust root is disabled and contains no keys.
    need(root["enabled"] is True and len(root["keys"]) == 1,
         "ORIGINAL_OWNER_KEY_NOT_ENROLLED")
    entry = root["keys"][0]
    need(type(entry) is dict and set(entry) == {
        "id", "public_key_b64", "status"}
         and entry["status"] == "active"
         and sha64(entry["id"])
         and entry["id"] == signed_receipt["key_id"],
         "PUBLIC_KEY_NOT_PINNED")
    pub = decode64(entry["public_key_b64"], 32)
    need(hashlib.sha256(pub).hexdigest() == entry["id"],
         "PUBLIC_KEY_FINGERPRINT_DRIFT")
    verify_ed25519(statement_data=doc,
                   signature_b64=signed_receipt["signature_base64"],
                   public_key_b64=entry["public_key_b64"])
    return {
        "schema": "forge.f139.rsi-r12j.crypto-only-proof.v1",
        "ticket": doc["ticket"],
        "run_id": doc["run_id"],
        "job_id": doc["job_id"],
        "run_attempt": 1,
        "owner_public_key_signature_verified": True,
        # Verify source-only public signature; do not upcast to original
        # native owner issuance, consumed execution or science.
        "independent_original_ledger_custody_verified": False,
        "once_only_original_execution_claim_verified": False,
        "credential_free_worker_admitted": False,
        "scientific_first_use": False,
        "source_promoted": False,
        "autonomous_rsi_proven": False,
    }
