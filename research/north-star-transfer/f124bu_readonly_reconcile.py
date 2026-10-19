"""F124-BU read-only authentic original GitHub native-workload evidence recount.

Input: GitHub provider's original same-source preflight and 20 real whole
process resource samples, downloaded unchanged. Do not import/execute model,
native scorer, benchmark generator or any protected source. No reruns.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import statistics

HERE=Path(__file__).resolve().parent
EXPECTED={
  "eligibility":("genuine-AZ-native-eligibility.json",
                 "7c4bb819064fe4809554299c05bb5aa9f83458a5ceda3995ba60b5b006ab9839"),
  "resource":("real-20-process-matched-native.json",
              "dec8a2d9df5935077049aa26ec5c32d396135f119326e315df5ec5ba943dccc5")}
CASES=("BU-SYN-01","BU-SYN-02")
ARMS=("AZ","learned")


def need(ok,label):
    if not ok:raise RuntimeError("F124BU_READONLY_ORIGINAL_"+label)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def check_file(folder,key,manifest):
    name,expected=EXPECTED[key]
    directory=Path(folder)
    need({p.name for p in directory.iterdir()}=={name,manifest},
         "EXACT_ORIGINAL_PROVIDER_FILES_"+key)
    raw=(directory/name).read_bytes()
    need(digest(raw)==expected,"EXACT_ORIGINAL_SHA_"+key)
    listing=(directory/manifest).read_text().splitlines()
    need(len(listing)==1 and listing[0].split()==[expected,name],
         "PREVIOUS_RUN_MANIFEST_"+key)
    return json.loads(raw)


def verify(pre_dir,cost_dir):
    sealed=json.loads((HERE/"f124bu-original-natural-native-resource-evidence.json").read_text())
    a=check_file(pre_dir,"eligibility","preflight.sha256")
    b=check_file(cost_dir,"resource","original-resource.sha256")
    need(a["schema"]=="mass.f124bu.natural-native-match-preflight.v1"
         and a["all_cases_naturally_eligible"] is True
         and a["all_cases_same_normalized_native_work"] is True
         and a["original_AZ_routing_forced"] is False
         and a["registered_sources_created"]==0
         and a["source_neutral_only_not_scientific_admission"] is True,
         "ACTUAL_UNFORCED_PROVIDER_ELIGIBILITY")
    need(b["schema"]=="mass.f124bu.naturally-routed-matched-workload-process-cost.v1"
         and b["fresh_process_samples"]==20
         and b["natural_original_AZ_route"] is True
         and b["never_forced_original_AZ_native_execution"] is True
         and b["native_input_and_actual_native_work_matched"] is True
         and b["whole_process_cost_per_case_nonregression"] is True
         and b["nonregistered_synthetic_only"] is True
         and b["new_prospective_924xxx_925xxx_sources"] is False
         and b["protected_cohorts_consumed"] is False
         and b["real_scientific_generalization_accepted"] is False
         and b["optimizer_policy_promoted"] is False,
         "ORIGINAL_20_WHOLE_PROCESS_NATIVE_BOUNDARY")
    need(len(b["original_20_unreplayed_process_receipts"])==20,
         "EXACT_REAL_OS_CASE_REPLICA_COUNT")
    res={}
    for case in CASES:
        p=a["cases"][case]
        e=sealed["cases"][case]
        need(p["AZ_original_natural_route"]=="affine"
             and p["AZ_scored_original_two_graphs"] is True
             and p["learned_original_native_calls"]==2
             and p["route_eligible_without_forcing"] is True
             and p["identical_normalized_native_inputs_and_full_outputs"] is True
             and p["original_public_graph_sha256"]==
                 e["source_neutral_full_public_graph_SHA256"]
             and p["AZ_native_call_input_hashes"]==
                 p["BQ_native_call_input_hashes"]==
                 e["identical_native_input_sha256_by_graph"]
             and p["AZ_native_call_output_hashes"]==
                 p["BQ_native_call_output_hashes"]==
                 e["identical_native_output_sha256_by_graph"],
             "ACTUAL_SAME_NATIVE_GRAPHS_SCORES_AND_COUNTERS_"+case)
        v=b["case_results"][case]
        need(v["same_work_full_OS_resource_noregression"] is True,
             "REAL_PER_CASE_RESOURCE_OUTCOME_"+case)
        arms={}
        for arm in ARMS:
            original_rows=[row for row in b["original_20_unreplayed_process_receipts"]
                           if row["case"]==case and row["arm"]==arm]
            need(len(original_rows)==5,"EXACT_FIVE_REAL_PROCESSES_"+case+arm)
            sealed_arm=e["measured"][arm]
            o=v[arm]
            cpu=[row["CPU_process_ns"] for row in original_rows]
            rss=[row["peak_OS_process_RSS_bytes"] for row in original_rows]
            need(cpu==sealed_arm["CPU_process_ns"]==o["CPU_samples_ns"]
                 and rss==sealed_arm["whole_peak_RSS_bytes"]==
                     o["peak_RSS_samples_bytes"]
                 and statistics.median(cpu)==
                     sealed_arm["CPU_median_ns"]==o["CPU_median_ns"]
                 and statistics.median(rss)==
                     sealed_arm["whole_peak_RSS_median_bytes"]==
                     o["peak_RSS_median_bytes"]
                 and max(rss)==sealed_arm["whole_peak_RSS_max_bytes"]==
                     o["peak_RSS_max_bytes"]
                 and o["native_scoring_outcome_SHA256"]==
                     e["identical_score_and_work_sha256"]
                 and o["allocator"]==sealed_arm["allocator"],
                 "ORIGINAL_SAMPLE_DATA_CHANGED_"+case+arm)
            need(all(row["native_calls"]==2
                     and row["natural_work_eligible"] is True
                     and row["original_AZ_forced_routing"] is False
                     and row["source_operator_passed_to_model"] is False
                     and row["original_case_firstuse"] is False
                     and row["protected_case_firstuse"] is False
                     and row["source_neutral_graph_SHA256"]==
                          e["source_neutral_full_public_graph_SHA256"]
                     and row["native_score_and_work_sha256"]==
                          e["identical_score_and_work_sha256"]
                     and row["scientific_acceptance"] is False
                     and row["route"]==
                         ("affine" if arm=="AZ" else "frozen_BQ_program")
                     for row in original_rows),
                 "TRUTHFUL_UNFORCED_ORIGINAL_WORK_PER_SAMPLE_"+case+arm)
            arms[arm]={"CPU_median_ns":statistics.median(cpu),
                       "RSS_median_bytes":statistics.median(rss),
                       "RSS_max_bytes":max(rss)}
        AZ=arms["AZ"];L=arms["learned"]
        need(L["CPU_median_ns"]<=AZ["CPU_median_ns"]
             and L["RSS_median_bytes"]<=AZ["RSS_median_bytes"]
             and L["RSS_max_bytes"]<=AZ["RSS_max_bytes"],
             "RECOUNT_STRICT_PER_CASE_SOURCE_NEUTRAL_PARITY_"+case)
        res[case]=arms
    flags=sealed["scientific_boundary"]
    need(flags["scientific_generalization_accepted"] is False
         and flags["prospective_924xxx_925xxx_registered_sources_used"] is False
         and flags["protected_BH_U_R_and_128_case_used"] is False
         and flags["previous_original_BM_BN_BO_BP_BQ_and_192_TRAIN_replayed"] is False
         and flags["original_AZ_route_forced"] is False
         and flags["optimizer_promoted"] is False,
         "RECONCILIATION_NO_SCIENTIFIC_PROMOTION")
    return {"schema":"mass.f124bu.readonly-independent-original-recount.v1",
            "provider_original_run":39219037991,
            "original_source_sha":"c3e2d62115225932842727ed7dbb6881c85b66de",
            "original_preflight_file_SHA256":EXPECTED["eligibility"][1],
            "original_20_process_file_SHA256":EXPECTED["resource"][1],
            "authenticated_original_process_sample_count":20,
            "naturally_routed_AZ_with_two_real_native_calls_each_case":True,
            "identical_native_inputs_scores_and_work":True,
            "strict_CPU_and_peak_RSS_resource_noregression_each_case":True,
            "recounted":res,
            "trained_model_or_source_executed_in_reconciliation":False,
            "actual_new_science_source_firstuse":False,
            "protected_holdout_used":False,
            "full_scientific_generalization_admission":False,
            "optimizer_policy_promotion":False}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--pre",type=Path,required=True)
    p.add_argument("--cost",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    result=verify(a.pre,a.cost)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,sort_keys=True)
        f.write("\n")
    print("F124BU_ORIGINAL_PROVIDER_ELIGIBLE_NATIVE_RECOUNT=PASS")
    print("F124BU_TWENTY_AUTHENTIC_NATIVE_PROCESS_RECEIPTS=PASS")
    print("F124BU_BOTH_SOURCE_NEUTRAL_WORKLOAD_MATCHED_COST_GATES=PASS")
    print("F124BU_ORIGINAL_BQ_AND_AZ_MODEL_EXECUTED_BY_AUDIT=false")
    print("F124BU_PROTECTED_FIRSTUSE=false")
    print("F124BU_TRANSFER_SCIENTIFIC_ACCEPTED=false")


if __name__=="__main__":
    main()
