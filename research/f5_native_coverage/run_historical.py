"""F5 three-arm historical engineering execution, no new F5 cohorts.

Runs source-pinned Y070 on *already-used* F3 engineering seeds and pairs.
Never execute Y070.run(); it internally accesses its own reserved heldout.
The output is a bounded architecture rehearsal, not F5 original science.
"""
import argparse,hashlib,json
from pathlib import Path
from policy import POLICIES
from worker import load_source,evaluate_historical,HISTORICAL_DEV,HISTORICAL_PAIRS,SOURCE_COMMIT

REGIMES=(("steady",None),("onset1",1))
CASES=2*2*4*4*3*3

def run(root):
    source=load_source(root)
    rows=[]
    for pair in HISTORICAL_PAIRS:
        for regime,onset in REGIMES:
            for family in source.FAMILIES:
                for seed in HISTORICAL_DEV:
                    for matching_policy in source.POLICIES:
                        for arm in POLICIES:
                            row=evaluate_historical(source,seed,pair,onset,family,matching_policy,arm)
                            if row["regime"]!=regime:raise ValueError("F5_REGIME_DRIFT")
                            rows.append(row)
    if len(rows)!=CASES:raise ValueError("F5_CASE_COUNT")
    groups={arm:{"cases":0,"pre":0,"post":0,"detections":0,
                 "steady_errors":0,"memory_reprobe_cases":0} for arm in POLICIES}
    for row in rows:
        score=groups[row["arm"]]
        score["cases"]+=1
        score["pre"]+=row["pre_mismatch"]
        score["post"]+=row["post_mismatch"]
        score["detections"]+=int(row["first_detection"] is not None)
        if row["regime"]=="steady":
            score["steady_errors"]+=row["pre_mismatch"]+row["post_mismatch"]
        if set(row["sample_trace"]["addresses"][5])==set(row["sample_trace"]["addresses"][3]):
            score["memory_reprobe_cases"]+=1
    return {
       "schema":"forge.f5.historical-adaptive-coverage-engineering.v1",
       "status":"F3_USED_DATA_ONLY_NOT_PROSPECTIVE_SCIENCE",
       "source_commit":SOURCE_COMMIT,
       "historical_seeds":list(HISTORICAL_DEV),
       "historical_pairs":[list(x) for x in HISTORICAL_PAIRS],
       "arms":list(POLICIES),
       "records":rows,"groups":groups,
       "new_f5_dev_cohort_accesses":0,
       "new_f5_sealed_cohort_accesses":0,
       "first_use_claims_consumed":0,
       "scientific_originals_executed":0,
       "scientific_winner_selected":False,
       "scientific_authority":False
    }

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source-root",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    result=run(args.source_root)
    raw=(json.dumps(result,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    with Path(args.out).open("xb") as file:file.write(raw)
    print("F5_SOURCE_PINNED_HISTORICAL_ENGINEERING=PASS")
    print("F5_HISTORICAL_TRIAL_ARM_RECORDS="+str(len(result["records"])))
    print("F5_HISTORICAL_RECORD_SHA256="+hashlib.sha256(raw).hexdigest())
    print("F5_FIRST_USE=ZERO")
