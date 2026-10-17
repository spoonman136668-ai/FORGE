"""F129-R source-authenticated public FIT/CHECK exactness and cost receipt.

No model selection, fitting, validation-based tuning, or protected source.
The packed-join candidate is frozen before source cases are generated.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
import f118_autonomy_feedback as f118
import f120_generated_environment as f120
import f129r_freeze_admission as freeze
import f129r_train_environment as env
import f129r_packed_token_join as mechanism

SCHEMA="forge.research.f129r.public-fit-check-packed-join.v1"
def need(ok,why):env.need(bool(ok),"ADMISSION_"+why)
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def lane_run(lane,vectors,provenance):
    fit=env.cohort_rows(lane,vectors,"FIT")
    check=env.cohort_rows(lane,vectors,"TRAIN_CHECK")
    need(len(fit)==len(check)==64 and
         sum(y for g,y in fit)==32 and sum(y for g,y in check)==32 and
         not ({env.digest(g) for g,y in fit}&{env.digest(g) for g,y in check}),
         "SPLIT_NOT_INDEPENDENT")
    # FIT validates the source and frozen limits ONLY; there are no weights
    # to learn, no selected model, and no labelled training features.
    fit_ref=mechanism.compare(fit)
    for result in fit_ref.values():
        need(result["paired_correct"]==32,"FIT_ORIGINAL_NEGATIVE")
    scored=mechanism.compare(check)
    benchmark=mechanism.benchmark(check)
    pass_accuracy=all(x["paired_correct"]==32 for x in scored.values())
    success=(pass_accuracy and benchmark["passes_frozen_runtime_target"] and
             benchmark["passes_frozen_memory_target"])
    return {
      "lane":lane,"candidate_source_sha256":provenance,
      "FIT_sha256":env.digest(fit),"TRAIN_CHECK_sha256":env.digest(check),
      "FIT_pairs":32,"TRAIN_CHECK_pairs":32,
      "unseen_check_disjoint":True,
      "trained_parameters":0,"fit_model_selection":False,
      "fit_source_checks":{k:v["paired_correct"] for k,v in fit_ref.items()},
      "TRAIN_CHECK_strong_controls":scored,
      "same_host_resource_benchmark":benchmark,
      "passes_both_frozen_development_thresholds":bool(success),
      "native_indexed_fast_baseline_included":True,
      "protected_confirmation_read":False,
      "scientific_acceptance":False}

def run(advisory,head):
    cfg,fr_digest=freeze.frozen()
    need(type(head) is str and re.fullmatch("[0-9a-f]{40}",head) and
         (not os.environ.get("GITHUB_SHA") or os.environ["GITHUB_SHA"]==head),
         "SOURCE_HEAD")
    sources=f120.validate(advisory,head)
    need(set(sources)=={"Wingless","Yggdrasil"},"TWO_LANES")
    result=[]
    for lane in ("Wingless","Yggdrasil"):
        rows=sources[lane]
        need(len(rows)==2 and [x["candidate_index"] for x in rows]==[2,3] and
             rows[0]["vector"]!=rows[1]["vector"],"AUTHENTIC_TWO_VECTORS")
        result.append(lane_run(lane,[e["vector"] for e in rows],
                      [e["source_candidate_sha256"] for e in rows]))
    return {
      "schema":SCHEMA,"source_sha":head,
      "frozen_git_blob":freeze.FREEZE_BLOB,
      "freeze_sha256":fr_digest,
      "source_advisory_sha256":digest(advisory),
      "stage":"PUBLIC_SYNTHETIC_FIT_AND_DISJOINT_TRAIN_CHECK_ONLY",
      "lanes":result,
      "all_lanes_pass_development_criteria":all(
            x["passes_both_frozen_development_thresholds"] for x in result),
      "scientific_success":False,
      "independent_scientific_first_use":False,
      "scientific_acceptance":False,
      "optimizer_promotion":False,
      "protected_CONFIRM_read":False,
      "originals_dispatched":0,
      "accepted_ref_mutations":0,
      "codex_calls":0,"paid_model_calls":0,"new_scheduler":False}
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--advisory",required=True)
    parser.add_argument("--source-sha",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    doc=run(f118.load_report(args.advisory),args.source_sha)
    dest=Path(args.output)
    need(dest.parent.is_dir() and not dest.exists(),"OVERWRITE_REFUSED")
    raw=(json.dumps(doc,sort_keys=True,separators=(",",":"))+"\n").encode()
    dest.open("xb").write(raw)
    print("F129R_TRAIN_SOURCE_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in doc["lanes"]:
        bench=lane["same_host_resource_benchmark"]
        print("F129R_"+lane["lane"].upper()+"_PAIRED="+str(
            lane["TRAIN_CHECK_strong_controls"][
                "F129R_PACKED_TOKEN_HASH_JOIN_NO_LEARNING_NO_SELECTION"]["paired_correct"])+"/32")
        print("F129R_"+lane["lane"].upper()+"_RUNTIME_RATIO="+str(
            bench["packed_to_native_median_walltime_ratio"]))
        print("F129R_"+lane["lane"].upper()+"_MEMORY_RATIO="+str(
            bench["packed_to_native_traced_peak_ratio"]))
    print("F129R_PROTECTED_CONFIRM_UNOPENED=true")
    print("F129R_SCIENTIFIC_ACCEPTANCE=false")
if __name__=="__main__":
    try:main()
    except (env.Invalid,freeze.Invalid,f118.Quarantined,
            ValueError,KeyError,TypeError,OSError,OverflowError,ZeroDivisionError) as e:
        print("F129R_TRAIN_QUARANTINED="+str(e),file=sys.stderr)
        raise SystemExit(1)
