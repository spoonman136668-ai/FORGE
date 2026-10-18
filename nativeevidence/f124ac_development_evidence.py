"""F124-AC source-authenticated passive error attribution on disjoint graphs.

Original model executes before the separate scorer constructs any causal
reference. Read-only instrumentation is exact-logit and counter-checked
against frozen AB / AA parents. This is NOT new model training.
"""
from __future__ import annotations
from collections import Counter,defaultdict
import argparse, hashlib, json, math, sys
from pathlib import Path

import f124ac_frozen_source as frozen
import f124ac_passive_trace as obs
import f124ab_development_evidence as parent
import f124ab_soft_hamming_pareto as ab
import f124aa_packed_transfer as aa
import f124q_independent_binding as original_t
import f124w_hop_trace_indexed as original_w

SCHEMA="forge.research.f124ac.fresh-long-depth-packed-failure-diagnostics.v1"
AB_RAW_SHA="270202bae8773bd39c33116b0b365716bd23d53f2a92d7395f77d4a7baee67b9"

def need(condition,label):
    frozen.need(condition,"RECEIPT_"+label)

def original_custody(o,t,u,w,x,y,z,aa_path,ab_path):
    bases,deltas=parent.authentic(o,t,u,w,x,y,z,aa_path)
    raw=Path(ab_path).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==AB_RAW_SHA,
         "UNCHANGED_AB_RAW_ORIGINAL")
    p=json.loads(raw)
    need(p["schema"]=="forge.research.f124ab.frozen-soft-hamming-packed-pareto-development.v1"
         and p["freeze_git_blob"]=="61724ad438c1609a6738bef7b7a3e239132d8944"
         and p["candidate_fit_selection"]["gamma"]==.25
         and p["candidate_fit_selection"]["penalty"]==.25
         and p["scientific_acceptance"] is False
         and p["optimizer_promotion"] is False
         and p["protected_first_use"] is False
         and p["lanes"][1]["DEV"]["controls"]["FIT_soft_head"]["paired"]==38
         and p["lanes"][0]["DEV"]["controls"]["packed_1"]["paired"]==32,
         "ORIGINAL_FIT_RECEIPT_AND_NEGATIVES")
    return bases,deltas

def public_reference(graph,relaxed):
    """SCORER ONLY, invoked after frozen predictors/observers finish."""
    frozen.original.parent.validate_extended(graph)
    states=[(graph["start"],None,[])]
    for role in graph["roles"]:
        nxt=[]
        for node,carry,hist in states:
            for edge in graph["edges"]:
                if edge["from"]!=node or edge["role"]!=role:continue
                mismatch=(0 if carry is None else
                          sum(a!=b for a,b in zip(carry,edge["src_bits"])))
                if carry is None or mismatch<=(1 if relaxed else 0):
                    nxt.append((edge["to"],tuple(edge["dst_bits"]),
                                hist+[(edge["to"],tuple(edge["dst_bits"]))]))
                    need(len(nxt)<=256,"REFERENCE_SOURCE_ROUTE_LIMIT")
        states=nxt
    options=[hist for node,_,hist in states if node==graph["target"]]
    need(len(options)==1,"UNIQUE_PUBLIC_CAUSAL_WITNESS")
    return options[0]

def causal_join(trace,witness,wing=False):
    need(len(trace)==len(witness),"FULL_MODEL_HOP_TRACE")
    lost_candidates=None
    lost_hard=None
    steps=[]
    for i,(snap,(node,key)) in enumerate(zip(trace,witness),1):
        if wing:
            packed=0
            for j,v in enumerate(obs.pack_public(list(key))):packed|=v<<(j*3)
            candidate=any(n==node and any(dst==packed for _,_,dst in rows)
                          for n,rows in snap["all_public_candidate_keys"])
            kept=any(n==node and stored==packed for n,_,stored in snap["kept"])
            hard_active=kept
            hard_retained=False
            eviction=snap["discarded_count"]
            witness_score=next((score for n,score,stored in snap["kept"]
                                if n==node and stored==packed),None)
            total_score=max((score for _,score,_ in snap["kept"]),default=None)
        else:
            candidate=any(c[0]==node and c[1]==key for c in snap["candidate"])
            active=[c for c in snap["active"] if c[0]==node and c[1]==key]
            retained=[c for c in snap["retained"] if c[0]==node and c[1]==key]
            hard_active=bool(active)
            hard_retained=bool(retained)
            kept=hard_active or hard_retained
            eviction=snap["evictions_this_hop"]
            witness_score=max((c[2] for c in active+retained),default=None)
            total_score=max((c[2] for c in snap["active"]+snap["retained"]),
                             default=None)
        if not candidate and lost_candidates is None:lost_candidates=i
        if not kept and lost_hard is None:lost_hard=i
        steps.append({"hop":i,"candidate_reference_seen":bool(candidate),
                      "reference_in_active":bool(hard_active),
                      "reference_in_retained":bool(hard_retained),
                      "reference_survived":bool(kept),
                      "total_candidates":snap["candidate_count"],
                      "evictions":eviction,
                      "best_surviving_value":total_score,
                      "reference_surviving_value":witness_score,
                      "reference_minus_best":(witness_score-total_score
                           if witness_score is not None and
                              total_score is not None else None)})
    return {"first_reference_missing_candidate_hop":lost_candidates,
            "first_reference_pruned_hop":lost_hard,
            "reference_survived_final":bool(steps[-1]["reference_survived"]),
            "by_hop":steps}

def collision_census(graph):
    """Public bits only; counts semantic aliases, not causal model decisions."""
    groups=defaultdict(set)
    role_groups=defaultdict(set)
    for e in graph["edges"]:
        for key in ("src_bits","dst_bits"):
            bits=tuple(e[key])
            groups[obs.pack_public(list(bits))].add(bits)
        role_groups[(e["from"],e["role"],obs.pack_public(e["src_bits"]))].add(
            tuple(e["src_bits"]))
    return {
        "all_public_packed_alias_sets":sum(len(v)>1 for v in groups.values()),
        "same_node_role_source_alias_sets":
            sum(len(v)>1 for v in role_groups.values()),
        "max_distinct_raw_keys_per_compressed_code":
            max((len(v) for v in groups.values()),default=0)}

def empty_arm():
    return {"pairs":0,"paired":0,"false_positive":0,"false_negative":0,
            "per_family":{f:{"pairs":0,"paired":0,"false_positive":0,
                             "false_negative":0,"by_depth":{}}
                          for f in frozen.FAMILIES},
            "edge_or_scans":0,"raw_bit_ops":0,"max_active":0,"max_retained":0,
            "case_sha256":[]}

def score(lane,phase,base,delta):
    arms=("soft_AB","T_original","Z_exact") if lane=="Yggdrasil" else (
          "one_state_AB","three_state_AB")
    outcomes={arm:empty_arm() for arm in arms}
    diagnostics={"positive_case_hashes":[],"error_mode_histogram":{},
                 "false_positive_census":{},
                 "hopwise_positive":{},"family_causal_loss":{},
                 "aliases":{"all_packed_alias_sets":0,
                            "same_node_role_source_alias_sets":0},
                 "long_depth_cases":0,"terminal_reference_survived":0,
                 "terminal_reference_missing":0,
                 "score_negative_even_when_reference_survives":0,
                 "source_blind_trace_hashes":[]}
    for seed,vector,family,pos,neg in frozen.pairs(lane,phase):
        predictions={}
        traces={}
        if lane=="Yggdrasil":
            # All original source-blind inference and parity happens first.
            for label,g in (("positive",pos),("negative",neg)):
                score_soft,raw,ratio,work,path=obs.observe_ygg(g,base,delta)
                old_raw,old_ratio,old_work=ab.soft_continuity(
                    g,base,delta,.25)
                control_raw,control_work=aa.ygg_original(g,base,delta)
                need(raw==old_raw==control_raw and ratio==old_ratio
                     and score_soft==ab.logit(old_raw,old_ratio,.25)
                     and all(work[k]==old_work[k] for k in old_work)
                     and all(work[k]==control_work[k] for k in control_work),
                     "YGG_OBSERVER_MUST_BE_ORIGINAL_BITWISE")
                originalZ,oldr,baselineZ,originalWork=aa.ygg_continuity(
                    g,base,delta)
                need(baselineZ==raw
                     and all(work[k]==originalWork[k] for k in originalWork),
                     "ORIGINAL_Z_COST_AND_T_RANK_PRESERVED")
                predictions[label]={
                    "soft_AB":(score_soft,work),
                    "T_original":(control_raw,control_work),
                    "Z_exact":(originalZ,originalWork)}
                traces[label]=path
                if label=="positive":
                    diagnostics["source_blind_trace_hashes"].append(
                        original_t.digest({"phase":phase,"seed":seed,
                                           "vector":vector,"family":family,
                                           "trace":path}))
        else:
            for label,g in (("positive",pos),("negative",neg)):
                one,work,trace=obs.observe_wing(g,base,delta)
                untouched,old_work=aa.packed_one_state(g,base,delta)
                three,work3=ab.packed_frontier(g,base,delta,3)
                need(one==untouched and work==old_work,
                     "WING_OBSERVER_MUST_BE_ORIGINAL_EXACT")
                predictions[label]={
                    "one_state_AB":(one,work),
                    "three_state_AB":(three,work3)}
                traces[label]=trace
                if label=="positive":
                    diagnostics["source_blind_trace_hashes"].append(
                        original_t.digest({"seed":seed,"vector":vector,
                                           "phase":phase,"trace":trace}))
                aliases=collision_census(g)
                diagnostics["aliases"]["all_packed_alias_sets"]+=aliases[
                    "all_public_packed_alias_sets"]
                diagnostics["aliases"]["same_node_role_source_alias_sets"]+=aliases[
                    "same_node_role_source_alias_sets"]
        # Only after BOTH graph predictions and trace hashes are complete
        # may the scorer derive the ground-truth public reference witness.
        witness=public_reference(pos,relaxed=family=="one_bit_relaxed_keys")
        initial=causal_join(traces["positive"],witness,
                            wing=lane=="Wingless")
        diagnostics["terminal_reference_survived"]+=int(initial[
            "reference_survived_final"])
        diagnostics["terminal_reference_missing"]+=int(not initial[
            "reference_survived_final"])
        depth=len(pos["roles"])
        if depth>=10:diagnostics["long_depth_cases"]+=1
        for step in initial["by_hop"]:
            d=diagnostics["hopwise_positive"].setdefault(str(step["hop"]),{
                "graphs":0,"candidates_seen":0,"retained":0,
                "active":0,"survived":0,"evictions":0,"negative_logit":0})
            d["graphs"]+=1
            d["candidates_seen"]+=int(step["candidate_reference_seen"])
            d["retained"]+=int(step["reference_in_retained"])
            d["active"]+=int(step["reference_in_active"])
            d["survived"]+=int(step["reference_survived"])
            d["evictions"]+=step["evictions"]
            d["negative_logit"]+=int(
                predictions["positive"][arms[0]][0]<0)
        error_type=("SCORE_NEGATIVE_PATH_SURVIVED" if
                    initial["reference_survived_final"] else
                    "REFERENCE_PATH_PRUNED")
        if predictions["positive"][arms[0]][0]<0:
            diagnostics["error_mode_histogram"][error_type]=(
                diagnostics["error_mode_histogram"].get(error_type,0)+1)
            if initial["reference_survived_final"]:
                diagnostics["score_negative_even_when_reference_survives"]+=1
        family_loss=diagnostics["family_causal_loss"].setdefault(family,{
            "count":0,"positive_errors":0,"terminal_survived":0,
            "first_candidate_missing":{},"first_hard_loss":{}})
        family_loss["count"]+=1
        family_loss["positive_errors"]+=int(
            predictions["positive"][arms[0]][0]<0)
        family_loss["terminal_survived"]+=int(initial[
            "reference_survived_final"])
        for target,key in (("first_candidate_missing",
                            initial["first_reference_missing_candidate_hop"]),
                           ("first_hard_loss",
                            initial["first_reference_pruned_hop"])):
            x=str(key) if key is not None else "SURVIVED"
            family_loss[target][x]=family_loss[target].get(x,0)+1
        for arm in arms:
            yes=predictions["positive"][arm][0]>=0
            no=predictions["negative"][arm][0]>=0
            rec=outcomes[arm]
            family_rec=rec["per_family"][family]
            d=family_rec["by_depth"].setdefault(str(depth),{
                "pairs":0,"paired":0})
            correct=int(yes and not no)
            for dest in (rec,family_rec,d):
                dest["pairs"]+=1;dest["paired"]+=correct
            for dest in (rec,family_rec):
                dest["false_positive"]+=int(no)
                dest["false_negative"]+=int(not yes)
            for name in ("positive","negative"):
                work=predictions[name][arm][1]
                rec["edge_or_scans"]+=work.get(
                    "public_edge_scans",work.get("edge_inspections",0))
                rec["raw_bit_ops"]+=work.get(
                    "raw_bit_ops",work.get("raw_bit_reads",0))
                rec["max_active"]=max(rec["max_active"],work["max_active"])
                rec["max_retained"]=max(rec["max_retained"],
                                       work.get("max_retained",0))
            rec["case_sha256"].append(original_t.digest({
                "phase":phase,"family":family,"seed":seed,
                "vector":vector,"arm":arm,"yes":yes,"no":no}))
            if arm==arms[0] and no:
                tag=family+"/"+str(depth)
                diagnostics["false_positive_census"][tag]=(
                    diagnostics["false_positive_census"].get(tag,0)+1)
        diagnostics["positive_case_hashes"].append(original_t.digest({
            "seed":seed,"vector":vector,"phase":phase,"family":family,
            "positive_logit":predictions["positive"][arms[0]][0],
            "negative_logit":predictions["negative"][arms[0]][0],
            "posthoc_join":initial}))
    need(len(diagnostics["positive_case_hashes"])==48 and
         len(diagnostics["source_blind_trace_hashes"])==48 and
         sum(diagnostics["family_causal_loss"][f]["count"]
             for f in frozen.FAMILIES)==48 and
         diagnostics["terminal_reference_missing"]+
             diagnostics["terminal_reference_survived"]==48,
         "COMPLETE_UNALTERED_DIAGNOSTIC_COHORT")
    for arm,rec in outcomes.items():
        need(rec["pairs"]==48 and len(rec["case_sha256"])==48
             and all(rec["per_family"][f]["pairs"]==12 for f in frozen.FAMILIES)
             and rec["max_retained"]<=9
             and (rec["max_active"]<=7 if lane=="Yggdrasil"
                  else rec["max_active"]<=192),
             "FULL_FAMILY_AND_HARD_STATE_BUDGET")
    return {"phase":phase,"paired_source_graphs":48,
            "source_construction_protected":False,
            "original_source_only":True,
            "arms":outcomes,"posthoc_diagnostics":diagnostics}

def run(o,t,u,w,x,y,z,aa,ab_path):
    frozen.frozen()
    bases,deltas=original_custody(o,t,u,w,x,y,z,aa,ab_path)
    result={"schema":SCHEMA,"freeze_git_blob":frozen.FREEZE_BLOB,
            "original_ab_json_sha256":AB_RAW_SHA,
            "zero_new_training":True,"frozen_model_weights":True,
            "protected_first_use":False,"independent_science_acceptance":False,
            "optimizer_promotion":False,"production":False,
            "accepted_ref_mutations":0,"cost_matched_superiority":False,
            "lanes":[]}
    for lane in ("Wingless","Yggdrasil"):
        row={"lane":lane,"FIT":score(lane,"FIT",bases[lane],deltas[lane]),
             "DEV":score(lane,"DEV",bases[lane],deltas[lane]),
             "original_weights_sha256":original_t.digest(bases[lane]),
             "original_delta_sha256":original_t.digest(deltas[lane])}
        result["lanes"].append(row)
    return result

def main():
    p=argparse.ArgumentParser()
    for name in ("o","t","u","w","x","y","z","aa","ab","output"):
        p.add_argument("--"+name,required=True)
    args=p.parse_args();target=Path(args.output)
    need(target.parent.is_dir() and not target.exists(),
         "NO_OVERWRITE_AUTHENTIC_RECEIPT")
    r=run(args.o,args.t,args.u,args.w,args.x,args.y,args.z,args.aa,args.ab)
    raw=json.dumps(r,indent=2,sort_keys=True).encode()+b"\n"
    with target.open("xb") as f:f.write(raw)
    print("F124AC_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    for row in r["lanes"]:
        a=row["DEV"]["arms"]
        if row["lane"]=="Wingless":
            print("F124AC_WING_DEV=one:"+str(a["one_state_AB"]["paired"])+
                  "/48;three:"+str(a["three_state_AB"]["paired"])+"/48")
        else:
            print("F124AC_YGG_DEV=soft:"+str(a["soft_AB"]["paired"])+
                  "/48;T:"+str(a["T_original"]["paired"])+
                  "/48;Z:"+str(a["Z_exact"]["paired"])+"/48")

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,KeyError,TypeError,ArithmeticError) as e:
        print("F124AC_FAIL_CLOSED:"+str(e),file=sys.stderr)
        sys.exit(1)
