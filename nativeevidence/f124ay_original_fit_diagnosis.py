"""F124-AY one original sealed Ygg TRAIN-FIT failure-attribution experiment.

Only source's FIT constructor is called. The evaluator-only structural
witness is computed AFTER all source-blind model probes have completed.
The 96-observation arm is extra-cost attribution, not an eligible model.
"""
from __future__ import annotations
import argparse,hashlib,json,sys,time,platform
from collections import Counter,defaultdict
from pathlib import Path
import f124ay_source_only as birth
import f124ay_structural_diagnostics as diag

SCHEMA="forge.research.f124ay.one-original-frozen-negative-decomposition.v1"
def need(ok,tag):birth.need(ok,"FIRST_DIAGNOSTIC_"+tag)

def summarize(rows,key):
    groups={"affine":[],"feistel":[]}
    for row in rows:
        groups[row["operator_family"]].append(row[key])
    out={}
    for kind,items in groups.items():
        need(len(items)==12,"TWELVE_CASES_PER_OPERATOR_FAMILY")
        original=[x["public48"] for x in items]
        extended=[x["public96"] for x in items]
        out[kind]={
            "cases":len(items),
            "48_public_abstained":sum(x["original_AX_admitted"] is False for x in original),
            "48_rank_zero":sum(x["rank_valid_fits"]==0 for x in original),
            "48_fit_residual_rejected":sum(x["first_hard_blocker"]=="FIT_RESIDUAL" for x in original),
            "48_check_rejected":sum(x["first_hard_blocker"]=="CHECK" for x in original),
            "48_bijection_rejected":sum(x["first_hard_blocker"]=="BIJECTION" for x in original),
            "48_passed":sum(x["first_hard_blocker"]=="ADMITTED" for x in original),
            "48_rank_valid_trials_total":sum(x["rank_valid_fits"] for x in original),
            "96_rank_valid_trials_total":sum(x["rank_valid_fits"] for x in extended),
            "48_best_fit_error_per_input_bit": [
                x["best_fit_error_per_input_bit"] for x in original],
            "96_best_fit_error_per_input_bit":[
                x["best_fit_error_per_input_bit"] for x in extended],
            "48_best_CHECK_accuracy":[x["best_observed_public_CHECK_accuracy"] for x in original],
            "96_best_CHECK_accuracy":[x["best_observed_public_CHECK_accuracy"] for x in extended],
        }
    return out

def run():
    freeze=birth.frozen()
    rows=birth.fit_rows()
    sourceonly=[]
    timer=time.process_time_ns()
    for seed,vector,family,op,nonce,p,n in rows:
        original=birth.public48(seed,vector,op,p["demos"])
        expanded=birth.public96_diagnostic(seed,vector,op,original)
        # Only opaque sourceblind PUBLIC pairs and nonce go to the learner.
        first=diag.probe(original,nonce)
        second=diag.probe(expanded,nonce)
        need(first["public_responses"]==48 and second["public_responses"]==96
             and first["attempts"]==second["attempts"]==256 and
             first["AX_max_extra_model_bits"]==second["AX_max_extra_model_bits"]==320,
             "FIXED_COMPOSITIONAL_CENSUS")
        sourceonly.append({"seed":seed,"vector":list(vector),
                          "graph_family":family,
                          "operator_family":"affine" if op.startswith("affine_") else "feistel",
                          "operator":op,"model_results":{"public48":first,"public96":second}})
    sourceblind_cpu=time.process_time_ns()-timer
    # Diagnostics now independently use evaluator truth. No evaluator truth is
    # passed into, used to select, or used to tune any model.
    structural={op:diag.witness(op) for op in birth.OPERATORS["TRAIN"]}
    by_family=summarize(sourceonly,"model_results")
    for op,result in structural.items():
        need(result["oracle_evaluator_only"]
             and result["operator_family"] in ("affine","feistel"),
             "SOURCE_ONLY_ORACLE_DIAGNOSTIC")
    counts=Counter(row["graph_family"] for row in sourceonly)
    need(counts==Counter({fam:6 for fam in birth.FAMILIES})
         and len(sourceonly)==24,"COMPLETE_ORIGINAL_TRAIN_FIT")
    proof={
        "affine_any_third_derivative":
            any(v["proven_outside_degree2"] for v in structural.values()
                if v["operator_family"]=="affine"),
        "Feistel_all_operators_proven_outside_quadratic":
            all(v["proven_outside_degree2"] for v in structural.values()
                if v["operator_family"]=="feistel"),
        "Feistel_all_operators_proven_outside_two_pairs":
            all(v["proven_outside_AX_2pair_class"] for v in structural.values()
                if v["operator_family"]=="feistel"),
        "finite_witness_not_a_fit_or_evaluation_model":True
    }
    return {"schema":SCHEMA,"parent":"089745a0ea0c388842c0ed1be5f9221daf580549",
        "freeze_git_blob":birth.FREEZE_BLOB,
        "freeze_before_code_commit":"3df04df42869c5cf3f58386d3feea628913d1942",
        "original_frozen_FIT_cases":24,"FIT_cases_per_family":12,
        "FIT_cases_per_graph_family":6,
        "source_oracle_truth_evaluator_only":True,
        "AX_original_sparse_source_unchanged":True,
        "original_48_public_responses_per_case":48,
        "diagnostic_96_public_responses_per_case":96,
        "public_extra_responses_per_case":48,
        "public_total_observations_per_case":96,
        "public_input_uniqueness_not_assumed":True,
        "extra_information_not_eligible_as_equal_cost":True,
        "public_noise_48":6,"public_noise_96":12,
        "fitting_attempts_per_case_per_arm":256,
        "sourceblind_total_cpu_ns":sourceblind_cpu,
        "runtime":{"python":platform.python_version(),"platform":platform.platform()},
        "structural_witnesses_by_operator":structural,
        "structural_claims":proof,
        "sourceblind_diagnostic_by_operator_family":by_family,
        "individual_FIT_cases":sourceonly,
        "reserved_SCREEN_cases_constructed":0,
        "reserved_DEV_cases_constructed":0,
        "Wingless_cases_constructed":0,
        "scientific_acceptance":False,
        "optimizer_promotion":False,
        "production_activation":False,
        "accepted_ref_mutation":False,
        "merging_authorized":False,
        "original_negative_retained":True}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    args=p.parse_args()
    path=Path(args.output)
    need(path.parent.is_dir() and not path.exists(),"NEW_ONLY_ORIGINAL_RECEIPT")
    d=run()
    raw=(json.dumps(d,sort_keys=True,indent=2)+"\n").encode()
    with path.open("xb") as f:f.write(raw)
    print("F124AY_FIRST_FIT_JSON_SHA256="+hashlib.sha256(raw).hexdigest())
    for op,w in d["structural_witnesses_by_operator"].items():
        print("F124AY_STRUCTURAL_"+op+"="+json.dumps({
           k:w[k] for k in ("distinct_nonzero_second_difference_pairs_at_zero",
                "nonzero_third_derivatives","proven_outside_degree2",
                "proven_outside_AX_2pair_class")},sort_keys=True))
    for group,v in d["sourceblind_diagnostic_by_operator_family"].items():
        print("F124AY_ATTRIBUTION_"+group+"="+json.dumps({
           k:v[k] for k in ("cases","48_public_abstained","48_rank_zero",
           "48_fit_residual_rejected","48_check_rejected",
           "48_bijection_rejected","48_passed","48_rank_valid_trials_total",
           "96_rank_valid_trials_total")},sort_keys=True))
    print("F124AY_PROVEN_OUTSIDE_DEGREE2_ALL_FEISTEL="+str(
        d["structural_claims"]["Feistel_all_operators_proven_outside_quadratic"]).lower())
    print("F124AY_SCREEN_DEV_UNTOUCHED=true")
    print("F124AY_SCIENTIFIC_PROMOTION=false")

if __name__=="__main__":
    try:main()
    except (ValueError,TypeError,KeyError,OSError,ArithmeticError,AssertionError) as error:
        print("F124AY_FAIL_CLOSED:"+str(error),file=sys.stderr)
        sys.exit(1)
