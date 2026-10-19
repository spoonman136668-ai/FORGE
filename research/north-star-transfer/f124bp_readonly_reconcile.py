"""F124-BP independent read-only reconciliation of original 49 JSON receipts.

Never import, instantiate or run registered source generators, original AZ,
the learned model, any protected holdout or previously consumed TRAIN cases.
Read only provider-original bytes. Reject missing, copied or altered receipts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics

HERE=Path(__file__).resolve().parent
COHORT={"procedural":range(922000,922012),
        "feedback":range(923000,923012)}
ARMS=("AZ","compact")
AGG_SHA256="19f16929782f05144ee8afcd2bf4d24c6c2fd6c3096e2b35e81f0332b58d226b"


def need(ok,label):
    if not ok:raise RuntimeError("F124BP_ORIGINAL_ARCHIVE_"+label)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def reconcile(original):
    need(original.is_dir(),"UNMOUNTED_ORIGINAL_PROVIDER_ARTIFACT")
    files={p.name:p for p in original.iterdir() if p.is_file()}
    expected={"aggregated-original-FIT.json","firstuse-sha256.txt"}|{
        f"firstuse_{case}_{arm}.json"
        for cohort in COHORT.values() for case in cohort for arm in ARMS}
    need(set(files)==expected and len(files)==50,
         "ORIGINAL_50_ARCHIVED_FILES")
    raw={filename:file.read_bytes() for filename,file in files.items()}
    manifest=raw["firstuse-sha256.txt"].decode().splitlines()
    need(len(manifest)==49,"ORIGINAL_MANIFEST_49")
    witnessed=set()
    for line in manifest:
        parts=line.split()
        need(len(parts)==2 and len(parts[0])==64,"MANIFEST_FORMAT")
        name=parts[1].removeprefix("./")
        need(name in files and name not in witnessed,"MANIFEST_OBJECT")
        need(sha(raw[name])==parts[0],"FIRSTUSE_PERFILE_HASH_"+name)
        witnessed.add(name)
    need(witnessed==expected-{"firstuse-sha256.txt"},
         "EXACT_ORIGINAL_FIRSTUSE_FILES")
    need(sha(raw["aggregated-original-FIT.json"])==AGG_SHA256,
         "ORIGINAL_UNMODIFIED_AGGREGATE")
    aggregate=json.loads(raw["aggregated-original-FIT.json"])["summary"]
    need(aggregate["schema"]==
         "mass.f124bp.original-new-composition-development.v1"
         and aggregate["cases"]==24 and aggregate["arm_records"]==48
         and aggregate["preregistered_joint_FIT_admissible"] is False
         and aggregate["science_accepted"] is False,
         "FROZEN_AGGREGATE_NEGATIVE")
    for name in ("prior_BM_BN_BO_cases_used","original_192_TRAIN_replayed",
                 "BO_BP_protected_and_prior_BH_U_R_used",
                 "external_thirdparty_source_novelty_certified",
                 "full_scientific_resource_parity_certified",
                 "optimizer_policy_promoted"):
        need(aggregate[name] is False,
             "UNAUTHORIZED_SOURCE_OR_SCIENCE_"+name)
    frozen=json.loads((HERE/"f124bp-original-frozen-outcome.json").read_text())
    summary={}
    original_percase=[]
    for family,cohort in COHORT.items():
        per=[]
        for case in cohort:
            records={}
            for arm in ARMS:
                fn=f"firstuse_{case}_{arm}.json"
                r=json.loads(raw[fn])
                need(r["schema"]==
                     "mass.f124bp.original-sourceborn-development-pair.v1"
                     and r["case"]==case and r["family"]==family
                     and r["arm"]==arm,
                     "ORIGINAL_FIRSTUSE_CASE_ARM")
                need(r["private_source_evaluator_only"]==
                     {"positive":1,"negative":0},
                     "PRIVATE_SYMBOLIC_SOURCE_TRUTH")
                need(r["positive_accepted"] is
                     (r["positive_score"]>=0)
                     and r["hard_negative_false_positive"] is
                     (r["hard_negative_score"]>=0),
                     "ORIGINAL_REAL_SCORE_PREDICTION")
                need(r["measured_CPU_ns"]>0
                     and r["measured_whole_process_RSS_bytes"]>0,
                     "ACTUAL_PROCESS_COST")
                for flag in ("previous_FIT_cases_replayed","old_TRAIN_replayed",
                             "protected_128_and_BH_U_R_used",
                             "scientific_accepted","optimizer_promoted"):
                    need(r[flag] is False,"NO_UNAUTHORIZED_FIRSTUSE_"+flag)
                records[arm]=r
            a,b=records["AZ"],records["compact"]
            need(a["same_public_graph_SHA256"]==
                 b["same_public_graph_SHA256"],
                 "SAME_PUBLIC_SOURCE_AND_NATIVE_GRAPH")
            row={
              "case":case,"family":family,
              "AZ_positive":a["positive_accepted"],
              "AZ_FP":a["hard_negative_false_positive"],
              "compact_positive":b["positive_accepted"],
              "compact_FP":b["hard_negative_false_positive"],
              "compact_fitted":b["model_trace"].get("fitted",False),
              "AZ_CPU_ns":a["measured_CPU_ns"],
              "compact_CPU_ns":b["measured_CPU_ns"],
              "AZ_OS_RSS_bytes":a["measured_whole_process_RSS_bytes"],
              "compact_OS_RSS_bytes":b["measured_whole_process_RSS_bytes"],
              "public_graph_SHA256":a["same_public_graph_SHA256"],
              "AZ_original_receipt_SHA256":sha(raw[f"firstuse_{case}_AZ.json"]),
              "compact_original_receipt_SHA256":sha(raw[f"firstuse_{case}_compact.json"])
            }
            per.append(row)
            original_percase.append(row)
        correct={q["case"] for q in per
                 if q["compact_positive"] and not q["compact_FP"]}
        eligible={q["case"] for q in per if q["AZ_positive"] and not q["AZ_FP"]}
        rec={
          "pair_count":len(per),
          "baseline_positive_count":sum(q["AZ_positive"] for q in per),
          "baseline_hard_false_positive_count":sum(q["AZ_FP"] for q in per),
          "compact_positive_count":sum(q["compact_positive"] for q in per),
          "compact_hard_false_positive_ids":[q["case"] for q in per if q["compact_FP"]],
          "baseline_positive_lost_ids":[q["case"] for q in per
                                         if q["AZ_positive"] and not q["compact_positive"]],
          "compact_correct_pairs":len(correct),
          "new_correct_pairs":sorted(correct-eligible),
          "compact_identifiable_cases":sum(q["compact_fitted"] for q in per),
          "resource_parity_every_case":all(
              q["compact_CPU_ns"]<=q["AZ_CPU_ns"]
              and q["compact_OS_RSS_bytes"]<=q["AZ_OS_RSS_bytes"]
              for q in per),
          "RSS_regression_cases":[q["case"] for q in per
                                  if q["compact_OS_RSS_bytes"]>q["AZ_OS_RSS_bytes"]],
          "CPU_regression_cases":[q["case"] for q in per
                                  if q["compact_CPU_ns"]>q["AZ_CPU_ns"]],
          "AZ_CPU_median_ns":statistics.median(q["AZ_CPU_ns"] for q in per),
          "compact_CPU_median_ns":statistics.median(q["compact_CPU_ns"] for q in per),
          "AZ_RSS_median_bytes":statistics.median(q["AZ_OS_RSS_bytes"] for q in per),
          "compact_RSS_median_bytes":statistics.median(q["compact_OS_RSS_bytes"] for q in per)}
        static=frozen["families"][family]
        compare={
          "pair_count":"paired_cases",
          "baseline_positive_count":"original_AZ_accepted_positives",
          "baseline_hard_false_positive_count":"original_AZ_hard_FP",
          "compact_positive_count":"learned_accepted_positives",
          "compact_correct_pairs":"correctly_discriminated_pairs",
          "compact_identifiable_cases":"learned_identifiable_cases",
          "AZ_CPU_median_ns":"original_AZ_median_CPU_ns",
          "compact_CPU_median_ns":"learned_median_CPU_ns",
          "AZ_RSS_median_bytes":"original_AZ_median_OS_RSS_bytes",
          "compact_RSS_median_bytes":"learned_median_OS_RSS_bytes",
          "RSS_regression_cases":"per_case_RSS_regression_ids",
          "CPU_regression_cases":"per_case_CPU_regression_ids"}
        for field,field_static in compare.items():
            need(rec[field]==static[field_static],
                 "SIGNED_FROZEN_DATA_RECOUNT_"+family+"_"+field)
        recorded=aggregate["results"][family]
        for k in ("baseline_positive_count","compact_positive_count",
                  "compact_hard_false_positive_ids",
                  "baseline_positive_lost_ids","compact_correct_pairs",
                  "new_correct_pairs","resource_parity_every_case"):
            need(recorded[k]==rec[k],"FIRSTUSE_AGGREGATE_RECOUNT_"+family+"_"+k)
        need(recorded["frozen_FIT_admissible"] is False,
             "FROZEN_FIT_NEGATIVE")
        summary[family]=rec
    return {"schema":"mass.f124bp.readonly-provider-original-49-receipt-reconciliation.v1",
            "original_run":39186562655,
            "original_exact_head":"0a4a271a91fda97bc4c810553d047e6620e7b1eb",
            "original_artifact_id":12158670755,
            "original_artifact_ZIP_SHA256":"4a431c86dcbd325c2fbb3c4fcecf18196e3491b64a2ad74c1a4cee6478da6f1a",
            "original_aggregate_sha256":AGG_SHA256,
            "all_49_sha256_manifest_entries_verified":True,
            "all_48_original_arm_receipts_recounted":True,
            "source_cases_consumed_once":24,
            "reconciled_families":summary,
            "original_receipt_ids_and_process_costs":original_percase,
            "source_model_or_native_imported":False,
            "firstuse_replayed":False,
            "protected_cohort_consumed":False,
            "scientific_generalization_accepted":False,
            "optimizer_policy_promoted":False,
            "disposition":"VALID_ORIGINAL_IN_FAMILY_POSITIVE_CROSS_FAMILY_AND_STRICT_RSS_NEGATIVE"}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    result=reconcile(a.original)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(result,sort_keys=True,indent=2)+"\n").encode()
    with a.output.open("xb") as f:f.write(raw)
    print("F124BP_PROVIDER_ORIGINAL_49_RECEIPTS=PASS")
    print("F124BP_SOURCE_A_CORRECT_PAIRS=12/12")
    print("F124BP_SOURCE_B_CORRECT_PAIRS=0/12")
    print("F124BP_STRICT_COST_PARITY=false")
    print("F124BP_NEW_PROTECTED_FIRSTUSE=false")
    print("F124BP_SCIENCE_ACCEPTED=false")
    print("F124BP_ORIGINAL_RECOUNT_SHA256="+sha(raw))


if __name__=="__main__":
    main()
