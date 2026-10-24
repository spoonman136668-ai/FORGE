"""L4 independent no-network native receipt reconciler; fail closed.

Production training text is never loaded in the comparison job. The three
external-source role identities, five trained checkpoint identities, output
hashes and all measured QUALITY counts must match exactly. CPU/wall/RSS may
differ across OS and are never asserted identical.
"""
import json
from pathlib import Path
import sys
import math

ARMS=("P_SLOT_INDEPENDENT","SEQ_CONDITIONAL","JOINT_SPAN_COUNT",
      "P_WITH_SELECT_REPAIR","FIT_PRIOR")
ROLES=("L4_REAL_TRAIN","L4_REAL_SELECT","L4_REAL_DEV")
COUNTS={"L4_REAL_TRAIN":1200,"L4_REAL_SELECT":300,"L4_REAL_DEV":300}
SCHEMA="forge.optimizer.language.l4.realtext-public-gap-receipt.v1"
GIT_BLOB="7dcb3a2d4cc3b48b6283dd46870bfeb78f88aac9"
NUMERIC_FIELDS=("two_word_exact_match","first_word_accuracy",
                "second_word_accuracy","gap_has_train_out_of_vocabulary")
EXACT_FIELDS=("evaluated_rows","predicted_gaps_sha256",
              "repair_changes","categorical_lookup_proxy_not_FLOPs")


def reconcile(linux,windows):
    for x in (linux,windows):
        if (x.get("schema")!=SCHEMA or
            x.get("source_git_blob_sha1")!=GIT_BLOB or
            x.get("previous_L1_L3_dev_reuse")!=0 or
            x.get("protected_Q21_FSA_scientific_first_use") is not False or
            x.get("Q21_and_active_research_unchanged") is not True or
            x.get("externally_blinded_science") is not False or
            x.get("model_scientific_go") is not False or
            x.get("fully_resource_matched_conventional_LM") is not False or
            x.get("actual_parallel_execution") is not False):
            raise ValueError("L4_EXTERNAL_OR_SCIENTIFIC_CUSTODY_VIOLATION")
        if (set(x.get("source_role_sha256",{}))!=set(ROLES) or
            x.get("source_role_counts")!=COUNTS or
            set(x.get("models",{}))!=set(ARMS) or
            set(x.get("evaluations",{}))!=set(ROLES)):
            raise ValueError("L4_FROZEN_ROLE_AND_ARM_COVERAGE")
    if linux["source_raw_sha256"]!=windows["source_raw_sha256"]:
        raise ValueError("L4_EXTERNAL_RAW_SHA256_DIFFERENT")
    if linux["source_role_sha256"]!=windows["source_role_sha256"]:
        raise ValueError("L4_ROLE_SHA256_MISMATCH")
    for role in ROLES:
        if len(linux["source_role_sha256"][role])!=64:
            raise ValueError("L4_INVALID_DIGEST_LENGTH")
    errors=[]
    comparisons=0
    for arm in ARMS:
        l,w=linux["models"][arm],windows["models"][arm]
        for field in (
            "checkpoint_sha256","checkpoint_bytes_including_underlying_models",
            "conceptual_dependency_stages","actual_parallel_execution",
            "repair_threshold_SELECTED_only",
        ):
            if l.get(field)!=w.get(field):
                errors.append({"arm":arm,"field":field,
                               "linux":l.get(field),"windows":w.get(field)})
    for role in ROLES:
        l,w=linux["evaluations"][role],windows["evaluations"][role]
        if set(l)!=set(ARMS) or set(w)!=set(ARMS):
            raise ValueError("L4_ALL_ROLE_ARM_RECEIPT_COVERAGE")
        for arm in ARMS:
            x,y=l[arm],w[arm]
            for field in EXACT_FIELDS:
                if x.get(field)!=y.get(field):
                    errors.append({"role":role,"arm":arm,"field":field})
            if x["evaluated_rows"]!=COUNTS[role]:
                raise ValueError("L4_ROLE_RECORD_COUNT")
            for field in NUMERIC_FIELDS:
                av,bv=x.get(field),y.get(field)
                if not (isinstance(av,(float,int)) and isinstance(bv,(float,int))
                        and math.isfinite(av) and math.isfinite(bv)):
                    raise ValueError("L4_NONFINITE_QUALITY")
                comparisons+=1
                if av!=bv:
                    errors.append({"role":role,"arm":arm,"metric":field,
                                   "linux":av,"windows":bv})
    if errors:
        for problem in errors[:8]:
            print("L4_CROSS_OS_DRIFT "+json.dumps(problem,sort_keys=True))
        raise ValueError("L4_FROZEN_PUBLIC_NUMERIC_REPRODUCIBILITY_FAIL")
    return {
        "schema":"forge.optimizer.language.l4.cross-native-public.v1",
        "exact_source_raw_sha256":linux["source_raw_sha256"],
        "three_source_role_digests":"3_OF_3_EXACT",
        "fifteen_model_role_outputs":"15_OF_15_IDENTICAL",
        "exact_quality_numeric_comparisons":comparisons,
        "not_independent_blinded_science":True,
        "not_language_Pareto_qualified":True,
        "result":"L4_PUBLIC_EXTERNAL_REALTEXT_ENGINEERING_QUALIFIED_ONLY",
    }


def main():
    if len(sys.argv)!=4:
        raise SystemExit("usage: compare.py linux.json windows.json report.json")
    with open(sys.argv[1],encoding="utf-8") as f: l=json.load(f)
    with open(sys.argv[2],encoding="utf-8") as f: w=json.load(f)
    result=reconcile(l,w)
    dest=Path(sys.argv[3])
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",
                    encoding="utf-8")
    print("L4_EXTERNAL_CORPUS_GIT_SHA_AND_ROLES=PASS")
    print("L4_ALL_FITTED_DEV_PREDICTIONS=15_OF_15_EXACT")
    print("L4_SIGNED_QUALITY_METRICS=PASS")
    print("L4_SCIENTIFIC_GO=NOT_ELIGIBLE")


if __name__=="__main__":
    main()
