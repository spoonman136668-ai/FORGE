"""Development-only prospective assignment envelope validation.

This validator is deliberately non-authorizing. A valid envelope does not prove
independent randomization, honest timestamps, or scientific improvement.
It never reads or mutates the original F139 owner ledger.
"""
from __future__ import annotations

import hashlib
import json
import re

SCHEMA = "forge.f139.prospective-assignment.v1"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
FIELDS = frozenset({
    "schema", "lane", "ticket", "owner_source_sha", "candidate_sha256",
    "eligible_candidate_sha256", "policy_sha256", "selection_mode",
    "selection_probability_bp", "assignment_event_sha256",
    "decision_utc", "outcome_available_at_decision",
})
MODES = frozenset({"DETERMINISTIC", "RANDOMIZED_CLAIM"})


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_assignment(record, *, expected_ticket, expected_source_sha,
                        expected_candidate_sha256, expected_eligible_hashes):
    """Check internal consistency; never confer provenance or authorization."""
    if not isinstance(record, dict) or set(record) != FIELDS:
        raise ValueError("F139_PROSPECTIVE_ASSIGNMENT_FIELDS")
    for field in ("owner_source_sha", "candidate_sha256",
                  "policy_sha256", "assignment_event_sha256"):
        if not isinstance(record[field], str) or not HEX64.fullmatch(record[field]):
            raise ValueError("F139_PROSPECTIVE_ASSIGNMENT_DIGEST")
    hashes = record["eligible_candidate_sha256"]
    if (not isinstance(hashes, list) or not hashes or
            any(not isinstance(h, str) or not HEX64.fullmatch(h) for h in hashes) or
            hashes != sorted(set(hashes))):
        raise ValueError("F139_PROSPECTIVE_ASSIGNMENT_SLATE")
    if (record["schema"] != SCHEMA or record["lane"] not in ("Wingless", "Yggdrasil")
            or not isinstance(record["ticket"], str) or not record["ticket"]
            or record["ticket"] != expected_ticket
            or record["owner_source_sha"] != expected_source_sha
            or record["candidate_sha256"] != expected_candidate_sha256
            or hashes != sorted(set(expected_eligible_hashes))
            or record["candidate_sha256"] not in hashes):
        raise ValueError("F139_PROSPECTIVE_ASSIGNMENT_IDENTITY")
    mode = record["selection_mode"]
    probability = record["selection_probability_bp"]
    if (mode not in MODES or type(probability) is not int or
            not 1 <= probability <= 10000 or
            (mode == "DETERMINISTIC" and probability != 10000)):
        raise ValueError("F139_PROSPECTIVE_ASSIGNMENT_POLICY")
    timestamp = record["decision_utc"]
    if (not isinstance(timestamp, str) or
            re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", timestamp) is None):
        raise ValueError("F139_PROSPECTIVE_ASSIGNMENT_TIMESTAMP")
    if record["outcome_available_at_decision"] is not False:
        raise ValueError("F139_PROSPECTIVE_ASSIGNMENT_RETROSPECTIVE")
    return {
        "schema": "forge.f139.prospective-assignment-review.v1",
        "assignment_sha256": sha256(canonical(record)),
        "mode": "UNTRUSTED_DECISION_CLAIMS_ONLY",
        "internal_consistency": True,
        "independent_randomization_proven": False,
        "decision_time_proven": False,
        "scientific_authorized": False,
    }
