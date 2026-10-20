"""F124-DI independent read-only audit of all 48 *development-only* OS trials.

No source generator or learner imported or replayed. Verifies all 16
sourcefree development cases × 3 models, paired public episode identity,
zero oracle, real CPU/RSS, honest natural FIT/CHECK gating. NOT scientific.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import statistics
FAMILIES=("two_register_add_carry","two_register_rotate_and_add",
          "non_arithmetic_bitwise_boolean","three_register_outside_model")
ARMS=("learned_CV_causal_prior","independent_equal_CV_peer","frozen_degree4_reference")
SEEDS=(701,702,703,704)
def need(ok,why):
    if not ok:raise RuntimeError("F124DI_READONLY_"+why)
def digest(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--shards",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    z=p.parse_args()
    need(not z.out.exists(),"NO_DEVELOPMENT_EVIDENCE_OVERWRITE")
    files=list(z.shards.glob("dev-*.json"))
    need(len(files)==4 and {x.name for x in files}==
         {"dev-"+f+".json" for f in FAMILIES},"EXACT_FOUR_DEVELOPMENT_SHARDS")
    rows={};hashes=[]
    for file in files:
        d=json.loads(file.read_text())
        need(d["schema"]=="mass.f124di.zero-oracle-dev-12-full-OS.v1"
             and d["full_OS_process_count"]==12
             and len(d["development_samples"])==12
             and d["no_extra_oracle_queries"] and not d["external_source_birth"]
             and d["new_scientific_firstuse_consumed"]==0
             and not d["scientific_acceptance"],"EVIDENCE_ONLY_DEV")
        hashes.append({"file":file.name,"sha256":digest(d)})
        for row in d["development_samples"]:
            key=row["family"],row["seed"],row["arm"]
            need(row["schema"]=="mass.f124di.sourcefree-zero-oracle-development-trial.v1"
                 and row["family"]==d["family"]
                 and row["seed"] in SEEDS and row["arm"] in ARMS
                 and row["complete_FIT_episodes"]==24
                 and row["internal_FIT_train_episodes"]==20
                 and row["internal_FIT_validation_episodes"]==4
                 and row["full_CHECK_veto_only_episodes"]==8
                 and row["untouched_development_heldout_positive"]==8
                 and row["matched_hard_negatives"]==8
                 and row["new_oracle_queries_or_labels"]==0
                 and not row["CHECK_used_for_training"]
                 and row["sourcefree_development_only"]
                 and row["original_scientific_firstuse"]==0
                 and not row["consumed_scientific_sources_replayed"]
                 and not row["prior_F124DG_DH_cases_replayed"]
                 and not row["scientific_acceptance"]
                 and row["complete_OS_includes_python_import_FIT_prior_CHECK_heldout"]
                 and row["complete_OS_CPU_user_sys_ns"]>0
                 and row["complete_OS_peak_RSS_bytes"]>0,
                 "EVERY_TRUE_COMPLETED_SAME_INFORMATION_OS_PROCESS")
            need(key not in rows,"DUPLICATE_FROZEN_MODEL_CASE")
            rows[key]=row
    need(set(rows)=={(f,s,a) for f in FAMILIES for s in SEEDS for a in ARMS},
         "ALL_48_DEVELOPMENT_PROCESS_ROSTER")
    for f in FAMILIES:
        for s in SEEDS:
            trio=[rows[f,s,a] for a in ARMS]
            for prop in ("FIT_public_sha256","CHECK_public_sha256",
                         "HELDOUT_public_sha256"):
                need(len({x[prop] for x in trio})==1,
                     "UNEQUAL_PUBLIC_SOURCE_"+prop)
    summaries=[]
    for f in FAMILIES:
        for arm in ARMS:
            case=[rows[f,s,arm] for s in SEEDS]
            summaries.append({
               "family":f,"arm":arm,
               "natural_FIT_cases":sum(x["natural_FIT"] for x in case),
               "natural_CHECK_admitted_cases_of_4":sum(x["natural_CHECK_admission"] for x in case),
               "CHECK_exact_full_trajectories_of_32":sum(x["CHECK_correct_full_trajectories"] for x in case),
               "CHECK_admitted_exact_heldout_positive_of_32":sum(x["admitted_exact_heldout_positives"] or 0 for x in case),
               "CHECK_admitted_hard_false_positive_of_32":sum(x["admitted_hard_false_positives"] or 0 for x in case),
               "median_one_full_OS_CPU_ns":statistics.median(x["complete_OS_CPU_user_sys_ns"] for x in case),
               "median_one_full_OS_RSS_bytes":statistics.median(x["complete_OS_peak_RSS_bytes"] for x in case),
               "no_extra_oracle_queries":True,
               "matched_native_internal_FLOPs":False,
               "repetitions_per_model_case":1,
               "science_accepted":False})
    rec={"schema":"mass.f124di.original-dev-independent-48-OS-reconciliation.v1",
         "all_original_development_OS_processes":[rows[key] for key in sorted(rows)],
         "four_sourcefree_original_shard_digests":hashes,
         "aggregates":summaries,"whole_OS_processes":48,
         "source_free_development_only":True,
         "external_scientific_firstuse_consumed":0,
         "scientific_acceptance":False}
    z.out.mkdir(parents=True)
    (z.out/"original-dev-complete-48-processes.json").write_text(
        json.dumps(rec,indent=2,sort_keys=True)+"\n")
    (z.out/"safe-findings.json").write_text(json.dumps({
      "schema":"mass.f124di.development-only-safe-summary.v1",
      "original_48_OS_receipts_SHA256":digest(rec),
      "results":summaries,"science_accepted":False},indent=2,sort_keys=True)+"\n")
    print("F124DI_INDEPENDENT_DEV_48_FULL_OS_AUDIT=PASS")
    for x in summaries:print("F124DI_DEVELOPMENT_FINDING="+json.dumps(x,sort_keys=True))
    print("F124DI_NEW_SCIENTIFIC_FIRSTUSE=0")
if __name__=="__main__":main()
