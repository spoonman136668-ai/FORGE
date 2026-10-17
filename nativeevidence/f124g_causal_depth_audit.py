"""F124-G immutable F124-F TRAIN-only causal retrieval and calibration diagnosis.

No model update, threshold choice, original first-use, or reserved CONFIRM access.
Independent float replay must agree with the qualified frozen model to 1e-12.
Scorer-only exact raw-token lineage determines whether a true causal prefix
survives the learned hard top-3 query-conditional retention; it is NEVER used
to select/score keys inside the model.

Ablations and oracle-label-informed thresholds are POST-HOC diagnostics,
ineligible for scientific success, heldout selection, or optimizer promotion.
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

import f123_cross_os_custody as parent
import f124f_public_graph_source as graph
import f124f_conditional_memory as model

BASE_SHA = "25e6f7c900ed37f3102b095a866ade467bbaeaf7"
F124F_TRAIN_SHA = "4cf3bbd2338d62c595288c459fea066db674246964c6a582971f823454162350"
F123_TRAIN_SHA = "12da879272212b899c6b942004ff38dc21ffa6bb20e7a81eac21d691746b474d"
F124F_MODEL_BLOB = "30b50f9500a7905378b53613280658b1b95c9a29"
F124F_SOURCE_BLOB = "1961628bdc9df47975f8c9ccd44370329ed02ae5"
SCHEMA = "forge.research.f124g.immutable-train-causal-depth-audit.v1"

def need(value, code):
    graph.require(value, "F124G_" + code)

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def edge_identity(edge):
    return (edge["from"], edge["to"], edge["role"],
            tuple(edge["src_bits"]), tuple(edge["dst_bits"]))

def sig(x):
    return 1.0/(1.0+math.exp(-max(-40.,min(40.,x))))

def witness(obs, weights, arm, query_priority=True):
    """Independent forward replay with scorer-only causal history witnesses.

    It uses the model's EXACT fixed top-three comparator. 'valid_prefix' is
    computed independently and is never read in mass, priority, or classification.
    """
    graph.validate(obs)
    need(arm in ("A","B") and type(query_priority) is bool and
         len(weights)==(19 if arm=="A" else 20) and
         all(type(w) in (int,float) and math.isfinite(w) for w in weights),
         "SOURCE_MODEL_PARAMETERS")
    edges=sorted(obs["edges"],key=edge_identity)
    lookups={}
    for role in obs["roles"]:
        for e in edges:
            if e["role"]==role:
                lookups.setdefault((e["from"],role),[]).append(e["src_bits"])
    def agreement(left,right):
        return weights[16]+sum(weights[i]*((2*a-1)*(2*b-1))/16.
                   for i,(a,b) in enumerate(zip(left,right)))
    states={obs["start"]:[(1.,None,True)]}
    byhop=[]
    for i,role in enumerate(obs["roles"]):
        incoming={}
        messages=0
        for node in sorted(states):
            eligible=[e for e in edges if e["from"]==node and e["role"]==role]
            for mass,old_key,valid_prefix in states[node]:
                for e in eligible:
                    gate=1. if old_key is None else sig(agreement(old_key,e["src_bits"]))
                    retained_key=tuple(e["dst_bits"])
                    # scorer-only bool; neither selection nor score sees it.
                    next_valid=(valid_prefix and
                                (old_key is None or old_key==tuple(e["src_bits"])))
                    incoming.setdefault(e["to"],[]).append((
                        mass*gate,retained_key,edge_identity(e),next_valid))
                    messages+=1
                    need(messages<=128,"SOURCE_ACTIVATION_BOUNDS")
        states={}
        next_role=obs["roles"][i+1] if i+1<len(obs["roles"]) else None
        good_drop=bad_drop=0
        for node in sorted(incoming):
            candidates=[]
            for mass,rawkey,edgeid,valid_prefix in incoming[node]:
                queries=lookups.get((node,next_role),[]) if next_role else []
                priority=(max(agreement(rawkey,q) for q in queries)
                          if query_priority and queries else 0.)
                candidates.append(((priority,mass,edgeid,rawkey),
                                  mass,rawkey,valid_prefix))
            candidates.sort(key=lambda x:(-x[0][0],-x[0][1],x[0][2],x[0][3]))
            good_drop+=sum(bool(v) for _,_,_,v in candidates[3:])
            bad_drop+=sum(not v for _,_,_,v in candidates[3:])
            records=[]
            for _,mass,rawkey,valid_prefix in candidates[:3]:
                if arm=="B":
                    novelty=(min(sum(a!=b for a,b in zip(rawkey,prevkey))/16.
                            for _,prevkey,_ in records) if records else 1.)
                    mass*=sig(weights[19]*(novelty-.25))
                records.append((mass,rawkey,valid_prefix))
            states[node]=records
        byhop.append({"hop":i+1,"valid_causal_prefix_evicted":good_drop,
                      "inconsistent_prefix_evicted":bad_drop,
                      "live_records":sum(len(v) for v in states.values()),
                      "messages":messages})
        need(byhop[-1]["live_records"]<=128,"SCORER_MEMORY_BUDGET")
    target=states.get(obs["target"],[])
    total=sum(x[0] for x in target)
    signed=math.log(total+1e-6)/len(obs["roles"])
    logit=weights[17]*(signed-weights[18])
    score=sig(logit)
    return {"score":score,"logit":logit,"signed_log_evidence_per_hop":signed,
            "terminal_mass":total,"causal_target_records":sum(bool(x[2]) for x in target),
            "noncausal_target_records":sum(not x[2] for x in target),
            "causal_prefix_evicted":sum(x["valid_causal_prefix_evicted"] for x in byhop),
            "records_evicted":sum(x["valid_causal_prefix_evicted"]+
                                  x["inconsistent_prefix_evicted"] for x in byhop),
            "byhop":byhop}

def public_true_path(obs):
    """Independent *scorer-only* public consistency oracle, never model data."""
    graph.validate(obs)
    frontier=[(obs["start"],None,[])]
    for role in obs["roles"]:
        ahead=[]
        for node,carried,path in frontier:
            for e in obs["edges"]:
                if node==e["from"] and e["role"]==role and (
                        carried is None or carried==tuple(e["src_bits"])):
                    ahead.append((e["to"],tuple(e["dst_bits"]),path+[e]))
                    need(len(ahead)<=256,"REFERENCE_ORACLE_BUDGET")
        frontier=ahead
    winners=[path for node,_,path in frontier if node==obs["target"]]
    need(len(winners)==1,"PUBLIC_CAUSAL_PATH_NOT_UNIQUE")
    return winners[0]

def causal_deletion(obs,weights,arm):
    """Posthoc compare deleting a necessary join edge vs an alternative join edge.

    Public symbolic witness is computed only AFTER training/inference; deletion
    uses unchanged weights and never affects model or selector.
    """
    path=public_true_path(obs)
    join_edge=None
    wrong=None
    for e in path[1:]:
        peers=[x for x in obs["edges"] if x["to"]==e["to"] and
               x["role"]==e["role"] and edge_identity(x)!=edge_identity(e)]
        if peers:
            join_edge=e
            wrong=sorted(peers,key=edge_identity)[0]
            break
    need(join_edge is not None and wrong is not None,
         "CAUSAL_JOIN_REFERENCE_MISSING")
    old=model.forward(obs,weights,arm)[0]
    def remove(which):
        others=copy.deepcopy(obs)
        ident=edge_identity(which)
        candidates=[idx for idx,e in enumerate(others["edges"])
                    if edge_identity(e)==ident]
        need(len(candidates)==1,"PUBLIC_PARALLEL_EDGE_AMBIGUITY")
        del others["edges"][candidates[0]]
        graph.validate(others)
        return others
    real=remove(join_edge)
    distractor=remove(wrong)
    need(graph.public_routes(real)==0 and
         graph.public_routes(distractor)==1,
         "JOIN_ABLATION_CAUSAL_TRUTH_DRIFT")
    real_drop=old-model.forward(real,weights,arm)[0]
    other_drop=old-model.forward(distractor,weights,arm)[0]
    return {"true_join_edge_score_drop":real_drop,
            "distractor_join_edge_score_drop":other_drop,
            "true_join_deletion_stronger":real_drop>other_drop,
            "causal_deletion_truth_invalidates_route":True,
            "distractor_deletion_keeps_route":True}

def oracle_threshold(rows):
    """Optimistic TRAIN-label-seen single threshold; NEVER a new decision rule."""
    scores=sorted({r[x] for r in rows for x in ("positive","negative")})
    candidates=[0.,.5,1.]+[(a+b)/2. for a,b in zip(scores,scores[1:])]
    scored=[]
    for threshold in candidates:
        paired=sum(x["positive"]>=threshold and x["negative"]<threshold
                   for x in rows)
        scored.append((paired,-abs(threshold-.5),-threshold,threshold))
    best=max(scored)
    return {"label_informed_train_oracle_upper_bound_pairs":best[0],
            "posthoc_oracle_threshold_forbidden":round(best[3],12),
            "original_frozen_decision_threshold":.5,
            "not_eligible_for_acceptance":True}

def mean(values):
    return round(sum(values)/len(values),12) if values else None

def source_identity():
    graph.frozen();model.contract()
    for mod,expected in ((graph,F124F_SOURCE_BLOB),(model,F124F_MODEL_BLOB)):
        raw=Path(mod.__file__).read_bytes().replace(b"\r\n",b"\n")
        need(graph.git_blob(raw)==expected,"QUALIFIED_MODEL_SOURCE_BLOB_DRIFT")

def read_train_receipt(path):
    need(digest(path)==F124F_TRAIN_SHA,"IMMUTABLE_TRAIN_RECEIPT_DRIFT")
    obj=json.loads(Path(path).read_bytes())
    need(obj["schema"]=="forge.research.f124f.train-only-query-conditioned-custody.v1"
         and obj["source_sha"]==BASE_SHA
         and obj["graph_git_blob"]==F124F_SOURCE_BLOB
         and obj["model_git_blob"]==F124F_MODEL_BLOB
         and obj["phase"]=="TRAIN_ONLY"
         and obj["confirmation_examples_generated"]==0
         and obj["scientific_first_use"] is False
         and obj["scientific_acceptances"]==0
         and obj["optimizer_promotions"]==0,"TRAIN_REPORT_IDENTITY")
    return obj

def audit(f124f_json,f123_dir):
    source_identity()
    saved=read_train_receipt(f124f_json)
    ancestry,ancestrysha=parent.read_receipt(f123_dir)
    need(ancestrysha==F123_TRAIN_SHA
         and ancestry["source_sha"]=="7882849a59964f412a87589be653114e7bf64d52"
         and [x["lane"] for x in ancestry["lanes"]]==["Wingless","Yggdrasil"]
         and [x["lane"] for x in saved["lanes"]]==["Wingless","Yggdrasil"],
         "F123_SOURCE_VECTOR_ANCESTRY")
    lanes=[]
    for original,trace in zip(ancestry["lanes"],saved["lanes"]):
        lane=original["lane"]
        vectors=original["training_vectors"]
        need(trace["lane"]==lane and trace["vectors"]==vectors
             and len(vectors)==2,"SOURCE_VECTOR_ASSOCIATION")
        pairs=[graph.build(seed,v,lane,"TRAIN") for v in vectors
               for seed in graph.TRAIN[lane]]
        need(len(pairs)==48,"TRAIN_PAIR_BOUNDARY")
        arms={}
        for arm in ("A","B"):
            original_arm=trace["learned_arms"][arm]
            weights=original_arm["weights"]
            need(model.sha(weights)==original_arm["weight_sha256"]
                 and original_arm["training_epochs"]==100
                 and original_arm["paired_examples"]==48
                 and original_arm["parameters"]==(19 if arm=="A" else 20),
                 "SOURCE_FROZEN_WEIGHTS_OR_SELECTOR")
            rows=[]
            for positive,negative in pairs:
                p=witness(positive,weights,arm)
                n=witness(negative,weights,arm)
                # Replay the EXACT original predictions before interpreting a
                # single scorer-only causal variable or exploratory ablation.
                need(abs(model.forward(positive,weights,arm)[0]-p["score"])<=1e-12
                     and abs(model.forward(negative,weights,arm)[0]-n["score"])<=1e-12,
                     "EXACT_ORIGINAL_PREDICTION_REPLAY")
                need(p["causal_target_records"]<=1 and
                     n["causal_target_records"]==0,
                     "CAUSAL_ORACLE_LINEAGE_CONTRADICTION")
                ablation=causal_deletion(positive,weights,arm)
                original_noquery=model.forward(
                    positive,weights,arm,query_priority=False)[0]
                rows.append({
                    "hops":len(positive["roles"]),
                    "positive":p["score"],"negative":n["score"],
                    "positive_logit":p["logit"],"negative_logit":n["logit"],
                    "positive_ranked_higher":p["score"]>n["score"],
                    "paired_correct":p["score"]>=.5 and n["score"]<.5,
                    "positive_score_above_threshold":p["score"]>=.5,
                    "negative_score_below_threshold":n["score"]<.5,
                    "causal_record_survives":p["causal_target_records"]==1,
                    "causal_prefix_evicted":p["causal_prefix_evicted"],
                    "total_records_evicted":p["records_evicted"],
                    "ablate_public_next_query_score_delta":
                        p["score"]-original_noquery,
                    "causal_join_deletion":ablation})
            need(len(rows)==48,"TRAIN_REPLAY_SIZE")
            paired=sum(x["paired_correct"] for x in rows)
            rank=sum(x["positive_ranked_higher"] for x in rows)
            positive_correct=sum(x["positive_score_above_threshold"] for x in rows)
            negative_correct=sum(x["negative_score_below_threshold"] for x in rows)
            need(paired==original_arm["train_paired_correct"] and
                 rank==original_arm["ranked_positive_higher"] and
                 positive_correct==original_arm["train_positive_correct"] and
                 negative_correct==original_arm["train_negative_correct"],
                 "PUBLISHED_TRAIN_ACCURACY_REPLAY_DRIFT")
            depth={}
            for d in (4,5):
                subset=[x for x in rows if x["hops"]==d]
                need(len(subset)==24,"TRAIN_DEPTH_BALANCE")
                depth[str(d)]={
                    "pairs":len(subset),
                    "paired_correct":sum(x["paired_correct"] for x in subset),
                    "positive_ranked_higher":sum(x["positive_ranked_higher"] for x in subset),
                    "mean_positive_logit":mean([x["positive_logit"] for x in subset]),
                    "mean_negative_logit":mean([x["negative_logit"] for x in subset]),
                    "mean_positive_score":mean([x["positive"] for x in subset]),
                    "mean_negative_score":mean([x["negative"] for x in subset]),
                    "causal_target_survived":sum(x["causal_record_survives"] for x in subset)}
            arms[arm]={
                "original_train_pairs_correct":paired,
                "original_positive_rank_higher":rank,
                "original_frozen_threshold":.5,
                "causal_positive_targets_survived":sum(x["causal_record_survives"] for x in rows),
                "positive_cases_losing_causal_prefix":sum(x["causal_prefix_evicted"]>0 for x in rows),
                "mean_valid_prefix_evictions":mean([x["causal_prefix_evicted"] for x in rows]),
                "query_priority_mean_score_delta":mean([x["ablate_public_next_query_score_delta"] for x in rows]),
                "query_priority_changes_positive_score_count":
                    sum(abs(x["ablate_public_next_query_score_delta"])>1e-12 for x in rows),
                "causal_join_deletion_stronger_than_distractor":
                    sum(x["causal_join_deletion"]["true_join_deletion_stronger"] for x in rows),
                "mean_true_causal_deletion_score_drop":
                    mean([x["causal_join_deletion"]["true_join_edge_score_drop"] for x in rows]),
                "mean_distractor_deletion_score_drop":
                    mean([x["causal_join_deletion"]["distractor_join_edge_score_drop"] for x in rows]),
                "oracle_train_threshold_descriptive_only":oracle_threshold(rows),
                "depth":depth,
                "train_cases":rows}
        lanes.append({"lane":lane,"frozen_selected_arm":trace["selected_train_arm"],
                      "arms":arms,"training_vectors_sha256":model.sha(vectors)})
    return {"schema":SCHEMA,"qualified_parent_head":BASE_SHA,
            "parent_training_report_sha256":F124F_TRAIN_SHA,
            "parent_candidate_receipt_sha256":F123_TRAIN_SHA,
            "original_f124f_freeze_blob":graph.FREEZE_BLOB,
            "no_weights_retrained_or_changed":True,
            "original_model_frozen_decision_threshold":.5,
            "posthoc_oracle_threshold_not_scientific":True,
            "diagnostic_query_ablation_only":True,
            "reserved_confirmation_cases_generated":0,
            "scientific_first_use_authorized":False,
            "original_science_executed":False,
            "scientific_acceptances":0,"accepted_ref_mutations":0,
            "optimizer_promotions":0,"resource_matched_superiority_not_established":True,
            "lanes":lanes}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--f124f-report",required=True)
    ap.add_argument("--f123-ubuntu-dir",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    out=Path(args.output)
    need(out.parent.is_dir() and not out.exists(),"REFUSE_EXISTING_REPORT")
    report=audit(args.f124f_report,args.f123_ubuntu_dir)
    with out.open("xb") as stream:
        stream.write((json.dumps(report,sort_keys=True,separators=(",",":"))+"\n").encode())

if __name__=="__main__":
    try:main()
    except (graph.Invalid,parent.Invalid,ValueError,KeyError,TypeError,OSError) as err:
        print("F124G_SOURCE_BORN_TRAIN_DIAGNOSTIC=QUARANTINED "+str(err),file=sys.stderr)
        raise SystemExit(1)
