"""F9 autonomous F8->learned order, strict train-only rule selection.

Only already-examined F3 seeds 67204/67205 enter training; previously
consumed 67206/67207 enter the independently replayed validation split.
Training labels are the actual pinned Y070 outcomes of each matched
physical-sensor timing. Never use prospective or sealed cohorts.
"""
import argparse,hashlib,json
from pathlib import Path
from policy import (TRAIN_SEEDS,VALIDATION_SEEDS,PAIRS,RULES,choose_branch,
                    NEXT_ID,public_start)
from worker import load_source,evaluate,SOURCE_COMMIT

F8_SCHEMA="forge.f8.automatic-f7-matched-timing-engineering.v1"
F8_REVIEW="forge.f8.independent-matched-sensor-timing-review.v1"
RULE_EARLY="ALWAYS_EARLY"
RULE_SWAP="ALWAYS_SWAP"

def require(ok,why):
    if not ok:raise ValueError("F9_AUTONOMY_"+why)

def canon(v):
    return (json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()

def preflight(parent,review):
    require(parent.get("schema")==F8_SCHEMA and
            parent.get("status")=="PREVIOUSLY_USED_F3_ONLY_NOT_FROZEN_SCIENCE"
            and parent.get("source_commit")==SOURCE_COMMIT
            and parent.get("selected_proposal")==
                "Y-FORGE-F8-MATCHED-SENSOR-TIMING-CONTROL-PROPOSAL"
            and parent.get("matched_physical_sensor_sets") is True
            and parent.get("used_development_seeds")==list(VALIDATION_SEEDS)
            and parent.get("used_pairs")==[list(x) for x in PAIRS]
            and parent.get("public_scalar_reads")==10
            and parent.get("winner_selected") is False
            and parent.get("scientific_dispatch_authorized") is False
            and all(parent.get(k)==0 for k in (
                "new_development_or_sealed_uses","new_originals",
                "new_first_use_claims","paid_api_calls")),"F8_PARENT")
    require(review.get("schema")==F8_REVIEW and
            review.get("status")=="USED_F3_REAL_SOURCE_REPLAY_ONLY_NO_SCIENCE"
            and review.get("replayed_trial_arms")==192
            and review.get("matched_set_comparisons")==96
            and review.get("totals")==parent.get("groups")
            and review.get("new_originals")==0
            and review.get("first_use_claims")==0
            and review.get("scientific_dispatch_authorized") is False,"INDEPENDENT_F8")
    groups=parent["groups"]
    a,b=groups["F8-F7-EARLY-CONTROL"],groups["F8-SAME-SET-3-5-SWAP"]
    require(a["cases"]==b["cases"]==96 and
            a["pre"]+a["post"]==74 and b["pre"]+b["post"]==66 and
            a["steady_errors"]==b["steady_errors"]==0,"MATCHED_F8_FINDING")
    require(type(parent.get("records")) is list and len(parent["records"])==192,
            "PARENT_RECORDS")
    return "F8_PUBLIC_TIME_ORDER_MATTERS_MATCHED_SENSOR_SET"

def cases(source,seeds,rules):
    rows=[]
    for pair in PAIRS:
        for regime in ("steady","onset1"):
            for family in source.FAMILIES:
                for seed in seeds:
                    for source_policy in source.POLICIES:
                        for rule in rules:
                            rows.append(evaluate(source,seed,pair,regime,
                                                 family,source_policy,rule))
    return rows

def index_controls(rows):
    result={}
    for row in rows:
        key=(row["seed"],tuple(row["pair"]),row["regime"],
             tuple(row["family"]),row["matching_policy"])
        result.setdefault(key,{})
        require(row["rule"] not in result[key],"DUPLICATE_LABEL")
        result[key][row["rule"]]=row
    return result

def fit(rows):
    # Both counterfactual outcomes known only because both physical source
    # experiments were run on already-used training seeds.
    pairings=index_controls(rows)
    require(len(pairings)==96 and all(set(x)=={RULE_EARLY,RULE_SWAP}
             for x in pairings.values()),"TRAIN_LABEL_COMPLETENESS")
    examples=[]
    for key,arms in sorted(pairings.items()):
        require(key[0] in TRAIN_SEEDS,"VAL_LEAK")
        early,swap=arms[RULE_EARLY],arms[RULE_SWAP]
        e=early["sample_trace"]["decision"]
        w=swap["sample_trace"]["decision"]
        require(e["public_start"]==w["public_start"] and
                e["physical_nonanchor_set"]==w["physical_nonanchor_set"]
                and e["decision"]=="EARLY" and w["decision"]=="SWAP",
                "MATCHED_TRAINING_SOURCE")
        examples.append((e["public_start"],
            early["pre_mismatch"]+early["post_mismatch"],
            swap["pre_mismatch"]+swap["post_mismatch"]))
    ranking=[]
    for rule in RULES:
        total=0;early_count=0
        for start,early_loss,swap_loss in examples:
            # Construct only the public anchor readings needed by the
            # decision formula, with a=1 d=0 and start derived as source
            # start, but note s=(b0+3)%16%14: start=0..13 can be reached
            # by b0=(s-3)%16 only for s>=3; avoid surrogate values by
            # classify the integer public_start itself here.
            decision=classify_start(rule,start)
            total+=early_loss if decision else swap_loss
            early_count+=int(decision)
        ranking.append({"rule":rule,"training_mismatch_total":total,
                        "training_early_cases":early_count})
    best=min(ranking,key=lambda v:(v["training_mismatch_total"],
                                  RULES.index(v["rule"])))
    require(len(examples)==96,"TRAIN_CASES")
    return {"schema":"forge.f9.frozen-public-order-rule.v1",
        "status":"TRAINED_F3_USED_SPLIT_ONLY_NO_PROSPECTIVE_AUTHORITY",
        "hypothesis_id":NEXT_ID,"source_commit":SOURCE_COMMIT,
        "training_seeds":list(TRAIN_SEEDS),
        "unseen_in_fit_validation_seeds":list(VALIDATION_SEEDS),
        "training_case_pairs":96,"rule_bank":list(RULES),
        "scores":ranking,"selected_rule":best["rule"],
        "selected_training_loss":best["training_mismatch_total"],
        "budget_public_reads":10,"max_retained":9,
        "new_cohort_uses":0,"new_first_use_claims":0,
        "scientific_originals":0,"scientific_dispatch_authorized":False}

def classify_start(rule,s):
    require(rule in RULES and type(s) is int and 0<=s<14,"FEATURE")
    return {"ALWAYS_EARLY":True,"ALWAYS_SWAP":False,
            "START_EVEN_EARLY":s%2==0,"START_ODD_EARLY":s%2==1,
            "START_LT7_EARLY":s<7,"START_GE7_EARLY":s>=7,
            "START_MOD3_ZERO_EARLY":s%3==0,
            "START_MOD3_NONZERO_EARLY":s%3!=0}[rule]

def execute(parent_raw,review_raw,root):
    source=load_source(root)
    trigger=preflight(json.loads(parent_raw),json.loads(review_raw))
    training=cases(source,TRAIN_SEEDS,(RULE_EARLY,RULE_SWAP))
    model=fit(training)
    validation_rules=tuple(dict.fromkeys((
        RULE_EARLY,RULE_SWAP,model["selected_rule"])))
    validation=cases(source,VALIDATION_SEEDS,validation_rules)
    # Constant-rule selection means no third distinct arm. In that case
    # the learned policy is genuinely nonadaptive; never claim otherwise.
    return {"schema":"forge.f9.automatic-public-order-training.v1",
        "status":"F3_PREVIOUSLY_USED_ENGINEERING_ONLY",
        "parent_f8_sha256":hashlib.sha256(parent_raw).hexdigest(),
        "parent_f8_witness_sha256":hashlib.sha256(review_raw).hexdigest(),
        "parent_trigger":trigger,"model":model,
        "training":training,"validation":validation,
        "training_case_arms":len(training),
        "validation_case_arms":len(validation),
        "validation_rules":list(validation_rules),
        "source_commit":SOURCE_COMMIT,
        "new_cohort_uses":0,"first_use_claims":0,
        "scientific_originals":0,"paid_api_calls":0,
        "winner_selected":False,"scientific_dispatch_authorized":False}

def main():
    p=argparse.ArgumentParser()
    for field in ("parent","witness","source-root","out"):
        p.add_argument("--"+field,required=True)
    a=p.parse_args()
    raw=canon(execute(Path(a.parent).read_bytes(),
                      Path(a.witness).read_bytes(),a.source_root))
    with Path(a.out).open("xb") as out:out.write(raw)
    print("F9_AUTOMATIC_F8_TO_TRAIN_ONLY_PUBLIC_ORDER=PASS")
    print("F9_ENGINEERING_RECORD_SHA256="+hashlib.sha256(raw).hexdigest())
    data=json.loads(raw)
    print("F9_SELECTED_TRAINING_RULE="+data["model"]["selected_rule"])
    print("F9_TRAINING_ARMS="+str(data["training_case_arms"]))
    print("F9_VALIDATION_ARMS="+str(data["validation_case_arms"]))
    print("F9_NEW_FIRST_USE=ZERO")
if __name__=="__main__":main()
