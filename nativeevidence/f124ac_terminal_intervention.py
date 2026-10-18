"""F124-AC original 16-cell O/U terminal evidence readout (new frozen source).

FIT selects small non-negative depth correction and/or locally exact terminal
bridge bonus subject to zero FIT false positives. DEV never selects.
No new persistent state, no use of true path / label in forward scoring.
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
import f124ac_source as source
import f124v_yggdrasil_causal_trace as V
import f124o_native_learners as O

need=source.need
original_forward=V.original_forward
ARMS=("O","U")
GRID=(0.,.1,.2,.4,.8,1.6,3.2)
FAMILIES=("unchanged","depth_only","terminal_exact_only","combined")
SCHEMA="forge.research.f124ac.terminal-bridge-FIT-only.v1"

def forward(arm,g,weights,mode='diverse',positive_prefix=None,alpha=0.,beta=0.):
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
    logit+=alpha*(len(g["roles"])-9)+beta*int(last_link_confirmed)
    if len(g["roles"])<=9 and mode=="original" and alpha==0 and beta==0:
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
    return [source.transfer_pair(seed,vector,phase,"long_depth")
            for vector in source.VECTORS
            for seed in source.COHORTS["YggdrasilStress"][phase]]

def examples(weights,phase):
    out={arm:[] for arm in ARMS}
    for idx,(positive,negative) in enumerate(source_pairs(phase)):
        preds={(arm,polarity):forward(arm,g,weights,"diverse")
               for arm in ARMS
               for polarity,g in (("positive",positive),("negative",negative))}
        path=exact_positive_prefix(positive)
        for arm in ARMS:
            p=preds[(arm,"positive")];n=preds[(arm,"negative")]
            trace=forward(arm,positive,weights,"diverse",positive_prefix=path)
            need(trace["logit_hex"]==p["logit_hex"],"ORACLE_LEAK")
            lost=any(h["stage"] in ("pruned","not_generated") for h in trace["hops"])
            out[arm].append({"case":idx,"depth":len(positive["roles"]),
               "positive_base":float.fromhex(p["logit_hex"]),
               "negative_base":float.fromhex(n["logit_hex"]),
               "positive_exact_link":bool(p["terminal_exact_link_confirmed"]),
               "negative_exact_link":bool(n["terminal_exact_link_confirmed"]),
               "positive_terminal_cell_count":p["terminal_target_cell_count"],
               "negative_terminal_cell_count":n["terminal_target_cell_count"],
               "original_path_lost":lost,"positive_per_hop":trace["hops"],
               "positive_ephemeral_terminal_keys":p["ephemeral_exact_candidate_keys"],
               "negative_ephemeral_terminal_keys":n["ephemeral_exact_candidate_keys"]})
    need(all(len(out[arm])==48 for arm in ARMS),"CASES_48")
    return out

def candidates(family):
    if family=="unchanged":return [(0.,0.)]
    if family=="depth_only":return [(a,0.) for a in GRID]
    if family=="terminal_exact_only":return [(0.,b) for b in GRID]
    return [(a,b) for a in GRID for b in GRID]

def classification(row,a,b):
    bump=a*(row["depth"]-9)
    pp=row["positive_base"]+bump+b*int(row["positive_exact_link"])
    nn=row["negative_base"]+bump+b*int(row["negative_exact_link"])
    return pp>=0,nn>=0,pp,nn

def score(rows,a,b):
    all_cases=[]
    by_depth={str(d):{"cases":0,"correct":0,"false_positive":0,
                       "false_negative":0} for d in (10,11,12)}
    for row in rows:
        positive,negative,plogit,nlogit=classification(row,a,b)
        correct=positive and not negative
        d=by_depth[str(row["depth"])]
        d["cases"]+=1
        d["correct"]+=int(correct)
        d["false_positive"]+=int(negative)
        d["false_negative"]+=int(not positive)
        all_cases.append({"case":row["case"],"depth":row["depth"],
            "correct":correct,"false_positive":negative,
            "false_negative":not positive,
            "terminal_link_positive":row["positive_exact_link"],
            "terminal_link_negative":row["negative_exact_link"],
            "positive_logit_hex":plogit.hex(),
            "negative_logit_hex":nlogit.hex(),
            "path_lost":row["original_path_lost"],
            "positive_terminal_cell_count":row["positive_terminal_cell_count"],
            "negative_terminal_cell_count":row["negative_terminal_cell_count"]})
    need(all(x["cases"]==16 for x in by_depth.values()),"PER_DEPTH_16")
    return {"pairs":48,"correct":sum(z["correct"] for z in all_cases),
      "false_positives":sum(z["false_positive"] for z in all_cases),
      "false_negatives":sum(z["false_negative"] for z in all_cases),
      "path_lost":sum(z["path_lost"] for z in all_cases),
      "positive_exact_link_cases":sum(z["positive_exact_link"] for z in rows),
      "negative_exact_link_cases":sum(z["negative_exact_link"] for z in rows),
      "by_depth":by_depth,"cases":all_cases}

def choose_fit(fit_rows):
    chosen={};curves={}
    for arm in ARMS:
        chosen[arm]={};curves[arm]={}
        for family in FAMILIES:
            entries=[]
            for alpha,beta in candidates(family):
                r=score(fit_rows[arm],alpha,beta)
                entries.append({"alpha":alpha,"beta":beta,
                                "correct":r["correct"],"FP":r["false_positives"]})
            valid=[x for x in entries if x["FP"]==0]
            selected=sorted(valid,key=lambda x:(-x["correct"],x["alpha"]+x["beta"],
                                                 x["alpha"],x["beta"]))[0] if valid else None
            chosen[arm][family]=selected
            curves[arm][family]=entries
    return chosen,curves

def main():
    ap=argparse.ArgumentParser()
    for name in ("o","r","s","u"):
        ap.add_argument("--original-"+name,required=True)
    ap.add_argument("--output",required=True)
    a=ap.parse_args()
    source.frozen()
    weights=V.original_weights(a.original_o,a.original_r,a.original_s,a.original_u)
    fit=examples(weights,"FIT")
    selected,curves=choose_fit(fit)
    dev=examples(weights,"DEV")
    data={"schema":SCHEMA,"freeze_blob":source.PROTOCOL_BLOB,
          "FIT_selected":selected,"FIT_curves":curves,
          "FIT_scores":{arm:{family:score(fit[arm],x["alpha"],x["beta"])
                     if x is not None else None for family,x in selected[arm].items()}
                     for arm in ARMS},
          "DEV_scores":{arm:{family:score(dev[arm],x["alpha"],x["beta"])
                     if x is not None else None for family,x in selected[arm].items()}
                     for arm in ARMS},
          "DEV_proposals_never_selected":True,
          "original_fitted_O_U_unchanged":True,"persistent_cells":16,
          "no_original_protected_first_use":True,
          "independent_science_accepted":False,"optimizer_promoted":False}
    for arm in ARMS:
        base=data["DEV_scores"][arm]["unchanged"]
        changed=data["DEV_scores"][arm]["combined"]
        data.setdefault("development_verdict",{})[arm]=(
            "DEVELOPMENT_SUCCESS" if changed and
               changed["correct"]>base["correct"] and
               changed["false_positives"]==0
             else "DEVELOPMENT_NEGATIVE")
    out=Path(a.output);need(out.parent.is_dir() and not out.exists(),"OUTPUT_EXCLUSIVE")
    raw=(json.dumps(data,sort_keys=True,indent=2)+"\n").encode()
    with out.open("xb") as f:f.write(raw)
    print("F124AC_SHA256="+hashlib.sha256(raw).hexdigest(),flush=True)
    for arm in ARMS:
        print("F124AC_FIT_"+arm+"="+json.dumps(selected[arm],sort_keys=True),flush=True)
        for family in FAMILIES:
            r=data["DEV_scores"][arm][family]
            print("F124AC_DEV_"+arm+"_"+family+":"+
                  ("unqualified" if r is None else
                   "correct="+str(r["correct"])+"/48:FP="+str(r["false_positives"])+
                   ":FN="+str(r["false_negatives"])+":path_lost="+str(r["path_lost"])),
                  flush=True)
        print("F124AC_VERDICT_"+arm+"="+data["development_verdict"][arm],flush=True)

if __name__=="__main__":
    try:main()
    except (ValueError,KeyError,TypeError,OSError,ArithmeticError) as e:
        print("F124AC_QUARANTINE="+str(e),file=sys.stderr);sys.exit(1)
