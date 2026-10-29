"""ACC-34 authoritative 36-ID acceleration scoreboard, explicitly NOT native model admission.

It reuses the unchanged AC-08 exact-source register. AC-10..AC-32
causal-learning and MiniGrid compatibility gates cannot silently count as
a 36-method native acceleration performance pass.
"""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"research/ac07_sourcefree/ac08_portfolio.py"
SCHEMA="forge.acc34.acceleration36-stage2-tracking.v1"
EXPECTED={f"U{i:02d}" for i in range(1,31)}|{f"AC-D{i}" for i in range(1,7)}
def portfolio_module():
    spec=importlib.util.spec_from_file_location("acc34_exact_ac08",SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("ACC34_ORIGINAL_AC08_REGISTER_UNAVAILABLE")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def scoreboard(run_full_screening=False):
    reg=portfolio_module()
    if len(reg.ORIGINAL_NAMES)!=30 or len(reg.NATIVE_NAMES)!=6:
        raise RuntimeError("ACC34_ORIGINAL_36_NAME_REGISTER_DRIFT")
    if (set(reg.AC06_ORIGINAL)|set(reg.AC07_ORIGINAL))!={
        f"U{i:02d}" for i in range(1,31)} or
        set(reg.AC06_ORIGINAL)&set(reg.AC07_ORIGINAL) or
        set(reg.PHYSICAL_ONLY)!={"U03","U06"}):
        raise RuntimeError("ACC34_ORIGINAL_EXPERIMENT_COVERAGE_DRIFT")
    if run_full_screening:
        previous=reg.report()
        if previous.get("unique_claim_count")!=36 or {
            x["claim_id"] for x in previous["portfolio_rows"]}!=EXPECTED or not previous["negative_evidence_preserved"]:
            raise RuntimeError("ACC34_ORIGINAL_SCREENING_RESULTS_NOT_REPRODUCED")
    rows=[]
    for i,name in enumerate(reg.ORIGINAL_NAMES,1):
        ident=f"U{i:02d}"
        source="AC06" if ident in reg.AC06_ORIGINAL else "AC07"
        rows.append({
            "claim_id":ident,"title":name,
            "original_proposal":True,
            "stage1_evidence":source,
            "stage1_scope":("DIGITAL_SUBSTITUTE_NOT_PHYSICAL_PROOF"
                            if ident in reg.PHYSICAL_ONLY else "RESTRICTED_SYNTHETIC_ONLY"),
            "stage2_native_model_integrated":False,
            "stage2_performance_status":"NOT_QUALIFIED",
            "follow_up_allowed":True,
            "scientific_admission":False,
        })
    for i,name in enumerate(reg.NATIVE_NAMES,1):
        ident=f"AC-D{i}"
        rows.append({
            "claim_id":ident,"title":name,
            "original_proposal":False,"stage1_evidence":"AC05",
            "stage1_scope":"RESTRICTED_SYNTHETIC_LEARNING_ONLY",
            "stage2_native_model_integrated":False,
            "stage2_performance_status":("GO_CPU_MICROKERNEL_UNQUALIFIED_NOT_MODEL"
                                           if ident=="AC-D1" else "NOT_QUALIFIED"),
            "follow_up_allowed":True,
            "scientific_admission":False,
        })
    if len(rows)!=36 or {x["claim_id"] for x in rows}!=EXPECTED:
        raise RuntimeError("ACC34_DUPLICATE_OR_MISSING_CANDIDATE")
    return {
        "schema":SCHEMA,
        "original_user_proposals":30,"additional_mechanism_hypotheses":6,
        "total_registered_candidates":36,
        "initial_source_free_restricted_screened":36,
        "hardware_substitutes_not_physical_results":["U03","U06"],
        "source_evidence_pins":reg.CASE_PINS,
        "stage2_qualified_native_model_speedups":0,
        "all_candidates_remain_eligible_for_bounded_tests":True,
        "current_acceleration_stage2_gate":"AC-D1_GO_CPU_MICROKERNEL_NOT_MODEL",
        "native_pilot_priority_ids":["AC-D1","AC-D5","AC-D3"],
        "separate_native_intelligence_gates_count_as_acceleration_wins":False,
        "negative_evidence_and_first_use_guards_preserved":True,
        "wingless_or_ygg_original_models_changed":False,
        "forge_controller_queue_changed":False,
        "scientific_first_use":False,
        "scientific_admission":False,
        "rows":rows,
    }

if __name__=="__main__":
    if len(sys.argv)>3 or (len(sys.argv)>1 and sys.argv[1]!="--full"):
        raise SystemExit("usage: acc34_scoreboard.py [--full] [output.json]")
    audit="--full" in sys.argv
    args=[s for s in sys.argv[1:] if s!="--full"]
    report=scoreboard(audit)
    payload=json.dumps(report,indent=2,sort_keys=True)+"\n"
    if args:
        Path(args[0]).write_text(payload,encoding="utf-8")
    else:
        print(payload,end="")
