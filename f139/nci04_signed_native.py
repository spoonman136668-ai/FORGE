"""F139-NCI04-A3: composed signed native-intent admission and receipt boundary.

INERT until the original F139 controller independently qualifies a distinct
NCI-04 issue kind, signs it under its existing owner epoch, and activates a
credential-isolated native worker. This module NEVER dispatches or writes to
GitHub, source trees, SQLite, accepted refs, or scientific stores.

A legacy D2K package-diagnostic ticket is categorically not native authority.
A native intent requires BOTH an authentic legacy F139 workflow ticket HMAC
and a domain-separated NCI-04 HMAC over the immutable native candidate
qualification key, issue identity, exact target source/tree and full intent
digest. No fallback/implicit conversion from existing issue work is allowed.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
import re

from f139.nci04_native_contract import Candidate, canonical, digest, parse_intent
from f139.nci04_native_worker import (commands_for, YGGDRASIL_G29_SOURCE, YGGDRASIL_G29_TESTS, YGG_G29_ATLAS_TEST, YGG_G29_ATLAS_MARKER)
from f139.verify_ticket import REPO, WORKFLOW, admit as admit_controller_ticket, Untrusted

ISSUE_NUMBER = re.compile(r"[1-9][0-9]*\Z")
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
NATIVE_TICKET = re.compile(r"f139-nci04-i([1-9][0-9]*)-([a-f0-9]{12})-([a-f0-9]{8})\Z")
INTENT_SCHEMA = "forge.f139.nci04.composed-native-work.v1"
RECEIPT_SCHEMA = "forge.f139.nci04.native-execution-receipt.v1"
MAX_RECEIPT = 64000


def require(value: bool, reason: str) -> None:
    if not value:
        raise Untrusted("F139_NCI04_" + reason)


def _identity(inputs: dict, issue_number: str, issue_id: str,
              issue_body_sha256: str, candidate: Candidate) -> dict:
    require(isinstance(inputs, dict) and isinstance(issue_number, str)
            and ISSUE_NUMBER.fullmatch(issue_number) is not None
            and isinstance(issue_id, str) and ISSUE_NUMBER.fullmatch(issue_id) is not None
            and isinstance(issue_body_sha256, str)
            and SHA256.fullmatch(issue_body_sha256) is not None,
            "ISSUE_IDENTITY_INVALID")
    ticket = inputs.get("ticket")
    require(isinstance(ticket, str) and NATIVE_TICKET.fullmatch(ticket) is not None,
            "NATIVE_TICKET_REQUIRED")
    match = NATIVE_TICKET.fullmatch(ticket)
    require(match.group(1) == issue_number
            and match.group(2) == inputs.get("source_sha", "")[:12]
            and match.group(3) == candidate.intent_sha256[:8],
            "NATIVE_TICKET_IDENTITY_DRIFT")
    require(inputs.get("lane") == candidate.lane, "LANE_DRIFT")
    require(isinstance(inputs.get("signature"), str)
            and SHA256.fullmatch(inputs["signature"]) is not None,
            "CONTROLLER_SIGNATURE_INVALID")
    return {
        "schema": INTENT_SCHEMA,
        "repository": REPO, "workflow": WORKFLOW,
        "ticket": ticket, "lane": candidate.lane,
        "source_sha": inputs["source_sha"], "epoch": inputs["epoch"],
        "controller_signature_sha256": digest(inputs["signature"].encode("ascii")),
        "issue_number": int(issue_number), "issue_id": int(issue_id),
        "issue_body_sha256": issue_body_sha256,
        "native_intent_sha256": candidate.intent_sha256,
        "qualification_key": candidate.qualification_key,
        "native_target_commit": candidate.target_commit,
        "native_target_tree": candidate.target_tree_sha,
        "native_path": candidate.path,
        "before_sha256": candidate.before_sha256,
        "after_sha256": candidate.after_sha256,
        "no_scientific_first_use": True,
    }


def sign_native_intent(inputs: dict, candidate: Candidate, *,
                       issue_number: str, issue_id: str,
                       issue_body_sha256: str) -> str:
    """Controller-side signature constructor; caller has no action authority."""
    key = inputs.get("key")
    require(isinstance(key, str) and len(key) >= 32,
            "OWNER_KEY_MISSING")
    payload = _identity(inputs, issue_number, issue_id, issue_body_sha256,
                        candidate)
    return hmac.new(key.encode(), b"F139-NCI04-V1\n" + canonical(payload),
                    hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class NativeAdmission:
    ticket: str
    lane: str
    source_sha: str
    run_id: int
    runner_os: str
    issue_number: int
    issue_id: int
    intent: Candidate
    authorization_sha256: str


def admit_native_intent(inputs: dict, native_intent_raw: bytes, *,
                        native_signature: str, issue_number: str,
                        issue_id: str, issue_body_sha256: str,
                        authenticated_main_sha: str, authenticated_target_commit: str,
                        authenticated_target_tree: str) -> NativeAdmission:
    require(isinstance(inputs,dict) and isinstance(inputs.get("ticket"),str)
            and NATIVE_TICKET.fullmatch(inputs["ticket"]) is not None,
            "NATIVE_TICKET_REQUIRED")
    # Existing ticket must pass the real F139 HMAC, epoch, run source/event
    # check before any candidate bytes are considered. It must be a distinct
    # native ticket; D2K and frozen historical tickets are never upcast.
    # F139 V1 HMAC signs the original ticket/lane/source/epoch ONLY.
    # Native issue identity is independently covered by the domain-separated
    # NCI04 HMAC below. Never smuggle native fields into old D2K V2 semantics.
    legacy_inputs = {**inputs, "issue_number": "", "issue_id": "",
                     "body_sha256": "", "target_package": ""}
    admit_controller_ticket(legacy_inputs)
    candidate = parse_intent(native_intent_raw, protected_main=authenticated_main_sha,
                             target_commit=authenticated_target_commit,
                             target_tree_sha=authenticated_target_tree)
    payload = _identity(inputs, issue_number, issue_id, issue_body_sha256,
                        candidate)
    require(isinstance(native_signature, str)
            and SHA256.fullmatch(native_signature) is not None,
            "NATIVE_SIGNATURE_INVALID")
    expected = sign_native_intent(inputs, candidate, issue_number=issue_number,
                                  issue_id=issue_id, issue_body_sha256=issue_body_sha256)
    require(hmac.compare_digest(expected, native_signature),
            "NATIVE_SIGNATURE_MISMATCH")
    require(candidate.target_commit == authenticated_target_commit
            and candidate.target_tree_sha == authenticated_target_tree
            and inputs["source_sha"] == authenticated_main_sha,
            "AUTHENTICATED_SOURCE_DRIFT")
    return NativeAdmission(
        inputs["ticket"], candidate.lane, inputs["source_sha"],
        int(inputs["run_id"]), inputs["os"], int(issue_number), int(issue_id),
        candidate, digest(canonical(payload)))


def receipt_from_report(admission: NativeAdmission, report: dict) -> dict:
    """Build a source-bound development receipt; no science or merge grant."""
    require(isinstance(admission, NativeAdmission) and isinstance(report, dict),
            "REPORT_FIELDS_INVALID")
    c = admission.intent
    dual_mode = c.lane == "Yggdrasil" and c.path == YGGDRASIL_G29_SOURCE
    common = {
        "schema", "intent_sha256", "qualification_key", "target_commit",
        "target_tree_sha", "candidate_file", "candidate_sha256", "lane",
        "qualification_complete", "real_code_changed_in_isolated_copy",
        "commands", "child_peak_rss_bytes", "scientific_first_use",
        "protected_holdouts_accessed", "accepted_ref_mutations",
        "paid_model_calls", "durable_controller_custody_verified",
        "unattended_controller_dispatch_verified",
    }
    fields = common | ({"dual_custody"} if dual_mode else set())
    schema = ("forge.f139.nci04.native-development-diagnostic.v2"
              if dual_mode else
              "forge.f139.nci04.native-development-diagnostic.v1")
    require(set(report) == fields and report.get("schema") == schema
            and report["intent_sha256"] == c.intent_sha256
            and report["qualification_key"] == c.qualification_key
            and report["target_commit"] == c.target_commit
            and report["target_tree_sha"] == c.target_tree_sha
            and report["candidate_file"] == c.path
            and report["candidate_sha256"] == c.after_sha256
            and report["lane"] == admission.lane
            and report["real_code_changed_in_isolated_copy"] is True
            and report["scientific_first_use"] is False
            and type(report["protected_holdouts_accessed"]) is int
            and report["protected_holdouts_accessed"] == 0
            and type(report["accepted_ref_mutations"]) is int
            and report["accepted_ref_mutations"] == 0
            and type(report["paid_model_calls"]) is int
            and report["paid_model_calls"] == 0
            and report["durable_controller_custody_verified"] is False
            and report["unattended_controller_dispatch_verified"] is False,
            "REPORT_AUTHORITY_OR_SOURCE_INVALID")
    fixed, commands = commands_for(admission.intent), report["commands"]
    require(isinstance(commands, list) and 1 <= len(commands) <= len(fixed),
            "COMMAND_SEQUENCE_INVALID")
    for actual, expected in zip(commands, fixed):
        command_fields = {"command", "outcome", "returncode", "elapsed_ms",
                          "output_sha256", "output_bytes", "excerpt"}
        if dual_mode:
            command_fields.add("test_count")
        require(isinstance(actual, dict) and set(actual) == command_fields
                and actual["command"] == list(expected)
                and actual["outcome"] in ("PASS", "TEST_FAILURE", "TIMEOUT")
                and type(actual["returncode"]) is int
                and type(actual["elapsed_ms"]) is int and actual["elapsed_ms"] >= 0
                and isinstance(actual["output_sha256"], str)
                and SHA256.fullmatch(actual["output_sha256"]) is not None
                and type(actual["output_bytes"]) is int and actual["output_bytes"] >= 0
                and isinstance(actual["excerpt"], str)
                and len(actual["excerpt"].encode("utf-8")) <= 4096
                and ((actual["outcome"] == "PASS" and actual["returncode"] == 0)
                     or (actual["outcome"] == "TIMEOUT" and actual["returncode"] == -1)
                     or (actual["outcome"] == "TEST_FAILURE" and actual["returncode"] > 0)),
                "COMMAND_EVIDENCE_INVALID")
        if dual_mode:
            require(type(actual["test_count"]) is int and actual["test_count"] >= 0
                    and (actual["outcome"] != "PASS"
                         or tuple(expected[1:4]) != ("-B", "-m", "unittest")
                         or actual["test_count"] > 0),
                    "COMMAND_TEST_COUNT_INVALID")
    complete = len(commands) == len(fixed) and all(
        x["outcome"] == "PASS" for x in commands)
    require(report["qualification_complete"] is complete
            and (complete or commands[-1]["outcome"] != "PASS"),
            "FALSE_QUALIFICATION_CLAIM")
    if dual_mode:
        dual = report["dual_custody"]
        require(isinstance(dual, dict) and set(dual) == {
            "schema", "baseline_commit", "baseline_tree_sha", "test_inventory",
            "baseline_g29", "baseline_full", "candidate_g29",
            "candidate_non_atlas_test_modules",
        } and dual["schema"] == "forge.f139.nci04.yggdrasil.g29-dual-custody.v1"
            and dual["baseline_commit"] == c.target_commit
            and dual["baseline_tree_sha"] == c.target_tree_sha
            and dual["test_inventory"] == sorted(
                (YGG_G29_ATLAS_TEST,) + YGGDRASIL_G29_TESTS)
            and dual["candidate_non_atlas_test_modules"] == list(YGGDRASIL_G29_TESTS),
            "G29_DUAL_CUSTODY_IDENTITY_INVALID")
        def argv(name):
            return ["python", "-B", "-m", "unittest", "discover",
                    "-s", "tests", "-p", name, "-v"]
        def valid_record(record, expected_argv):
            require(isinstance(record, dict) and set(record) == {
                "command", "outcome", "returncode", "elapsed_ms",
                "output_sha256", "output_bytes", "excerpt", "test_count",
            } and record["command"] == expected_argv
                and record["outcome"] == "PASS" and record["returncode"] == 0
                and type(record["elapsed_ms"]) is int and record["elapsed_ms"] >= 0
                and isinstance(record["output_sha256"], str)
                and SHA256.fullmatch(record["output_sha256"]) is not None
                and type(record["output_bytes"]) is int and record["output_bytes"] >= 0
                and isinstance(record["excerpt"], str)
                and len(record["excerpt"].encode("utf-8")) <= 4096
                and type(record["test_count"]) is int and record["test_count"] > 0,
                "G29_BASELINE_EVIDENCE_INVALID")
        valid_record(dual["baseline_g29"], argv(YGG_G29_ATLAS_TEST))
        valid_record(dual["baseline_full"], argv("test_*.py"))
        atlas = dual["candidate_g29"]
        require(isinstance(atlas, dict) and set(atlas) == {
            "command", "outcome", "returncode", "elapsed_ms", "output_sha256",
            "output_bytes", "excerpt", "test_count", "disposition", "expected_marker",
        } and atlas["command"] == argv(YGG_G29_ATLAS_TEST)
            and atlas["expected_marker"] == YGG_G29_ATLAS_MARKER + c.path
            and type(atlas["elapsed_ms"]) is int and atlas["elapsed_ms"] >= 0
            and isinstance(atlas["output_sha256"], str)
            and SHA256.fullmatch(atlas["output_sha256"]) is not None
            and type(atlas["output_bytes"]) is int and atlas["output_bytes"] >= 0
            and isinstance(atlas["excerpt"], str)
            and len(atlas["excerpt"].encode("utf-8")) <= 4096
            and type(atlas["test_count"]) is int and atlas["test_count"] > 0,
            "G29_CANDIDATE_ATLAS_EVIDENCE_INVALID")
        if atlas["disposition"] == "EXPECTED_FROZEN_ATLAS_REJECTION":
            require(atlas["outcome"] == "TEST_FAILURE"
                    and atlas["returncode"] > 0
                    and atlas["expected_marker"] in atlas["excerpt"],
                    "G29_EXPECTED_NEGATIVE_NOT_AUTHENTIC")
        elif atlas["disposition"] == "PASS":
            require(atlas["outcome"] == "PASS" and atlas["returncode"] == 0,
                    "G29_ATLAS_PASS_CLAIM_INVALID")
        else:
            raise Untrusted("F139_NCI04_G29_ATLAS_DISPOSITION_INVALID")
    raw = canonical(report)
    require(len(raw) <= MAX_RECEIPT, "REPORT_OVERSIZE")
    return {
        "schema": RECEIPT_SCHEMA,
        "ticket": admission.ticket, "lane": admission.lane,
        "source_sha": admission.source_sha,
        "issue_number": admission.issue_number, "issue_id": admission.issue_id,
        "run_id": admission.run_id, "os": admission.runner_os,
        "native_authorization_sha256": admission.authorization_sha256,
        "native_intent_sha256": c.intent_sha256,
        "qualification_key": c.qualification_key,
        "target_commit": c.target_commit, "target_tree_sha": c.target_tree_sha,
        "native_report_sha256": digest(raw), "native_qualified": complete,
        "development_only": True, "scientific_first_use_authorized": False,
        "scientific_originals_dispatched": 0, "accepted_ref_mutations": 0,
        "paid_model_calls": 0, "local_custody_verified": False,
        "controller_unattended_verified": False,
    }
