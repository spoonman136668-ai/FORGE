"""F124-AB frozen independent 10-12-hop false decision forensic.

All fitted O/U weights remain untouched; two frozen 16-cell allocators.
FIT-only 11-value threshold grid is selected before DEV construction;
failure type separates false positive evidence from absent causal memory.
"""
from __future__ import annotations
import argparse, hashlib, json, math, sys
from pathlib import Path
import f124ab_source as source
import f124v_yggdrasil_causal_trace as V
import f124o_native_learners as O
need=source.need
original_forward=V.original_forward
ARMS=("O","U")
MODES=("original","diverse")
GRID=(-8,-6,-4,-2,-1,0,1,2,4,6,8)
SCHEMA="forge.research.f124ab.long-chain-terminal-evidence.v1"

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
    return {"target_best_accumulated_score":best,
            "terminal_target_cell_count":len(terminal),
            "prediction":bool(O.sigmoid(logit)>=.5),
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




def source_pairs(phase):
    return [source.transfer_pair(seed,vector,phase,"long_depth")
            for vector in source.VECTORS
            for seed in source.COHORTS["YggdrasilStress"][phase]]

def blind_eval(weights,phase):
    # Inference first, causal oracle only after predictions have completed.
    out={arm:{mode:[] for mode in MODES} for arm in ARMS}
    for i,(pos,neg) in enumerate(source_pairs(phase)):
        blind={(arm,mode):(forward(arm,pos,weights,mode),
                           forward(arm,neg,weights,mode))
               for arm in ARMS for mode in MODES}
        truepath=exact_positive_prefix(pos)
        for arm in ARMS:
            for mode in MODES:
                p,n=blind[(arm,mode)]
                traced=forward(arm,pos,weights,mode,truepath)
                need(traced["logit_hex"]==p["logit_hex"],
                     "EVALUATOR_PATH_LEAK")
                loss=next((x["hop"] for x in traced["hops"]
                           if x["stage"] in ("pruned","not_generated")),None)
                out[arm][mode].append({
                    "index":i,"depth":len(pos["roles"]),
                    "positive_logit_hex":p["logit_hex"],
                    "negative_logit_hex":n["logit_hex"],
                    "positive_logit":float.fromhex(p["logit_hex"]),
                    "negative_logit":float.fromhex(n["logit_hex"]),
                    "positive_target_score":p["target_best_accumulated_score"],
                    "negative_target_score":n["target_best_accumulated_score"],
                    "positive_terminal_cell_count":p["terminal_target_cell_count"],
                    "negative_terminal_cell_count":n["terminal_target_cell_count"],
                    "causal_prefix_survived":loss is None,
                    "first_path_loss":loss,
                    "positive_false_negative":not p["prediction"],
                    "negative_false_positive":n["prediction"],
                    "unadjusted_pair_correct":p["prediction"] and not n["prediction"],
                    "hops":traced["hops"]})
    need(all(len(out[arm][mode])==48
        for arm in ARMS for mode in MODES),"48_CASES_PER_MODEL")
    return out

def choose_fit_thresholds(fit):
    # Fixed grid, fit pairs ONLY. No DEV data permitted here.
    selected={};curves={}
    for arm in ARMS:
        selected[arm]={};curves[arm]={}
        for mode in MODES:
            cases=fit[arm][mode]
            chart={str(t):sum(row["positive_logit"]>=t and
                               row["negative_logit"]<t for row in cases)
                   for t in GRID}
            chosen=max(GRID,key=lambda t:(chart[str(t)],-abs(t),-t))
            selected[arm][mode]=chosen
            curves[arm][mode]=chart
    return selected,curves

def summarize(cases,threshold):
    per_depth={str(d):{"pairs":0,"paired":0,"false_positive":0,
                        "false_negative":0} for d in (10,11,12)}
    errors={"false_positives":0,"false_negatives":0,
            "paired_correct":0,"path_losses":0,
            "retained_path_but_wrong_pair":0,"positive_target_absent":0,
            "negative_target_present":0}
    for row in cases:
        p=row["positive_logit"]>=threshold
        n=row["negative_logit"]>=threshold
        ok=p and not n
        d=per_depth[str(row["depth"])]
        d["pairs"]+=1;d["paired"]+=int(ok)
        d["false_positive"]+=int(n);d["false_negative"]+=int(not p)
        errors["paired_correct"]+=int(ok)
        errors["false_positives"]+=int(n)
        errors["false_negatives"]+=int(not p)
        errors["path_losses"]+=int(not row["causal_prefix_survived"])
        errors["retained_path_but_wrong_pair"]+=int(
            row["causal_prefix_survived"] and not ok)
        errors["positive_target_absent"]+=int(row["positive_terminal_cell_count"]==0)
        errors["negative_target_present"]+=int(row["negative_terminal_cell_count"]>0)
    need(all(x["pairs"]==16 for x in per_depth.values()),"DEPTH_BALANCE")
    return {**errors,"by_depth":per_depth,"threshold":threshold}

def main():
    ap=argparse.ArgumentParser()
    for x in ("o","r","s","u"):ap.add_argument("--original-"+x,required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args();source.frozen()
    weights=V.original_weights(args.original_o,args.original_r,
                               args.original_s,args.original_u)
    fit=blind_eval(weights,"FIT")
    thresholds,curves=choose_fit_thresholds(fit)
    dev=blind_eval(weights,"DEV")
    report={"schema":SCHEMA,"freeze_blob":source.PROTOCOL_BLOB,
       "training_steps":0,"selected_from_FIT_only":True,
       "FIT_threshold_grid":list(GRID),"FIT_curves":curves,
       "FIT_selected_thresholds":thresholds,
       "development_unmodified_models":True,
       "FIT":{a:{m:summarize(fit[a][m],thresholds[a][m])
                 for m in MODES} for a in ARMS},
       "DEV":{a:{m:{"unadjusted":summarize(dev[a][m],0),
                  "fit_threshold":summarize(dev[a][m],thresholds[a][m]),
                  "cases":dev[a][m]}
                 for m in MODES} for a in ARMS},
       "protected_first_use":False,"science_accepted":False,
       "optimizer_promoted":False,"accepted_refs_modified":False}
    target=Path(args.output)
    need(target.parent.is_dir() and not target.exists(),"IMMUTABLE_OUTPUT")
    data=(json.dumps(report,sort_keys=True,indent=2)+"\n").encode()
    with target.open("xb") as f:f.write(data)
    print("F124AB_Y_SHA256="+hashlib.sha256(data).hexdigest(),flush=True)
    print("F124AB_FIT_THRESHOLDS="+json.dumps(thresholds,sort_keys=True),flush=True)
    for arm in ARMS:
        for mode in MODES:
            q=report["DEV"][arm][mode]
            x=q["unadjusted"];z=q["fit_threshold"]
            print("F124AB_DEV_"+arm+"_"+mode+
                  ":original="+str(x["paired_correct"])+"/48:FIT_adjusted="+
                  str(z["paired_correct"])+"/48:FP="+str(x["false_positives"])+
                  ":FN="+str(x["false_negatives"])+
                  ":path_lost="+str(x["path_losses"])+
                  ":survived_but_wrong="+str(x["retained_path_but_wrong_pair"]),flush=True)

if __name__=="__main__":
    try:main()
    except (ValueError,KeyError,TypeError,OSError,ArithmeticError) as e:
        print("F124AB_Y_QUARANTINE="+str(e),file=sys.stderr);sys.exit(1)
