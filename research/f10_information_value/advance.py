"""Automatically advance qualified F9 into a fitted F10 sensor-value policy.

Training uses F9 public readings on already-consumed F3 seeds 67204/05.
Validation uses disjoint already-consumed F3 seeds 67206/07. A separate
reviewer re-fits every sensor value and replays all 96 real source cases.
No scientific authority or paid API is involved.
"""
import argparse,hashlib,json
from pathlib import Path
from train import train,previous_evidence,canonical
from worker import load_source,evaluate,SOURCE_COMMIT
from policy import CHECK,PAIRS

def must(ok,why):
    if not ok:raise ValueError("F10_AUTONOMOUS_"+why)

def execute(f9_bytes,review_bytes,root):
    parent=json.loads(f9_bytes)
    reviewer=json.loads(review_bytes)
    previous_evidence(parent,reviewer)
    model=train(f9_bytes,review_bytes)
    source=load_source(root)
    rows=[]
    for pair in PAIRS:
        for regime in ("steady","onset1"):
            for family in source.FAMILIES:
                for seed in CHECK:
                    for matching in source.POLICIES:
                        rows.append(evaluate(source,model,seed,pair,regime,family,matching))
    must(len(rows)==96,"VALIDATION_N")
    totals={"cases":0,"pre":0,"post":0,"detections":0,
            "steady_errors":0,"earliest_detection":None,
            "anomalous_before_episode_5":0}
    for row in rows:
        totals["cases"]+=1
        totals["pre"]+=row["pre_mismatch"]
        totals["post"]+=row["post_mismatch"]
        totals["detections"]+=int(row["first_detection"] is not None)
        if row["regime"]=="steady":
            totals["steady_errors"]+=row["pre_mismatch"]+row["post_mismatch"]
        if row["sample_trace"]["decision"]["anomaly_after_3"]:
            totals["anomalous_before_episode_5"]+=1
        first=row["first_detection"]
        if first is not None:
            totals["earliest_detection"]=(first if totals["earliest_detection"] is None
                                          else min(first,totals["earliest_detection"]))
    controls={}
    for rule in ("ALWAYS_EARLY","ALWAYS_SWAP",parent["model"]["selected_rule"]):
        data=[row for row in parent["validation"] if row["rule"]==rule]
        must(len(data)==96 and all(row["seed"] in CHECK for row in data),
             "PARENT_CONTROL")
        controls[rule]={"cases":len(data),
                        "mismatches":sum(row["pre_mismatch"]+row["post_mismatch"] for row in data),
                        "detections":sum(row["first_detection"] is not None for row in data)}
    must(controls["ALWAYS_EARLY"]["mismatches"]==74
         and controls["ALWAYS_SWAP"]["mismatches"]==66
         and controls[parent["model"]["selected_rule"]]["mismatches"]==66,
         "F9_FROZEN_CONTROL_IDENTITY")
    return {
      "schema":"forge.f10.automatic-public-information-value-engineering.v1",
      "status":"F3_USED_ONLY_NO_SCIENTIFIC_AUTHORITY",
      "hypothesis":"Learn expected quadratic uncertainty reduction for each candidate public observation rather than select a fixed schedule",
      "parent_f9_sha256":hashlib.sha256(f9_bytes).hexdigest(),
      "parent_f9_independent_sha256":hashlib.sha256(review_bytes).hexdigest(),
      "parent_source_commit":SOURCE_COMMIT,
      "model":model,"validation":rows,"validation_summary":totals,
      "f9_used_validation_controls":controls,
      "new_cohort_uses":0,"new_first_use_claims":0,
      "new_scientific_originals":0,"paid_api_calls":0,
      "scientific_winner_selected":False,
      "scientific_dispatch_authorized":False
    }

def main():
    p=argparse.ArgumentParser()
    for name in ("parent","witness","source-root","out"):
        p.add_argument("--"+name,required=True)
    a=p.parse_args()
    data=execute(Path(a.parent).read_bytes(),
                 Path(a.witness).read_bytes(),a.source_root)
    encoded=canonical(data)
    with Path(a.out).open("xb") as file:file.write(encoded)
    print("F10_F9_AUTOMATIC_EXPECTED_INFORMATION_VALUE_TRAINING=PASS")
    print("F10_FROZEN_MODEL_SHA256="+hashlib.sha256(canonical(data["model"])).hexdigest())
    print("F10_96_USED_VALIDATION_CASES=PASS")
    print("F10_HISTORICAL_TOTALS="+str(data["validation_summary"]))
    print("F10_CONTROL_TOTALS="+str(data["f9_used_validation_controls"]))
    print("F10_NEW_FIRST_USE=ZERO")
if __name__=="__main__":main()
