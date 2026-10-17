"""F123 learned graph routing; TRAIN-only development, never scientific admission.

Arm A ranks *all* public role-compatible routes using frozen F122 raw-token
compatibility plus trainable query-path weights. Arm B propagates learned
token-conditioned attention through the full public graph for every query hop.
Neither receives graph truth, selected edges, precomputed equality, or holdout.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import f120_generated_environment as f120
import f122_raw_transfer as f122
import f123_multipath_environment as env

F122_CODE_BLOB = "23b2570c1e5be6fcee5b0bba12cd6e788332ab96"
EPOCHS = 100
LIMIT = 768

def require(test, code):
    env.require(test, code)

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def sigmoid(x):
    x = max(-40., min(40., x))
    return 1. / (1. + math.exp(-x))

def bits(left, right):
    require(len(left) == len(right) == 16, "INVALID_TOKEN_WIDTH")
    # Raw token bit interactions; no equality bit or oracle feature.
    return [1.] + [(2 * a - 1) * (2 * b - 1) for a, b in zip(left, right)]

def public_paths(obs):
    env.validate_observation(obs)
    paths = [(obs["start"], ())]
    for role in obs["roles"]:
        nxt = []
        for node, prefix in paths:
            for edge in obs["edges"]:
                if edge["from"] == node and edge["role"] == role:
                    nxt.append((edge["to"], prefix + (edge,)))
                    require(len(nxt) <= 256, "PATH_BUDGET_EXCEEDED")
        paths = nxt
    complete = [path for node, path in paths if node == obs["target"]]
    require(complete and len(complete) <= 256, "NO_PUBLIC_QUERY_ROUTES")
    return complete

def frozen_f122(lane, vectors):
    raw = Path(f122.__file__).read_bytes().replace(b"\r\n", b"\n")
    require(f120.blob(raw) == F122_CODE_BLOB, "F122_SOURCE_IDENTITY_DRIFT")
    f122.frozen()
    rows = [r for v in vectors for r in f122.build_rows(
        {"vector": list(v)}, lane, "TRAIN")]
    samples = f122.train_samples(rows)
    # This is the immutable F122 architecture and F122 TRAIN source only.
    return f122.train(samples, "A")[0]

def a_features(obs, frozen_weights):
    out = []
    for route in public_paths(obs):
        margins = []
        for left, right in zip(route, route[1:]):
            token_pair = (tuple(left["dst_bits"]), tuple(right["src_bits"]))
            p, _ = f122.model_a(frozen_weights, token_pair)
            margins.append(2. * p - 1.)
        require(margins, "EMPTY_ROUTE_JUNCTION")
        out.append([1., sum(margins) / len(margins), min(margins)])
    return out

def predict_a(obs, weights, foundation):
    features = a_features(obs, foundation)
    scores = [sum(w * x for w, x in zip(weights, row)) for row in features]
    highest = max(scores)
    exps = [math.exp(v - highest) for v in scores]
    total = sum(exps)
    log_mean_exp = highest + math.log(total / len(scores))
    prob = sigmoid(log_mean_exp)
    share = [v / total for v in exps]
    deriv = [sum(s * row[k] for s, row in zip(share, features))
             for k in range(len(weights))]
    return prob, deriv

def predict_b(obs, weights):
    """Recurrent graph propagation, no externally selected or enumerated path."""
    env.validate_observation(obs)
    raw = weights[:-2]
    gain, cutoff = weights[-2:]
    states = [(obs["start"], None, 1., [0.] * len(raw))]
    for step, role in enumerate(obs["roles"]):
        nxt = []
        for node, previous, mass, derivative in states:
            for edge in obs["edges"]:
                if edge["from"] != node or edge["role"] != role:
                    continue
                if previous is None:
                    attention, grad_att = 1., [0.] * len(raw)
                else:
                    feat = bits(previous, edge["src_bits"])
                    feat.append(float(step) / len(obs["roles"]))
                    require(len(feat) == len(raw), "ATTENTION_WIDTH_MISMATCH")
                    attention = sigmoid(sum(w * x for w, x in zip(raw, feat)))
                    grad_att = [attention * (1. - attention) * x for x in feat]
                next_grad = [g * attention + mass * da
                             for g, da in zip(derivative, grad_att)]
                nxt.append((edge["to"], edge["dst_bits"], mass * attention, next_grad))
                require(len(nxt) <= 256, "PROPAGATION_BUDGET_EXCEEDED")
        states = nxt
    surviving = [(m, grad) for node, _, m, grad in states if node == obs["target"]]
    require(surviving, "NO_PUBLIC_QUERY_ROUTES")
    amount = sum(m for m, _ in surviving)
    d_amount = [sum(grad[k] for _, grad in surviving)
                for k in range(len(raw))]
    p = sigmoid(gain * (amount - cutoff))
    return p, [gain * v for v in d_amount] + [amount - cutoff, -gain]

def fit(rows, arm, foundation=None):
    require(arm in ("A", "B"), "INVALID_ARM")
    require(len(rows) == 96 and sum(label for _, label in rows) == 48,
            "TRAINING_COHORT_IDENTITY")
    if arm == "A":
        require(foundation is not None and len(foundation) == 17,
                "UNQUALIFIED_F122_FOUNDATION")
        weights = [-1.2, 0.4, 0.4]
        forward = lambda obs, w: predict_a(obs, w, foundation)
        lr = 0.25
    else:
        weights = [-1.2] + [0.17] * 16 + [0.05] + [3.0, 0.5]
        forward = predict_b
        lr = 0.22
    initial = list(weights)
    for _ in range(EPOCHS):
        grads = [0.] * len(weights)
        for obs, label in rows:
            prob, dp = forward(obs, weights)
            for k, d in enumerate(dp):
                grads[k] += (prob - label) * d
        for k, value in enumerate(grads):
            step = max(-1., min(1., value / len(rows)))
            weights[k] = max(-8., min(8., weights[k] - lr * step))
        require(all(math.isfinite(v) for v in weights), "NONFINITE_UPDATE")
    movement = sum((a - b) ** 2 for a, b in zip(initial, weights)) ** .5
    require(movement > 0.0001 and len(weights) + (17 if arm == "A" else 0) <= LIMIT,
            "NO_LEARNING_OR_PARAMETER_LIMIT")
    return weights, movement

def score(rows, arm, weights, foundation=None):
    correctly = paired = 0
    for i in range(0, len(rows), 2):
        pos, yp = rows[i]
        neg, yn = rows[i + 1]
        require(yp == 1 and yn == 0, "TRAIN_PAIR_ORDER_DRIFT")
        f = (lambda obs: predict_a(obs, weights, foundation)[0]) if arm == "A" else (
            lambda obs: predict_b(obs, weights)[0])
        yes, no = f(pos) >= 0.5, f(neg) < 0.5
        correctly += int(yes) + int(no)
        paired += int(yes and no)
    return {"pairs": len(rows) // 2, "paired_correct": paired,
            "balanced_accuracy": round(correctly / len(rows), 8)}

def train_lane(lane, vectors):
    env.frozen()
    require(lane in env.COHORTS and type(vectors) is list and len(vectors) == 2
            and all(type(v) is list and len(v) == 3
                    and all(type(x) is int and 0 <= x <= 3 for x in v)
                    for v in vectors) and vectors[0] != vectors[1],
            "CANDIDATE_SOURCE_VECTOR_INVALID")
    rows = []
    for v in vectors:
        for seed in env.COHORTS[lane]["TRAIN"]:
            positive, negative = env.build(seed, v, lane, "TRAIN")
            rows.extend(((positive, 1), (negative, 0)))
    require(len(rows) == 96, "TRAIN_SIZE_DRIFT")
    f122weights = frozen_f122(lane, vectors)
    learned = {}
    for arm in ("A", "B"):
        weights, movement = fit(rows, arm, f122weights if arm == "A" else None)
        learned[arm] = {"weights": weights, "movement": movement,
                        "train_score": score(rows, arm, weights, f122weights)}
    selected = sorted(learned, key=lambda a:
                      (-learned[a]["train_score"]["paired_correct"], a))[0]
    return {"lane": lane, "phase": "TRAIN_ONLY", "train_graph_sha256": digest(rows),
            "f122_training_foundation_sha256": digest(f122weights),
            "f122_source_git_blob": F122_CODE_BLOB,
            "model_arms": {arm: {"weight_sha256": digest(x["weights"]),
                                "parameters": len(x["weights"]) +
                                    (17 if arm == "A" else 0),
                                "movement": round(x["movement"], 8),
                                "train_score": x["train_score"]}
                           for arm, x in learned.items()},
            "train_selected_arm": selected,
            "train_candidate_vectors": [list(v) for v in vectors],
            "f122_training_foundation_weights": list(f122weights),
            "trained_weights": {arm: list(learned[arm]["weights"])
                                for arm in ("A", "B")},
            "confirmation_inputs_generated": 0,
            "originals_dispatched": 0,
            "scientific_acceptances": 0,
            "optimizer_promotions": 0}
