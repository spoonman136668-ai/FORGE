"""F139-adjacent, source-only efficient-language screening identity.

This module does not execute models, acquire cohorts, trust provider receipts,
dispatch work, authenticate scientific first-use, or read private custody.
"""
from __future__ import annotations

import hashlib
import json
import math
import re

SCHEMA = "forge.language-screen.preparation-only.v1"
RECEIPT_SCHEMA = "forge.language-screen.focused-receipt-advisory.v1"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
FIELDS = frozenset({
    "schema", "mode", "candidate", "comparator", "data",
    "protocol_sha256", "environment_sha256", "meter_source_sha256",
    "focused_suite_sha256", "budgets", "authority"
})
MECHANISMS = frozenset({
    "latent-state-to-language", "hierarchical-concept-to-text",
    "adaptive-character-word-phrase-chunk", "parallel-verify-repair",
    "reusable-compositional-linguistic-structures",
})
COMPARATORS = frozenset({"recurrent", "state-space", "transformer",
                         "non-autoregressive", "symbolic"})
MEASUREMENTS = (
    "language_fidelity", "task_quality", "training_flops",
    "inference_flops", "sequential_latency_seconds",
    "peak_memory_bytes", "storage_bytes", "energy_joules",
)


class Refused(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise Refused("ELANG_" + reason)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _bad_constant(_value):
    raise Refused("ELANG_NONFINITE_JSON")


def parse(raw):
    """Strict bounded canonical-input decoder; no duplicate keys or NaN."""
    need(type(raw) is bytes and 0 < len(raw) <= 16384, "INPUT_SIZE")
    try:
        result = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique,
                            parse_constant=_bad_constant)
    except Refused:
        raise
    except (UnicodeError, ValueError, TypeError) as exc:
        raise Refused("ELANG_INVALID_JSON") from exc
    need(type(result) is dict, "NOT_OBJECT")
    return result


def canonical(value):
    try:
        data = json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise Refused("ELANG_NONCANONICAL_PAYLOAD") from exc
    need(0 < len(data) <= 16384, "CANONICAL_SIZE")
    return data


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def _hex(value, width=64):
    return type(value) is str and bool((SHA64 if width == 64 else SHA40).fullmatch(value))


def _object(value, keys, code):
    need(type(value) is dict and set(value) == set(keys), code)


def validate(contract):
    """A complete frozen development identity, never an execution permit."""
    _object(contract, FIELDS, "FIELDS")
    need(contract["schema"] == SCHEMA and contract["mode"] == "prepare_only",
         "PREPARATION_SCOPE")
    c = contract["candidate"]
    _object(c, ("mechanism", "commit_sha", "tree_sha", "config_sha256"),
            "CANDIDATE_FIELDS")
    need(type(c["mechanism"]) is str and c["mechanism"] in MECHANISMS
         and _hex(c["commit_sha"], 40)
         and _hex(c["tree_sha"], 40) and _hex(c["config_sha256"]),
         "CANDIDATE_IDENTITY")
    comparator = contract["comparator"]
    _object(comparator, ("family", "commit_sha", "tree_sha", "config_sha256"),
            "COMPARATOR_FIELDS")
    need(type(comparator["family"]) is str
         and comparator["family"] in COMPARATORS
         and _hex(comparator["commit_sha"], 40)
         and _hex(comparator["tree_sha"], 40)
         and _hex(comparator["config_sha256"]), "COMPARATOR_IDENTITY")
    datasets = contract["data"]
    _object(datasets, ("train_sha256", "development_sha256", "holdout_sha256"),
            "DATA_FIELDS")
    need(all(_hex(v) for v in datasets.values()) and
         len(set(datasets.values())) == 3, "SPLITS_UNBOUND_OR_OVERLAPPING")
    for field in ("protocol_sha256", "environment_sha256",
                  "meter_source_sha256", "focused_suite_sha256"):
        need(_hex(contract[field]), "IDENTITY_" + field.upper())
    b = contract["budgets"]
    _object(b, ("max_training_cpu_seconds", "max_inference_cpu_seconds",
                "max_peak_memory_bytes", "max_trials"), "BUDGET_FIELDS")
    need(all(type(b[field]) is int and b[field] > 0 for field in b),
         "BUDGET_NOT_BOUNDED_INTEGER")
    need(b["max_trials"] <= 4 and b["max_training_cpu_seconds"] <= 600
         and b["max_inference_cpu_seconds"] <= 300
         and b["max_peak_memory_bytes"] <= 4 * 1024**3,
         "BUDGET_EXCEEDS_DEVELOPMENT_SCREEN")
    authority = contract["authority"]
    _object(authority, ("science_admitted", "first_use", "dispatch",
                        "new_controller", "paid_api_calls"), "AUTHORITY_FIELDS")
    need(authority == {"science_admitted": False, "first_use": False,
                       "dispatch": False, "new_controller": False,
                       "paid_api_calls": 0}, "AUTHORITY_ESCALATION")
    canonical(contract)
    return contract


def candidate_key(contract):
    """Address the whole candidate/comparator/data/environment/test bundle."""
    return sha256(canonical(validate(contract)))


def inspect_focused_receipt(contract, receipt):
    """Self-consistency ONLY; an external qualified custodian must verify it.

    Even an identity-matching receipt cannot certify a GitHub run, scientific
    outcome, cached test PASS, or permission to skip any required regression.
    """
    fingerprint = candidate_key(contract)
    _object(receipt, ("schema", "candidate_key", "suite_sha256",
                      "environment_sha256", "output_sha256",
                      "test_count", "status", "scientific_first_use"),
            "RECEIPT_FIELDS")
    need(receipt["schema"] == RECEIPT_SCHEMA
         and all(_hex(receipt[field]) for field in
                 ("candidate_key", "suite_sha256", "environment_sha256",
                  "output_sha256"))
         and type(receipt["test_count"]) is int
         and receipt["test_count"] > 0
         and receipt["status"] == "PASS"
         and receipt["scientific_first_use"] is False,
         "RECEIPT_MALFORMED_OR_UNSAFE")
    need(receipt["candidate_key"] == fingerprint
         and receipt["suite_sha256"] == contract["focused_suite_sha256"]
         and receipt["environment_sha256"] == contract["environment_sha256"],
         "STALE_FOCUSED_RECEIPT_IDENTITY")
    return {
        "schema": "forge.language-screen.cache-candidate-inspection.v1",
        "candidate_key": fingerprint,
        "exact_identity_match": True,
        "provider_custody_independently_verified": False,
        "cached_qualification_authorized": False,
        "scientific_first_use": False,
        "disposition": "EXTERNAL_PROVIDER_VERIFICATION_REQUIRED",
    }


def measurement_coverage(metrics):
    """Measurement presence/validity, not a quality or efficiency result."""
    _object(metrics, MEASUREMENTS, "MEASUREMENT_FIELDS")
    measured = []
    unavailable = []
    for name in MEASUREMENTS:
        value = metrics[name]
        if value is None:
            unavailable.append(name)
            continue
        need(type(value) in (int, float) and math.isfinite(value)
             and value >= 0, "MEASUREMENT_INVALID_" + name.upper())
        if name in ("language_fidelity", "task_quality"):
            need(value <= 1, "QUALITY_OUT_OF_RANGE")
        if name in ("peak_memory_bytes", "storage_bytes",
                    "training_flops", "inference_flops"):
            need(type(value) is int, "MEASUREMENT_NOT_INTEGER_" + name.upper())
        measured.append(name)
    return {"schema": "forge.language-screen.measurement-coverage.v1",
            "measured": measured, "unavailable": unavailable,
            "completeness": len(measured) == len(MEASUREMENTS),
            "quality_or_scientific_gain_claimed": False,
            "scientific_first_use": False}
