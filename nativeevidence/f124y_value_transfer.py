"""F124-Y Y: FIT-only logit-threshold intervention versus FIT-frozen
structural removal of S's accumulated value credit; DEV never tunes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

import f124y_source as source
import f124o_native_learners as O
import f124r_causal_learners as R
import f124s_native_mechanisms as S
import f124t_variants as T
import f124v_yggdrasil_causal_trace as V
import f124n_development_evidence as adapter
import f124h_train_receipt as ctrl

SCHEMA="forge.research.f124y.fit-only-score-vs-threshold-intervention.v1"
THRESHOLDS=(-8,-6,-4,-3,-2,-1,0,1,2,3,4,6,8)
ARMS=("O_original","R_readout","S_original","U_rank",
      "S_no_value_credit","S_fit_threshold_only","S_no_value_fit_threshold",
      "fixed_12of16")


def need(ok,code):source.need(ok,"Y_INTERVENTION_"+code)


def source_pairs(phase):
    return [source.build("Yggdrasil",seed,v,phase)
            for v in source.VECTORS
            for seed in source.COHORTS["Yggdrasil"][phase]]


def evaluate_source(phase,w,thresholds,fixed):
    records={name:{"paired":0,"pairs":0,"false_positives":0,
                   "false_negatives":0,"by_depth":{str(d):{"pairs":0,"paired":0}
                      for d in (7,8,9)},
                   "cases":[]} for name in ARMS}
    for pairix,(pos,neg) in enumerate(source_pairs(phase)):
        depth=len(pos["roles"])
        if not source.paired_admit(pos,neg):raise ValueError("BAD_PUBLIC_PAIR")
        score={}
        for k,g in enumerate((pos,neg)):
            base=list(w["base"])
            a=O.yggdrasil_forward(g,base)[0]
            b=R.yggdrasil_continuous(g,base,list(w["R"]))[0]
            c=S.yggdrasil_cell_credit(g,base,list(w["S"]))[0]
            d=V.U.ygg_rank(g,base,list(w["U"]))[0]
            z=T.yggdrasil_credit_ablation(g,base,list(w["S"]),
                     value_credit=False,rank_credit=True)[0]
            fixedpred,_=fixed(g)
            for arm,logit in (("O_original",a),("R_readout",b),
                              ("S_original",c),("U_rank",d),
                              ("S_no_value_credit",z),
                              ("S_fit_threshold_only",c),
                              ("S_no_value_fit_threshold",z)):
                thr=(thresholds["S"] if arm=="S_fit_threshold_only" else
                     thresholds["no_value"] if arm=="S_no_value_fit_threshold" else 0.)
                score[(arm,k)]=logit>=thr
            score[("fixed_12of16",k)]=bool(fixedpred)
        for arm in ARMS:
            a,b=score[(arm,0)],score[(arm,1)]
            row=records[arm]
            row["pairs"]+=1;row["paired"]+=int(a and not b)
            row["false_positives"]+=int(b)
            row["false_negatives"]+=int(not a)
            row["by_depth"][str(depth)]["pairs"]+=1
            row["by_depth"][str(depth)]["paired"]+=int(a and not b)
            row["cases"].append(hashlib.sha256(json.dumps({
                "phase":phase,"pair":pairix,"arm":arm,"pos":a,"neg":b,
                "depth":depth},sort_keys=True).encode()).hexdigest())
    for x in records.values():
        need(x["pairs"]==48 and all(z["pairs"]==16 for z in x["by_depth"].values()),
             "COMPLETE_DENOMINATORS")
    return records


def fit_thresholds(w):
    """Only frozen FIT examples can rank predeclared thresholds."""
    pairs=source_pairs("FIT")
    need(len(pairs)==48,"FIT_DENOMINATOR")
    values={"S":[],"no_value":[]}
    for p,n in pairs:
        base=list(w["base"])
        for g in (p,n):
            values["S"].append(
                S.yggdrasil_cell_credit(g,base,list(w["S"]))[0])
            values["no_value"].append(
                T.yggdrasil_credit_ablation(g,base,list(w["S"]),
                    value_credit=False,rank_credit=True)[0])
    elected={};curves={}
    for family,logits in values.items():
        counts={}
        for threshold in THRESHOLDS:
            paired=sum(logits[i]>=threshold and logits[i+1]<threshold
                       for i in range(0,96,2))
            counts[str(threshold)]=paired
        winner=max(THRESHOLDS,key=lambda t:(counts[str(t)],-abs(t),-t))
        elected[family]=winner
        curves[family]=counts
    return elected,curves


def main():
    p=argparse.ArgumentParser()
    for name in ("o","r","s","u"):p.add_argument("--original-"+name,required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    source.frozen()
    w=V.original_weights(a.original_o,a.original_r,a.original_s,a.original_u)
    thresholds={"S":0,"no_value":0}
    curves={"S":{"fixed_zero":True},"no_value":{"fixed_zero":True}}
    fixed=adapter.clone_single_validator(ctrl.fixed_comparator,"graph")
    report={"schema":SCHEMA,"freeze_blob":source.PROTOCOL_BLOB,
            "separate_nonprotected_development_source":True,
            "training_or_new_learned_parameters":0,
            "all_original_weight_states_unchanged":True,
            "FIT_threshold_curve":curves,"FIT_selected_thresholds":thresholds,
            "DEV_never_used_to_select_threshold":True,
            "no_new_FIT_or_DEV_selection":True,
            "FIT":evaluate_source("FIT",w,thresholds,fixed),
            "DEV":evaluate_source("DEV",w,thresholds,fixed),
            "protected_first_use":False,"scientific_acceptances":0,
            "optimizer_promotions":0,"accepted_refs":0}
    out=Path(a.output)
    need(out.parent.is_dir() and not out.exists(),"IMMUTABLE_OUTPUT")
    raw=(json.dumps(report,sort_keys=True,indent=2)+"\n").encode()
    with out.open("xb") as f:f.write(raw)
    print("F124YV_SHA256="+hashlib.sha256(raw).hexdigest(),flush=True)
    print("F124YV_FIXED_THRESHOLDS="+json.dumps(thresholds,sort_keys=True),flush=True)
    for name,v in report["DEV"].items():
        print("F124YV_DEV_"+name+":paired="+str(v["paired"])+
              "/48:FP="+str(v["false_positives"])+
              ":FN="+str(v["false_negatives"]),flush=True)


if __name__=="__main__":
    try:main()
    except (ValueError,OSError,KeyError,TypeError,ArithmeticError) as err:
        print("F124YV_QUARANTINE="+str(err),file=sys.stderr)
        sys.exit(1)
