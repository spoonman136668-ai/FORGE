"""F121 source-only supervised composition development (not scientific acceptance).

Two genuinely trainable bounded models operate on engineered LOCAL variable
equality features from F120's generated public graph environments. Global
graph-oracle truth is used for evaluation only, never as a model feature.
Training selects A/B once; independent confirmation cannot tune the model.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys

import f120_generated_environment as f120
import f118_autonomy_feedback as f118

ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "reference/research-intake/f121-learned-binding-development-freeze.json"
FREEZE_BLOB = "67105accb3ca50aef8cc436cf0b730b1eefbc19e"
SCHEMA = "forge.autonomy.f121.trainable-binding-development.v1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
COHORTS = {
    "Wingless": {"TRAIN": range(92000, 92024), "CONFIRM": range(92100, 92148)},
    "Yggdrasil": {"TRAIN": range(93000, 93024), "CONFIRM": range(93100, 93148)},
}
class Invalid(ValueError):
    pass

def require(test, reason):
    if not test:
        raise Invalid("F121_" + reason)

def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()

def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()

def frozen():
    raw = FREEZE.read_bytes().replace(b"\r\n", b"\n")
    require(f120.blob(raw) == FREEZE_BLOB, "FROZEN_PROTOCOL_TAMPERED")
    p = json.loads(raw)
    require(p["schema"] == "forge.autonomy.f121.frozen-trainable-binding-composition-development.v1"
        and p["parent_main_commit"] == "0eca385586f8d4860a3b0076a880962419bdccc0"
        and p["parent_f120_graph_code_blob"] == "775c120fb4dfb27baf52240f88c11d8a99478451"
        and p["parent_f120_protocol_blob"] == "15b94953426fd9064a9a2fb309713ea8312313b3"
        and p["cohorts"]["training_epochs"] == 120
        and p["cohorts"]["train_pairs_per_candidate"] == 24
        and p["cohorts"]["confirm_pairs_per_candidate"] == 48
        and p["limits"]["trainable_parameters_per_candidate_max"] == 32
        and all(p["authority"].values()), "PREREGISTERED_IDENTITY_DRIFT")
    require(p["cohorts"]["training_pair_seeds"] ==
        {"Wingless": [92000, 92023], "Yggdrasil": [93000, 93023]}
        and p["cohorts"]["confirmation_pair_seeds"] ==
        {"Wingless": [92100, 92147], "Yggdrasil": [93100, 93147]},
        "COHORT_IDENTITY_DRIFT")
    return p, hashlib.sha256(raw).hexdigest()

def paired_graph(seed, vector):
    """Counterfactual slot swap preserves whole-graph value histogram."""
    original = f120.graph(seed, vector)
    positive = list(original["positive"])
    edges = list(positive)
    node = original["start"]
    path = []
    for role in original["roles"]:
        matching = [(i, e) for i, e in enumerate(edges)
                    if e[0] == node and e[2] == role]
        require(len(matching) == 1, "AMBIGUOUS_ROLE_PATH")
        i, edge = matching[0]
        path.append(i)
        node = edge[1]
    require(node == original["target"] and len(path) >= 2,
            "INCOMPLETE_GRAPH_PATH")
    # Ensure every environment has a role-INCOMPATIBLE distractor to
    # exchange an existing variable slot. Add the SAME edge to both arms.
    decoys = [i for i, e in enumerate(edges) if e[2].startswith("junk-")]
    if not decoys:
        decoy_id = "decoy-f121-" + str(seed)
        edges.append((original["start"], decoy_id, "junk-f121", 50000 + seed,
                      60000 + seed))
        decoys = [len(edges) - 1]
    target_index = path[max(1, len(path) // 2)]
    decoy_index = decoys[0]
    require(target_index != decoy_index, "DECOY_COLLIDES_WITH_PATH")
    before = edges[target_index]
    distractor = edges[decoy_index]
    require(before[3] != distractor[3], "NON_DISTINCT_SWAP_VALUES")
    negative = list(edges)
    swapped_target = list(before)
    swapped_decoy = list(distractor)
    swapped_target[3] = distractor[3]
    swapped_decoy[3] = before[3]
    negative[target_index] = tuple(swapped_target)
    negative[decoy_index] = tuple(swapped_decoy)
    pos = sorted(edges)
    neg = sorted(negative)
    def slots(es):
        return sorted(s for e in es for s in (e[3], e[4]))
    def topology(es):
        return sorted((e[0], e[1], e[2]) for e in es)
    require(topology(pos) == topology(neg) and slots(pos) == slots(neg),
            "CANDIDATE_MARGINALS_LEAK_LABEL")
    require(f120.binding_solver(original, pos)
            and not f120.binding_solver(original, neg)
            and f120.role_only(original, pos)
            and f120.role_only(original, neg), "ORACLE_COUNTERFACTUAL_FAILURE")
    return {**original, "positive": pos, "negative": neg,
            "source_environment_vector": list(vector)}

def local_features(case, edges):
    """Extract one sequence of actual LOCAL equality signals, not labels.

    Path topology/roles are available on both positive and negative inputs.
    The global validity label is not evaluated here or made an input.
    """
    node = case["start"]
    previous = None
    match_bits = []
    for role in case["roles"]:
        options = [edge for edge in edges if edge[0] == node and edge[2] == role]
        require(len(options) == 1, "LOCAL_ROLE_AMBIGUITY")
        edge = options[0]
        if previous is not None:
            match_bits.append(1 if previous == edge[3] else 0)
        previous = edge[4]
        node = edge[1]
    require(node == case["target"] and len(match_bits) >= 1,
            "LOCAL_PATH_NOT_COMPLETE")
    return match_bits

def sigmoid(x):
    if x >= 0:
        return 1 / (1 + math.exp(-min(x, 100)))
    q = math.exp(max(x, -100))
    return q / (1 + q)

def model_a(weights, bits):
    features = (1.0, sum(bits) / len(bits), (len(bits) + 1) / 4.0)
    score = sum(w * x for w, x in zip(weights, features))
    return sigmoid(score), list(features)

def model_b(weights, bits):
    # Learnable recurrent composition of locally sensed binding links.
    a, b, bias, out, outbias = weights
    h = 0.0
    derivatives = [0.0, 0.0, 0.0]
    for bit in bits:
        hprev = h
        h = math.tanh(a * h + b * (2 * bit - 1) + bias)
        factor = 1 - h * h
        derivatives = [
            factor * (hprev + a * derivatives[0]),
            factor * ((2 * bit - 1) + a * derivatives[1]),
            factor * (1 + a * derivatives[2])]
    p = sigmoid(out * h + outbias)
    return p, [out * d for d in derivatives] + [h, 1.0]

def train(samples, kind):
    require(len(samples) == 96 and
            sum(label for _, label in samples) == 48, "TRAIN_COHORT_NOT_FROZEN")
    weights = ([0.1, -0.2, 0.01] if kind == "A"
               else [0.25, 0.4, -0.1, 0.5, 0.0])
    start = list(weights)
    for _ in range(120):
        gradient = [0.0] * len(weights)
        for bits, label in samples:
            p, dp = (model_a(weights, bits) if kind == "A"
                     else model_b(weights, bits))
            for k in range(len(weights)):
                gradient[k] += (p - label) * dp[k]
        for k in range(len(weights)):
            step = max(-1.0, min(1.0, gradient[k] / len(samples)))
            weights[k] = max(-8.0, min(8.0, weights[k] - 0.8 * step))
    movement = sum((a - b) ** 2 for a, b in zip(weights, start)) ** 0.5
    require(movement > 0.001 and all(math.isfinite(x) for x in weights),
            "MODEL_DID_NOT_GENUINELY_TRAIN")
    return weights, round(movement, 8)

def predict(kind, weights, bits):
    return (model_a(weights, bits) if kind == "A"
            else model_b(weights, bits))[0] >= 0.5

def records_for(candidate, lane, phase):
    records = []
    for seed in COHORTS[lane][phase]:
        case = paired_graph(seed, candidate["vector"])
        a, b = local_features(case, case["positive"]), local_features(case, case["negative"])
        require(len(a) == len(b) and sum(a) == len(a) and
                sum(b) == len(b) - 1, "COUNTERFACTUAL_FEATURE_LEAK_OR_BROKEN_JOIN")
        records.append({"seed": seed, "case_sha256": sha(case),
                        "positive_bits": a, "negative_bits": b,
                        "hops": case["hops"]})
    return records

def score(records, kind, weights):
    tp = tn = fp = fn = paired = 0
    for row in records:
        pos = predict(kind, weights, row["positive_bits"])
        neg = predict(kind, weights, row["negative_bits"])
        tp += int(pos)
        fn += int(not pos)
        tn += int(not neg)
        fp += int(neg)
        paired += int(pos and not neg)
    n = len(records)
    return {"pairs": n, "paired_correct": paired,
            "positive_correct": tp, "negative_correct": tn,
            "balanced_accuracy": round((tp + tn) / (2*n), 8),
            "false_positive": fp, "false_negative": fn}

def control(records, kind):
    paired = tp = tn = 0
    for row in records:
        valid_pos = valid_neg = False
        if kind == "CTRL_DEPTH2":
            valid_pos = row["hops"] <= 2
        elif kind == "CTRL_ROLE":
            valid_pos = valid_neg = True
        elif kind == "CTRL_ORACLE":
            valid_pos = True
        elif kind == "CTRL_CONSTANT":
            valid_pos = valid_neg = False
        else:
            raise Invalid("F121_UNKNOWN_CONTROL")
        tp += int(valid_pos)
        tn += int(not valid_neg)
        paired += int(valid_pos and not valid_neg)
    return {"pairs": len(records), "paired_correct": paired,
            "balanced_accuracy": round((tp+tn)/(2*len(records)), 8),
            "positive_correct": tp, "negative_correct": tn}

def execute(advisory, source, run_id, event):
    freeze, freeze_sha = frozen()
    require(isinstance(source, str) and HEX40.fullmatch(source)
            and isinstance(run_id, int) and run_id > 0
            and event in ("schedule", "push", "pull_request", "workflow_dispatch")
            and (not os.environ.get("GITHUB_SHA") or os.environ["GITHUB_SHA"] == source),
            "CURRENT_SOURCE_OR_RUN_MISMATCH")
    candidates = f120.validate(advisory, source)
    lanes = []
    for lane in ("Wingless", "Yggdrasil"):
        train_rows = [records_for(x, lane, "TRAIN") for x in candidates[lane]]
        # TRAIN contains all source environments but NO confirmation case.
        samples = [(bits, label) for rows in train_rows for r in rows
                   for bits, label in ((r["positive_bits"], 1),
                                       (r["negative_bits"], 0))]
        trained = {name: train(samples, name) for name in ("A", "B")}
        train_metrics = {name: [score(rows, name, trained[name][0])
                               for rows in train_rows] for name in ("A", "B")}
        selection = sorted(("A", "B"), key=lambda n:
                           (-sum(x["paired_correct"] for x in train_metrics[n]), n))[0]
        # Confirm only AFTER the above immutable TRAIN-only selection.
        confirmation = [records_for(x, lane, "CONFIRM") for x in candidates[lane]]
        confirm_metrics = {name: [score(rows, name, trained[name][0])
                                 for rows in confirmation]
                           for name in ("A", "B")}
        ctrls = {name: [control(rows, name) for rows in confirmation]
                 for name in ("CTRL_DEPTH2", "CTRL_ROLE",
                              "CTRL_CONSTANT", "CTRL_ORACLE")}
        all_control_accuracies = [v["balanced_accuracy"]
                                  for kind, v in ((k, x) for k in ctrls if k != "CTRL_ORACLE"
                                                  for x in ctrls[k])]
        selected_accuracies = [x["balanced_accuracy"] for x in confirm_metrics[selection]]
        # Two source environments have matched cohort size, so mean is valid.
        margin = round(sum(selected_accuracies)/2 - max(all_control_accuracies), 8)
        lanes.append({"lane": lane,
            "candidate_source_sha256": [x["source_candidate_sha256"] for x in candidates[lane]],
            "graph_training_pair_sha256": sha(train_rows),
            "graph_confirmation_pair_sha256": sha(confirmation),
            "weights_from_train_only": {k: [round(w, 8) for w in trained[k][0]]
                                         for k in ("A", "B")},
            "parameter_l2_movement": {k: trained[k][1] for k in ("A", "B")},
            "train_scores": train_metrics,
            "selected_train_only_model": selection,
            "confirm_scores": confirm_metrics,
            "frozen_untrained_controls": ctrls,
            "selected_vs_strongest_nonoracle_margin": margin,
            "development_relative_gain_0_05_observed": margin >= 0.05,
            "confirm_was_used_for_model_selection": False,
            "symbolic_equality_sensor_is_engineered_not_learned": True,
            "independent_scientific_transfer_established": False})
    return {"schema": SCHEMA, "source_sha": source, "run_id": run_id,
        "event": event, "freeze_sha256": freeze_sha,
        "advisory_sha256": sha(advisory), "lanes": lanes,
        "train_pairs_total": 96, "confirmation_pairs_total": 192,
        "actual_learned_parameter_updates": True, "models_per_lane": 2,
        "scientific_first_use_authorized": False, "originals_dispatched": 0,
        "scientific_acceptances": 0, "accepted_ref_mutations": 0,
        "optimizer_promotions": 0, "Codex_calls": 0, "paid_model_calls": 0,
        "new_scheduler": False, "ckb_plane_contact": False,
        "cloudflare_writes": 0, "mind_palace_writes": 0}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--advisory", required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--event", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    out = Path(args.output)
    require(out.parent.exists() and not out.exists(), "MUTABLE_OUTPUT_FORBIDDEN")
    result = execute(f118.load_report(args.advisory), args.source_ref,
                     args.run_id, args.event)
    with out.open("xb") as file:
        file.write(canonical(result))

if __name__ == "__main__":
    try:
        main()
    except (Invalid, f120.Invalid, f118.Quarantined, ValueError,
            TypeError, KeyError, OSError) as exc:
        print("F121_PUBLIC_LEARNED_BINDING_DEVELOPMENT=QUARANTINED " + str(exc),
              file=sys.stderr)
        raise SystemExit(1)
