"""ACC-97 deterministic rule-switch episodes, FIT/DEV only; no model admission.

The observed records contain inputs and labels only at allowed cells. Evaluation
queries are separate from learner observations and must never be passed to learn().
"""
from __future__ import annotations
import hashlib
import json
import random
from fitdev import ALLOWED, seed_for, next_bit, CountTable

SCHEMA = "forge.acc97.u24.switch-sourcefree.v1"
PRE_STEPS = 128
ADAPT_STEPS = 64
POST_STEPS = 128
TOTAL_STEPS = PRE_STEPS + ADAPT_STEPS + POST_STEPS

def frozen_rule_pair(split: str, first_rule: int):
    if split not in ALLOWED or first_rule not in ALLOWED[split][0]:
        raise ValueError("UNAUTHORIZED_RULE")
    rules = ALLOWED[split][0]
    return first_rule, rules[(rules.index(first_rule) + 1) % len(rules)]

def switching_trace(split: str, first_rule: int, seed: int,
                    *, width: int = 25, episode: int = 0):
    first, second = frozen_rule_pair(split, first_rule)
    if width not in (25, 63, 127):
        raise ValueError("PROTOCOL_DRIFT")
    rng = random.Random(seed_for(split, first, seed, episode))
    cells = [rng.randrange(2) for _ in range(width)]
    records = []
    for step in range(TOTAL_STEPS):
        rule = first if step < PRE_STEPS else second
        neighbors = [(cells[(i-1) % width], cells[i], cells[(i+1) % width])
                     for i in range(width)]
        following = [next_bit(rule, *n) for n in neighbors]
        visible_indices = set(rng.sample(range(width), width // 4))
        visible = [(neighbors[i], following[i]) for i in range(width) if i in visible_indices]
        queries = [(neighbors[i], following[i]) for i in range(width) if i not in visible_indices]
        records.append({"step": step, "visible": visible, "queries": queries})
        cells = following
    digest = hashlib.sha256(json.dumps(records, separators=(",", ":"),
                            sort_keys=True).encode("utf-8")).hexdigest()
    return {"schema": SCHEMA, "split": split, "first_rule": first, "second_rule": second,
            "width": width, "records": records, "trace_sha256": digest,
            "reserved_test_used": False, "science_accepted": False}

def evaluate_count_table(trace, *, reset_at_switch=False):
    """A fair streaming reference: see visible observations only AFTER prediction."""
    if trace["schema"] != SCHEMA or len(trace["records"]) != TOTAL_STEPS:
        raise ValueError("TRACE_CONTRACT_DRIFT")
    table = CountTable.fresh()
    phase_hits = [0, 0, 0]
    phase_queries = [0, 0, 0]
    snapshots = {}
    for step, record in enumerate(trace["records"]):
        if record["step"] != step:
            raise ValueError("STEP_DRIFT")
        if step == PRE_STEPS and reset_at_switch:
            # Oracle reset has privileged change timing: label as a nonfair upper bound.
            table = CountTable.fresh()
        phase = 0 if step < PRE_STEPS else (1 if step < PRE_STEPS + ADAPT_STEPS else 2)
        for neighbors, actual in record["queries"]:
            phase_hits[phase] += (table.predict(neighbors) == actual)
            phase_queries[phase] += 1
        table.observe(record["visible"])
        if step == PRE_STEPS + ADAPT_STEPS - 1:
            snapshots["adapt_end"] = table.snapshot()
            table = CountTable.restore(snapshots["adapt_end"])
            if table.snapshot() != snapshots["adapt_end"]:
                raise RuntimeError("COLD_RESTART_MISMATCH")
    return {"phase_accuracy": [n/d for n, d in zip(phase_hits, phase_queries)],
            "phase_queries": phase_queries,
            "adapt_error": phase_queries[1] - phase_hits[1],
            "state_sha256": hashlib.sha256(table.snapshot().encode()).hexdigest(),
            "restart_snapshot_sha256": hashlib.sha256(
                snapshots["adapt_end"].encode()).hexdigest(),
            "oracle_reset": bool(reset_at_switch),
            "science_accepted": False, "resource_qualified": False}

def development_screen(split: str, first_rule: int, seed: int, *, width: int = 25):
    trace = switching_trace(split, first_rule, seed, width=width)
    return {"schema": SCHEMA, "split": split, "source_sha256": trace["trace_sha256"],
            "carry": evaluate_count_table(trace),
            "oracle_reset": evaluate_count_table(trace, reset_at_switch=True),
            "classification": "SOURCEFREE_DEV_DIAGNOSTIC_ONLY",
            "reserved_test_used": False, "scientific_acceptance": "NOT_GRANTED"}
