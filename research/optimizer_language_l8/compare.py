"""Independent no-NLP/no-network L8 Windows/Linux attribution reconciliation.

Both original E2E Git objects, legacy 180 exposed MR identity, three public
cohorts, every 5x3 generated output SHA and EVERY source/attribution/quality
scalar must match, despite cross-host CPU, wall and memory variation.
"""
import json
import math
from pathlib import Path
import sys

SCHEMA="forge.optimizer.language.l8.public-fallback-attribution-native.v1"
ROLES=("L8_TRAIN","L8_AUDIT_SELECT","L8_AUDIT_DEV")
COUNTS={"L8_TRAIN":700,"L8_AUDIT_SELECT":80,"L8_AUDIT_DEV":160}
ARMS=("REFERENCE_RETRIEVAL","DELEX_TEMPLATE","CONSTRAINED_TEMPLATE",
      "NO_FALLBACK_CONSTRAINED","CANONICAL_FACTS")
ROUTE_NUMERATORS=(
    "records","learned_only_output_count","canonical_fallback_count",
    "abstention_count","observed_five_literal_slots",
    "five_literal_exact_copy_hits","learned_route_literal_hits",
    "learned_route_literal_slots","fallback_route_literal_hits",
    "fallback_route_literal_slots","all_MR_keys_raw_literal_slots",
    "all_MR_keys_raw_literal_hits")
FRACTIONS=(
    "learned_route_fraction","canonical_fallback_fraction",
    "abstention_fraction","five_literal_copy_rate_with_abstention_zero",
    "learned_route_literal_copy_rate_conditional",
    "fallback_route_literal_copy_rate_conditional",
    "all_MR_keys_raw_literal_copy_proxy","all_keys_raw_literal_complete_rate",
    "name_literal_recall","near_literal_recall",
    "possible_conflicting_TRAIN_value_rate_NOT_NLI",
    "unresolved_brace_marker_rate",
    "reference_token_F1_one_human_ref_NOT_fluency",
    "learned_route_reference_F1_conditional",
    "sentence_terminal_punctuation_proxy",
    "semicolon_factlist_indicator")


def reconcile(linux,windows):
    for receipt in (linux,windows):
        if (
            receipt.get("schema")!=SCHEMA or
            receipt.get("research_scope")!="ADDITIVE_PUBLIC_DEVELOPMENT_ONLY" or
            receipt.get("prior_L7_180_public_dev_used_for_fit_or_eval")!=0 or
            receipt.get("E2E_official_TEST_consumed") is not False or
            receipt.get("Q21_FSA_HELD_first_use") is not False or
            receipt.get("NCI_ITD_BIO_Optimizer_FORGE_unchanged") is not True or
            receipt.get("externally_blinded_semantics_or_human_fluency") is not False or
            receipt.get("fully_trained_neural_comparator_and_matched_compute") is not False or
            receipt.get("scientific_pareto_go") is not False or
            receipt.get("hardware_parallel_generation") is not False
        ):
            raise ValueError("L8_GOVERNANCE_OR_PRIOR_EXPOSED_DEV_DRIFT")
        if (set(receipt.get("original_files_sha256",{}))!=
            {"trainset.csv","devset.csv"} or
            receipt.get("counts")!=COUNTS or
            set(receipt.get("source_role_sha256",{}))!=set(ROLES) or
            set(receipt.get("models",{}))!=set(ARMS) or
            set(receipt.get("evaluations",{}))!=set(ROLES)):
            raise ValueError("L8_NEW_SOURCE_ROLE_MODEL_RECEIPT_COVERAGE")
    for field in (
        "original_files_sha256","source_role_sha256",
        "old_l7_dev_mr_identity_sha256"):
        if linux[field]!=windows[field]:
            raise ValueError("L8_CROSS_NATIVE_SOURCE_OR_SPENT_DEV_IDENTITY_DRIFT_"+field)
    if any(len(sha)!=64 for sha in linux["source_role_sha256"].values()):
        raise ValueError("L8_SOURCE_ROLE_SHA256_MALFORMED")
    errors=[]
    numeric=0
    for arm in ARMS:
        a,b=linux["models"][arm],windows["models"][arm]
        for field in ("checkpoint_sha256","checkpoint_bytes",
                      "original_l7_trained_examples",
                      "trained_pattern_count","shares_model_and_training_with",
                      "incremental_trained_checkpoint_bytes"):
            if a.get(field)!=b.get(field):
                errors.append({"arm":arm,"field":field})
    for role in ROLES:
        la,wa=linux["evaluations"][role],windows["evaluations"][role]
        if set(la)!=set(ARMS) or set(wa)!=set(ARMS):
            raise ValueError("L8_FIVE_ARM_PUBLIC_ROLE_COVERAGE_MISSING")
        for arm in ARMS:
            a,b=la[arm],wa[arm]
            if a["records"]!=COUNTS[role]:
                raise ValueError("L8_PROSPECTIVE_ROLE_RECORD_BUDGET_DRIFT")
            for field in ("generated_outputs_sha256","route_counts",
                          "string_comparison_operation_proxy_NOT_FLOPs"):
                if a.get(field)!=b.get(field):
                    errors.append({"role":role,"arm":arm,"field":field})
            if len(a["generated_outputs_sha256"])!=64:
                raise ValueError("L8_GENERATION_DIGEST_MALFORMED")
            for field in ROUTE_NUMERATORS:
                if a.get(field)!=b.get(field):
                    errors.append({"role":role,"arm":arm,"field":field,
                                   "linux":a.get(field),"windows":b.get(field)})
            for field in FRACTIONS:
                x,y=a.get(field),b.get(field)
                if x is None or y is None:
                    if x is not None or y is not None:
                        errors.append({"role":role,"arm":arm,"field":field})
                    continue
                if not (type(x) in (float,int) and type(y) in (float,int)
                        and math.isfinite(x) and math.isfinite(y)):
                    raise ValueError("L8_NONFINITE_FAITHFULNESS_OR_ATTRIBUTION")
                numeric+=1
                if abs(x-y)>1e-12:
                    errors.append({"role":role,"arm":arm,"field":field,
                                   "linux":x,"windows":y})
    if errors:
        for wrong in errors[:12]:
            print("L8_SOURCE_OR_MODEL_CROSS_OS_MISMATCH "+
                  json.dumps(wrong,sort_keys=True))
        raise ValueError("L8_PRESPECIFIED_NATIVE_CUSTODY_AND_FIDELITY_FAIL")
    return {
        "schema":"forge.optimizer.language.l8.independent-native-attribution.v1",
        "original_E2E_data_source_identity":"2_OF_2_EXACT",
        "fresh_public_cohort_SHA256":"3_OF_3_EXACT",
        "trained_baseline_5_arms_times_3_roles":"15_OF_15_EXACT",
        "attribution_and_literal_quality_numeric_scalars":numeric,
        "old_L7_dev_reuse":0,
        "official_E2E_test_first_use":False,
        "semantic_entailment_assessed":False,
        "inference_pareto_admitted":False,
        "result":"L8_PUBLIC_FALLBACK_SOURCE_ATTRIBUTION_REPRODUCIBLE_ONLY",
    }


def main():
    if len(sys.argv)!=4:
        raise SystemExit("usage: compare.py linux.json windows.json report.json")
    with open(sys.argv[1],encoding="utf-8") as f: left=json.load(f)
    with open(sys.argv[2],encoding="utf-8") as f: right=json.load(f)
    result=reconcile(left,right)
    path=Path(sys.argv[3])
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",
                    encoding="utf-8")
    print("L8_FRESH_PUBLIC_DEV_COHORES_AND_SPENT_L7_EXCLUSION=PASS")
    print("L8_REALIZER_GENERATION_AND_FALLBACK_IDENTITY=15_OF_15_PASS")
    print("L8_LITERAL_ATRIBUTION_REPRODUCED="+str(result["attribution_and_literal_quality_numeric_scalars"]))
    print("L8_NO_NATIVE_SCIENTIFIC_GO=PASS")


if __name__=="__main__":
    main()
