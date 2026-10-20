"""F124-DA independent source-free original program discovery custody.

Read-only complete 160 whole Linux process receipt audit, 5 repeats each
of eight cases x four equally informed or strong recurrent trained arms.
Does not import new source modules, learners or scientific original sources.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import statistics

FAMILIES=("heldout_two_stage_arithmetic_programs","out_of_primitive_class_multiplicative_carry")
SEEDS=(51,52,53,54)
ARMS=("shared_program","independent_pooled","edge_program","frozen_gated_recurrent")
REPS=5

def need(ok,msg):
    if not ok:raise RuntimeError("F124DA_REVIEW_"+msg)

def digest(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def load(path):
    required={"shard-"+family+"-"+str(seed)+".json" for family in FAMILIES
            for seed in (51,53)}
    present=list(path.glob("shard-*.json"))
    need(len(present)==4 and {x.name for x in present}==required,
         "FOUR_COMPLETE_NONSELECTIVE_SHARDS")
    packet_hash=[];observations={}
    for filename in present:
        source=json.loads(filename.read_text())
        need(source["schema"]=="mass.f124da.original-sourcefree-40-process-shard.v1"
             and source["whole_OS_process_count"]==40 and len(source["samples"])==40
             and source["new_original_scientific_sources_consumed"]==0
             and not source["protected_source_opened"]
             and not source["scientific_acceptance"],"SHARD_FIRSTUSE_DENIED")
        packet_hash.append({"file":filename.name,"sha256":digest(source)})
        for obj in source["samples"]:
            row=obj["original_process"]
            key=row["family"],row["seed"],row["arm"]
            need(row["family"]==source["family"] and
                 row["seed"] in (source["first_seed"],source["first_seed"]+1)
                 and row["arm"] in ARMS and obj["rep"] in range(REPS)
                 and row["schema"]=="mass.f124da.sourcefree-operator-program-trial.v1"
                 and row["FIT_episodes"]==24
                 and row["CHECK_veto_only_episodes"]==8
                 and row["HELDOUT_positive_episodes"]==8
                 and row["matched_hard_negative_episodes"]==8
                 and row["all_eight_autoregressive_steps_scored_if_fitted"]
                 and row["full_process_includes_start_import_FIT_CHECK_HELDOUT"]
                 and row["whole_OS_CPU_user_and_sys_ns"]>0
                 and row["whole_OS_peak_RSS_bytes"]>0
                 and row["source_program_never_passed_to_model"]
                 and row["all_old_original_scientific_924_to_937_sources_untouched"]
                 and row["scientific_firstuse_consumed"]==0
                 and not row["protected_source_used"] and not row["scientific_acceptance"],
                 "CASE_COMPLETE_OS_AND_PRIVATE_SCIENCE_INTACT")
            observations.setdefault(key,{})
            need(obj["rep"] not in observations[key],"DUPLICATE_PROCESS_REPETITION")
            observations[key][obj["rep"]]=row
    expected={(family,seed,arm) for family in FAMILIES for seed in SEEDS for arm in ARMS}
    need(set(observations)==expected and len(observations)==32 and
         all(set(record)==set(range(REPS)) for record in observations.values()),
         "COMPLETE_32_MODEL_CASES_AND_160_ORIGINAL_OS_PROCESSES")
    for family in FAMILIES:
        for seed in SEEDS:
            same=[observations[family,seed,a][0] for a in ARMS]
            for field in ("FIT_SHA256","CHECK_SHA256","HELDOUT_SHA256"):
                need(len({x[field] for x in same})==1,
                     "SAME_AUTHENTIC_PUBLIC_SOURCE_"+field)
    for group in observations.values():
        first=group[0]
        for x in group.values():
            for field in ("FIT_SHA256","CHECK_SHA256","HELDOUT_SHA256",
                "natural_fit_model_found","natural_CHECK_8_of_8_admitted",
                "diagnostic_CHECK_exact","diagnostic_HELDOUT_exact_positives",
                "diagnostic_HELDOUT_hard_false_positives",
                "diagnostic_HELDOUT_positive_bit_errors",
                "admitted_HELDOUT_exact_positives","admitted_HELDOUT_hard_false_positives"):
                need(x[field]==first[field],"REPETITION_DIAGNOSTIC_DRIFT_"+field)
    return observations,packet_hash

def aggregate(observations):
    out=[]
    for family in FAMILIES:
        for arm in ARMS:
            cases=[observations[family,seed,arm][0] for seed in SEEDS]
            cost=[x["whole_OS_CPU_user_and_sys_ns"] for seed in SEEDS
                  for x in observations[family,seed,arm].values()]
            rss=[x["whole_OS_peak_RSS_bytes"] for seed in SEEDS
                 for x in observations[family,seed,arm].values()]
            out.append({
                "family":family,"arm":arm,"cases":4,
                "naturally_FIT_fitted":sum(x["natural_fit_model_found"] for x in cases),
                "naturally_CHECK_admitted":sum(x["natural_CHECK_8_of_8_admitted"] for x in cases),
                "diagnostic_CHECK_exact_of_32":sum(x["diagnostic_CHECK_exact"] for x in cases),
                "diagnostic_HELDOUT_exact_positives_of_32":sum(x["diagnostic_HELDOUT_exact_positives"] for x in cases),
                "diagnostic_HELDOUT_hard_false_positives_of_32":sum(x["diagnostic_HELDOUT_hard_false_positives"] for x in cases),
                "diagnostic_HELDOUT_bit_errors":sum(x["diagnostic_HELDOUT_positive_bit_errors"] for x in cases),
                "admitted_HELDOUT_exact_positives_of_32":sum(x["admitted_HELDOUT_exact_positives"] or 0 for x in cases),
                "admitted_HELDOUT_hard_false_positives_of_32":sum(x["admitted_HELDOUT_hard_false_positives"] or 0 for x in cases),
                "complete_OS_sample_count":len(cost),
                "median_whole_OS_CPU_ns":statistics.median(cost),
                "median_whole_OS_peak_RSS_bytes":statistics.median(rss),
                "maximum_whole_OS_peak_RSS_bytes":max(rss),
                "equivalent_FLOPS_proven":False,
                "scientific_nonregression_claimed":False
            })
    return out

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--shards",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    a=parser.parse_args()
    need(not a.out.exists(),"IMMUTABLE_RESULT_ONLY")
    data,hashes=load(a.shards)
    summary=aggregate(data)
    whole={"schema":"mass.f124da.complete-sourcefree-program-learning-160-process-audit.v1",
        "raw_cases":[{"family":k[0],"seed":k[1],"arm":k[2],
            "repetitions":[{"rep":rep,"row":v} for rep,v in sorted(x.items())]}
            for k,x in sorted(data.items())],
        "four_original_sourcefree_shard_hashes":hashes,
        "all_eight_model_family_aggregates":summary,
        "sourcefree_cases":8,"whole_OS_receipts":160,
        "consumed_original_sci_sources":0,
        "protected_original_holdout_released":False,
        "scientific_accepted":False}
    a.out.mkdir(parents=True)
    (a.out/"complete-160-sourcefree-program-evidence.json").write_text(
         json.dumps(whole,sort_keys=True,indent=2)+"\n")
    safe={"schema":"mass.f124da.sourcefree-program-study-safe-summary.v1",
      "whole_160_receipt_content_sha256":digest(whole),
      "model_family_summary":summary,
      "sourcefree_cases":8,"whole_OS_receipts":160,
      "scientific_firstuse":False,"scientific_acceptance":False}
    (a.out/"safe-summary.json").write_text(json.dumps(safe,sort_keys=True,indent=2)+"\n")
    print("F124DA_160_WHOLE_OS_AND_EQUIVALENT_SOURCE_RECEIPTS=PASS")
    for item in summary:
        print("F124DA_OPERATOR_RESULT="+json.dumps(item,sort_keys=True))
    print("F124DA_ORIGINAL_SCIENCE_FIRSTUSE=FALSE")
    print("F124DA_SCIENTIFIC_ACCEPTANCE=FALSE")

if __name__=="__main__":main()
