"""F123: integer-only raw-symbol relation learning and disjoint challenge generator.

All data are public synthetic development. The exact symbolic matcher appears
only in generator validation/control reporting; no comparator, equality bit,
oracle truth, source token or label is a model input.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

import f120_generated_environment as f120
import f118_autonomy_feedback as f118

ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "reference/research-intake/f123-deterministic-transfer-freeze.json"
FREEZE_BLOB = "1dfa142e4ecdf6f20c05e415a24d284a3e81f59e"
SCHEMA = "forge.autonomy.f123.deterministic-raw-transfer-development.v1"
PARENT = "2e183a5c8d5df68f644a4a06f0ef689b88c9e223"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
WIDTH, EPOCHS = 24, 100
SEEDS = {
    "Wingless": {"TRAIN": range(96000, 96024), "CONFIRM": range(96100, 96148)},
    "Yggdrasil": {"TRAIN": range(97000, 97024), "CONFIRM": range(97100, 97148)},
}

class Invalid(ValueError):
    pass

def require(condition, code):
    if not condition:
        raise Invalid("F123_" + code)

def canonical(x):
    return f120.canonical(x)

def sha(x):
    return f120.sha(x)

def frozen():
    raw = FREEZE.read_bytes().replace(b"\r\n", b"\n")
    require(f120.blob(raw) == FREEZE_BLOB, "FREEZE_BLOB_DRIFT")
    spec = json.loads(raw)
    require(spec["schema"] == "forge.autonomy.f123.frozen-deterministic-raw-transfer-development.v1"
            and spec["parent_f122_head"] == PARENT
            and spec["parent_f122_raw_code_blob"] ==
                "23b2570c1e5be6fcee5b0bba12cd6e788332ab96"
            and spec["cohorts"]["training_epochs"] == EPOCHS
            and spec["cohorts"]["encoding_bits"] == WIDTH
            and spec["cohorts"]["training_hops"] == [2, 3]
            and spec["cohorts"]["confirmation_hops"] == [7, 9]
            and all(spec["authority"].values()),
            "FROZEN_IDENTITY_OR_AUTHORITY")
    require(spec["cohorts"]["training_seed_inclusive"] ==
            {"Wingless": [96000, 96023], "Yggdrasil": [97000, 97023]}
            and spec["cohorts"]["confirmation_seed_inclusive"] ==
            {"Wingless": [96100, 96147], "Yggdrasil": [97100, 97147]},
            "SEED_RANGE_DRIFT")
    return hashlib.sha256(raw).hexdigest()

def hash_int(*parts):
    # Counter-hash PRF; no Python random, platform RNG or floats.
    blob = "|".join(map(str, parts)).encode("utf-8")
    return int.from_bytes(hashlib.sha256(blob).digest()[:8], "big")

def graph(seed, vector, lane, phase):
    """Independent from the F122 graph/RNG path, with stronger heldout motifs."""
    require(lane in SEEDS and phase in ("TRAIN", "CONFIRM")
            and seed in SEEDS[lane][phase]
            and type(vector) is list and len(vector) == 3
            and all(type(v) is int and 0 <= v <= 3 for v in vector),
            "GRAPH_ARGUMENT_INVALID")
    hops = (2 if seed % 2 == 0 else 3) if phase == "TRAIN" else (
        7 if seed % 2 == 0 else 9)
    family = "f123-train-rel" if phase == "TRAIN" else "f123-unseen-heldout-role"
    namespace = lane + "/" + phase + "/" + str(seed) + "/" + "-".join(map(str, vector))
    nodes = [family + "/node/" + str(seed) + "/" + str(i) for i in range(hops + 1)]
    roles = [family + "/" + str((i * 3 + vector[2]) % (4 if phase == "TRAIN" else 13))
             for i in range(hops)]
    nside = (2 + vector[1]) if phase == "TRAIN" else (5 + vector[1])
    values = [10**9 + hash_int(namespace, "symbol", i) for i in range(hops + nside * 3 + 6)]
    require(len(set(values)) == len(values), "RAW_SYMBOL_COLLISION")
    positive = [(nodes[i], nodes[i + 1], roles[i], values[i], values[i + 1])
                for i in range(hops)]
    sides = []
    for j in range(nside):
        off = family + "/fork/" + str(seed) + "/" + str(j)
        origin = nodes[(j * 2 + vector[0]) % hops]
        positive.append((origin, off, "off-role/" + str(j),
                         values[hops + 1 + j], values[hops + nside + 1 + j]))
        sides.append((off, origin))
        if phase == "CONFIRM":
            # Unreachable by any required role; cycles + alternate terminals.
            positive.append((off, origin, "cycle-unseen/" + str(j),
                             values[hops + nside + 1 + j],
                             values[hops + 2 * nside + 1 + j]))
            positive.append((off, nodes[-1], "false-merge/" + str(j),
                             values[hops + 2 * nside + 1 + j], values[0]))
    break_idx = max(1, hops // 2)
    decoy_idx = hops  # first decoy and main path never share a required role
    negative = list(positive)
    active, decoy = list(negative[break_idx]), list(negative[decoy_idx])
    require(active[3] != decoy[3], "COUNTERFACTUAL_SYMBOL_NOT_DISTINCT")
    near_to_symbol = values[break_idx]
    hard_symbol = decoy[3]
    active[3], decoy[3] = decoy[3], active[3]
    negative[break_idx], negative[decoy_idx] = tuple(active), tuple(decoy)
    # Change physical edge ordering as well as topology family, but preserve
    # edge multiset *within* a paired positive/negative graph.
    pos_order = sorted(positive, key=lambda e: hash_int(namespace, "edge", e[0], e[1]))
    neg_order = sorted(negative, key=lambda e: hash_int(namespace, "edge", e[0], e[1]))
    case = {"seed": seed, "lane": lane, "phase": phase, "vector": list(vector),
            "start": nodes[0], "target": nodes[-1], "roles": roles, "hops": hops,
            "positive": pos_order, "negative": neg_order,
            "hard_symbol": hard_symbol, "near_to_symbol": near_to_symbol}
    topo = lambda es: sorted(tuple(edge[:3]) for edge in es)
    hist = lambda es: sorted(v for e in es for v in e[3:])
    require(topo(pos_order) == topo(neg_order)
            and hist(pos_order) == hist(neg_order)
            and f120.binding_solver(case, pos_order)
            and not f120.binding_solver(case, neg_order)
            and f120.role_only(case, pos_order)
            and f120.role_only(case, neg_order),
            "PAIR_GENERATOR_OR_ORACLE_INVARIANT")
    return case

def raw_junctions(case, edges):
    node, prev, out = case["start"], None, []
    for role in case["roles"]:
        choices = [e for e in edges if e[0] == node and e[2] == role]
        require(len(choices) == 1, "AMBIGUOUS_ROLE_PATH")
        edge = choices[0]
        if prev is not None:
            out.append((prev, edge[3]))
        prev, node = edge[4], edge[1]
    require(node == case["target"] and len(out) == case["hops"] - 1,
            "INCOMPLETE_RELATION_PATH")
    return out

def token(value, salt):
    digest = hashlib.sha256((salt + "/" + str(value)).encode()).digest()
    code = int.from_bytes(digest[:3], "big")
    return tuple((code >> bit) & 1 for bit in range(WIDTH))

def encodings(case):
    salt = "F123/" + case["lane"] + "/" + case["phase"] + "/" + str(case["seed"])
    symbols = {v for edge in case["positive"] + case["negative"] for v in edge[3:]}
    table = {v: token(v, salt) for v in symbols}
    require(len(set(table.values())) == len(symbols), "TOKEN_COLLISION")
    if case["phase"] == "CONFIRM" and case["seed"] % 2 == 0:
        # Frozen near-collision challenge: exact one-bit raw-token difference
        # while retaining two DISTINCT underlying variable identities.
        src = table[case["near_to_symbol"]]
        flipped = list(src)
        bit = case["seed"] % WIDTH
        flipped[bit] ^= 1
        near = tuple(flipped)
        require(near not in {bits for symbol, bits in table.items()
                             if symbol != case["hard_symbol"]},
                "ADVERSARIAL_TOKEN_COLLISION")
        table[case["hard_symbol"]] = near
    require(len(set(table.values())) == len(symbols),
            "TOKEN_ENCODING_NONINJECTIVE")
    return table

def encode_pair(pair, table):
    require(pair[0] in table and pair[1] in table, "OUT_OF_SOURCE_SYMBOL")
    return (table[pair[0]], table[pair[1]])

def features(pair):
    # Engineered bilinear inductive bias is disclosed, but neither equality nor
    # Hamming-distance is provided as an input; all weights are trained.
    left, right = pair
    require(len(left) == WIDTH and len(right) == WIDTH
            and all(bit in (0, 1) for bit in left + right),
            "ENCODING_SHAPE_INVALID")
    return (1,) + tuple((2 * a - 1) * (2 * b - 1)
                        for a, b in zip(left, right))

def train(samples):
    require(len(samples) == 96 and sum(label for _, label in samples) == 48,
            "TRAINING_COHORT_INVALID")
    weight = [0] * (WIDTH + 1)
    updates = 0
    for _ in range(EPOCHS):
        for pair, truth in samples:
            x = features(pair)
            signed_label = 1 if truth else -1
            margin = sum(a * b for a, b in zip(weight, x))
            if signed_label * margin <= 0:
                new_weight = [max(-256, min(256, w + signed_label * f))
                              for w, f in zip(weight, x)]
                require(new_weight != weight, "SATURATED_INTEGER_WEIGHTS")
                weight = new_weight
                updates += 1
    require(updates > 0 and len(weight) == WIDTH + 1
            and all(type(w) is int for w in weight),
            "INTEGER_TRAINING_NOT_PROVEN")
    return weight, updates

def predict(weight, pair):
    return sum(a * b for a, b in zip(weight, features(pair))) > 0

def make_rows(candidate, lane, phase):
    rows = []
    for seed in SEEDS[lane][phase]:
        case = graph(seed, candidate["vector"], lane, phase)
        lookup = encodings(case)
        p = raw_junctions(case, case["positive"])
        n = raw_junctions(case, case["negative"])
        diff = [i for i, (left, right) in enumerate(zip(p, n)) if left != right]
        require(len(diff) == 1 and p[diff[0]][0] == n[diff[0]][0],
                "NOT_ONE_CONTROLLED_DIFFERENCE")
        hard = phase == "CONFIRM" and seed % 2 == 0
        if hard:
            a = lookup[case["near_to_symbol"]]
            b = lookup[case["hard_symbol"]]
            require(sum(x != y for x, y in zip(a, b)) == 1,
                    "HELDOUT_NEAR_COLLISION_NOT_HARD")
        rows.append({"seed": seed, "hops": case["hops"], "hard": hard,
                     "graph_sha256": sha(case),
                     "positive": [encode_pair(z, lookup) for z in p],
                     "negative": [encode_pair(z, lookup) for z in n],
                     "changed_index": diff[0]})
    return rows

def train_samples(rows):
    return [(row["positive"][row["changed_index"]], 1) for row in rows] + [
            (row["negative"][row["changed_index"]], 0) for row in rows]

def score(rows, weight):
    tp = tn = paired = 0
    hard_correct = hard_count = 0
    for row in rows:
        pos = all(predict(weight, pair) for pair in row["positive"])
        neg = all(predict(weight, pair) for pair in row["negative"])
        good = int(pos and not neg)
        tp += int(pos)
        tn += int(not neg)
        paired += good
        if row["hard"]:
            hard_count += 1
            hard_correct += good
    return {"pairs": len(rows), "paired_correct": paired,
            "positive_correct": tp, "negative_correct": tn,
            "balanced_correct": tp + tn, "balanced_denominator": 2 * len(rows),
            "hard_pairs": hard_count, "hard_paired_correct": hard_correct}

def control(rows, arm):
    total = len(rows)
    if arm == "CTRL_RAW_EXACT":
        tp, tn, paired = total, total, total
    elif arm == "CTRL_ROLE":
        tp, tn, paired = total, 0, 0
    elif arm == "CTRL_DEPTH2":
        tp = sum(int(r["hops"] <= 2) for r in rows)
        tn, paired = total, tp
    elif arm == "CTRL_CONSTANT":
        tp, tn, paired = 0, total, 0
    else:
        raise Invalid("UNKNOWN_CONTROL")
    return {"pairs": total, "paired_correct": paired,
            "positive_correct": tp, "negative_correct": tn,
            "balanced_correct": tp + tn, "balanced_denominator": 2 * total,
            "hard_pairs": sum(int(r["hard"]) for r in rows),
            "hard_paired_correct": sum(int(r["hard"]) for r in rows)
                                   if arm == "CTRL_RAW_EXACT" else 0}

def execute(advisory, source, run_id, event):
    freeze_sha = frozen()
    require(type(source) is str and HEX40.fullmatch(source)
            and type(run_id) is int and run_id > 0
            and event in ("schedule", "push", "pull_request", "workflow_dispatch")
            and (not os.environ.get("GITHUB_SHA") or os.environ["GITHUB_SHA"] == source),
            "CURRENT_SOURCE_IDENTITY_MISMATCH")
    candidates = f120.validate(advisory, source)
    lanes = []
    for lane in ("Wingless", "Yggdrasil"):
        training = [make_rows(c, lane, "TRAIN") for c in candidates[lane]]
        samples = [sample for rows in training for sample in train_samples(rows)]
        learned, updates = train(samples)
        train_results = [score(rows, learned) for rows in training]
        holdout = [make_rows(c, lane, "CONFIRM") for c in candidates[lane]]
        confirm_results = [score(rows, learned) for rows in holdout]
        controls = {name: [control(rows, name) for rows in holdout] for name in
                    ("CTRL_RAW_EXACT", "CTRL_ROLE", "CTRL_DEPTH2", "CTRL_CONSTANT")}
        lanes.append({"lane": lane,
            "candidate_source_sha256": [c["source_candidate_sha256"] for c in candidates[lane]],
            "training_input_sha256": sha(training),
            "confirmation_input_sha256": sha(holdout),
            "integer_weights": learned, "integer_weight_sha256": sha(learned),
            "genuine_integer_updates": updates,
            "training": train_results, "confirmation": confirm_results,
            "controls": controls, "train_only_model": "I",
            "hard_confirmation_pairs": sum(x["hard_pairs"] for x in confirm_results),
            "hard_confirmation_paired_correct":
                sum(x["hard_paired_correct"] for x in confirm_results),
            "all_confirmation_pairs": sum(x["pairs"] for x in confirm_results),
            "all_confirmation_paired_correct":
                sum(x["paired_correct"] for x in confirm_results),
            "exact_symbolic_control_paired_correct": sum(
                x["paired_correct"] for x in controls["CTRL_RAW_EXACT"]),
            "independent_witnessed_scientific_transfer": False,
            "heldout_was_used_for_selection_or_training": False})
    return {"schema": SCHEMA, "source_sha": source, "run_id": run_id, "event": event,
            "freeze_sha256": freeze_sha, "advisory_sha256": sha(advisory),
            "model_parameters": WIDTH + 1, "training_pairs_total": 96,
            "confirmation_pairs_total": 192, "lanes": lanes,
            "integer_training_and_inference_only": True,
            "public_source_only": True, "external_challenge_witness": False,
            "scientific_first_use_authorized": False, "originals_dispatched": 0,
            "scientific_acceptances": 0, "accepted_ref_mutations": 0,
            "optimizer_promotions": 0, "Codex_calls": 0, "paid_model_calls": 0,
            "new_scheduler": False, "ckb_plane_contact": False,
            "cloudflare_writes": 0, "mind_palace_writes": 0}

def main():
    parser = argparse.ArgumentParser()
    for arg in ("--advisory", "--source-ref", "--output", "--event"):
        parser.add_argument(arg, required=True)
    parser.add_argument("--run-id", type=int, required=True)
    args = parser.parse_args()
    out = Path(args.output)
    require(out.parent.exists() and not out.exists(), "MUTABLE_OUTPUT")
    result = execute(f118.load_report(args.advisory), args.source_ref,
                     args.run_id, args.event)
    with out.open("xb") as stream:
        stream.write(canonical(result))

if __name__ == "__main__":
    try:
        main()
    except (Invalid, f120.Invalid, f118.Quarantined, TypeError,
            KeyError, ValueError, OSError) as exc:
        print("F123_SOURCE_ONLY=QUARANTINED " + str(exc), file=sys.stderr)
        raise SystemExit(1)
