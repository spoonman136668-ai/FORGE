"""F5 engineering evidence -> automatic, non-authorizing successor proposal.

Triggered after the existing source-pinned historical worker and independent
replay. No new controller. No candidate method tuning, science execution,
first-use claim, sealed-data access, or paid model/API calls.
"""
import argparse
import hashlib
import json
from pathlib import Path

PARENT_SOURCE="5797a257a75fe139313e8486cd1a1ae79c44b148"
ARMS=("F5-FIXED","F5-COVERAGE","F5-MINIMAX","F5-MEMORY")
SEEDS=(67204,67205,67206,67207)
PAIRS=((8,10),(11,13))
RULES=("PUBLIC_MEMORY_RECHECK_NO_GAIN",
       "WORST_CASE_GEOMETRY_VS_HISTORICAL_TRADEOFF",
       "HISTORICAL_EVIDENCE_NOT_DECISIVE")

def require(ok,code):
    if not ok:raise ValueError("F5_SUCCESSOR_"+code)

def canonical(data):
    return (json.dumps(data,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def load(raw):
    def pairs_unique(pairs):
        x={}
        for key,val in pairs:
            require(key not in x,"DUPLICATE_JSON_KEY")
            x[key]=val
        return x
    return json.loads(raw,object_pairs_hook=pairs_unique,
                      parse_constant=lambda _:require(False,"NONFINITE_JSON"))

def recompute_groups(record):
    # Reject report-only totals. Recalculate the 4-arm summaries from
    # exactly 768 historical trial rows that the separate real-source
    # evaluator has already replayed in this workflow.
    require(record.get("schema")=="forge.f5.historical-adaptive-coverage-engineering.v1","RECORD_SCHEMA")
    require(record.get("status")=="F3_USED_DATA_ONLY_NOT_PROSPECTIVE_SCIENCE","RECORD_AUTHORITY")
    require(record.get("source_commit")==PARENT_SOURCE,"SOURCE")
    require(record.get("historical_seeds")==list(SEEDS),"REUSED_F3_SEEDS")
    require(record.get("historical_pairs")==[list(x) for x in PAIRS],"REUSED_F3_PAIRS")
    require(record.get("arms")==list(ARMS),"ARM_ORDER")
    require(record.get("scientific_authority") is False and
            record.get("scientific_winner_selected") is False and
            record.get("new_f5_dev_cohort_accesses")==0 and
            record.get("new_f5_sealed_cohort_accesses")==0 and
            record.get("first_use_claims_consumed")==0 and
            record.get("scientific_originals_executed")==0,"NO_ORIGINAL")
    rows=record.get("records")
    require(type(rows) is list and len(rows)==768,"CASE_COUNT")
    groups={arm:{"cases":0,"pre":0,"post":0,"detections":0,
                 "steady_errors":0,"memory_reprobe_cases":0} for arm in ARMS}
    seen=set()
    for row in rows:
        require(type(row) is dict,"ROW")
        arm=row.get("arm")
        require(arm in ARMS and type(row.get("seed")) is int
                and row["seed"] in SEEDS,"ROW_IDENTITY")
        pair=row.get("pair")
        require(type(pair) is list and tuple(pair) in PAIRS,"ROW_PAIR")
        regime=row.get("regime")
        require(regime in ("steady","onset1"),"REGIME")
        family=row.get("family")
        require(type(family) is list and len(family)==3 and
                all(type(v) is int for v in family),"SOURCE_FAMILY")
        policy=row.get("matching_policy")
        require(type(policy) is str and policy,"MATCHING_POLICY")
        key=(arm,row["seed"],tuple(pair),regime,tuple(family),policy)
        require(key not in seen,"REPLAY_OR_DUPLICATE_CASE")
        seen.add(key)
        pre,post=row.get("pre_mismatch"),row.get("post_mismatch")
        require(type(pre) is int and type(post) is int and 0<=pre<=8
                and 0<=post<=8,"MISMATCH_METRIC")
        require(row.get("public_reads")==10 and
                row.get("decoder")=="F5-GENERALIZED-PUBLIC-V1","COST_OR_DECODER")
        sample=row.get("sample_trace")
        require(type(sample) is dict and type(sample.get("addresses")) is list
                and len(sample["addresses"])==5,"READ_TRACE")
        trace=sample["addresses"]
        require(all(type(pair) is list and len(pair)==2 and
                    len(set(pair))==2 and
                    all(type(c) is int and 0<=c<16 for c in pair)
                    for pair in trace),"READ_TRACE_SHAPE")
        require(row.get("first_detection") in (None,5,7),"DETECTION")
        if regime=="steady":
            require(row["first_detection"] is None,"STEADY_FALSE_DETECTION")
        score=groups[arm]
        score["cases"]+=1
        score["pre"]+=pre
        score["post"]+=post
        score["detections"]+=int(row["first_detection"] is not None)
        if regime=="steady":score["steady_errors"]+=pre+post
        if set(trace[3])==set(trace[4]):score["memory_reprobe_cases"]+=1
    require(all(g["cases"]==192 for g in groups.values()),"ARM_BALANCE")
    require(groups==record.get("groups"),"FORGED_SUMMARY")
    return groups

def prepare(record_bytes,witness_bytes,geometry_bytes,options_bytes):
    record=load(record_bytes)
    witness=load(witness_bytes)
    geometry=load(geometry_bytes)
    opts=load(options_bytes)
    groups=recompute_groups(record)
    require(witness.get("schema")=="forge.f5.independent-historical-engineering-review.v1"
            and witness.get("status")=="HISTORICAL_SOURCE_REPLAY_ONLY_NO_NEW_FIRST_USE"
            and witness.get("source_commit")==PARENT_SOURCE
            and witness.get("replayed_records")==768
            and witness.get("groups")==groups
            and witness.get("new_f5_cohort_accesses")==0
            and witness.get("first_use_claims_consumed")==0
            and witness.get("scientific_authority") is False,"WITNESS")
    require(geometry.get("schema")=="forge.f5.public-coverage-geometry.v1"
            and geometry.get("status")=="SOURCE_ONLY_NO_NEW_SCIENTIFIC_DATA"
            and geometry.get("baseline_offsets")==[0,1,5,10]
            and geometry.get("optimal_offsets")==[0,1,4,6]
            and geometry.get("baseline",{}).get("worst_pair_exposure")==5
            and geometry.get("optimal",{}).get("worst_pair_exposure")==7
            and geometry.get("nonanchor_pair_count")==91
            and geometry.get("enumerated_offset_patterns")==286
            and geometry.get("new_first_use_claims")==0
            and geometry.get("prospective_scientific_execution_authorized") is False,
            "GEOMETRY")
    require(opts.get("schema")=="forge.f5.historical-successor-options.v1"
            and opts.get("status")=="ENGINEERING_ONLY_PREDECLARED_BEFORE_NEW_COHORT_USE"
            and opts.get("parent",{}).get("immutable_source")==PARENT_SOURCE
            and opts.get("parent",{}).get("expected_replay_records")==768
            and opts.get("limit")=={"max_prepared_successors":1,
               "science_launches":0,"new_seed_allocations":0,
               "first_use_claims":0,"paid_api_calls":0},"CATALOGUE_LIMIT")
    pool=opts.get("hypotheses")
    require(type(pool) is list and len(pool)==3 and
            [x.get("rule") for x in pool]==list(RULES) and
            [x.get("rank") for x in pool]==[1,2,3] and
            len({x.get("id") for x in pool})==3,"CATALOGUE")
    coverage=groups["F5-COVERAGE"]
    memory=groups["F5-MEMORY"]
    minimax=groups["F5-MINIMAX"]
    if memory["memory_reprobe_cases"]>0 and (
            memory["pre"]+memory["post"]>=coverage["pre"]+coverage["post"]):
        index=0
    elif minimax["pre"]+minimax["post"]>coverage["pre"]+coverage["post"]:
        index=1
    else:
        index=2
    selected=pool[index]
    facts={
        "coverage_historical_total":coverage["pre"]+coverage["post"],
        "memory_historical_total":memory["pre"]+memory["post"],
        "minimax_historical_total":minimax["pre"]+minimax["post"],
        "memory_reprobe_cases":memory["memory_reprobe_cases"],
        "geometry_worst_coverage":5,
        "geometry_worst_minimax":7
    }
    return {
      "schema":"forge.f5.automatic-evidence-to-successor-proposal.v1",
      "disposition":"SUCCESSOR_PREPARED_CUSTODY_BLOCKED_NO_ORIGINAL",
      "lane":"Yggdrasil",
      "parent_status":"HISTORICAL_REUSED_F3_ENGINEERING_ONLY",
      "parent_source_commit":PARENT_SOURCE,
      "evidence_sha256":{"record":sha(record_bytes),"independent_replay":sha(witness_bytes),
                         "geometry":sha(geometry_bytes),"frozen_options":sha(options_bytes)},
      "selection_rule":selected["rule"],
      "selected":{"proposal_id":selected["id"],"hypothesis":selected["hypothesis"],
                  "reason":selected["reason"],"next_action":selected["next_action"]},
      "considered_ids":[x["id"] for x in pool],
      "evidence_facts":facts,
      "not_a_scientific_winner":True,
      "unverified_first_use_ledger":"BLOCKED",
      "new_seed_allocations":0,
      "new_scientific_originals":0,
      "new_first_use_claims":0,
      "source_or_accepted_ref_changes":0,
      "paid_api_calls":0,
      "scientific_dispatch_authorized":False,
      "successor_ready_for_autonomous_method_engineering":True
    }

def main():
    parser=argparse.ArgumentParser()
    for x in ("record","witness","geometry","options","out"):
        parser.add_argument("--"+x,required=True)
    a=parser.parse_args()
    arguments=[Path(getattr(a,p)).read_bytes() for p in
               ("record","witness","geometry","options")]
    report=prepare(*arguments)
    with Path(a.out).open("xb") as fd:fd.write(canonical(report))
    print("F5_AUTOMATIC_REPLAY_TO_SUCCESSOR=PASS")
    print("F5_SUCCESSOR_ID="+report["selected"]["proposal_id"])
    print("F5_NEW_FIRST_USE=ZERO")
    print("F5_SCIENTIFIC_DISPATCH=BLOCKED")
if __name__=="__main__":main()
