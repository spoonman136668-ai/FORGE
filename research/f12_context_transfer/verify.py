"""Independent F12 training-fold and historical counterfactual verifier.

Does NOT import F12 producer fit/choose/scorecard code. Input F11 source
record was already independently replayed against the pinned real Y070
simulator in the preceding automatic GitHub Actions step. This verifier
reconstructs all matched action labels, four disjoint family holdouts,
frozen pooling width and 96 earlier-used development-only decisions.
"""
import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path

RADII=(0,1,2,3,7)
PARENT="forge.f11.automatic-task-aligned-information-value-engineering.v1"
WITNESS="forge.f11.independent-task-aligned-value-review.v1"

def deny(ok,label):
    if not ok: raise ValueError("F12_INDEPENDENT_"+label)

def case_set(rows,seeds,actions):
    deny(type(rows) is list and len(rows)==96*len(actions),"CASE_COUNT")
    groups={}
    for item in rows:
        deny(type(item) is dict and type(item.get("seed")) is int
             and item["seed"] in seeds and item.get("pair") in ([8,10],[11,13])
             and item.get("regime") in ("steady","onset1")
             and type(item.get("family")) is list
             and type(item.get("matching_policy")) is str
             and type(item.get("arm")) is int and item["arm"] in actions,
             "CASE_OR_SOURCE_ID")
        key=(item["seed"],tuple(item["pair"]),item["regime"],
             tuple(item["family"]),item["matching_policy"])
        actions_by_case=groups.setdefault(key,{})
        deny(item["arm"] not in actions_by_case,"DUPLICATE_ACTION")
        actions_by_case[item["arm"]]=item
        att=item.get("sample_trace",{}).get("decision",{})
        pre=item.get("pre_mismatch")
        post=item.get("post_mismatch")
        deny(type(pre) is int and type(post) is int
             and 0<=pre<=8 and 0<=post<=8 and pre+post<=8
             and type(att.get("public_start")) is int and 0<=att["public_start"]<14
             and att.get("action_index")==item["arm"]
             and att.get("reads")==item.get("public_reads")==10
             and att.get("distinct_nonanchors")==6
             and type(att.get("physical_cells")) is list
             and len(att["physical_cells"])==6
             and len(set(att["physical_cells"]))==6,
             "PUBLIC_TRACE_METRIC_DRIFT")
    deny(len(groups)==96,"MISSING_SOURCE_CASES")
    for acts in groups.values():
        deny(set(acts)==set(actions),"MISSING_ACTION_LABEL")
        contexts={v["sample_trace"]["decision"]["public_start"] for v in acts.values()}
        sensors={tuple(v["sample_trace"]["decision"]["physical_cells"])
                 for v in acts.values()}
        deny(len(contexts)==len(sensors)==1,"ACTION_SENSOR_OR_CONTEXT_DRIFT")
    return groups

def choose_action(context,examples,radius):
    deny(radius in RADII and type(context) is int and 0<=context<14
         and len(examples)>0,"MODEL_DOMAIN")
    n=len(examples)
    aggregates=[]
    for action in range(6):
        global_loss=0
        local_loss=0
        local_count=0
        for case in examples.values():
            source_context=case[action]["sample_trace"]["decision"]["public_start"]
            d=abs(context-source_context)
            related=min(d,14-d)<=radius
            loss=case[action]["pre_mismatch"]+case[action]["post_mismatch"]
            global_loss+=loss
            if related:
                local_count+=1
                local_loss+=loss
        global_mean=Fraction(global_loss,n)
        score=(global_mean if local_count<3 else
               (local_loss+8*global_mean)/(local_count+8))
        aggregates.append(score)
    return sorted(range(6),key=lambda a:(aggregates[a],a))[0]

def recompute(parent_bytes,witness_bytes,proposal):
    origin=json.loads(parent_bytes)
    review=json.loads(witness_bytes)
    deny(origin.get("schema")==PARENT
         and origin.get("status")=="REUSED_F3_TRAIN_AND_VALIDATION_ONLY"
         and origin.get("source_commit")==
            "5797a257a75fe139313e8486cd1a1ae79c44b148"
         and origin.get("scientific_dispatch_authorized") is False
         and origin.get("scientific_winner_selected") is False
         and all(origin.get(k)==0 for k in ("new_first_use_claims",
             "new_originals","new_cohort_accesses","paid_api_calls")),
         "PARENT_SOURCE_IDENTITY")
    deny(review.get("schema")==WITNESS and
         review.get("status")=="PREVIOUS_F3_SOURCE_REPLAY_ONLY_NO_NEW_SCIENCE"
         and review.get("training_real_source_case_arms")==576 and
         review.get("validation_real_source_case_arms")==672 and
         review.get("validation_totals")==origin.get("validation_summary")
         and review.get("best_constant_historical_mismatch")==66 and
         review.get("learned_historical_mismatch")==71 and
         review.get("new_first_use_claims")==0 and
         review.get("scientific_dispatch_authorized") is False,
         "INDEPENDENT_PINNED_Y070_REPLAY")
    deny(proposal.get("schema")=="forge.f12.cross-context-task-value-transfer.v1"
         and proposal.get("status")=="REUSED_F3_HISTORICAL_TRANSFER_ENGINEERING_ONLY"
         and proposal.get("hypothesis_id")=="Y-FORGE-F12-CROSS-CONTEXT-TRANSFER-PROPOSAL"
         and proposal.get("parent_record_sha256")==hashlib.sha256(parent_bytes).hexdigest()
         and proposal.get("independent_y070_witness_sha256")==
            hashlib.sha256(witness_bytes).hexdigest()
         and proposal.get("protocol")==
            "leave-one-F3-source-family-out-training-only-cyclic-kernel"
         and proposal.get("parent_y070_commit")==origin.get("source_commit")
         and proposal.get("training_seeds")==[67204,67205]
         and proposal.get("validation_seeds")==[67206,67207]
         and proposal.get("candidate_radii")==list(RADII)
         and proposal.get("pseudo_observations")==8
         and proposal.get("minimum_context_support")==3
         and proposal.get("training_source_counterfactual_cases")==576
         and proposal.get("previously_used_validation_counterfactual_cases")==576,
         "PROTOCOL_PROVENANCE")
    training=case_set(origin.get("training"),(67204,67205),tuple(range(6)))
    validation=case_set([x for x in origin.get("validation",[])
                         if type(x.get("arm")) is int],
                        (67206,67207),tuple(range(6)))
    family_set=sorted(set(k[3] for k in training))
    deny(len(family_set)==4,"HISTORICAL_SOURCE_FAMILY_COUNT")
    cv=[]
    for radius in RADII:
        misses=0
        histogram=[0]*6
        for family in family_set:
            fitted={key:case for key,case in training.items() if key[3]!=family}
            excluded={key:case for key,case in training.items() if key[3]==family}
            deny(len(fitted)==72 and len(excluded)==24 and
                 not set(fitted).intersection(excluded),"CROSS_VALIDATION_LEAK")
            for case in excluded.values():
                context=case[0]["sample_trace"]["decision"]["public_start"]
                selected=choose_action(context,fitted,radius)
                misses+=case[selected]["pre_mismatch"]+case[selected]["post_mismatch"]
                histogram[selected]+=1
        cv.append({"radius":radius,"leave_family_out_mismatches":misses,
                   "training_action_counts":histogram})
    best=min(cv,key=lambda entry:(entry["leave_family_out_mismatches"],
                                  RADII.index(entry["radius"])))
    deny(proposal.get("leave_family_out_scores")==cv and
         proposal.get("frozen_radius")==best["radius"],
         "FIT_ON_HELDOUT_OR_CHANGED_CV")
    cases=[]
    histogram=[0]*6
    for key,arms in sorted(validation.items()):
        context=arms[0]["sample_trace"]["decision"]["public_start"]
        picked=choose_action(context,training,best["radius"])
        histogram[picked]+=1
        obs=arms[picked]
        cases.append({"seed":key[0],"pair":list(key[1]),
            "regime":key[2],"family":list(key[3]),
            "matching_policy":key[4],"public_start":context,
            "selected_action":picked,
            "pre_mismatch":obs["pre_mismatch"],
            "post_mismatch":obs["post_mismatch"],
            "first_detection":obs["first_detection"]})
    observed=sum(v["pre_mismatch"]+v["post_mismatch"] for v in cases)
    controls={str(a):sum(
        case[a]["pre_mismatch"]+case[a]["post_mismatch"] for case in validation.values())
        for a in range(6)}
    deny(controls["0"]==74 and controls["2"]==66
         and min(controls.values())==66,
         "PINNED_HISTORICAL_FIXED_CONTROLS")
    deny(proposal.get("validation_case_selections")==cases
         and proposal.get("validation_action_counts")==histogram
         and proposal.get("historical_validation_mismatches")==observed
         and proposal.get("historical_fixed_controls")==controls,
         "NEW_MODEL_VALIDATION_REPLAY")
    deny(proposal.get("scientific_dispatch_authorized") is False
         and proposal.get("winner_selected") is False
         and all(proposal.get(k)==0 for k in ("new_first_use_claims",
                "new_originals","new_cohort_accesses","paid_api_calls")),
         "UNAUTHORIZED_SCIENTIFIC_ORIGINAL")
    return {"schema":"forge.f12.independent-cross-context-review.v1",
        "status":"REUSED_F3_COUNTERFACTUAL_TRANSFER_ONLY_NOT_SCIENCE",
        "source_replay_witness_verified":True,
        "training_cases":96,"validation_cases":96,
        "recomputed_training_folds":4*len(RADII),
        "frozen_radius":best["radius"],
        "historical_validation_mismatches":observed,
        "historical_best_fixed_mismatches":66,
        "validation_action_counts":histogram,
        "new_first_use_claims":0,"scientific_dispatch_authorized":False}

def main():
    p=argparse.ArgumentParser()
    for x in ("record","parent","witness","out"):p.add_argument("--"+x,required=True)
    a=p.parse_args()
    record=json.loads(Path(a.record).read_bytes())
    result=recompute(Path(a.parent).read_bytes(),Path(a.witness).read_bytes(),record)
    data=(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n").encode()
    with Path(a.out).open("xb") as f:f.write(data)
    print("F12_INDEPENDENT_CROSS_CONTEXT_SOURCE_TRANSFER=PASS")
    print("F12_VALIDATION_MISMATCHES="+str(result["historical_validation_mismatches"]))
    print("F12_BEST_FIXED=66")
    print("F12_FIRST_USE_ORIGINAL=ZERO")
if __name__=="__main__":main()
