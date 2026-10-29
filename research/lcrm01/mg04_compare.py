#!/usr/bin/env python3
"""Compare two independent real original DoorKey MG04 source process receipts."""
import argparse,json
from pathlib import Path
from k4r_minigrid_source import canon,sha
from mg04_public_effect_native_agency import SCHEMA,POS,NEG,ROLES

def verify(d):
    if (d.get("schema")!=SCHEMA or d.get("classification") not in (POS,NEG)
        or d.get("scientific_first_use") is not False
        or d.get("native_model_accepted") is not False
        or d.get("controller_mutated") is not False
        or d.get("original_wingless_R8_modified") is not False
        or d.get("original_yggdrasil_R12_modified") is not False
        or d.get("same_public_and_budget_provenance") is not True
        or d.get("same_1664_fit_samples_per_arm")!=1664):
        raise ValueError("MG04_NO_AUTHENTIC_EQUAL_PUBLIC_AUTHORITY")
    evidence=d.get("canonical_evidence")
    if not isinstance(evidence,dict) or sha(canon(evidence).encode())!=d.get("canonical_evidence_sha256"):
        raise ValueError("MG04_CANONICAL_REAL_EVENT_DIGEST_MISMATCH")
    events=evidence["original_source_native_public_action_and_effect_records"]
    if len(events)!=9:raise ValueError("MG04_EXPECTED_NINE_ORIGINAL_WORLD_RUNS")
    summary=d["source_origin_summary"]
    for seed in (64301,64303,64307):
        trio=[e for e in events if e["seed_evaluator_only"]==seed]
        if {e["role"] for e in trio}!=set(ROLES) or len(trio)!=3:
            raise ValueError("MG04_ACTOR_CUSTODY_MISSING")
        if len({e["original_start_public_sha256"] for e in trio})!=1:
            raise ValueError("MG04_INEQUIVALENT_PUBLIC_RESET")
        for e in trio:
            steps=e["real_original_selected_events"]
            if (not steps or len(steps)!=e["actual_original_env_steps"]
                or len(steps)!=e["native_or_conventional_actions"]+e["abstentions"]
                or e["abstentions"]!=e["external_public_collector_actions"]):
                raise ValueError("MG04_UNDECLARED_NATIVE_VS_EXTERNAL_ACTOR")
            for i,s in enumerate(steps):
                if (s["step"]!=i+1 or s["native_or_control_selected_feedback_count"]!=i+1
                    or s["real_original_action"] not in range(7)
                    or type(s["real_original_action"]) is not int
                    or type(s["actual_selected_reward"]) is not float
                    or type(s["terminated"]) is not bool or type(s["truncated"]) is not bool
                    or set(s["public_before"])!={"image","direction","mission"}
                    or set(s["public_after"])!={"image","direction","mission"}
                    or s["objective_explicit_external"] not in
                       ("carrying_changed","visible_door_state_changed")):
                    raise ValueError("MG04_FALSE_AUTHENTIC_SOURCE_CONSEQUENCE")
                if s["model_proposal"] is None and not s["source_of_executed_action"].startswith("public_external"):
                    raise ValueError("MG04_ABSTENTION_IMPERSONATED_NATIVE")
                if s["model_proposal"] is not None and s["real_original_action"]!=s["model_proposal"]:
                    raise ValueError("MG04_NATIVE_SELECTED_ACTION_REPLACED")
    for role in ROLES:
        if summary[role]["episodes"]!=3 or summary[role]["actual_original_source_actions"]<3:
            raise ValueError("MG04_CONVENTIONAL_OR_NATIVE_ORIGINAL_SOURCE_MISSING")
    return evidence

def main():
    p=argparse.ArgumentParser()
    for n in ("first","second","output"):p.add_argument("--"+n,type=Path,required=True)
    x=p.parse_args()
    a=json.loads(x.first.read_text());b=json.loads(x.second.read_text())
    c=verify(a);e=verify(b)
    if c!=e or a["classification"]!=b["classification"] or a["canonical_evidence_sha256"]!=b["canonical_evidence_sha256"]:
        raise ValueError("MG04_INDEPENDENT_REPRODUCTION_FALSE")
    result={"classification":a["classification"],"canonical_sha256":a["canonical_evidence_sha256"],
        "independent_processes":2,"original_farama_selected_public_real":True,
        "actual_model_decisions":a["source_origin_summary"],"scientific_first_use":False}
    x.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("MG04_TWO_PROCESS",result["classification"])
    print("MG04_TWO_PROCESS_CANONICAL_SHA",result["canonical_sha256"])
    print("MG04_TWO_PROCESS_NATIVE_ACTIONS",json.dumps(result["actual_model_decisions"],sort_keys=True))
if __name__=="__main__":main()
