"""F124-AD original-cell recursive intermediate-hop credit and mismatch controls.

Original exact 7+9 public destination-diverse selector and unchanged trained O/U
weights. The ONLY hypothesis changes existing cell.score at each intermediate
public edge by FIT-frozen gamma (exact raw16 continuity) or penalty (mismatch).
No new persistent state; causal reference path used solely after inference.
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
import f124ad_source as source
import f124v_yggdrasil_causal_trace as V
import f124o_native_learners as O
import f124ac_terminal_intervention as prior
need=source.need
original_forward=V.original_forward
ARMS=("O","U")
FAMILIES=("baseline","exact_credit","mismatch_penalty","combined")
GRID=(0.,.1,.25,.5,1.,2.,4.,8.)
SCHEMA="forge.research.f124ad.recursive-causal-credit.v1"

def forward(arm,g,weights,mode='diverse',positive_prefix=None,gamma=0.,penalty=0.):
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
    terminal_exact_cells=set()
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
                if carried is not None:
                    if carried==tuple(e["src_bits"]):
                        value+=gamma
                    else:
                        value-=penalty
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
                if (i==len(g["roles"])-1 and e["to"]==g["target"]
                    and carried is not None
                    and carried==tuple(e["src_bits"])):
                    terminal_exact_cells.add((tuple(e["dst_bits"]),value.hex()))
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
    last_link_confirmed=any(
        node==g["target"] and (tuple(bits),value.hex()) in terminal_exact_cells
        for node,bits,value in active+retained)
    # Persistent score is the sole accumulator; no extra cell/feature storage.
    if len(g["roles"])<=9 and mode=="original" and gamma==0 and penalty==0:
        ref,_=original_forward(arm,g,weights)
        need(logit.hex()==ref.hex(),"ORIGINAL_7_9_MODEL_REPLAY_"+arm)
    return {"terminal_exact_link_confirmed":last_link_confirmed,
            "ephemeral_exact_candidate_keys":len(terminal_exact_cells),
            "target_best_accumulated_score":best,
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
    cases=[source.transfer_pair(seed,vector,phase,"long_depth")
          for vector in source.VECTORS
          for seed in source.COHORTS["YggdrasilStress"][phase]]
    need(len(cases)==48,"EXACT_48_PER_PHASE")
    return cases

def params(family):
    if family=="baseline":return ((0.,0.),)
    if family=="exact_credit":return tuple((gamma,0.) for gamma in GRID)
    if family=="mismatch_penalty":return tuple((0.,p) for p in GRID)
    return tuple((gamma,p) for gamma in GRID for p in GRID)

def measure(weights,cohort,arm,gamma,penalty,trace=False):
    cases=[]
    for index,(positive,negative) in enumerate(cohort):
        pos=forward(arm,positive,weights,gamma=gamma,penalty=penalty)
        neg=forward(arm,negative,weights,gamma=gamma,penalty=penalty)
        p=float.fromhex(pos["logit_hex"]);n=float.fromhex(neg["logit_hex"])
        if gamma==0 and penalty==0:
            for graph,current in ((positive,pos),(negative,neg)):
                old=prior.forward(arm,graph,weights,alpha=0.,beta=0.)
                need(old["logit_hex"]==current["logit_hex"],
                     "UNCHANGED_ORIGINAL_BASELINE_NOT_BIT_IDENTICAL")
        rec={"index":index,"depth":len(positive["roles"]),
            "positive_hex":pos["logit_hex"],"negative_hex":neg["logit_hex"],
            "positive":p>=0,"negative":n>=0,
            "paired_correct":p>=0 and n<0,
            "false_positive":n>=0,"false_negative":p<0,
            "positive_terminal_cell_count":pos["terminal_target_cell_count"],
            "negative_terminal_cell_count":neg["terminal_target_cell_count"],
            "positive_score_hex":float(pos["target_best_accumulated_score"]).hex(),
            "negative_score_hex":float(neg["target_best_accumulated_score"]).hex(),
            "active_slots":pos["final_active"],"retained_slots":pos["final_retained"]}
        if trace:
            path=exact_positive_prefix(positive)
            observed=forward(arm,positive,weights,positive_prefix=path,
                             gamma=gamma,penalty=penalty)
            need(observed["logit_hex"]==pos["logit_hex"],
                 "CAUSAL_ORACLE_ALTERED_INFERENCE")
            rec["first_true_path_loss"]=next((
                x["hop"] for x in observed["hops"]
                if x["stage"] in ("pruned","not_generated")),None)
            rec["per_hop"]=observed["hops"]
        cases.append(rec)
    need(len(cases)==48,"DENOMINATOR_NOT_48")
    depths={str(d):{"pairs":0,"correct":0,"false_positives":0,
                     "false_negatives":0} for d in (10,11,12)}
    for v in cases:
        z=depths[str(v["depth"])]
        z["pairs"]+=1;z["correct"]+=int(v["paired_correct"])
        z["false_positives"]+=int(v["false_positive"])
        z["false_negatives"]+=int(v["false_negative"])
        need(v["active_slots"]<=7 and v["retained_slots"]<=9
             and v["active_slots"]+v["retained_slots"]<=16,
             "PERSISTENT_ORIGINAL_16_CELLS_EXCEEDED")
    need(all(z["pairs"]==16 for z in depths.values()),
         "PER_DEPTH_SOURCE_BIRTH_IMBALANCE")
    return {"pairs":48,
            "correct":sum(x["paired_correct"] for x in cases),
            "false_positives":sum(x["false_positive"] for x in cases),
            "false_negatives":sum(x["false_negative"] for x in cases),
            "first_path_losses":sum(
                x.get("first_true_path_loss") is not None for x in cases) if trace else None,
            "by_depth":depths,"cases":cases if trace else None}

def select_fit(weights,fit):
    chosen={};curves={}
    for arm in ARMS:
        chosen[arm]={};curves[arm]={}
        for family in FAMILIES:
            curve=[]
            for gamma,penalty in params(family):
                x=measure(weights,fit,arm,gamma,penalty,False)
                curve.append({"gamma":gamma,"penalty":penalty,
                    "correct":x["correct"],"false_positives":x["false_positives"],
                    "false_negatives":x["false_negatives"]})
            good=[x for x in curve if x["false_positives"]==0]
            selected=min(good,key=lambda x:(-x["correct"],
                       x["gamma"]+x["penalty"],x["gamma"],x["penalty"])
                       ) if good else None
            chosen[arm][family]=selected;curves[arm][family]=curve
    return chosen,curves

def main():
    a=argparse.ArgumentParser()
    for name in ("o","r","s","u"):
        a.add_argument("--original-"+name,required=True)
    a.add_argument("--output",required=True)
    args=a.parse_args();source.frozen()
    weights=V.original_weights(args.original_o,args.original_r,
                               args.original_s,args.original_u)
    fit=source_pairs("FIT")
    selected,curves=select_fit(weights,fit)
    dev=source_pairs("DEV")
    fit_selected={};dev_selected={};verdict={}
    for arm in ARMS:
        fit_selected[arm]={};dev_selected[arm]={}
        for family in FAMILIES:
            selection=selected[arm][family]
            if selection is None:
                fit_selected[arm][family]=None
                dev_selected[arm][family]=None
                continue
            gamma,penalty=selection["gamma"],selection["penalty"]
            fit_selected[arm][family]=measure(weights,fit,arm,gamma,penalty,False)
            dev_selected[arm][family]=measure(weights,dev,arm,gamma,penalty,True)
        baseline=dev_selected[arm]["baseline"]
        proposed=dev_selected[arm]["combined"]
        verdict[arm]=("DEVELOPMENT_SUCCESS" if
            proposed is not None and proposed["correct"]>baseline["correct"]
            and proposed["false_positives"]==0
            else "DEVELOPMENT_NEGATIVE")
    report={"schema":SCHEMA,"freeze_blob":source.PROTOCOL_BLOB,
        "fitted_original_O_U_unchanged":True,"DEV_never_selected":True,
        "original_active_slots":7,"original_retained_slots":9,
        "no_added_persistent_cell_fields":True,
        "FIT_selected":selected,"FIT_curves":curves,
        "FIT_scores":fit_selected,"DEV_scores":dev_selected,
        "verdict":verdict,"protected_first_use":False,
        "science_accepted":False,"optimizer_promoted":False}
    output=Path(args.output);need(output.parent.is_dir() and not output.exists(),
                                 "EXCLUSIVE_EVIDENCE_FILE")
    data=(json.dumps(report,sort_keys=True,indent=2)+"\n").encode()
    with output.open("xb") as h:h.write(data)
    print("F124AD_SHA256="+hashlib.sha256(data).hexdigest(),flush=True)
    for arm in ARMS:
        for family in FAMILIES:
            z=dev_selected[arm][family];c=selected[arm][family]
            print("F124AD_DEV_"+arm+"_"+family+":"+
                ("UNQUALIFIED" if z is None else
                 "paired="+str(z["correct"])+"/48:FP="+str(z["false_positives"])+
                 ":FN="+str(z["false_negatives"])+
                 ":lost="+str(z["first_path_losses"])+
                 ":gamma="+str(c["gamma"])+":penalty="+str(c["penalty"])),
                 flush=True)
        print("F124AD_VERDICT_"+arm+"="+verdict[arm],flush=True)

if __name__=="__main__":
    try:main()
    except (ValueError,KeyError,TypeError,OSError,ArithmeticError) as e:
        print("F124AD_QUARANTINE="+str(e),file=sys.stderr);sys.exit(1)
