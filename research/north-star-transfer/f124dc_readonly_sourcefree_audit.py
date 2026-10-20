"""Independent READ-ONLY F124-DC full 144-process OS evidence reconciliation.

Never imports the source author or candidate/peer: no source regeneration,
no consumed original science. Checks all 6 original nonoverlapping sourcefree
shards and five distinct original condition/process identifiers per case.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import statistics

FAMILIES=("ternary-majority-unseen","ternary-selector-unseen","quartic-fourway-unseen")
SEEDS=(71,72,73,74)
ARMS=("meta_NAND_constructor","equally_meta_trained_ANF_peer",
      "same_compute_no_meta_gate_ablation","prior_F124DA_two_input_lexicon")
REPS=3

def need(ok,why):
    if not ok:raise RuntimeError("F124DC_AUDIT_"+why)

def digest(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def examine(folder):
    shards=list(folder.glob("shard-*.json"))
    expected={"shard-"+family+"-"+str(seed)+".json"
              for family in FAMILIES for seed in (71,73)}
    need(len(shards)==6 and {s.name for s in shards}==expected,
         "ALL_SIX_FIXED_SOURCEFREE_SHARDS")
    samples={};sha=[]
    for path in shards:
        p=json.loads(path.read_text())
        need(p["schema"]=="mass.f124dc.sourcefree-original-24-process-shard.v1"
             and len(p["original_os_samples"])==24
             and p["whole_linux_processes"]==24
             and p["scientific_original_firstuse_consumed"]==0
             and not p["science_accepted"],"ORIGINAL_SHARD_PROTOCOL")
        sha.append({"original_shard":path.name,"sha256":digest(p)})
        for measurement in p["original_os_samples"]:
            z=measurement["row"]
            key=(z["family"],z["seed"],z["arm"])
            need(z["schema"]=="mass.f124dc.original-sourcefree-new-primitive-trial.v1"
                 and z["family"]==p["family"]
                 and z["seed"] in (p["seed_start"],p["seed_start"]+1)
                 and z["arm"] in ARMS
                 and measurement["rep"] in range(REPS)
                 and z["public_meta_tasks"]==12
                 and z["novel_FIT_episodes"]==24
                 and z["CHECK_veto_only_episodes"]==8
                 and z["heldout_positive_episodes"]==8
                 and z["matched_negative_episodes"]==8
                 and z["whole_python_import_meta_fit_veto_heldout_process"]
                 and z["complete_OS_user_plus_system_CPU_ns"]>0
                 and z["complete_OS_peak_RSS_bytes"]>0
                 and not z["original_sci_cases_924_to_937_used"]
                 and not z["hidden_source_law_or_operator_label_given_to_model"]
                 and z["sourcefree_synthetic_only"]
                 and z["scientific_firstuse_consumed"]==0
                 and not z["scientific_acceptance"],
                 "FULL_NATIVE_FIT_VETO_AND_ORIGINAL_SOURCE_INTEGRITY")
            samples.setdefault(key,{})
            need(measurement["rep"] not in samples[key],
                 "DUPLICATE_ORIGINAL_OS_MEASUREMENT")
            samples[key][measurement["rep"]]=z
    allkeys={(f,s,a) for f in FAMILIES for s in SEEDS for a in ARMS}
    need(set(samples)==allkeys and all(set(d)==set(range(REPS)) for d in samples.values()),
         "ALL_144_PREREGISTERED_ORIGINAL_PROCESS_SAMPLES")
    for family in FAMILIES:
        for seed in SEEDS:
            shared=[samples[family,seed,a][0] for a in ARMS]
            for field in ("same_public_meta_SHA256","same_public_FIT_SHA256",
                          "same_public_CHECK_SHA256","same_public_unseen_SHA256"):
                need(len({x[field] for x in shared})==1,
                     "MATCHED_PAIRED_DATA_HASH_"+field)
    for group in samples.values():
        first=group[0]
        for rec in group.values():
            for field in ("FIT_naturally_fitted","CHECK_naturally_admitted",
                       "CHECK_full_trajectories_correct",
                       "diagnostic_full_heldout_positive_exact",
                       "diagnostic_full_hard_false_positives",
                       "diagnostic_bit_errors","CHECK_admitted_positive_exact",
                       "CHECK_admitted_hard_false_positives"):
                need(rec[field]==first[field],"REPEAT_INCONSISTENT_"+field)
    return samples,sha

def summarize(cases):
    out=[]
    for family in FAMILIES:
        for arm in ARMS:
            sample=[cases[family,seed,arm][0] for seed in SEEDS]
            osruns=[z for seed in SEEDS for z in cases[family,seed,arm].values()]
            out.append({
              "family":family,"arm":arm,
              "FIT_fitted_cases_of_4":sum(x["FIT_naturally_fitted"] for x in sample),
              "natural_CHECK_admitted_cases_of_4":sum(x["CHECK_naturally_admitted"] for x in sample),
              "CHECK_correct_full_episodes_of_32":sum(x["CHECK_full_trajectories_correct"] for x in sample),
              "diagnostic_positive_exact_of_32":sum(x["diagnostic_full_heldout_positive_exact"] or 0 for x in sample),
              "diagnostic_hard_false_positives_of_32":sum(x["diagnostic_full_hard_false_positives"] or 0 for x in sample),
              "admitted_positive_exact_of_32":sum(x["CHECK_admitted_positive_exact"] or 0 for x in sample),
              "admitted_hard_false_positives_of_32":sum(x["CHECK_admitted_hard_false_positives"] or 0 for x in sample),
              "not_fit_or_CHECK_means_no_admitted_heldout_scoring":True,
              "original_full_OS_process_samples":12,
              "median_full_CPU_ns":statistics.median(x["complete_OS_user_plus_system_CPU_ns"] for x in osruns),
              "median_full_peak_RSS_bytes":statistics.median(x["complete_OS_peak_RSS_bytes"] for x in osruns),
              "native_work_matched_FLOPs":False,
              "scientific_resource_nonregression_proven":False})
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--shards",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    x=p.parse_args()
    need(not x.out.exists(),"DO_NOT_OVERWRITE_AN_ORIGINAL_EVIDENCE_FILE")
    source,sha=examine(x.shards)
    findings=summarize(source)
    output={"schema":"mass.f124dc.complete-original-144-process-sourcefree.v1",
       "original_full_OS_records":[{"family":key[0],"seed":key[1],"arm":key[2],
          "repeat":r,"row":z} for key,group in sorted(source.items())
          for r,z in sorted(group.items())],
       "independent_shard_hashes":sha,"all_12_family_arm_findings":findings,
       "total_whole_linux_process_receipts":144,
       "original_external_source_independent_authentication":False,
       "scientific_original_firstuse_consumed":0,
       "protected_sources_opened":False,"science_accepted":False}
    x.out.mkdir(parents=True)
    (x.out/"original-complete-144-os.json").write_text(json.dumps(output,sort_keys=True,indent=2)+"\n")
    safe={"schema":"mass.f124dc.safe-structural-discovery-evidence.v1",
          "complete_144_receipts_sha256":digest(output),
          "results":findings,
          "original_model_processes":144,
          "externally_independent_source_born":False,
          "sourcefree_only":True,"scientific_success":False}
    (x.out/"source-safe-findings.json").write_text(json.dumps(safe,sort_keys=True,indent=2)+"\n")
    print("F124DC_INDEPENDENT_READONLY_144_ORIGINAL_PROCESS_AUDIT=PASS")
    for q in findings:print("F124DC_SOURCEFREE_STRUCTURAL_RESULT="+json.dumps(q,sort_keys=True))
    print("F124DC_NEW_REAL_SCI_FIRSTUSE=0")
    print("F124DC_SCIENTIFIC_ACCEPTANCE=FALSE")

if __name__=="__main__":main()
