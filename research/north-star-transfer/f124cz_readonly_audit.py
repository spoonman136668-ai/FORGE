"""F124-CZ independently reconcile all sourcefree out-of-class receipts.

Requires all 200 real Linux whole-process samples, 5 repetitions of each
fixed family/seed/arm, identical public FIT/CHECK/heldout across five arms,
natural admissions preserved and every source-born original family excluded.
Read-only: does not import trained models or regenerate synthetic sources.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import statistics

REGIMES=("nonlinear_cross_role_quadratic","modular_carry_composition")
SEEDS=(41,42,43,44)
ARMS=("frozen_affine","shared_quadratic","independent_pooled",
      "edge_quadratic","frozen_gated_recurrent")
REPS=5

def need(ok,why):
    if not ok:raise RuntimeError("F124CZ_REVIEW_"+why)

def digest(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,
               separators=(",",":")).encode()).hexdigest()

def load_and_verify(directory):
    expect={"shard-"+realm+"-"+str(seed)+".json" for realm in REGIMES
            for seed in (41,43)}
    files=list(directory.glob("shard-*.json"))
    need({f.name for f in files}==expect and len(files)==4,
         "ALL_FOUR_ORIGINAL_NONOVERLAPPING_SHARDS")
    jobs={}
    source_hashes=[]
    for file in files:
        obj=json.loads(file.read_text())
        need(obj["schema"]=="mass.f124cz.sourcefree-outofclass-original-shard.v1"
             and obj["full_linux_process_count"]==50
             and len(obj["processes"])==50 and
             obj["scientific_originals_consumed"]==0 and
             not obj["private_source_oracle_in_model"] and
             not obj["scientific_acceptance"],
             "AUTHENTIC_UNSELECTED_SHARD_CUSTODY")
        source_hashes.append({"shard":file.name,"sha256":digest(obj)})
        for record in obj["processes"]:
            row=record["original_process"]
            k=(row["realm"],row["seed"],row["arm"])
            need(row["realm"]==obj["regime"] and
                 row["seed"] in (obj["first_seed"],obj["first_seed"]+1) and
                 row["arm"] in ARMS and record["repetition"] in range(REPS),
                 "EXACT_SOURCE_CASE_IDENTITY")
            need(row["schema"]=="mass.f124cz.original-sourcefree-outofclass-trial.v1"
                 and row["FIT_complete_episodes"]==24
                 and row["CHECK_veto_only_complete_episodes"]==8
                 and row["heldout_complete_positive_episodes"]==8
                 and row["matched_hard_negative_episodes"]==8
                 and row["complete_python_import_fit_veto_positive_and_negative_process"]
                 and row["whole_OS_CPU_user_sys_ns"]>0
                 and row["whole_OS_peak_RSS_bytes"]>0
                 and row["private_source_law_not_passed_to_learner"]
                 and row["no_old_924_through_937_original_sci_sources_used"]
                 and not row["science_accepted"],
                 "WHOLE_NATIVE_AND_ORIGINAL_SCIENCE_BOUNDARY")
            jobs.setdefault(k,{})
            need(record["repetition"] not in jobs[k],
                 "NO_REPEATED_SAMPLE_ID")
            jobs[k][record["repetition"]]=row
    needed={(realm,seed,arm) for realm in REGIMES for seed in SEEDS
            for arm in ARMS}
    need(set(jobs)==needed and all(set(samples)==set(range(REPS))
             for samples in jobs.values()),"COMPLETE_40_CASE_ARM_200_SAMPLE_ROSTER")
    for realm in REGIMES:
        for seed in SEEDS:
            same=[jobs[realm,seed,arm][0] for arm in ARMS]
            for key in ("FIT_public_SHA256","CHECK_veto_public_SHA256",
                        "HELDOUT_public_SHA256"):
                need(len({x[key] for x in same})==1,
                     "EQUAL_SOURCE_INFO_ALL_MODELS_"+key)
    for k,samples in jobs.items():
        root=samples[0]
        for z in samples.values():
            for field in ("FIT_public_SHA256","CHECK_veto_public_SHA256",
                          "HELDOUT_public_SHA256","fitted_naturally_from_FIT",
                          "natural_CHECK_admitted","complete_CHECK_exact_trajectories",
                          "diagnostic_heldout_exact_positive",
                          "diagnostic_heldout_exact_hard_false_positive",
                          "diagnostic_heldout_positive_bit_errors",
                          "admitted_heldout_exact_positive","admitted_heldout_hard_false_positive"):
                need(z[field]==root[field],
                     "INCONSISTENT_FIVE_REPETITIONS_OF_SAME_FROZEN_CASE_"+field)
    return jobs,source_hashes

def results(jobs):
    rows=[]
    for realm in REGIMES:
        for arm in ARMS:
            cases=[jobs[realm,seed,arm][0] for seed in SEEDS]
            cpu=[v["whole_OS_CPU_user_sys_ns"] for seed in SEEDS
                  for v in jobs[realm,seed,arm].values()]
            rss=[v["whole_OS_peak_RSS_bytes"] for seed in SEEDS
                  for v in jobs[realm,seed,arm].values()]
            rows.append({
              "regime":realm,"arm":arm,
              "naturally_fitted_cases":sum(x["fitted_naturally_from_FIT"] for x in cases),
              "natural_CHECK_admitted_cases_of_4":sum(x["natural_CHECK_admitted"] for x in cases),
              "natural_CHECK_exact_trajectories_of_32":sum(x["complete_CHECK_exact_trajectories"] for x in cases),
              "diagnostic_heldout_positives_exact_of_32":sum(x["diagnostic_heldout_exact_positive"] for x in cases),
              "diagnostic_heldout_hard_false_positives_of_32":sum(x["diagnostic_heldout_exact_hard_false_positive"] for x in cases),
              "diagnostic_heldout_positive_bit_errors":sum(x["diagnostic_heldout_positive_bit_errors"] for x in cases),
              "admitted_heldout_positives_exact":sum(x["admitted_heldout_exact_positive"] or 0 for x in cases),
              "admitted_heldout_hard_false_positives":sum(x["admitted_heldout_hard_false_positive"] or 0 for x in cases),
              "full_process_samples":len(cpu),
              "median_whole_OS_CPU_ns":statistics.median(cpu),
              "median_whole_OS_peak_RSS_bytes":statistics.median(rss),
              "maximum_whole_OS_peak_RSS_bytes":max(rss),
              "matched_native_work_equivalence_proven":False,
              "scientific_nonregression_claimed":False})
    return rows

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--shards",required=True,type=Path)
    ap.add_argument("--out",required=True,type=Path)
    x=ap.parse_args()
    need(not x.out.exists(),"NO_ORIGINAL_EVIDENCE_OVERWRITE")
    jobs,hashes=load_and_verify(x.shards)
    summarized=results(jobs)
    report={
      "schema":"mass.f124cz.readonly-sourcefree-outofclass-200-process-study.v1",
      "complete_original_200_processes":[
         {"realm":k[0],"seed":k[1],"arm":k[2],"repetition":rep,"row":z}
         for k,group in sorted(jobs.items()) for rep,z in sorted(group.items())],
      "four_sourcefree_shard_SHA256":hashes,
      "all_10_family_arm_outcomes":summarized,
      "models_tested":["frozen affine only","shared quadratic","independently trained pooled quadratic","fully trained edge quadratic","frozen gated recurrent"],
      "original_science_firstuse_consumed":0,
      "real_scientific_out_of_hypothesis_transfer_claimed":False,
      "natural_CHECK_no_forced_admissions":True,
      "protected_source_opened":False,"scientific_acceptance":False}
    x.out.mkdir(parents=True)
    (x.out/"full-200-os-receipts.json").write_text(
            json.dumps(report,sort_keys=True,indent=2)+"\n")
    safe={"schema":"mass.f124cz.sourcefree-outofclass-final-safe-summary.v1",
          "full_200_receipt_evidence_SHA256":digest(report),
          "aggregate":summarized,"sample_count":200,
          "no_firstuse":True,"science_accepted":False}
    (x.out/"safe-summary.json").write_text(
         json.dumps(safe,sort_keys=True,indent=2)+"\n")
    print("F124CZ_ALL_200_SOURCEFREE_WHOLE_OS_RECEIPTS=PASS")
    for r in summarized:
        print("F124CZ_OUTOFCLASS_RESULT="+json.dumps(r,sort_keys=True))
    print("F124CZ_ORIGINAL_SCIENTIFIC_FIRSTUSE=0")
    print("F124CZ_SCIENCE_ACCEPTED=FALSE")

if __name__=="__main__":main()
