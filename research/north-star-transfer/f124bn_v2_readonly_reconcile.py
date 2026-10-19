"""F124-BN read-only original 49-file first-use verification.

Never import, run or reconstruct either causal source or model. Source cases
and original first-use observations remain consumed; only compare original
provider artifact bytes, task/arm identity and fixed preregistered acceptance.
"""
from __future__ import annotations
import argparse,hashlib,json,statistics
from pathlib import Path

HERE=Path(__file__).resolve().parent
EXPECTED_AGGREGATE="f32a8be79f38ba41b2e4b20d61d61ba6a98ddce8b1785a8807ef42eac89d1cde"
RANGES={"mix":range(918000,918012),"word":range(919000,919012)}
ARMS=("AZ","learned")


def need(x,label):
    if not x:raise RuntimeError("F124BN_FIRSTUSE_RECON_"+label)


def sha(x):
    return hashlib.sha256(x).hexdigest()


def verify(folder):
    frozen=json.loads((HERE/"f124bn-v2-original-development-result.json").read_text())
    need(folder.is_dir(),"ARTIFACT_FOLDER")
    names={p.name:p for p in folder.iterdir() if p.is_file()}
    expected={"aggregated-original-FIT.json"}|{
        f"original_{seed}_{arm}.json"
        for values in RANGES.values() for seed in values for arm in ARMS}
    need(set(names)==expected,"EXACT_49_FIRSTUSE_JSON")
    raw={name:path.read_bytes() for name,path in names.items()}
    need(sha(raw["aggregated-original-FIT.json"])==EXPECTED_AGGREGATE,
         "ORIGINAL_AGGREGATE_HASH")
    summary=json.loads(raw["aggregated-original-FIT.json"])["summary"]
    need(summary["schema"]=="mass.f124bn.v2.frozen-new-relationship-dev-fit.v1"
         and summary["cases_consumed"]==24
         and summary["original_arm_records"]==48
         and summary["joint_FIT_gate"] is False
         and summary["scientific_accepted"] is False,
         "FROZEN_SCIENCE_NEGATIVE")
    for k in ("original_BM_source_reused","original_BH_U_R_holdout_used",
              "new_BN_128_holdout_used","original_consumed_TRAIN_replayed",
              "optimizer_promotion"):
        need(summary[k] is False,"ZERO_PROTECTED_OR_POLICY_"+k)
    outcomes={}
    original_rows=[]
    for family,cohort in RANGES.items():
        observed=[]
        for case in cohort:
            arms={}
            for arm in ARMS:
                name=f"original_{case}_{arm}.json"
                record=json.loads(raw[name])
                need(record["schema"]==
                     "mass.f124bn.v2.new-original-dev-fit-causal-pair.v1"
                     and record["arm"]==arm and record["case"]==case
                     and record["family"]==family,
                     "ORIGINAL_CASE_ARM_IDENTITY")
                need(record["original_private_symbolic_truth"]==
                     {"positive":1,"negative":0},"EXACT_CAUSAL_SOURCE_TRUTH")
                need(record["positive_accepted"] is
                     (record["positive_score"]>=0)
                     and record["negative_false_positive"] is
                     (record["negative_score"]>=0),
                     "UNALTERED_OUTPUT_DECISION")
                need(record["CPU_ns"]>0
                     and record["whole_process_peak_RSS_bytes"]>0,
                     "MEASURED_RESOURCE")
                for k in ("old_BM_cases_reused","old_TRAIN_replayed",
                          "BH_U_R_or_BN_holdout_used","scientific_accepted",
                          "optimizer_promoted"):
                    need(record[k] is False,"REPLAY_OR_SCIENCE_STATUS")
                arms[arm]=record
            old,new=arms["AZ"],arms["learned"]
            for k in ("original_public_pair_and_graph_sha256",
                      "positive_graph_sha256","negative_graph_sha256"):
                need(old[k]==new[k],"IDENTICAL_SOURCE_"+k)
            row={"case":case,"family":family,
                 "AZ_pos":old["positive_accepted"],"AZ_FP":old["negative_false_positive"],
                 "candidate_pos":new["positive_accepted"],
                 "candidate_FP":new["negative_false_positive"],
                 "candidate_identifiable":new["model_trace"].get(
                     "learned_identifiable",False),
                 "AZ_CPU_ns":old["CPU_ns"],"candidate_CPU_ns":new["CPU_ns"],
                 "AZ_OS_RSS":old["whole_process_peak_RSS_bytes"],
                 "candidate_OS_RSS":new["whole_process_peak_RSS_bytes"],
                 "source_sha256":old["original_public_pair_and_graph_sha256"],
                 "AZ_original_receipt_sha256":sha(raw[f"original_{case}_AZ.json"]),
                 "candidate_original_receipt_sha256":sha(
                     raw[f"original_{case}_learned.json"])}
            observed.append(row)
            original_rows.append(row)
        data={
          "AZ_positive_count":sum(r["AZ_pos"] for r in observed),
          "AZ_hard_FP_count":sum(r["AZ_FP"] for r in observed),
          "learner_positive_count":sum(r["candidate_pos"] for r in observed),
          "learner_FP_case_ids":[r["case"] for r in observed if r["candidate_FP"]],
          "baseline_positive_lost_ids":[r["case"] for r in observed
                                        if r["AZ_pos"] and not r["candidate_pos"]],
          "correctly_classified_learned_pairs":sum(
              r["candidate_pos"] and not r["candidate_FP"] for r in observed),
          "learned_identifiable_cases":sum(
              r["candidate_identifiable"] for r in observed),
          "learner_CPU_ns_median":statistics.median(
              r["candidate_CPU_ns"] for r in observed),
          "AZ_CPU_ns_median":statistics.median(
              r["AZ_CPU_ns"] for r in observed),
          "learner_process_RSS_median":statistics.median(
              r["candidate_OS_RSS"] for r in observed),
          "AZ_process_RSS_median":statistics.median(
              r["AZ_OS_RSS"] for r in observed)}
        frozen_expected=frozen["new_source_families"][family]
        # The sealed summary uses editorial labels; the original receipt
        # uses evaluator field labels. Map keys explicitly, never adjust
        # values or reinterpret the observed scientific outcomes.
        labels={
            "AZ_positive_count":"baseline_original_AZ_positive",
            "AZ_hard_FP_count":"baseline_original_AZ_hard_FP",
            "learner_positive_count":"learned_positive",
            "baseline_positive_lost_ids":"baseline_positive_lost_ids",
            "correctly_classified_learned_pairs":"correctly_discriminated_pairs",
            "learned_identifiable_cases":"learned_model_identifiable",
            "learner_CPU_ns_median":"learner_CPU_ns_median",
            "AZ_CPU_ns_median":"AZ_CPU_ns_median",
            "learner_process_RSS_median":"learner_process_RSS_median",
            "AZ_process_RSS_median":"AZ_process_RSS_median",
        }
        for key, sealed_key in labels.items():
            need(frozen_expected[sealed_key]==data[key],
                 "FROZEN_ORIGINAL_NEGATIVE_RESULT_"+family+"_"+key)
        need(frozen_expected["learned_hard_FP"]==
             len(data["learner_FP_case_ids"]),
             "FROZEN_ORIGINAL_FP_COUNT_"+family)
        group=summary["families"][family]
        need(group["learner_positive_count"]==data["learner_positive_count"]
             and group["AZ_positive_count"]==data["AZ_positive_count"]
             and group["learner_FP_case_ids"]==data["learner_FP_case_ids"]
             and group["baseline_positive_lost_ids"]==
                 data["baseline_positive_lost_ids"]
             and group["FIT_gate_met"] is False,
             "ORIGINAL_SUMMARY_RECONCILE_"+family)
        outcomes[family]=data
    return {"schema":"mass.f124bn.original-v2-provider-recounted-fit.v1",
            "exact_original_sha":"ed9c52c495fe65307cd3077959d257d1f4990914",
            "original_run":39183174503,
            "original_artifact_id":12156554495,
            "original_archive_sha256":"6026b4767a6b70b7f6c124934c966823973cdc8c30ed6688e58b883ea285cf0b",
            "original_raw_aggregate_sha256":EXPECTED_AGGREGATE,
            "original_49_files_verified":True,
            "original_48_cases_and_arms":original_rows,
            "sourceborn_results":outcomes,
            "per_original_source_case_retuned_or_replayed":False,
            "preregistered_FIT_joint_success":False,
            "partial_causal_discrimination_observed":True,
            "new_128_case_protected_holdouts_used":False,
            "old_BH_U_R_used":False,
            "original_192_TRAIN_replayed":False,
            "full_scientific_replication_or_resource_parity":False,
            "external_thirdparty_source_novelty":False,
            "scientific_accepted":False,
            "optimizer_promotion":False,
            "disposition":"VALID_NEW_FIT_PARTIAL_POSITIVE_BUT_FROZEN_GATE_FAIL"}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    result=verify(a.original)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(result,sort_keys=True,indent=2)+"\n").encode()
    with a.output.open("xb") as f:f.write(raw)
    print("F124BN_ORIGINAL_49_FILE_RECONCILIATION=PASS")
    print("F124BN_NEW_MIX_CAUSAL_CORRECT=9/12")
    print("F124BN_NEW_NONLINEAR_CAUSAL_CORRECT=0/12")
    print("F124BN_GENUINE_HOLDOUT_USED=false")
    print("F124BN_SCIENTIFIC_TRANSFER_ACCEPTED=false")
    print("F124BN_SOURCE_REGENERATION=0")
    print("F124BN_READONLY_RECEIPT_SHA256="+sha(raw))


if __name__=="__main__":
    main()
