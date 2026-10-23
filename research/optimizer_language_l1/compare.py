"""L1 independent Windows/Linux frozen public role and realization acceptance."""
import json
import math
from pathlib import Path
import sys

ROLES=("L1_TRAIN","L1_SELECT","L1_INDOMAIN_DEV",
       "L1_NOVEL_COMPOSITION_DEV")
EVAL_ROLES=ROLES[2:]
ARMS=("PARALLEL_FACTOR","AUTOREGRESSIVE_CHUNK",
      "PARALLEL_SELECTIVE_REPAIR","PARALLEL_UNCONDITIONAL",
      "FULL_MEANING_LOOKUP","SOURCE_KNOWN_TEMPLATE_DIAGNOSTIC")
METRICS=("exact_utterance_accuracy","mean_slot_accuracy",
         "core_actor_verb_object_accuracy",
         "clause_semantic_slot_fidelity",
         "normalized_character_edit_distance",
         "punctuation_accuracy")
TOLERANCE=1e-6


def reconcile(linux,windows):
    for value in (linux,windows):
        if (value.get("schema")!=
            "forge.optimizer.language.l1.public-parallel-realization-receipt.v1" or
            value.get("scientific_first_use") is not False or
            value.get("externally_independent_language_source") is not False or
            value.get("protected_Q21_FSA_cohorts_consumed")!=0 or
            value.get("native_Wingless_Yggdrasil_candidate") is not None):
            raise ValueError("L1_SOURCE_SCIENCE_CUSTODY_VIOLATION")
        if set(value.get("source_role_sha256",{}))!=set(ROLES) or \
                set(value.get("fitted_model_evidence",{}))!=set(ARMS) or \
                set(value.get("evaluations",{}))!=set(EVAL_ROLES):
            raise ValueError("L1_ROLE_MODEL_OR_DEV_INVENTORY")
        for role in EVAL_ROLES:
            if set(value["evaluations"][role])!=set(ARMS):
                raise ValueError("L1_MISSING_EVAL_ARM")
    if linux["source_role_sha256"]!=windows["source_role_sha256"]:
        raise ValueError("L1_FOUR_SOURCE_SHA256_DRIFT")
    for arm in ARMS:
        a=linux["fitted_model_evidence"][arm]
        b=windows["fitted_model_evidence"][arm]
        for key in ("checkpoint_sha256","checkpoint_bytes",
                    "training_utterances_consumed",
                    "sequential_dependency_stages"):
            if a[key]!=b[key]:
                raise ValueError("L1_TRAINED_MODEL_CHECKPOINT_OR_SCOPE_DRIFT "+
                                 arm+" "+key)
    errors=[]
    for role in EVAL_ROLES:
        for arm in ARMS:
            a=linux["evaluations"][role][arm]
            b=windows["evaluations"][role][arm]
            for key in METRICS:
                av,bv=a.get(key),b.get(key)
                if not (type(av) in (float,int) and
                        type(bv) in (float,int) and
                        math.isfinite(av) and math.isfinite(bv)):
                    raise ValueError("L1_NONFINITE_QUALITY")
                if abs(av-bv)>TOLERANCE:
                    errors.append({"role":role,"arm":arm,"metric":key,
                                   "linux":av,"windows":bv})
            if a["n_examples"]!=b["n_examples"] or \
                    a["categorical_lookup_and_candidate_scoring_operation_proxy"]!=\
                    b["categorical_lookup_and_candidate_scoring_operation_proxy"] or \
                    a["total_verified_repairs"]!=b["total_verified_repairs"]:
                errors.append({"role":role,"arm":arm,"issue":"operation count drift"})
    if errors:
        for x in errors[:15]:
            print("L1_CROSS_OS_QUALITY_DRIFT "+json.dumps(x,sort_keys=True))
        raise ValueError("L1_FROZEN_NUMERIC_ACCEPTANCE_FAILURE")
    return {
        "schema":"forge.optimizer.language.l1.independent-native-reconciliation.v1",
        "role_hashes":"4_OF_4_EXACT",
        "model_checkpoint_hashes":"6_OF_6_EXACT",
        "quality_metrics":"72_OF_72_WITHIN_1E-6",
        "operation_counts":"12_OF_12_EXACT",
        "scientific_go":False,
        "external_natural_language_evaluation":False,
        "status":"L1_ALIGNED_SYNTHETIC_ENGINEERING_ACCEPTANCE_ONLY",
    }


def main():
    if len(sys.argv)!=4:
        raise SystemExit("usage: compare.py linux.json windows.json receipt.json")
    with open(sys.argv[1],encoding="utf-8") as f:
        linux=json.load(f)
    with open(sys.argv[2],encoding="utf-8") as f:
        windows=json.load(f)
    report=reconcile(linux,windows)
    path=Path(sys.argv[3])
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",
                    encoding="utf-8")
    print("L1_FOUR_SOURCE_DIGESTS=PASS")
    print("L1_SIX_MODEL_CHECKPOINTS=PASS")
    print("L1_QUALITY_METRICS=72_OF_72_PASS")
    print("L1_NO_PROTECTED_Q21_FIRST_USE=PASS")
    print("L1_REPRODUCIBLE_PUBLIC_SYNTHETIC_ONLY=PASS")


if __name__=="__main__":
    main()
