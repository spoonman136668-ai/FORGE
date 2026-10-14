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
    # Independent reconstruction of the historical, previously-used F3
    # training-only two-cell maximum-coverage choice; no F4 cohort access.
    model=record.get("historical_training")
    require(type(model) is dict and model.get("schema")=="forge.f4.historical-training-only-rehearsal.v1","TRAINING_SCHEMA")
    require(model.get("status")=="MECHANISM_REHEARSAL_F3_USED_LABELS_ONLY_NOT_F4_TRAINING","TRAINING_AUTHORITY")
    require(model.get("training_seed_ids")==[67200,67201,67202,67203],"TRAINING_SEEDS")
    require(model.get("historical_pair_labels")==[[8,10],[11,13],[8,10],[11,13]],"TRAINING_LABELS")
    require(model.get("method")=="train_label_maximum_cover_greedy_lex_tie","TRAINING_ALGORITHM")
    expected_pairs=((8,10),(11,13),(8,10),(11,13))
    uncovered=set(range(4))
    selected=[]
    for _ in range(2):
        candidates=[]
        for address in range(2,16):
            if address in selected:continue
            gain=sum(i in uncovered and address in pair for i,pair in enumerate(expected_pairs))
            candidates.append((-gain,address))
        loss,address=min(candidates)
        require(loss<0,"NO_TRAINING_COVERAGE")
        selected.append(address)
        uncovered={i for i in uncovered if address not in expected_pairs[i]}
    inferred=[[0,1],[0,1],[0,1],selected,[0,1]]
    ablation=[[0,1],[0,1],[0,1],[0,1],selected]
    require(model.get("learned_physical_sensors")==selected,"LEARNED_SENSOR_SET")
    require(model.get("set_schedule")==inferred and model.get("order_control_schedule")==ablation,"LEARNED_SCHEDULE")
    require(model.get("read_budget")==10 and model.get("f4_development_seeds_consumed")==0 and
            model.get("sealed_first_uses")==0 and model.get("scientific_originals")==0 and
            model.get("science_admitted") is False and model.get("inference_uses_hidden_pair") is False,
            "TRAINING_LEAK_OR_AUTHORITY")
    model_raw=(json.dumps(model,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    require(hashlib.sha256(model_raw).hexdigest()==record.get("historical_training_sha256"),"TRAINING_HASH")

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
