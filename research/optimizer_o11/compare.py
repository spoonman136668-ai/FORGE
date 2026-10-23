"""O11 independently reconcile native training traces; diagnose, don't mask drift.

No evaluation data is opened. Reconciliation fails on broken identity, missing
trace coverage, unequal source roles, malformed parameters or invalid science
custody. Actual floating-point differences are RECORDED at the earliest
step (the purpose of this forensic diagnostic), not tuned away or called GO.
"""
import json
import math
import pathlib
import sys

FAMILIES=("A_CUE0_COMPOSE","B_CUE4_COMPOSE","C_SELECTOR_COMPOSE","NULL_IID")
KINDS=("TRAINED_PHASE_MEMORY","FROZEN_PHASE_TRAINED_HEAD","LINEAR_COUNT_MEMORY")
SEEDS=(17,31)
TRACE=(0,1,2,3,8,16,32,96,192,384,768,1536,3072,3840)
KEYS=("weight_hex","moment1_hex","moment2_hex","train_probe_gradient_hex")
SCALARS=("train_probe_loss_hex","phase_hex","sin_phase_hex","cos_phase_hex")


def model_map(receipt):
    rows=receipt.get("traces",[])
    result={(r["family"],r["variant"],r["seed"]):r for r in rows}
    expected={(f,k,s) for f in FAMILIES for k in KINDS for s in SEEDS}
    if set(result)!=expected or len(rows)!=24:
        raise ValueError("O11_MISSING_OR_DUPLICATE_MODEL_TRACE")
    return result


def compare(linux,windows):
    for receipt in (linux,windows):
        if receipt.get("schema")!="forge.optimizer.o11.native-train-only-trace.v1" or \
                receipt.get("O10_TRAIN_SELECT_DEV_CONSUMED")!=0 or \
                receipt.get("PROTECTED_FIRST_USE") is not False:
            raise ValueError("O11_ROLE_CUSTODY_VIOLATION")
        if receipt.get("code_identity")!=(
                "O10_PHASE_BLOB_56203c6aa60b29c4a5e8fb4bcd250bc212582209"):
            raise ValueError("O11_MODEL_IDENTITY_DRIFT")
        if set(receipt.get("o11_new_source_sha256",{}))!=set(FAMILIES):
            raise ValueError("O11_FAMILY_COVERAGE")
    identical_sources=(linux["o11_new_source_sha256"]==
                       windows["o11_new_source_sha256"])
    if not identical_sources:
        raise ValueError("O11_CROSS_OS_TRAIN_SOURCE_SHA_DRIFT")
    l,w=model_map(linux),model_map(windows)
    summary=[]
    earliest_any=None
    math_probe_diffs=[]
    for input_key in linux["math_library_probes"]:
        left=linux["math_library_probes"][input_key]
        right=windows["math_library_probes"].get(input_key)
        if not right:
            raise ValueError("O11_MISSING_NATIVE_MATH_PROBE")
        for op,v in left.items():
            other=right.get(op)
            if not other:
                raise ValueError("O11_MISSING_NATIVE_MATH_OP")
            if v!=other:
                math_probe_diffs.append({"input":input_key,"op":op,
                                         "linux":v,"windows":other})
    for family in FAMILIES:
        for kind in KINDS:
            for seed in SEEDS:
                key=(family,kind,seed)
                a,b=l[key]["trace"],w[key]["trace"]
                if len(a)!=len(TRACE) or len(b)!=len(TRACE) or \
                        tuple(x["step"] for x in a)!=TRACE or \
                        tuple(x["step"] for x in b)!=TRACE:
                    raise ValueError("O11_INCOMPLETE_FROZEN_TRACE")
                first_exact=None
                first_weight_1e12=None
                first_weight_1e6=None
                max_abs_weight=0.0
                first_field=None
                for x,y in zip(a,b):
                    step=x["step"]
                    for field in KEYS+SCALARS:
                        z1,z2=x[field],y[field]
                        if field in KEYS:
                            if len(z1)!=8 or len(z2)!=8:
                                raise ValueError("O11_TRACE_PARAMETER_SHAPE")
                            pairs=list(zip(z1,z2))
                        else:
                            pairs=[(z1,z2)]
                        for j,(v1,v2) in enumerate(pairs):
                            left,right=float.fromhex(v1),float.fromhex(v2)
                            if not math.isfinite(left) or not math.isfinite(right):
                                raise ValueError("O11_NONFINITE_NATIVE_FLOAT")
                            if v1!=v2 and first_exact is None:
                                first_exact=step
                                first_field=f"{field}[{j}]"
                            if field=="weight_hex":
                                diff=abs(left-right)
                                max_abs_weight=max(max_abs_weight,diff)
                                if first_weight_1e12 is None and diff>1e-12:
                                    first_weight_1e12=step
                                if first_weight_1e6 is None and diff>1e-6:
                                    first_weight_1e6=step
                row={
                    "family":family,"kind":kind,"seed":seed,
                    "first_exact_native_float_mismatch_step":first_exact,
                    "first_exact_native_float_mismatch_field":first_field,
                    "first_weight_divergence_gt_1e-12_step":first_weight_1e12,
                    "first_weight_divergence_gt_1e-6_step":first_weight_1e6,
                    "maximum_weight_absolute_difference":max_abs_weight,
                    "final_checkpoint_identity":(
                        l[key]["last_checkpoint_sha256"]==
                        w[key]["last_checkpoint_sha256"]),
                }
                summary.append(row)
                if first_exact is not None:
                    earliest_any=(first_exact if earliest_any is None
                                  else min(first_exact,earliest_any))
    if len(summary)!=24:
        raise ValueError("O11_DIAGNOSTIC_COVERAGE")
    return {
        "schema":"forge.optimizer.o11.cross-os-forensics.v1",
        "diagnostic_only":True,
        "scientific_GO":False,
        "o10_unchanged_frozen_protocol":"TRUE",
        "cross_os_source_digests_4_of_4_match":True,
        "independent_models_checked":len(summary),
        "frozen_trace_snapshots_per_model":len(TRACE),
        "earliest_exact_model_drift_step":earliest_any,
        "native_libm_probe_hex_mismatch_count":len(math_probe_diffs),
        "native_libm_probe_hex_mismatches":math_probe_diffs,
        "models":summary,
        "classification":(
            "O11_TRAINING_CROSS_OS_FLOAT_DIFFERENCES_IDENTIFIED"
            if any(x["first_weight_divergence_gt_1e-6_step"] is not None
                   for x in summary)
            else "O11_NO_WEIGHT_DIFFERENCE_ABOVE_1E-6_IN_FROZEN_TRAIN_ONLY_PROBE"
        ),
    }


def main():
    if len(sys.argv)!=4:
        raise SystemExit("usage: compare.py linux.json windows.json output.json")
    with open(sys.argv[1],encoding="utf-8") as fh:
        linux=json.load(fh)
    with open(sys.argv[2],encoding="utf-8") as fh:
        windows=json.load(fh)
    report=compare(linux,windows)
    output=pathlib.Path(sys.argv[3])
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",
                      encoding="utf-8")
    print("O11_ORIGINAL_O10_MODEL_SOURCE_UNCHANGED=PASS")
    print("O11_INDEPENDENT_TRAIN_SOURCE_SHA=4_OF_4_IDENTICAL")
    print("O11_TRAINED_MODEL_TRACE_COVERAGE=24_OF_24")
    print("O11_TRACE_SNAPSHOTS_PER_MODEL=14")
    print("O11_EARLIEST_ANY_NATIVE_DRIFT_STEP="+str(
        report["earliest_exact_model_drift_step"]))
    print("O11_MATH_LIBRARY_PROBE_MISMATCH_COUNT="+str(
        report["native_libm_probe_hex_mismatch_count"]))
    for row in report["models"]:
        if row["first_weight_divergence_gt_1e-6_step"] is not None:
            print("O11_WEIGHT_DRIFT "+row["family"]+" "+row["kind"]+
                  " seed="+str(row["seed"])+" first_step="+str(
                      row["first_weight_divergence_gt_1e-6_step"])+
                  " max_absolute="+str(row["maximum_weight_absolute_difference"]))
    print("O11_RESULT="+report["classification"])
    print("O11_NO_SCIENTIFIC_PROMOTION=PASS")
    print("O11_TRAIN_FORENSICS_RECEIPT="+str(output))


if __name__=="__main__":
    main()
