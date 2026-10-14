"""Independent F4 fixed engineering fixture verifier; no F4 first-use."""
import argparse,json,hashlib
from collections import Counter
from pathlib import Path
from matched_worker import load_pinned,ARMS,F3_DEV_USED,Y070_COMMIT,score_case
from run_matched_fixture import PAIRS,REGIMES,FIXTURE_SEED

def require(x,reason):
    if not x:raise ValueError("F4_INDEPENDENT_"+reason)

def replay(record,ygg_root):
    require(record.get("schema")=="forge.f4.equal-decoder.source-pinned-engineering-fixture.v1","SCHEMA")
    require(record.get("status")=="INSTRUMENTATION_QUALIFIED_NOT_SCIENCE_NOT_COHORT_AUTHORITY","STATUS")
    require(record.get("pinned_source_commit")==Y070_COMMIT,"SOURCE")
    require(record.get("engineering_seed")==FIXTURE_SEED and FIXTURE_SEED in F3_DEV_USED,"SEED")
    require(record.get("new_f4_dev_seeds_used")==0 and record.get("sealed_first_use_claims")==0 and
            record.get("new_scientific_originals")==0 and record.get("science_admitted") is False,"AUTHORITY")
    require(record.get("matched_decoder")=="F4-PUBLIC-DECODER-V1","DECODER")
    require(record.get("arms")=={k:[list(pair) for pair in v] for k,v in ARMS.items()},"CONTROLS")
    require(Counter(sum(record["arms"]["F4-SET"],[]))==
            Counter(sum(record["arms"]["F4-ORDER-CONTROL"],[])),"EQUAL_SENSOR_SET")
    rows=record.get("records")
    require(type(rows) is list and len(rows)==36,"COUNT")
    y=load_pinned(ygg_root)
    totals={arm:{"pre":0,"post":0,"detections":0,"cases":0} for arm in ARMS}
    index=0
    for pair in PAIRS:
        for regime,onset in REGIMES:
            for policy in y.POLICIES:
                for arm in ARMS:
                    row=rows[index];index+=1
                    require(row["regime"]==regime and row["seed"]==FIXTURE_SEED and row["pair"]==list(pair) and
                            row["policy"]==policy and row["family"]==list(y.FAMILIES[0]) and row["arm"]==arm,"CASE_ID")
                    fresh=score_case(y,FIXTURE_SEED,pair,onset,y.FAMILIES[0],policy,arm)
                    for key,value in fresh.items():
                        require(row.get(key)==value,"CAUSAL_METRIC_OR_TRACE")
                    totals[arm]["pre"]+=fresh["pre"]
                    totals[arm]["post"]+=fresh["post"]
                    totals[arm]["detections"]+=int(fresh["first_detection"] is not None)
                    totals[arm]["cases"]+=1
    require(all(x["cases"]==12 for x in totals.values()),"ARM_COUNT")
    return {"schema":"forge.f4.independent-engineering-fixture-review.v1",
            "status":"EQUAL_DECODER_AND_SENSOR_ORDER_ABLATION_REPLAY_PASS",
            "pinned_source_commit":Y070_COMMIT,"replayed":index,"totals":totals,
            "scientific_original":False,"f4_first_use_claims":0,"new_development_cohort_used":False}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--record",required=True)
    p.add_argument("--yggdrasil-root",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    original=Path(a.record).read_bytes()
    witness=replay(json.loads(original),a.yggdrasil_root)
    raw=(json.dumps(witness,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    with Path(a.out).open("xb") as f:f.write(raw)
    print("F4_INDEPENDENT_MATCHED_COMPARATOR_REPLAY=PASS")
    print("F4_VERIFIED_RECORD_SHA256="+hashlib.sha256(original).hexdigest())
    print("F4_WITNESS_SHA256="+hashlib.sha256(raw).hexdigest())
