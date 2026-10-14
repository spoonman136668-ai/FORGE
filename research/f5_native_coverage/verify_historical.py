"""Independent F5 source-pinned audit of historical adaptive coverage evidence.

Recomputes every trial from pristine pinned Y070, not just submitted scores;
verifies observed sensor address trace, memory bounds, and all no-first-use
claims. This is an engineering witness, NOT independent F5 sealed science.
"""
import argparse,hashlib,json
from pathlib import Path
from policy import POLICIES,PROBES
from worker import load_source,evaluate_historical,HISTORICAL_DEV,HISTORICAL_PAIRS,SOURCE_COMMIT
from run_historical import REGIMES,CASES

def need(ok,msg):
    if not ok:raise ValueError("F5_INDEPENDENT_"+msg)

def replay(record,root):
    need(record.get("schema")=="forge.f5.historical-adaptive-coverage-engineering.v1","SCHEMA")
    need(record.get("status")=="F3_USED_DATA_ONLY_NOT_PROSPECTIVE_SCIENCE","STATUS")
    need(record.get("source_commit")==SOURCE_COMMIT,"SOURCE")
    need(record.get("historical_seeds")==list(HISTORICAL_DEV),"SEEDS")
    need(record.get("historical_pairs")==[list(x) for x in HISTORICAL_PAIRS],"PAIRS")
    need(record.get("arms")==list(POLICIES),"POLICIES")
    need(record.get("new_f5_dev_cohort_accesses")==0 and
         record.get("new_f5_sealed_cohort_accesses")==0 and
         record.get("first_use_claims_consumed")==0 and
         record.get("scientific_originals_executed")==0,"CLAIM_BOUNDARY")
    need(record.get("scientific_authority") is False and
         record.get("scientific_winner_selected") is False,"AUTHORITY")
    rows=record.get("records")
    need(type(rows) is list and len(rows)==CASES,"ROW_COUNT")
    source=load_source(root)
    out={arm:{"cases":0,"pre":0,"post":0,"detections":0,
              "steady_errors":0,"memory_reprobe_cases":0} for arm in POLICIES}
    n=0
    for pair in HISTORICAL_PAIRS:
        for regime,onset in REGIMES:
            for family in source.FAMILIES:
                for seed in HISTORICAL_DEV:
                    for matching_policy in source.POLICIES:
                        for arm in POLICIES:
                            observed=rows[n];n+=1
                            need(observed["pair"]==list(pair) and observed["regime"]==regime
                                 and observed["family"]==list(family) and observed["seed"]==seed
                                 and observed["matching_policy"]==matching_policy and observed["arm"]==arm,
                                 "IDENTITY")
                            reference=evaluate_historical(source,seed,pair,onset,family,matching_policy,arm)
                            need(observed==reference,"METRIC_OR_PUBLIC_READ_TAMPER")
                            need(observed["decoder"]=="F5-GENERALIZED-PUBLIC-V1" and
                                 observed["public_reads"]==10,"BUDGET")
                            trace=observed["sample_trace"]
                            need(len(trace["addresses"])==len(PROBES),"TRACE_SHAPE")
                            score=out[arm]
                            score["cases"]+=1
                            score["pre"]+=reference["pre_mismatch"]
                            score["post"]+=reference["post_mismatch"]
                            score["detections"]+=int(reference["first_detection"] is not None)
                            if regime=="steady":
                                score["steady_errors"]+=reference["pre_mismatch"]+reference["post_mismatch"]
                            if set(trace["addresses"][5])==set(trace["addresses"][3]):
                                score["memory_reprobe_cases"]+=1
    need(out==record.get("groups"),"GROUP_METRIC_TAMPER")
    need(all(x["cases"]==CASES//len(POLICIES) for x in out.values()),"BALANCE")
    return {
      "schema":"forge.f5.independent-historical-engineering-review.v1",
      "status":"HISTORICAL_SOURCE_REPLAY_ONLY_NO_NEW_FIRST_USE",
      "source_commit":SOURCE_COMMIT,
      "replayed_records":n,"groups":out,
      "new_f5_cohort_accesses":0,
      "first_use_claims_consumed":0,
      "scientific_authority":False
    }

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--record",required=True)
    p.add_argument("--source-root",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    original=Path(args.record).read_bytes()
    witness=replay(json.loads(original),args.source_root)
    raw=(json.dumps(witness,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    with Path(args.out).open("xb") as f:f.write(raw)
    print("F5_INDEPENDENT_PUBLIC_SOURCE_REPLAY=PASS")
    print("F5_VERIFIED_CASES="+str(witness["replayed_records"]))
    print("F5_RECORD_SHA256="+hashlib.sha256(original).hexdigest())
    print("F5_WITNESS_SHA256="+hashlib.sha256(raw).hexdigest())
    print("F5_FIRST_USE=ZERO")
