"""G92 exact-output self-sketch microtree feasibility accounting.

Synthetic CPU analytical proxy only; NOT measured GPU/model throughput.
Frozen design: docs/research/acc_g91_g106/G92_MICROTREE_PREREG_20261031.md
All measurements emitted as machine-readable JSON to stdout.
"""
import json
import math
import platform
import statistics
import time

import numpy as np
from threadpoolctl import threadpool_limits

SCHEMA = "forge.acc.g92.microtree_synthetic.v1"
SEEDS = (9201, 9202, 9203)
VOCAB, LOW_RANK, DEPTH = 64, 8, 3
WIDTHS = (1, 2, 4)
HISTORIES, OUTPUT_TOKENS = 16, 24
SECOND_PREV_SCALE, DRAFT_COST, TARGET_SPEEDUP = .2, .1, 1.15


def build_oracle(seed):
    rng = np.random.default_rng(seed)
    a = rng.standard_normal((VOCAB, VOCAB))
    b = rng.standard_normal((VOCAB, VOCAB))
    histories = rng.integers(0, VOCAB, size=(HISTORIES, 2))
    return a, b, histories


def svd_sketch(a, b):
    def approximate(matrix):
        u, s, vh = np.linalg.svd(matrix, full_matrices=False)
        return (u[:, :LOW_RANK] * s[:LOW_RANK]) @ vh[:LOW_RANK, :]
    return approximate(a), approximate(b)


def greedy_token(a, b, context):
    assert len(context) >= 2
    scores = a[context[-1]] + SECOND_PREV_SCALE * b[context[-2]]
    if not np.all(np.isfinite(scores)):
        raise ArithmeticError("NONFINITE_ORACLE")
    return int(np.argmax(scores))


def propose(sketch_a, sketch_b, context, width):
    scores = sketch_a[context[-1]] + SECOND_PREV_SCALE * sketch_b[context[-2]]
    if not np.all(np.isfinite(scores)):
        raise ArithmeticError("NONFINITE_DRAFT")
    return tuple(int(x) for x in np.argsort(-scores, kind="stable")[:width])


def reference_sequence(a, b, start):
    history = list(start)
    out = []
    for _ in range(OUTPUT_TOKENS):
        token = greedy_token(a, b, history)
        history.append(token)
        out.append(token)
    return out


def verify_tree(a, b, sketch_a, sketch_b, context, width):
    """Materialize and verify EVERY proposed node, including rejected branches."""
    nodes = [()]
    frontier = [()]
    suggestions = {}
    draft_expansions = 0
    for _ in range(DEPTH):
        following = []
        for prefix in frontier:
            choices = propose(sketch_a, sketch_b, context + prefix, width)
            suggestions[prefix] = choices
            draft_expansions += 1
            following.extend(prefix + (choice,) for choice in choices)
        nodes.extend(following)
        frontier = following
    outcomes = {prefix: greedy_token(a, b, context + prefix) for prefix in nodes}
    output = []
    prefix = ()
    for layer in range(DEPTH + 1):
        token = outcomes[prefix]
        output.append(token)
        if layer == DEPTH or token not in suggestions[prefix]:
            break
        prefix = prefix + (token,)
    return output, len(nodes), draft_expansions


def run_case(a, b, sketch_a, sketch_b, start, width, seed, history_id):
    expected = reference_sequence(a, b, start)
    produced = []
    history = tuple(int(x) for x in start)
    batches = verified_nodes = draft_nodes = accepted = 0
    while len(produced) < OUTPUT_TOKENS:
        chunk, nodes, expansions = verify_tree(a, b, sketch_a, sketch_b, history, width)
        remain = OUTPUT_TOKENS - len(produced)
        emitted = chunk[:remain]
        produced.extend(emitted)
        history += tuple(emitted)
        batches += 1
        verified_nodes += nodes
        draft_nodes += expansions
        accepted += max(0, len(emitted) - 1)
    exact = produced == expected
    if not exact:
        raise AssertionError("GREEDY_STREAM_MISMATCH")
    if not (verified_nodes >= batches >= 1 and draft_nodes >= batches):
        raise AssertionError("INVALID_WORK_ACCOUNTING")
    max_verifier_unit_cost = (OUTPUT_TOKENS / TARGET_SPEEDUP - DRAFT_COST * draft_nodes) / verified_nodes
    return dict(
        seed=seed, history_id=history_id, width=width,
        exact_reference_match=exact, emitted_tokens=len(produced),
        verifier_batches=batches, verified_nodes=verified_nodes,
        draft_expansions=draft_nodes, accepted_draft_tokens=accepted,
        tokens_per_batch=len(produced)/batches,
        verified_nodes_per_token=verified_nodes/len(produced),
        v_max_1p15x=max_verifier_unit_cost,
        infeasible_even_if_free_verifier=max_verifier_unit_cost <= 0,
    )


def screen():
    cases, setup = [], []
    with threadpool_limits(limits=1):
        for seed in SEEDS:
            a, b, histories = build_oracle(seed)
            t0 = time.perf_counter_ns()
            sketch_a, sketch_b = svd_sketch(a, b)
            setup.append(dict(seed=seed, sketch_setup_ms=(time.perf_counter_ns()-t0)/1e6))
            for width in WIDTHS:
                for i, start in enumerate(histories):
                    cases.append(run_case(a, b, sketch_a, sketch_b, start, width, seed, i))
    if len(cases) != len(SEEDS)*len(WIDTHS)*HISTORIES:
        raise AssertionError("INCOMPLETE_SCREEN")
    if any(not x["exact_reference_match"] for x in cases):
        raise AssertionError("EXACTNESS_FAILURE")
    summary = {}
    for width in WIDTHS:
        group = [x for x in cases if x["width"] == width]
        summary[str(width)] = dict(
            cases=len(group),
            all_exact=all(x["exact_reference_match"] for x in group),
            median_tokens_per_batch=statistics.median(x["tokens_per_batch"] for x in group),
            median_verified_nodes_per_token=statistics.median(x["verified_nodes_per_token"] for x in group),
            median_v_max_1p15x=statistics.median(x["v_max_1p15x"] for x in group),
            infeasible_cases=sum(x["infeasible_even_if_free_verifier"] for x in group),
        )
    valid_widths = [w for w in WIDTHS if summary[str(w)]["median_v_max_1p15x"] > 0]
    return dict(
        schema=SCHEMA,
        source_type="synthetic_cpu_analytical_feasibility_proxy",
        gpu_model_evidence="NOT_RUN",
        actual_speedup="NOT_MEASURED",
        scientific_acceptance="NOT_GRANTED",
        env=dict(python=platform.python_version(),numpy=np.__version__,blas_threads=1),
        frozen=dict(seeds=list(SEEDS),vocab=VOCAB,rank=LOW_RANK,depth=DEPTH,
                    widths=list(WIDTHS),histories=HISTORIES,output_tokens=OUTPUT_TOKENS,
                    second_prev_scale=SECOND_PREV_SCALE,draft_unit_cost=DRAFT_COST,
                    hypothetical_target_speedup=TARGET_SPEEDUP),
        sketch_initialization=setup,
        summary=summary,
        cases=cases,
        decision="FEASIBILITY_ONLY" if valid_widths else "NO_GO_ANALYTICAL",
        caveat="Self-sketch extracted from synthetic oracle; 0.1 draft unit is hypothetical. Theoretical v_max is NOT measured GPU/model speedup. Fully charged branching node counts; SVD setup reported separately.",
    )


if __name__ == "__main__":
    print("G92_JSON=" + json.dumps(screen(), sort_keys=True, allow_nan=False, separators=(",", ":")))
