"""F124-DA independent READ-ONLY 200 original OS process reconciliation.

No learner or source imports, no retraining, no prior consumed original
scientific source. Complete retained positive/negative and OS cost samples,
natural abstentions never converted to positive results.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import statistics

FAMILIES=("unseen_boolean_operator_lexicon","fourbit_carry_outside_lexicon")
SEEDS=(51,52,53,54)
ARMS=("learned_lexicon","independent_equal_lexicon","edge_lexicon",
      "frozen_quadratic","frozen_gated_recurrent")
REPS=5

def need(ok,reason):
    if not ok:raise RuntimeError("F124DA_AUDIT_"+reason)

def digest(z):
    return hashlib.sha256(json.dumps(z,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def validate(directory):
    files=list(directory.glob("shard-*.json"))
    expected={"shard-"+f+"-"+str(s)+".json" for f in FAMILIES for s in (51,53)}
    need(len(files)==4 and set(x.name for x in files)==expected,
         "EXACT_FOUR_COMPLETELY_DISTINCT_ORIGINAL_SHARDS")
    samples={};archive_hashes=[]
    for file in files:
        obj=json.loads(file.read_text())
        need(obj["schema"]=="mass.f124da.sourcefree-one-original-shard.v1"
             and len(obj["cases_and_arms"])==50 and obj["OS_process_count"]==50
             and obj["sourcefree_only"] and not obj["science_accepted"]
             and not obj["new_firstuse"],"UNMODIFIED_ORIGINAL_SHARD")
        archive_hashes.append({"name":file.name,"sha256":digest(obj)})
        for rec in obj["cases_and_arms"]:
            z=rec["row"];key=z["regime"],z["seed"],z["arm"]
            need(z["schema"]=="mass.f124da.sourcefree-new-operator-trial.v1"
                 and z["regime"]==obj["family"]
                 and z["seed"] in (obj["first_seed"],obj["first_seed"]+1)
                 and z["arm"] in ARMS and rec["rep"] in range(REPS)
                 and z["FIT_episodes"]==24 and z["CHECK_veto_only_episodes"]==8
                 and z["heldout_positive_episodes"]==8
                 and z["matched_hard_negative_episodes"]==8
                 and z["OS_includes_import_FIT_CHECK_heldout"]
                 and z["whole_OS_user_sys_CPU_ns"]>0 and z["whole_OS_max_RSS_bytes"]>0
                 and z["hidden_truth_tables_and_wire_indices_not_passed_to_models"]
                 and z["all_original_924_to_937_scientific_cases_untouched"]
                 and z["source_free_only"] and z["scientific_firstuse_cases"]==0
                 and not z["scientific_success_accepted"],
                 "ORIGINAL_RESOURCE_OR_SOURCE_SAFE_IDENTITY")
            samples.setdefault(key,{})
            need(rec["rep"] not in samples[key],"DUPLICATE_ORIGINAL_PROCESS")
            samples[key][rec["rep"]]=z
    expected_keys={(f,s,a) for f in FAMILIES for s in SEEDS for a in ARMS}
    need(set(samples)==expected_keys and all(set(x)==set(range(REPS))
          for x in samples.values()),"EVERY_ONE_OF_200_ORIGINAL_PROCESS_RECEIPTS")
    for family in FAMILIES:
        for seed in SEEDS:
            group=[samples[family,seed,arm][0] for arm in ARMS]
            for field in ("FIT_public_hash","CHECK_public_hash","HELDOUT_public_hash"):
                need(len({x[field] for x in group})==1,
                     "PAIRED_PUBLIC_EPISODES_IDENTITY_"+field)
    for group in samples.values():
        a=group[0]
        for z in group.values():
            for f in ("FIT_public_hash","CHECK_public_hash","HELDOUT_public_hash",
                      "FIT_model_fitted","natural_CHECK_admitted",
                      "natural_CHECK_full_trajectory_correct_count",
                      "diagnostic_heldout_positive_exact_count",
                      "diagnostic_heldout_negative_false_positive_count",
                      "diagnostic_heldout_bit_errors",
                      "qualified_heldout_exact_positive_count",
                      "qualified_hard_false_positive_count"):
                need(z[f]==a[f],"ORIGINAL_FIVE_PROCESS_REPLICATION_CONSISTENCY_"+f)
    return samples,archive_hashes

def summary(samples):
    out=[]
    for family in FAMILIES:
        for arm in ARMS:
            cases=[samples[family,s,arm][0] for s in SEEDS]
            costs=[z for s in SEEDS for z in samples[family,s,arm].values()]
            cpu=[z["whole_OS_user_sys_CPU_ns"] for z in costs]
            rss=[z["whole_OS_max_RSS_bytes"] for z in costs]
            out.append({
              "family":family,"arm":arm,
              "fitted_cases":sum(x["FIT_model_fitted"] for x in cases),
              "natural_CHECK_admitted_cases_of_4":sum(x["natural_CHECK_admitted"] for x in cases),
              "natural_CHECK_episodes_correct_of_32":sum(x["natural_CHECK_full_trajectory_correct_count"] for x in cases),
              "diagnostic_heldout_positive_exact_of_32":sum(x["diagnostic_heldout_positive_exact_count"] for x in cases),
              "diagnostic_heldout_hard_false_positive_of_32":sum(x["diagnostic_heldout_negative_false_positive_count"] for x in cases),
              "diagnostic_heldout_bit_errors":sum(x["diagnostic_heldout_bit_errors"] for x in cases),
              "CHECK_admitted_positive_exact":sum(x["qualified_heldout_exact_positive_count"] or 0 for x in cases),
              "CHECK_admitted_hard_false_positive":sum(x["qualified_hard_false_positive_count"] or 0 for x in cases),
              "median_complete_OS_CPU_ns":statistics.median(cpu),
              "median_complete_OS_peak_RSS_bytes":statistics.median(rss),
              "max_complete_OS_peak_RSS_bytes":max(rss),
              "full_process_samples":20,"native_equal_work_qualified":False,
              "scientific_nonregression_claimed":False})
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--shards",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    x=p.parse_args()
    need(not x.out.exists(),"NO_OVERWRITE_FIRST_ORIGINAL_RESEARCH_EVIDENCE")
    all_samples,sha=validate(x.shards)
    results=summary(all_samples)
    receipt={"schema":"mass.f124da.original-200-process-sourcefree-operator-evidence.v1",
         "original_processes":[{"family":k[0],"seed":k[1],"arm":k[2],
            "rep":rep,"row":z} for k,group in sorted(all_samples.items())
            for rep,z in sorted(group.items())],
         "four_original_shard_digests":sha,
         "ten_original_arm_family_findings":results,
         "all_science_924_to_937_untouched":True,
         "sourcefree_operator_induction_only":True,"new_firstuse":False,
         "scientific_success_accepted":False}
    x.out.mkdir(parents=True)
    (x.out/"full-200-OS-receipts.json").write_text(
           json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    digest_report={"schema":"mass.f124da.safe-operator-induction-summary.v1",
         "sha256_all_200_complete_process_evidence":digest(receipt),
         "findings":results,"original_OS_repeats":200,"science_accepted":False}
    (x.out/"safe-findings.json").write_text(
          json.dumps(digest_report,sort_keys=True,indent=2)+"\n")
    print("F124DA_ALL_200_PROCESS_SOURCEFREE_RECEIPTS=PASS")
    for q in results:print("F124DA_OPERATOR_FINDING="+json.dumps(q,sort_keys=True))
    print("F124DA_REAL_FIRSTUSE_EXPERIMENTS=0")
    print("F124DA_SCIENTIFIC_ACCEPTANCE=FALSE")

if __name__=="__main__":main()
