"""F4 matched-decoder engineering fixture on PREVIOUSLY USED F3 development seeds.

Not F4 development training, not F4 result, not a prospective scientific
trial, no new first-use claim. Qualification only of equal decoder/sensor
identity contrast under immutable Y070 source.
"""
import argparse,hashlib,json
from pathlib import Path
from matched_worker import (
    load_pinned,score_case,ARMS,CONTROL,SET_FIXTURE,ORDER_FIXTURE,Y070_COMMIT,
    F3_DEV_USED,verify_comparators
)

PAIRS=((8,10),(11,13))
REGIMES=(("steady",None),("onset1",1))
# Exactly 36 cases, one F3 already-used development seed and one original family.
FIXTURE_SEED=F3_DEV_USED[0]
def run(root):
    y=load_pinned(root)
    verify_comparators()
    results=[]
    family=y.FAMILIES[0]
    for pair in PAIRS:
        for regime,onset in REGIMES:
            for policy in y.POLICIES:
                for arm in ARMS:
                    row=score_case(y,FIXTURE_SEED,pair,onset,family,policy,arm)
                    row["regime"]=regime
                    results.append(row)
    if len(results)!=36:
        raise ValueError("F4_ENGINEERING_FIXTURE_COUNT")
    if any(row["reads"]!=10 for row in results):
        raise ValueError("F4_ENGINEERING_READ_BUDGET")
    return {
        "schema":"forge.f4.equal-decoder.source-pinned-engineering-fixture.v1",
        "status":"INSTRUMENTATION_QUALIFIED_NOT_SCIENCE_NOT_COHORT_AUTHORITY",
        "pinned_source_commit":Y070_COMMIT,
        "seed_identity":"F3_PREVIOUSLY_USED_DEVELOPMENT_ONLY",
        "engineering_seed":FIXTURE_SEED,
        "matched_decoder":"F4-PUBLIC-DECODER-V1",
        "protocol_original_id":"Y-FORGE-F4-SENSOR-SET-REALLOCATION-01",
        "arms":{arm:[list(pair) for pair in schedule] for arm,schedule in ARMS.items()},
        "records":results,
        "new_f4_dev_seeds_used":0,
        "sealed_first_use_claims":0,
        "new_scientific_originals":0,
        "science_admitted":False
    }

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--yggdrasil-root",required=True)
    p.add_argument("--out",required=True)
    options=p.parse_args()
    record=run(options.yggdrasil_root)
    encoded=(json.dumps(record,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    with Path(options.out).open("xb") as f:f.write(encoded)
    print("F4_MATCHED_DECODER_REAL_SOURCE_ENGINEERING=PASS")
    print("F4_MATCHED_DECODER_CASES=36")
    print("F4_RECORD_SHA256="+hashlib.sha256(encoded).hexdigest())
    print("F4_FIRST_USES=ZERO")
