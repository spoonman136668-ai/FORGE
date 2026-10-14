"""F7 historical early improvement -> automatic F8 matched-set timing ablation.

Scientific objective: isolate timing from number / identity of observed
physical sensors before interpreting F7 gains. Read only authenticated-
within-workflow source-pinned historical F7 development evidence, never
assign fresh or sealed scientific first-use.
"""
import argparse,hashlib,json
from pathlib import Path
from schedule import ARMS,matched_sets
from worker import load_source,evaluate,SEEDS,PAIRS,SOURCE_COMMIT

SUCCESSOR="Y-FORGE-F8-MATCHED-SENSOR-TIMING-CONTROL-PROPOSAL"
F7_SCHEMA="forge.f7.automatic-f6-negative-to-method-engineering.v1"
F7_REVIEW="forge.f7.independent-public-earliness-engineering-review.v1"

def need(ok,why):
    if not ok:raise ValueError("F8_AUTONOMOUS_"+why)

def canonical(obj):
    return (json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()

def preflight(parent,witness):
    need(parent.get("schema")==F7_SCHEMA and
         parent.get("status")=="F3_REUSED_ENGINEERING_SCIENTIFIC_CUSTODY_BLOCKED" and
         parent.get("source_commit")==SOURCE_COMMIT and
         parent.get("selected_proposal")=="Y-FORGE-F7-EARLY-SENSOR-BUDGET-REALLOCATION-PROPOSAL" and
         parent.get("already_used_f3_validation_seeds")==list(SEEDS) and
         parent.get("already_used_f3_pairs")==[list(p) for p in PAIRS] and
         parent.get("new_originals")==0 and parent.get("new_first_use_claims")==0 and
         parent.get("new_cohort_accesses")==0 and parent.get("paid_api_calls")==0 and
         parent.get("scientific_dispatch_authorized") is False and
         parent.get("no_scientific_winner_selected") is True,"F7_PROVENANCE")
    need(witness.get("schema")==F7_REVIEW and
         witness.get("status")=="F3_REUSED_REAL_SOURCE_REPLAY_PASS_NOT_SCIENCE" and
         witness.get("replayed_trial_arms")==192 and
         witness.get("new_first_use_claims")==0 and
         witness.get("scientific_originals")==0 and
         witness.get("scientific_dispatch_authorized") is False and
         witness.get("totals")==parent.get("totals"),"F7_INDEPENDENT_REVIEW")
    c=parent["totals"].get("F7-REPLAY-F5-COVERAGE",{})
    e=parent["totals"].get("F7-EARLY-SIX-COVERAGE",{})
    need(c.get("cases")==e.get("cases")==96 and
         c.get("pre")+c.get("post")==91 and
         e.get("pre")+e.get("post")==74 and
         c.get("earliest_detection")==5 and
         e.get("earliest_detection")==3 and
         c.get("steady_errors")==e.get("steady_errors")==0,"HISTORICAL_EARLY_GAIN")
    need(type(parent.get("records")) is list and len(parent["records"])==192,
         "F7_RECORD_COUNT")
    need(all(row.get("seed") in SEEDS and row.get("pair") in [list(p) for p in PAIRS]
             for row in parent["records"]),"HISTORICAL_COHORT")
    return "F7_EARLY_GAIN_COULD_BE_SENSOR_COUNT_OR_TIMING"

def run(parent_bytes,witness_bytes,root):
    parent=json.loads(parent_bytes)
    witness=json.loads(witness_bytes)
    rationale=preflight(parent,witness)
    source=load_source(root)
    records=[]
    for pair in PAIRS:
        for regime in ("steady","onset1"):
            for family in source.FAMILIES:
                for seed in SEEDS:
                    for policy in source.POLICIES:
                        two=[evaluate(source,seed,pair,regime,family,policy,arm)
                             for arm in ARMS]
                        matched_sets(two[0]["sample_trace"]["budget"],
                                     two[1]["sample_trace"]["budget"])
                        records.extend(two)
    need(len(records)==192,"CASE_COUNT")
    groups={name:{"cases":0,"pre":0,"post":0,"detections":0,
                  "steady_errors":0,"earliest_detection":None} for name in ARMS}
    for row in records:
        dest=groups[row["arm"]]
        dest["cases"]+=1
        dest["pre"]+=row["pre_mismatch"]
        dest["post"]+=row["post_mismatch"]
        dest["detections"]+=int(row["first_detection"] is not None)
        if row["regime"]=="steady":
            dest["steady_errors"]+=row["pre_mismatch"]+row["post_mismatch"]
        t=row["first_detection"]
        if t is not None:
            dest["earliest_detection"]=t if dest["earliest_detection"] is None else min(t,dest["earliest_detection"])
    need(all(v["cases"]==96 for v in groups.values()),"ARM_BALANCE")
    return {
        "schema":"forge.f8.automatic-f7-matched-timing-engineering.v1",
        "status":"PREVIOUSLY_USED_F3_ONLY_NOT_FROZEN_SCIENCE",
        "parent_f7_sha256":hashlib.sha256(parent_bytes).hexdigest(),
        "parent_f7_independent_sha256":hashlib.sha256(witness_bytes).hexdigest(),
        "parent_mechanism_uncertainty":rationale,
        "selected_proposal":SUCCESSOR,
        "source_commit":SOURCE_COMMIT,
        "used_development_seeds":list(SEEDS),
        "used_pairs":[list(x) for x in PAIRS],
        "arms":list(ARMS),
        "matched_physical_sensor_sets":True,
        "equal_public_decoder":"F7-COMMON-PUBLIC-EARLY-V1",
        "public_scalar_reads":10,
        "records":records,
        "groups":groups,
        "winner_selected":False,
        "new_development_or_sealed_uses":0,
        "new_originals":0,
        "new_first_use_claims":0,
        "paid_api_calls":0,
        "scientific_dispatch_authorized":False
    }

def main():
    p=argparse.ArgumentParser()
    for field in ("parent","witness","source-root","out"):
        p.add_argument("--"+field,required=True)
    a=p.parse_args()
    raw=canonical(run(Path(a.parent).read_bytes(),Path(a.witness).read_bytes(),a.source_root))
    with Path(a.out).open("xb") as fd:fd.write(raw)
    print("F8_F7_RESULT_TO_AUTOMATIC_TIMING_ABLATION=PASS")
    print("F8_ARCHIVE_SHA256="+hashlib.sha256(raw).hexdigest())
    print("F8_NEW_FIRST_USE=ZERO")
if __name__=="__main__":main()
