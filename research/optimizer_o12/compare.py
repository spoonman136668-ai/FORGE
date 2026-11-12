"""O12 independent native evidence comparison, intentionally strict for Decimal.

Fail closed on any cross-OS training role drift, Decimal parameter/moment/
gradient/probe difference, missing sample or violation of precommitted role
custody. Original native float drift is *diagnostic evidence*, never hidden.
"""
import json
import math
from pathlib import Path
import sys

FAMILIES=("A_CUE0_COMPOSE","B_CUE4_COMPOSE","C_SELECTOR_COMPOSE","NULL_IID")
ROLES=("O12_TRAIN","O12_TRAIN_DIAGNOSTIC")
ARMS=("NATIVE_O10_FLOAT","DECIMAL_PHASE_34","DECIMAL_PHASE_34_CONDITIONED")
SEEDS=(17,31)
STEPS=(0,1,2,3,16,96,192,384,768,1536,1920)
FIELDS=("w","adam_m","adam_v","train_gradient",
        "train_diagnostic_query_loss","phase","phase_sin","phase_cos")


def map_models(receipt):
    rows=receipt["models"]
    keys=[(m["family"],m["seed"],m["arm"]) for m in rows]
    expected={(f,s,a) for f in FAMILIES for s in SEEDS for a in ARMS}
    if len(rows)!=24 or len(set(keys))!=24 or set(keys)!=expected:
        raise ValueError("O12_EXACT_MODEL_ROLE_COVERAGE")
    return dict(zip(keys,rows))


def compare(linux,windows):
    for data in (linux,windows):
        if data.get("schema")!="forge.optimizer.o12.new-train-only-numeric-receipt.v1" or \
                data.get("no_old_o10_o11_dev_or_select_role_consumption") is not True or \
                data.get("protected_scientific_first_use") is not False or \
                data.get("scientific_candidate_admitted") is not False or \
                data.get("original_o10_model_code_blob")!=(
                    "56203c6aa60b29c4a5e8fb4bcd250bc212582209"):
            raise ValueError("O12_CUSTODY_OR_ORIGINAL_MODEL_IDENTITY")
    want={f"{f}:{r}" for f in FAMILIES for r in ROLES}
    if set(linux["sources_sha256"])!=want or \
            set(windows["sources_sha256"])!=want or \
            linux["sources_sha256"]!=windows["sources_sha256"]:
        raise ValueError("O12_FRESH_TRAIN_SOURCE_SHA_MISMATCH")
    l,w=map_models(linux),map_models(windows)
    wrong=[]
    native_drift=[]
    conditioned_vs_raw=[]
    decimal_compared=0
    for family in FAMILIES:
        for seed in SEEDS:
            for arm in ARMS:
                x,y=l[(family,seed,arm)],w[(family,seed,arm)]
                a,b=x["trace"],y["trace"]
                if len(a)!=len(STEPS) or len(b)!=len(STEPS) or \
                   tuple(t["step"] for t in a)!=STEPS or \
                   tuple(t["step"] for t in b)!=STEPS:
                    raise ValueError("O12_FROZEN_TRACE_COVERAGE")
                first_float=None
                first_native_1e12=None
                first_native_1e6=None
                worst_abs=0.
                for lx,wx in zip(a,b):
                    step=lx["step"]
                    for field in FIELDS:
                        val1,val2=lx[field],wx[field]
                        pairs=(zip(val1,val2)
                               if isinstance(val1,list) else [(val1,val2)])
                        if isinstance(val1,list) and (len(val1)!=8 or len(val2)!=8):
                            raise ValueError("O12_CHECKPOINT_SHAPE")
                        for j,(av,bv) in enumerate(pairs):
                            if not (math.isfinite(float.fromhex(av) if arm=="NATIVE_O10_FLOAT"
                                                  else float(av)) and
                                    math.isfinite(float.fromhex(bv) if arm=="NATIVE_O10_FLOAT"
                                                  else float(bv))):
                                raise ValueError("O12_NONFINITE_NATIVE_RECEIPT")
                            if arm!="NATIVE_O10_FLOAT":
                                decimal_compared+=1
                                if av!=bv:
                                    wrong.append({"family":family,"seed":seed,
                                                  "arm":arm,"step":step,
                                                  "field":field,"index":j,
                                                  "linux":av,"windows":bv})
                            else:
                                if av!=bv and first_float is None:
                                    first_float={"step":step,"field":field,"index":j}
                                if field=="w":
                                    delta=abs(float.fromhex(av)-float.fromhex(bv))
                                    worst_abs=max(worst_abs,delta)
                                    if delta>1e-12 and first_native_1e12 is None:
                                        first_native_1e12=step
                                    if delta>1e-6 and first_native_1e6 is None:
                                        first_native_1e6=step
                if arm!="NATIVE_O10_FLOAT":
                    if x["checkpoint_sha256"]!=y["checkpoint_sha256"]:
                        wrong.append({"family":family,"seed":seed,"arm":arm,
                                      "field":"final_checkpoint_sha256"})
                else:
                    native_drift.append({"family":family,"seed":seed,
                                         "first_hex_difference":first_float,
                                         "first_weight_gt_1e-12":first_native_1e12,
                                         "first_weight_gt_1e-6":first_native_1e6,
                                         "max_abs_weight_gap":worst_abs})
            raw=w[(family,seed,"DECIMAL_PHASE_34")]["trace"][-1]
            cond=w[(family,seed,"DECIMAL_PHASE_34_CONDITIONED")]["trace"][-1]
            conditioned_vs_raw.append({
                "family":family,"seed":seed,
                "conditioned_minus_original_decimal_train_diagnostic_nll":
                    float(cond["train_diagnostic_query_loss"])-
                    float(raw["train_diagnostic_query_loss"]),
                "raw_train_diagnostic_nll":raw["train_diagnostic_query_loss"],
                "conditioned_train_diagnostic_nll":cond["train_diagnostic_query_loss"],
            })
    if wrong:
        raise ValueError("O12_DECIMAL_EXACT_CROSS_OS_FAILURE "+json.dumps(wrong[:8]))
    return {
        "schema":"forge.optimizer.o12.cross-os-trainonly-result.v1",
        "accepted_scientific_candidate":False,
        "original_O10_reproducibility_gate":"FAIL_UNCHANGED",
        "original_O10_DEV_role_consumed":0,
        "source_role_digests_match":"8_OF_8",
        "decimal_cross_os_comparison":"TEXT_EXACT_PASS",
        "decimal_scalar_equal_checks":decimal_compared,
        "decimal_model_runs":16,
        "trace_steps_per_model":len(STEPS),
        "native_original_model_drift":native_drift,
        "conditioned_minus_unconditioned_train_diagnostic_loss":conditioned_vs_raw,
        "resource_seconds":{
            "linux_process_cpu_s":linux["whole_process_cpu_s"],
            "windows_process_cpu_s":windows["whole_process_cpu_s"],
        },
        "result":"O12_TRAIN_ONLY_DETERMINISTIC_ARITHMETIC_QUALIFIED_NOT_SCIENCE",
    }


def main():
    if len(sys.argv)!=4:
        raise SystemExit("usage: compare.py linux.json windows.json report.json")
    with open(sys.argv[1],encoding="utf-8") as f:
        linux=json.load(f)
    with open(sys.argv[2],encoding="utf-8") as f:
        windows=json.load(f)
    report=compare(linux,windows)
    dest=Path(sys.argv[3])
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("O12_FRESH_SOURCE_SHA256=8_OF_8_IDENTICAL")
    print("O12_DECIMAL_EXACT_COMPARISON=PASS")
    print("O12_DECIMAL_SCALAR_CHECKS="+str(report["decimal_scalar_equal_checks"]))
    for r in report["native_original_model_drift"]:
        print("O12_ORIGINAL_FLOAT "+str(r))
    for r in report["conditioned_minus_unconditioned_train_diagnostic_loss"]:
        print("O12_TRAIN_ONLY_CONDITIONED_LOSS_DELTA "+str(r))
    print("O12_FROZEN_O10_FAILURE_PRESERVED=PASS")
    print("O12_SCIENTIFIC_GO=NOT_EVALUATED")
    print("O12_REPORT="+str(dest))


if __name__=="__main__":
    main()
