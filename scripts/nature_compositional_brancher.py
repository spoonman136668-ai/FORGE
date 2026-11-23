"""Bounded compositional failure-guided mechanism search (advisory only).

This is a deterministic search over a typed mechanism grammar, not an LLM,
unconstrained invention engine, executable-code generator, or science authority.
The caller must independently authenticate source/terminal evidence and the
completeness of negative history. Structural hashes are identities, not proof
of semantic novelty. The module performs no I/O, network, model calls or writes.
"""
from __future__ import annotations

import hashlib
import json
import re

SCHEMA = "forge.research.compositional-branch-plan.v1"
EVENT_SCHEMA = "forge.research.compositional-development-negative.v1"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
EVENT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{7,127}\Z")
LANES = frozenset({"Wingless", "Yggdrasil", "TTT-Hybrid"})
SIGNALS = frozenset({
    "sparse-evidence", "causal-support-gap", "nonstationarity",
    "retention-loss", "context-interference", "saturation-boundary",
})
EVENT_FIELDS = frozenset({
    "schema", "event_id", "lane", "parent_sha", "parent_tree_sha",
    "evidence_sha256", "receipt_sha256", "observed_signals", "partition",
    "terminal_disposition",
})
MAX_HISTORY = 4096
MAX_EXPANSIONS = 64
MAX_DEPTH = 3
BEAM_WIDTH = 12
MAX_OUTPUTS = 24

# Typed primitives form a small compositional grammar. Each primitive has
# explicit input/output tokens, target failure dimensions and falsifiable claims.
# New hypotheses arise from runtime compositions and dependency edges, not a
# prewritten recipe table. The vocabulary remains finite and explicitly limited.
PRIMITIVES = {
    "support_calibration": {
        "phase": 0, "role": "evidence-estimation",
        "reads": ("support_counts", "prediction_errors"),
        "writes": ("calibrated_confidence",),
        "targets": ("sparse-evidence", "causal-support-gap"),
        "claim": "Local confidence calibration should distinguish weak support from robust evidence.",
        "prediction": "Weakly supported choices become less frequent while strong supported choices remain available.",
        "falsifier": "The same calibrated gate suppresses valid rare evidence or fails to reduce unsupported choices.",
    },
    "counterfactual_probe": {
        "phase": 0, "role": "causal-diagnosis",
        "reads": ("action_outcomes", "prediction_errors"),
        "writes": ("counterfactual_support",),
        "targets": ("causal-support-gap",),
        "claim": "Counterfactual outcome contrasts should expose unsupported action-effect assumptions.",
        "prediction": "Action choices become more accurate on interventions that distinguish competing causes.",
        "falsifier": "Observed improvement vanishes under matched intervention cost or action opportunity.",
    },
    "change_point_partition": {
        "phase": 0, "role": "regime-diagnosis",
        "reads": ("outcome_sequence",),
        "writes": ("regime_partition",),
        "targets": ("nonstationarity",),
        "claim": "Local change-point evidence should separate regime-specific observations from stable history.",
        "prediction": "Reversal adaptation improves without treating stationary fluctuations as regime changes.",
        "falsifier": "False change points partition stationary data and reduce retained competence.",
    },
    "multi_timescale_memory": {
        "phase": 1, "role": "temporal-representation",
        "reads": ("outcome_sequence", "memory_state"),
        "writes": ("temporal_context",),
        "targets": ("nonstationarity", "retention-loss"),
        "claim": "Separating short- and long-timescale evidence should preserve stable knowledge while exposing recent shifts.",
        "prediction": "The learner adapts to reversals while retaining prior knowledge through cold restore.",
        "falsifier": "Stationary retention worsens or recent evidence overwrites recoverable long-term structure.",
    },
    "context_partition": {
        "phase": 1, "role": "context-representation",
        "reads": ("context_features",),
        "writes": ("context_partition",),
        "targets": ("context-interference", "causal-support-gap"),
        "claim": "Context-local state separation should prevent evidence from unrelated contexts being conflated.",
        "prediction": "Cross-context contamination falls without blocking transfer of genuinely shared causes.",
        "falsifier": "A valid causal relationship fails to transfer to an unfamiliar but equivalent context.",
    },
    "confidence_gated_update": {
        "phase": 2, "role": "plasticity-control",
        "reads": ("calibrated_confidence",),
        "writes": ("sparse_update_policy",),
        "targets": ("sparse-evidence", "retention-loss", "context-interference"),
        "claim": "Updates gated by calibrated support should reduce weak-evidence overwrites.",
        "prediction": "Retention and interference improve while high-confidence new evidence can still modify state.",
        "falsifier": "The gate blocks valid new causal learning or only appears beneficial by reducing update opportunities.",
    },
    "regime_gated_consolidation": {
        "phase": 2, "role": "memory-consolidation",
        "reads": ("regime_partition", "temporal_context"),
        "writes": ("regime_aware_consolidation",),
        "targets": ("nonstationarity", "retention-loss"),
        "claim": "Consolidation conditioned on regime boundaries and temporal context should protect stable knowledge from transient reversals.",
        "prediction": "Cold recovery after regime changes improves at fixed memory capacity.",
        "falsifier": "The consolidation gate preserves obsolete rules or exceeds memory cost.",
    },
    "context_scoped_update": {
        "phase": 2, "role": "plasticity-control",
        "reads": ("context_partition", "calibrated_confidence"),
        "writes": ("context_scoped_plasticity",),
        "targets": ("context-interference", "sparse-evidence"),
        "claim": "Confidence-gated writes scoped to learned context partitions should reduce cross-context overwrites.",
        "prediction": "Interference falls while matched causal transfer remains intact.",
        "falsifier": "The partition causes context fragmentation or suppresses valid cross-context reuse.",
    },
    "saturation_invariant_guard": {
        "phase": 0, "role": "counter-invariant",
        "reads": ("support_counts",),
        "writes": ("monotonic_lifetime_counts",),
        "targets": ("saturation-boundary",),
        "claim": "A capped lifetime evidence counter must remain monotonic and stop at its declared maximum; evidence saturation must not silently decay or wrap it.",
        "prediction": "An at-cap 16-bit lifetime count remains 65535 after additional matching evidence, with unchanged serialized memory size.",
        "falsifier": "An at-cap lifetime count decreases, wraps, or requires unbounded extra storage.",
    },
    "two_tier_recent_evidence": {
        "phase": 1, "role": "bounded-recency",
        "reads": ("outcome_sequence", "memory_state", "monotonic_lifetime_counts"),
        "writes": ("recent_evidence_window",),
        "targets": ("saturation-boundary", "nonstationarity"),
        "claim": "A separate fixed-size recent-evidence window may permit reversal adaptation while leaving lifetime saturated evidence untouched.",
        "prediction": "Recent reversals become detectable without reducing lifetime counters or increasing the total memory budget.",
        "falsifier": "Lifetime counts recede, the recent window grows beyond its fixed allocation, or stationary retention/transfer regresses.",
    },
    "two_tier_memory_consistency_audit": {
        "phase": 3, "role": "verification",
        "reads": ("monotonic_lifetime_counts", "recent_evidence_window"),
        "writes": ("two_tier_memory_consistency",),
        "targets": ("saturation-boundary", "retention-loss"),
        "claim": "Independent checks of lifetime and recent evidence should expose accidental coupling between saturation and consolidation.",
        "prediction": "Lifetime invariants, fixed byte budget, and recent-response behavior all hold simultaneously.",
        "falsifier": "Consolidation mutates lifetime evidence, memory size drifts, or either counter family violates its own declared invariant.",
    },
    "counterfactual_retention_audit": {
        "phase": 3, "role": "verification",
        "reads": ("counterfactual_support", "memory_state"),
        "writes": ("retention_audit",),
        "targets": ("causal-support-gap", "retention-loss"),
        "claim": "Counterfactual probes before and after consolidation should expose whether retained causal knowledge changed.",
        "prediction": "Intervention accuracy remains stable across consolidation and cold restart.",
        "falsifier": "Retained predictions drift despite apparent short-term task improvement.",
    },
}
EXTERNAL_INPUTS = frozenset({
    "support_counts", "prediction_errors", "action_outcomes",
    "outcome_sequence", "memory_state", "context_features",
})
PRIMITIVE_IDS = tuple(PRIMITIVES)


class BranchSearchRejected(ValueError):
    """Invalid event, history, or search-budget input."""


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii")


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _validate_event(event):
    if type(event) is not dict or frozenset(event) != EVENT_FIELDS:
        raise BranchSearchRejected("BRANCH_EVENT_FIELDS")
    if (event["schema"] != EVENT_SCHEMA or
            type(event["event_id"]) is not str or not EVENT_ID.fullmatch(event["event_id"]) or
            type(event["lane"]) is not str or event["lane"] not in LANES or
            not isinstance(event["parent_sha"], str) or not SHA40.fullmatch(event["parent_sha"]) or
            not isinstance(event["parent_tree_sha"], str) or not SHA40.fullmatch(event["parent_tree_sha"]) or
            not isinstance(event["evidence_sha256"], str) or not SHA64.fullmatch(event["evidence_sha256"]) or
            not isinstance(event["receipt_sha256"], str) or not SHA64.fullmatch(event["receipt_sha256"]) or
            event["partition"] != "development" or
            event["terminal_disposition"] != "VERIFIED_TERMINAL_NEGATIVE"):
        raise BranchSearchRejected("BRANCH_EVENT_NOT_ELIGIBLE")
    observed = event["observed_signals"]
    if (type(observed) is not list or not observed or
            any(type(x) is not str or x not in SIGNALS for x in observed) or
            len(observed) != len(set(observed))):
        raise BranchSearchRejected("BRANCH_SIGNALS_INVALID")
    return event


def _ineligible(reason):
    return {
        "schema": SCHEMA, "disposition": reason, "branches": [],
        "expanded_nodes": 0, "scientific_first_use": False,
        "dispatch_authorized": False, "accepted_ref_mutations": 0,
        "model_calls": 0, "paid_api_calls": 0,
        "semantic_novelty_verified": False, "scientific_gain_verified": False,
    }


def _score(sequence, observed):
    targets = set()
    roles = set()
    for primitive_id in sequence:
        spec = PRIMITIVES[primitive_id]
        targets.update(spec["targets"])
        roles.add(spec["role"])
    coverage = len(targets.intersection(observed))
    # A modest compositional bonus favors plans that join different functions.
    # This is a search heuristic only; it is not evidence of useful synergy.
    interaction = max(0, len(roles) - 1)
    risk = 1 if ("retention-loss" in observed and
                 "confidence_gated_update" not in sequence and
                 "regime_gated_consolidation" not in sequence) else 0
    return coverage * 10 + interaction * 2 - risk


def _dependencies(sequence):
    available = set(EXTERNAL_INPUTS)
    edges = []
    produced_by = {}
    for index, primitive_id in enumerate(sequence):
        spec = PRIMITIVES[primitive_id]
        missing = set(spec["reads"]) - available
        if missing:
            return None
        for token in spec["reads"]:
            producer = produced_by.get(token)
            if producer is not None:
                edges.append({"from": sequence[producer], "to": primitive_id, "token": token})
        for token in spec["writes"]:
            produced_by[token] = index
            available.add(token)
    return edges


def _plan(sequence, event, observed, parent_id):
    edges = _dependencies(sequence)
    if edges is None:
        return None
    nodes = []
    for index, primitive_id in enumerate(sequence):
        spec = PRIMITIVES[primitive_id]
        nodes.append({
            "node_id": primitive_id, "depth": index + 1,
            "role": spec["role"], "reads": list(spec["reads"]),
            "writes": list(spec["writes"]),
        })
    mechanism = {"lane": event["lane"], "nodes": nodes, "edges": edges}
    mechanism_sha = _digest(mechanism)
    covered = sorted(set().union(*(set(PRIMITIVES[x]["targets"]) for x in sequence)) & observed)
    claims = [PRIMITIVES[x]["claim"] for x in sequence]
    predictions = [PRIMITIVES[x]["prediction"] for x in sequence]
    falsifiers = [PRIMITIVES[x]["falsifier"] for x in sequence]
    plan = {
        "schema": SCHEMA, "classification": "UNTESTED_ADVISORY_COMPOSITION",
        "lane": event["lane"], "parent_sha": event["parent_sha"],
        "parent_tree_sha": event["parent_tree_sha"],
        "origin_event_id": event["event_id"],
        "origin_evidence_sha256": event["evidence_sha256"],
        "origin_receipt_sha256": event["receipt_sha256"],
        "observed_failure_signals": sorted(observed),
        "covered_failure_signals": covered,
        "mechanism_nodes": nodes, "dependency_edges": edges,
        "mechanism_sha256": mechanism_sha,
        "branch_parent_id": parent_id, "depth": len(sequence),
        "causal_hypothesis_components": claims,
        "counterfactual_predictions": predictions,
        "falsification_conditions": falsifiers,
        "ablation_required": True,
        "semantic_novelty_verified": False,
        "scientific_first_use": False, "dispatch_authorized": False,
        "scientific_gain_verified": False,
    }
    plan["plan_sha256"] = _digest(plan)
    return plan


def propose(event, *, historical_negatives, consumed_mechanism_sha256,
            max_depth=MAX_DEPTH, beam_width=BEAM_WIDTH,
            max_expansions=MAX_EXPANSIONS, max_outputs=MAX_OUTPUTS):
    """Search a bounded causal-composition tree using a verified DEV negative ref.

    The input record must already have been authenticated by its owner. This
    function cannot authenticate it and treats every caller-supplied field as
    untrusted data. Branches are ordered mechanism DAGs, not executable code.
    """
    if event is None:
        return _ineligible("NO_NEW_HYPOTHESIS_SOURCE")
    _validate_event(event)
    bounds = ((max_depth, 1, MAX_DEPTH), (beam_width, 1, 32),
              (max_expansions, 1, MAX_EXPANSIONS), (max_outputs, 1, MAX_OUTPUTS))
    if any(type(value) is not int or value < low or value > high
           for value, low, high in bounds):
        raise BranchSearchRejected("BRANCH_BUDGET_INVALID")
    if (type(historical_negatives) not in (tuple, list) or len(historical_negatives) > MAX_HISTORY or
            type(consumed_mechanism_sha256) not in (tuple, list) or
            len(consumed_mechanism_sha256) > MAX_HISTORY):
        raise BranchSearchRejected("BRANCH_HISTORY_BOUND")
    ids, evidence, receipts = set(), set(), set()
    for old in historical_negatives:
        _validate_event(old)
        for seen, key in ((ids, "event_id"), (evidence, "evidence_sha256"),
                          (receipts, "receipt_sha256")):
            if old[key] in seen:
                raise BranchSearchRejected("BRANCH_DUPLICATE_HISTORY")
            seen.add(old[key])
    if (event["event_id"] in ids or event["evidence_sha256"] in evidence or
            event["receipt_sha256"] in receipts):
        return _ineligible("BRANCH_DUPLICATE_OR_RELABELED_EVENT")
    if any(type(x) is not str or not SHA64.fullmatch(x)
           for x in consumed_mechanism_sha256):
        raise BranchSearchRejected("BRANCH_CONSUMED_IDENTITY_INVALID")
    consumed = set(consumed_mechanism_sha256)
    observed = set(event["observed_signals"])
    frontier = [()]
    visited, output, expanded = set(), [], 0
    parent_for = {(): None}
    for depth in range(1, max_depth + 1):
        proposals = {}
        for parent in frontier:
            for primitive_id in PRIMITIVE_IDS:
                if expanded >= max_expansions:
                    break
                if primitive_id in parent:
                    continue
                sequence = parent + (primitive_id,)
                if _dependencies(sequence) is None:
                    continue
                expanded += 1
                plan = _plan(sequence, event, observed,
                             parent_for.get(parent))
                if plan is None or plan["mechanism_sha256"] in consumed:
                    continue
                key = plan["mechanism_sha256"]
                if key in visited or key in proposals:
                    continue
                # Retain only relevant singletons, but permit support primitives
                # when their outputs are required by a directly relevant update.
                targets = set(PRIMITIVES[primitive_id]["targets"])
                supports_relevant = any(
                    set(PRIMITIVES[child]["reads"]).intersection(PRIMITIVES[primitive_id]["writes"])
                    and set(PRIMITIVES[child]["targets"]).intersection(observed)
                    for child in PRIMITIVE_IDS
                )
                if not targets.intersection(observed) and not supports_relevant:
                    continue
                proposals[key] = (sequence, plan, _score(sequence, observed))
            if expanded >= max_expansions:
                break
        ranked = sorted(proposals.values(),
                        key=lambda item: (-item[2], item[1]["mechanism_sha256"]))
        selected = ranked[:beam_width]
        frontier = []
        for sequence, plan, _ in selected:
            key = plan["mechanism_sha256"]
            visited.add(key)
            parent_for[sequence] = key
            frontier.append(sequence)
            output.append(plan)
            if len(output) >= max_outputs:
                break
        if not frontier or expanded >= max_expansions or len(output) >= max_outputs:
            break
    output.sort(key=lambda plan: (-_score(tuple(n["node_id"] for n in plan["mechanism_nodes"]), observed),
                                  plan["depth"], plan["mechanism_sha256"]))
    if not output:
        return {**_ineligible("NO_UNCONSUMED_COMPOSITIONAL_BRANCH"),
                "expanded_nodes": expanded}
    return {
        **_ineligible("UNTESTED_COMPOSITIONAL_BRANCHES"),
        "branches": output, "expanded_nodes": expanded,
        "search": {"mode": "bounded-compositional-beam", "max_depth": max_depth,
                   "beam_width": beam_width, "max_expansions": max_expansions,
                   "max_outputs": max_outputs, "grammar_primitive_count": len(PRIMITIVES),
                   "semantic_novelty_verified": False},
    }
