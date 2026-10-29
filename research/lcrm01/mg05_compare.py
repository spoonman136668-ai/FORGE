#!/usr/bin/env python3
"""MG05 source-only real selected DoorKey evidence comparison, no science."""
import argparse
import json
from pathlib import Path
from k4r_minigrid_source import canon,sha
from mg05_native_only_original_world import SCHEMA,PASS,NEG,ROLES

def verify(o):
    if (o.get("schema")!=SCHEMA or o.get("classification") not in (PASS,NEG)
        or o.get("scientific_first_use") is not False
        or o.get("accepted_model_promoted") is not False
        or o.get("FORGE_controller_modified") is not False
        or o.get("original_wingless_R8_modified") is not False
        or o.get("original_yggdrasil_R12_modified") is not False
        or o.get("same_1664_source_fit")!=1664):
        raise ValueError("MG05_FALSE_OR_MISSING_NATIVE_AUTHORITY")
    e=o.get("canonical_evidence")
    if not isinstance(e,dict) or sha(canon(e).encode())!=o.get("canonical_evidence_sha256"):
        raise ValueError("MG05_TAMPERED_ORIGINAL_SELECTED_EVIDENCE")
    if not e.get("no_external_live_collector") or not e.get("native_wingless_is_new_DK8U_not_R8"):
        raise ValueError("MG05_FALSE_SOURCE_NATIVE_IDENTITY")
    records=e["original_source_action_records"]
    if len(records)!=9:raise ValueError("MG05_EXPECTED_NINE_INDEPENDENT_ORIGINAL_EPISODES")
    summ=o["source_origin_summary"]
    for seed in (65301,65303,65307):
        trio=[r for r in records if r["seed_evaluator_only"]==seed]
        if len(trio)!=3 or {r["role"] for r in trio}!=set(ROLES):
            raise ValueError("MG05_MISSING_NATIVE_OR_CONVENTIONAL_ARM")
        if len({r["start_exact_public_sha"] for r in trio})!=1:
            raise ValueError("MG05_UNEQUAL_PUBLIC_START")
        for r in trio:
            events=r["real_original_selected_events"]
            if (r["external_collector_actions"]!=0
                or r["original_source_steps"]!=len(events)
                or r["native_or_control_actions"]!=len(events)
                or r["native_abstentions"] not in (0,1)):
                raise ValueError("MG05_EXTERNAL_RESCUE_OR_ACTION_COUNT")
            role=r["role"]
            origin={"wingless_go_dk8u":"NATIVE_WINGLESS_GO_DK8U",
                    "yggdrasil_r13_on_r11":"NATIVE_YGGDRASIL_LOCAL_R13",
                    "uniform_seven_action_random":"EXPLICIT_CONVENTIONAL_RANDOM_CONTROL"}[role]
            for i,s in enumerate(events):
                if (s["ordinal"]!=i+1 or s["selected_feedback_delta"]!=i+1
                    or type(s["actual_source_action"])is not int
                    or s["actual_source_action"] not in range(7)
                    or s["model_selected_action"]!=s["actual_source_action"]
                    or s["action_origin"]!=origin
                    or type(s["actual_original_reward"])is not float
                    or type(s["terminated"])is not bool or type(s["truncated"])is not bool
                    or set(s["public_before"])!={"image","direction","mission"}
                    or set(s["public_after"])!={"image","direction","mission"}):
                    raise ValueError("MG05_FALSE_SELECTED_PUBLIC_NATIVE_FEEDBACK")
            if events and (r["native_abstentions"]!=0 and events[-1]["terminated"] or
                r["native_abstentions"]!=0 and events[-1]["truncated"]):
                raise ValueError("MG05_ABSTENTION_AFTER_TERMINAL")
    for role in ROLES:
        rows=[x for x in records if x["role"]==role]
        if summ[role]["episodes"]!=3 or summ[role]["external_collector_actions"]!=0:
            raise ValueError("MG05_FALSE_ROLE_SOURCE_SUMMARY")
        for field,recordfield in (("native_or_control_actions","native_or_control_actions"),
                                  ("original_source_steps","original_source_steps"),
                                  ("native_abstentions","native_abstentions"),
                                  ("source_goal_rewards","source_goal_rewards")):
            if summ[role][field]!=sum(x[recordfield] for x in rows):
                raise ValueError("MG05_FALSE_EVENT_AGGREGATION_"+field)
    return e

def main():
    a=argparse.ArgumentParser()
    for arg in ("first","second","output"):a.add_argument("--"+arg,required=True,type=Path)
    opts=a.parse_args()
    x=json.loads(opts.first.read_text(encoding="utf-8"))
    y=json.loads(opts.second.read_text(encoding="utf-8"))
    a1=verify(x);a2=verify(y)
    if a1!=a2 or x["canonical_evidence_sha256"]!=y["canonical_evidence_sha256"] or x["classification"]!=y["classification"]:
        raise ValueError("MG05_TWO_FRESH_PROCESSES_DISAGREE")
    out={"schema":"itd02.mg05.source-replay-verified.v1",
      "classification":x["classification"],
      "two_independent_fresh_source_processes":True,
      "selected_original_canonical_sha256":x["canonical_evidence_sha256"],
      "native_only_without_external_live_fallback":True,
      "native_source_origin_summary":x["source_origin_summary"],
      "scientific_first_use":False}
    opts.output.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print("MG05_TWO_PROCESS_RESULT",out["classification"])
    print("MG05_TWO_PROCESS_SOURCE_SHA",out["selected_original_canonical_sha256"])
    print("MG05_NATIVE_SOURCE_RESULTS",json.dumps(out["native_source_origin_summary"],sort_keys=True))

if __name__=="__main__":
    main()
