"""F122 bounded raw-symbol relation learning across disjoint graph structures.

Only synthetic public GenEnv source vectors are consumed. No precomputed
equality flags, oracle truth, source IDs or graph labels are model features.
The symbolic solver is used only for counterfactual/ceiling qualification.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import sys

import f120_generated_environment as f120
import f121_learned_binding as f121
import f118_autonomy_feedback as f118

ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "reference/research-intake/f122-raw-binding-transfer-freeze.json"
FREEZE_BLOB = "97549cd97011ed984cd4835537b338179706544e"
SCHEMA = "forge.autonomy.f122.raw-variable-transfer-development.v1"
PARENT_F121 = "57e54e98e223406e19dc8be5d73d309413250a85"
SEEDS = {
    "Wingless": {"TRAIN": range(94000, 94024), "CONFIRM": range(94100, 94148)},
    "Yggdrasil": {"TRAIN": range(95000, 95024), "CONFIRM": range(95100, 95148)},
}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
WIDTH, HIDDEN, EPOCHS = 16, 12, 100

class Invalid(ValueError):
    pass

def require(ok, reason):
    if not ok:
        raise Invalid("F122_" + reason)

def frozen():
    raw = FREEZE.read_bytes().replace(b"\r\n", b"\n")
    require(f120.blob(raw) == FREEZE_BLOB, "FROZEN_PROTOCOL_DRIFT")
    x = json.loads(raw)
    require(x["schema"] == "forge.autonomy.f122.frozen-raw-variable-binding-transfer-development.v1"
            and x["parent_f121_head"] == PARENT_F121
            and x["parent_f121_code_blob"] == "f06fa73a6092e7fa031f20c66f9a1b9da3867e70"
            and x["cohorts"]["training_epochs"] == EPOCHS
            and x["cohorts"]["training_hops"] == [2, 3]
            and x["cohorts"]["confirmation_hops"] == [5, 6]
            and x["cohorts"]["trainable_parameter_limit"] == 409
            and all(x["authority"].values()), "PREIMPLEMENTATION_CONTRACT_INCOMPLETE")
    require(x["cohorts"]["training_pair_seeds"] ==
            {"Wingless": [94000, 94023], "Yggdrasil": [95000, 95023]}
            and x["cohorts"]["confirmation_pair_seeds"] ==
            {"Wingless": [94100, 94147], "Yggdrasil": [95100, 95147]},
            "FROZEN_SEED_DRIFT")
    return hashlib.sha256(raw).hexdigest()

def canonical(x):
    return f120.canonical(x)

def sha(x):
    return f120.sha(x)

def graph(seed, vector, lane, phase):
    """Generate long/novel structural transfer without model-visible metadata."""
    require(lane in SEEDS and phase in ("TRAIN", "CONFIRM")
            and seed in SEEDS[lane][phase]
            and type(vector) is list and len(vector) == 3
            and all(type(v) is int and 0 <= v <= 3 for v in vector),
            "INVALID_GRAPH_SOURCE")
    rng = random.Random(seed * 193 + vector[0] * 17 + vector[1] * 31 + vector[2] * 7)
    hops = (2 if seed % 2 == 0 else 3) if phase == "TRAIN" else (5 if seed % 2 == 0 else 6)
    family = "source-role" if phase == "TRAIN" else "novel-heldout-relation"
    nodes = [family + "-node-" + str(seed) + "-" + str(i) for i in range(hops + 1)]
    roles = [family + "-" + str((i + vector[0]) % (3 if phase == "TRAIN" else 7))
             for i in range(hops)]
    values = rng.sample(range(1000, 60000), hops + 5)
    main = [(nodes[i], nodes[i + 1], roles[i], values[i], values[i + 1])
            for i in range(hops)]
    # Off-path edges have deliberately incompatible roles; confirmation has
    # distinct side-branch geometry, more hops, new roles, and new variable IDs.
    decoy_count = 1 + min(vector[1], 2) + (1 if phase == "CONFIRM" else 0)
    positive = list(main)
    for j in range(decoy_count):
        origin = nodes[(j + vector[2]) % hops] if phase == "CONFIRM" else nodes[0]
        off = family + "-side-" + str(seed) + "-" + str(j)
        positive.append((origin, off, "offpath-" + str(j), values[-2], values[-1]))
        if phase == "CONFIRM":
            positive.append((off, nodes[-1], "wrong-terminal-" + str(j),
                             values[-1], values[-2]))
    change = max(1, hops // 2)
    decoy_at = hops
    require(main[change][3] != positive[decoy_at][3],
            "COUNTERFACTUAL_NONDISTINCT")
    negative = list(positive)
    a, b = list(negative[change]), list(negative[decoy_at])
    a[3], b[3] = b[3], a[3]
    negative[change], negative[decoy_at] = tuple(a), tuple(b)
    rng.shuffle(positive)
    rng.shuffle(negative)
    case = {"start": nodes[0], "target": nodes[-1], "roles": roles, "hops": hops,
            "positive": positive, "negative": negative,
            "lane": lane, "phase": phase, "seed": seed,
            "vector": list(vector)}
    topo = lambda es: sorted((e[0], e[1], e[2]) for e in es)
    marginals = lambda es: sorted(v for e in es for v in e[3:])
    require(topo(positive) == topo(negative)
            and marginals(positive) == marginals(negative)
            and f120.binding_solver(case, positive)
            and not f120.binding_solver(case, negative)
            and f120.role_only(case, positive)
            and f120.role_only(case, negative), "SOURCE_GRAPH_OR_MARGINALS_INVALID")
    return case

def raw_junctions(case, edges):
    node, prev, out = case["start"], None, []
    for role in case["roles"]:
        options = [e for e in edges if e[0] == node and e[2] == role]
        require(len(options) == 1, "ROLE_PATH_NOT_UNIQUE")
        e = options[0]
        if prev is not None:
            out.append((prev, e[3]))
        prev, node = e[4], e[1]
    require(node == case["target"] and len(out) == case["hops"] - 1,
            "PATH_INCOMPLETE")
    return out

def token_bits(value, salt):
    # Encode each individual raw integer independently. This does NOT return
    # equality, pairwise distance, Hamming distance or correctness flags.
    digest = hashlib.sha256((salt + "/" + str(value)).encode()).digest()
    token = int.from_bytes(digest[:2], "big")
    return tuple((token >> i) & 1 for i in range(WIDTH))

def encodings(case):
    salt = "f122/" + case["lane"] + "/" + case["phase"] + "/" + str(case["seed"])
    raw_values = {v for e in case["positive"] for v in e[3:]}
    raw_values.update(v for e in case["negative"] for v in e[3:])
    codes = [token_bits(v, salt) for v in raw_values]
    require(len(set(codes)) == len(raw_values), "RAW_TOKEN_PROJECTION_COLLISION")
    return {v: token_bits(v, salt) for v in raw_values}

def encode_pair(x, y, lookup):
    require(x in lookup and y in lookup, "NON_GRAPH_SYMBOL")
    # The model receives ONLY two encoded raw tokens, not any equality bit.
    return (lookup[x], lookup[y])

def sigmoid(x):
    return f121.sigmoid(x)

def initialize(kind):
    if kind == "A":
        return [-0.07] + [0.03] * WIDTH
    require(kind == "B", "UNKNOWN_LEARNED_ARM")
    rng = random.Random(122)
    return ([[(rng.random() - 0.5) * 0.22 for _ in range(2 * WIDTH + 1)]
             for _ in range(HIDDEN)],
            [(rng.random() - 0.5) * 0.22 for _ in range(HIDDEN + 1)])

def model_a(weights, pair):
    left, right = pair
    cross = [(2 * left[i] - 1) * (2 * right[i] - 1) for i in range(WIDTH)]
    return sigmoid(weights[0] + sum(w * z for w, z in zip(weights[1:], cross))), [1] + cross

def model_b(weights, pair):
    left, right = pair
    x = [2 * v - 1 for v in left + right] + [1]
    hidden = [math.tanh(sum(a * b for a, b in zip(row, x)))
              for row in weights[0]]
    score = sum(w * h for w, h in zip(weights[1][:-1], hidden)) + weights[1][-1]
    return sigmoid(score), x, hidden

def train(samples, kind):
    require(len(samples) == 96 and sum(label for _, label in samples) == 48,
            "UNFROZEN_TRAINING_COHORT")
    w = initialize(kind)
    initial = json.dumps(w)
    # Deterministic, bounded, training-only stochastic gradient updates.
    for epoch in range(EPOCHS):
        for pair, truth in samples:
            if kind == "A":
                p, features = model_a(w, pair)
                step = max(-1., min(1., p - truth))
                for i, x in enumerate(features):
                    w[i] = max(-8., min(8., w[i] - 0.35 * step * x))
            else:
                p, x, h = model_b(w, pair)
                d = max(-1., min(1., p - truth))
                back = [d * w[1][j] * (1. - h[j] * h[j])
                        for j in range(HIDDEN)]
                for j in range(HIDDEN):
                    for k in range(len(x)):
                        w[0][j][k] = max(-8., min(8.,
                                             w[0][j][k] - 0.35 * back[j] * x[k]))
                for j in range(HIDDEN):
                    w[1][j] = max(-8., min(8., w[1][j] - 0.35 * d * h[j]))
                w[1][-1] = max(-8., min(8., w[1][-1] - 0.35 * d))
    flat = w if kind == "A" else [v for row in w[0] for v in row] + w[1]
    require(json.dumps(w) != initial and all(math.isfinite(v) for v in flat)
            and len(flat) <= 409, "UNTRAINED_OR_OVERSIZED_MODEL")
    return w, len(flat)

def predict(kind, weights, pair):
    return (model_a(weights, pair)[0] if kind == "A"
            else model_b(weights, pair)[0]) >= 0.5

def build_rows(candidate, lane, phase):
    rows = []
    for seed in SEEDS[lane][phase]:
        case = graph(seed, candidate["vector"], lane, phase)
        lookup = encodings(case)
        positive = raw_junctions(case, case["positive"])
        negative = raw_junctions(case, case["negative"])
        changed = [i for i, (a, b) in enumerate(zip(positive, negative))
                   if a != b]
        require(len(changed) == 1 and
                positive[changed[0]][0] == negative[changed[0]][0],
                "UNCONTROLLED_LOCAL_INTERVENTION")
        rows.append({"seed": seed, "hops": case["hops"],
                     "source_graph_sha256": sha(case),
                     "positive": [encode_pair(a, b, lookup) for a, b in positive],
                     "negative": [encode_pair(a, b, lookup) for a, b in negative],
                     "changed": changed[0]})
    return rows

def train_samples(rows):
    # Paired intervention yields the training truth and identifies its changed
    # path junction. No variable equality check is used to form model inputs.
    return [(row["positive"][row["changed"]], 1) for row in rows] + [
            (row["negative"][row["changed"]], 0) for row in rows]

def model_score(rows, kind, weights):
    tp = tn = paired = 0
    for row in rows:
        pos = all(predict(kind, weights, pair) for pair in row["positive"])
        neg = all(predict(kind, weights, pair) for pair in row["negative"])
        tp += int(pos)
        tn += int(not neg)
        paired += int(pos and not neg)
    return {"pairs": len(rows), "paired_correct": paired,
            "balanced_accuracy": round((tp + tn) / (2 * len(rows)), 8),
            "positive_correct": tp, "negative_correct": tn}

def control_score(rows, kind):
    tp = tn = paired = 0
    for row in rows:
        if kind == "CTRL_DEPTH2":
            classifications = [(row["hops"] <= 2), False]
        elif kind == "CTRL_ROLE":
            classifications = [True, True]
        elif kind == "CTRL_CONSTANT":
            classifications = [False, False]
        elif kind == "CTRL_EXACT_SYMBOLIC":
            classifications = [True, False]
        else:
            raise Invalid("UNKNOWN_CONTROL")
        p, n = classifications
        tp += int(p)
        tn += int(not n)
        paired += int(p and not n)
    return {"pairs": len(rows), "paired_correct": paired,
            "balanced_accuracy": round((tp + tn) / (2 * len(rows)), 8),
            "positive_correct": tp, "negative_correct": tn}

def execute(advisory, source, run_id, event):
    frozen_hash = frozen()
    require(type(source) is str and HEX40.fullmatch(source)
            and type(run_id) is int and run_id > 0
            and event in ("schedule", "push", "pull_request", "workflow_dispatch")
            and (not os.environ.get("GITHUB_SHA") or os.environ["GITHUB_SHA"] == source),
            "SOURCE_NOT_PINNED")
    candidates = f120.validate(advisory, source)
    lanes = []
    for lane in ("Wingless", "Yggdrasil"):
        training = [build_rows(x, lane, "TRAIN") for x in candidates[lane]]
        samples = [sample for rows in training for sample in train_samples(rows)]
        models = {arm: train(samples, arm) for arm in ("A", "B")}
        train_scores = {arm: [model_score(rows, arm, models[arm][0])
                              for rows in training] for arm in ("A", "B")}
        selected = sorted(("A", "B"), key=lambda arm:
                          (-sum(x["paired_correct"] for x in train_scores[arm]),
                           arm))[0]
        # None of the following held-out cases can change weights or selection.
        confirmation = [build_rows(x, lane, "CONFIRM") for x in candidates[lane]]
        confirm_scores = {arm: [model_score(rows, arm, models[arm][0])
                                for rows in confirmation] for arm in ("A", "B")}
        controls = {arm: [control_score(rows, arm) for rows in confirmation]
                    for arm in ("CTRL_DEPTH2", "CTRL_ROLE",
                                "CTRL_CONSTANT", "CTRL_EXACT_SYMBOLIC")}
        selected_score = sum(x["paired_correct"] for x in confirm_scores[selected])
        lanes.append({"lane": lane,
                      "candidate_source_sha256":
                          [c["source_candidate_sha256"] for c in candidates[lane]],
                      "train_graph_digest": sha(training),
                      "confirm_graph_digest": sha(confirmation),
                      "train_source_only_selection": selected,
                      "learned_parameters": {k: models[k][1] for k in ("A", "B")},
                      "model_weights_sha256": {k: sha(models[k][0]) for k in ("A", "B")},
                      "train_scores": train_scores,
                      "confirmation_scores": confirm_scores,
                      "frozen_controls": controls,
                      "selected_confirm_pair_accuracy": round(selected_score / 96, 8),
                      "selected_vs_symbolic_ceiling_pair_gap":
                          round(selected_score / 96 - 1., 8),
                      "train_and_confirm_source_isolated": True,
                      "engineered_equality_bit_given_to_model": False,
                      "confirmation_used_for_training_or_selection": False,
                      "independent_scientific_transfer_established": False})
    return {"schema": SCHEMA, "source_sha": source, "run_id": run_id,
            "event": event, "freeze_sha256": frozen_hash,
            "advisory_sha256": sha(advisory),
            "lanes": lanes, "training_pairs_total": 96,
            "confirmation_pairs_total": 192,
            "model_arms": 2, "actual_learned_parameter_updates": True,
            "public_source_only_development": True,
            "scientific_first_use_authorized": False,
            "originals_dispatched": 0, "scientific_acceptances": 0,
            "accepted_ref_mutations": 0, "optimizer_promotions": 0,
            "Codex_calls": 0, "paid_model_calls": 0, "new_scheduler": False,
            "ckb_plane_contact": False, "cloudflare_writes": 0,
            "mind_palace_writes": 0}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--advisory", required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--event", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    out = Path(args.output)
    require(out.parent.exists() and not out.exists(),
            "OUTPUT_OVERWRITE_FORBIDDEN")
    report = execute(f118.load_report(args.advisory), args.source_ref,
                     args.run_id, args.event)
    with out.open("xb") as handle:
        handle.write(canonical(report))

if __name__ == "__main__":
    try:
        main()
    except (Invalid, f120.Invalid, f121.Invalid, f118.Quarantined,
            ValueError, TypeError, KeyError, OSError) as exc:
        print("F122_RAW_VARIABLE_TRANSFER=QUARANTINED " + str(exc),
              file=sys.stderr)
        raise SystemExit(1)
