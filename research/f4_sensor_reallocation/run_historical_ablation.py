"""F4 historical engineering ablation on previously used F3 development seeds.

This evaluates the effect of physically different public sensors versus
sampling the SAME sensor multiset later. Every seed and swap pair was already
used in R36/F3 development. This is explicitly NOT F4 prospective training,
sealed evaluation, winner selection, or scientific acceptance.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from historical_train import historical_training_cases,learn_coverage,digest_model
from matched_worker import (
    load_pinned,score_case,verify_comparators,F3_DEV_USED,
    ARMS,Y070_COMMIT,SET_FIXTURE,ORDER_FIXTURE,
)

F3_PAIRS=((8,10),(11,13))
REGIMES=(("steady",None),("onset1",1))
EXPECTED_CASES=2*2*4*4*3*3

def run(root):
    model=learn_coverage(historical_training_cases())
    controls=verify_comparators()
    if model["set_schedule"]!=[list(p) for p in controls["F4-SET"]] or (
            model["order_control_schedule"]!=[list(p) for p in controls["F4-ORDER-CONTROL"]]):
        raise ValueError("F4_HISTORICAL_LEARNED_CONTROL_DRIFT")
    if tuple(model["learned_physical_sensors"])!=SET_FIXTURE[3] or (
            tuple(model["order_control_schedule"][-1])!=ORDER_FIXTURE[-1]):
        raise ValueError("F4_HISTORICAL_MODEL_NOT_IN_WORKER")
    y070=load_pinned(root)
    data=[]
    for pair in F3_PAIRS:
        for regime,onset in REGIMES:
            for family in y070.FAMILIES:
                for seed in F3_DEV_USED:
                    for policy in y070.POLICIES:
                        for arm in ARMS:
                            record=score_case(y070,seed,pair,onset,family,policy,arm)
                            record["regime"]=regime
                            data.append(record)
    if len(data)!=EXPECTED_CASES or any(x["seed"] not in F3_DEV_USED for x in data):
        raise ValueError("F4_HISTORICAL_COHORT_DRIFT")
    totals={arm:{"pre":0,"post":0,"detections":0,"cases":0,"steady_errors":0} for arm in ARMS}
    by_pair={}
    for record in data:
        arm=record["arm"]
        result=totals[arm]
        result["pre"]+=record["pre"]
        result["post"]+=record["post"]
        result["detections"]+=int(record["first_detection"] is not None)
        result["cases"]+=1
        if record["regime"]=="steady":
            result["steady_errors"]+=record["pre"]+record["post"]
        key=f"{record['pair'][0]}_{record['pair'][1]}:{record['regime']}:{arm}"
        if key not in by_pair:
            by_pair[key]={"pre":0,"post":0,"detections":0,"cases":0}
        by_pair[key]["pre"]+=record["pre"]
        by_pair[key]["post"]+=record["post"]
        by_pair[key]["detections"]+=int(record["first_detection"] is not None)
        by_pair[key]["cases"]+=1
    return {
        "schema":"forge.f4.historical-equal-decoder-ablation.v1",
        "status":"F3_REUSED_DEV_ABLATION_ONLY_NO_F4_FIRST_USE",
        "source_commit":Y070_COMMIT,
        "historical_training_sha256":digest_model(model),
        "train_seed_ids":model["training_seed_ids"],
        "historical_validation_seed_ids":list(F3_DEV_USED),
        "f3_dev_pairs":[list(pair) for pair in F3_PAIRS],
        "public_decoder":"F4-PUBLIC-DECODER-V1",
        "model":model,
        "arms":{arm:[list(pair) for pair in schedule] for arm,schedule in controls.items()},
        "records":data,
        "totals":totals,
        "by_pair_and_regime":by_pair,
        "f4_development_cohorts_used":0,
        "f4_sealed_cohorts_used":0,
        "new_first_use_claims":0,
        "new_scientific_originals":0,
        "scientific_winner_selected":False,
        "qualification_limit":"Historical F3 dev replay, NOT new independent F4 scientific evidence",
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--yggdrasil-root",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    result=run(a.yggdrasil_root)
    data=(json.dumps(result,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    with Path(a.out).open("xb") as fd:fd.write(data)
    print("F4_HISTORICAL_THREE_ARM_ABLATION=PASS")
    print("F4_HISTORICAL_CASES="+str(len(result["records"])))
    for arm,score in result["totals"].items():
        print("F4_HISTORICAL_"+arm.replace("-","_")+"="+str(score))
    print("F4_HISTORICAL_SHA256="+hashlib.sha256(data).hexdigest())
    print("F4_NEW_FIRST_USES=ZERO")

if __name__=="__main__":
    main()
