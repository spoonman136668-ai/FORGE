"""F124-DD separately executed read-only original 240 CPU/RSS receipt audit.

No new source author, candidate, peer, or first-use import. Verifies
eight nonoverlapping exact sourcefree shards, full 5 repetitions for each
of 4 causal families × 4 seeds × 3 models, paired data identities,
natural abstentions, correctness, CPU and RSS custody.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import statistics

FAMILIES=("fresh-ternary-compiler-sanity","four-input-parity-conjunction",
          "four-input-selector-with-interaction","nibble-addition-carry-out-of-bitwise")
SEEDS=(81,82,83,84)
ARMS=("compact_meta_NAND","independent_compact_meta_ANF","slow_meta_NAND_DAG")
REPS=5

def need(ok,reason):
    if not ok:raise RuntimeError("F124DD_AUDIT_"+reason)

def digest(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def read_original_shards(dir):
    files=list(dir.glob("shard-*.json"))
    expected={"shard-"+family+"-"+str(seed)+".json"
              for family in FAMILIES for seed in (81,83)}
    need(len(files)==8 and {f.name for f in files}==expected,
         "EXACT_EIGHT_ORIGINAL_SOURCEFREE_SHARDS")
    docs=[]
    roster={}
    for file in files:
        doc=json.loads(file.read_text())
        need(doc["schema"]=="mass.f124dd.sourcefree-original-30-process-shard.v1"
             and len(doc["original_measurements"])==30
             and doc["full_OS_processes"]==30
             and doc["authentic_scientific_firstuse_consumed"]==0
             and not doc["external_independent_source_origin"]
             and not doc["scientific_success"],"ORIGINAL_SOURCEFREE_PROVIDER_INTEGRITY")
        docs.append({"name":file.name,"sha256":digest(doc)})
        for x in doc["original_measurements"]:
            z=x["original_process"]
            key=z["family"],z["seed"],z["arm"]
            need(z["schema"]=="mass.f124dd.sourcefree-compact-operator-original-trial.v1"
                 and z["family"]==doc["family"]
                 and z["seed"] in (doc["first_seed"],doc["first_seed"]+1)
                 and z["arm"] in ARMS and x["repeat"] in range(REPS)
                 and z["meta_public_task_count"]==12
                 and z["FIT_full_episodes"]==24
                 and z["CHECK_veto_episodes"]==8
                 and z["heldout_positive_episodes"]==8
                 and z["matched_negative_episodes"]==8
                 and z["source_law_hidden_from_all_arms"]
                 and z["meta_trained_from_same_public_data"]
                 and not z["old_924_to_937_source_ids_used"]
                 and not z["old_DC_sciencefree_holdouts_reused"]
                 and z["sourcefree_synthetic_only"]
                 and z["new_original_scientific_firstuse"]==0
                 and not z["scientific_accepted"]
                 and z["OS_measurement_includes_import_meta_fit_compilation_CHECK_and_heldout"]
                 and z["whole_OS_CPU_user_system_ns"]>0
                 and z["whole_OS_peak_RSS_bytes"]>0,
                 "COMPLETE_OS_NATIVE_AND_SOURCE_PRIVACY_CONTRACT")
            roster.setdefault(key,{})
            need(x["repeat"] not in roster[key],"DUPLICATE_ORIGINAL_PROCESS_ID")
            roster[key][x["repeat"]]=z
    expected_keys={(fam,seed,arm) for fam in FAMILIES for seed in SEEDS for arm in ARMS}
    need(set(roster)==expected_keys and all(set(q)==set(range(REPS))
         for q in roster.values()),"COMPLETE_240_OS_RECEIPTS_FIXED_ROSTER")
    for family in FAMILIES:
        for seed in SEEDS:
            paired=[roster[family,seed,arm][0] for arm in ARMS]
            for field in ("meta_task_public_sha256","FIT_public_sha256",
                          "CHECK_public_sha256","holdout_public_sha256"):
                need(len({x[field] for x in paired})==1,
                     "STRONG_CONTROLS_RECEIVED_NONIDENTICAL_PUBLIC_SOURCE_"+field)
    for sourcecase in roster.values():
        exemplar=sourcecase[0]
        for x in sourcecase.values():
            for field in ("FIT_naturally_fitted","CHECK_naturally_admitted",
                          "CHECK_correct_full_trajectories",
                          "diagnostic_heldout_positive_exact",
                          "diagnostic_hard_false_positives",
                          "diagnostic_positive_bit_errors",
                          "CHECK_admitted_positive_exact","CHECK_admitted_hard_false_positives"):
                need(x[field]==exemplar[field],
                     "NATIVE_REPEATED_LEARNING_SOURCE_DRIFT_"+field)
    return roster,docs

def aggregate(roster):
    out=[]
    for family in FAMILIES:
        for arm in ARMS:
            cases=[roster[family,seed,arm][0] for seed in SEEDS]
            osrows=[row for seed in SEEDS for row in roster[family,seed,arm].values()]
            out.append({
               "family":family,"arm":arm,
               "FIT_natural_cases":sum(x["FIT_naturally_fitted"] for x in cases),
               "CHECK_admitted_cases_of_4":sum(x["CHECK_naturally_admitted"] for x in cases),
               "CHECK_exact_full_episodes_of_32":sum(x["CHECK_correct_full_trajectories"] for x in cases),
               "diagnostic_heldout_positives_exact_of_32":sum(x["diagnostic_heldout_positive_exact"] or 0 for x in cases),
               "diagnostic_hard_false_positives_of_32":sum(x["diagnostic_hard_false_positives"] or 0 for x in cases),
               "admitted_positives_of_32":sum(x["CHECK_admitted_positive_exact"] or 0 for x in cases),
               "admitted_hard_false_positives_of_32":sum(x["CHECK_admitted_hard_false_positives"] or 0 for x in cases),
               "no_fit_means_not_scored":True,
               "original_OS_process_samples":20,
               "median_complete_OS_CPU_ns":statistics.median(x["whole_OS_CPU_user_system_ns"] for x in osrows),
               "median_complete_OS_peak_RSS_bytes":statistics.median(x["whole_OS_peak_RSS_bytes"] for x in osrows),
               "maximum_complete_OS_peak_RSS_bytes":max(x["whole_OS_peak_RSS_bytes"] for x in osrows),
               "matched_native_internal_FLOPs_verified":False,
               "scientific_resource_nonregression_approved":False})
    return out

def decide(results):
    r={(x["family"],x["arm"]):x for x in results}
    decisions=[]
    for family in FAMILIES[1:3]:
        a=r[family,"compact_meta_NAND"]
        b=r[family,"independent_compact_meta_ANF"]
        good=a["CHECK_admitted_cases_of_4"]==b["CHECK_admitted_cases_of_4"]==4
        good=good and a["admitted_positives_of_32"]==b["admitted_positives_of_32"]==32
        good=good and a["admitted_hard_false_positives_of_32"]==b["admitted_hard_false_positives_of_32"]==0
        faster=a["median_complete_OS_CPU_ns"]<=b["median_complete_OS_CPU_ns"]
        decisions.append({"family":family,
                          "causal_correctness_tied":good,
                          "candidate_complete_CPU_ns":a["median_complete_OS_CPU_ns"],
                          "equal_peer_complete_CPU_ns":b["median_complete_OS_CPU_ns"],
                          "candidate_vs_peer_median_CPU_ratio":round(
                            a["median_complete_OS_CPU_ns"]/b["median_complete_OS_CPU_ns"],4),
                          "candidate_CPU_not_worse":faster,
                          "frozen_cost_gate_accepted":good and faster})
    return decisions

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--shards",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    need(not args.out.exists(),"NO_OVERWRITE_ORIGINAL_CUSTODY")
    obs,sha=read_original_shards(args.shards)
    findings=aggregate(obs)
    decisions=decide(findings)
    report={"schema":"mass.f124dd.complete-original-240-sourcefree-native.v1",
            "all_native_processes":[{"family":k[0],"seed":k[1],"arm":k[2],"repeat":idx,"row":row}
                                    for k,group in sorted(obs.items())
                                    for idx,row in sorted(group.items())],
            "eight_original_artifact_shard_hashes":sha,
            "all_12_family_arm_findings":findings,
            "strict_frozen_per_family_cpu_gate":decisions,
            "new_original_scientific_firstuse_consumed":0,
            "independently_authenticated_new_source_families":False,
            "science_accepted":False}
    args.out.mkdir(parents=True)
    (args.out/"original-complete-240-os.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    safe={"schema":"mass.f124dd.sourcefree-compact-qual-summary.v1",
          "all_240_receipt_sha256":digest(report),"aggregated_findings":findings,
          "strict_cost_gate":decisions,
          "all_original_OS_processes":240,"scientific_success":False}
    (args.out/"source-safe-findings.json").write_text(json.dumps(safe,sort_keys=True,indent=2)+"\n")
    print("F124DD_INDEPENDENT_ALL_240_WHOLE_OS_PROCESS_AUDIT=PASS")
    for row in findings:print("F124DD_ORIGINAL_SOURCEFREE_FINDING="+json.dumps(row,sort_keys=True))
    for row in decisions:print("F124DD_FROZEN_CPU_GATE="+json.dumps(row,sort_keys=True))
    print("F124DD_SCIENTIFIC_FIRSTUSE=0")
    print("F124DD_SCIENTIFIC_ACCEPTANCE=FALSE")

if __name__=="__main__":main()
