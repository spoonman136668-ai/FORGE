"""F123 preregistered comparison arms and TRAIN-only provenance.

No F123 confirmation seeds, seal/open first use, original experiments or policy
promotion. Public graph observations only; exact symbolic is a separate ceiling.
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

import f118_autonomy_feedback as f118
import f120_generated_environment as f120
import f122_raw_transfer as f122
import f123_multipath_environment as env
import f123_learned_routing as learned

SCHEMA = "forge.autonomy.f123.train-only-controls-custody.v1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
ROOT = Path(__file__).resolve().parents[1]
ARMS = ("CTRL_F122_NO_ROUTING", "CTRL_FIXED_SOFT_PATH",
        "CTRL_ROLE_ONLY", "CTRL_QUERY_ONLY", "CTRL_EXACT_SYMBOLIC")

def require(test, code):
    env.require(test, code)

def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()

def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()

def source_blob(file):
    b = Path(file).read_bytes().replace(b"\r\n", b"\n")
    return f120.blob(b)

def training_rows(lane, vectors):
    require(lane in env.COHORTS and type(vectors) is list and len(vectors) == 2,
            "MISSING_FROZEN_TRAIN_VECTORS")
    rows = []
    for v in vectors:
        for seed in env.COHORTS[lane]["TRAIN"]:
            p, n = env.build(seed, v, lane, "TRAIN")
            rows.extend(((p, 1), (n, 0)))
    require(len(rows) == 96, "TRAIN_ROWS_DRIFT")
    return rows

def topology_features(observation):
    """20 topological/query-only statistics. Deliberately ignores slot bits."""
    env.validate_observation(observation)
    paths = learned.public_paths(observation)
    edges = observation["edges"]
    nodes = {observation["start"], observation["target"]}
    incoming, outgoing = {}, {}
    for e in edges:
        nodes.update((e["from"], e["to"]))
        outgoing[e["from"]] = outgoing.get(e["from"], 0) + 1
        incoming[e["to"]] = incoming.get(e["to"], 0) + 1
    hops, count = len(observation["roles"]), len(edges)
    degree = [outgoing.get(x, 0) for x in nodes]
    pcounts = [sum(1 for e in edges if e["role"] == r)
               for r in observation["roles"]]
    duplicates = sum(n * (n - 1) // 2 for n in outgoing.values())
    x = [1., hops / 6., count / 64., len(nodes) / 64.,
         len(paths) / 16., len(set(observation["roles"])) / 6.,
         outgoing.get(observation["start"], 0) / 16.,
         incoming.get(observation["target"], 0) / 16.,
         sum(degree) / 64., max(degree) / 16., min(degree) / 16.,
         duplicates / 64., min(pcounts) / 32., max(pcounts) / 32.,
         sum(pcounts) / 64., len(set((e["from"], e["to"]) for e in edges)) / 64.,
         sum(1 for n in nodes if outgoing.get(n, 0) > 1) / 32.,
         sum(1 for n in nodes if incoming.get(n, 0) > 1) / 32.,
         len(edges) / max(1., float(len(nodes))),
         len(paths) / max(1., float(count))]
    require(len(x) == 20 and all(math.isfinite(z) for z in x),
            "QUERY_ONLY_FEATURE_CONTRACT")
    return x

def fit_query_only(rows):
    require(len(rows) == 96 and sum(label for _, label in rows) == 48,
            "QUERY_ONLY_UNQUALIFIED_TRAIN_ROWS")
    weights = [0.] * 20
    for _ in range(100):
        grads = [0.] * len(weights)
        for obs, label in rows:
            x = topology_features(obs)
            p = learned.sigmoid(sum(a * b for a, b in zip(x, weights)))
            for k in range(20):
                grads[k] += (p - label) * x[k]
        for k in range(20):
            weights[k] = max(-8., min(8., weights[k] -
                            0.25 * max(-1., min(1., grads[k] / len(rows)))))
    require(len(weights) == 20 and all(math.isfinite(w) for w in weights),
            "QUERY_ONLY_PARAMETER_BOUND")
    return weights

def fixed_soft_path(obs):
    # Approximate raw-token Hamming heuristic, fixed 12/16 agreement threshold.
    # Intentionally NOT exact symbolic equality, and never a candidate feature.
    for route in learned.public_paths(obs):
        if all(sum(a == b for a, b in zip(left["dst_bits"], right["src_bits"])) >= 12
               for left, right in zip(route, route[1:])):
            return True
    return False

def f122_no_routing(obs, foundation):
    # Public lexicographic path only; never an oracle path or learned selector.
    routes = learned.public_paths(obs)
    route = min(routes, key=lambda p:
                tuple((e["from"], e["to"], e["role"]) for e in p))
    return all(f122.model_a(foundation,
               (tuple(left["dst_bits"]), tuple(right["src_bits"])))[0] >= .5
               for left, right in zip(route, route[1:]))

def predict_control(obs, arm, foundation, query_weights):
    require(arm in ARMS, "UNKNOWN_FROZEN_CONTROL")
    env.validate_observation(obs)
    if arm == "CTRL_F122_NO_ROUTING":
        return f122_no_routing(obs, foundation)
    if arm == "CTRL_FIXED_SOFT_PATH":
        return fixed_soft_path(obs)
    if arm == "CTRL_ROLE_ONLY":
        return bool(env.symbolic_routes(obs, role_only=True))
    if arm == "CTRL_QUERY_ONLY":
        return learned.sigmoid(sum(a * b for a, b in
                zip(topology_features(obs), query_weights))) >= .5
    return bool(env.symbolic_routes(obs))

def paired_score(rows, predict):
    require(len(rows) % 2 == 0, "PAIRING_MISMATCH")
    paired = tp = tn = 0
    for k in range(0, len(rows), 2):
        positive, yp = rows[k]
        negative, yn = rows[k + 1]
        require(yp == 1 and yn == 0, "LABEL_PAIR_DRIFT")
        yes, no = bool(predict(positive)), not bool(predict(negative))
        paired += int(yes and no)
        tp += int(yes)
        tn += int(no)
    return {"pairs": len(rows) // 2, "paired_correct": paired,
            "positive_correct": tp, "negative_correct": tn,
            "balanced_accuracy": round((tp + tn) / len(rows), 8)}

def shuffled_token_control(obs):
    """Fixed, label-blind intervention, no changed-junction/oracle coordinate."""
    env.validate_observation(obs)
    output = json.loads(json.dumps(obs))
    order = sorted(range(len(output["edges"])),
                   key=lambda k: tuple(output["edges"][k][x]
                                       for x in ("from", "to", "role")))
    require(len(order) >= 2, "TOO_FEW_EDGES_TO_INTERVENE")
    src = [list(output["edges"][i]["src_bits"]) for i in order]
    for k, i in enumerate(order):
        output["edges"][i]["src_bits"] = src[(k + 1) % len(order)]
    env.validate_observation(output)
    return output

def train_evidence(advisory, source, run_id, event):
    require(type(source) is str and HEX40.fullmatch(source)
            and type(run_id) is int and run_id > 0
            and event in ("push", "pull_request", "workflow_dispatch", "schedule")
            and (not os.environ.get("GITHUB_SHA") or os.environ["GITHUB_SHA"] == source),
            "SOURCE_IDENTITY_UNQUALIFIED")
    freeze_digest = env.frozen()
    candidates = f120.validate(advisory, source)
    lanes = []
    for lane in ("Wingless", "Yggdrasil"):
        entries = candidates[lane]
        vectors = [e["vector"] for e in entries]
        train = learned.train_lane(lane, vectors)
        require(train["confirmation_inputs_generated"] == 0
                and train["f122_source_git_blob"] == learned.F122_CODE_BLOB,
                "TRAIN_BOUNDARY_OR_F122_SOURCE_DRIFT")
        rows = training_rows(lane, vectors)
        require(learned.digest(rows) == train["train_graph_sha256"],
                "TRAIN_GRAPH_REPLAY_DRIFT")
        foundation = train["f122_training_foundation_weights"]
        require(learned.digest(foundation) == train["f122_training_foundation_sha256"],
                "FOUNDATION_WEIGHT_IDENTITY_DRIFT")
        weights = train["trained_weights"]
        require(all(learned.digest(weights[a]) == train["model_arms"][a]["weight_sha256"]
                    for a in ("A", "B")), "TRAINED_WEIGHT_DIGEST_MISMATCH")
        query_weights = fit_query_only(rows)
        controls = {arm: paired_score(rows, lambda o, a=arm:
                    predict_control(o, a, foundation, query_weights))
                    for arm in ARMS}
        require(controls["CTRL_EXACT_SYMBOLIC"]["paired_correct"] == len(rows) // 2,
                "SYMBOLIC_CEILING_INCORRECT")
        selection = train["train_selected_arm"]
        selected_weights = weights[selection]
        if selection == "A":
            pfn = lambda o: learned.predict_a(o, selected_weights, foundation)[0]
        else:
            pfn = lambda o: learned.predict_b(o, selected_weights)[0]
        differences = [abs(pfn(o) - pfn(shuffled_token_control(o)))
                       for o, _ in rows]
        lanes.append({"lane": lane,
                      "advisory_candidate_source_shas": [
                          e["source_candidate_sha256"] for e in entries],
                      "training_vectors": vectors,
                      "training_provenance_sha256": train["train_graph_sha256"],
                      "train_frozen_weights": weights,
                      "train_f122_foundation_weights": foundation,
                      "train_query_only_weights": query_weights,
                      "train_source_only_selection": selection,
                      "selected_model_weights_sha256": learned.digest(selected_weights),
                      "weights_sha256": {arm: learned.digest(weights[arm])
                                         for arm in ("A", "B")},
                      "query_only_weights_sha256": learned.digest(query_weights),
                      "model_arms": train["model_arms"],
                      "train_control_scores": controls,
                      "shuffle_sensitivity_mean": round(sum(differences) / len(differences), 10),
                      "fully_informed_symbolic_is_computational_ceiling": True,
                      "confirmation_inputs_generated": 0,
                      "source_only_no_scientific_acceptance": True})
    return {"schema": SCHEMA, "source_sha": source, "run_id": run_id,
            "event": event, "freeze_git_blob": env.FREEZE_BLOB,
            "freeze_sha256": freeze_digest,
            "f123_environment_git_blob": source_blob(env.__file__),
            "f123_learned_git_blob": source_blob(learned.__file__),
            "f123_controls_git_blob": source_blob(__file__),
            "f122_foundation_git_blob": learned.F122_CODE_BLOB,
            "advisory_sha256": sha(advisory), "lanes": lanes,
            "frozen_controls": list(ARMS), "cohorts": "TRAIN_ONLY",
            "confirmation_inputs_generated": 0, "scientific_first_use": False,
            "scientific_acceptances": 0, "originals_dispatched": 0,
            "accepted_ref_mutations": 0, "optimizer_promotions": 0,
            "Codex_calls": 0, "paid_model_calls": 0, "new_scheduler": False,
            "ckb_plane_contact": False, "cloudflare_writes": 0,
            "mind_palace_writes": 0}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--advisory", required=True)
    p.add_argument("--source-ref", required=True)
    p.add_argument("--run-id", type=int, required=True)
    p.add_argument("--event", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    out = Path(a.output)
    require(out.parent.is_dir() and not out.exists(), "OUTPUT_REPLACEMENT_FORBIDDEN")
    proof = train_evidence(f118.load_report(a.advisory),
                           a.source_ref, a.run_id, a.event)
    with out.open("xb") as fp:
        fp.write(canonical(proof))

if __name__ == "__main__":
    try:
        main()
    except (env.Invalid, f118.Quarantined, f120.Invalid,
            ValueError, KeyError, TypeError, OSError) as err:
        print("F123_TRAIN_CUSTODY=QUARANTINED " + str(err), file=sys.stderr)
        raise SystemExit(1)
