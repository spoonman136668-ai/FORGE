"""ITD-01 common *development* evidence comparator; no science authority.

Wingless and Yggdrasil retain independent architectures and training. This
module makes no GitHub calls, runs no candidate code, and has no write path.
Source birth and independent first-use require EXTERNAL authenticated custody;
self-reported hashes and times can never establish that authority.
"""
from __future__ import annotations

import datetime as dt
import json
import re

PROTOCOL = "itd01.external-development-protocol.v1"
RESULT = "itd01.external-development-measurement.v1"
LANES = ("Wingless", "Yggdrasil")
CONTROLS = ("trained_bayesian", "trained_recurrent", "trained_symbolic")
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
STUDY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{2,79}\Z")
METRICS = frozenset({
    "correct", "total", "hard_false_positives", "all_in_cpu_ms",
    "peak_rss_bytes", "io_bytes", "resident_memory_bytes",
    "communication_bytes", "restart_cost_ms",
})
P_FIELDS = frozenset({
    "schema", "study_id", "lane", "target_source_commit",
    "preregistration_sha256", "preregistered_utc", "source_birth_utc",
    "external_contract_sha256", "training_cohort_sha256",
    "development_cohort_sha256", "controls",
    "scientific_first_use_authorized", "paid_model_calls",
})
R_FIELDS = frozenset({
    "schema", "study_id", "lane", "target_source_commit",
    "external_contract_sha256", "training_cohort_sha256",
    "development_cohort_sha256", "measured_utc", "arms",
    "protected_holdouts_accessed", "scientific_first_use",
    "paid_model_calls", "cross_lane_state_shared",
})
A_FIELDS = frozenset({"name", "fully_trained", "training_cohort_sha256",
                      "development_cohort_sha256", "metrics"})


class EvidenceRejected(ValueError):
    pass


def require(ok: bool, reason: str):
    if not ok:
        raise EvidenceRejected("ITD01_" + reason)


def read_json(raw: bytes):
    require(isinstance(raw, bytes) and 0 < len(raw) <= 20000, "INPUT_SIZE")
    def unique(pairs):
        value = {}
        for k, v in pairs:
            require(k not in value, "DUPLICATE_JSON_KEY")
            value[k] = v
        return value
    try:
        return json.loads(raw, object_pairs_hook=unique)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise EvidenceRejected("ITD01_JSON_INVALID") from exc


def utc(value):
    require(isinstance(value, str) and value.endswith("Z")
            and len(value) < 42, "UTC_FORMAT")
    try:
        result = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise EvidenceRejected("ITD01_UTC_FORMAT") from exc
    require(result.utcoffset() == dt.timedelta(0), "UTC_TIMEZONE")
    return result


def digest(value):
    return isinstance(value, str) and SHA64.fullmatch(value) is not None


def validate_protocol(p):
    require(type(p) is dict and set(p) == P_FIELDS, "PROTOCOL_FIELDS")
    require(p["schema"] == PROTOCOL, "PROTOCOL_SCHEMA")
    require(isinstance(p["study_id"], str)
            and STUDY.fullmatch(p["study_id"]) is not None, "STUDY_ID")
    require(p["lane"] in LANES and type(p["lane"]) is str, "LANE")
    require(isinstance(p["target_source_commit"], str)
            and SHA40.fullmatch(p["target_source_commit"]) is not None,
            "SOURCE_COMMIT")
    for key in ("preregistration_sha256", "external_contract_sha256",
                "training_cohort_sha256", "development_cohort_sha256"):
        require(digest(p[key]), "UNVERIFIED_" + key.upper())
    require(len({p["training_cohort_sha256"],
                 p["development_cohort_sha256"]}) == 2, "COHORT_REUSE")
    require(utc(p["preregistered_utc"]) < utc(p["source_birth_utc"]),
            "SOURCE_PRECEDES_PREREGISTRATION")
    require(type(p["controls"]) is list
            and p["controls"] == list(CONTROLS), "MATCHED_CONTROL_INVENTORY")
    require(p["scientific_first_use_authorized"] is False
            and type(p["paid_model_calls"]) is int and p["paid_model_calls"] == 0,
            "UNAUTHORIZED_SCIENCE_OR_MODEL")
    return p


def validate_report(p, r):
    validate_protocol(p)
    require(type(r) is dict and set(r) == R_FIELDS and
            r["schema"] == RESULT, "RESULT_FIELDS_OR_SCHEMA")
    for key in ("study_id", "lane", "target_source_commit",
                "external_contract_sha256", "training_cohort_sha256",
                "development_cohort_sha256"):
        require(r[key] == p[key], "RESULT_IDENTITY_DRIFT_" + key.upper())
    require(utc(r["measured_utc"]) > utc(p["source_birth_utc"]),
            "RESULT_BEFORE_SOURCE_BIRTH")
    require(type(r["protected_holdouts_accessed"]) is int
            and r["protected_holdouts_accessed"] == 0
            and r["scientific_first_use"] is False
            and type(r["paid_model_calls"]) is int
            and r["paid_model_calls"] == 0
            and r["cross_lane_state_shared"] is False,
            "RESULT_AUTHORITY_ESCALATION")
    require(type(r["arms"]) is list
            and len(r["arms"]) == len(CONTROLS) + 1, "ARM_COUNT")
    expected = ("candidate",) + CONTROLS
    require([arm.get("name") if type(arm) is dict else None
             for arm in r["arms"]] == list(expected), "ARM_INVENTORY")
    total = None
    for arm in r["arms"]:
        require(type(arm) is dict and set(arm) == A_FIELDS
                and arm["fully_trained"] is True, "UNTRAINED_OR_INVALID_ARM")
        for key in ("training_cohort_sha256", "development_cohort_sha256"):
            require(arm[key] == p[key], "UNEQUAL_INFORMATION_" + key.upper())
        m = arm["metrics"]
        require(type(m) is dict and set(m) == METRICS
                and all(type(v) is int for v in m.values()), "METRICS_INVALID")
        require(m["total"] > 0 and 0 <= m["correct"] <= m["total"]
                and 0 <= m["hard_false_positives"] <= m["total"]
                and all(m[k] >= 0 for k in METRICS - {
                    "total", "correct", "hard_false_positives"})
                and m["peak_rss_bytes"] > 0 and m["resident_memory_bytes"] > 0,
                "METRICS_OUT_OF_BOUNDS")
        if total is None:
            total = m["total"]
        require(m["total"] == total, "UNMATCHED_EVALUATION_DENOMINATOR")
    return r


def compare_development(p, r):
    """One objective score, not independent verification or promotion.

    Higher development accuracy and no greater *each* all-in resource dimension
    than the strongest trained comparator are necessary, not sufficient, for a
    positive development signal. A zero-FP policy is applied to the candidate.
    All evidence still requires separate GitHub/provider and first-use custody.
    """
    validate_report(p, r)
    candidate = r["arms"][0]["metrics"]
    references = [arm["metrics"] for arm in r["arms"][1:]]
    best = min(references, key=lambda m: (-m["correct"],
                                         m["all_in_cpu_ms"],
                                         m["peak_rss_bytes"]))
    all_costs = ("all_in_cpu_ms", "peak_rss_bytes", "io_bytes",
                 "resident_memory_bytes", "communication_bytes",
                 "restart_cost_ms")
    score_gain = candidate["correct"] - best["correct"]
    resource_parity = all(candidate[k] <= best[k] for k in all_costs)
    advantage = (score_gain > 0 and candidate["hard_false_positives"] == 0
                 and resource_parity)
    return {
        "schema": "itd01.external-development-audit.v1",
        "study_id": p["study_id"],
        "lane": p["lane"],
        "gain_correct_vs_best_trained_control": score_gain,
        "candidate_zero_hard_false_positives":
            candidate["hard_false_positives"] == 0,
        "all_in_resource_nonregression": resource_parity,
        "disposition": ("DEVELOPMENT_SIGNAL_INDEPENDENT_REVIEW_REQUIRED"
                        if advantage else "NEGATIVE_OR_INCONCLUSIVE_RETAIN"),
        "provider_source_birth_authenticated": False,
        "independent_first_use_qualified": False,
        "scientific_acceptance": False,
        "controller_or_scheduler_created": False,
        "automated_task_dispatch": False,
        "accepted_ref_mutations": 0,
    }
