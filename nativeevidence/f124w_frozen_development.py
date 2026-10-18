"""F124-W original-custody exact-algorithm diagnostics on *fresh* public DEV.

No reference/oracle in inference. The *scorer* recovers the unique raw-bit
causal reference solely from already-public positive graphs, and joins its
intermediate states to observer states *after* prediction. Never train or
modify original weights using reference path.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import sys

import f124w_hop_trace_indexed as w
import f124v_development_evidence as previous
import f124v_collision_centered as old
import f124q_fresh_source as source
import f124q_independent_binding as q

V_SHA="ce9e63e7e78daa470007df03a2447dab5c64f12f1a767d50df7a6b89740a31b3"
SCHEMA="forge.research.f124w.original-frozen-hop-survival-and-compute-development.v1"
WING_ARMS=("O_original","T_anchor","V_checksum","W_indexed_primary",
           "W_alternate","W_fit_selected","fixed_12of16")
YGG_ARMS=("O_original","T_unchanged","V_centered","fixed_12of16")


def need(ok,label):
    w.need(ok,"RECEIPT_"+label)


def authenticate(o,t,u,v):
    originals,deltas=previous.authenticate(o,t,u)
    data=Path(v).read_bytes()
    need(hashlib.sha256(data).hexdigest()==V_SHA,"AUTHENTIC_ORIGINAL_V_RECEIPT")
    report=json.loads(data)
    need(report["schema"]=="forge.research.f124v.fresh-equal-capacity-centered-evidence-dev.v1"
         and report["freeze_blob"]=="a88353bfd2090a3869aa4e125f92605c3a5626f7"
         and report["scientific_acceptance"] is False
         and report["optimizer_promotion"] is False
         and report["original_weights_and_prior_failures_unchanged"]
         and report["new_training_steps"]==0
         and report["resource_matched_superiority_proven"] is False
         and report["lanes"][0]["dev"]["arms"]["new_collision"]["paired"]==44
         and report["lanes"][1]["dev"]["arms"]["new_centered"]["paired"]==16,
         "SOURCE_NEGATIVE_AND_POSITIVE_RETAINED")
    return originals,deltas


def exact_reference_path(graph):
    """Diagnostics ONLY: never call from forward/trace; post-prediction join."""
    source.validate_public(graph)
    frontier=[(graph["start"],None,[])]
    for role in graph["roles"]:
        following=[]
        for node,carried,steps in frontier:
            for edge in graph["edges"]:
                if edge["from"]==node and edge["role"]==role and (
                    carried is None or list(carried)==edge["src_bits"]
                ):
                    following.append((edge["to"],tuple(edge["dst_bits"]),
                                      steps+[(edge["to"],tuple(edge["dst_bits"]))]))
                    need(len(following)<=256,"DIAGNOSTIC_REFERENCE_ROUTE_LIMIT")
        frontier=following
    candidates=[hist for node,_,hist in frontier if node==graph["target"]]
    need(len(candidates)==1 and len(candidates[0])==len(graph["roles"]),
         "REFERENCE_POSITIVE_NOT_UNIQUE")
    return candidates[0]


def witness_join(trace,path):
    """Compare only publicly emitted cells and posthoc ground truth."""
    need(len(trace)==len(path),"FULL_HOP_TRACE")
    first_lost=None
    stages=[]
    for hop,(snapshot,(node,key)) in enumerate(zip(trace,path),start=1):
        wanted=(node,tuple(key))
        def match(cell):
            return (cell[0],tuple(cell[1]))==wanted
        before=[cell for cell in snapshot["candidate_states"] if match(cell)]
        active=[cell for cell in snapshot["active"] if match(cell)]
        retained=[cell for cell in snapshot["retained"] if match(cell)]
        full=active+retained
        if not full and first_lost is None:first_lost=hop
        witness_score=max((cell[2] for cell in full),default=None)
        other_scores=[cell[2] for cell in snapshot["active"]+snapshot["retained"]
                      if not match(cell)]
        top_other=max(other_scores,default=None)
        stages.append({
            "hop":hop,"candidate_reachable_before_prune":bool(before),
            "survived_active":bool(active),"survived_retained":bool(retained),
            "survived_total":bool(full),
            "witness_value":witness_score,
            "best_competing_value":top_other,
            "witness_minus_competitor":(witness_score-top_other
                if witness_score is not None and top_other is not None else None),
            "hop_candidate_count":snapshot["candidate_count"],
            "hop_evictions":snapshot["evictions_at_hop"],
            "centered_increment_min":snapshot["centered_increment_min"],
            "centered_increment_max":snapshot["centered_increment_max"],
            "max_public_cell_value":snapshot["top_candidate_score"]})
    return {"first_causal_path_loss":first_lost,
            "causal_path_survives_terminal":bool(stages[-1]["survived_total"]),
            "hops":stages}


def wing_predict(arm,g,base,delta,fixed,chosen):
    if arm=="O_original":
        return previous.predict("Wingless","original_O",g,base,delta,fixed)
    if arm=="T_anchor":
        return previous.predict("Wingless","T_anchored",g,base,delta,fixed)
    if arm=="fixed_12of16":
        return previous.predict("Wingless","fixed_12of16",g,base,delta,fixed)
    if arm=="V_checksum":
        logit,work=old.wingless_collision_reassignment(g,base,delta)
    else:
        scheme=(w.PRIMARY if arm=="W_indexed_primary" else
                w.ALTERNATE if arm=="W_alternate" else chosen)
        logit,work=w.indexed_wingless(g,base,delta,scheme)
        # Immutable V checksum must retain EXACT raw logit and classification.
        if scheme==w.PRIMARY:
            original_logit,original_work=old.wingless_collision_reassignment(g,base,delta)
            need(logit==original_logit,"CACHED_V_BITWISE_FORWARD_MISMATCH")
            work["uncached_public_edge_scan_proxy"]=original_work["public_edge_scans"]
            work["uncached_raw_bit_ops_proxy"]=original_work["raw_bit_ops"]
            # Original V full-scans edges for each state, plus one entire
            # graph scan per each uncached public prospective lookup.
            n=len(g["edges"])
            calls=work["lookahead_cache_hits"]+work["lookahead_cache_misses"]
            work["uncached_fullscan_including_lookups"]=(original_work[
                "public_edge_scans"]+calls*n)
    return bool(logit>=0),work


def fit_checksum(pairs,base,delta):
    row={}
    for name,coeffs in (("PRIMARY",w.PRIMARY),("ALTERNATE",w.ALTERNATE)):
        paired=0
        for _,_,pos,neg in pairs:
            p,_=w.indexed_wingless(pos,base,delta,coeffs)
            n,_=w.indexed_wingless(neg,base,delta,coeffs)
            paired+=int(p>=0 and n<0)
        row[name]=paired
    # Single FIT-only selection; tie to existing primary.
    choice=w.ALTERNATE if row["ALTERNATE"]>row["PRIMARY"] else w.PRIMARY
    return choice,row


def run(o,t,u,v):
    w.frozen()
    base,delta=authenticate(o,t,u,v)
    fixed=previous.earlier.parent.original_adapter.clone_single_validator(
        previous.earlier.previous.old_control.fixed_comparator,"graph")
    # Freeze FIT-only choice before any DEV graph generated.
    chosen,fit_scores=fit_checksum(w.pairs("Wingless","FIT"),
                                   base["Wingless"],delta["Wingless"])
    report={"schema":SCHEMA,"freeze_git_blob":w.FREEZE_BLOB,
      "source_qualified_parent":"163e67995f57e4be9543be4b5451aef1982cfca4",
      "source_v_raw_sha256":V_SHA,"immutable_qualified_originals":True,
      "new_source_only":True,"training_steps":0,
      "fit_selected_checksum":list(chosen),"fit_primary_vs_alternate":fit_scores,
      "selected_only_using_FIT":True,"DEV_only_after_all_methods_frozen":True,
      "resource_matched_superiority_proven":False,"scientific_acceptances":0,
      "optimizer_promotions":0,"protected_first_use":False,
      "paid_model_calls":0,"codex_calls":0,"accepted_ref_mutations":0,
      "lanes":[]}
    for lane in ("Wingless","Yggdrasil"):
        names=WING_ARMS if lane=="Wingless" else YGG_ARMS
        results={"lane":lane,"FIT":None,"DEV":None,
                 "inference_memory_unchanged":True}
        for phase in ("FIT","DEV"):
            stats={name:{"pairs":0,"paired":0,"false_positive":0,"false_negative":0,
                        "depth":{str(n):{"pairs":0,"paired":0} for n in (7,8,9)},
                        "edge_work":0,"bit_work":0,"index_build_work":0,
                        "affinity_ops":0,"look_cache_entries_max":0,
                        "extra_cache_entries_max":0,"max_active":0,"max_retained":0,
                        "case_sha256":[]} for name in names}
            trace={"positive_graphs":48,"negative_graphs":48,
                   "methods":{}}
            for mode in ("T_rank_only","V_centered"):
                trace["methods"][mode]={
                    "hop_aggregation":{str(depth):{} for depth in (7,8,9)},
                    "first_causal_loss_histogram":{},
                    "individual_witness_sha256":[],
                    "correct_positive":0,"correct_negative":0,
                    "per_depth_outcomes":{str(depth):{"positive":0,"negative":0}
                                           for depth in (7,8,9)}}
            for seed,vec,pos,neg in w.pairs(lane,phase):
                depth=str(len(pos["roles"]))
                need(source.public_routes(pos)==1 and
                     source.public_routes(neg)==0 and
                     source.public_routes(pos,True)==source.public_routes(neg,True),
                     "FULL_LABEL_BLIND_SOURCE")
                if lane=="Yggdrasil":
                    # Model performs FIRST, before evaluating reference.
                    models={}
                    for mode in ("T_rank_only","V_centered"):
                        original_forward=(q.forward if mode=="T_rank_only"
                                          else lambda l,g,b,d:old.yggdrasil_centered_evidence(g,b,d))
                        for which,g in (("positive",pos),("negative",neg)):
                            score,work,path_trace=w.ygg_hop_trace(
                                g,base[lane],delta[lane],mode)
                            old_score,old_work=original_forward(
                                lane,g,base[lane],delta[lane])
                            need(score==old_score and
                                 all(work[k]==old_work[k] for k in old_work),
                                 "INSTRUMENTED_TRACE_NOT_IDENTICAL_TO_FROZEN")
                            models[(mode,which)]=(score,path_trace)
                    reference=exact_reference_path(pos)
                    for mode in ("T_rank_only","V_centered"):
                        yes,p_trace=models[(mode,"positive")]
                        no,n_trace=models[(mode,"negative")]
                        row=trace["methods"][mode]
                        row["correct_positive"]+=int(yes>=0)
                        row["correct_negative"]+=int(no<0)
                        row["per_depth_outcomes"][depth]["positive"]+=int(yes>=0)
                        row["per_depth_outcomes"][depth]["negative"]+=int(no<0)
                        witness=witness_join(p_trace,reference)
                        loss=witness["first_causal_path_loss"]
                        key=str(loss) if loss is not None else "SURVIVED"
                        row["first_causal_loss_histogram"][key]=(
                            row["first_causal_loss_histogram"].get(key,0)+1)
                        row["individual_witness_sha256"].append(q.digest({
                            "seed":seed,"vector":vec,"phase":phase,
                            "model":mode,"reference_join":witness}))
                        for stage in witness["hops"]:
                            s=str(stage["hop"])
                            agg=row["hop_aggregation"][depth].setdefault(s,{
                              "graphs":0,"before_prune":0,"active":0,"retained":0,
                              "any_survival":0,"evictions":0,
                              "score_gap_sum":0.,"score_gap_count":0,
                              "centered_min_sum":0.,"centered_max_sum":0.})
                            agg["graphs"]+=1
                            agg["before_prune"]+=int(stage["candidate_reachable_before_prune"])
                            agg["active"]+=int(stage["survived_active"])
                            agg["retained"]+=int(stage["survived_retained"])
                            agg["any_survival"]+=int(stage["survived_total"])
                            agg["evictions"]+=stage["hop_evictions"]
                            agg["centered_min_sum"]+=stage["centered_increment_min"]
                            agg["centered_max_sum"]+=stage["centered_increment_max"]
                            if stage["witness_minus_competitor"] is not None:
                                agg["score_gap_sum"]+=stage["witness_minus_competitor"]
                                agg["score_gap_count"]+=1
                for arm in names:
                    vals=[]
                    for which,g in (("positive",pos),("negative",neg)):
                        if lane=="Wingless":
                            predicted,work=wing_predict(arm,g,base[lane],delta[lane],
                                                        fixed,chosen)
                        else:
                            if arm=="V_centered":
                                sc,work=old.yggdrasil_centered_evidence(
                                    g,base[lane],delta[lane]);predicted=sc>=0
                            elif arm=="T_unchanged":
                                sc,work=q.forward(lane,g,base[lane],delta[lane])
                                predicted=sc>=0
                            else:
                                predicted,work=previous.predict(
                                    lane,{"O_original":"original_O",
                                          "fixed_12of16":"fixed_12of16"}[arm],
                                    g,base[lane],delta[lane],fixed)
                        vals.append(predicted)
                        row=stats[arm]
                        row["edge_work"]+=work.get("public_edge_inspections",
                                                  work.get("public_edge_scans",0))
                        row["bit_work"]+=work.get("compressed_bit_reads",
                                                 work.get("raw_bit_ops",0))
                        row["index_build_work"]+=work.get("index_build_edge_inspections",0)
                        row["affinity_ops"]+=work.get("compressed_affinity_operations",0)
                        row["look_cache_entries_max"]=max(row["look_cache_entries_max"],
                              work.get("max_lookahead_cache_entries",0))
                        row["extra_cache_entries_max"]=max(row["extra_cache_entries_max"],
                              work.get("max_encoded_entries",0)+
                              work.get("max_lookahead_cache_entries",0)+
                              work.get("max_index_entries",0))
                        row["max_active"]=max(row["max_active"],work.get("max_active",0))
                        row["max_retained"]=max(row["max_retained"],work.get("max_retained",0))
                    yes,no=vals
                    row=stats[arm]
                    paired=bool(yes and not no)
                    row["pairs"]+=1
                    row["paired"]+=int(paired)
                    row["false_positive"]+=int(no)
                    row["false_negative"]+=int(not yes)
                    row["depth"][depth]["pairs"]+=1
                    row["depth"][depth]["paired"]+=int(paired)
                    row["case_sha256"].append(q.digest({
                        "arm":arm,"phase":phase,"seed":seed,"vector":vec,
                        "positive":yes,"negative":no,"paired":paired}))
            for arm,z in stats.items():
                need(z["pairs"]==48 and len(z["case_sha256"])==48
                     and all(r["pairs"]==16 for r in z["depth"].values())
                     and z["max_retained"]<=9
                     and (z["max_active"]<=7 if lane=="Yggdrasil" else
                          z["max_active"]<=192),
                     "FROZEN_FULL_COHORT_AND_MEMORY_CAPACITY")
            if lane=="Wingless":
                need(stats["V_checksum"]["paired"]==
                     stats["W_indexed_primary"]["paired"] and
                     stats["V_checksum"]["false_positive"]==
                     stats["W_indexed_primary"]["false_positive"] and
                     stats["V_checksum"]["false_negative"]==
                     stats["W_indexed_primary"]["false_negative"],
                     "EXACT_CACHED_BASELINE_CONTROL")
            else:
                for mode in ("T_rank_only","V_centered"):
                    witness=trace["methods"][mode]
                    need(len(witness["individual_witness_sha256"])==48
                         and sum(witness["first_causal_loss_histogram"].values())==48
                         and all(v["graphs"]==16 for depth,d in
                           witness["hop_aggregation"].items()
                           for v in d.values()),
                         "FULL_7_8_9_HOP_DIAGNOSTICS")
            results[phase]={"pairs":48,"arms":stats,"reference_exact":48,
                             "reference_role_only":0,
                             "trace":trace if lane=="Yggdrasil" else None}
        report["lanes"].append(results)
    return report


def main():
    parser=argparse.ArgumentParser()
    for x in ("o","t","u","v","output"):
        parser.add_argument("--"+x,required=True)
    args=parser.parse_args()
    output=Path(args.output)
    need(output.parent.is_dir() and not output.exists(),"NEVER_OVERWRITE_RECEIPT")
    report=run(args.o,args.t,args.u,args.v)
    b=json.dumps(report,indent=2,sort_keys=True).encode()+b"\n"
    with output.open("xb") as f:f.write(b)
    print("F124W_AUTHENTIC_RECEIPT_SHA256="+hashlib.sha256(b).hexdigest())
    for row in report["lanes"]:
        a=row["DEV"]["arms"]
        if row["lane"]=="Wingless":
            print("F124W_WING_DEV=selected="+str(a["W_fit_selected"]["paired"])+
                  "/48:V="+str(a["V_checksum"]["paired"])+
                  "/48:fixed="+str(a["fixed_12of16"]["paired"])+"/48")
        else:
            print("F124W_YGG_DEV=V="+str(a["V_centered"]["paired"])+
                  "/48:T="+str(a["T_unchanged"]["paired"])+
                  "/48:fixed="+str(a["fixed_12of16"]["paired"])+"/48")


if __name__=="__main__":
    try:main()
    except (OSError,KeyError,TypeError,ValueError,ArithmeticError) as exc:
        print("F124W_FAIL_CLOSED:"+str(exc),file=sys.stderr)
        sys.exit(1)
