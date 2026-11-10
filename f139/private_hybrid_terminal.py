"""Private Hybrid provider-terminal custody: read-only, no live admission.

Distinct from public FORGE V1 issue/ZIP route: private payloads may NEVER be
copied into FORGE issue bodies. This deterministic inspector binds a private
provider terminal ZIP to the pre-existing original-owner NativeAdmission and
the already verified credentialed private-payload binding. This module NEVER
creates a NativeAdmission, signs tickets, dispatches, executes private code,
reads credentials, writes an owner ledger, or promotes a result to science.

Provider metadata MUST be independently authenticated by the actual private
repository identity. Bare dicts and SHA strings alone do not authenticate
GitHub runs, actors or original owner issuance. The result *always* retains
unverified live owner ledger/worker execution until separately witnessed.
"""
from __future__ import annotations

import io
import json
import re
import zipfile

from f139.nci04_native_contract import canonical, digest
from f139.nci04_signed_native import NativeAdmission, receipt_from_report
from f139.private_hybrid_reference import LANE, REPOSITORY

SCHEMA = "forge.f139.private-hybrid-provider-terminal.v1"
TRANSPORT = "forge.f139.private-hybrid-private-provider-binding.v1"
FILES = frozenset({
    "f139-native-report.json",
    "f139-native-receipt.json",
    "f139-native-receipt.sha256",
    "f139-private-provider-binding.json",
})
MAX_ZIP_BYTES = 2_000_000
MAX_MEMBER_BYTES = 64_000
HEX40 = re.compile(r"[a-f0-9]{40}\Z")
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
META_FIELDS = frozenset({
    "repository", "private", "private_run_id", "private_job_id",
    "private_artifact_id", "digest", "size_in_bytes", "private_commit",
    "private_tree", "original_owner_run_id", "source_sha",
})
TRANSPORT_FIELDS = frozenset({
    "schema", "repository", "private_run_id", "private_job_id",
    "private_artifact_id", "original_owner_run_id", "source_sha",
    "private_payload_sha256", "private_target_commit", "private_target_tree",
    "private_storage_commit", "private_storage_tree", "native_receipt_sha256",
    "native_report_sha256", "scientific_first_use", "owner_ledger_verified",
    "private_worker_signed_verified",
})


class PrivateTerminalDenied(ValueError):
    pass


def need(ok, why):
    if not ok:
        raise PrivateTerminalDenied("F139_PRIVATE_HYBRID_TERMINAL_" + why)


def load_unique(raw):
    need(type(raw) is bytes and 0 < len(raw) <= MAX_MEMBER_BYTES,
         "JSON_BOUNDED")
    def unique(pairs):
        out = {}
        for key, val in pairs:
            need(key not in out, "DUPLICATE_JSON_FIELD")
            out[key] = val
        return out
    try:
        doc = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeError, TypeError) as exc:
        raise PrivateTerminalDenied("F139_PRIVATE_HYBRID_TERMINAL_BAD_JSON") from exc
    need(type(doc) is dict and canonical(doc) == raw, "CANONICAL_JSON_ONLY")
    return doc


def verify_private_provider_terminal(raw_zip, authenticated_meta, admission,
                                     verified_owner_binding, *,
                                     verified_private_reference):
    """Structurally verify provider bytes. No live-signature/ledger inference.

    Inputs must come from independently authenticated sources outside the
    untrusted private candidate sandbox. In particular NativeAdmission alone
    must NOT be reconstituted from public JSON; owner must first authenticate
    its real HMAC and durable issue/epoch ledger.
    """
    need(type(raw_zip) is bytes and 0 < len(raw_zip) <= MAX_ZIP_BYTES,
         "ZIP_SIZE_INVALID")
    need(type(authenticated_meta) is dict and
         set(authenticated_meta) == META_FIELDS,
         "PROVIDER_METADATA_FIELDS")
    meta = authenticated_meta
    need(meta["repository"] == REPOSITORY and meta["private"] is True,
         "PRIVATE_PROJECT_PROVIDER_REQUIRED")
    for key in ("private_run_id", "private_job_id", "private_artifact_id",
                "original_owner_run_id", "size_in_bytes"):
        need(type(meta[key]) is int and meta[key] > 0,
             "PROVIDER_INTEGER_IDENTITY")
    for key in ("private_commit", "private_tree", "source_sha"):
        need(type(meta[key]) is str and HEX40.fullmatch(meta[key]) is not None,
             "PROVIDER_SOURCE_SHA")
    need(meta["digest"] == "sha256:" + digest(raw_zip)
         and meta["size_in_bytes"] == len(raw_zip),
         "PROVIDER_ZIP_DIGEST")
    need(type(admission) is NativeAdmission
         and admission.lane == LANE
         and admission.intent.lane == LANE
         and admission.run_id == meta["original_owner_run_id"]
         and admission.source_sha == meta["source_sha"],
         "ORIGINAL_OWNER_ADMISSION_IDENTITY")
    need(type(verified_owner_binding) is dict
         and verified_owner_binding.get("schema") ==
             "forge.f139.private-hybrid-credentialed-binding.v1"
         and verified_owner_binding.get("provided_owner_hmac_pair_matched") is True
         and verified_owner_binding.get("private_blob_bytes_matched") is True
         and verified_owner_binding.get("ticket") == admission.ticket
         and verified_owner_binding.get("authorization_binding_sha256") ==
             admission.authorization_sha256
         and verified_owner_binding.get("private_payload_sha256") ==
             admission.intent.intent_sha256
         and verified_owner_binding.get("reference_sha256") ==
             digest(canonical(verified_private_reference))
         and verified_owner_binding.get("owner_source_sha") == admission.source_sha
         and verified_owner_binding.get("private_target_commit") ==
             admission.intent.target_commit
         and verified_owner_binding.get("private_target_tree") ==
             admission.intent.target_tree_sha
         and verified_owner_binding.get("original_owner_live_issue_verified") is False
         and verified_owner_binding.get("private_worker_executed") is False,
         "CREDENTIAL_VERIFIER_BINDING_INVALID")
    need(type(verified_private_reference) is dict
         and verified_private_reference.get("schema") ==
             "forge.f139.private-hybrid-payload-reference.v1"
         and verified_private_reference.get("lane") == LANE
         and verified_private_reference.get("repository") == REPOSITORY
         and verified_private_reference.get("private_payload_sha256") ==
             admission.intent.intent_sha256
         and verified_private_reference.get("private_payload_commit") ==
             meta["private_commit"]
         and verified_private_reference.get("private_payload_tree") ==
             meta["private_tree"]
         and verified_private_reference.get("private_target_commit") ==
             admission.intent.target_commit
         and verified_private_reference.get("private_target_tree") ==
             admission.intent.target_tree_sha,
         "PRIVATE_BLOB_STORAGE_OR_TARGET_DRIFT")
    try:
        with zipfile.ZipFile(io.BytesIO(raw_zip)) as archive:
            rows = archive.infolist()
            need(len(rows) == len(FILES) and
                 {x.filename for x in rows} == FILES and
                 all(not x.is_dir() and x.flag_bits & 1 == 0 and
                     x.file_size <= MAX_MEMBER_BYTES and
                     x.compress_size <= MAX_MEMBER_BYTES
                     for x in rows),
                 "ZIP_MEMBER_SET")
            members = {x.filename: archive.read(x.filename)
                       for x in rows}
    except PrivateTerminalDenied:
        raise
    except (ValueError, OSError, RuntimeError, zipfile.BadZipFile) as exc:
        raise PrivateTerminalDenied("F139_PRIVATE_HYBRID_TERMINAL_INVALID_ZIP") from exc
    receipt_raw = members["f139-native-receipt.json"]
    report_raw = members["f139-native-report.json"]
    need(members["f139-native-receipt.sha256"] ==
         (digest(receipt_raw) + "  f139-native-receipt.json\n").encode("ascii"),
         "RECEIPT_MEMBER_DIGEST")
    receipt = load_unique(receipt_raw)
    report = load_unique(report_raw)
    transport = load_unique(members["f139-private-provider-binding.json"])
    need(set(transport) == TRANSPORT_FIELDS and
         transport["schema"] == TRANSPORT and transport["repository"] == REPOSITORY,
         "PRIVATE_TRANSPORT_SCHEMA")
    for name in ("private_run_id", "private_job_id", "private_artifact_id",
                 "original_owner_run_id", "source_sha", "private_commit",
                 "private_tree"):
        if name in transport:
            need(transport[name] == meta[name], "PRIVATE_PROVIDER_TERMINAL_DRIFT")
    need(transport["source_sha"] == meta["source_sha"] and
         transport["private_run_id"] == meta["private_run_id"] and
         transport["private_job_id"] == meta["private_job_id"] and
         transport["private_artifact_id"] == meta["private_artifact_id"] and
         transport["original_owner_run_id"] == meta["original_owner_run_id"] and
         transport["private_storage_commit"] == meta["private_commit"] and
         transport["private_storage_tree"] == meta["private_tree"] and
         transport["private_payload_sha256"] == admission.intent.intent_sha256 and
         transport["private_target_commit"] == admission.intent.target_commit and
         transport["private_target_tree"] == admission.intent.target_tree_sha and
         transport["native_receipt_sha256"] == digest(receipt_raw) and
         transport["native_report_sha256"] == digest(report_raw) and
         transport["scientific_first_use"] is False and
         transport["owner_ledger_verified"] is False and
         transport["private_worker_signed_verified"] is False,
         "TRANSPORT_AUTHORITY_OR_SOURCE_DRIFT")
    expected_receipt = receipt_from_report(admission, report)
    need(expected_receipt == receipt and
         expected_receipt["native_authorization_sha256"] ==
             admission.authorization_sha256 and
         expected_receipt["native_intent_sha256"] ==
             admission.intent.intent_sha256,
         "NATIVE_RECEIPT_RECOMPUTATION_DRIFT")
    # Even a syntactically passing report cannot stand in for original-owner
    # issuance, job execution, platform admission or owner-side WAL settlement.
    return {
        "schema": SCHEMA,
        "private_project": REPOSITORY,
        "private_run_id": meta["private_run_id"],
        "private_job_id": meta["private_job_id"],
        "original_owner_run_id": admission.run_id,
        "source_sha": admission.source_sha,
        "native_intent_sha256": admission.intent.intent_sha256,
        "native_receipt_sha256": digest(receipt_raw),
        "native_report_sha256": digest(report_raw),
        "provider_zip_sha256": digest(raw_zip),
        "reported_native_qualified": expected_receipt["native_qualified"],
        "provider_zip_structurally_verified": True,
        "original_owner_live_issuance_verified": False,
        "independent_private_worker_execution_verified": False,
        "durable_owner_ledger_settled": False,
        "scientific_first_use": False,
        "candidate_accepted": False,
    }
