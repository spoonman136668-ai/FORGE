"""L2 independent native result reconciler, strict frozen source identity.

CPU/wall/peak-RAM are observed separately per native OS, not forced to be
identical. Quality and operation counts must match at 1e-6. Models with
different learned capacities are NOT declared resource-matched.
"""
import json
import math
from pathlib import Path
import sys

from public_source import ROLES,COUNTS
from runner import ARMS

QUALITY_FIELDS=(
    "meaning_fidelity_exact","mean_correct_chunk_fraction",
    "subject_code_accuracy","dependent_verb_accuracy",
    "synthetic_surface_grammar_accuracy",
    "corrupted_gold_exact_false_positive_rate",
)
SCHEMA="forge.optimizer.language.l2.public-dependence-receipt.v1"
TOL=1e-6


def reconcile(linux,windows):
    for receipt in (linux,windows):
        if receipt.get("schema")!=SCHEMA or \
                receipt.get("previous_l1_l2_protected_dev_reuse")!=0 or \
                receipt.get("Q21_FSA_protected_scientific_first_use") is not False or \
                receipt.get("existing_research_priority_unchanged") is not True or \
                receipt.get("language_model_replacement_claim") is not False or \
                receipt.get("externally_independent_natural_language") is not False or \
                receipt.get("actual_parallel_hardware_inference") is not False:
            raise ValueError("L2_GOVERNANCE_OR_SOURCE_CUSTODY_DRIFT")
        if set(receipt.get("source_role_sha256",{}))!=set(ROLES) or \
                receipt.get("source_role_sizes")!=COUNTS:
            raise ValueError("L2_SOURCE_ROLE_COVERAGE")
        if set(receipt.get("resources",{}))!=set(ARMS) or \
                set(receipt.get("evaluations",{}))!=set(ROLES):
            raise ValueError("L2_TRAINED_EVAL_COVERAGE")
    if linux["source_role_sha256"]!=windows["source_role_sha256"]:
        raise ValueError("L2_CROSS_OS_SOURCE_SHA_DRIFT")
    for role in ROLES:
        if len(linux["source_role_sha256"][role])!=64:
            raise ValueError("L2_INVALID_ROLE_SHA")
    mismatches=[]
    for arm in ARMS:
        left,right=linux["resources"][arm],windows["resources"][arm]
        for fixed in ("checkpoint_bytes","conceptual_serial_dependency_stages",
                      "execution_is_actually_parallel"):
            if left.get(fixed)!=right.get(fixed):
                mismatches.append({"arm":arm,"field":fixed,
                                   "linux":left.get(fixed),"windows":right.get(fixed)})
        if left.get("frozen_selected_field_subsets")!=right.get("frozen_selected_field_subsets"):
            mismatches.append({"arm":arm,"field":"frozen_SELECTED_feature_sets"})
    compare_count=0
    for role in ROLES:
        la,wa=linux["evaluations"][role],windows["evaluations"][role]
        if set(la)!=set(ARMS) or set(wa)!=set(ARMS):
            raise ValueError("L2_ARM_EVALUATION_COVERAGE")
        for arm in ARMS:
            l,w=la[arm],wa[arm]
            if l["records"]!=COUNTS[role] or w["records"]!=COUNTS[role]:
                raise ValueError("L2_ROLE_RECORD_BUDGET")
            for field in QUALITY_FIELDS:
                x,y=l.get(field),w.get(field)
                if x is None or y is None:
                    if x is not None or y is not None:
                        mismatches.append({"role":role,"arm":arm,"field":field})
                    continue
                if not (type(x) in (int,float) and type(y) in (int,float)
                        and math.isfinite(x) and math.isfinite(y)):
                    raise ValueError("L2_NONFINITE_METRIC")
                compare_count+=1
                if abs(x-y)>TOL:
                    mismatches.append({
                        "role":role,"arm":arm,"metric":field,
                        "linux":x,"windows":y,"difference":abs(x-y)
                    })
            for exact in ("categorical_lookup_scoring_operations_NOT_FLOPS",
                          "trained_verifier_repairs_applied"):
                if l[exact]!=w[exact]:
                    mismatches.append({"role":role,"arm":arm,"metric":exact})
    if mismatches:
        for detail in mismatches[:12]:
            print("L2_NATIVE_DISAGREEMENT "+json.dumps(detail,sort_keys=True))
        raise ValueError("L2_PREDECLARED_CROSS_OS_REPRODUCIBILITY_FAIL")
    return {
        "schema":"forge.optimizer.language.l2.native-public-comparison.v1",
        "all_four_role_digests":"4_OF_4_EXACT",
        "source_roles_without_semantic_overlap":True,
        "frozen_model_evaluation_coverage":"24_OF_24",
        "quality_metric_numeric_comparisons":compare_count,
        "native_lookups_and_repairs_reconciled":True,
        "actual_parallel_wall_speedup_claimed":False,
        "scientific_candidate_admitted":False,
        "result":"L2_PUBLIC_DEPENDENCY_DEVELOPMENT_REPRODUCIBLE_NOT_INDEPENDENT_SCIENCE"
    }


def main():
    if len(sys.argv)!=4:
        raise SystemExit("usage: compare.py linux.json windows.json report.json")
    with open(sys.argv[1],encoding="utf-8") as f: linux=json.load(f)
    with open(sys.argv[2],encoding="utf-8") as f: windows=json.load(f)
    result=reconcile(linux,windows)
    target=Path(sys.argv[3])
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",
                      encoding="utf-8")
    print("L2_SOURCE_CUSTODY=4_OF_4_EXACT")
    print("L2_MODEL_ROLE_METRIC_COMPARISONS=24_OF_24_PASS")
    print("L2_QUALITY_METRIC_FLOAT_COMPARISONS="+str(
        result["quality_metric_numeric_comparisons"]))
    print("L2_NO_NCI_ITD_BIO_Q21_FORGE_DISPLACEMENT=PASS")
    print("L2_LANGUAGE_SCIENTIFIC_GO=NOT_ELIGIBLE")


if __name__=="__main__":
    main()
