"""F12 cross-context task-value transfer from independently replayed F11.

No new simulator, no novel/held-out scientific cohorts, no new controllers.
Use the six fully observed F11 counterfactual actions per *already used*
F3 case. Select a circular public-context pooling width by leave-one-
source-family-out TRAINING cross-validation, freeze it, then score the
previously used and separate 67206/67207 development split exactly once.

The parent F11 Y070 original source and independent source witness remain
the authority for each counterfactual, not unverified synthetic labels.
"""
import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path

SOURCE="5797a257a75fe139313e8486cd1a1ae79c44b148"
TRAIN=(67204,67205)
CHECK=(67206,67207)
RADII=(0,1,2,3,7)
PSEUDO=8
MIN_SUPPORT=3
PARENT_SCHEMA="forge.f11.automatic-task-aligned-information-value-engineering.v1"
WITNESS_SCHEMA="forge.f11.independent-task-aligned-value-review.v1"
SCHEMA="forge.f12.cross-context-task-value-transfer.v1"
HYPOTHESIS="Y-FORGE-F12-CROSS-CONTEXT-TRANSFER-PROPOSAL"

def need(ok,reason):
    if not ok:
        raise ValueError("F12_FAIL_CLOSED_"+reason)

def encode(data):
    return (json.dumps(data,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()

def evidence(parent,witness):
    need(parent.get("schema")==PARENT_SCHEMA and
         parent.get("status")=="REUSED_F3_TRAIN_AND_VALIDATION_ONLY" and
         parent.get("source_commit")==SOURCE and
         parent.get("scientific_dispatch_authorized") is False and
         parent.get("scientific_winner_selected") is False and
         all(parent.get(k)==0 for k in (
             "new_first_use_claims","new_originals","new_cohort_accesses",
             "paid_api_calls")),"PARENT_IDENTITY_AND_AUTHORITY")
    model=parent.get("model",{})
    need(model.get("train_seeds")==list(TRAIN) and
         model.get("validation_seeds")==list(CHECK) and
         model.get("source_commit")==SOURCE and
         model.get("training_cases_per_order")==96 and
         model.get("public_scalar_reads")==10 and
         model.get("retained_limit")==9 and
         model.get("scientific_dispatch_authorized") is False and
         model.get("new_first_use_claims")==0,"FROZEN_PARENT_MODEL")
    need(witness.get("schema")==WITNESS_SCHEMA and
         witness.get("status")=="PREVIOUS_F3_SOURCE_REPLAY_ONLY_NO_NEW_SCIENCE"
         and witness.get("training_real_source_case_arms")==576
         and witness.get("validation_real_source_case_arms")==672
         and witness.get("reviewed_model_table_values")==84
         and witness.get("validation_totals")==parent.get("validation_summary")
         and witness.get("best_constant_historical_mismatch")==66
         and witness.get("learned_historical_mismatch")==71
         and witness.get("scientific_dispatch_authorized") is False
         and witness.get("new_first_use_claims")==0,
         "INDEPENDENT_SOURCE_REPLAY_WITNESS")
    return True

def grouped(rows,seeds,expected):
    need(type(rows) is list and len(rows)==96*len(expected),
         "ARM_CASE_COUNT")
    output={}
    for r in rows:
        need(type(r) is dict and
             type(r.get("seed")) is int and r["seed"] in seeds and
             r.get("pair") in ([8,10],[11,13]) and
             r.get("regime") in ("steady","onset1") and
             type(r.get("family")) is list and
             type(r.get("matching_policy")) is str,
             "CASE_IDENTITY")
        a=r.get("arm")
        need(type(a) is int and a in expected,"ACTION_IDENTITY")
        key=(r["seed"],tuple(r["pair"]),r["regime"],
             tuple(r["family"]),r["matching_policy"])
        output.setdefault(key,{})
        need(a not in output[key],"ONCE_ONLY_CASE_ACTION")
        output[key][a]=r
        trace=r.get("sample_trace",{}).get("decision",{})
        loss=r.get("pre_mismatch")
        post=r.get("post_mismatch")
        need(type(loss) is int and type(post) is int and
             0<=loss<=8 and 0<=post<=8 and loss+post<=8 and
             type(trace.get("public_start")) is int and
             0<=trace["public_start"]<14 and
             trace.get("reads")==10 and
             trace.get("distinct_nonanchors")==6 and
             type(trace.get("physical_cells")) is list and
             len(set(trace["physical_cells"]))==6 and
             trace.get("action_index")==a and
             r.get("public_reads")==10,"PUBLIC_TRACE_OR_BUDGET")
    need(len(output)==96 and all(set(v)==set(expected) for v in output.values()),
         "COMPLETE_MATCHED_COUNTERFACTUALS")
    for actions in output.values():
        readings=list(actions.values())
        t=readings[0]["sample_trace"]["decision"]
        need(all(x["sample_trace"]["decision"]["public_start"]==
                 t["public_start"] and
                 x["sample_trace"]["decision"]["physical_cells"]==
                 t["physical_cells"] for x in readings),
             "SENSOR_SET_OR_CONTEXT_NOT_MATCHED")
    return output

def distance(a,b):
    d=abs(a-b)
    return min(d,14-d)

def action_cost(row):
    return row["pre_mismatch"]+row["post_mismatch"]

def choose(context,training,radius):
    need(type(context) is int and 0<=context<14 and radius in RADII
         and type(training) is dict and len(training)>0,"MODEL_INPUT")
    matched=list(training.values())
    totals=[0]*6
    sum_local=[0]*6
    nlocal=[0]*6
    for arms in matched:
        sensor_context=arms[0]["sample_trace"]["decision"]["public_start"]
        near=distance(context,sensor_context)<=radius
        for a in range(6):
            loss=action_cost(arms[a])
            totals[a]+=loss
            if near:
                sum_local[a]+=loss
                nlocal[a]+=1
    need(len(set(nlocal))==1,"COUNTERFACTUAL_SUPPORT_BIAS")
    n=len(matched)
    scores=[]
    for action in range(6):
        global_mean=Fraction(totals[action],n)
        if nlocal[action]<MIN_SUPPORT:
            score=global_mean
        else:
            score=(sum_local[action]+PSEUDO*global_mean)/(nlocal[action]+PSEUDO)
        scores.append(score)
    return min(range(6),key=lambda a:(scores[a],a))

def leave_family_out(train):
    families=sorted({key[3] for key in train})
    need(len(families)==4,"FOUR_TRAINING_FAMILIES")
    candidates=[]
    for radius in RADII:
        costs=0
        choices=[0]*6
        for family in families:
            fit={k:v for k,v in train.items() if k[3]!=family}
            held={k:v for k,v in train.items() if k[3]==family}
            need(len(fit)==72 and len(held)==24,"FAMILY_GROUP_LEAKAGE")
            for actions in held.values():
                context=actions[0]["sample_trace"]["decision"]["public_start"]
                arm=choose(context,fit,radius)
                costs+=action_cost(actions[arm])
                choices[arm]+=1
        candidates.append({"radius":radius,
                           "leave_family_out_mismatches":costs,
                           "training_action_counts":choices})
    return candidates

def proceed(raw,independent_raw):
    parent=json.loads(raw)
    witness=json.loads(independent_raw)
    evidence(parent,witness)
    train=grouped(parent.get("training"),TRAIN,tuple(range(6)))
    validation=grouped([row for row in parent.get("validation",[])
                        if type(row.get("arm")) is int],
                       CHECK,tuple(range(6)))
    scorecard=leave_family_out(train)
    best=min(scorecard,key=lambda x:(
        x["leave_family_out_mismatches"],RADII.index(x["radius"])))
    radius=best["radius"]
    selected=[]
    action_counts=[0]*6
    for key,arms in sorted(validation.items()):
        context=arms[0]["sample_trace"]["decision"]["public_start"]
        action=choose(context,train,radius)
        row=arms[action]
        action_counts[action]+=1
        selected.append({"seed":key[0],"pair":list(key[1]),
                         "regime":key[2],"family":list(key[3]),
                         "matching_policy":key[4],
                         "public_start":context,"selected_action":action,
                         "pre_mismatch":row["pre_mismatch"],
                         "post_mismatch":row["post_mismatch"],
                         "first_detection":row["first_detection"]})
    total=sum(x["pre_mismatch"]+x["post_mismatch"] for x in selected)
    need(len(selected)==96 and sum(action_counts)==96,"VALIDATION_COUNTS")
    controls={str(a):sum(action_cost(v[a]) for v in validation.values())
              for a in range(6)}
    need(controls["0"]==74 and controls["2"]==66 and
         min(controls.values())==66,"ORIGINAL_CONTROLS")
    return {"schema":SCHEMA,
        "status":"REUSED_F3_HISTORICAL_TRANSFER_ENGINEERING_ONLY",
        "hypothesis_id":HYPOTHESIS,
        "parent_y070_commit":SOURCE,
        "parent_record_sha256":hashlib.sha256(raw).hexdigest(),
        "independent_y070_witness_sha256":hashlib.sha256(independent_raw).hexdigest(),
        "protocol":"leave-one-F3-source-family-out-training-only-cyclic-kernel",
        "training_seeds":list(TRAIN),"validation_seeds":list(CHECK),
        "candidate_radii":list(RADII),
        "pseudo_observations":PSEUDO,"minimum_context_support":MIN_SUPPORT,
        "training_source_counterfactual_cases":576,
        "previously_used_validation_counterfactual_cases":576,
        "leave_family_out_scores":scorecard,
        "frozen_radius":radius,
        "validation_case_selections":selected,
        "validation_action_counts":action_counts,
        "historical_validation_mismatches":total,
        "historical_fixed_controls":controls,
        "winner_selected":False,"scientific_dispatch_authorized":False,
        "new_first_use_claims":0,"new_originals":0,
        "new_cohort_accesses":0,"paid_api_calls":0}

def main():
    p=argparse.ArgumentParser()
    for name in ("parent","witness","out"):
        p.add_argument("--"+name,required=True)
    a=p.parse_args()
    result=proceed(Path(a.parent).read_bytes(),
                   Path(a.witness).read_bytes())
    with Path(a.out).open("xb") as fd:
        fd.write(encode(result))
    print("F12_TRAIN_ONLY_CROSS_CONTEXT_POOLING=PASS")
    print("F12_FROZEN_RADIUS="+str(result["frozen_radius"]))
    print("F12_SOURCE_USED_VALIDATION_MISMATCHES="+
          str(result["historical_validation_mismatches"]))
    print("F12_BEST_FIXED_USED_DEVELOPMENT=66")
    print("F12_ORIGINAL_SCIENTIFIC_FIRST_USE=ZERO")
if __name__=="__main__":
    main()
