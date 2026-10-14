"""F14 historical successor: learn compositional public-token task values.

No fresh cohorts, originals, new first-use, or scientific authorization.
Fit only from F11's independently witnessed already-used F3 training split;
select smoothing by source-family-exclusive training folds, freeze, and
evaluate one separate already-used F3 validation split. All six matched
action counterfactuals are real pinned Y070 source outcomes.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"f13_raw_public_value"))
from train import grouped

SOURCE="5797a257a75fe139313e8486cd1a1ae79c44b148"
SMOOTH=(4,12,36,108)
SCHEMA="forge.f14.factorized-public-task-value.v1"

def need(value,reason):
    if not value: raise ValueError("F14_SOURCE_"+reason)

def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()

def public(arms):
    return arms[0]["public"]

def fit(training,pseudo):
    need(pseudo in SMOOTH and len(training)>0,"FROZEN_SMOOTHING")
    n=len(training)
    average=[Fraction(sum(arms[a]["loss"] for arms in training.values()),n)
             for a in range(6)]
    table={}
    for pos in range(4):
        for token in range(16):
            subset=[arms for arms in training.values() if public(arms)[pos]==token]
            table[pos,token]=tuple(
                (sum(arms[a]["loss"] for arms in subset)+pseudo*average[a])/
                (len(subset)+pseudo) for a in range(6))
    return average,table

def choose(features,model):
    average,table=model
    need(type(features) is tuple and len(features)==4 and
         all(type(v) is int and 0<=v<16 for v in features),
         "PUBLIC_ONLY_FEATURES")
    scores=[average[a]+sum((table[pos,features[pos]][a]-average[a]
              for pos in range(4)),Fraction())/4 for a in range(6)]
    return min(range(6),key=lambda a:(scores[a],a))

def ratio(v):
    return [v.numerator,v.denominator]

def digest(model):
    avg,table=model
    payload={"global":[ratio(v) for v in avg],
             "positions":[{"position":i,"token":v,
               "task_values":[ratio(x) for x in table[i,v]]}
               for i in range(4) for v in range(16)]}
    return hashlib.sha256(canonical(payload)).hexdigest()

def cross_family(training):
    families=sorted(set(key[3] for key in training))
    need(len(training)==96 and len(families)==4,"F3_TRAIN_SCOPE")
    result=[]
    for pseudo in SMOOTH:
        mismatches=0
        action_counts=[0]*6
        for family in families:
            used={k:v for k,v in training.items() if k[3]!=family}
            excluded={k:v for k,v in training.items() if k[3]==family}
            need(len(used)==72 and len(excluded)==24 and
                 not set(used).intersection(excluded),
                 "TRAIN_ONLY_EXCLUSIVE_FOLDS")
            model=fit(used,pseudo)
            for arms in excluded.values():
                action=choose(public(arms),model)
                mismatches+=arms[action]["loss"]
                action_counts[action]+=1
        result.append({"smoothing":pseudo,
                       "training_family_holdout_mismatches":mismatches,
                       "action_counts":action_counts})
    return result

def execute(f11raw,f11wraw,f13raw,f13wraw):
    f11=json.loads(f11raw); f11w=json.loads(f11wraw)
    f13=json.loads(f13raw); f13w=json.loads(f13wraw)
    need(f11.get("schema")=="forge.f11.automatic-task-aligned-information-value-engineering.v1"
         and f11.get("source_commit")==SOURCE
         and f11.get("new_first_use_claims")==0
         and f11.get("scientific_dispatch_authorized") is False
         and f11w.get("schema")=="forge.f11.independent-task-aligned-value-review.v1"
         and f11w.get("training_real_source_case_arms")==576
         and f11w.get("validation_real_source_case_arms")==672
         and f11w.get("best_constant_historical_mismatch")==66
         and f11w.get("scientific_dispatch_authorized") is False,
         "PINNED_ORIGINAL_WITNESS")
    need(f13.get("schema")=="forge.f13.raw-public-task-value-transfer.v1"
         and f13.get("status")=="PREVIOUS_F3_SOURCE_ONLY_NOT_SCIENCE"
         and f13.get("source_commit")==SOURCE
         and f13.get("parent_f11_sha256")==hashlib.sha256(f11raw).hexdigest()
         and f13.get("independent_f11_sha256")==hashlib.sha256(f11wraw).hexdigest()
         and f13.get("validation_task_mismatches")==74
         and min(f13.get("six_fixed_validation_mismatches",{}).values())==66
         and f13.get("scientific_dispatch_authorized") is False
         and f13.get("first_use_claims")==f13.get("new_originals")==0
         and f13w.get("schema")=="forge.f13.independent-raw-public-transfer-review.v1"
         and f13w.get("historical_task_mismatches")==74
         and f13w.get("best_fixed_historical_mismatches")==66
         and f13w.get("scientific_dispatch_authorized") is False
         and f13w.get("first_use_claims")==0,
         "QUALIFIED_F13_NEGATIVE")
    training=grouped(f11["training"],(67204,67205))
    validation=grouped([r for r in f11["validation"]
                        if type(r.get("arm")) is int],(67206,67207))
    scores=cross_family(training)
    choice=min(scores,key=lambda r:(
        r["training_family_holdout_mismatches"],SMOOTH.index(r["smoothing"])))
    model=fit(training,choice["smoothing"])
    selected=[]; counts=[0]*6
    for key,arms in sorted(validation.items()):
        action=choose(public(arms),model)
        counts[action]+=1
        selected.append({"seed":key[0],"pair":list(key[1]),
             "regime":key[2],"family":list(key[3]),
             "matching_policy":key[4],"public_anchors":list(public(arms)),
             "chosen_action":action,"task_mismatch":arms[action]["loss"]})
    controls={str(a):sum(arms[a]["loss"] for arms in validation.values())
              for a in range(6)}
    need(len(selected)==96 and controls["2"]==66 and
         min(controls.values())==66,"FIXED_REAL_SOURCE_CONTROLS")
    return {"schema":SCHEMA,"status":"REUSED_F3_HISTORICAL_SOURCE_ONLY",
       "hypothesis":"Y-FORGE-F14-FACTORIZED-PUBLIC-TASK-RELEVANCE-PROPOSAL",
       "source_commit":SOURCE,
       "f11_sha256":hashlib.sha256(f11raw).hexdigest(),
       "f11_witness_sha256":hashlib.sha256(f11wraw).hexdigest(),
       "f13_sha256":hashlib.sha256(f13raw).hexdigest(),
       "f13_witness_sha256":hashlib.sha256(f13wraw).hexdigest(),
       "training_seeds":[67204,67205],
       "validation_seeds":[67206,67207],
       "training_family_folds":16,
       "candidate_training_scores":scores,
       "frozen_smoothing":choice["smoothing"],
       "frozen_model_sha256":digest(model),
       "validation_choices":selected,"validation_action_counts":counts,
       "validation_task_mismatches":sum(x["task_mismatch"] for x in selected),
       "six_fixed_validation_mismatches":controls,
       "new_originals":0,"new_cohort_accesses":0,"first_use_claims":0,
       "paid_api_calls":0,"scientific_winner_selected":False,
       "scientific_dispatch_authorized":False}

def main():
    parser=argparse.ArgumentParser()
    for item in ("f11","f11-witness","f13","f13-witness","out"):
        parser.add_argument("--"+item,required=True)
    args=parser.parse_args()
    raw=[Path(getattr(args,x.replace("-","_"))).read_bytes()
         for x in ("f11","f11-witness","f13","f13-witness")]
    result=execute(*raw)
    with Path(args.out).open("xb") as f:f.write(canonical(result))
    print("F14_TRAIN_ONLY_FACTORIZED_PUBLIC_TASK_VALUE=PASS")
    print("F14_HISTORICAL_TASK_MISMATCHES="+str(result["validation_task_mismatches"]))
    print("F14_ORIGINAL_AND_FIRST_USE=ZERO")
if __name__=="__main__":main()
