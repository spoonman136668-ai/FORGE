"""F7 independent source replay and geometry-only feasibility witness.

Replays all real Y070 public trial values, active/retained matching metrics,
exact cohort identities, and the automatic F6-negative trigger. The
independent reviewer does not initiate an original or allocate new seeds.
"""
import argparse
import hashlib
import json
from itertools import combinations
from pathlib import Path
from policy import POLICIES,OFFSETS,select,verify_observations
from worker import load_source,evaluate,SEEDS,PAIRS,SOURCE_COMMIT
from advance import require,qualify_parent,canonical

def independently_prove_geometry(report):
    # Independently rederive worst-case coverage from translated pair
    # exposure sets rather than using the producer's geometry function.
    def worst(offsets):
        minimum=14
        for a,b in combinations(range(14),2):
            count=sum(
                1 for rotation in range(14)
                if any((rotation+x)%14==a or (rotation+x)%14==b
                       for x in offsets))
            minimum=min(minimum,count)
        return minimum
    actual=worst(OFFSETS)
    max_all=max(worst((0,)+rest) for rest in combinations(range(1,14),5))
    require(actual==9 and max_all==9,"F7_EARLY_GEOMETRY_NOT_MINIMAX")
    require(report=={
        "pairs":91,"starts":14,"min_visible_starts":9,
        "max_visible_starts":11,
        "mean_visible_starts_numerator":126*7,
        "six_early_and_late_nonanchor_reads":6,
        "ten_scalar_reads":10
    },"F7_GEOMETRY_SUMMARY")
    return max_all

def verify(report,f6_raw,review_raw,root):
    parent=json.loads(f6_raw)
    f6_witness=json.loads(review_raw)
    trigger=qualify_parent(parent,f6_witness)
    require(report.get("schema")=="forge.f7.automatic-f6-negative-to-method-engineering.v1"
        and report.get("status")=="F3_REUSED_ENGINEERING_SCIENTIFIC_CUSTODY_BLOCKED"
        and report.get("parent_f6_evidence_sha256")==hashlib.sha256(f6_raw).hexdigest()
        and report.get("parent_f6_independent_review_sha256")==
            hashlib.sha256(review_raw).hexdigest()
        and report.get("parent_trigger")==trigger
        and report.get("selected_proposal")==
            "Y-FORGE-F7-EARLY-SENSOR-BUDGET-REALLOCATION-PROPOSAL"
        and report.get("source_commit")==SOURCE_COMMIT
        and report.get("already_used_f3_validation_seeds")==list(SEEDS)
        and report.get("already_used_f3_pairs")==[list(x) for x in PAIRS]
        and report.get("early_public_sensor_offsets")==list(OFFSETS)
        and report.get("arms")==list(POLICIES)
        and report.get("public_decoder")=="F7-COMMON-PUBLIC-EARLY-V1",
        "CHAIN_IDENTITIES")
    max_worst=independently_prove_geometry(report.get("geometry"))
    source=load_source(root)
    rows=report.get("records")
    require(type(rows) is list and len(rows)==192,"RECORD_COUNT")
    total={arm:{"cases":0,"pre":0,"post":0,"detections":0,
                 "steady_errors":0,"earliest_detection":None}
           for arm in POLICIES}
    pos=0
    for pair in PAIRS:
        for regime in ("steady","onset1"):
            for family in source.FAMILIES:
                for seed in SEEDS:
                    for match_policy in source.POLICIES:
                        for arm in POLICIES:
                            item=rows[pos];pos+=1
                            require(item.get("seed")==seed and
                                item.get("pair")==list(pair) and
                                item.get("regime")==regime and
                                item.get("family")==list(family) and
                                item.get("matching_policy")==match_policy and
                                item.get("arm")==arm,"CASE_IDENTITY")
                            expected=evaluate(source,seed,pair,regime,
                                              family,match_policy,arm)
                            require(expected==item,"MEASUREMENTS_OR_TRACE_TAMPER")
                            trace=item["sample_trace"]
                            readings={}
                            for time,addresses,values in zip(
                                (0,1,3,5,7),
                                trace["addresses"],trace["public_values"]):
                                require(type(addresses) is list and
                                        len(addresses)==2 and
                                        type(values) is list and
                                        len(values)==2,"RAW_TRACE")
                                readings[time]=dict(zip(addresses,values))
                            require(verify_observations(arm,readings)==
                                    trace["coverage"],"CAUSAL_TRACE")
                            stats=total[arm]
                            stats["cases"]+=1
                            stats["pre"]+=item["pre_mismatch"]
                            stats["post"]+=item["post_mismatch"]
                            stats["detections"]+=int(item["first_detection"] is not None)
                            if regime=="steady":
                                stats["steady_errors"]+=item["pre_mismatch"]+item["post_mismatch"]
                            first=item["first_detection"]
                            if first is not None:
                                stats["earliest_detection"]=(first if stats["earliest_detection"] is None
                                   else min(stats["earliest_detection"],first))
    require(total==report.get("totals"),"METRICS")
    require(all(x["cases"]==96 for x in total.values()),"CASE_BALANCE")
    require(report.get("no_scientific_winner_selected") is True and
        report.get("scientific_dispatch_authorized") is False and
        all(report.get(k)==0 for k in (
            "new_originals","new_first_use_claims","new_cohort_accesses","paid_api_calls")),
        "SCIENCE_AUTHORITY")
    return {
      "schema":"forge.f7.independent-public-earliness-engineering-review.v1",
      "status":"F3_REUSED_REAL_SOURCE_REPLAY_PASS_NOT_SCIENCE",
      "replayed_trial_arms":pos,
      "max_possible_six_offset_worst_coverage":max_worst,
      "totals":total,
      "new_first_use_claims":0,
      "scientific_originals":0,
      "scientific_dispatch_authorized":False
    }

def main():
    p=argparse.ArgumentParser()
    for option in ("f7","f6","f6-review","source-root","out"):
        p.add_argument("--"+option,required=True)
    args=p.parse_args()
    raw=Path(args.f7).read_bytes()
    result=verify(json.loads(raw),Path(args.f6).read_bytes(),
                  Path(args.f6_review).read_bytes(),args.source_root)
    encoded=canonical(result)
    with Path(args.out).open("xb") as fd:fd.write(encoded)
    print("F7_INDEPENDENT_PUBLIC_SENSING_REAL_SOURCE=PASS")
    print("F7_REPLAYED_TRIAL_ARMS="+str(result["replayed_trial_arms"]))
    print("F7_WITNESS_SHA256="+hashlib.sha256(encoded).hexdigest())
    print("F7_NEW_SCIENTIFIC_FIRST_USE=ZERO")
if __name__=="__main__":main()
