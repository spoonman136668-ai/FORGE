"""F124-DH READONLY original causal information bound and efficiency audit.

Uses the complete sealed ORIGINAL source-free F124-DG evidence from a
specific GitHub Actions run. Never imports learner, source generator,
FIT/private source, replay oracles, or even NumPy. A query increases GF(2)
feature rank by at most one. For every original seed, compute the sharp
minimal independent-intervention count required for full 163-rank
identification, and preserve real 0/16/48-budget policy outcomes and cost.

This is RETROSPECTIVE mechanistic diagnosis; does not convert prior
source-free results to new first-use, independent science or model promotion.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import statistics

FAMILIES=("sparse_degree4_GF2_unknown","dense_degree4_GF2_unknown")
SEEDS=(201,202,203,204)
ARMS=("meta_rank","independent_meta_rank","lex_exact_rank")
BUDGETS=(0,16,48)
HYP=163
ORIGINAL_RUN=39355584842
ORIGINAL_SHA="f6c98b741c4726589e33bbb192d4ce4598d669e5"

def need(ok,reason):
    if not ok:raise RuntimeError("F124DH_READONLY_"+reason)

def digest(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,
        separators=(",",":")).encode()).hexdigest()

def review(original,summary):
    need(original["schema"]==
         "mass.f124dg.original-sourcefree-active-72wholeOS-readonly-evidence.v1"
         and summary["schema"]==
         "mass.f124dg.original-active-learning-safe-summary.v1",
         "IMMUTABLE_DG_ORIGINAL_AUDIT_SCHEMA")
    need(digest(original)==summary["all_72_evidence_sha256"],
         "ORIGINAL_72_SOURCE_SAFE_CRYPTOGRAPHIC_IDENTITY")
    need(original["scientific_firstuse_consumed"]==0
         and original["extra_queries_are_NEW_oracle_information_not_learned_without_DATA"]
         and original["strongest_primary_comparator_exactly_informed_and_fit"]
         and not original["resource_FLOP_CPU_RSS_nonregression_certified"]
         and not original["scientific_acceptance"]
         and summary["no_original_sci_firstuse"],
         "HONEST_SCIENCE_INFORMATION_AND_STRONG_PEER")
    rows=original["full_original_72_processes"]
    expected={(fam,seed,arm,bud) for fam in FAMILIES for seed in SEEDS
              for arm in ARMS for bud in BUDGETS}
    keyed={(r["family"],r["seed"],r["arm"],r["extra_oracle_budget"]):r for r in rows}
    need(len(rows)==72 and set(keyed)==expected,
         "ALL_EXACT_ORIGINAL_CASES_AND_BUDGETS")
    deficits=[]
    for fam in FAMILIES:
        for seed in SEEDS:
            cohort=[keyed[fam,seed,arm,bud] for arm in ARMS for bud in BUDGETS]
            need(len({v["FIT_hash"] for v in cohort})==1
                 and len({v["CHECK_hash"] for v in cohort})==1
                 and len({v["HELDOUT_hash"] for v in cohort})==1
                 and len({v["original_FIT_rank"] for v in cohort})==1,
                 "SAME_ORIGINAL_PUBLIC_EVIDENCE_PER_CASE")
            original_rank=cohort[0]["original_FIT_rank"]
            need(0<=original_rank<=HYP,"VALID_EXACT_HYPOTHESIS_RANK")
            lower=HYP-original_rank
            d={"family":fam,"seed":seed,"original_FIT_rank":original_rank,
               "GF2_operator_hypothesis_rank":HYP,
               "minimum_independent_new_4bit_queries_for_FULL_IDENTIFICATION":lower,
               "16_queries_can_identify_FULL_model":lower<=16,
               "48_queries_can_identify_FULL_model":lower<=48,
               "mathematically_possible_to_IDENTIFY_FULL_model_within_48":lower<=48,
               "full_function_identification_is_NOT_REQUIRED_for_some_correct_predictions":True,
               "sourcefree_original_only":True}
            deficits.append(d)
            for arm in ARMS:
                for budget in BUDGETS:
                    x=keyed[fam,seed,arm,budget]
                    number=x["new_oracle_queries_consumed"]
                    need(x["full_hypothesis_dimension"]==HYP
                         and number<=budget and number>=0
                         and x["final_rank"]==original_rank+number
                         and x["rank_gain_from_extra_information"]==number
                         and (number==budget or x["final_rank"]==HYP)
                         and x["query_budget_is_MAXIMUM_not_forced_redundant_observations"]
                         and x["full_python_OS_user_sys_CPU_ns"]>0
                         and x["full_python_OS_peak_RSS_bytes"]>0,
                         "EACH_ORIGINAL_INFORMATION_UNIT_METERED_AND_NATIVE_COST")
                    need((x["final_rank"]==HYP)==(number==lower),
                         "MAXIMUM_RANK_IDENTIFICATION_IDENTITY")
            for bud in BUDGETS:
                a=keyed[fam,seed,"meta_rank",bud]
                peer=keyed[fam,seed,"independent_meta_rank",bud]
                for prop in ("final_rank","natural_CHECK_admission",
                  "diagnostic_HELDOUT_exact_positives_of_8",
                  "admitted_HELDOUT_exact_positives",
                  "admitted_HELDOUT_hard_false_positive"):
                    need(a[prop]==peer[prop],
                         "EQUAL_SOURCE_TRAINED_PEER_MUST_MATCH_LEARNED_POLICY_"+prop)
    grouped=[]
    for fam in FAMILIES:
        for bud in BUDGETS:
            arms={}
            for arm in ARMS:
                z=[keyed[fam,seed,arm,bud] for seed in SEEDS]
                arms[arm]={
                    "natural_CHECK_admitted_cases_of_4":
                         sum(v["natural_CHECK_admission"] for v in z),
                    "admitted_HELDOUT_exact_positives_of_32":
                         sum(v["admitted_HELDOUT_exact_positives"] or 0 for v in z),
                    "diagnostic_HELDOUT_exact_positives_of_32":
                         sum(v["diagnostic_HELDOUT_exact_positives_of_8"] for v in z),
                    "admitted_hard_false_positive_count":
                         sum(v["admitted_HELDOUT_hard_false_positive"] or 0 for v in z),
                    "rank_by_seed":[v["final_rank"] for v in z],
                    "median_full_OS_CPU_ns":statistics.median(
                         v["full_python_OS_user_sys_CPU_ns"] for v in z),
                    "median_full_OS_peak_RSS_bytes":statistics.median(
                         v["full_python_OS_peak_RSS_bytes"] for v in z)}
            base=arms["independent_meta_rank"]["median_full_OS_CPU_ns"]
            candidate=arms["meta_rank"]["median_full_OS_CPU_ns"]
            groups={"family":fam,"new_information_budget":bud,"models":arms,
             "meta_rank_vs_equal_peer_median_whole_OS_CPU_ratio":
                  candidate/base,
             "strong_control_matches_or_beats_candidate_on_original_heldout":
                  arms["lex_exact_rank"]["admitted_HELDOUT_exact_positives_of_32"]>=
                  arms["meta_rank"]["admitted_HELDOUT_exact_positives_of_32"],
             "equal_internal_FLOPs_or_native_operations_proven":False,
             "scientific_CPU_RSS_nonregression_qualified":False}
            grouped.append(groups)
    return {"schema":"mass.f124dh.retrospective-sourcefree-rank-and-cost-bound.v1",
      "original_run_id":ORIGINAL_RUN,
      "original_run_head":ORIGINAL_SHA,
      "original_run_full_72_evidence_sha256":digest(original),
      "casewise_sharp_information_lower_bounds":deficits,
      "all_six_equal_budget_native_cost_policy_comparisons":grouped,
      "cases_with_48_queries_insufficient_for_FULL_rank":
            [dict(family=d["family"],seed=d["seed"],need=d[
               "minimum_independent_new_4bit_queries_for_FULL_IDENTIFICATION"])
             for d in deficits if not d["48_queries_can_identify_FULL_model"]],
      "recomputed_as_readonly_math_not_a_new_sourcefree_trial":True,
      "original_scientific_firstuse_consumed":0,
      "source_or_model_replayed":False,
      "CHECK_veto_preserved":True,
      "scientific_acceptance":False,
      "protected_source_opened":False,
      "model_promotion":False
    }

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--source",required=True,type=Path)
    a.add_argument("--out",required=True,type=Path)
    args=a.parse_args()
    need(not args.out.exists(),"APPEND_SAFE_EVIDENCE_NO_OVERWRITE")
    full=json.loads((args.source/"all-72-whole-os.json").read_text())
    safe=json.loads((args.source/"source-safe-summary.json").read_text())
    result=review(full,safe)
    args.out.mkdir(parents=True)
    (args.out/"original-readonly-rank-lower-bounds.json").write_text(
         json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("F124DH_ORIGINAL_72_SOURCEFREE_OS_EVIDENCE_READONLY_AUDIT=PASS")
    print("F124DH_ALL_EIGHT_GF2_MINIMUM_INFORMATION_BOUND="+json.dumps(
         [{k:z[k] for k in ("family","seed","original_FIT_rank",
           "minimum_independent_new_4bit_queries_for_FULL_IDENTIFICATION")}
          for z in result["casewise_sharp_information_lower_bounds"]],sort_keys=True))
    print("F124DH_48_QUERY_FULL_RANK_IMPOSSIBILITY="+json.dumps(
          result["cases_with_48_queries_insufficient_for_FULL_rank"],
          sort_keys=True))
    for g in result["all_six_equal_budget_native_cost_policy_comparisons"]:
        print("F124DH_POLICY="+json.dumps({
          "family":g["family"],"budget":g["new_information_budget"],
          "meta_admitted":g["models"]["meta_rank"][
             "admitted_HELDOUT_exact_positives_of_32"],
          "peer_admitted":g["models"]["independent_meta_rank"][
             "admitted_HELDOUT_exact_positives_of_32"],
          "lex_admitted":g["models"]["lex_exact_rank"][
             "admitted_HELDOUT_exact_positives_of_32"],
          "meta_to_peer_CPU_ratio":g[
             "meta_rank_vs_equal_peer_median_whole_OS_CPU_ratio"]},sort_keys=True))
    print("F124DH_NEW_EXPERIMENTAL_FIRSTUSE=0")
    print("F124DH_SCIENCE_ACCEPTED=FALSE")

if __name__=="__main__":main()
