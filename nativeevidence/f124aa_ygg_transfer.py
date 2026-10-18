"""F124-AA independent 16-cell public-destination diversity diagnostic.
True route is only evaluated after all original and candidate model scores.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import f124aa_source as source
import f124v_yggdrasil_causal_trace as V
import f124o_native_learners as O
need=V.need
original_forward=V.original_forward
ARMS=("O","U")
MODES=("original","diverse")
SCHEMA="forge.research.f124aa.public-node-diversity-16-cell-development.v1"

def forward(arm,g,weights,mode='original',positive_prefix=None):
    """Instrument model allocation. Prefix remains evaluator-only diagnostic."""
    source.validate_public(g)
    source.need(mode in ("original","diverse"),"MODE")
    active_limit=7
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
        if mode=="diverse":
            winners=[]
            seen=set()
            for row in candidates:
                if row[2][0] not in seen:
                    winners.append(row)
                    seen.add(row[2][0])
                    if len(winners)==active_limit:break
            selected_pre={id(row) for row in winners}
            for row in candidates:
                if len(winners)==active_limit:break
                if id(row) not in selected_pre:
                    winners.append(row)
        else:
            winners=candidates[:active_limit]
        active=[row[2] for row in winners]
        selected={id(row) for row in winners}
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
    if mode=="original":
        need(logit.hex()==ref.hex(),"ORIGINAL_7_9_MODEL_REPLAY_"+arm)
    return {"prediction":bool(O.sigmoid(logit)>=.5),
            "logit_hex":logit.hex(),"hops":hops,
            "total_evictions":sum(h["evictions"] for h in hops),
            "final_active":len(active),"final_retained":len(retained)}




def measure(weights,phase):
    result={arm:{mode:{"paired":0,"pairs":0,"lost":0,"pressure_over16":0,
                         "by_depth":{str(d):{"pairs":0,"paired":0,"lost":0}
                                       for d in (7,8,9)},
                         "cases":[]} for mode in MODES}
             for arm in ARMS}
    for v in source.VECTORS:
        for seed in source.COHORTS["YggdrasilStress"][phase]:
            positive,negative=source.stress_pair(seed,v,phase)
            source.paired_admit(positive,negative)
            blind={(arm,mode):(forward(arm,positive,weights,mode),
                               forward(arm,negative,weights,mode))
                   for arm in ARMS for mode in MODES}
            path=V.exact_positive_prefix(positive)
            depth=str(len(positive["roles"]))
            for arm in ARMS:
                for mode in MODES:
                    p,n=blind[(arm,mode)]
                    detailed=forward(arm,positive,weights,mode,path)
                    source.need(detailed["logit_hex"]==p["logit_hex"],
                                "INFERENCE_MUST_BE_BLIND_TO_ORACLE")
                    lost=any(h["stage"] in ("pruned","not_generated")
                             for h in detailed["hops"])
                    over16=max(h["number_candidates"] for h in detailed["hops"])>16
                    correct=p["prediction"] and not n["prediction"]
                    q=result[arm][mode]
                    q["pairs"]+=1;q["paired"]+=int(correct)
                    q["lost"]+=int(lost)
                    q["pressure_over16"]+=int(over16)
                    q["by_depth"][depth]["pairs"]+=1
                    q["by_depth"][depth]["paired"]+=int(correct)
                    q["by_depth"][depth]["lost"]+=int(lost)
                    q["cases"].append({"seed":seed,"vector":list(v),
                        "depth":int(depth),"paired_correct":bool(correct),
                        "first_path_loss":next((h["hop"] for h in detailed["hops"]
                             if h["stage"] in ("pruned","not_generated")),None),
                        "max_candidates":max(h["number_candidates"]
                                         for h in detailed["hops"]),
                        "positive_logit":p["logit_hex"],
                        "negative_logit":n["logit_hex"],
                        "per_hop":detailed["hops"]})
    for arm in ARMS:
        for mode in MODES:
            q=result[arm][mode]
            source.need(q["pairs"]==48 and len(q["cases"])==48 and
                 all(d["pairs"]==16 for d in q["by_depth"].values()),
                 "COMPLETE_DEVELOPMENT_DENOMINATOR")
            q["case_sha256"]=hashlib.sha256(json.dumps(q["cases"],sort_keys=True,
                     separators=(",",":")).encode()).hexdigest()
            q["active_slots"]=7;q["retained_slots"]=9
            q["persistent_cell_slots"]=16
    return result

def main():
    ap=argparse.ArgumentParser()
    for name in ("o","r","s","u"):ap.add_argument("--original-"+name,required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    source.frozen()
    weight=V.original_weights(args.original_o,args.original_r,
                              args.original_s,args.original_u)
    output=Path(args.output)
    source.need(output.parent.is_dir() and not output.exists(),"OUTPUT_NONOVERWRITE")
    x={"schema":SCHEMA,"freeze_blob":source.PROTOCOL_BLOB,
        "original_fit_coefficients_unchanged":True,
        "no_new_training_or_parameters":True,
        "original_7_9_hex_replay_passed":True,
        "model_never_reads_truth_or_target_for_allocation":True,
        "persistent_record_slots":16,"same_physical_total_heap_proven":False,
        "FIT":measure(weight,"FIT"),"DEV":measure(weight,"DEV"),
        "protected_first_use":False,"science_accepted":False,
        "optimizer_promoted":False,"accepted_ref_mutations":False}
    data=(json.dumps(x,sort_keys=True,indent=2)+"\n").encode()
    with output.open("xb") as f:f.write(data)
    print("F124AAY_SHA256="+hashlib.sha256(data).hexdigest(),flush=True)
    for arm in ARMS:
        for mode in MODES:
            v=x["DEV"][arm][mode]
            print("F124AAY_DEV_"+arm+"_"+mode+
                  ":paired="+str(v["paired"])+"/48"+
                  ":lost="+str(v["lost"])+"/48"+
                  ":pressure="+str(v["pressure_over16"])+"/48",flush=True)

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,KeyError,TypeError,ArithmeticError) as e:
        print("F124AAY_QUARANTINED="+str(e),file=sys.stderr)
        sys.exit(1)
