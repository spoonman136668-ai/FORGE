"""F124-DB independent read-only sourcefree 160-OS-process reconciliation.

No source/task or learner imports. Requires all 4 shards and 5 authentic
measurements of each of the 2×4×4 model/task pairs. Natural CHECK vetoes
and all negatives retained; no artificial success from unadmitted models.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import statistics

FAMILIES=("nested-additive-new-graph","nested-xor-new-graph")
SEEDS=(61,62,63,64)
ARMS=("meta_constructor","equal_meta_peer","frozen_quadratic","frozen_gated_recurrent")
REPS=5

def need(ok,why):
    if not ok:raise RuntimeError("F124DB_AUDIT_"+why)

def digest(z):
    return hashlib.sha256(json.dumps(z,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def verify(directory):
    files=list(directory.glob("shard-*.json"))
    expect={"shard-"+family+"-"+str(seed)+".json"
            for family in FAMILIES for seed in (61,63)}
    need(len(files)==4 and {f.name for f in files}==expect,
         "ALL_FOUR_FROZEN_NONOVERLAPPING_ORIGINAL_SHARDS")
    records={};filesha=[]
    for f in files:
        x=json.loads(f.read_text())
        need(x["schema"]=="mass.f124db.sourcefree-40-native-receipts.v1"
             and x["whole_OS_processes"]==40 and len(x["samples"])==40
             and x["scientific_source_firstuse_consumed"]==0
             and not x["scientific_acceptance"],"AUTHENTIC_SOURCEFREE_SHARD_ONLY")
        filesha.append({"shard":f.name,"sha256":digest(x)})
        for q in x["samples"]:
            z=q["measurement"];k=(z["family"],z["seed"],z["arm"])
            need(z["schema"]=="mass.f124db.original-sourcefree-compositional-construction-trial.v1"
                 and z["family"]==x["family"]
                 and z["seed"] in (x["first_seed"],x["first_seed"]+1)
                 and z["arm"] in ARMS and q["rep"] in range(REPS)
                 and z["public_meta_tasks"]==12
                 and z["FIT_episodes"]==24 and z["CHECK_veto_episodes"]==8
                 and z["unseen_positive_episodes"]==8
                 and z["matched_hard_negative_episodes"]==8
                 and z["whole_OS_includes_Python_import_meta_FIT_CHECK_and_heldout"]
                 and z["whole_OS_user_plus_sys_CPU_ns"]>0
                 and z["whole_OS_peak_RSS_bytes"]>0
                 and z["source_hidden_macro_and_tree_not_passed_to_learners"]
                 and z["no_prior_scientific_original_cases_read"]
                 and z["sourcefree_only"] and z["scientific_firstuse_consumed"]==0
                 and not z["scientific_acceptance"],"COMPLETE_ORIGINAL_SCIENCE_AND_OS_CUSTODY")
            records.setdefault(k,{})
            need(q["rep"] not in records[k],"DUPLICATE_OS_REPETITION")
            records[k][q["rep"]]=z
    expected={(f,s,a) for f in FAMILIES for s in SEEDS for a in ARMS}
    need(set(records)==expected and all(set(group)==set(range(REPS))
         for group in records.values()),"ALL_160_OS_SAMPLES_OF_FROZEN_ROSTER")
    for family in FAMILIES:
        for seed in SEEDS:
            group=[records[family,seed,arm][0] for arm in ARMS]
            for key in ("meta_task_public_sha256","heldout_FIT_sha256",
                        "heldout_CHECK_sha256","heldout_unseen_sha256"):
                need(len({x[key] for x in group})==1,
                     "SAME_PUBLIC_META_AND_HELDOUT_ALL_ARMS_"+key)
    for rec in records.values():
        first=rec[0]
        for z in rec.values():
            for field in ("naturally_fitted_FIT","natural_CHECK_admission",
                     "natural_CHECK_correct_episodes","diagnostic_heldout_exact_positives",
                     "diagnostic_hard_false_positives","diagnostic_heldout_bit_errors",
                     "admitted_exact_heldout_positives","admitted_hard_false_positives"):
                need(z[field]==first[field],"FIVE_RUNS_NOT_DETERMINISTIC_"+field)
    return records,filesha

def aggregate(rec):
    result=[]
    for family in FAMILIES:
        for arm in ARMS:
            cases=[rec[family,seed,arm][0] for seed in SEEDS]
            costs=[z for seed in SEEDS for z in rec[family,seed,arm].values()]
            result.append({
             "family":family,"arm":arm,
             "cross_task_meta_trained":cases[0]["cross_task_meta_trained"],
             "naturally_fitted_heldout_cases":sum(x["naturally_fitted_FIT"] for x in cases),
             "natural_CHECK_admitted_cases_of_4":sum(x["natural_CHECK_admission"] for x in cases),
             "natural_CHECK_exact_episodes_of_32":sum(x["natural_CHECK_correct_episodes"] for x in cases),
             "diagnostic_positive_full_episodes_exact_of_32":sum(x["diagnostic_heldout_exact_positives"] or 0 for x in cases),
             "diagnostic_negative_hard_false_positive_of_32":sum(x["diagnostic_hard_false_positives"] or 0 for x in cases),
             "CHECK_admitted_exact_heldout_positives":sum(x["admitted_exact_heldout_positives"] or 0 for x in cases),
             "CHECK_admitted_hard_false_positive":sum(x["admitted_hard_false_positives"] or 0 for x in cases),
             "total_process_replicates":20,
             "median_whole_OS_CPU_ns":statistics.median(z["whole_OS_user_plus_sys_CPU_ns"] for z in costs),
             "median_whole_OS_peak_RSS_bytes":statistics.median(z["whole_OS_peak_RSS_bytes"] for z in costs),
             "native_training_work_equal":False,
             "resource_nonregression_proven":False})
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--shards",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    x=p.parse_args()
    need(not x.out.exists(),"ORIGINAL_EVIDENCE_CANNOT_OVERWRITE")
    records,hashes=verify(x.shards)
    out=aggregate(records)
    review={"schema":"mass.f124db.readonly-original-sourcefree-160-process.v1",
      "all_original_OS_processes":[{"family":k[0],"seed":k[1],"arm":k[2],
         "rep":i,"row":z} for k,group in sorted(records.items())
         for i,z in sorted(group.items())],
      "four_original_shard_hashes":hashes,"findings":out,
      "new_scientific_firstuse_consumed":0,"protected_science_opened":False,
      "scientific_acceptance":False}
    x.out.mkdir(parents=True)
    (x.out/"full-original-160-native.json").write_text(
         json.dumps(review,sort_keys=True,indent=2)+"\n")
    safe={"schema":"mass.f124db.sourcefree-safe-retained-findings.v1",
      "full_original_160_native_sha256":digest(review),
      "sourcefree_results":out,"OS_processes":160,
      "science_accepted":False}
    (x.out/"safe-findings.json").write_text(
         json.dumps(safe,sort_keys=True,indent=2)+"\n")
    print("F124DB_ALL_160_WHOLE_OS_PROCESS_RECEIPTS=PASS")
    for z in out:print("F124DB_STRUCTURAL_FINDING="+json.dumps(z,sort_keys=True))
    print("F124DB_ORIGINAL_FIRSTUSE=0")
    print("F124DB_SCIENTIFIC_ACCEPTANCE=FALSE")

if __name__=="__main__":main()
