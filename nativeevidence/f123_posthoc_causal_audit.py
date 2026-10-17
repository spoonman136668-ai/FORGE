"""F123 read-only TRAIN causal audit, exact qualified F123 source and frozen weights.

This diagnostics-only implementation cannot select, train, tune, read CONFIRM,
run sealed originals, or grant scientific acceptance. Causal route witnesses
are computed *after* model predictions, from already-public TRAIN graphs.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import f120_generated_environment as f120
import f123_cross_os_custody as custody
import f123_multipath_environment as env
import f123_learned_routing as learned
import f123_controls as controls

PARENT_HEAD = "7882849a59964f412a87589be653114e7bf64d52"
SOURCE_BLOBS = {
    "f122_raw_transfer.py": "23b2570c1e5be6fcee5b0bba12cd6e788332ab96",
    "f123_multipath_environment.py": "73d1775710a9f36b5ea02143a013316645dde48c",
    "f123_learned_routing.py": "6f90560c331e20967d0b13892668da8060e06cdc",
    "f123_controls.py": "02b53fd8bc9623c904ca6b6924d2189934d4b854",
    "f123_cross_os_custody.py": "dcc6834623dbef5833407b9858e16961e2bacdfe"
}
SCHEMA = "forge.autonomy.f123.posthoc-train-causal-cost-audit.v1"
TRAIN_REPORT_SHA = "12da879272212b899c6b942004ff38dc21ffa6bb20e7a81eac21d691746b474d"

def require(x, code):
    env.require(x, "AUDIT_" + code)

def sources():
    env.frozen()
    for name, expected in SOURCE_BLOBS.items():
        file = Path(__file__).with_name(name)
        require(f120.blob(file.read_bytes().replace(b"\r\n", b"\n")) == expected,
                "QUALIFIED_FOUNDATION_DRIFT_" + name)

def edge_key(e):
    return (e["from"], e["to"], e["role"])

def public_edge_id(e):
    return (e["from"], e["to"], e["role"], tuple(e["src_bits"]), tuple(e["dst_bits"]))

def route_key(path):
    return hashlib.sha256(json.dumps([public_edge_id(e) for e in path],
                          sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def route_witness(obs, weights):
    """Independent public-route reconstruction of B attention *after* inference."""
    require(len(weights) == 20, "B_WEIGHT_SHAPE")
    scores = []
    for path in learned.public_paths(obs):
        mass = 1.
        for step, (left, right) in enumerate(zip(path, path[1:]), start=1):
            raw = learned.bits(left["dst_bits"], right["src_bits"])
            raw.append(step / len(obs["roles"]))
            mass *= learned.sigmoid(sum(w * v for w, v in zip(weights[:-2], raw)))
        valid = all(a["dst_bits"] == b["src_bits"] for a, b in zip(path, path[1:]))
        scores.append({"route_sha256": route_key(path), "mass": mass,
                       "symbolic_valid_posthoc": valid,
                       "edges": [edge_key(e) for e in path]})
    scores.sort(key=lambda s: (-s["mass"], s["route_sha256"]))
    reconstruction = learned.sigmoid(weights[-2] *
                     (sum(row["mass"] for row in scores) - weights[-1]))
    actual = learned.predict_b(obs, weights)[0]
    require(abs(reconstruction - actual) <= 1e-12,
            "INDEPENDENT_RECONSTRUCTION_DRIFT")
    return actual, scores

def model_cost(obs):
    """Deterministic structural workload proxies, never invented elapsed times."""
    routes = learned.public_paths(obs)
    states = [(obs["start"], None)]
    scans = matches = bit_mac = 0
    for i, role in enumerate(obs["roles"]):
        nxt = []
        for node, previous in states:
            for edge in obs["edges"]:
                scans += 1
                if edge["from"] == node and edge["role"] == role:
                    if previous is not None:
                        matches += 1
                        bit_mac += 18
                    nxt.append((edge["to"], edge["dst_bits"]))
        states = nxt
    # Approximate fixed soft route work assuming no short circuit.
    fixed_bit_comparisons_upper = 16 * sum(len(p)-1 for p in routes)
    return {"b_public_edge_scans": scans, "b_learned_attention_junctions": matches,
            "b_feature_multiply_adds": bit_mac,
            "fixed_raw_bit_comparisons_upper": fixed_bit_comparisons_upper,
            "public_route_count": len(routes)}

def edge_ablation(obs, weights):
    """Invert each downstream route-edge source slot, with no oracle coordinates."""
    actual = learned.predict_b(obs, weights)[0]
    ids = set()
    for route in learned.public_paths(obs):
        for e in route[1:]:
            ids.add(public_edge_id(e))
    diffs = []
    for ident in sorted(ids):
        candidate = copy.deepcopy(obs)
        matches = [edge for edge in candidate["edges"] if public_edge_id(edge) == ident]
        require(len(matches) == 1, "MULTIEDGE_PUBLIC_TOKEN_ID_AMBIGUITY")
        matches[0]["src_bits"] = [1-v for v in matches[0]["src_bits"]]
        change = abs(learned.predict_b(candidate, weights)[0] - actual)
        diffs.append((ident[:3], change))
    return diffs

def paired_audit(positive, negative, weights):
    env.admit(positive, negative)
    yes, pos_routes = route_witness(positive, weights)
    no, neg_routes = route_witness(negative, weights)
    from collections import Counter
    topologies = set(edge_key(e) for e in positive["edges"])
    require(topologies == set(edge_key(e) for e in negative["edges"]),
            "EDGE_TOPOLOGY_DRIFT")
    def group(obs, topo):
        return Counter((tuple(e["src_bits"]), tuple(e["dst_bits"]))
                       for e in obs["edges"] if edge_key(e) == topo)
    altered = set()
    swapped_edge_count = 0
    for key in topologies:
        pos, neg = group(positive, key), group(negative, key)
        if pos != neg:
            altered.add(key)
            swapped_edge_count += sum((pos - neg).values())
    require(swapped_edge_count == 2 and len(altered) >= 1,
            "MATCHED_MULTIEDGE_INTERVENTION_DRIFT")
    abl = edge_ablation(positive, weights)
    require(bool(abl), "NO_ELIGIBLE_CAUSAL_ABLATION")
    biggest = max(x[1] for x in abl)
    top_keys = {key for key, val in abl if abs(val-biggest) <= 1e-14}
    top_pos = pos_routes[0]
    top_neg = neg_routes[0]
    summary = {"positive_prob": round(yes, 12), "negative_prob": round(no, 12),
               "paired_correct": yes >= .5 and no < .5,
               "counterfactual_probability_gap": round(yes-no, 12),
               "positive_top_route_symbolically_valid": top_pos["symbolic_valid_posthoc"],
               "negative_top_route_symbolically_valid": top_neg["symbolic_valid_posthoc"],
               "positive_top_route_id": top_pos["route_sha256"],
               "negative_top_route_id": top_neg["route_sha256"],
               "positive_top_route_mass": round(top_pos["mass"], 12),
               "negative_top_route_mass": round(top_neg["mass"], 12),
               "intervention_changed_edges": len(altered),
               "max_nonprivileged_edge_ablation_delta": round(biggest, 12),
               "max_ablation_touches_counterfactual_edge": bool(top_keys & altered),
               "cost": model_cost(positive)}
    return summary

def audit(ubuntu_dir, windows_dir):
    sources()
    parity = custody.audit(ubuntu_dir, windows_dir)
    u, uh = custody.read_receipt(ubuntu_dir)
    require(uh == TRAIN_REPORT_SHA and parity["ubuntu_train_receipt_sha256"] == uh
            and u["source_sha"] == PARENT_HEAD
            and parity["source_sha"] == PARENT_HEAD
            and u["freeze_git_blob"] == env.FREEZE_BLOB,
            "IMMUTABLE_TRAIN_PROVENANCE_DRIFT")
    lanes = []
    for row in u["lanes"]:
        name = row["lane"]
        require(row["train_source_only_selection"] in ("A", "B")
                and row["confirmation_inputs_generated"] == 0
                and len(row["training_vectors"]) == 2,
                "UNEXPECTED_TRAIN_SELECTION")
        weights = row["train_frozen_weights"]["B"]
        summaries = []
        for vector in row["training_vectors"]:
            for seed in env.COHORTS[name]["TRAIN"]:
                pair = env.build(seed, vector, name, "TRAIN")
                summaries.append(paired_audit(*pair, weights))
        require(len(summaries) == 48, "TRAIN_SET_DRIFT")
        paired = sum(r["paired_correct"] for r in summaries)
        require(paired == row["model_arms"]["B"]["train_score"]["paired_correct"],
                "REPLAY_SCORE_DRIFT")
        fixed = row["train_control_scores"]["CTRL_FIXED_SOFT_PATH"]["paired_correct"]
        selected = row["train_source_only_selection"]
        target = .05
        prior = row["model_arms"][selected]["train_score"]["paired_correct"]
        delta = (prior-fixed) / 48
        means = lambda k: round(sum(r[k] for r in summaries)/len(summaries), 10)
        lanes.append({"lane": name, "train_pairs": 48,
                      "selected_train_arm": selected,
                      "selected_train_pairs_correct": prior,
                      "fixed_heuristic_pairs_correct": fixed,
                      "train_margin_points": round(delta, 9),
                      "preregistered_min_margin_points": target,
                      "train_threshold_met": delta >= target,
                      "b_paired_correct_replayed": paired,
                      "b_counterfactual_gap_mean": means("counterfactual_probability_gap"),
                      "b_counterfactual_gap_positive_pairs": sum(r["counterfactual_probability_gap"] > 0 for r in summaries),
                      "b_positive_top_route_valid": sum(r["positive_top_route_symbolically_valid"] for r in summaries),
                      "b_negative_top_route_valid": sum(r["negative_top_route_symbolically_valid"] for r in summaries),
                      "b_max_ablation_matches_changed_edge": sum(r["max_ablation_touches_counterfactual_edge"] for r in summaries),
                      "b_ablation_max_abs_delta_mean": means("max_nonprivileged_edge_ablation_delta"),
                      "b_public_edge_scans_mean": round(sum(r["cost"]["b_public_edge_scans"] for r in summaries)/48, 6),
                      "b_feature_mult_adds_mean": round(sum(r["cost"]["b_feature_multiply_adds"] for r in summaries)/48, 6),
                      "fixed_raw_bit_comparisons_upper_mean": round(sum(r["cost"]["fixed_raw_bit_comparisons_upper"] for r in summaries)/48, 6),
                      "resource_matched_control_qualification": "NOT_ESTABLISHED_COUNTS_ONLY",
                      "records_sha256": controls.sha(summaries),
                      "diagnostic_training_records": summaries})
    return {"schema": SCHEMA, "foundational_exact_commit": PARENT_HEAD,
            "original_f123_train_receipt_sha256": uh,
            "cross_os_parity_verified": True, "training_only": True,
            "confirmation_cases_constructed": 0,
            "preregistered_threshold_changed": False,
            "controls_changed": False,
            "f123_promotion_allowed": False,
            "first_use_authorized": False,
            "originals_dispatched": 0,
            "learned_generalization_claim": False,
            "lanes": lanes}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ubuntu-dir", required=True)
    parser.add_argument("--windows-dir", required=True)
    parser.add_argument("--output", required=True)
    a = parser.parse_args()
    output = Path(a.output)
    require(output.parent.is_dir() and not output.exists(), "IMMUTABLE_OUTPUT_BOUNDARY")
    result = audit(a.ubuntu_dir, a.windows_dir)
    output.write_text(json.dumps(result, sort_keys=True, separators=(",", ":"))+"\n",
                      encoding="utf-8")

if __name__ == "__main__":
    try:
        main()
    except (env.Invalid, custody.Invalid, ValueError, OSError, KeyError, TypeError) as exc:
        print("F123_TRAIN_CAUSAL_AUDIT=QUARANTINED: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
