"""Legacy finite Nature-inspired research-plan prototype.

Superseded for compositional exploration by scripts.nature_compositional_brancher.
Retained to preserve the original fixed-recipe comparison and its source history.
This is advisory-only and not an F139 owner hook.
The caller must independently verify original terminal receipts, source/tree
custody, complete historical negatives, and their training-only status. A
receipt digest here is an opaque identity, NOT authentication or trial authority.
This module never reads a repo, runs generated code, admits science or dispatches.
A new plan SHA does not establish scientific/mechanism novelty.
"""
from __future__ import annotations

import hashlib
import json
import re

SCHEMA = "forge.research.nature-failure-guided-plan.v1"
EVENT_SCHEMA = "forge.research.verified-development-negative-ref.v1"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
EVENT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{7,127}\Z")
EVENT_FIELDS = frozenset({"schema", "event_id", "lane", "parent_sha", "parent_tree_sha",
                          "evidence_sha256", "receipt_sha256", "failure_class", "partition",
                          "terminal_disposition"})
LANES = frozenset({"Wingless", "Yggdrasil", "TTT-Hybrid"})
# Fixed design recipes, not a learned generator. Distinct hashes need independent
# semantic review before they can be counted as genuinely new hypotheses.
RECIPES = {
    "sparse-evidence-overconfidence": (
        (("local-reliability-calibration",),
         "Does calibrated local reliability avoid overconfident sparse decisions?",
         "Lower weak-support error without reducing verified causal coverage.",
         "Worse unfamiliar-transfer error or excessive abstention.",
         "Unmodified parent and support-matched uniform calibration."),
        (("counterfactual-support-check",),
         "Does counterfactual support checking improve sparse-action selection?",
         "Fewer unsupported action choices at fixed action opportunity.",
         "No causal benefit at matched intervention cost.",
         "Identical compute with support labels masked."),
        (("local-reliability-calibration", "cold-retention-guard"),
         "Can reliability gating preserve cold competence after interference?",
         "Lower error while familiar retention remains within frozen tolerance.",
         "Familiar Brier drift exceeds the frozen permitted limit.",
         "The same gate with the retention guard removed."),
    ),
    "nonstationary-reversal": (
        (("change-point-evidence-quarantine",),
         "Can suspected reversals be isolated without deleting prior knowledge?",
         "Earlier response to genuine reversals at matched stationary accuracy.",
         "Spurious shifts erase stable learned relationships.",
         "Equivalent recency window without an explicit quarantine."),
        (("multi-timescale-local-evidence",),
         "Can multiple local timescales improve adaptation to regime changes?",
         "Better reversals without a greater memory or action budget.",
         "Retention/interference deteriorates versus the strongest control.",
         "One timescale under the same memory capacity."),
        (("change-point-evidence-quarantine", "cold-retention-guard"),
         "Can a quarantine preserve a cold checkpoint through repeated reversals?",
         "Improved recovery on unfamiliar switches without familiar drift.",
         "Checkpoint recovery degrades or memory budget is exceeded.",
         "Quarantine with no independent retention guard."),
    ),
    "context-interference": (
        (("causal-context-boundary-test",),
         "Does explicit context-boundary testing reduce interference?",
         "Less cross-context contamination under equal learned-state capacity.",
         "Failed transfer or new context aliases.",
         "Randomized boundaries under the same storage budget."),
        (("sparse-context-gated-update",),
         "Do sparse local updates retain knowledge across contexts?",
         "Improved cold retention and action prediction at matched compute.",
         "Unfamiliar contexts cannot reuse valid causal structure.",
         "Ungated updates with the same compute and memory."),
        (("causal-context-boundary-test", "cross-context-transfer-probe"),
         "Can context protection coexist with unfamiliar causal transfer?",
         "Retention improves without reducing measured transfer.",
         "Any apparent gain disappears on held-out unfamiliar contexts.",
         "Boundary test without the transfer probe."),
    ),
}


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii")


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _validate_event(event):
    if type(event) is not dict or frozenset(event) != EVENT_FIELDS:
        raise ValueError("NATURE_EVENT_FIELDS_INVALID")
    if (event["schema"] != EVENT_SCHEMA or
            type(event["event_id"]) is not str or not EVENT_ID.fullmatch(event["event_id"]) or
            type(event["lane"]) is not str or event["lane"] not in LANES or
            any(type(event[key]) is not str or not regex.fullmatch(event[key])
                for key, regex in (("parent_sha", SHA40), ("parent_tree_sha", SHA40),
                                   ("evidence_sha256", SHA64), ("receipt_sha256", SHA64))) or
            event["partition"] != "development" or
            event["terminal_disposition"] != "VERIFIED_TERMINAL_NEGATIVE" or
            type(event["failure_class"]) is not str or
            len(event["failure_class"]) > 80):
        raise ValueError("NATURE_EVENT_NOT_ELIGIBLE")
    return event


def _ineligible(reason):
    return {"schema": SCHEMA, "disposition": reason, "plans": [],
            "scientific_first_use": False, "dispatch_authorized": False,
            "accepted_ref_mutations": 0, "model_calls": 0, "paid_api_calls": 0,
            "novelty_verified": False, "scientific_gain_verified": False}


def propose(event, *, historical_negatives, consumed_mechanism_sha256):
    """Emit up to 3 bounded research plans for one *caller-verified* new event.

    All inputs must be exact frozen snapshots prepared by an independent owner.
    Historical negatives may cover other lanes, and are never mutated. Missing
    provenance/unknown class/exhaustion produce NO plans; no code is generated.
    There is deliberately no I/O, callback, external model, clock or randomness.
    """
    if event is None:
        return _ineligible("NO_NEW_HYPOTHESIS_SOURCE")
    _validate_event(event)
    if (type(historical_negatives) not in (tuple, list) or
            len(historical_negatives) > 4096 or
            type(consumed_mechanism_sha256) not in (tuple, list) or
            len(consumed_mechanism_sha256) > 4096):
        raise ValueError("NATURE_HISTORY_BOUND_INVALID")
    ids, evidences, receipts = set(), set(), set()
    for old in historical_negatives:
        _validate_event(old)
        for seen, key in ((ids, "event_id"), (evidences, "evidence_sha256"),
                          (receipts, "receipt_sha256")):
            if old[key] in seen:
                raise ValueError("NATURE_INCOMPLETE_OR_DUPLICATE_HISTORY")
            seen.add(old[key])
    if (event["event_id"] in ids or event["evidence_sha256"] in evidences or
            event["receipt_sha256"] in receipts):
        return _ineligible("DUPLICATE_OR_RELABELED_EVENT")
    if any(type(key) is not str or not SHA64.fullmatch(key)
           for key in consumed_mechanism_sha256):
        raise ValueError("NATURE_CONSUMED_MECHANISM_INVALID")
    recipes = RECIPES.get(event["failure_class"])
    if recipes is None:
        return _ineligible("NO_NEW_HYPOTHESIS_SOURCE")
    used = set(consumed_mechanism_sha256)
    output = []
    for mechanism, question, prediction, failure, ablation in recipes:
        # Mechanism identity intentionally excludes incidental event prose, IDs
        # and timestamps; changing a receipt or parent cannot reset consumption.
        mechanism_sha = _digest({"lane": event["lane"], "structure": mechanism})
        if mechanism_sha in used:
            continue
        used.add(mechanism_sha)
        plan = {"schema": SCHEMA, "classification": "UNTESTED_ADVISORY_ONLY",
                "lane": event["lane"], "parent_sha": event["parent_sha"],
                "parent_tree_sha": event["parent_tree_sha"],
                "origin_event_id": event["event_id"],
                "origin_evidence_sha256": event["evidence_sha256"],
                "origin_receipt_sha256": event["receipt_sha256"],
                "failure_class": event["failure_class"],
                "mechanism_structure": list(mechanism),
                "mechanism_sha256": mechanism_sha,
                "depth": len(mechanism), "question": question,
                "counterfactual_prediction": prediction,
                "failure_condition": failure, "ablation": ablation,
                "scientific_first_use": False, "dispatch_authorized": False,
                "novelty_verified": False, "scientific_gain_verified": False}
        plan["plan_sha256"] = _digest(plan)
        output.append(plan)
    if not output:
        return _ineligible("MECHANISMS_ALREADY_CONSUMED")
    result = _ineligible("UNTESTED_ADVISORY_PLANS")
    result["plans"] = output
    return result
