"""Independent L3 native receipt qualification, fail closed on numerical drift."""
import json
import math
from pathlib import Path
import sys

from public_source import ROLES,COUNTS
from runner import ARMS

SCHEMA="forge.optimizer.language.l3.native-neural-comparison.v1"
QUALITY=("exact_semantic_utterance","mean_chunk_accuracy",
         "actor_accuracy","verb_inflection_accuracy",
         "corrupted_target_false_exact_rate")
TOL=.005


def reconcile(linux,windows):
    for receipt in (linux,windows):
        if receipt.get("schema")!=SCHEMA or \
                receipt.get("scope")!="SYNTHETIC_PUBLIC_DEV_ONLY" or \
                receipt.get("science_promotion") is not False or \
                receipt.get("prior_L1_L2_dev_roles_consumed")!=0 or \
                receipt.get("Q21_FSA_protected_first_use") is not False or \
                receipt.get("unchanged_active_native_research") is not True or \
                receipt.get("actual_parallel_execution") is not False or \
                receipt.get("external_unaligned_natural_language_source") is not False or \
                receipt.get("numpy_version")!="2.1.3":
            raise ValueError("L3_PUBLIC_PROTECTED_SOURCE_GOVERNANCE_DRIFT")
        if set(receipt.get("source_sha256",{}))!=set(ROLES) or \
                receipt.get("source_role_counts")!=COUNTS:
            raise ValueError("L3_NEW_ROLE_COVERAGE")
        if set(receipt.get("models",{}))!=set(ARMS) or \
                set(receipt.get("evaluations",{}))!=set(ROLES):
            raise ValueError("L3_REGISTERED_COMPARATORS_COVERAGE")
    if linux["source_sha256"]!=windows["source_sha256"]:
        raise ValueError("L3_WIN_LINUX_SOURCE_SHA_MISMATCH")
    if any(len(sha)!=64 for sha in linux["source_sha256"].values()):
        raise ValueError("L3_ROLE_HASH_NOT_SHA256")
    unequal=[]
    for arm in ARMS:
        x,y=linux["models"][arm],windows["models"][arm]
        for field in ("selected_seed","trainable_parameter_count",
                      "serial_dependency_stages",
                      "actual_parallel_execution",
                      "optimizer_update_count_each_start",
                      "selection_field_subsets","checkpoint_bytes_including_optimizer"):
            if x.get(field)!=y.get(field):
                unequal.append({"arm":arm,"field":field,
                                "linux":x.get(field),"windows":y.get(field)})
    comparisons=0
    for role in ROLES:
        lx,wx=linux["evaluations"][role],windows["evaluations"][role]
        if set(lx)!=set(ARMS) or set(wx)!=set(ARMS):
            raise ValueError("L3_FROZEN_MODEL_ROLE_COVERAGE")
        for arm in ARMS:
            a,b=lx[arm],wx[arm]
            if a.get("records")!=COUNTS[role] or b.get("records")!=COUNTS[role]:
                raise ValueError("L3_ROLE_EXPERIENCE_COUNT_DRIFT")
            for metric in QUALITY:
                left,right=a.get(metric),b.get(metric)
                if left is None or right is None:
                    if left is not None or right is not None:
                        unequal.append({"role":role,"arm":arm,"metric":metric})
                    continue
                comparisons+=1
                if not (type(left) in (float,int) and
                        type(right) in (float,int) and
                        math.isfinite(left) and math.isfinite(right)):
                    raise ValueError("L3_NONFINITE_NATIVE_METRIC")
                if abs(left-right)>TOL:
                    unequal.append({"role":role,"arm":arm,"metric":metric,
                                    "linux":left,"windows":right})
    if unequal:
        for e in unequal[:12]:
            print("L3_NATIVE_RECEIPT_DRIFT "+json.dumps(e,sort_keys=True))
        raise ValueError("L3_FROZEN_COMPARABILITY_ACCEPTANCE_FAIL")
    return {
        "schema":"forge.optimizer.language.l3.cross-native-result.v1",
        "new_source_sha256":"5_OF_5_EXACT",
        "registered_model_role_receipts":"25_OF_25_PRESENT",
        "numeric_quality_comparisons":comparisons,
        "scientific_first_use":False,
        "true_NAR_parallel_hardware_speedup_demonstrated":False,
        "parameter_and_compute_budgets_matched":False,
        "qualified_engineering":"NATIVE_PUBLIC_LEARNED_COMPARATORS_REPRODUCIBLE_ONLY"
    }


def main():
    if len(sys.argv)!=4:
        raise SystemExit("usage: compare.py linux.json windows.json output.json")
    with open(sys.argv[1],encoding="utf-8") as f:
        linux=json.load(f)
    with open(sys.argv[2],encoding="utf-8") as f:
        windows=json.load(f)
    result=reconcile(linux,windows)
    dest=Path(sys.argv[3])
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("L3_CROSS_OS_SOURCE=5_OF_5_EXACT")
    print("L3_PUBLIC_DEV_MODEL_ROLE_COMPARISONS=25_OF_25_PASS")
    print("L3_NUMERIC_QUALITY_COMPARISONS="+str(result["numeric_quality_comparisons"]))
    print("L3_SCIENTIFIC_GO=NOT_ELIGIBLE")


if __name__=="__main__":
    main()
