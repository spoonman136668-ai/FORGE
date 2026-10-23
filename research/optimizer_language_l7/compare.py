"""L7 pure-stdlib independent Windows/Linux human-structured-public result audit.

Source identity and output strings must agree exactly. Native CPU/wall/RSS
vary by OS and remain separate resource evidence. This is NOT blinded
semantic entailment or qualified conventional language-model comparison.
"""
import json
import math
from pathlib import Path
import sys

ROLES=("L7_TRAIN","L7_SELECT","L7_DEV")
COUNTS={"L7_TRAIN":700,"L7_SELECT":80,"L7_DEV":100}
ARMS=("REFERENCE_RETRIEVAL","DELEX_TEMPLATE",
      "CONSTRAINED_TEMPLATE","CANONICAL_FACTS")
SCHEMA="forge.optimizer.language.l7.public-real-mr-text-receipt.v1"
FIELDS=("literal_slot_copy_rate","name_literal_recall","near_literal_recall",
        "known_unrequested_name_near_indicator_rate",
        "unresolved_placeholder_fraction",
        "single_reference_token_F1_not_BLEU","generated_mean_token_count",
        "exact_reference_string_fraction")


def reconcile(linux,windows):
    for x in (linux,windows):
        if (x.get("schema")!=SCHEMA or
            x.get("governance")!="ADDITIVE_PUBLIC_DEV_ONLY" or
            x.get("Q21_FSA_HELD_protected_first_use") is not False or
            x.get("prior_L1_L6_dev_roles_used")!=0 or
            x.get("official_E2E_test_touched") is not False or
            x.get("independent_blinded_NLI_or_human_language_assessment") is not False or
            x.get("scientific_Pareto_GO") is not False or
            x.get("fully_trained_resource_matched_neural_controls") is not False or
            x.get("true_hardware_parallel_generation") is not False):
            raise ValueError("L7_ORIGINAL_RESEARCH_GOVERNANCE_OR_TEST_CUSTODY_FAIL")
        if (x.get("role_counts")!=COUNTS or
            set(x.get("source_role_sha256",{}))!=set(ROLES) or
            set(x.get("fitted_models",{}))!=set(ARMS) or
            set(x.get("public_role_evaluations",{}))!=set(ROLES)):
            raise ValueError("L7_ORIGINAL_SOURCE_AND_ARM_RECEIPT_COVERAGE")
    if (linux["original_git_sha256"]!=windows["original_git_sha256"] or
        linux["source_role_sha256"]!=windows["source_role_sha256"]):
        raise ValueError("L7_EXTERNAL_SOURCE_OR_ROLE_SHA_DRIFT")
    differences=[]
    nfields=0
    for arm in ARMS:
        left,right=linux["fitted_models"][arm],windows["fitted_models"][arm]
        for field in ("frozen_checkpoint_sha256","whole_trained_checkpoint_bytes",
                      "fit_examples","learned_delex_patterns"):
            if left.get(field)!=right.get(field):
                differences.append({"arm":arm,"field":field})
    for role in ROLES:
        a,b=linux["public_role_evaluations"][role],windows["public_role_evaluations"][role]
        if set(a)!=set(ARMS) or set(b)!=set(ARMS):
            raise ValueError("L7_MISSING_FROZEN_EVAL_ARM")
        for arm in ARMS:
            x,y=a[arm],b[arm]
            for field in ("records","observed_literal_slots","exact_literal_slot_hits",
                          "generated_output_sha256"):
                if x.get(field)!=y.get(field):
                    differences.append({"role":role,"arm":arm,"field":field})
            if x.get("records")!=COUNTS[role]:
                raise ValueError("L7_SOURCE_EVAL_ROLE_CARDINALITY")
            for field in FIELDS:
                l,r=x.get(field),y.get(field)
                if l is None or r is None:
                    if l is not None or r is not None:
                        differences.append({"role":role,"arm":arm,"field":field})
                    continue
                if not (type(l) in (float,int) and type(r) in (float,int)
                        and math.isfinite(l) and math.isfinite(r)):
                    raise ValueError("L7_UNBOUNDED_NONFINITE_SCORE")
                nfields+=1
                if abs(l-r)>1e-12:
                    differences.append({"role":role,"arm":arm,"field":field,
                                        "linux":l,"windows":r})
    if differences:
        for d in differences[:12]:
            print("L7_CROSS_OS_SOURCE_OR_FIDELITY_DRIFT "+json.dumps(d,sort_keys=True))
        raise ValueError("L7_FROZEN_FULL_WINDOWS_LINUX_RECONCILIATION_FAIL")
    return {
        "schema":"forge.optimizer.language.l7.public-cross-native-receipt.v1",
        "external_train_and_dev_identity":"2_OF_2_EXACT",
        "independent_source_roles":"3_OF_3_EXACT",
        "learned_model_role_receipts":"12_OF_12_EXACT",
        "quality_comparable_scalars":nfields,
        "source_dataset_is_PUBLIC":True,
        "human_fluency_and_NLI_are_unassessed":True,
        "scientific_Pareto_admission":False,
        "result":"L7_PUBLIC_REAL_STRUCTURED_MEANING_LANGUAGE_ENGINEERING_REPRODUCIBLE",
    }


def main():
    if len(sys.argv)!=4:
        raise SystemExit("usage: compare.py linux.json windows.json report.json")
    with open(sys.argv[1],encoding="utf-8") as f: linux=json.load(f)
    with open(sys.argv[2],encoding="utf-8") as f: windows=json.load(f)
    report=reconcile(linux,windows)
    dest=Path(sys.argv[3])
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",
                    encoding="utf-8")
    print("L7_E2E_ORIGINAL_EXTERNAL_SOURCE=2_OF_2_EXACT")
    print("L7_TRAIN_SELECT_DEV_MR_IDENTITY=3_OF_3_EXACT")
    print("L7_FOUR_REALIZERS_EVALUATED_ON_THREE_ROLES=12_OF_12_EXACT")
    print("L7_CONTENT_FIDELITY_LITERAL_NOT_NLI=PASS")
    print("L7_GENERAL_LANGUAGE_SCIENTIFIC_GO=NOT_ELIGIBLE")


if __name__=="__main__":
    main()
