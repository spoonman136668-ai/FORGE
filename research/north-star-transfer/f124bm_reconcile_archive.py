"""F124-BM read-only original archived FIT reconciliation; NO source execution.

Consumes only the immutable 65 files that were *actually archived* by the
original first-use run. Neither training, new source constructors, nor any
native/model code is imported. Fails closed on missing/tampered case identities.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

FIT={"GF2":range(914000,914016),"ARX":range(915000,915016)}
ARMS=("AZ","learned")
EXPECTED={
    "GF2":{"AZ_positive_accepted":16,"AZ_hard_FP":16,
           "AZ_abstain":0,"learned_positive_accepted":1,
           "learned_hard_FP":1,"learned_hard_FP_ids":[914011],
           "learned_baseline_positive_losses":15,
           "correct_candidate_pairs":0,"correct_AZ_pairs":0},
    "ARX":{"AZ_positive_accepted":0,"AZ_hard_FP":0,
           "AZ_abstain":16,"learned_positive_accepted":1,
           "learned_hard_FP":1,"learned_hard_FP_ids":[915009],
           "learned_baseline_positive_losses":0,
           "correct_candidate_pairs":0,"correct_AZ_pairs":0}
}
REQUIRED_CHILD={
    "schema","seed","arm","source_family",
    "same_public_and_graph_sha256","positive_graph_sha256",
    "hard_graph_sha256","positive_score","hard_negative_score",
    "positive_accepted","hard_negative_accepted",
    "private_symbolic_truth_only_for_evaluation","native_policy_trace",
    "task_CPU_ns","whole_process_peak_RSS_bytes",
    "original_TRAIN_replayed","original_BH_U_R_heldout_used",
    "BM_128case_holdout_used","science_accepted","optimizer_promotion"
}


def need(ok,code):
    if not ok:
        raise RuntimeError("F124BM_ORIGINAL_ARCHIVE_"+code)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def reconcile(folder):
    need(folder.is_dir(),"ARCHIVE_DIRECTORY")
    files={p.name:p for p in folder.iterdir() if p.is_file()}
    expected_files={
        "aggregated-prospective-FIT.json",
        *(f"firstuse_{seed}_{arm}.json"
          for group in FIT.values() for seed in group for arm in ARMS)
    }
    need(set(files)==expected_files,"EXACT_ORIGINAL_65_FILES")
    original_bytes={name:p.read_bytes() for name,p in files.items()}
    original=json.loads(original_bytes["aggregated-prospective-FIT.json"])
    need(set(original)=={"summary"},"ORIGINAL_AGGREGATE_SHAPE")
    orig=original["summary"]
    need(orig["schema"]==
         "mass.f124bm.first-original-fitscreen-source-blind-causal-contrast.v1"
         and orig["total_pair_count"]==32
         and orig["total_task_arm_evaluations"]==64
         and orig["FIT_gain_and_FP_constraints_met_in_both"] is False,
         "PREDECLARED_NEGATIVE_STATUS")
    for name in ("original_U_R_protected_used",
                 "BM_protected_128pair_cohorts_used",
                 "original_192_TRAIN_replayed",
                 "scientific_out_of_distribution_accepted",
                 "optimizer_policy_update"):
        need(orig[name] is False,"NO_PROTECTED_OR_POLICY_"+name)

    observed={}
    rows=[]
    for family,seeds in FIT.items():
        seed_rows=[]
        for seed in seeds:
            arm_records={}
            for arm in ARMS:
                file=f"firstuse_{seed}_{arm}.json"
                item=json.loads(original_bytes[file])
                need(REQUIRED_CHILD<=set(item),"CHILD_FIELDS")
                need(item["schema"]==
                     "mass.f124bm.original-frozen-prospective-public-FIT-only.v1"
                     and item["seed"]==seed and item["arm"]==arm
                     and item["source_family"]==family,
                     "SOURCE_CASE_IDENTITY")
                need(item["private_symbolic_truth_only_for_evaluation"]==
                     {"positive_routes":1,"hard_negative_routes":0},
                     "PRIVATE_LABEL_BOTH_TRUTH")
                need(item["positive_accepted"] is
                     (item["positive_score"]>=0)
                     and item["hard_negative_accepted"] is
                     (item["hard_negative_score"]>=0),
                     "EVALUATOR_PREDICTION_INTEGRITY")
                need(type(item["task_CPU_ns"]) is int
                     and item["task_CPU_ns"]>0
                     and type(item["whole_process_peak_RSS_bytes"]) is int
                     and item["whole_process_peak_RSS_bytes"]>0,
                     "RESOURCE_ORIGINAL")
                for flag in ("original_TRAIN_replayed",
                             "original_BH_U_R_heldout_used",
                             "BM_128case_holdout_used",
                             "science_accepted","optimizer_promotion"):
                    need(item[flag] is False,"UNAUTHORIZED_EVALUATION")
                need(item["native_policy_trace"][
                     "original_scientific_policy"] is True,
                     "FROZEN_ORIGINAL_POLICY")
                arm_records[arm]=(item,digest(original_bytes[file]))
            az,ash=arm_records["AZ"]
            learned,lsh=arm_records["learned"]
            for field in ("same_public_and_graph_sha256",
                          "positive_graph_sha256","hard_graph_sha256"):
                need(az[field]==learned[field],"SAME_SOURCE_"+field)
            row={
                "seed":seed,"source_family":family,
                "public_case_sha256":az["same_public_and_graph_sha256"],
                "AZ_positive":az["positive_accepted"],
                "AZ_hard_FP":az["hard_negative_accepted"],
                "AZ_abstain":az["native_policy_trace"]["policy_abstained"],
                "learned_positive":learned["positive_accepted"],
                "learned_hard_FP":learned["hard_negative_accepted"],
                "AZ_raw_receipt_sha256":ash,
                "learned_raw_receipt_sha256":lsh,
                "AZ_task_CPU_ns":az["task_CPU_ns"],
                "learned_task_CPU_ns":learned["task_CPU_ns"],
                "AZ_OS_peak_RSS":az["whole_process_peak_RSS_bytes"],
                "learned_OS_peak_RSS":learned["whole_process_peak_RSS_bytes"]
            }
            seed_rows.append(row)
            rows.append(row)
        actual={
            "AZ_positive_accepted":sum(r["AZ_positive"] for r in seed_rows),
            "AZ_hard_FP":sum(r["AZ_hard_FP"] for r in seed_rows),
            "AZ_abstain":sum(r["AZ_abstain"] for r in seed_rows),
            "learned_positive_accepted":sum(r["learned_positive"] for r in seed_rows),
            "learned_hard_FP":sum(r["learned_hard_FP"] for r in seed_rows),
            "learned_hard_FP_ids":[r["seed"] for r in seed_rows
                                   if r["learned_hard_FP"]],
            "learned_baseline_positive_losses":sum(
                r["AZ_positive"] and not r["learned_positive"]
                for r in seed_rows),
            "correct_candidate_pairs":sum(
                r["learned_positive"] and not r["learned_hard_FP"]
                for r in seed_rows),
            "correct_AZ_pairs":sum(
                r["AZ_positive"] and not r["AZ_hard_FP"] for r in seed_rows)
        }
        need(actual==EXPECTED[family],"PREDEFINED_NEGATIVE_COUNTS_"+family)
        original_group=orig["families"][family]
        need(original_group["candidate_positive_count"]==
             actual["learned_positive_accepted"]
             and original_group["baseline_positive_count"]==
             actual["AZ_positive_accepted"]
             and len(original_group["candidate_hard_false_positive_ids"])==
             actual["learned_hard_FP"]
             and len(original_group["baseline_positive_lost_ids"])==
             actual["learned_baseline_positive_losses"]
             and original_group["FIT_mechanistic_gate"] is False,
             "ORIGINAL_SUMMARY_DISAGREEMENT_"+family)
        observed[family]=actual

    return {
        "schema":"mass.f124bm.custody-original-provider-firstuse-negative.v1",
        "original_run_id":39180767870,
        "original_exact_head":"98e1ccae79af2ab3f21173f7827dd4627ff64895",
        "original_artifact_id":12156221004,
        "original_artifact_digest":"sha256:3ef60ff75f92038c69082dc7a2be2d3c58d851145951551b3646117865062b2b",
        "original_raw_aggregate_sha256":digest(original_bytes[
            "aggregated-prospective-FIT.json"]),
        "independently_recounted_from_64_original_receipts":observed,
        "source_cases_consumed_once":32,
        "frozen_arm_evaluations":64,
        "per_original_case_custody_and_resource":rows,
        "original_firstuse_reporting_step_failed_after_result":True,
        "source_regenerated_in_reconciliation":False,
        "source_model_imported_in_reconciliation":False,
        "original_BH_U_R_used":False,
        "BM_128case_protected_holdout_used":False,
        "original_192_TRAIN_replayed":False,
        "scientific_transfer_success":False,
        "protected_scientific_admission":False,
        "thirdparty_origin_witnessed":False,
        "optimizer_promotion":False,
        "disposition":"VALID_PROSPECTIVE_FIT_NEGATIVE_WITH_ORIGINAL_RAW_CUSTODY"
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original-dir",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    data=reconcile(a.original_dir)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(data,sort_keys=True,indent=2)+"\n").encode()
    with a.output.open("xb") as f:
        f.write(raw)
    print("F124BM_RECONCILED_ORIGINAL_CASES=32")
    print("F124BM_RECONCILED_ORIGINAL_RECORDS=64")
    print("F124BM_FIT_TRANSFER_GATE=FAIL")
    print("F124BM_SCIENCE_PROMOTION=false")
    print("F124BM_SOURCE_CONSTRUCTION_IN_RECOVERY=0")
    print("F124BM_RECONCILED_SHA256="+digest(raw))


if __name__=="__main__":
    main()
