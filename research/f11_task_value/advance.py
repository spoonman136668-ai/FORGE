"""F11 end-to-end autonomous task-value training from F10's negative.

No more handcrafted public-start rules. Evaluate all six matched-physical-
sensor temporal orders on *previously consumed* F3 training seeds, fit
posterior expected future physical-matching loss by public calibration,
freeze it before separately-used validation seeds, then compare with all
six constant order controls and qualified F9 controls. F10 unchanged.
"""
import argparse,hashlib,json
from pathlib import Path
from policy import (ORDERS,SOURCE,TRAIN_SEEDS,TEST_SEEDS,PAIRS,
                    SCHEMA,STATUS,PSEUDO,MIN_CONTEXT_SUPPORT,
                    validate_model)
from worker import load_source,evaluate

def need(ok,why):
    if not ok:raise ValueError("F11_AUTONOMOUS_"+why)

def canonical(data):
    return (json.dumps(data,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()

def previous_evidence(f10,f10_review,f11,f11_review):
    need(f10.get("schema")=="forge.f10.automatic-public-information-value-engineering.v1"
         and f10.get("status")=="F3_USED_ONLY_NO_SCIENTIFIC_AUTHORITY"
         and f10.get("model",{}).get("train_seeds")==list(TRAIN_SEEDS)
         and f10.get("model",{}).get("validation_seeds")==list(TEST_SEEDS)
         and f10.get("new_first_use_claims")==0 and
         f10.get("scientific_dispatch_authorized") is False
         and f10.get("new_scientific_originals")==0,
         "F10_PARENT_SOURCE")
    need(f10_review.get("schema")=="forge.f10.independent-learned-information-value-review.v1"
         and f10_review.get("status")=="F3_USED_SOURCE_REPLAY_QUALIFIED_NOT_SCIENCE"
         and f10_review.get("replayed_validation")==96
         and f10_review.get("f10_historical_mismatches")==112
         and f10_review.get("best_fixed_historical_mismatches")==66
         and f10_review.get("scientific_dispatch_authorized") is False,
         "INDEPENDENT_F10_NEGATIVE")
    need(f11.get("schema")=="forge.f10.automatic-negative-to-f11-design.v1"
         and f11.get("status")=="ENGINEERING_SUCCESSOR_ONLY_FIRST_USE_BLOCKED"
         and f11.get("selected_proposal_id")==
             "Y-FORGE-F11-TASK-ALIGNED-OBSERVATION-VALUE-PROPOSAL"
         and f11.get("historical_f10_mismatches")==112
         and f11.get("historical_best_fixed_mismatches")==66
         and f11.get("original_f10_model_frozen_no_retuning") is True
         and f11.get("scientific_dispatch_authorized") is False
         and f11.get("new_first_use_claims")==0
         and f11.get("new_data_accesses")==0,"F11_HYPOTHESIS")
    need(f11_review.get("schema")=="forge.f11.independent-negative-successor-review.v1"
         and f11_review.get("status")=="F11_DESIGN_PREPARED_NO_PROSPECTIVE_FIRST_USE"
         and f11_review.get("selected_id")==f11["selected_proposal_id"]
         and f11_review.get("replayed_rows")==96
         and f11_review.get("first_use_claims")==0
         and f11_review.get("scientific_dispatch_authorized") is False,
         "F11_HYPOTHESIS_REVIEW")

def initial_model():
    obj={"schema":SCHEMA,"status":STATUS,"source_commit":SOURCE,
         "train_seeds":list(TRAIN_SEEDS),"validation_seeds":list(TEST_SEEDS),
         "orders":[list(a) for a in ORDERS],
         "pseudo_observations":PSEUDO,
         "minimum_context_support":MIN_CONTEXT_SUPPORT,
         "training_cases_per_order":96,"public_scalar_reads":10,
         "retained_limit":9,"new_first_use_claims":0,
         "scientific_dispatch_authorized":False,
         "value_table":[{"public_start":s,"action_index":a,
                         "cases":0,"total_task_loss":0,"global_loss":0}
                        for s in range(14) for a in range(6)]}
    validate_model(obj)
    return obj

def source_cases(source,seeds,model,actions):
    out=[]
    for pair in PAIRS:
        for regime in ("steady","onset1"):
            for family in source.FAMILIES:
                for seed in seeds:
                    for policy in source.POLICIES:
                        for arm in actions:
                            out.append(evaluate(source,model,seed,pair,regime,
                                                family,policy,arm))
    return out

def fit(records):
    need(type(records) is list and len(records)==576,"TRAINING_CASE_COUNT")
    example={}
    sums=[[0,0] for _ in range(6)]
    local=[[[0,0] for _ in range(6)] for _ in range(14)]
    for row in records:
        need(row.get("seed") in TRAIN_SEEDS and
             type(row.get("arm")) is int and row["arm"] in range(6) and
             row.get("pair") in [list(x) for x in PAIRS],
             "TRAIN_ONLY_ACTION")
        identity=(row["seed"],tuple(row["pair"]),row["regime"],
                  tuple(row["family"]),row["matching_policy"])
        example.setdefault(identity,set())
        need(row["arm"] not in example[identity],"DUPLICATED_COUNTERFACTUAL")
        example[identity].add(row["arm"])
        s=row["sample_trace"]["decision"]["public_start"]
        need(type(s) is int and 0<=s<14,"PUBLIC_CONTEXT")
        loss=row["pre_mismatch"]+row["post_mismatch"]
        need(type(loss) is int and 0<=loss<=8,"TASK_MISMATCH_LOSS")
        local[s][row["arm"]][0]+=1
        local[s][row["arm"]][1]+=loss
        sums[row["arm"]][0]+=1
        sums[row["arm"]][1]+=loss
    need(len(example)==96 and all(v==set(range(6)) for v in example.values())
         and all(pair[0]==96 for pair in sums),"MATCHED_FULL_ACTION_BUDGET")
    model=initial_model()
    for s in range(14):
        supports=set(local[s][arm][0] for arm in range(6))
        need(len(supports)==1,"CONTEXT_SUPPORT_BIAS")
        for arm in range(6):
            row=model["value_table"][s*6+arm]
            row["cases"],row["total_task_loss"]=local[s][arm]
            row["global_loss"]=sums[arm][1]
    validate_model(model)
    return model

def summarize(rows,arms):
    groups={str(x):{"cases":0,"pre":0,"post":0,"detections":0,
                    "steady_errors":0,"earliest_detection":None}
            for x in arms}
    for row in rows:
        group=groups[str(row["arm"])]
        group["cases"]+=1
        group["pre"]+=row["pre_mismatch"]
        group["post"]+=row["post_mismatch"]
        group["detections"]+=int(row["first_detection"] is not None)
        if row["regime"]=="steady":
            group["steady_errors"]+=row["pre_mismatch"]+row["post_mismatch"]
        first=row["first_detection"]
        if first is not None:
            group["earliest_detection"]=(first if group["earliest_detection"] is None
                                        else min(first,group["earliest_detection"]))
    need(all(x["cases"]==96 for x in groups.values()),"BALANCED_COMPARATORS")
    return groups

def run(raws,root):
    documents=[json.loads(b) for b in raws]
    previous_evidence(*documents)
    source=load_source(root)
    train_rows=source_cases(source,TRAIN_SEEDS,initial_model(),tuple(range(6)))
    frozen=fit(train_rows)
    check_rows=source_cases(source,TEST_SEEDS,frozen,tuple(range(6))+("LEARNED",))
    need(len(check_rows)==672,"VALIDATION_COUNT")
    totals=summarize(check_rows,tuple(range(6))+("LEARNED",))
    need(totals["0"]["pre"]+totals["0"]["post"]==74 and
         totals["2"]["pre"]+totals["2"]["post"]==66 and
         all(group["steady_errors"]==0 for group in totals.values()),
         "F8_SOURCE_MATCHED_CONTROLS")
    return {
      "schema":"forge.f11.automatic-task-aligned-information-value-engineering.v1",
      "status":"REUSED_F3_TRAIN_AND_VALIDATION_ONLY",
      "source_commit":SOURCE,
      "parent_sha256":{"f10":hashlib.sha256(raws[0]).hexdigest(),
                       "f10_witness":hashlib.sha256(raws[1]).hexdigest(),
                       "f11_hypothesis":hashlib.sha256(raws[2]).hexdigest(),
                       "f11_hypothesis_witness":hashlib.sha256(raws[3]).hexdigest()},
      "model":frozen,"training":train_rows,
      "validation":check_rows,"validation_summary":totals,
      "new_first_use_claims":0,"new_originals":0,
      "new_cohort_accesses":0,"paid_api_calls":0,
      "scientific_winner_selected":False,
      "scientific_dispatch_authorized":False
    }

def main():
    p=argparse.ArgumentParser()
    for name in ("f10","f10-witness","f11","f11-witness","source-root","out"):
        p.add_argument("--"+name,required=True)
    a=p.parse_args()
    inputs=[Path(getattr(a,key.replace("-","_"))).read_bytes() for key
            in ("f10","f10-witness","f11","f11-witness")]
    report=run(inputs,a.source_root)
    encoded=canonical(report)
    with Path(a.out).open("xb") as out:out.write(encoded)
    totals={k:v["pre"]+v["post"] for k,v in report["validation_summary"].items()}
    print("F11_AUTOMATIC_TASK_ALIGNED_TRAIN_AND_VALIDATION=PASS")
    print("F11_TRAINED_REAL_CASE_ARMS=576")
    print("F11_REPLAYED_REAL_VALIDATION_ARMS=672")
    print("F11_HISTORICAL_MISMATCH_TOTALS="+str(totals))
    print("F11_LEARNED_ADAPTATION_NO_PREMATURE_WINNER")
    print("F11_ARCHIVE_SHA256="+hashlib.sha256(encoded).hexdigest())
    print("F11_PROSPECTIVE_FIRST_USE=ZERO")
if __name__=="__main__":main()
