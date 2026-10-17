"""F125-R frozen-weight TRAIN causal sensitivity and calibration diagnostic.

Replay original source-bound TRAIN weights; never refit, tune decision threshold,
change source seeds or inspect reserved CONFIRM. Positive/negative paired
counterfactuals are the model-blind causal intervention supplied by the frozen
environment. Wrong-role swaps provide a provenance-preserving null control.
This is synthetic diagnostic evidence, not prospective scientific acceptance.
"""
from __future__ import annotations

from collections import defaultdict
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys

import f118_autonomy_feedback as f118
import f125r_train_qualification as train
import f125r_train_environment as env
import f125r_path_model as model

SCHEMA = "forge.autonomy.f125r.train-only-calibration-causal-diagnostic.v1"
SOURCE_KIND = "AUTHENTIC_SOURCE_PUBLIC_TRAIN_ONLY_NOT_SCIENCE"

def need(ok, code):
    env.need(bool(ok), "FROZEN_DIAGNOSTIC_" + code)

def sealed(path):
    return train.sealed(path)

def wrong_role_null(graph):
    """Blind to both truth and selected route; unchanged public slot marginals."""
    env.validate(graph)
    role_set = set(graph["roles"])
    choices = sorted(
        ((idx, item) for idx, item in enumerate(graph["edges"])
         if item["role"] not in role_set),
        key=lambda pair: (pair[1]["from"], pair[1]["to"],pair[1]["role"],
                          model.edge_id(pair[1])))
    need(len(choices)>=2,"OFFROLE_NULL_EDGES")
    a,b = (choices[0][0],choices[1][0])
    output = copy.deepcopy(graph)
    before=env.marginals(graph)
    output["edges"][a]["src_bits"],output["edges"][b]["src_bits"]=(
        output["edges"][b]["src_bits"],output["edges"][a]["src_bits"])
    need(output!=graph and env.marginals(output)==before,
         "NONCAUSAL_TOKEN_SWAP_INERT_OR_CHANGED_INPUT_MARGINAL")
    env.validate(output)
    return output

def lane_diagnosis(lane, report, vectors):
    need(report.get("lane")==lane
         and report.get("source_vectors_sha256")==env.digest(vectors)
         and report.get("learned_parameter_count")==20
         and report.get("frozen_optimizer_epochs")==100
         and report.get("pruned_states_by_design")==0
         and report.get("protected_confirmation_samples")==0
         and report.get("scientific_accepted") is False
         and report.get("matched_compute_ratio_to_f123_dense_established") is False,
         "TRAIN_RECEIPT_AUTHORITY")
    weights=report["trained_weights"]
    rows=env.train_rows(lane,vectors)
    need(env.digest(rows)==report["train_rows_sha256"]
         and model.sha(weights)==report["weights_sha256"]
         and report["train_score"]==model.score(rows,weights),
         "SAVED_TRAIN_WEIGHTS_SCORE_OR_GRAPH_DRIFT")
    counts=defaultdict(lambda: {"pairs":0,"paired_correct":0,
                                "positive_correct":0,"negative_correct":0,
                                "positive_probability_sum":0.,
                                "negative_probability_sum":0.,
                                "signed_positive_minus_negative_sum":0.,
                                "positive_higher_probability_pairs":0,
                                "null_probability_delta_sum":0.,
                                "null_prediction_flips":0,
                                "max_state_keys":0,
                                "mass_differential_sum":0.,
                                "cost_events":0})
    traces=[]
    for i in range(0,len(rows),2):
        source_index=i//64
        seed=env.LANES[lane].start+(i%64)//2
        pos,positive_label=rows[i]
        neg,negative_label=rows[i+1]
        need((positive_label,negative_label)==(1,0)
             and env.graph_paths(pos,True)==1
             and env.graph_paths(neg,True)==0
             and env.marginals(pos)==env.marginals(neg),
             "SOURCE_CAUSAL_PAIR_REPLAY")
        pp,_,pt=model.forward(pos,weights,True)
        np,_,nt=model.forward(neg,weights,True)
        pn=wrong_role_null(pos)
        nn=wrong_role_null(neg)
        null_pos=model.forward(pn,weights)[0]
        null_neg=model.forward(nn,weights)[0]
        need(abs(null_pos-pp)<=1e-10 and abs(null_neg-np)<=1e-10,
             "WRONG_ROLE_NULL_INFLUENCES_PUBLIC_QUERY")
        correct_pos=pp>=.5
        correct_neg=np<.5
        key="depth-"+str(len(pos["roles"]))
        category=counts[key]
        category["pairs"]+=1
        category["paired_correct"]+=int(correct_pos and correct_neg)
        category["positive_correct"]+=int(correct_pos)
        category["negative_correct"]+=int(correct_neg)
        category["positive_probability_sum"]+=pp
        category["negative_probability_sum"]+=np
        category["signed_positive_minus_negative_sum"]+=pp-np
        category["positive_higher_probability_pairs"]+=int(pp>np)
        category["null_probability_delta_sum"]+=abs(null_pos-pp)+abs(null_neg-np)
        category["null_prediction_flips"]+=int((pp>=.5)!=(null_pos>=.5))
        category["null_prediction_flips"]+=int((np>=.5)!=(null_neg>=.5))
        category["max_state_keys"]=max(category["max_state_keys"],
                                       pt["work"]["state_limit_peak"],
                                       nt["work"]["state_limit_peak"])
        category["mass_differential_sum"]+=pt["terminal_mass"]-nt["terminal_mass"]
        category["cost_events"]+=sum(pt["work"].values())+sum(nt["work"].values())
        traces.append({
           "train_pair_index":i//2,"source_vector_index":source_index,
           "source_seed":seed,
           "source_positive_sha256":model.sha(pos),
           "source_negative_sha256":model.sha(neg),
           "positive_probability":round(pp,14),
           "negative_probability":round(np,14),
           "positive_minus_negative":round(pp-np,14),
           "positive_terminal_mass":round(pt["terminal_mass"],14),
           "negative_terminal_mass":round(nt["terminal_mass"],14),
           "public_key_state_peak":max(pt["work"]["state_limit_peak"],
                                        nt["work"]["state_limit_peak"]),
           "positive_null_probability":round(null_pos,14),
           "negative_null_probability":round(null_neg,14),
           "paired_correct":bool(correct_pos and correct_neg),
           "public_topology_token_multiset_preserved":True,
           "no_model_oracle_route_used":True})
    ordered={k:{name:(round(value,12) if isinstance(value,float) else value)
                for name,value in data.items()}
             for k,data in sorted(counts.items())}
    need(len(traces)==64 and sum(x["pairs"] for x in ordered.values())==64
         and sum(x["paired_correct"] for x in ordered.values())==
                  report["train_score"]["paired_correct"]
         and sum(x["positive_correct"] for x in ordered.values())==
                  report["train_score"]["positive_correct"]
         and sum(x["negative_correct"] for x in ordered.values())==
                  report["train_score"]["negative_correct"],
         "INCONSISTENT_UNCHANGED_TRAIN_METRICS")
    return {"lane":lane,
            "saved_train_weights_sha256":model.sha(weights),
            "train_rows_sha256":env.digest(rows),
            "paired_test_records":64,
            "unchanged_frozen_threshold":0.5,
            "depth_strata":ordered,
            "positive_probability_sum":round(sum(r["positive_probability"] for r in traces),12),
            "negative_probability_sum":round(sum(r["negative_probability"] for r in traces),12),
            "positive_higher_probability_pairs":sum(
                r["positive_minus_negative"]>0 for r in traces),
            "null_intervention_prediction_flips":sum(
                x["null_prediction_flips"] for x in ordered.values()),
            "sampled_train_graphs":128,
            "model_threshold_tuned":False,
            "learned_parameters_updated":False,
            "cost_parity_claim":False,
            "causal_pair_diagnostics_sha256":model.sha(traces),
            "pair_diagnostics":traces}

def diagnose(advisory,headroom,weights,source):
    need(isinstance(source,str) and
         re.fullmatch(r"[0-9a-f]{40}",source) is not None
         and (not os.environ.get("GITHUB_SHA")
              or os.environ["GITHUB_SHA"]==source)
         and weights.get("schema")==train.SCHEMA
         and weights.get("source_sha")==source
         and weights.get("frozen_git_blob")==train.freeze.FROZEN_BLOB
         and weights.get("phase")==SOURCE_KIND
         and weights.get("advisory_sha256")==env.digest(advisory)
         and weights.get("headroom_report_sha256")==env.digest(headroom)
         and weights.get("model_git_blob")==train.git_blob(model.__file__)
         and weights.get("train_graph_git_blob")==train.git_blob(env.__file__)
         and weights.get("headroom_source_git_blob")==
              train.git_blob(train.headroom.__file__)
         and weights.get("protected_confirmation_read") is False
         and weights.get("scientific_acceptance") is False
         and weights.get("optimizer_promotion") is False
         and weights.get("scientific_first_use") is False
         and weights.get("originals_dispatched")==0,
         "SOURCE_OR_FIRST_USE_PROVENANCE")
    candidates=train.verify_headroom(advisory,headroom,source)
    need([e["lane"] for e in weights["lanes"]]==["Wingless","Yggdrasil"],
         "LANE_IDENTITY")
    lanes=[]
    for lane,report in zip(("Wingless","Yggdrasil"),weights["lanes"]):
        entries=candidates[lane]
        need(report["source_candidate_shas"]==
             [e["source_candidate_sha256"] for e in entries],
             "AUTHENTIC_CANDIDATE_SHA_DRIFT")
        lanes.append(lane_diagnosis(lane,report,[e["vector"] for e in entries]))
    return {"schema":SCHEMA,"source_sha":source,
            "frozen_git_blob":train.freeze.FROZEN_BLOB,
            "training_model_git_blob":train.git_blob(model.__file__),
            "source_advisory_sha256":env.digest(advisory),
            "lanes":lanes,
            "diagnostic_scope":"PUBLIC_SYNTHETIC_TRAIN_ONLY_SAVED_WEIGHTS",
            "protected_confirmation_read":False,
            "originals_dispatched":0,
            "scientific_first_use":False,
            "scientific_acceptance":False,
            "optimizer_promotion":False,
            "threshold_or_train_weights_changed":False,
            "resource_matched_superiority_established":False}

def main():
    p=argparse.ArgumentParser()
    for name in ("advisory","headroom","weights","source-sha","output"):
        p.add_argument("--"+name,required=True)
    args=p.parse_args()
    # Three independently sealed immutable input files from the SAME source run.
    advisory,_=sealed(args.advisory)
    headroom,_=sealed(args.headroom)
    weights,_=sealed(args.weights)
    result=diagnose(advisory,headroom,weights,args.source_sha)
    out=Path(args.output)
    need(out.parent.is_dir() and not out.exists(),"RECEIPT_REPLACEMENT")
    raw=(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n").encode()
    out.open("xb").write(raw)
    print("F125R_CALIBRATION_CUSTODY_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in result["lanes"]:
        print("F125R_"+lane["lane"].upper()+"_TOKEN_RANKED_PAIRS="+
              str(lane["positive_higher_probability_pairs"])+"/64")
        print("F125R_"+lane["lane"].upper()+"_NULL_PREDICTION_FLIPS="+
              str(lane["null_intervention_prediction_flips"]))
    print("F125R_CONFIRMATION_UNTOUCHED=true")
    print("F125R_SCIENTIFIC_ACCEPTED=false")

if __name__=="__main__":
    try:main()
    except (env.Invalid,train.freeze.Invalid,
            f118.Quarantined,KeyError,TypeError,ValueError,OSError) as err:
        print("F125R_DIAGNOSTIC_QUARANTINED="+str(err),file=sys.stderr)
        raise SystemExit(1)
