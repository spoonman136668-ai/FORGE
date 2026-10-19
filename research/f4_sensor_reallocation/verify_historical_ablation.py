"""Independent, source-based F4 *historical engineering* ablation witness.

Recomputes all public-sensor observations and mismatch totals from immutable
Y070, including adversarial trace/metric checks; never accesses new F4 cohorts.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from historical_train import historical_training_cases,learn_coverage,digest_model
from matched_worker import load_pinned,score_case,F3_DEV_USED,ARMS,verify_comparators,Y070_COMMIT
from run_historical_ablation import EXPECTED_CASES,F3_PAIRS,REGIMES

def require(ok,code):
    if not ok:raise ValueError("F4_HISTORICAL_WITNESS_"+code)

def verify(report,root):
    require(report.get("schema")=="forge.f4.historical-equal-decoder-ablation.v1","SCHEMA")
    require(report.get("status")=="F3_REUSED_DEV_ABLATION_ONLY_NO_F4_FIRST_USE","STATUS")
    require(report.get("source_commit")==Y070_COMMIT,"SOURCE")
    require(report.get("historical_validation_seed_ids")==list(F3_DEV_USED),"HISTORICAL_SEEDS")
    require(report.get("f3_dev_pairs")==[list(x) for x in F3_PAIRS],"PAIR_IDENTITY")
    require(report.get("public_decoder")=="F4-PUBLIC-DECODER-V1","EQUAL_DECODER")
    require(all(report.get(key)==0 for key in ("f4_development_cohorts_used","f4_sealed_cohorts_used",
                                              "new_first_use_claims","new_scientific_originals")),"FIRST_USE")
    require(report.get("scientific_winner_selected") is False,"SCIENTIFIC_WINNER")
    model=learn_coverage(historical_training_cases())
    require(report.get("model")==model and report.get("train_seed_ids")==model["training_seed_ids"],"MODEL_RECOMPUTE")
    require(report.get("historical_training_sha256")==digest_model(model),"MODEL_DIGEST")
    controls=verify_comparators()
    expected_arms={name:[list(p) for p in schedule] for name,schedule in controls.items()}
    require(report.get("arms")==expected_arms,"PHYSICAL_CONTROLS")
    require(Counter(sum(expected_arms["F4-SET"],[]))==Counter(sum(expected_arms["F4-ORDER-CONTROL"],[])),
            "MATCHED_SENSOR_MULTISET")
    rows=report.get("records")
    require(type(rows) is list and len(rows)==EXPECTED_CASES,"CASE_COUNT")
    y=load_pinned(root)
    totals={arm:{"pre":0,"post":0,"detections":0,"cases":0,"steady_errors":0} for arm in ARMS}
    per_pair={}
    index=0
    for pair in F3_PAIRS:
        for regime,onset in REGIMES:
            for family in y.FAMILIES:
                for seed in F3_DEV_USED:
                    for policy in y.POLICIES:
                        for arm in ARMS:
                            case=rows[index];index+=1
                            require(case.get("pair")==list(pair) and case.get("regime")==regime
                                    and case.get("family")==list(family) and case.get("seed")==seed
                                    and case.get("policy")==policy and case.get("arm")==arm,
                                    "CASE_IDENTITY")
                            # Replay against original pinned source; do not trust
                            # reported raw traces or summary metrics.
                            recomputed=score_case(y,seed,pair,onset,family,policy,arm)
                            require(all(case.get(k)==v for k,v in recomputed.items()),"TRACE_OR_METRIC_TAMPER")
                            require(case["decoder_identity"]=="F4-PUBLIC-DECODER-V1" and case["reads"]==10,
                                    "BUDGET")
                            total=totals[arm]
                            total["pre"]+=recomputed["pre"]
                            total["post"]+=recomputed["post"]
                            total["detections"]+=int(recomputed["first_detection"] is not None)
                            total["cases"]+=1
                            if regime=="steady":total["steady_errors"]+=recomputed["pre"]+recomputed["post"]
                            name=f"{pair[0]}_{pair[1]}:{regime}:{arm}"
                            if name not in per_pair:
                                per_pair[name]={"pre":0,"post":0,"detections":0,"cases":0}
                            item=per_pair[name]
                            item["pre"]+=recomputed["pre"]
                            item["post"]+=recomputed["post"]
                            item["detections"]+=int(recomputed["first_detection"] is not None)
                            item["cases"]+=1
    require(totals==report.get("totals"),"AGGREGATE_TAMPER")
    require(per_pair==report.get("by_pair_and_regime"),"PAIR_METRIC_TAMPER")
    require(all(score["cases"]==EXPECTED_CASES//3 for score in totals.values()),"CASE_BALANCE")
    return {
        "schema":"forge.f4.independent-historical-three-arm-review.v1",
        "status":"HISTORICAL_ABLATION_REPLAY_QUALIFIED_NOT_NEW_SCIENCE",
        "source_commit":Y070_COMMIT,"records_replayed":index,
        "totals":totals,"by_pair_and_regime":per_pair,
        "new_f4_cohorts_used":0,"new_originals":0,
        "scientific_admission":False,"scientific_winner_selected":False,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--record",required=True)
    p.add_argument("--yggdrasil-root",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    original=Path(a.record).read_bytes()
    witness=verify(json.loads(original),a.yggdrasil_root)
    body=(json.dumps(witness,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    with Path(a.out).open("xb") as f:f.write(body)
    print("F4_HISTORICAL_INDEPENDENT_REPLAY=PASS")
    print("F4_HISTORICAL_VERIFIED_CASES="+str(witness["records_replayed"]))
    print("F4_HISTORICAL_RECORD_SHA256="+hashlib.sha256(original).hexdigest())
    print("F4_HISTORICAL_WITNESS_SHA256="+hashlib.sha256(body).hexdigest())
    print("F4_FIRST_USE_CLAIMS=ZERO")

if __name__=="__main__":
    main()
