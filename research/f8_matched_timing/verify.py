"""Independent F8 causal timing-vs-sensor-set attribution audit.

Recreates every matched trial directly in pinned Y070 and independently
checks all public observation values, timestamps, per-case matched physical
sets, error counts and unchanged scientific admission boundary.
"""
import argparse,hashlib,json
from pathlib import Path
from schedule import ARMS,EPISODES,choose,validate_trace,matched_sets
from worker import load_source,evaluate,SEEDS,PAIRS,SOURCE_COMMIT

def need(ok,reason):
    if not ok:raise ValueError("F8_INDEPENDENT_"+reason)

def check(report,parent_raw,witness_raw,root):
    parent=json.loads(parent_raw);witness=json.loads(witness_raw)
    need(report.get("schema")=="forge.f8.automatic-f7-matched-timing-engineering.v1"
        and report.get("status")=="PREVIOUSLY_USED_F3_ONLY_NOT_FROZEN_SCIENCE"
        and report.get("parent_f7_sha256")==hashlib.sha256(parent_raw).hexdigest()
        and report.get("parent_f7_independent_sha256")==hashlib.sha256(witness_raw).hexdigest()
        and parent.get("source_commit")==SOURCE_COMMIT
        and parent.get("already_used_f3_validation_seeds")==list(SEEDS)
        and parent.get("new_first_use_claims")==0
        and witness.get("status")=="F3_REUSED_REAL_SOURCE_REPLAY_PASS_NOT_SCIENCE"
        and witness.get("replayed_trial_arms")==192
        and witness.get("totals")==parent.get("totals")
        and report.get("parent_mechanism_uncertainty")==
            "F7_EARLY_GAIN_COULD_BE_SENSOR_COUNT_OR_TIMING"
        and report.get("selected_proposal")==
            "Y-FORGE-F8-MATCHED-SENSOR-TIMING-CONTROL-PROPOSAL"
        and report.get("source_commit")==SOURCE_COMMIT
        and report.get("used_development_seeds")==list(SEEDS)
        and report.get("used_pairs")==[list(x) for x in PAIRS]
        and report.get("arms")==list(ARMS)
        and report.get("matched_physical_sensor_sets") is True
        and report.get("equal_public_decoder")=="F7-COMMON-PUBLIC-EARLY-V1"
        and report.get("public_scalar_reads")==10,"IDENTITY")
    rows=report.get("records")
    need(type(rows) is list and len(rows)==192,"CASE_COUNT")
    source=load_source(root)
    totals={a:{"cases":0,"pre":0,"post":0,"detections":0,
               "steady_errors":0,"earliest_detection":None} for a in ARMS}
    index=0
    for pair in PAIRS:
        for regime in ("steady","onset1"):
            for family in source.FAMILIES:
                for seed in SEEDS:
                    for policy in source.POLICIES:
                        observed=[]
                        for arm in ARMS:
                            row=rows[index];index+=1
                            need(row.get("seed")==seed and
                                 row.get("pair")==list(pair) and
                                 row.get("regime")==regime and
                                 row.get("family")==list(family) and
                                 row.get("matching_policy")==policy and
                                 row.get("arm")==arm,"CASE_IDENTITY")
                            expected=evaluate(source,seed,pair,regime,family,policy,arm)
                            need(row==expected,"SOURCE_REPLAY_OR_VALUE_TAMPER")
                            trace=row["sample_trace"]
                            observed_history={}
                            for t,addresses,values in zip(
                                EPISODES,trace["addresses"],trace["public_values"]):
                                need(type(addresses) is list and len(addresses)==2 and
                                     type(values) is list and len(values)==2,
                                     "TRACE_SHAPE")
                                historical=dict(zip(addresses,values))
                                decision=choose(arm,t,observed_history)
                                need(tuple(addresses)==decision,"FUTURE_ORACLE_ADDRESS")
                                observed_history[t]=historical
                            need(validate_trace(arm,observed_history)==trace["budget"],
                                 "BUDGET_OR_TIMING")
                            observed.append(row)
                            stats=totals[arm]
                            stats["cases"]+=1
                            stats["pre"]+=row["pre_mismatch"]
                            stats["post"]+=row["post_mismatch"]
                            first=row["first_detection"]
                            stats["detections"]+=int(first is not None)
                            if regime=="steady":
                                stats["steady_errors"]+=row["pre_mismatch"]+row["post_mismatch"]
                            if first is not None:
                                stats["earliest_detection"]=(first if stats["earliest_detection"] is None
                                                             else min(first,stats["earliest_detection"]))
                        need(matched_sets(observed[0]["sample_trace"]["budget"],
                                          observed[1]["sample_trace"]["budget"]),
                             "MATCHED_PHYSICAL_CELLS")
    need(totals==report.get("groups"),"TAMPERED_SUMMARY")
    need(all(x["cases"]==96 for x in totals.values()),"BALANCE")
    need(report.get("winner_selected") is False and
         report.get("scientific_dispatch_authorized") is False and
         all(report.get(k)==0 for k in (
             "new_development_or_sealed_uses","new_originals",
             "new_first_use_claims","paid_api_calls")),"FALSE_SCIENTIFIC_AUTHORITY")
    return {"schema":"forge.f8.independent-matched-sensor-timing-review.v1",
            "status":"USED_F3_REAL_SOURCE_REPLAY_ONLY_NO_SCIENCE",
            "replayed_trial_arms":index,
            "matched_set_comparisons":96,
            "totals":totals,
            "new_originals":0,"first_use_claims":0,
            "scientific_dispatch_authorized":False}

def main():
    p=argparse.ArgumentParser()
    for field in ("record","parent","witness","source-root","out"):
        p.add_argument("--"+field,required=True)
    a=p.parse_args()
    r=check(json.loads(Path(a.record).read_bytes()),
            Path(a.parent).read_bytes(),Path(a.witness).read_bytes(),a.source_root)
    raw=(json.dumps(r,sort_keys=True,separators=(",",":"))+"\n").encode()
    with Path(a.out).open("xb") as fd:fd.write(raw)
    print("F8_INDEPENDENT_MATCHED_TIMING_ABLATION=PASS")
    print("F8_MATCHED_TRIALS="+str(r["matched_set_comparisons"]))
    print("F8_RESULTS="+str(r["totals"]))
    print("F8_REVIEW_SHA256="+hashlib.sha256(raw).hexdigest())
    print("F8_FRESH_ORIGINALS=ZERO")
if __name__=="__main__":main()
