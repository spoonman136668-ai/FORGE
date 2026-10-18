"""F124-Y independent equal-total-cell-budget study (16 cells, no new training).

Every frozen 7+9 model logit must reproduce original bit for bit. Comparators
only move allocation between 16 original persistent node/key/score cell slots.
Evaluator-only causal-path oracle is calculated after model scoring.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

import f124y_source as source
import f124o_native_learners as O
import f124v_yggdrasil_causal_trace as V

need=V.need
original_forward=V.original_forward
ARMS=("O","U")
ALLOCATIONS=(6,7,8,9,10)
SCHEMA="forge.research.f124y.same-16-cells-stress-repartition.v1"

def partition_forward(arm,g,weights,active_limit,positive_prefix=None):
    """Instrument model allocation. Prefix remains evaluator-only diagnostic."""
    source.validate_public(g)
    need(active_limit in (6,7,8,9,10),"ONLY_FROZEN_16_CELL_ALLOCATIONS")
    base=list(weights["base"])
    edges=O.sorted_edges(g)
    active=[(g["start"],None,0.)]
    retained=[]
    R_sum=R_n=R_target_sum=R_target_n=0.
    hops=[]
    def comp(carried,src):
        if carried is None:return 1.
        return sum(base[j]*sum(int(a==b) for a,b in zip(
            carried[j*4:j*4+4],src[j*4:j*4+4]))/4.
            for j in range(4))/4.
    def future(edge,nextr):
        if nextr is None:return .5
        options=[e for e in edges if e["from"]==edge["to"] and
                 e["role"]==nextr]
        return max((sum(int(a==b) for a,b in zip(
            edge["dst_bits"],q["src_bits"]))/16. for q in options),
                   default=0.)
    for i,role in enumerate(g["roles"]):
        nextr=g["roles"][i+1] if i+1<len(g["roles"]) else None
        prior_active=active
        prior_retained=retained
        candidates=[]
        for node,carried,score in active+retained:
            for e in edges:
                if e["from"]!=node or e["role"]!=role:continue
                similarity=comp(carried,e["src_bits"])
                value=score+base[4]*(similarity-.35)
                ranking=base[5]*(similarity-.5)
                if arm=="R":
                    soft=O.sigmoid(6.*(similarity-.5))
                    R_sum+=soft
                    R_n+=1
                    if i==len(g["roles"])-1 and e["to"]==g["target"]:
                        R_target_sum+=soft;R_target_n+=1
                elif arm=="S":
                    confidence=O.sigmoid(6.*(similarity-.5))-.5
                    value+=weights["S"][0]*confidence
                    ranking+=weights["S"][1]*confidence
                elif arm=="U":
                    confidence=O.sigmoid(6.*(similarity-.5))-.5
                    ranking+=weights["U"][0]*confidence
                    ranking+=weights["U"][1]*(future(e,nextr)-.5)
                cell=(e["to"],tuple(e["dst_bits"]),value)
                candidates.append((value+ranking,value-ranking,cell))
        candidates.sort(key=lambda x:(-x[0],-x[1],x[2][0],x[2][1]))
        active=[row[2] for row in candidates[:active_limit]]
        selected={id(row) for row in candidates[:active_limit]}
        extras=[row for row in candidates if id(row) not in selected]
        extras.sort(key=lambda x:(-x[1],-x[0],x[2][0],x[2][1]))
        retained=[row[2] for row in extras[:16-active_limit]]
        need(len(active)<=active_limit and len(retained)<=16-active_limit and
             len(active)+len(retained)<=16,"ORIGINAL_CELL_BUDGET")
        if positive_prefix is not None:
            goal=positive_prefix[i]
            def has(cell):
                return (cell[0],cell[1])==goal
            indices=[idx for idx,c in enumerate(candidates) if has(c[2])]
            cscore=max((candidates[j][0] for j in indices),default=None)
            best=candidates[0][0] if candidates else None
            report={"hop":i+1,"depth":len(g["roles"]),
              "candidate_generated":bool(indices),
              "candidate_best_rank":(min(indices)+1 if indices else None),
              "candidate_priority_gap_to_best":(
                round(best-cscore,9) if cscore is not None else None),
              "in_active":any(has(c) for c in active),
              "in_retained":any(has(c) for c in retained),
              "number_candidates":len(candidates),
              "number_active":len(active),
              "number_retained":len(retained),
              "evictions":max(0,len(candidates)-16),
              "retained_coming_into_hop":len(prior_retained),
              "from_retained_to_active":False}
            if i:
                previous=positive_prefix[i-1]
                prior_causal_retained=any(
                    (x[0],x[1])==previous for x in prior_retained)
                prior_causal_active=any(
                    (x[0],x[1])==previous for x in prior_active)
                report["previous_causal_active"]=prior_causal_active
                report["previous_causal_retained"]=prior_causal_retained
                report["from_retained_to_active"]=bool(
                    prior_causal_retained and report["in_active"]
                    and not prior_causal_active)
            if report["in_active"]:report["stage"]="active"
            elif report["in_retained"]:report["stage"]="retained"
            elif indices:report["stage"]="pruned"
            else:report["stage"]="not_generated"
            hops.append(report)
    terminal=[value for node,_,value in active+retained
              if node==g["target"]]
    best=max(terminal,default=-2.*len(g["roles"]))
    logit=4.*(best/max(1,len(g["roles"])-1)-base[6])
    if arm=="R":
        mean=R_sum/max(1,R_n)-.5
        target=(R_target_sum/max(1,R_target_n)-.5) if R_target_n else -.5
        logit=logit+2.*weights["R"][0]*mean
        logit=logit+2.*weights["R"][1]*target
    ref,_=original_forward(arm,g,weights)
    if active_limit==7:
        need(logit.hex()==ref.hex(),"ORIGINAL_7_9_MODEL_REPLAY_"+arm)
    return {"prediction":bool(O.sigmoid(logit)>=.5),
            "logit_hex":logit.hex(),"hops":hops,
            "total_evictions":sum(h["evictions"] for h in hops),
            "final_active":len(active),"final_retained":len(retained)}



def measure(weights,phase):
    records={}
    for arm in ARMS:
        records[arm]={str(a):{"paired":0,"pairs":0,"paths_lost":0,
                              "candidate_above_16":0,"max_candidate_count":0,
                              "by_depth":{str(d):{"pairs":0,"paired":0,"lost":0}
                                          for d in (7,8,9)},
                              "cases":[]} for a in ALLOCATIONS}
    for v in source.VECTORS:
        for seed in source.COHORTS["YggdrasilStress"][phase]:
            pos,neg=source.stress_pair(seed,v,phase)
            source.paired_admit(pos,neg)
            # Score ALL arm/partition variants BEFORE computing true path.
            blind={}
            for arm in ARMS:
                for a in ALLOCATIONS:
                    blind[(arm,a)]=(partition_forward(arm,pos,weights,a),
                                    partition_forward(arm,neg,weights,a))
            path=V.exact_positive_prefix(pos)
            depth=str(len(pos["roles"]))
            for arm in ARMS:
                for a in ALLOCATIONS:
                    left,right=blind[(arm,a)]
                    traced=partition_forward(arm,pos,weights,a,
                                             positive_prefix=path)
                    need(traced["logit_hex"]==left["logit_hex"],
                         "ORACLE_MUST_NOT_MODIFY_ANY_MODEL_SCORE")
                    lost=any(h["stage"] in ("pruned","not_generated")
                             for h in traced["hops"])
                    nmax=max(h["number_candidates"] for h in traced["hops"])
                    success=left["prediction"] and not right["prediction"]
                    if a==7:
                        pold,_=V.original_forward(arm,pos,weights)
                        nold,_=V.original_forward(arm,neg,weights)
                        need(pold.hex()==left["logit_hex"] and
                             nold.hex()==right["logit_hex"],
                             "ORIGINAL_7_9_SIGNED_LOGIT_MISMATCH")
                    rec=records[arm][str(a)]
                    rec["pairs"]+=1;rec["paired"]+=int(success)
                    rec["paths_lost"]+=int(lost)
                    rec["candidate_above_16"]+=int(nmax>16)
                    rec["max_candidate_count"]=max(rec["max_candidate_count"],nmax)
                    rec["by_depth"][depth]["pairs"]+=1
                    rec["by_depth"][depth]["paired"]+=int(success)
                    rec["by_depth"][depth]["lost"]+=int(lost)
                    rec["cases"].append({"seed":seed,"vector":list(v),
                       "allocation":[a,16-a],"depth":int(depth),
                       "correct_pair":bool(success),"causal_path_lost":lost,
                       "first_loss":next((h["hop"] for h in traced["hops"]
                             if h["stage"] in ("pruned","not_generated")),None),
                       "max_candidates":nmax,
                       "positive_logit_hex":left["logit_hex"],
                       "negative_logit_hex":right["logit_hex"],
                       "hops":traced["hops"]})
    for arm in ARMS:
        for a in ALLOCATIONS:
            rec=records[arm][str(a)]
            need(rec["pairs"]==48 and len(rec["cases"])==48 and
                 all(item["pairs"]==16 for item in rec["by_depth"].values()),
                 "FULL_48_PER_DEPTH_AND_BUDGET")
            rec["case_sha256"]=hashlib.sha256(json.dumps(
                 rec["cases"],sort_keys=True,separators=(",",":")).encode()).hexdigest()
            rec["allocation"]={"active":a,"retained":16-a,
                                  "same_total_cells":16,
                                  "no_new_cell_features":True}
    return records


def main():
    p=argparse.ArgumentParser()
    for name in ("o","r","s","u"):p.add_argument("--original-"+name,required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    source.frozen()
    weights=V.original_weights(a.original_o,a.original_r,a.original_s,a.original_u)
    report={"schema":SCHEMA,"freeze_blob":source.PROTOCOL_BLOB,
        "fixed_number_of_cells":16,"same_cell_fields":True,
        "model_weights_unchanged":True,"new_training_steps":0,
        "original_seven_nine_logit_replay_verified":True,
        "protected_first_use":False,"science_accepted":False,
        "optimizer_promoted":False,
        "FIT":measure(weights,"FIT"),"DEV":measure(weights,"DEV")}
    out=Path(a.output)
    source.need(out.parent.is_dir() and not out.exists(),"OUTPUT_EXCLUSIVE")
    raw=(json.dumps(report,indent=2,sort_keys=True)+"\n").encode()
    with out.open("xb") as h:h.write(raw)
    print("F124YC_SHA256="+hashlib.sha256(raw).hexdigest(),flush=True)
    for arm in ARMS:
        for alloc in ALLOCATIONS:
            x=report["DEV"][arm][str(alloc)]
            print("F124YC_DEV_"+arm+":"+str(alloc)+"+"+str(16-alloc)+
                  ":paired="+str(x["paired"])+"/48:lost="+str(x["paths_lost"])+
                  "/48:over16="+str(x["candidate_above_16"])+"/48",flush=True)


if __name__=="__main__":
    try:main()
    except (ValueError,KeyError,OSError,TypeError,ArithmeticError) as e:
        print("F124YC_QUARANTINE="+str(e),file=sys.stderr)
        sys.exit(1)
