"""F124-AA independent developmental transfer on novel key encodings, decoy
topology and 10–12-hop chains; source-only public reference checks.

All model parameters are original FIT-only; public destination selection is
frozen prior to this source's construction. For 7–9 hops, reference original
O/U logits must replay byte-identically. For 10–12 hops, the original source
validator does not support these depths, so this module extends the SAME
frozen algorithm and reports it as an adaptation, not original-model approval.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import tracemalloc
import f124aa_source as source
import f124v_yggdrasil_causal_trace as V
import f124o_native_learners as O

need=source.need
original_forward=V.original_forward
ARMS=("O","U")
MODES=("original","diverse")
FAMILIES=("rekey","rewire","long_depth")
SCHEMA="forge.research.f124aa.yggdrasil-independent-transfer.v1"

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
    if len(g["roles"])<=9 and mode=="original":
        ref,_=original_forward(arm,g,weights)
        need(logit.hex()==ref.hex(),"ORIGINAL_7_9_MODEL_REPLAY_"+arm)
    return {"prediction":bool(O.sigmoid(logit)>=.5),
            "logit_hex":logit.hex(),"hops":hops,
            "total_evictions":sum(h["evictions"] for h in hops),
            "final_active":len(active),"final_retained":len(retained)}





def exact_positive_prefix(g):
    """AFTER model evaluation: uniquely find complete public token-valid route."""
    source.validate_public(g)
    edges=O.sorted_edges(g)
    finished=[]
    def walk(hop,node,carried,path):
        if hop==len(g["roles"]):
            if node==g["target"]:
                finished.append(path)
                need(len(finished)<=1,"NONUNIQUE_PUBLIC_CAUSAL_PATH")
            return
        for e in edges:
            if e["from"]==node and e["role"]==g["roles"][hop] and (
                carried is None or tuple(e["src_bits"])==carried):
                walk(hop+1,e["to"],tuple(e["dst_bits"]),
                     path+((e["to"],tuple(e["dst_bits"])),))
    walk(0,g["start"],None,())
    need(len(finished)==1 and len(finished[0])==len(g["roles"]),
         "NO_SINGLE_PUBLIC_POSITIVE_PATH")
    return finished[0]



def measure(weights,phase):
    out={}
    for family in FAMILIES:
        result={arm:{mode:{"pairs":0,"correct":0,"path_lost":0,
                          "candidate_over16":0,"source_depths":{},
                          "inference_ns":0,"inference_py_peak_max":0,
                          "cases":[]}
                     for mode in MODES} for arm in ARMS}
        for vector in source.VECTORS:
            for seed in source.COHORTS["YggdrasilStress"][phase]:
                p,n=source.transfer_pair(seed,vector,phase,family)
                need(source.paired_admit(p,n),"PUBLIC_PAIR_INVALID")
                blind={}
                for arm in ARMS:
                    for mode in MODES:
                        t0=time.perf_counter_ns()
                        tracemalloc.start()
                        tracemalloc.reset_peak()
                        x=forward(arm,p,weights,mode)
                        y=forward(arm,n,weights,mode)
                        elapsed=time.perf_counter_ns()-t0
                        _,pk=tracemalloc.get_traced_memory()
                        tracemalloc.stop()
                        blind[(arm,mode)]=(x,y,elapsed,pk)
                route=exact_positive_prefix(p)
                for arm in ARMS:
                    for mode in MODES:
                        x,y,elapsed,pk=blind[(arm,mode)]
                        detailed=forward(arm,p,weights,mode,route)
                        need(detailed["logit_hex"]==x["logit_hex"],
                             "ORACLE_INFERENCE_LEAK")
                        lost=any(h["stage"] in ("pruned","not_generated")
                                 for h in detailed["hops"])
                        observed=max(h["number_candidates"] for h in detailed["hops"])
                        ok=x["prediction"] and not y["prediction"]
                        row=result[arm][mode]
                        row["pairs"]+=1;row["correct"]+=int(ok)
                        row["path_lost"]+=int(lost)
                        row["candidate_over16"]+=int(observed>16)
                        row["inference_ns"]+=elapsed
                        row["inference_py_peak_max"]=max(row["inference_py_peak_max"],pk)
                        depth=str(len(p["roles"]))
                        row["source_depths"].setdefault(depth,{"pairs":0,"correct":0,
                                                                  "lost":0})
                        d=row["source_depths"][depth]
                        d["pairs"]+=1;d["correct"]+=int(ok);d["lost"]+=int(lost)
                        row["cases"].append({"seed":seed,"vector":list(vector),
                            "family":family,"depth":int(depth),
                            "correct_pair":bool(ok),"path_lost":lost,
                            "candidate_max":observed,
                            "prediction_positive":x["prediction"],
                            "prediction_negative":y["prediction"],
                            "positive_logit_hex":x["logit_hex"],
                            "negative_logit_hex":y["logit_hex"],
                            "first_loss":next((h["hop"] for h in detailed["hops"]
                                 if h["stage"] in ("pruned","not_generated")),None),
                            "inference_ns":elapsed,"inference_py_peak_bytes":pk,
                            "per_hop":detailed["hops"]})
        for arm in ARMS:
            for mode in MODES:
                x=result[arm][mode]
                need(x["pairs"]==48 and len(x["cases"])==48 and
                     all(v["pairs"]==16 for v in x["source_depths"].values())
                     and len(x["source_depths"])==3,
                     "SOURCE_DENOMINATOR_OR_DEPTH")
                x["cases_sha256"]=hashlib.sha256(json.dumps(
                   x["cases"],sort_keys=True,separators=(",",":")).encode()).hexdigest()
                x["cell_slots"]={"active":7,"retained":9,"total":16}
                x["depth_over_original_source_limit"]=family=="long_depth"
        out[family]=result
    return out


def main():
    p=argparse.ArgumentParser()
    for x in ("o","r","s","u"):
        p.add_argument("--original-"+x,required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    source.frozen()
    weights=V.original_weights(args.original_o,args.original_r,
                               args.original_s,args.original_u)
    result={"schema":SCHEMA,"freeze_blob":source.PROTOCOL_BLOB,
        "FIT":measure(weights,"FIT"),"DEV":measure(weights,"DEV"),
        "no_new_training":True,"original_weights_unchanged":True,
        "original_7_9_logit_replay_enforced":True,
        "long_depth_uses_extended_public_validation_not_original_certification":True,
        "same_16_cell_slots":True,"total_physical_ram_equal_proven":False,
        "new_source_is_development_only":True,
        "protected_original_first_use":False,"independent_science_acceptance":False,
        "optimizer_promotion":False,"accepted_ref_changes":False}
    path=Path(args.output)
    need(path.parent.is_dir() and not path.exists(),"NO_OVERWRITE")
    raw=(json.dumps(result,sort_keys=True,indent=2)+"\n").encode()
    with path.open("xb") as f:f.write(raw)
    print("F124AA_Y_SHA256="+hashlib.sha256(raw).hexdigest(),flush=True)
    for family,arms in result["DEV"].items():
        for arm,modes in arms.items():
            for mode,x in modes.items():
                print("F124AA_DEV_"+family+"_"+arm+"_"+mode+
                      ":paired="+str(x["correct"])+"/48:lost="+
                      str(x["path_lost"])+"/48:over16="+
                      str(x["candidate_over16"])+"/48:py_peak="+
                      str(x["inference_py_peak_max"])+
                      ":cpu_ns="+str(x["inference_ns"]),flush=True)


if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as e:
        print("F124AA_Y_QUARANTINE="+str(e),file=sys.stderr)
        sys.exit(1)
