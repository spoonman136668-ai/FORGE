"""Automatic F6-negative -> F7 early-coverage engineering, no original use.

Reads the actual F6 qualified historical training/validation record and
independent witness, then deterministically selects budget reallocation if
the F6 memory policy made zero rechecks. F7 runs on previously used F3
validation seeds only. No new scientific cohorts or authorization.
"""
import argparse
import hashlib
import json
from pathlib import Path
from policy import POLICIES,OFFSETS,geometry_certificate
from worker import load_source,evaluate,SOURCE_COMMIT,SEEDS,PAIRS

F6_ID="Y-FORGE-F6-UNCERTAINTY-CALIBRATION-PROPOSAL"
F7_ID="Y-FORGE-F7-EARLY-SENSOR-BUDGET-REALLOCATION-PROPOSAL"

def require(value,why):
    if not value:raise ValueError("F7_AUTONOMOUS_"+why)

def canonical(obj):
    return (json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()

def qualify_parent(f6,f6_witness):
    require(f6.get("schema")=="forge.f6.automatic-trained-engineering-evidence.v1"
        and f6.get("status")=="HISTORICAL_F3_USED_ONLY_INDEPENDENT_REVIEW_REQUIRED"
        and f6.get("parent_y070_commit")==SOURCE_COMMIT
        and f6.get("successor_id")==F6_ID,"F6_PARENT_IDENTITY")
    require(f6_witness.get("schema")=="forge.f6.independent-learned-uncertainty-engineering-review.v1"
        and f6_witness.get("status")=="F3_USED_SPLIT_REPLAY_QUALIFIED_NOT_PROSPECTIVE_SCIENCE"
        and f6_witness.get("validation_cases")==96
        and f6_witness.get("validation_summary")==f6.get("validation_summary"),
        "INDEPENDENT_PARENT_REVIEW")
    model=f6.get("model",{})
    require(model.get("schema")=="forge.f6.public-only.calibrated-memory-threshold.v1"
        and model.get("status")=="TRAINED_ON_PREVIOUSLY_USED_F3_DEVELOPMENT_ONLY"
        and model.get("frozen_threshold")==f6_witness.get("learned_threshold")
        and model.get("training_seed_ids")==[67204,67205]
        and model.get("untouched_validation_seed_ids")==list(SEEDS)
        and model.get("scientific_dispatch_authorized") is False,"FROZEN_METHOD")
    v=f6.get("validation_summary",{})
    require(v.get("cases")==96 and v.get("steady_errors")==0
        and v.get("rechecks")==0,"F6_ZERO_RECHECK_NEGATIVE")
    records=f6.get("validation_records")
    require(type(records) is list and len(records)==96,"PARENT_RECORDS")
    require(all(r.get("seed") in SEEDS and r.get("pair") in
            [[8,10],[11,13]] and r.get("arm")=="F6-LEARNED-UNCERTAINTY"
            for r in records),"PARENT_PROVENANCE")
    controls=f6.get("matched_f5_validation_controls",{})
    require(set(controls)=={"F5-COVERAGE","F5-MEMORY"} and
        all(controls[k].get("cases")==96 for k in controls),"PARENT_CONTROLS")
    require(f6.get("new_first_use_claims")==0 and
        f6.get("new_originals")==0 and f6.get("new_cohort_accesses")==0 and
        f6.get("paid_api_calls")==0 and
        f6.get("scientific_authority") is False and
        f6_witness.get("scientific_dispatch_authorized") is False,"NO_AUTHORITY")
    return "F6_MEMORY_INACTIVE_VALIDATED_F3_USED"

def run(f6_raw,review_raw,root):
    parent=json.loads(f6_raw)
    witness=json.loads(review_raw)
    trigger=qualify_parent(parent,witness)
    geometry=geometry_certificate()
    require(geometry["pairs"]==91 and geometry["starts"]==14 and
            geometry["min_visible_starts"]==9 and
            geometry["six_early_and_late_nonanchor_reads"]==6,
            "EARLY_GEOMETRY_CHANGED")
    source=load_source(root)
    rows=[]
    for pair in PAIRS:
        for regime in ("steady","onset1"):
            for family in source.FAMILIES:
                for seed in SEEDS:
                    for matching_policy in source.POLICIES:
                        for arm in POLICIES:
                            rows.append(evaluate(source,seed,pair,regime,
                                                 family,matching_policy,arm))
    require(len(rows)==192,"BOUNDED_REPLAY_CASES")
    totals={arm:{"cases":0,"pre":0,"post":0,"detections":0,
                 "steady_errors":0,"earliest_detection":None} for arm in POLICIES}
    for row in rows:
        data=totals[row["arm"]]
        data["cases"]+=1
        data["pre"]+=row["pre_mismatch"]
        data["post"]+=row["post_mismatch"]
        if row["regime"]=="steady":
            data["steady_errors"]+=row["pre_mismatch"]+row["post_mismatch"]
        first=row["first_detection"]
        data["detections"]+=int(first is not None)
        if first is not None:
            if data["earliest_detection"] is None:
                data["earliest_detection"]=first
            else:data["earliest_detection"]=min(data["earliest_detection"],first)
    require(all(v["cases"]==96 for v in totals.values()),"ARM_BALANCE")
    return {
      "schema":"forge.f7.automatic-f6-negative-to-method-engineering.v1",
      "status":"F3_REUSED_ENGINEERING_SCIENTIFIC_CUSTODY_BLOCKED",
      "parent_f6_evidence_sha256":hashlib.sha256(f6_raw).hexdigest(),
      "parent_f6_independent_review_sha256":hashlib.sha256(review_raw).hexdigest(),
      "parent_trigger":trigger,
      "selected_proposal":F7_ID,
      "method":"budget-neutral early 6-nonanchor public-sensor coverage",
      "public_decoder":"F7-COMMON-PUBLIC-EARLY-V1",
      "source_commit":SOURCE_COMMIT,
      "already_used_f3_validation_seeds":list(SEEDS),
      "already_used_f3_pairs":[list(x) for x in PAIRS],
      "early_public_sensor_offsets":list(OFFSETS),
      "geometry":geometry,
      "arms":list(POLICIES),
      "records":rows,"totals":totals,
      "no_scientific_winner_selected":True,
      "new_originals":0,"new_first_use_claims":0,
      "new_cohort_accesses":0,"paid_api_calls":0,
      "scientific_dispatch_authorized":False
    }

def main():
    p=argparse.ArgumentParser()
    for option in ("f6","f6-review","source-root","out"):
        p.add_argument("--"+option,required=True)
    args=p.parse_args()
    f6_raw=Path(args.f6).read_bytes()
    witness_raw=Path(args.f6_review).read_bytes()
    report=run(f6_raw,witness_raw,args.source_root)
    data=canonical(report)
    with Path(args.out).open("xb") as out:out.write(data)
    print("F7_AUTONOMOUS_FROM_F6_NEGATIVE=PASS")
    print("F7_ALREADY_USED_TRIAL_ARMS="+str(len(report["records"])))
    print("F7_REPLAY_SHA256="+hashlib.sha256(data).hexdigest())
    print("F7_ENGINEERING_RESULTS="+str(report["totals"]))
    print("F7_NEW_SCIENTIFIC_ORIGINALS=ZERO")
if __name__=="__main__":main()
