#!/usr/bin/env python3
"""MG28 historical source-only falsification of MG27 action-conditioned signal.

Prequential actual selected actions only. Brier compared to equally informed
context-only, action-only, global-only and last-context empirical controls.
"""
from __future__ import annotations
import argparse,collections,json
from fractions import Fraction
from pathlib import Path
from mg25_original_policy_activation_audit import get_source,inspect as authenticate_mg25,FAMILIES,SEEDS,digest
from mg27_original_action_outcome_falsification import checked_event

HERE=Path(__file__).resolve().parent
FROZEN=HERE/"mg28_matched_signal_falsification_prereg.json"
SOURCE="e2dda4721d6d96ffd083faac5960013380b29c3325f560defa989c4eef0852a9"
SCHEMA="itd02.mg28.matched-context-action-only-original-source-predictivity.v1"
ROLES=("wingless_MG23","yggdrasil_MG23","conventional_full")
METHODS=("full","context_only","action_only","global_only","last_context","permuted")
WINDOW=32

def preflight():
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    b=p["parent"];m=p["method"];a=p["acceptance"]
    if (p["schema"]!=SCHEMA or
        p["phase"]!="PRECOMMITTED_RETROSPECTIVE_FALSIFICATION_BEFORE_EXECUTABLE_NOT_SCIENCE_FIRST_USE" or
        b["MG27"]!="4134f8fb268d78fdd527a1c67f1974ae77977252" or
        b["MG24_sha"]!=SOURCE or b["source_actions"]!=9186 or
        b["source_episodes"]!=72 or
        m["actors"]!=list(ROLES) or m["worlds"]!=list(FAMILIES) or
        m["window"]!=WINDOW or
        a["pooled_natives_full_supported_at_least"]!=100 or
        a["full_brier_improvement_over_context_only_at_least"]!="0.0200000000" or
        a["full_brier_improvement_over_action_only_at_least"]!="0.0200000000" or
        not all(p["boundaries"].values())):
        raise ValueError("MG28_PREDECLARED_MATCHED_STRONG_CONTROLS_CHANGED")
    return p

def predictors(history,key,action):
    # All candidate predictions are computed from immutable *earlier*
    # real selected public source actions and returned outcomes only.
    pool={
      "full":[o for c,a,o in history if c==key and a==action],
      "context_only":[o for c,a,o in history if c==key],
      "action_only":[o for c,a,o in history if a==action],
      "global_only":[o for c,a,o in history],
      "permuted":[o for c,a,o in history if c==key and (a+1)%7==action],
      "last_context":[o for c,a,o in history if c==key],
    }
    values={}
    for name,observations in pool.items():
        n=len(observations)
        if name=="last_context":
            pred=Fraction(observations[-1]) if n else Fraction(1,2)
        else:
            pred=Fraction(sum(observations)+1,n+2)
        values[name]=(pred,n)
    return values

def new_counter():
    return {"steps":0,"supported":0,"changed":0,
            "context_supported":0,"action_supported":0,
            "permuted_supported":0,"squared":{name:Fraction(0) for name in METHODS},
            "all_squared":{name:Fraction(0) for name in METHODS}}

def observe(counter,history,event):
    # checked_event validates original before/action/after SHAs.
    key,action,actual=checked_event(event)
    prior=predictors(history,key,action)
    counter["steps"]+=1
    counter["changed"]+=actual
    if prior["full"][1]:
        counter["supported"]+=1
        counter["context_supported"]+=int(prior["context_only"][1]>0)
        counter["action_supported"]+=int(prior["action_only"][1]>0)
        counter["permuted_supported"]+=int(prior["permuted"][1]>0)
        for name in METHODS:
            counter["squared"][name]+=(prior[name][0]-actual)**2
    for name in METHODS:
        counter["all_squared"][name]+=(prior[name][0]-actual)**2
    history.append((key,action,actual))
    if len(history)>WINDOW:del history[0]
    return counter

def join(a,b):
    for key in ("steps","supported","changed","context_supported","action_supported","permuted_supported"):
        a[key]+=b[key]
    for key in ("squared","all_squared"):
        for name in METHODS:a[key][name]+=b[key][name]
    return a

def decimal(value):
    return format(float(value),".10f")

def summary(counter):
    n=counter["supported"];s=counter["steps"]
    result={k:counter[k] for k in ("steps","supported","changed","context_supported",
                                  "action_supported","permuted_supported")}
    result["original_supported_brier"]={
        method:decimal(counter["squared"][method]/n) if n else None for method in METHODS
    }
    result["all_original_actions_brier"]={
        method:decimal(counter["all_squared"][method]/s) if s else None for method in METHODS
    }
    result["full_improvement_over_context_only"]=(
        decimal((counter["squared"]["context_only"]-counter["squared"]["full"])/n) if n else None)
    result["full_improvement_over_action_only"]=(
        decimal((counter["squared"]["action_only"]-counter["squared"]["full"])/n) if n else None)
    result["full_improvement_over_global"]=(
        decimal((counter["squared"]["global_only"]-counter["squared"]["full"])/n) if n else None)
    result["full_improvement_over_last_context"]=(
        decimal((counter["squared"]["last_context"]-counter["squared"]["full"])/n) if n else None)
    return result

def analyze(source):
    episodes=source["full_original_selected_source_72_episodes"]
    lookup={(r["family"],r["dev_seed_exposed"],r["role"]):r for r in episodes}
    if len(episodes)!=72 or len(lookup)!=72:
        raise ValueError("MG28_SOURCE_MISSING_72_ACTUAL_EPISODES")
    per_role={};per_family_role={}
    pooled=new_counter()
    for role in ROLES:
        role_counter=new_counter()
        for family,seeds in zip(FAMILIES,SEEDS):
            family_counter=new_counter()
            history=[]
            for seed in seeds:
                row=lookup[(family,seed,role)]
                events=row["selected_source_events"]
                if not 1<=len(events)<=128:
                    raise ValueError("MG28_ORIGINAL_SELECTED_ACTION_LIMIT")
                for e in events:observe(family_counter,history,e)
            per_family_role[family+"|"+role]=summary(family_counter)
            join(role_counter,family_counter)
            if role in ROLES[:2]:join(pooled,family_counter)
        per_role[role]=summary(role_counter)
    s=pooled["supported"]
    decision=(s>=100 and
      (pooled["squared"]["context_only"]-pooled["squared"]["full"])/s>=Fraction(2,100) and
      (pooled["squared"]["action_only"]-pooled["squared"]["full"])/s>=Fraction(2,100))
    result={
      "schema":"itd02.mg28.matched-strong-on-policy-action-context-control-receipt.v1",
      "classification":("MG28_ACTION_CONTEXT_SIGNAL_PASSES_BOTH_STRONG_CONTROLS__NO_SCIENCE"
                        if decision else "MG28_ACTION_CONTEXT_SIGNAL_NOT_INCREMENTAL_TO_BOTH_STRONG_CONTROLS__NO_SCIENCE"),
      "new_native_model_code":False,
      "new_original_env_steps":0,
      "original_public_source_sha256":SOURCE,
      "original_episodes_authenticated":72,
      "original_selected_actions_authenticated":9186,
      "first_use_science":False,
      "source_dev_cohort_already_exposed":True,
      "native_opt_in_warranted_by_precommitted_rule":decision,
      "native_pooled":summary(pooled),
      "per_role":per_role,
      "per_family_role":per_family_role,
      "meaning":"On-policy next-observation-change prediction vs equally earlier-informed context-only/action-only; never off-policy efficacy or causal understanding"
    }
    result["sha256"]=digest(result)
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--first",type=Path)
    parser.add_argument("--second",type=Path)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--compare",nargs=2,type=Path)
    args=parser.parse_args()
    if args.compare:
        a,b=(json.loads(p.read_text(encoding="utf-8")) for p in args.compare)
        if a!=b or a.get("original_selected_actions_authenticated")!=9186 or a.get("new_original_env_steps")!=0:
            raise ValueError("MG28_CROSS_HOST_ORIGINAL_EVIDENCE_DIFFER")
        print("MG28_MATCHED_CONTEXT_ACTION_SOURCE_CROSS_OS_PASS",a["sha256"])
        return
    if not (args.first and args.second and args.output):
        parser.error("read-only original two-process evidence and output required")
    preflight()
    a=get_source(args.first);b=get_source(args.second)
    if a["source"]!=b["source"]:
        raise ValueError("MG28_ORIGINAL_TWO_PROCESS_REPLAY_DIFFER")
    authenticate_mg25(a)
    result=analyze(a["source"])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("MG28_STRONG_CONTEXT_ONLY_ACTION_ONLY_SOURCE_FALSIFICATION",result["classification"],result["sha256"])
    print("MG28_POOLED_NATIVE_STRONG_CONTROLS",json.dumps(result["native_pooled"],sort_keys=True))
if __name__=="__main__":main()
