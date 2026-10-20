"""F124-DE independent no-retraining audit of 144 new sourcefree OS samples.

No source/task author, candidate, or independent comparator import; read
provider originals ONLY. Verify exact eight fixed shards, 4x4x3x3 condition
roster, public FIT/CHECK/unseen identity, real complete OS CPU/RSS,
natural CHECK veto, and fresh source nonreuse. Observe failures honestly.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import statistics
FAMILIES=("novel-carry-nibble-add","novel-rotate-after-add",
          "fresh-bitwise-crossrole-check","three-nibble-unseen-negative")
SEEDS=(91,92,93,94)
ARMS=("sparse_crossbit_compact","independent_equal_degree4_ANF","prior_optimized_bitwise_ANF")
REPS=3
def need(ok,why):
    if not ok:raise RuntimeError("F124DE_INDEPENDENT_AUDIT_"+why)
def digest(z):
    return hashlib.sha256(json.dumps(z,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def read(directory):
    files=list(directory.glob("shard-*.json"))
    expected={"shard-"+family+"-"+str(start)+".json"
              for family in FAMILIES for start in (91,93)}
    need(len(files)==8 and {f.name for f in files}==expected,
         "EXACT_8_FRESH_ORIGINAL_SOURCEFREE_SHARDS")
    samples={};shardhash=[]
    for path in files:
        item=json.loads(path.read_text())
        need(item["schema"]=="mass.f124de.original-sourcefree-18-OS-measurements.v1"
             and len(item["whole_OS_samples"])==18
             and item["sourcefree_original_OS_processes"]==18
             and not item["independently_birthed_scientific_sources"]
             and item["science_firstuse_consumed"]==0
             and not item["scientific_acceptance"],"SOURCEFREE_SHARD_CUSTODY")
        shardhash.append({"original_filename":path.name,"sha256":digest(item)})
        for observation in item["whole_OS_samples"]:
            row=observation["row"]
            key=(row["family"],row["seed"],row["arm"])
            need(row["schema"]=="mass.f124de.original-sourcefree-crossbit-trial.v1"
                 and row["family"]==item["family"]
                 and row["seed"] in (item["first_seed"],item["first_seed"]+1)
                 and row["arm"] in ARMS and observation["rep"] in range(REPS)
                 and row["FIT_episodes"]==24
                 and row["CHECK_veto_only_episodes"]==8
                 and row["untouched_heldout_positive_episodes"]==8
                 and row["matched_crossrole_negatives"]==8
                 and row["events_per_episode"]==8
                 and row["source_private_formula_not_given_to_model"]
                 and row["unrestricted_256_entry_nibble_operator_not_identifiable_from_192_rows"]
                 and row["sourcefree_only"]
                 and not row["science_original_924_to_937_accessed"]
                 and not row["prior_F124DD_81_to_84_used"]
                 and row["new_scientific_firstuse_consumed"]==0
                 and not row["independent_external_source_birth"]
                 and not row["science_accepted"]
                 and row["OS_includes_python_import_meta_FIT_native_compilation_CHECK_heldout"]
                 and row["full_OS_CPU_user_system_ns"]>0
                 and row["full_OS_peak_RSS_bytes"]>0,
                 "FULL_ORIGINAL_OS_AND_PRIVACY_BOUNDARY")
            samples.setdefault(key,{})
            need(observation["rep"] not in samples[key],"DUPLICATE_ORIGINAL_OS_REPETITION")
            samples[key][observation["rep"]]=row
    expected_keys={(f,s,a) for f in FAMILIES for s in SEEDS for a in ARMS}
    need(set(samples)==expected_keys and all(set(v)==set(range(REPS))
         for v in samples.values()),"ALL_144_AUTHENTIC_NATIVE_OS_RECORDS")
    for f in FAMILIES:
        for seed in SEEDS:
            paired=[samples[f,seed,arm][0] for arm in ARMS]
            for col in ("meta_public_SHA256","FIT_public_SHA256",
                        "CHECK_public_SHA256","heldout_public_SHA256"):
                need(len({r[col] for r in paired})==1,
                     "DIFFERENT_PUBLIC_SOURCE_ASYMMETRY_"+col)
    for rows in samples.values():
        q=rows[0]
        for z in rows.values():
            for key in ("natural_FIT","natural_CHECK_admission",
                        "CHECK_correct_complete_episodes",
                        "diagnostic_heldout_positive_exact",
                        "diagnostic_hard_false_positives",
                        "admitted_positive_exact","admitted_hard_false_positives"):
                need(z[key]==q[key],"SAME_FIXED_CASE_REPEAT_NOT_DETERMINISTIC_"+key)
    return samples,shardhash

def aggregate(samples):
    output=[]
    for f in FAMILIES:
        for arm in ARMS:
            cases=[samples[f,s,arm][0] for s in SEEDS]
            osrows=[row for s in SEEDS for row in samples[f,s,arm].values()]
            output.append({
              "family":f,"arm":arm,
              "FIT_naturally_fitted_cases_of_4":sum(x["natural_FIT"] for x in cases),
              "CHECK_naturally_admitted_cases_of_4":sum(x["natural_CHECK_admission"] for x in cases),
              "CHECK_complete_correct_episodes_of_32":sum(x["CHECK_correct_complete_episodes"] for x in cases),
              "diagnostic_unseen_positives_exact_of_32":sum(x["diagnostic_heldout_positive_exact"] or 0 for x in cases),
              "diagnostic_hard_false_positive_of_32":sum(x["diagnostic_hard_false_positives"] or 0 for x in cases),
              "CHECK_admitted_exact_positives_of_32":sum(x["admitted_positive_exact"] or 0 for x in cases),
              "CHECK_admitted_hard_false_positives_of_32":sum(x["admitted_hard_false_positives"] or 0 for x in cases),
              "mean_FIT_pair_visibility_upper_bound":sum(x["FIT_possible_pair_unique_cell_max"] for x in cases)/4,
              "unfitted_means_not_scored":True,
              "original_full_OS_process_count":12,
              "median_complete_OS_CPU_ns":statistics.median(x["full_OS_CPU_user_system_ns"] for x in osrows),
              "median_complete_OS_peak_RSS_bytes":statistics.median(x["full_OS_peak_RSS_bytes"] for x in osrows),
              "matched_internal_native_FLOPs":False,
              "scientific_resource_nonregression_approved":False})
    return output

def prespecified_decision(rows):
    r={(x["family"],x["arm"]):x for x in rows}
    decision=[]
    for family in FAMILIES[:2]:
        c=r[family,"sparse_crossbit_compact"]
        p=r[family,"independent_equal_degree4_ANF"]
        tied=(c["CHECK_naturally_admitted_cases_of_4"]==
              p["CHECK_naturally_admitted_cases_of_4"]==4
              and c["CHECK_admitted_exact_positives_of_32"]==
                  p["CHECK_admitted_exact_positives_of_32"]==32
              and c["CHECK_admitted_hard_false_positives_of_32"]==
                  p["CHECK_admitted_hard_false_positives_of_32"]==0)
        fast=c["median_complete_OS_CPU_ns"]<=p["median_complete_OS_CPU_ns"]
        rss=c["median_complete_OS_peak_RSS_bytes"]<=p["median_complete_OS_peak_RSS_bytes"]
        decision.append({
          "family":family,
          "equal_capability_32_exact_0_hard_FP":tied,
          "candidate_to_peer_complete_CPU_ratio":round(c["median_complete_OS_CPU_ns"]/p["median_complete_OS_CPU_ns"],5),
          "candidate_to_peer_complete_RSS_ratio":round(c["median_complete_OS_peak_RSS_bytes"]/p["median_complete_OS_peak_RSS_bytes"],5),
          "full_OS_CPU_noregression":fast,"full_OS_RSS_noregression":rss,
          "strict_prespecified_CPU_and_RSS_gate_pass":tied and fast and rss,
          "internal_native_FLOP_parity_verified":False})
    return decision

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--shards",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    z=p.parse_args()
    need(not z.out.exists(),"ORIGINAL_CUSTODY_FILE_MUST_NOT_EXIST")
    cases,sha=read(z.shards)
    outcomes=aggregate(cases);decisions=prespecified_decision(outcomes)
    report={"schema":"mass.f124de.independent-full-144-os-sourcefree.v1",
       "all_144_original_measurements":[{"family":key[0],"seed":key[1],"arm":key[2],
          "rep":i,"row":q} for key,group in sorted(cases.items())
          for i,q in sorted(group.items())],
       "eight_original_shard_hashes":sha,
       "all_family_arm_results":outcomes,
       "strict_two_nonbitwise_sourcefree_decisions":decisions,
       "independent_external_scientific_source_birthed":False,
       "new_scientific_firstuse_consumed":0,
       "scientific_success":False}
    z.out.mkdir(parents=True)
    (z.out/"full-144-sourcefree-native-evidence.json").write_text(
         json.dumps(report,sort_keys=True,indent=2)+"\n")
    safe={"schema":"mass.f124de.safe-crossbit-original-summary.v1",
      "complete_144_OS_digest_SHA256":digest(report),
      "aggregates":outcomes,"prespecified_cost_admission":decisions,
      "scientific_original_firstuse":0,"scientific_accepted":False}
    (z.out/"source-safe-findings.json").write_text(json.dumps(safe,sort_keys=True,indent=2)+"\n")
    print("F124DE_INDEPENDENT_ALL_144_WHOLE_OS_RECEIPTS=PASS")
    for row in outcomes:print("F124DE_ORIGINAL_SOURCEFREE_RESULT="+json.dumps(row,sort_keys=True))
    for row in decisions:print("F124DE_STRICT_CPU_RSS_GATE="+json.dumps(row,sort_keys=True))
    print("F124DE_ORIGINAL_SCI_FIRSTUSE=0")
if __name__=="__main__":main()
