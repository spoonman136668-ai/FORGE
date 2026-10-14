"""F13: learn task-value from raw public anchor history, not handcoded rotation.

Four public scalar measurements (two anchor cells, episodes 0/1) define
distance to previously witnessed cases. A training-only leave-one-source-
family-out choice among fixed k-nearest-neighbor sizes freezes *before*
evaluating the separate, already-used F3 seed split. Each of six matched
counterfactual action losses comes from the independently verified frozen
Y070 original, never a hidden label available to online policy input.
"""
import argparse, hashlib, json
from fractions import Fraction
from pathlib import Path

SOURCE="5797a257a75fe139313e8486cd1a1ae79c44b148"
PARENT="forge.f11.automatic-task-aligned-information-value-engineering.v1"
WITNESS="forge.f11.independent-task-aligned-value-review.v1"
F12="forge.f12.cross-context-task-value-transfer.v1"
F12W="forge.f12.independent-cross-context-review.v1"
K_VALUES=(4,12,24,72)
PSEUDO=8

def need(ok,why):
    if not ok:raise ValueError("F13_SOURCE_"+why)

def canonical(obj):
    return (json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()

def grouped(rows,seeds):
    need(type(rows) is list,"CASE_LIST")
    result={}
    for row in rows:
        need(type(row.get("seed")) is int and row["seed"] in seeds and
             row.get("pair") in ([8,10],[11,13]) and
             row.get("regime") in ("steady","onset1") and
             type(row.get("arm")) is int and 0<=row["arm"]<6 and
             row.get("public_reads")==10,"HISTORICAL_SCOPE")
        key=(row["seed"],tuple(row["pair"]),row["regime"],
             tuple(row["family"]),row["matching_policy"])
        observed=row["sample_trace"]
        cells=observed["addresses"]
        values=observed["public_values"]
        need(type(cells) is list and len(cells)==5 and
             cells[:2]==[[0,1],[0,1]] and
             type(values) is list and len(values)==5 and
             all(type(v) is int and 0<=v<16 for t in values[:2] for v in t)
             and all(len(t)==2 for t in values[:2]),
             "PUBLIC_FOUR_ANCHOR_SCALARS")
        features=tuple(v for pair in values[:2] for v in pair)
        action=row["arm"]
        result.setdefault(key,{})
        need(action not in result[key],"DUPLICATE_ACTION")
        result[key][action]={"public":features,
            "loss":row["pre_mismatch"]+row["post_mismatch"]}
    need(len(result)==96 and all(set(a)==set(range(6)) for a in result.values()),
         "FULL_SOURCE_COUNTERFACTUALS")
    for actions in result.values():
        need(len({v["public"] for v in actions.values()})==1,
             "MISMATCHED_CALIBRATION_OR_SOURCE")
        need(all(type(v["loss"]) is int and 0<=v["loss"]<=8
                 for v in actions.values()),"SOURCE_TASK_LOSS")
    return result

def features(arms):
    return arms[0]["public"]

def distance(a,b):
    need(len(a)==len(b)==4,"PUBLIC_VECTOR_SHAPE")
    return sum(min(abs(x-y),16-abs(x-y)) for x,y in zip(a,b))

def infer(public,training,k):
    need(type(public) is tuple and len(public)==4 and
         all(type(x) is int and 0<=x<16 for x in public) and
         type(training) is dict and len(training)>=k and k in K_VALUES,
         "PUBLIC_MODEL_INPUT")
    ordered=sorted(training.items(),
        key=lambda item:(distance(public,features(item[1])),item[0]))
    nearby=ordered[:k]
    n=len(training)
    total=[sum(arms[a]["loss"] for arms in training.values()) for a in range(6)]
    local=[sum(arms[a]["loss"] for _,arms in nearby) for a in range(6)]
    scores=[(Fraction(local[a],1)+PSEUDO*Fraction(total[a],n))/
            (k+PSEUDO) for a in range(6)]
    return min(range(6),key=lambda a:(scores[a],a))

def training_crossfamily(train):
    family_names=sorted({key[3] for key in train})
    need(len(family_names)==4,"FOUR_SOURCE_FAMILIES")
    scores=[]
    for k in K_VALUES:
        bad=0;choices=[0]*6
        for family in family_names:
            remaining={x:v for x,v in train.items() if x[3]!=family}
            heldout={x:v for x,v in train.items() if x[3]==family}
            need(len(remaining)==72 and len(heldout)==24 and
                 not set(remaining).intersection(heldout),
                 "TRAINING_ONLY_FAMILY_FOLDS")
            for arms in heldout.values():
                action=infer(features(arms),remaining,k)
                bad+=arms[action]["loss"]
                choices[action]+=1
        scores.append({"neighbors":k,"training_crossfamily_mismatches":bad,
                       "action_counts":choices})
    return scores

def execute(f11raw,f11wraw,f12raw,f12wraw):
    p=json.loads(f11raw);w=json.loads(f11wraw)
    f12=json.loads(f12raw);f12w=json.loads(f12wraw)
    need(p.get("schema")==PARENT and
         p.get("source_commit")==SOURCE and
         p.get("status")=="REUSED_F3_TRAIN_AND_VALIDATION_ONLY" and
         p.get("new_first_use_claims")==0 and
         p.get("scientific_dispatch_authorized") is False and
         w.get("schema")==WITNESS and
         w.get("status")=="PREVIOUS_F3_SOURCE_REPLAY_ONLY_NO_NEW_SCIENCE" and
         w.get("training_real_source_case_arms")==576 and
         w.get("validation_real_source_case_arms")==672 and
         w.get("best_constant_historical_mismatch")==66 and
         w.get("learned_historical_mismatch")==71 and
         w.get("scientific_dispatch_authorized") is False,
         "INDEPENDENT_ORIGINAL_SOURCE")
    need(f12.get("schema")==F12 and
         f12.get("status")=="REUSED_F3_HISTORICAL_TRANSFER_ENGINEERING_ONLY"
         and f12.get("parent_record_sha256")==hashlib.sha256(f11raw).hexdigest() and
         f12.get("independent_y070_witness_sha256")==hashlib.sha256(f11wraw).hexdigest() and
         f12.get("historical_validation_mismatches")==71 and
         f12.get("winner_selected") is False and
         f12.get("scientific_dispatch_authorized") is False and
         f12w.get("schema")==F12W and
         f12w.get("historical_validation_mismatches")==71 and
         f12w.get("training_cases")==f12w.get("validation_cases")==96 and
         f12w.get("scientific_dispatch_authorized") is False,
         "F12_NEGATIVE_SOURCE")
    train=grouped(p["training"],(67204,67205))
    validate=grouped([x for x in p["validation"] if type(x["arm"]) is int],
                     (67206,67207))
    scores=training_crossfamily(train)
    best=min(scores,key=lambda x:(
        x["training_crossfamily_mismatches"],K_VALUES.index(x["neighbors"])))
    k=best["neighbors"];decisions=[];counts=[0]*6
    for case,arms in sorted(validate.items()):
        public=features(arms)
        arm=infer(public,train,k)
        counts[arm]+=1
        decisions.append({"seed":case[0],"pair":list(case[1]),
            "regime":case[2],"family":list(case[3]),
            "matching_policy":case[4],"public_anchors":list(public),
            "chosen_action":arm,"task_mismatch":arms[arm]["loss"]})
    control={str(i):sum(v[i]["loss"] for v in validate.values()) for i in range(6)}
    need(control["0"]==74 and control["2"]==66 and
         min(control.values())==66 and len(decisions)==96,
         "SIX_SOURCE_FIXED_CONTROLS")
    return {"schema":"forge.f13.raw-public-task-value-transfer.v1",
       "status":"PREVIOUS_F3_SOURCE_ONLY_NOT_SCIENCE",
       "hypothesis":"Y-FORGE-F13-RAW-PUBLIC-TASK-RELEVANCE-TRANSFER-PROPOSAL",
       "parent_f11_sha256":hashlib.sha256(f11raw).hexdigest(),
       "independent_f11_sha256":hashlib.sha256(f11wraw).hexdigest(),
       "parent_f12_sha256":hashlib.sha256(f12raw).hexdigest(),
       "independent_f12_sha256":hashlib.sha256(f12wraw).hexdigest(),
       "source_commit":SOURCE,"train_seed_ids":[67204,67205],
       "validation_seed_ids":[67206,67207],
       "training_crossfamily_candidate_scores":scores,
       "frozen_neighbors":k,"validation_choices":decisions,
       "validation_action_counts":counts,
       "validation_task_mismatches":sum(x["task_mismatch"] for x in decisions),
       "six_fixed_validation_mismatches":control,
       "new_cohort_accesses":0,"new_originals":0,"first_use_claims":0,
       "paid_api_calls":0,"scientific_winner_selected":False,
       "scientific_dispatch_authorized":False}

def main():
    a=argparse.ArgumentParser()
    for n in ("f11","f11-witness","f12","f12-witness","out"):
        a.add_argument("--"+n,required=True)
    x=a.parse_args()
    paths=[Path(getattr(x,n.replace("-","_"))).read_bytes()
           for n in ("f11","f11-witness","f12","f12-witness")]
    doc=execute(*paths)
    with Path(x.out).open("xb") as fd:fd.write(canonical(doc))
    print("F13_RAW_PUBLIC_FAMILY_HELDOUT_TRAINING=PASS")
    print("F13_TRAIN_ONLY_NEIGHBORS="+str(doc["frozen_neighbors"]))
    print("F13_HISTORICAL_TASK_MISMATCHES="+str(doc["validation_task_mismatches"]))
    print("F13_FRESH_ORIGINALS_AND_FIRST_USE=ZERO")
if __name__=="__main__":main()
