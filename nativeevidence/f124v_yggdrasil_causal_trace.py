"""F124-VY exact-logit, evaluator-only forensic tracing of cognitive cell loss.

Models only read public graph keys, original pretrained parameter values and
their fixed 7-active/9-retained capacities. The evaluator derives a unique
PUBLIC exact causal positive path AFTER scores are computed and observes where
its (node, raw carried key) prefix appears or disappears across hops.
No model update, capacity change or protected source inspection.
"""
from __future__ import annotations
from collections import Counter
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import f124v_fresh_source as source
import f124o_native_learners as O
import f124r_causal_learners as R
import f124s_native_mechanisms as S
import f124u_microindex_causal_rank as U
import f124n_development_evidence as adapter
import f124h_train_receipt as control_mod

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f124v-yggdrasil-causal-survival-freeze.json"
BLOB="763dadc723a89aa356f4bb992765ffd17c52c127"
O_SHA="025c97abc8eb69079d7d7d0f59bfdb81235b9ad9ab83e230f32b542d2cfbdb5d"
R_SHA="8ac2d22d10c91e453e33ca7d6deba44a75d92849b106d6f49cc9f19b123f2525"
S_SHA="fb28a06ca4e0bfde9b4053734d61f2e3d1e760a8a3dda29e834780abe2339f25"
U_SHA="5634fa8b1acb02abf0640a558d268dccb751ace43093efd518f265ed44a56a49"
ARMS=("O","R","S","U")


def need(ok,msg):
    source.need(ok,"Y_TRACE_"+msg)


def sha(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,
        separators=(",",":")).encode()).hexdigest()


def contract():
    raw=FREEZE.read_bytes().replace(b"\r\n",b"\n")
    need(source.git_blob(raw)==BLOB,"FROZEN_YGG_PROTOCOL")
    p=json.loads(raw)
    need(p["schema"]=="forge.research.f124v.yggdrasil-causal-survival.freeze.v1"
         and p["stage"]=="PREIMPLEMENTATION_FROZEN"
         and p["qualified_parent"]["head"]==
             "7d8df58e3fd7363e5c91b39a426ff3430fedf20d"
         and p["experiment"]["arms"]==
             ["original_O","R_continuous_readout",
              "S_cell_value_and_rank_credit","U_fresh_learned_rank"]
         and p["experiment"]["oracle_use"].startswith("Post-inference")
         and all(x is False for x in p["authority"].values()),
         "CONTRACT_DRIFT")
    source.frozen()
    return p


def authenticate(path,digest):
    raw=Path(path).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==digest,"PRIOR_RECEIPT_SHA")
    return json.loads(raw)


def original_weights(o_path,r_path,s_path,u_path):
    o=authenticate(o_path,O_SHA)
    r=authenticate(r_path,R_SHA)
    s=authenticate(s_path,S_SHA)
    u=authenticate(u_path,U_SHA)
    def selected(p,lane="Yggdrasil"):
        rows=[x for x in p["lanes"] if x["lane"]==lane]
        need(len(rows)==1,"DUPLICATE_OR_MISSING_ORIGINAL_LANE")
        return rows[0]
    a,b,c=selected(o),selected(r),selected(s)
    base=a["training"]["trained_weights"]
    rd=b["training"]["delta"]
    sd=c["training"]["delta"]
    ud=u["Yggdrasil_training"]["learned_delta"]
    need(O.sha(base)==a["training"]["trained_weight_sha256"]
         and R.digest(rd)==b["training"]["delta_sha256"]
         and S.digest(sd)==c["training"]["delta_sha256"]
         and U.sha(ud)==u["Yggdrasil_training"]["delta_sha256"]
         and u["Yggdrasil_training"]["dev_access_during_training"]==0
         and len(base)==7 and len(rd)==len(sd)==len(ud)==2,
         "FROZEN_ORIGINAL_TRAINED_WEIGHTS")
    return {"base":list(base),"R":list(rd),"S":list(sd),"U":list(ud)}


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


def original_forward(arm,g,weights):
    base=list(weights["base"])
    if arm=="O":return O.yggdrasil_forward(g,base)
    if arm=="R":return R.yggdrasil_continuous(g,base,list(weights["R"]))
    if arm=="S":return S.yggdrasil_cell_credit(g,base,list(weights["S"]))
    if arm=="U":return U.ygg_rank(g,base,list(weights["U"]))
    raise ValueError("INVALID_DIAGNOSTIC_ARM")


def trace_model(arm,g,weights,positive_prefix=None):
    """Instrument model allocation. Prefix remains evaluator-only diagnostic."""
    source.validate_public(g)
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
        active=[row[2] for row in candidates[:7]]
        selected={id(row) for row in candidates[:7]}
        extras=[row for row in candidates if id(row) not in selected]
        extras.sort(key=lambda x:(-x[1],-x[0],x[2][0],x[2][1]))
        retained=[row[2] for row in extras[:9]]
        need(len(active)<=7 and len(retained)<=9 and
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
        logit+=2.*weights["R"][0]*mean+2.*weights["R"][1]*target
    ref,_=original_forward(arm,g,weights)
    need(logit.hex()==ref.hex(),"FORENSIC_REPLAY_MUST_BE_BIT_IDENTICAL_"+arm)
    return {"prediction":bool(O.sigmoid(logit)>=.5),
            "logit_hex":logit.hex(),"hops":hops,
            "total_evictions":sum(h["evictions"] for h in hops),
            "final_active":len(active),"final_retained":len(retained)}


def evaluate(weights,phase):
    res={}
    for arm in ARMS:
        cells=[]
        paired=neg_fp=0
        first_loss=Counter()
        ever_loss=0
        for v in source.VECTORS:
            for seed in source.COHORTS["Yggdrasil"][phase]:
                p,n=source.build("Yggdrasil",seed,v,phase)
                # Confirm public admissibility then separately compute model
                # scores BEFORE using evaluator-only true-path data.
                old_pos,_=original_forward(arm,p,weights)
                old_neg,_=original_forward(arm,n,weights)
                pos_trace=trace_model(arm,p,weights,positive_prefix=None)
                neg_trace=trace_model(arm,n,weights,positive_prefix=None)
                need(old_pos.hex()==pos_trace["logit_hex"]
                     and old_neg.hex()==neg_trace["logit_hex"],
                     "UNMODIFIED_PREDICTION_REPLAY")
                route=exact_positive_prefix(p)
                traced=trace_model(arm,p,weights,positive_prefix=route)
                need(traced["logit_hex"]==pos_trace["logit_hex"],
                     "FORENSIC_TRACING_CHANGED_LOGIT")
                stages=[x["stage"] for x in traced["hops"]]
                first=next((x for x in traced["hops"]
                     if x["stage"] in ("pruned","not_generated")),None)
                label=str(first["hop"]) if first else "survived"
                first_loss[label]+=1
                ever_loss+=int(first is not None)
                paired+=int(pos_trace["prediction"] and not neg_trace["prediction"])
                neg_fp+=int(neg_trace["prediction"])
                cells.append({"source_seed":seed,"vector":list(v),
                  "depth":len(p["roles"]), "prediction_pos":pos_trace["prediction"],
                  "prediction_neg":neg_trace["prediction"],
                  "correct_pair":bool(pos_trace["prediction"] and
                                      not neg_trace["prediction"]),
                  "first_loss_hop":(first["hop"] if first else None),
                  "first_loss_cause":(first["stage"] if first else None),
                  "hops":traced["hops"],
                  "negative_total_evictions":neg_trace["total_evictions"],
                  "positive_total_evictions":traced["total_evictions"]})
        need(len(cells)==48,"EXACT_48_POSITIVE_PAIRS_PER_ARM")
        depth_stats={}
        for d in (7,8,9):
            rows=[x for x in cells if x["depth"]==d]
            need(len(rows)==16,"HOP_DEPTH_DENOMINATOR")
            depth_stats[str(d)]={
              "pairs":16,"paired_correct":sum(x["correct_pair"] for x in rows),
              "first_loss_count":sum(x["first_loss_hop"] is not None for x in rows),
              "survive_to_end":sum(x["hops"][-1]["stage"] in
                                  ("active","retained") for x in rows)}
        hop_stats={}
        for hop in range(1,10):
            all_hops=[x["hops"][hop-1] for x in cells if len(x["hops"])>=hop]
            if not all_hops:continue
            hop_stats[str(hop)]={"population":len(all_hops),
              "generated":sum(x["candidate_generated"] for x in all_hops),
              "active":sum(x["in_active"] for x in all_hops),
              "retained":sum(x["in_retained"] for x in all_hops),
              "pruned":sum(x["stage"]=="pruned" for x in all_hops),
              "not_generated":sum(x["stage"]=="not_generated" for x in all_hops),
              "reactivated_from_retained":sum(
                  x["from_retained_to_active"] for x in all_hops)}
        res[arm]={"pairs":48,"paired_correct":paired,
                  "negative_false_positives":neg_fp,
                  "first_loss_hop_counts":dict(first_loss),
                  "ever_lost_count":ever_loss,
                  "per_depth":depth_stats,"per_hop":hop_stats,
                  "complete_trace_case_sha256":sha(cells),
                  "cases":cells}
    return res


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--original-o",required=True)
    parser.add_argument("--original-r",required=True)
    parser.add_argument("--original-s",required=True)
    parser.add_argument("--original-u",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    contract()
    w=original_weights(args.original_o,args.original_r,args.original_s,
                       args.original_u)
    dest=Path(args.output)
    need(not dest.exists() and dest.parent.is_dir(),"EXCLUSIVE_OUTPUT")
    report={"schema":"forge.research.f124v.yggdrasil-causal-survival-observation.v1",
       "preimplementation_blob":BLOB,
       "model_weights_fit_only_unchanged":True,
       "new_training_steps":0,
       "fit":evaluate(w,"FIT"),
       "dev":evaluate(w,"DEV"),
       "protected_original_first_use":False,
       "independent_scientific_confirmation":False,
       "scientific_acceptances":0,
       "optimizer_promotions":0,
       "accepted_ref_mutations":0,
       "no_model_trace_oracle_leak":True}
    text=json.dumps(report,sort_keys=True,indent=2)+"\n"
    dest.write_text(text)
    print("F124V_YGG_SHA256="+hashlib.sha256(text.encode()).hexdigest())
    for name,x in report["dev"].items():
        print("F124V_YGG_DEV_"+name+":correct="+
              str(x["paired_correct"])+"/48:ever_lost="+
              str(x["ever_lost_count"])+"/48:first_loss="+
              json.dumps(x["first_loss_hop_counts"],sort_keys=True))


if __name__=="__main__":
    try:main()
    except (OSError,ValueError,KeyError,TypeError,ArithmeticError) as exc:
        print("F124V_YGG_QUARANTINED="+str(exc),file=sys.stderr)
        sys.exit(1)
