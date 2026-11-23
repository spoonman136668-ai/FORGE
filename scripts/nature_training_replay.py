"""Read-only four-arm Nature comparator for *development* receipts.

The caller independently authenticates source custody, original trial evidence,
complete negatives, scientific first-use authority and the control selection.
This pure function can only report source-unverified development diagnostics;
no synthetic or caller-authored result can qualify a scientific discovery.
"""
from __future__ import annotations

import hashlib
import json
import math
import re

SCHEMA = "forge.research.nature-dev-replay.v1"
ARMS = ("A", "B", "C", "D")  # preselected strongest control, blind, guided, no-memory
CONTROL_IDS = frozenset({"finite", "dream-rsi", "pareto", "infogain"})
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
CASE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}\Z")
FREEZE_KEYS = frozenset({
    "schema", "parent_sha", "parent_tree_sha", "protocol_sha256",
    "development_corpus_sha256", "partition", "selected_control",
    "terminal_event_ids", "case_input_sha256", "max_wall_ms",
    "max_cpu_ms", "max_peak_rss_bytes", "negative_control",
})
ROW_KEYS = frozenset({
    "terminal_event_id", "input_sha256", "plan_sha256",
    "beneficial_dev_outcome", "retention_drift_brier", "wall_ms",
    "cpu_ms", "peak_rss_bytes", "model_calls", "sealed_holdout_access",
    "scientific_first_use",
})


class DevReplayRejected(ValueError):
    """A fail-closed protocol or fairness violation."""


def _require(condition, reason):
    if not condition:
        raise DevReplayRejected(reason)


def _sha(value, regex=SHA64):
    return type(value) is str and regex.fullmatch(value) is not None


def _digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("ascii")).hexdigest()


def _freeze(raw):
    _require(type(raw) is dict and frozenset(raw) == FREEZE_KEYS, "FREEZE_FIELDS")
    _require(raw["schema"] == SCHEMA and raw["partition"] == "development",
             "PROTECTED_PARTITION")
    _require(_sha(raw["parent_sha"], SHA40) and
             _sha(raw["parent_tree_sha"], SHA40) and
             _sha(raw["protocol_sha256"]) and
             _sha(raw["development_corpus_sha256"]), "FREEZE_SOURCE_IDENTITY")
    _require(type(raw["selected_control"]) is str and
             raw["selected_control"] in CONTROL_IDS, "CONTROL_NOT_PRESELECTED")
    ids = raw["terminal_event_ids"]
    _require(type(ids) is list and 2 <= len(ids) <= 12 and
             all(type(x) is str and CASE.fullmatch(x) is not None for x in ids)
             and len(ids) == len(set(ids)), "FROZEN_EVENT_IDS")
    inputs = raw["case_input_sha256"]
    _require(type(inputs) is dict and set(inputs) == set(ids) and
             all(_sha(v) for v in inputs.values()) and
             len(set(inputs.values())) == len(ids), "FROZEN_INPUT_IDENTITIES")
    for k in ("max_wall_ms", "max_cpu_ms", "max_peak_rss_bytes"):
        _require(type(raw[k]) is int and 1 <= raw[k] <= 10**12,
                 "BUDGET_NOT_PREDECLARED")
    _require(type(raw["negative_control"]) is bool, "NEGATIVE_CONTROL_NOT_FROZEN")
    return ids


def _paired_sign_test(a, c):
    """Exact two-sided McNemar/binomial discordance diagnostic (not a CI)."""
    improved = sum(1 for x, y in zip(a, c) if not x and y)
    worsened = sum(1 for x, y in zip(a, c) if x and not y)
    total = improved + worsened
    if not total:
        return 1.0
    smallest = min(improved, worsened)
    return min(1.0, 2.0 * sum(math.comb(total, k) for k in range(smallest + 1))
               / (2 ** total))


def evaluate(freeze, rows_by_arm):
    """Equal-information, equal-attempt, within-5%-cost training-only diagnostics.

    Receipts are untrusted caller inputs, even with SHA-256 identities. This code
    never reads files, sends requests, executes experiments, signs approvals, or
    selects a control after seeing outcomes. It does not make a SCIENTIFIC_PASS.
    """
    ids = _freeze(freeze)
    _require(type(rows_by_arm) is dict and set(rows_by_arm) == set(ARMS),
             "FOUR_ARMS_REQUIRED")
    summaries = {}
    outcomes = {}
    for arm in ARMS:
        rows = rows_by_arm[arm]
        _require(type(rows) is list and len(rows) == len(ids),
                 "EQUAL_EVALUATION_COUNT")
        _require(all(type(row) is dict and frozenset(row) == ROW_KEYS
                     for row in rows), "ROW_FIELDS")
        _require([row["terminal_event_id"] for row in rows] == ids,
                 "EVENT_ORDER_OR_INFORMATION_DRIFT")
        used_plans = set()
        wall = cpu = 0
        successes = 0
        max_drift = -1.0
        peak = 0
        for row in rows:
            _require(row["input_sha256"] ==
                     freeze["case_input_sha256"][row["terminal_event_id"]],
                     "HOLDOUT_OR_INPUT_LEAKAGE")
            plan = row["plan_sha256"]
            _require(_sha(plan), "PLAN_IDENTITY")
            _require(plan not in used_plans, "REPLAYED_PLAN_WITHIN_ARM")
            used_plans.add(plan)
            _require(type(row["beneficial_dev_outcome"]) is bool and
                     type(row["retention_drift_brier"]) in (float, int)
                     and math.isfinite(row["retention_drift_brier"]) and
                     -1 <= row["retention_drift_brier"] <= 1, "OUTCOME_FIELDS")
            _require(type(row["wall_ms"]) is int and row["wall_ms"] > 0 and
                     type(row["cpu_ms"]) is int and row["cpu_ms"] > 0 and
                     type(row["peak_rss_bytes"]) is int and
                     row["peak_rss_bytes"] > 0, "UNMEASURED_RESOURCE")
            _require(row["model_calls"] == 0 and
                     type(row["model_calls"]) is int and
                     row["sealed_holdout_access"] is False and
                     row["scientific_first_use"] is False,
                     "UNAUTHORIZED_MODEL_OR_SCIENCE_ACCESS")
            wall += row["wall_ms"]
            cpu += row["cpu_ms"]
            peak = max(peak, row["peak_rss_bytes"])
            max_drift = max(max_drift, row["retention_drift_brier"])
            successes += int(row["beneficial_dev_outcome"])
        _require(wall <= freeze["max_wall_ms"] and
                 cpu <= freeze["max_cpu_ms"] and
                 peak <= freeze["max_peak_rss_bytes"], "EXCEEDED_RESOURCE_BUDGET")
        summaries[arm] = {"beneficial_training_labels": successes,
                          "attempts": len(ids), "wall_ms": wall,
                          "cpu_ms": cpu, "peak_rss_bytes": peak,
                          "max_retention_drift_brier": max_drift}
        outcomes[arm] = [x["beneficial_dev_outcome"] for x in rows]
    for budget in ("wall_ms", "cpu_ms"):
        totals = [summaries[x][budget] for x in ARMS]
        _require(max(totals) - min(totals) <= max(totals) * 0.05,
                 "UNEQUAL_WHOLE_PROCESS_COST")
    if freeze["negative_control"]:
        _require(all(not any(outcomes[x]) for x in ARMS),
                 "NEGATIVE_CONTROL_FALSE_DISCOVERY")
    a, c = summaries["A"]["beneficial_training_labels"], summaries["C"]["beneficial_training_labels"]
    relative = None if a == 0 else (c - a) / a
    retention_ok = all(summaries[x]["max_retention_drift_brier"] <= 0.02
                       for x in ARMS)
    result = {"schema": SCHEMA, "classification": "SOURCE_UNVERIFIED_DEV_DIAGNOSTIC",
              "frozen_sha256": _digest(freeze),
              "development_corpus_sha256": freeze["development_corpus_sha256"],
              "selected_control": freeze["selected_control"],
              "arms": summaries, "candidate_vs_control_relative": relative,
              "paired_two_sided_sign_p": _paired_sign_test(outcomes["A"], outcomes["C"]),
              "retention_within_proposed_limit": retention_ok,
              "comparison_source_authenticated": False,
              "original_terminal_receipts_authenticated": False,
              "scientific_first_use": False, "scientific_gain_verified": False,
              "deployment_authorized": False, "paid_api_calls": 0,
              "model_calls": 0, "protected_holdouts_accessed": 0}
    # Even a very favorable source-unverified synthetic comparison is not science.
    result["diagnostic"] = ("NO_CONTROL_SUCCESSES" if relative is None else
                            "RETENTION_VETO" if not retention_ok else
                            "TRAINING_LABELS_ONLY_NOT_SCIENCE")
    return result
