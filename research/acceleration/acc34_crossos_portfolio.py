"""ACC-34: preserve all 36 original acceleration hypotheses, audit native Go results.

This source-only portfolio registrar does NOT import original native models,
access scientific holdouts, change an accepted research registry, or trigger
FORGE autonomous model selection. Windows/Linux results must be independent.
"""
from __future__ import annotations
import argparse
import json
import pathlib
import sys

ROOT=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"research"/"ac07_sourcefree"))
import ac08_portfolio

SCHEMA="forge.acc34.acceleration-36-native-go-stage2-review.v1"
GO_SCHEMA="forge.acc34.acd1.native-go-verified-delta-sourcefree.v1"
POS="ACC34_ACD1_VERIFIED_GO_KERNEL_CPU_AND_SYS_POSITIVE__NO_SCIENCE"
NEG="ACC34_ACD1_NO_TOTAL_VERIFIED_NATIVE_GO_CPU_WIN__NO_SCIENCE"

def validate(report,host):
    if not isinstance(report,dict):
        raise ValueError("ACC34_INVALID_OS_REPORT")
    required={
        "schema":GO_SCHEMA,"acceleration_candidate":"AC-D1",
        "portfolio_total":36,"native_go_kernel_only":True,
        "original_native_models_untouched":True,
        "scientific_first_use":False,"scientific_admission":False,
        "cpu_includes_fit_and_verification":True,
        "true_os_peak_rss_measured":False,
        "pre_registered_cpu_threshold":0.9,
        "pre_registered_sys_threshold":1.1,
    }
    if any(report.get(k)!=v for k,v in required.items()) or report.get("classification") not in (POS,NEG):
        raise ValueError("ACC34_OS_SOURCE_OR_SCOPE_DRIFT:"+host)
    scenarios=report.get("scenarios")
    if not isinstance(scenarios,list) or [s.get("scenario") for s in scenarios]!=[
        "BENIGN","HIDDEN_INTERACTION"]:
        raise ValueError("ACC34_FROZEN_SOURCE_SCENARIOS:"+host)
    supposed_positive=True
    for s in scenarios:
        if (s.get("verified_exact_output_equal") is not True or
            s.get("oracle_exact_output_equal") is not True or
            s.get("full_measured_events")!=5*4096 or
            s.get("verified_measured_events")!=5*4096 or
            len(s.get("five_paired_verified_full_cpu_ratios",[]))!=5 or
            len(s.get("five_paired_verified_full_sys_ratios",[]))!=5 or
            any(not isinstance(q,(int,float)) or q<=0 for q in
                s["five_paired_verified_full_cpu_ratios"]+
                s["five_paired_verified_full_sys_ratios"]) or
            s["unverified_diagnostic"]["worker"]["fit_probes"]!=24 or
            s["unverified_diagnostic"]["worker"]["scientific_first_use"] is not False or
            s["oracle_diagnostic"]["worker"]["fit_probes"]!=0):
            raise ValueError("ACC34_CORRECTNESS_AND_FIT_BARRIER:"+host)
        if (s["scenario"]=="BENIGN" and s["unverified_mismatched_events"]!=0 or
            s["scenario"]=="HIDDEN_INTERACTION" and
            (s["unverified_mismatched_events"]<1 or s["verified_repairs_total"]<1)):
            raise ValueError("ACC34_NEGATIVE_CONSEQUENCE_EVIDENCE_MISSING:"+host)
        cpu=s.get("median_verified_full_cpu_ratio")
        mem=s.get("median_verified_full_sys_ratio")
        if not isinstance(cpu,(int,float)) or not isinstance(mem,(int,float)):
            raise ValueError("ACC34_RESOURCE_EVIDENCE_MISSING:"+host)
        if cpu>0.9 or mem>1.1:
            supposed_positive=False
    if report["classification"]!=(POS if supposed_positive else NEG):
        raise ValueError("ACC34_CLASSIFICATION_NOT_PREDECLARED:"+host)
    return True

def synthesize(linux,windows):
    validate(linux,"linux")
    validate(windows,"windows")
    for index in range(2):
        a=linux["scenarios"][index];b=windows["scenarios"][index]
        if (a["unverified_mismatched_events"]!=b["unverified_mismatched_events"] or
            a["verified_repairs_total"]!=b["verified_repairs_total"]):
            raise ValueError("ACC34_CROSS_OS_DIFFERENT_CAUSAL_RESULT")
    portfolio=ac08_portfolio.report()
    rows=portfolio["portfolio_rows"]
    original={f"U{i:02d}" for i in range(1,31)}
    additional={f"AC-D{i}" for i in range(1,7)}
    if (portfolio["unique_claim_count"]!=36 or len(rows)!=36 or
        {r["claim_id"] for r in rows}!=original|additional or
        set(portfolio["physical_substitute_only_ids"])!={"U03","U06"} or
        not portfolio["negative_evidence_preserved"] or
        portfolio["scientific_first_use_authorized"] or
        portfolio["scientific_admission_authorized"]):
        raise ValueError("ACC34_ORIGINAL_36_PORTFOLIO_LOST")
    cross_positive=linux["classification"]==POS and windows["classification"]==POS
    items=[]
    for row in rows:
        ident=row["claim_id"]
        items.append({
            "id":ident,"title":row["title"],"original_evidence":row["measured_by"],
            "stage1_status":row["evidence_scope"],
            "stage2_status":"NATIVE_GO_KERNEL_ENGINEERING_TESTED" if ident=="AC-D1" else "NOT_YET_EXECUTED",
            "actual_native_model_speedup_proven":False,
            "scientific_admission":False,
            "research_retained":True,
            "next_action":("Evaluate discovery/verification tradeoff against matched native controls" if ident=="AC-D1"
                else "Retain bounded candidate for independently preregistered Stage 2 investigation")
        })
    return {
        "schema":SCHEMA,
        "original_30_plus_six_kept":True,
        "all_36_covers_exactly":len(items),
        "source_evidence_commit_pins":portfolio["source_evidence_commit_pins"],
        "physical_hardware_substitutes_not_real_physical_tests":["U03","U06"],
        "continuation_from_portfolio":"AC08",
        "stage2_first_native_go_kernel_candidate":"AC-D1",
        "source_only_native_go_linux_classification":linux["classification"],
        "source_only_native_go_windows_classification":windows["classification"],
        "cross_host_engineering_cpu_and_sys_positive":cross_positive,
        "aggregate_engineering_classification":POS if cross_positive else NEG,
        "scientific_first_use":False,"scientific_admission":False,
        "original_native_model_integration":False,
        "FORGE_autonomy_or_controller_mutated":False,
        "next_original_research_priority":["AC-D1 verification cost","AC-D3 delayed-memory split","AC-D5 collision-qualified local credit"],
        "acceleration_candidates":items,
        "host_results":{
            "linux":[{"scenario":s["scenario"],"cpu_ratio":s["median_verified_full_cpu_ratio"],
                      "sys_ratio":s["median_verified_full_sys_ratio"],
                      "unsafe_missed_events":s["unverified_mismatched_events"],
                      "verified_repairs":s["verified_repairs_total"]} for s in linux["scenarios"]],
            "windows":[{"scenario":s["scenario"],"cpu_ratio":s["median_verified_full_cpu_ratio"],
                        "sys_ratio":s["median_verified_full_sys_ratio"],
                        "unsafe_missed_events":s["unverified_mismatched_events"],
                        "verified_repairs":s["verified_repairs_total"]} for s in windows["scenarios"]]
        }
    }

def main():
    p=argparse.ArgumentParser()
    for arg in ("linux","windows","output"):
        p.add_argument("--"+arg,required=True,type=pathlib.Path)
    a=p.parse_args()
    result=synthesize(json.loads(a.linux.read_text(encoding="utf-8")),
                      json.loads(a.windows.read_text(encoding="utf-8")))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("ACC34_PORTFOLIO_36_ORIGINAL_CANDIDATES=PASS")
    print("ACC34_ACD1_CROSS_HOST_VERIFIED_CPU_CLASSIFICATION="+
          result["aggregate_engineering_classification"])
    print("ACC34_SCIENTIFIC_MODEL_PROMOTION=NO")
if __name__=="__main__":
    main()
