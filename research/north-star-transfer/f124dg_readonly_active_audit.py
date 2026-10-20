"""F124-DG independent read-only 72-cell budget/query and cost audit.

All four authentic sourcefree GitHub-hosted whole-OS shards are mandatory.
No models retrained, no synthetic or private source law imported by audit,
no original scientific 924-937 tasks replayed, and no CHECK re-selection.
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

def require(ok,why):
    if not ok:raise RuntimeError("F124DG_AUDIT_"+why)

def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def load(directory):
    names={"shard-"+family+"-"+str(seed)+".json" for family in FAMILIES
           for seed in (201,203)}
    paths=list(directory.glob("shard-*.json"))
    require(len(paths)==4 and {x.name for x in paths}==names,
            "ALL_FOUR_DISTINCT_SOURCEFREE_SHARDS")
    rows={}
    shards=[]
    for file in paths:
        shard=json.loads(file.read_text())
        require(shard["schema"]=="mass.f124dg.original-sourcefree-active-18-os-process-shard.v1"
                and shard["whole_OS_processes"]==18
                and len(shard["measurements"])==18
                and shard["original_scientific_firstuse_consumed"]==0
                and not shard["science_accepted"],"AUTHENTIC_COMPLETE_SHARD")
        shards.append({"file":file.name,"content_sha256":digest(shard)})
        for x in shard["measurements"]:
            key=x["family"],x["seed"],x["arm"],x["extra_oracle_budget"]
            require(x["family"]==shard["family"] and
                    x["seed"] in (shard["first_seed"],shard["first_seed"]+1)
                    and x["arm"] in ARMS and x["extra_oracle_budget"] in BUDGETS,
                    "EXACT_MEASURED_CELL_ID")
            require(key not in rows,"DUPLICATE_OR_RETRIED_CELL")
            require(x["schema"]=="mass.f124dg.frozen-sourcefree-budgeted-active-causal-trial.v1"
                    and x["FIT_episodes"]==24 and
                    x["CHECK_veto_episodes"]==8 and
                    x["HELDOUT_positive_episodes"]==8 and
                    x["new_oracle_queries_consumed"]==x["extra_oracle_budget"]
                    and x["queries_distinct"] and
                    x["final_rank"]>=x["original_FIT_rank"] and
                    x["rank_gain_from_extra_information"]==(
                        x["final_rank"]-x["original_FIT_rank"])
                    and x["full_hypothesis_dimension"]==163
                    and x["whole_process_includes_import_FIT_extra_oracle_CHECK_HELDOUT"]
                    and x["full_python_OS_user_sys_CPU_ns"]>0
                    and x["full_python_OS_peak_RSS_bytes"]>0
                    and x["sourcefree_hidden_coefficients_never_passed_to_models"]
                    and x["science_original_firstuse_consumed"] is False
                    and not x["science_accepted"],"EQUAL_INFORMATION_NATIVE_SAFETY")
            rows[key]=x
    expected={(f,s,a,b) for f in FAMILIES for s in SEEDS
              for a in ARMS for b in BUDGETS}
    require(set(rows)==expected and len(rows)==72,
            "ALL_72_ORIGINAL_PREDECLARED_PROCESS_RESULTS")
    for f in FAMILIES:
        for s in SEEDS:
            vals=[rows[f,s,a,b] for a in ARMS for b in BUDGETS]
            for field in ("FIT_hash","CHECK_hash","HELDOUT_hash",
                          "same_public_meta_score_sha256","original_FIT_rank"):
                require(len({v[field] for v in vals})==1,
                        "ALL_ARMS_SAME_SOURCE_AND_PUBLIC_INFO_"+field)
            for budget in BUDGETS:
                a=rows[f,s,"meta_rank",budget]
                p=rows[f,s,"independent_meta_rank",budget]
                # If independently specified equal meta rank-greedy cannot
                # reproduce the same evidence/answers, fail rather than
                # choose whichever arm gives a better outcome.
                for key in ("final_rank","natural_CHECK_admission",
                   "diagnostic_HELDOUT_exact_positives_of_8",
                   "diagnostic_HELDOUT_bit_errors","admitted_HELDOUT_exact_positives",
                   "diagnostic_HELDOUT_hard_false_positive_of_8"):
                    require(a[key]==p[key],
                            "INDEPENDENT_EQUALLY_INFORMED_PRIMARY_PEER_DISAGREES_"+key)
            require(rows[f,s,"meta_rank",0]["original_FIT_rank"]<=
                    rows[f,s,"meta_rank",16]["final_rank"]<=
                    rows[f,s,"meta_rank",48]["final_rank"],
                    "ORACLE_ADDITIONAL_INFORMATION_MONOTONIC_RANK")
    return rows,shards

def summary(rows):
    out=[]
    for f in FAMILIES:
        for arm in ARMS:
            for budget in BUDGETS:
                rs=[rows[f,s,arm,budget] for s in SEEDS]
                out.append({
                  "family":f,"arm":arm,"additional_oracle_queries_per_case":budget,
                  "cases":4,"natural_CHECK_admitted_cases_of_4":
                      sum(v["natural_CHECK_admission"] for v in rs),
                  "diagnostic_full_HELDOUT_positives_correct_out_of_32":
                      sum(v["diagnostic_HELDOUT_exact_positives_of_8"] for v in rs),
                  "admitted_full_HELDOUT_positives_correct_out_of_32":
                      sum(v["admitted_HELDOUT_exact_positives"] or 0 for v in rs),
                  "admitted_hard_false_positives":
                      sum(v["admitted_HELDOUT_hard_false_positive"] or 0 for v in rs),
                  "diagnostic_total_bit_errors":
                      sum(v["diagnostic_HELDOUT_bit_errors"] for v in rs),
                  "FIT_rank_by_seed":[v["original_FIT_rank"] for v in rs],
                  "final_rank_by_seed":[v["final_rank"] for v in rs],
                  "median_whole_OS_CPU_ns":statistics.median(
                     v["full_python_OS_user_sys_CPU_ns"] for v in rs),
                  "median_whole_OS_peak_RSS_bytes":statistics.median(
                     v["full_python_OS_peak_RSS_bytes"] for v in rs),
                  "sourcefree_only":True,"scientific_nonregression_proven":False
                })
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--shards",required=True,type=Path)
    ap.add_argument("--out",required=True,type=Path)
    args=ap.parse_args()
    require(not args.out.exists(),"NO_SOURCEFREE_AUDIT_OVERWRITE")
    rows,shards=load(args.shards)
    findings=summary(rows)
    record={
      "schema":"mass.f124dg.original-sourcefree-active-72wholeOS-readonly-evidence.v1",
      "full_original_72_processes":[rows[key] for key in sorted(rows)],
      "original_shard_hashes":shards,"all_18_aggregate_model_budget_rows":findings,
      "scientific_firstuse_consumed":0,
      "extra_queries_are_NEW_oracle_information_not_learned_without_DATA":True,
      "strongest_primary_comparator_exactly_informed_and_fit":True,
      "resource_FLOP_CPU_RSS_nonregression_certified":False,
      "scientific_acceptance":False}
    args.out.mkdir(parents=True)
    (args.out/"all-72-whole-os.json").write_text(
        json.dumps(record,sort_keys=True,indent=2)+"\n")
    safe={"schema":"mass.f124dg.original-active-learning-safe-summary.v1",
          "all_72_evidence_sha256":digest(record),"shard_hashes":shards,
          "aggregate":findings,"no_original_sci_firstuse":True,
          "scientific_acceptance":False}
    (args.out/"source-safe-summary.json").write_text(
        json.dumps(safe,sort_keys=True,indent=2)+"\n")
    print("F124DG_ALL_72_SOURCEFREE_FULL_OS_CASES=PASS")
    for r in findings:
        print("F124DG_ACTIVE_CAUSAL_RESULT="+json.dumps(r,sort_keys=True))
    print("F124DG_NEW_ORIGINAL_SCIENTIFIC_FIRSTUSE=0")
    print("F124DG_SCIENTIFIC_ACCEPTANCE=FALSE")

if __name__=="__main__":main()
