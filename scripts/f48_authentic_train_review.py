"""F48 authentic TRAIN-only result review and bounded F49 advisory hypotheses.

Reads two exact, first-attempt GitHub Actions artifacts. Never executes originals,
approves science, dispatches workers or adapts live optimizer policies.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

class Blocked(ValueError):
    pass

EXPECTED = {
    "Wingless": {
        "commit": "0bad6a035e4257f0bc18f593a25e0770d378d17d",
        "run": 38805703700, "artifact": 12005084367,
        "report": "51162d3a09abcd17f6609e0a23172cc3fc69b47c37bbcc7a319ad9d9890acc02",
        "schema": "wingless.f48.disjoint-trained-query-value.trainonly.v1",
        "stage": "ONE_FRESH_FIT_AND_DIAGNOSTIC_NO_PRIMARY_ORIGINAL",
        "seeds": [411100, 411104], "families": [600, 601, 602, 603],
        "reserve": [412000, 412016], "n": 32,
    },
    "Yggdrasil": {
        "commit": "b2407c469086c6a0ea99e9f3986c4336ef832e79",
        "run": 38805887306, "artifact": 12006805585,
        "report": "94944ed5bfe427b1eed301fba532cd455643b3e56f54408c40283dde219ddb86",
        "schema": "yggdrasil.f48.shifted-anchor-identifiability.trainonly.v1",
        "stage": "NEW_SHIFTED_SENSING_TRAIN_ONLY_NO_ORIGINAL",
        "seeds": [421100, 421108], "families": [620, 621, 622, 623],
        "reserve": [422000, 422016], "n": 128,
    },
}

def need(ok, reason):
    if not ok:
        raise Blocked("F48_" + reason)

def sha(b):
    return hashlib.sha256(b).hexdigest()

def unique(pairs):
    d = {}
    for key, val in pairs:
        need(key not in d, "DUPLICATE_KEY")
        d[key] = val
    return d

def load(path, lane):
    spec = EXPECTED[lane]
    root = Path(path)
    raw = (root / "result.json").read_bytes()
    need(0 < len(raw) <= 3000000 and sha(raw) == spec["report"], "REPORT_HASH")
    manifest = (root / "result.sha256").read_text().split()
    need(len(manifest) == 2 and manifest[0] == sha(raw)
         and Path(manifest[1]).name == "result.json", "MANIFEST")
    need((root / "SOURCE_SHA").read_text().strip() == spec["commit"], "SOURCE_COMMIT")
    d = json.loads(raw, object_pairs_hook=unique)
    need(d.get("schema") == spec["schema"] and d.get("stage") == spec["stage"],
         "SOURCE_SCHEMA_STAGE")
    need(d.get("accepted_ref_mutation") is False
         and d.get("independent_F3_custody") is False
         and d.get("paid_api_calls") == 0, "FALSE_AUTHORITY")
    if lane == "Wingless":
        need(d.get("original_executed") is False
             and d.get("originals_reserved_not_consumed") == spec["reserve"]
             and d.get("diagnostic_seeds") == spec["seeds"]
             and d.get("fit_seeds") == [411000,411004], "W_ORIGINAL_OR_COHORT")
    else:
        need(d.get("primary_original_not_executed") is True
             and d.get("reserved_seeds") == spec["reserve"]
             and d.get("diagnostic_seeds") == spec["seeds"]
             and d.get("fit_seeds") == [421000,421008], "Y_ORIGINAL_OR_COHORT")
    return d, {"run_id": spec["run"], "artifact_id": spec["artifact"],
               "commit": spec["commit"], "report_sha256": spec["report"]}

def recount(d, lane):
    spec = EXPECTED[lane]
    rows = d["rows"]
    scores = d["scores"]
    need(type(rows) is list and len(rows) == spec["n"]
         and d["questions"] == len(rows)
         and set(d["families"]) == set(spec["families"]), "COHORT_SIZE")
    key = "answers" if lane == "Wingless" else "predictions"
    seen = set()
    for row in rows:
        need(spec["seeds"][0] <= row["seed"] < spec["seeds"][1]
             and row["family"] in spec["families"], "SEED_FAMILY_LEAK")
        if lane == "Wingless":
            ident = (row["seed"],row["family"],row["length"])
            need(row["length"] in (3, 5), "QUERY_LENGTH")
        else:
            ident = (row["seed"],row["family"],row["mechanism"],row["condition"])
            need(row["public_pairs"] == 12 and row["public_flat_anchors"] == 24,
                 "PUBLIC_ANCHOR_PARITY")
        need(ident not in seen and set(row[key]) == set(scores),
             "DUPLICATE_SOURCE_OR_ARM")
        seen.add(ident)
        if lane == "Wingless":
            for arm, trace in row["receipts"].items():
                need(len(trace) <= 2
                     and len({tuple(r[:2]) for r in trace}) == len(trace),
                     "PAID_MAPPING_REUSE")
        else:
            for arm, traces in row["receipts"].items():
                need(len(traces) == 3
                     and all(len(trace) == 2 and trace[0] == 0
                             and trace[1] in (1, 2, 3) for trace in traces),
                     "PAID_SENSOR_REUSE")
    correct = {}
    for arm, sc in scores.items():
        nright = sum(row[key][arm] == row["truth"] for row in rows)
        need(sc["correct"] == nright and sc["total"] == len(rows)
             and abs(sc["accuracy"] - nright/len(rows)) < 1e-12,
             "SCORE_RECOUNT")
        correct[arm] = nright
        if lane == "Yggdrasil":
            fp = sum(bool(r[key][arm]) and not r["truth"] for r in rows)
            fn = sum(not bool(r[key][arm]) and r["truth"] for r in rows)
            probabilities = [r["probabilities"][arm] for r in rows]
            need(all(type(p) in (int,float) and 0 < p < 1
                     for p in probabilities), "PROBABILITY_BOUNDS")
            brier = sum((r["probabilities"][arm]-r["truth"])**2 for r in rows)/len(rows)
            loss = -sum(math.log(r["probabilities"][arm] if r["truth"]
                                 else 1-r["probabilities"][arm]) for r in rows)/len(rows)
            need(fp == sc["fp"] and fn == sc["fn"]
                 and abs(brier-sc["Brier"]) < 1e-10
                 and abs(loss-sc["logloss"]) < 1e-10, "METRICS_RECOUNT")
    return rows, correct

def review_wingless(d, rows, correct):
    trial = "learned_query_cost_value"
    fair = ("one_step_value","exact_entropy","query_frontier","budget_matched_rank")
    best = max(correct[a] for a in fair)
    gain = (correct[trial] - best)/len(rows)
    work = {arm:sum(row["work"][arm] for row in rows)
            for arm in d["posterior_world_work"]}
    need(work == d["posterior_world_work"]
         and d["strongest_budget_fair_control"] in fair,
         "WORK_OR_CONTROL_RECOUNT")
    ratio = work[trial]/max(1,work[d["strongest_budget_fair_control"]])
    family = {str(f):{a:sum(r["answers"][a] == r["truth"] for r in rows
                            if r["family"] == f) for a in d["scores"]}
              for f in EXPECTED["Wingless"]["families"]}
    need(family == d["by_family"], "FAMILY_RECOUNT")
    guard = all(family[str(f)][trial] >= max(family[str(f)][a] for a in fair)
                for f in EXPECTED["Wingless"]["families"])
    qualified = gain >= .05 and ratio <= 1.2 and guard
    need(abs(gain-d["candidate_gain"]) < 1e-12
         and abs(ratio-d["posterior_work_ratio"]) < 1e-12
         and guard == d["family_nondegradation"]
         and qualified == d["frozen_criterion_met"]
         and d["verdict"] == ("TRAIN_ONLY_SUPPORTED_NOT_F3" if qualified
                              else "TRAIN_ONLY_NEGATIVE"), "FROZEN_THRESHOLD")
    need(d["diagnostic_truth_not_used_for_fit"] is True
         and d["public_only_action_inputs"] is True
         and d["training_questions"] == 32
         and max(d["training_beta_scores"].values()) ==
             d["training_beta_scores"][str(d["selected_beta_train_only"])],
         "FIT_OR_PROVENANCE")
    return {"lane":"Wingless", "trial_correct":correct[trial],
            "strongest_fair_correct":best,"n":len(rows),
            "gain_pp":round(100*gain,6),"posterior_work_ratio":round(ratio,6),
            "family_nondegradation":guard,
            "disposition":"TRAIN_ONLY_SUPPORTED_NOT_F3" if qualified else "TRAIN_ONLY_NEGATIVE",
            "next_hypothesis":("ISOLATE_PUBLIC_REVEAL_VALUE_IDENTIFIABILITY_AND_STABLE_ACTION_RANKS_BEFORE_NEW_LEARNING"
                              if not qualified else "INDEPENDENT_NEW_FAMILY_TRAIN_REPLICATION_AT_EQUAL_COST")}

def review_yggdrasil(d, rows, correct):
    trial = "learned_intervention_invariant"
    shuffled = "count_matched_shuffled_intervention_pairs"
    unpaired = "learned_unpaired_ablation"
    fair = ("fitted_Gaussian_latent","empirical_conditional_Brier","Gaussian_kernel",
            "public_global_static","source_variance",unpaired,shuffled)
    best = max(correct[a] for a in fair)
    gain = (correct[trial]-best)/len(rows)
    shuffled_gain = (correct[trial]-correct[shuffled])/len(rows)
    unpaired_gain = (correct[trial]-correct[unpaired])/len(rows)
    mechanism = {r["mechanism"] for r in rows}
    need(mechanism == {"nonlinear_hysteresis","cross_channel_flip"}
         and set(d["heldout_mechanisms"]) == mechanism
         and d["shifted_heldout_mechanisms"] ==
              ["nonlinear_hysteresis_shifted","cross_channel_flip_asymmetric"],
         "MECHANISM_IDENTITY")
    for m in mechanism:
        for arm in correct:
            recount = sum(r["predictions"][arm] == r["truth"]
                          for r in rows if r["mechanism"] == m)
            need(recount == d["by_mechanism"][m][arm]["correct"],
                 "MECHANISM_SCORE_RECOUNT")
    guard = all(d["by_mechanism"][m][trial]["correct"] >=
                max(d["by_mechanism"][m][a]["correct"] for a in fair)
                for m in mechanism)
    qualified = gain >= .02 and shuffled_gain > 0 and unpaired_gain > 0 and guard
    need(abs(gain - d["gain_over_strongest_fair"]) < 1e-12
         and abs(shuffled_gain-d["shuffled_pairs_ablation_gain"]) < 1e-12
         and abs(unpaired_gain-d["unpaired_ablation_gain"]) < 1e-12
         and guard == d["heldout_mechanism_nondegradation"]
         and qualified == d["frozen_criterion_met"]
         and d["verdict"] == ("TRAIN_ONLY_SUPPORTED_NOT_F3" if qualified
                              else "TRAIN_ONLY_NEGATIVE"), "Y_FROZEN_THRESHOLD")
    return {"lane":"Yggdrasil","trial_correct":correct[trial],
            "strongest_fair_correct":best,"shuffled_correct":correct[shuffled],
            "unpaired_correct":correct[unpaired],"n":len(rows),
            "gain_pp":round(100*gain,6),
            "paired_vs_shuffled_pp":round(100*shuffled_gain,6),
            "paired_vs_unpaired_pp":round(100*unpaired_gain,6),
            "mechanism_nondegradation":guard,
            "disposition":"TRAIN_ONLY_SUPPORTED_NOT_F3" if qualified else "TRAIN_ONLY_NEGATIVE",
            "next_hypothesis":("TEST_PAIRED_INFORMATION_IDENTIFIABILITY_VERSUS_UNPAIRED_PUBLIC_BASELINE_WITH_MATCHED_SOURCE_NEGATIVES"
                              if not qualified else "INDEPENDENT_NEW_MECHANISM_TRAIN_REPLICATION_AT_EQUAL_COST")}

def review(wingless, yggdrasil):
    w, ws = load(wingless,"Wingless")
    y, ys = load(yggdrasil,"Yggdrasil")
    wr, wc = recount(w,"Wingless")
    yr, yc = recount(y,"Yggdrasil")
    findings = [review_wingless(w,wr,wc),review_yggdrasil(y,yr,yc)]
    return {"schema":"forge.autonomy.f48-authentic-train-review.v1",
            "source":{"Wingless":ws,"Yggdrasil":ys},
            "reviewed_train_lanes":2,
            "findings":findings,
            "prospective_primary_originals_executed":0,
            "science_acceptance_or_promotion_authorized":False,
            "dream_rsi_prospective_improvement_established":False,
            "theta_evolve_training_authorized":False,
            "new_controller_or_worker_dispatch_authorized":False,
            "hypothesis_successors_advisory_only":True}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--wingless",required=True)
    p.add_argument("--yggdrasil",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    report=review(args.wingless,args.yggdrasil)
    Path(args.out).write_text(json.dumps(report,sort_keys=True,separators=(",",":"))+"\n")

if __name__=="__main__":
    main()
