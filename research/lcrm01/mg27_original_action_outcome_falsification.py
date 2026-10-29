#!/usr/bin/env python3
"""MG27 read-only original source action-outcome predictivity falsification.

Factual on-policy next public change only, original source-selected actions
unaltered. Context/action permuted histories are negative controls, not world
observations, and never produce any new environmental outcome.
"""
from __future__ import annotations
import argparse
import collections
from fractions import Fraction
import json
from pathlib import Path

from mg25_original_policy_activation_audit import (
    get_source,inspect as authenticate_mg25,FAMILIES,SEEDS,digest
)
from mg26_source_consequence_signal_audit import context

HERE=Path(__file__).resolve().parent
CONTRACT=HERE/"mg27_action_outcome_falsification_prereg.json"
ROLES=("wingless_MG23","yggdrasil_MG23","conventional_full")
SOURCE="e2dda4721d6d96ffd083faac5960013380b29c3325f560defa989c4eef0852a9"
SCHEMA="itd02.mg27.exposed-original-public-selected-action-outcome-falsification.v1"

def preflight():
    p=json.loads(CONTRACT.read_text(encoding="utf-8"))
    m=p["method"];c=p["cohort"];src=p["source"]
    if (p["schema"]!=SCHEMA or
        p["phase"]!="PRECOMMITTED_ANALYTIC_BEFORE_EXECUTABLE_RETROSPECTIVE_NO_SCIENCE_FIRST_USE" or
        src["MG26_head"]!="a807a916c30d698f091eab40a3071df4348b022f" or
        src["MG24_source_SHA256"]!=SOURCE or
        src["episodes"]!=72 or src["source_steps"]!=9186 or
        c["roles"]!=list(ROLES) or
        m["lookback_selected_steps"]!=32 or
        m["no_signal_predictor_probability"]!=0.5 or
        not all(p["boundaries"].values()) or
        not all(p["qualification"].values())):
        raise ValueError("MG27_PREREG_OR_SOURCE_LINEAGE_DRIFT")
    return p

def checked_event(event):
    before=event["before"];after=event["after"]
    if (set(before)!={"image","direction","mission"} or
        set(after)!=set(before) or
        before["mission"]!=after["mission"] or
        type(event["action"]) is not int or event["action"] not in range(7) or
        event["before_sha256"]!=digest(before) or
        event["after_sha256"]!=digest(after)):
        raise ValueError("MG27_UNAUTHENTICATED_ORIGINAL_ACTION_PUBLIC_PAIR")
    return (context(before),event["action"],
            int(event["before_sha256"]!=event["after_sha256"]))

def probability(history,key,selected,permuted=False,inverted=False):
    outcomes=[1-v if inverted else v for c,a,v in history
        if c==key and ((a+1)%7 if permuted else a)==selected]
    n=len(outcomes)
    return (Fraction(sum(outcomes)+1,n+2),n)

def squared(p,outcome):
    v=p-outcome
    return v*v

def empty_metrics():
    return {"steps":0,"source_changed":0,"original_supported":0,
            "permute_matched":0,"brier_original":Fraction(),
            "brier_no_signal":Fraction(),"brier_inverted":Fraction(),
            "brier_original_matched":Fraction(),
            "brier_permuted_matched":Fraction(),"original_goals":0,
            "novelty_positive_actual_source_selected":0}

def update_metric(m,history,e):
    key,action,changed=checked_event(e)
    # These original public data are immutable source receipts. The current
    # outcome is not visible to any predictor until AFTER the predictions.
    original,n=probability(history,key,action)
    negative,neg_n=probability(history,key,action,permuted=True)
    inverted,inv_n=probability(history,key,action,inverted=True)
    if inv_n!=n:raise ValueError("MG27_OUTCOME_CONTROL_SUPPORT_MISMATCH")
    m["steps"]+=1
    m["source_changed"]+=changed
    m["original_goals"]+=int(e["reward"]>0 and e["terminated"])
    if n:
        m["original_supported"]+=1
        m["brier_original"]+=squared(original,changed)
        m["brier_no_signal"]+=squared(Fraction(1,2),changed)
        m["brier_inverted"]+=squared(inverted,changed)
    if n and neg_n:
        m["permute_matched"]+=1
        m["brier_original_matched"]+=squared(original,changed)
        m["brier_permuted_matched"]+=squared(negative,changed)
    # No leakage: append real selected outcome only AFTER current scoring.
    history.append((key,action,changed))
    if len(history)>32:del history[0]
    return m

def merge(a,b):
    for name,value in b.items():
        a[name]+=value
    return a

def decimal(x):
    return format(float(x),".10f")

def summary(m):
    a=dict((key,value) for key,value in m.items() if type(value)is int)
    n=m["original_supported"];z=m["permute_matched"]
    def rate(key,denom):
        return decimal(m[key]/denom) if denom else None
    a.update({
        "brier_original_on_supported":rate("brier_original",n),
        "brier_no_signal_on_supported":rate("brier_no_signal",n),
        "brier_inverted_on_supported":rate("brier_inverted",n),
        "brier_original_matched":rate("brier_original_matched",z),
        "brier_permuted_matched":rate("brier_permuted_matched",z),
        "brier_improvement_vs_no_signal":decimal((m["brier_no_signal"]-m["brier_original"])/n) if n else None,
        "brier_improvement_vs_permuted_on_matched":decimal((m["brier_permuted_matched"]-m["brier_original_matched"])/z) if z else None
    })
    return a

def run(source):
    original=source["full_original_selected_source_72_episodes"]
    lookup={(row["family"],row["dev_seed_exposed"],row["role"]):row for row in original}
    if len(original)!=72 or len(lookup)!=72:raise ValueError("MG27_MISSING_ORIGINAL_ROLE_EPISODES")
    role_metrics={}
    family_metrics={}
    all_orig_steps=0
    for role in ROLES:
        total=empty_metrics()
        for family,seeds in zip(FAMILIES,SEEDS):
            history=[]
            metrics=empty_metrics()
            for seed in seeds:
                row=lookup[(family,seed,role)]
                events=row["selected_source_events"]
                if not 1<=len(events)<=128:raise ValueError("MG27_ORIGINAL_EPISODE_BOUND")
                for e in events:
                    update_metric(metrics,history,e)
            family_metrics[family+"|"+role]=summary(metrics)
            merge(total,metrics)
        role_metrics[role]=summary(total)
        all_orig_steps+=total["steps"]
    # Remaining original actors MUST be independently authenticated by MG25
    # even though MG27's hypothesis concerns the three eligible roles.
    if all_orig_steps<=0 or all_orig_steps>=9186:
        raise ValueError("MG27_ORIGINAL_SELECTED_SOURCE_ROLE_CUSTODY")
    pooled=empty_metrics()
    for role in ROLES[:2]:
        for family in FAMILIES:
            m=empty_metrics()
            hist=[]
            for seed in SEEDS[FAMILIES.index(family)]:
                for event in lookup[(family,seed,role)]["selected_source_events"]:
                    update_metric(m,hist,event)
            merge(pooled,m)
    m=summary(pooled)
    decision=(pooled["permute_matched"]>=100 and pooled["original_supported"]>0 and
        (pooled["brier_no_signal"]-pooled["brier_original"])/pooled["original_supported"]>=Fraction(2,100) and
        (pooled["brier_permuted_matched"]-pooled["brier_original_matched"])/pooled["permute_matched"]>=Fraction(2,100))
    return {"schema":"itd02.mg27.original-public-action-outcome-source-falsification-receipt.v1",
        "classification":"RETROSPECTIVE_EXPOSED_DEV_OFFLINE_NOT_CAUSAL_OR_GOAL_SCIENCE",
        "original_source_SHA256":SOURCE,"original_source_total_steps_authenticated":9186,
        "source_original_episodes_authenticated":72,
        "source_actual_steps_examined_for_three_actors":all_orig_steps,
        "per_role":role_metrics,"per_family_actor":family_metrics,
        "pooled_two_native_same_support":m,
        "predeclared_signal_pass_for_native_opt_in_followup":decision,
        "meaning":"association between selected action and ensuing public change, not benefit of taking proposed action",
        "offpolicy_actions_executed":0,"new_original_world_source_steps":0,
        "new_source_seed_claims":0,"native_models_changed":False,
        "scientific_first_use":False}

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--first",type=Path)
    a.add_argument("--second",type=Path)
    a.add_argument("--output",type=Path)
    a.add_argument("--compare",nargs=2,type=Path)
    args=a.parse_args()
    if args.compare:
        x,y=(json.loads(q.read_text(encoding="utf-8")) for q in args.compare)
        if (x!=y or x["original_source_SHA256"]!=SOURCE or
            x["original_source_total_steps_authenticated"]!=9186 or
            x["new_original_world_source_steps"]!=0):
            raise ValueError("MG27_WINDOWS_LINUX_FALSIFICATION_EVIDENCE_MISMATCH")
        print("MG27_INDEPENDENT_SOURCE_ACTUAL_OUTCOME_CROSS_OS_PASS "+digest(x))
        return
    if not all((args.first,args.second,args.output)):
        a.error("original MG24 two authentic process receipts and output required")
    preflight()
    x=get_source(args.first);y=get_source(args.second)
    if x["source"]!=y["source"]:raise ValueError("MG27_ORIGINAL_SOURCE_PROCESSES_DIFFER")
    authenticate_mg25(x)
    receipt=run(x["source"])
    receipt["sha256"]=digest(receipt)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("MG27_ORIGINAL_ACTION_OUTCOME_FALSIFICATION_PASS_NOT_SCIENCE "+receipt["sha256"])
    print("MG27_NATIVE_SOURCE_INFORMATION_FALSIFICATION "+json.dumps({
        "native_pooled":receipt["pooled_two_native_same_support"],
        "decision":receipt["predeclared_signal_pass_for_native_opt_in_followup"]
    },sort_keys=True,separators=(",",":")))
if __name__=="__main__":main()
