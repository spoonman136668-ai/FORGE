"""F123 TRAIN-only causal routing and resource diagnostic (not acceptance).

Uses exact saved Arm-B weights, the public synthetic TRAIN graph and a
label-blind model trace. A public exact symbolic solver is used only AFTER
ablation selection, for independent reference-label diagnosis. No CONFIRM.
"""
from __future__ import annotations
from collections import Counter
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys

import f120_generated_environment as f120
import f123_controls as ctl
import f123_learned_routing as learn
import f123_multipath_environment as env

SCHEMA = "forge.autonomy.f123.train-only-route-causal-diagnostic.v1"
LANES = ("Wingless", "Yggdrasil")
EPS = 1e-10

def need(ok, why):
    env.require(bool(ok), "CAUSAL_AUDIT_" + why)

def sealed(path):
    p = Path(path)
    raw = p.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    seal = p.with_suffix(".sha256")
    need(seal.exists() and seal.read_text(encoding="utf-8").strip() ==
         sha + "  " + p.name, "SHA_RECEIPT_MISMATCH")
    return json.loads(raw.decode("utf-8-sig")), sha

def sorted_routes(g):
    env.validate_observation(g)
    return sorted(learn.public_paths(g),
                  key=lambda p: json.dumps(p, sort_keys=True, separators=(",", ":")))

def b_trace(g, weights):
    """After-the-fact mass decomposition; exact forward equivalence required."""
    need(type(weights) is list and len(weights) == 20 and
         all(type(v) in (int, float) and math.isfinite(v) and abs(v) <= 8
             for v in weights), "WEIGHTS")
    routes = sorted_routes(g)
    masses = []
    for path in routes:
        mass = 1.
        for step, (a, b) in enumerate(zip(path, path[1:]), start=1):
            x = learn.bits(a["dst_bits"], b["src_bits"])
            x.append(float(step) / len(g["roles"]))
            need(len(x) == 18, "QUERY_FEATURE_WIDTH")
            mass *= learn.sigmoid(sum(a * b for a, b in zip(x, weights[:18])))
        masses.append(mass)
    predicted = learn.predict_b(g, weights)[0]
    reconstructed = learn.sigmoid(weights[18] * (sum(masses) - weights[19]))
    need(abs(predicted - reconstructed) <= EPS, "UNFAITHFUL_MODEL_TRACE")
    total = sum(masses)
    shares = [v / total for v in masses]
    best = min(range(len(routes)), key=lambda i:
               (-shares[i], learn.digest(routes[i])))
    return {"probability": predicted, "path": routes[best],
            "winner_sha256": learn.digest(routes[best]),
            "top_share": shares[best], "path_count": len(routes),
            "hops": len(g["roles"]), "trace_error": abs(predicted-reconstructed)}

def parity(g):
    return (Counter((e["from"], e["to"], e["role"]) for e in g["edges"]),
            Counter(tuple(bits) for e in g["edges"]
                    for bits in (e["src_bits"], e["dst_bits"])))

def interventions(g, top_route):
    """Swap a model-selected interior edge with wrong-role decoy, then null swap.

    No truth/seed/privileged junction enters the intervention selector.
    Both preserve entire graph role/topology and raw token histograms.
    """
    env.validate_observation(g)
    need(len(top_route) >= 2, "ROUTE_TOO_SHORT")
    chosen = [i for i, e in enumerate(g["edges"]) if e == top_route[1]]
    need(len(chosen) == 1, "AMBIGUOUS_PUBLIC_EDGE")
    junk = sorted([i for i,e in enumerate(g["edges"])
                   if e["role"] not in g["roles"]],
                  key=lambda i: (g["edges"][i]["from"], g["edges"][i]["to"], g["edges"][i]["role"]))
    need(len(junk) >= 2 and chosen[0] not in junk, "MISSING_OFFPATH_CONTROL")
    def swap(i, j):
        copyg = copy.deepcopy(g)
        before = parity(copyg)
        left, right = copyg["edges"][i], copyg["edges"][j]
        need(left["src_bits"] != right["src_bits"], "IDENTICAL_TOKENS")
        left["src_bits"], right["src_bits"] = right["src_bits"], left["src_bits"]
        env.validate_observation(copyg)
        need(parity(copyg) == before, "INTERVENTION_MARGINAL_DRIFT")
        return copyg
    on, off = swap(chosen[0], junk[0]), swap(junk[0], junk[1])
    need(on != g and off != g and on != off, "INERT_ABLATION")
    return on, off

def resource_proxy(g, trace):
    """Symbolic feature-work *upper proxies*, NOT elapsed runtime or cost parity."""
    hops, routes = trace["hops"], trace["path_count"]
    need(2 <= hops <= 3 and routes >= 2, "NONTRAIN_STRUCTURES")
    joins = routes * (hops - 1)
    return {"edges":len(g["edges"]), "hops":hops, "routes":routes,
            "arm_b_query_feature_multiply_proxy":joins * 18,
            "f122_single_path_pairwise_bit_proxy":(hops-1) * 16,
            "fixed_all_path_bit_proxy":joins * 16,
            "relative_b_to_f122_proxy":round(18*routes/16, 8),
            "wallclock_benchmark":False, "resource_equivalence_proven":False}

def analyze_lane(lane, saved, expected):
    need(saved.get("lane") == lane and saved.get("training_vectors") == expected
         and saved.get("confirmation_inputs_generated") == 0
         and saved.get("source_only_no_scientific_acceptance") is True
         and saved.get("train_source_only_selection") == "B",
         "SAVED_TRAIN_SELECTION_OR_COHORT")
    weights = saved["train_frozen_weights"]["B"]
    need(learn.digest(weights) == saved["selected_model_weights_sha256"]
         == saved["model_arms"]["B"]["weight_sha256"]
         and len(weights) == 20, "SELECTED_WEIGHT_IDENTITY")
    rows = ctl.training_rows(lane, expected)
    need(learn.digest(rows) == saved["training_provenance_sha256"],
         "TRAIN_GRAPH_REPLAY_DRIFT")
    strata, details = [], []
    for source_index, vector in enumerate(expected):
        metrics = {"train_pairs":24, "correct_pairs":0, "valid_route_destroyed":0,
                   "onroute_label_flip":0, "offroute_prediction_flip":0,
                   "onroute_abs_probability_delta_sum":0.,
                   "offroute_abs_probability_delta_sum":0.}
        for seed_index, seed in enumerate(env.COHORTS[lane]["TRAIN"]):
            offset = source_index*48 + seed_index*2
            p, n = rows[offset][0], rows[offset+1][0]
            need(rows[offset][1] == 1 and rows[offset+1][1] == 0
                 and env.symbolic_routes(p) == 1 and env.symbolic_routes(n) == 0,
                 "TRAIN_LABELS_DRIFT")
            tp, tn = b_trace(p, weights), b_trace(n, weights)
            metrics["correct_pairs"] += int(tp["probability"] >= .5 and
                                            tn["probability"] < .5)
            for label, g, trace in ((1,p,tp),(0,n,tn)):
                on, off = interventions(g, trace["path"])
                after_on, after_off = b_trace(on, weights), b_trace(off, weights)
                delta_on = abs(after_on["probability"] - trace["probability"])
                delta_off = abs(after_off["probability"] - trace["probability"])
                need(delta_off <= EPS and
                     bool(env.symbolic_routes(off)) == bool(label),
                     "OFFROUTE_NULL_NOT_NULL")
                metrics["onroute_abs_probability_delta_sum"] += delta_on
                metrics["offroute_abs_probability_delta_sum"] += delta_off
                metrics["offroute_prediction_flip"] += int(
                    (trace["probability"]>=.5) != (after_off["probability"]>=.5))
                metrics["onroute_label_flip"] += int(
                    (trace["probability"]>=.5) != (after_on["probability"]>=.5))
                if label:
                    metrics["valid_route_destroyed"] += int(env.symbolic_routes(on)==0)
                details.append({"vector_index":source_index, "train_seed":seed,
                    "label":label, "graph_sha256":learn.digest(g),
                    "model_selected_path_sha256":trace["winner_sha256"],
                    "model_path_share":round(trace["top_share"],12),
                    "prob_before":round(trace["probability"],12),
                    "prob_on_route_swap":round(after_on["probability"],12),
                    "prob_off_route_null":round(after_off["probability"],12),
                    "truth_after_on_route":bool(env.symbolic_routes(on)),
                    "truth_after_null":bool(env.symbolic_routes(off)),
                    "resource_upper_proxies":resource_proxy(g,trace),
                    "truth_used_in_path_selection":False})
        strata.append({"vector_index":source_index, "vector_sha256":learn.digest(vector),
                      **{k:round(v,12) if type(v) is float else v
                         for k,v in metrics.items()}})
    total = sum(x["correct_pairs"] for x in strata)
    need(total == saved["model_arms"]["B"]["train_score"]["paired_correct"],
         "FROZEN_TRAIN_SCORE_MISMATCH")
    strong = max(row["paired_correct"] for arm,row in
                 saved["train_control_scores"].items()
                 if arm!="CTRL_EXACT_SYMBOLIC")
    need(len(details)==96, "TOTAL_GRAPH_COUNT")
    margin = round((total-strong)/48,8)
    return {"lane":lane, "selected_arm":"B",
            "train_pairs":48, "paired_correct":total,
            "strongest_nonoracle_control_correct":strong,
            "train_only_margin":margin, "frozen_margin_met":margin>=.05,
            "training_selected_weights_sha256":learn.digest(weights),
            "causal_traces":details, "strata":strata,
            "resource_matched":False, "scientific_claim_earned":False}

def execute(advisory, saved, source, advisory_sha, saved_sha):
    need(type(source) is str and re.fullmatch(r"[0-9a-f]{40}",source)
         and saved.get("source_sha")==source
         and saved.get("advisory_sha256")==ctl.sha(advisory)
         and saved.get("freeze_git_blob")==env.FREEZE_BLOB
         and saved.get("freeze_sha256")==env.frozen()
         and saved.get("cohorts")=="TRAIN_ONLY"
         and saved.get("confirmation_inputs_generated")==0
         and saved.get("scientific_first_use") is False
         and saved.get("optimizer_promotions")==0
         and saved.get("scientific_acceptances")==0,
         "SOURCE_OR_AUTHORITY")
    candidates = f120.validate(advisory,source)
    need([x.get("lane") for x in saved["lanes"]]==list(LANES),
         "INDEPENDENT_LANE_ORDER")
    lanes=[analyze_lane(lane, record, [x["vector"] for x in candidates[lane]])
           for lane,record in zip(LANES,saved["lanes"])]
    return {"schema":SCHEMA,"source_sha":source,
            "freeze_git_blob":env.FREEZE_BLOB,
            "source_advisory_sha256":advisory_sha,
            "train_weights_report_sha256":saved_sha,
            "lanes":lanes,"train_only":True,
            "both_lanes_frozen_margin_met":all(x["frozen_margin_met"] for x in lanes),
            "protected_confirmation_read":False,"scientific_acceptance":False,
            "optimizer_promotion":False,"originals_dispatched":0,
            "resource_parity_established":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--advisory",required=True)
    p.add_argument("--train-report",required=True)
    p.add_argument("--source-ref",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    need(not os.environ.get("GITHUB_SHA") or
         os.environ["GITHUB_SHA"]==a.source_ref, "LIVE_HEAD_DRIFT")
    advisory,asha=sealed(a.advisory)
    saved,rsha=sealed(a.train_report)
    report=execute(advisory,saved,a.source_ref,asha,rsha)
    out=Path(a.output)
    need(out.parent.is_dir() and not out.exists(),"IMMUTABLE_OUTPUT")
    out.write_bytes((json.dumps(report,sort_keys=True,separators=(",",":"))+"\n").encode())
    print("F123_TRAIN_ABLATION_SHA256="+hashlib.sha256(out.read_bytes()).hexdigest())
    print("F123_CONFIRMATION_READ=false")
    print("F123_SCIENTIFIC_ACCEPTANCE=false")

if __name__=="__main__":
    try:
        main()
    except (env.Invalid,f120.Invalid,KeyError,ValueError,TypeError,
            OSError,AttributeError) as e:
        print("F123_TRAIN_CAUSAL_AUDIT_QUARANTINED="+str(e),file=sys.stderr)
        raise SystemExit(1)
