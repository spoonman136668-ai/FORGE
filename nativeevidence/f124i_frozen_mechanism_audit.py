"""F124-I frozen F124-H TRAIN causal and computational qualification.

Replay the original F124-H 100-epoch weights and 0.5 rule exactly.
Evaluate paired stratum scores, leave-one-join-edge-out causal interventions,
and explicit public-graph resource proxies. The exact path solver is scorer-
only, never used in original inference, training, selection or candidate edits.

This is TRAIN-only diagnostic analysis, *not* independent scientific first-use.
"""
from __future__ import annotations
import argparse
from collections import Counter
import copy
import hashlib
import json
import math
from pathlib import Path
import sys

import f123_cross_os_custody as upstream
import f124h_source as source
import f124h_signed_evidence as model
import f124h_train_receipt as receipt

SCHEMA="forge.research.f124i.frozen-train-mechanism-resource-audit.v1"
F124H_HEAD="409f9129442f3d47b3d9bc032342f48042f3127a"
F124H_TRAIN_SHA="3ce0356ad9c19aeb4557ffe0b138908707c65ab3ce4b6af952adbf9899988254"
F123_TRAIN_SHA="12da879272212b899c6b942004ff38dc21ffa6bb20e7a81eac21d691746b474d"
F123_HEAD="7882849a59964f412a87589be653114e7bf64d52"
FREEZE_BLOB="5b3ca556f2cf55323b6317d506a62c6b2a4aab85"
SOURCE_BLOB="3feab91460f29ec169e1904479a134bb04691937"
MODEL_BLOB="599d7a87f0812f3a7d2c8680861b6360d3640bc0"
COSTS=("public_edge_scans","raw_bit_multiply_adds","exp_evaluations","sigmoids")
STRATA=source.STRATA

def need(ok,code):
    source.require(ok,"F124I_"+code)

def sha_bytes(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def canonical(obj):
    return (json.dumps(obj,sort_keys=True,separators=(",",":"))+"\n").encode()

def id_edge(e):
    return (e["from"],e["to"],e["role"],tuple(e["src_bits"]),tuple(e["dst_bits"]))

def prove_source():
    need(source.FREEZE_BLOB==FREEZE_BLOB and len(source.frozen())==64
         and model.frozen(),"FROZEN_PROTOCOL_IDENTITY")
    for mod,expected in ((source,SOURCE_BLOB),(model,MODEL_BLOB)):
        actual=source.git_blob(Path(mod.__file__).read_bytes().replace(b"\r\n",b"\n"))
        need(actual==expected,"ORIGINAL_SOURCE_GIT_BLOB_DRIFT")
    need(all(set(source.TRAIN[lane]).isdisjoint(source.RESERVED_CONFIRM[lane])
             for lane in source.TRAIN),"CONFIRM_COHORT_LEAK")

def read_frozen_parent(path):
    need(sha_bytes(path)==F124H_TRAIN_SHA,"IMMUTABLE_PARENT_WEIGHTS_DIGEST")
    data=json.loads(Path(path).read_bytes())
    need(data["schema"]=="forge.research.f124h.train-only-signed-competing-evidence.v1"
         and data["source_sha"]==F124H_HEAD
         and data["phase"]=="TRAIN_ONLY"
         and data["frozen_protocol_git_blob"]==FREEZE_BLOB
         and data["source_git_blob"]==SOURCE_BLOB
         and data["model_git_blob"]==MODEL_BLOB
         and data["authenticated_candidate_receipt_sha256"]==F123_TRAIN_SHA
         and data["protected_confirmation_cases_generated"]==0
         and data["independent_original_first_use"] is False
         and data["scientific_acceptances"]==0
         and data["accepted_ref_mutations"]==0
         and data["optimizer_promotions"]==0
         and len(data["lanes"])==2,
         "PARENT_SCIENTIFIC_SOURCE_IDENTITY")
    return data

def public_causal_path(obs):
    """Public symbolic scorer only; unique positive path enforced."""
    source.validate(obs)
    frontier=[(obs["start"],None,[])]
    for role in obs["roles"]:
        nxt=[]
        for current,carried,path in frontier:
            for e in obs["edges"]:
                if e["from"]==current and e["role"]==role and (
                        carried is None or carried==tuple(e["src_bits"])):
                    nxt.append((e["to"],tuple(e["dst_bits"]),path+[e]))
                    need(len(nxt)<=256,"REFERENCE_TRAVERSAL_LIMIT")
        frontier=nxt
    matches=[path for node,_,path in frontier if node==obs["target"]]
    need(len(matches)==1,"CAUSAL_PATH_NOT_UNIQUE")
    return matches[0]

def remove_edge(obs,edge):
    target=id_edge(edge)
    match=[i for i,e in enumerate(obs["edges"]) if id_edge(e)==target]
    need(len(match)==1,"PUBLIC_EDGE_IDENTITIES_NOT_UNIQUE")
    cleaned=copy.deepcopy(obs)
    del cleaned["edges"][match[0]]
    source.validate(cleaned)
    return cleaned

def causal_and_distractor(obs,weights,arm):
    """Counterfactual deletion, identical frozen weights.

    Select the FIRST indispensable path edge with a peer incoming to its
    destination at the same role. This is chosen by the *scorer* after the
    model is frozen. Never return a modified model/source to training.
    """
    path=public_causal_path(obs)
    true_edge=decoy=None
    for e in path[1:]:
        others=[alt for alt in obs["edges"]
                if alt["to"]==e["to"] and alt["role"]==e["role"]
                and id_edge(alt)!=id_edge(e)]
        if others:
            true_edge=e
            decoy=sorted(others,key=id_edge)[0]
            break
    need(true_edge is not None,"NONDISCRIMINATING_CAUSAL_JOIN")
    necessary=remove_edge(obs,true_edge)
    distractor=remove_edge(obs,decoy)
    need(source.public_routes(necessary)==0
         and source.public_routes(distractor)==1,
         "CAUSAL_TRUTH_CHANGED_BY_CONTROL")
    original=model.forward(obs,weights,arm)[0]
    causal_removed=model.forward(necessary,weights,arm)[0]
    decoy_removed=model.forward(distractor,weights,arm)[0]
    return {"true_edge_drop":original-causal_removed,
            "distractor_edge_drop":original-decoy_removed,
            "causal_drop_greater":original-causal_removed>original-decoy_removed,
            "causal_deleted_truth":0,"distractor_deleted_truth":1,
            "original_score":original}

def inventory(obs):
    source.validate(obs)
    return (Counter((e["from"],e["to"],e["role"]) for e in obs["edges"]),
            Counter(tuple(e[k]) for e in obs["edges"]
                    for k in ("src_bits","dst_bits")))

def add_counts(acc,cost):
    for key in COSTS:acc[key]+=cost[key]
    acc["peak_key_records"]=max(acc["peak_key_records"],cost["peak_key_records"])
    acc["peak_messages"]=max(acc["peak_messages"],cost["max_messages_per_hop"])
    acc["evicted_records"]+=cost["evicted_records"]

def add_fixed(acc,cost):
    acc["public_edge_scans"]+=cost["public_edge_scans"]
    acc["raw_bit_comparisons"]+=cost["bit_comparisons"]

def audit(parent_report,source_dir):
    prove_source()
    original=read_frozen_parent(parent_report)
    vectors_record,vector_sha=upstream.read_receipt(source_dir)
    need(vector_sha==F123_TRAIN_SHA and vectors_record["source_sha"]==F123_HEAD
         and vectors_record["cohorts"]=="TRAIN_ONLY"
         and vectors_record["confirmation_inputs_generated"]==0
         and [x["lane"] for x in vectors_record["lanes"]]==["Wingless","Yggdrasil"]
         and [x["lane"] for x in original["lanes"]]==["Wingless","Yggdrasil"],
         "IMMUTABLE_TRAIN_VECTOR_ANCESTRY")
    lanes=[]
    for lane_source,lane_original in zip(vectors_record["lanes"],original["lanes"]):
        lane=lane_source["lane"]
        vectors=lane_source["training_vectors"]
        need(lane_original["lane"]==lane
             and lane_original["vectors"]==vectors
             and lane_original["candidate_source_shas"]==
                   lane_source["advisory_candidate_source_shas"]
             and len(vectors)==2 and vectors[0]!=vectors[1]
             and lane_original["selected_arm_train_only"]=="B",
             "PARENT_TRAIN_ONLY_SELECTION_DRIFT")
        cohort=[]
        for v in vectors:
            for seed in source.TRAIN[lane]:
                p,n=source.build(seed,v,lane,"TRAIN")
                need(source.paired_admit(p,n) and inventory(p)==inventory(n),
                     "COHORT_PAIR_COUNTERFACTUAL_DRIFT")
                cohort.append((seed,v,p,n))
        need(len(cohort)==48,"TRAIN_PAIRS_COUNT")
        controls={"public_edge_scans":0,"raw_bit_comparisons":0}
        exact_control_paired=0
        for seed,v,p,n in cohort:
            positive,pc=receipt.fixed_comparator(p)
            negative,nc=receipt.fixed_comparator(n)
            exact_control_paired+=int(positive and not negative)
            add_fixed(controls,pc);add_fixed(controls,nc)
        known_control=lane_original["control_fixed_12of16"]
        need(exact_control_paired==known_control["paired_correct"]
             and controls["public_edge_scans"]==known_control["edge_scans"]
             and controls["raw_bit_comparisons"]==known_control["raw_bit_comparisons"],
             "PARENT_CONTROL_REPRODUCTION")
        arms={}
        for arm in ("A","B"):
            original_arm=lane_original["arms"][arm]
            weights=original_arm["weights"]
            need(original_arm["weight_sha256"]==model.sha(weights)
                 and original_arm["epochs"]==100
                 and original_arm["pairs"]==48
                 and len(weights)==(20 if arm=="A" else 21)
                 and original_arm["confirmation_generated"]==0,
                 "ORIGINAL_LEARNED_WEIGHT_DRIFT")
            totals=dict.fromkeys(COSTS,0)
            totals.update(peak_key_records=0,peak_messages=0,evicted_records=0)
            cases=[]
            for seed,v,p,n in cohort:
                ps,pl,_,pc=model.forward(p,weights,arm)
                ns,nl,_,nc=model.forward(n,weights,arm)
                add_counts(totals,pc);add_counts(totals,nc)
                ablate=causal_and_distractor(p,weights,arm)
                stratum=source.STRATA[seed%len(source.STRATA)]
                cases.append({
                    "source_seed":seed,"stratum":stratum,
                    "hops":len(p["roles"]),"positive_score":round(ps,12),
                    "negative_score":round(ns,12),
                    "positive_logit":round(pl,12),"negative_logit":round(nl,12),
                    "paired_correct":ps>=.5 and ns<.5,
                    "positive_higher":pl>nl,
                    "causal_deletion":{k:(round(v,12) if type(v) is float else v)
                                       for k,v in ablate.items()},
                    "input_pair_role_topology_and_token_histogram_equal":True})
            paired=sum(x["paired_correct"] for x in cases)
            pos_correct=sum(x["positive_score"]>=.5 for x in cases)
            neg_correct=sum(x["negative_score"]<.5 for x in cases)
            ranked=sum(x["positive_higher"] for x in cases)
            need(paired==original_arm["paired_correct"]
                 and pos_correct==original_arm["positive_correct"]
                 and neg_correct==original_arm["negative_correct"]
                 and ranked==original_arm["positive_rank_higher"],
                 "PUBLISHED_FROZEN_TRAIN_REPLAY_MISMATCH")
            depth={}
            for d in (4,5):
                group=[x for x in cases if x["hops"]==d]
                need(len(group)==24 and sum(x["paired_correct"] for x in group)==
                     original_arm["depth"][str(d)]["paired"],"ORIGINAL_DEPTH_DRIFT")
                depth[str(d)]={
                    "pairs":24,"paired_correct":sum(x["paired_correct"] for x in group),
                    "positive_ranked_higher":sum(x["positive_higher"] for x in group),
                    "mean_positive_logit":round(sum(x["positive_logit"] for x in group)/24,10),
                    "mean_negative_logit":round(sum(x["negative_logit"] for x in group)/24,10)}
            strata={}
            for name in STRATA:
                rows=[x for x in cases if x["stratum"]==name]
                need(len(rows)>0,"MISSING_FROZEN_ADVERSARIAL_STRATUM")
                strata[name]={"pairs":len(rows),
                    "paired_correct":sum(x["paired_correct"] for x in rows),
                    "ranked_higher":sum(x["positive_higher"] for x in rows),
                    "causal_drop_greater":sum(x["causal_deletion"]["causal_drop_greater"] for x in rows)}
            arms[arm]={"frozen_original_train_paired_correct":paired,
                       "frozen_weight_sha256":original_arm["weight_sha256"],
                       "frozen_0_5_decision_threshold":.5,
                       "depth":depth,"strata":strata,
                       "causal_edge_deletion_has_stronger_effect":
                           sum(x["causal_deletion"]["causal_drop_greater"] for x in cases),
                       "mean_true_causal_edge_deletion_score_drop":round(
                           sum(x["causal_deletion"]["true_edge_drop"] for x in cases)/48,10),
                       "mean_distractor_deletion_score_drop":round(
                           sum(x["causal_deletion"]["distractor_edge_drop"] for x in cases)/48,10),
                       "public_work_total_both_labels":totals,
                       "serialized_weights_bytes":len(canonical(weights)),
                       "parameter_count":len(weights),
                       "cases":cases}
        lanes.append({"lane":lane,"original_train_selected_arm":"B",
                      "control_fixed_12of16":known_control,
                      "public_fixed_work_total_both_labels":controls,
                      "arms":arms,
                      "equal_information_not_equal_compute":True})
    return {"schema":SCHEMA,
            "parent_original_source_head":F124H_HEAD,
            "original_train_weights_receipt_sha256":F124H_TRAIN_SHA,
            "authenticated_candidate_vectors_sha256":F123_TRAIN_SHA,
            "frozen_protocol_blob":FREEZE_BLOB,
            "original_model_blob":MODEL_BLOB,
            "original_environment_blob":SOURCE_BLOB,
            "exact_original_weights_unchanged":True,
            "retraining_occurred":False,"threshold_changed":False,
            "resourcing_changed":False,"posthoc_ablation_non_scientific":True,
            "reserved_confirmation_examples_generated":0,
            "independent_first_use":False,"scientific_accepted":False,
            "accepted_ref_mutations":0,"optimizer_promotions":0,
            "resource_matched_superiority_proven":False,
            "lanes":lanes}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--f124h-report",required=True)
    ap.add_argument("--f123-ubuntu-dir",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    target=Path(args.output)
    need(target.parent.is_dir() and not target.exists(),"REFUSE_OUTPUT_OVERWRITE")
    with target.open("xb") as handle:
        handle.write(canonical(audit(args.f124h_report,args.f123_ubuntu_dir)))

if __name__=="__main__":
    try:main()
    except (source.Invalid,upstream.Invalid,ValueError,KeyError,TypeError,OSError) as e:
        print("F124I_FROZEN_TRAIN_DIAGNOSTIC=QUARANTINED "+str(e),file=sys.stderr)
        raise SystemExit(1)
