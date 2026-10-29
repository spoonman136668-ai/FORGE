#!/usr/bin/env python3
"""MG03 separate-process exact authentic public source comparison, no science."""
import argparse,json
from pathlib import Path
from k4r_minigrid_source import canon,sha
from mg03_equal_public_doorkey_live import SCHEMA,PASS

def verify(result):
    if (result.get("schema")!=SCHEMA or result.get("classification")!=PASS
        or result.get("scientific_first_use") is not False
        or result.get("scientific_accepted") is not False
        or result.get("accepted_native_model_modified") is not False
        or result.get("wingless_native_R8_upgraded") is not False
        or result.get("FORGE_controller_modified") is not False
        or result.get("authentic_original_env_step") is not True
        or result.get("same_exact_public_input") is not True
        or result.get("equal_native_seven_action_legal_set") is not True
        or result.get("original_FIT_identical_feedback_per_model")!=1664
        or result.get("paired_original_live_episodes")!=4):
        raise ValueError("MG03_SOURCE_OR_NATIVE_ACCEPTANCE_CLAIM_INVALID")
    canonical=result["canonical_original_source_records"]
    if sha(canon(canonical).encode())!=result["canonical_original_source_trace_sha"]:
        raise ValueError("MG03_INVALID_CANONICAL_EXACT_SOURCE_SHA")
    records=canonical.get("original_doorkey_live_records")
    if (not isinstance(records,list) or len(records)!=4 or
        not canonical["different_native_architectures_and_no_shared_memory"] or
        not canonical["wingless_go_dk7_is_not_original_r8"] or
        not canonical["source_only_external_abstention_collector"]):
        raise ValueError("MG03_NATIVE_SOURCE_OR_HONEST_FALLBACK_MISSING")
    for seed in (63301,63303):
        pair=[x for x in records if x["seed_evaluator_only"]==seed]
        if len(pair)!=2 or {x["native"] for x in pair}!={"wingless_native_go_dk7","yggdrasil_native_r12_on_r11"}:
            raise ValueError("MG03_PAIRED_SOURCE_EPISODES_NOT_EQUAL")
        if pair[0]["exact_identical_start_public_sha"]!=pair[1]["exact_identical_start_public_sha"]:
            raise ValueError("MG03_UNEQUAL_SOURCE_PUBLIC_START")
        if pair[0]["selected_original_public_events"][0]["public_before"]!=pair[1]["selected_original_public_events"][0]["public_before"]:
            raise ValueError("MG03_PUBLIC_START_ACTOR_PREFERENCE")
        for episode in pair:
            rows=episode["selected_original_public_events"]
            if (not rows or len(rows)!=episode["actual_original_steps"] or
                episode["native_selected_proposals"]+episode["native_abstentions"]!=len(rows) or
                episode["external_public_collector_fallbacks"]!=episode["native_abstentions"]):
                raise ValueError("MG03_NATIVE_PROPOSAL_OR_SOURCE_COUNT_DRIFT")
            for j,row in enumerate(rows):
                if (row["ordinal"]!=j+1 or row["native_selected_feedback_count"]!=j+1
                    or type(row["actual_seven_action"]) is not int
                    or row["actual_seven_action"] not in range(7)
                    or not isinstance(row["original_selected_reward"],float)
                    or type(row["terminated"]) is not bool
                    or type(row["truncated"]) is not bool
                    or set(row["public_before"])!={"image","direction","mission"}
                    or set(row["public_after"])!={"image","direction","mission"}):
                    raise ValueError("MG03_MISSING_AUTHENTIC_PUBLIC_ORIGINAL_STEP")
                if row["native_proposed_action"] is None and not row["action_origin"].startswith("declared_common"):
                    raise ValueError("MG03_SILENT_EXTERNAL_ACTION_IMPERSONATES_NATIVE")
                if row["native_proposed_action"] is not None and row["actual_seven_action"]!=row["native_proposed_action"]:
                    raise ValueError("MG03_NATIVE_ACTION_CHANGED_AFTER_PROPOSAL")
    return canonical

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--a",type=Path,required=True)
    a.add_argument("--b",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    p=a.parse_args()
    x=json.loads(p.a.read_text());y=json.loads(p.b.read_text())
    c1=verify(x);c2=verify(y)
    if c1!=c2 or x["canonical_original_source_trace_sha"]!=y["canonical_original_source_trace_sha"]:
        raise ValueError("MG03_INDEPENDENT_PROCESSES_NOT_IDENTICAL")
    summary={"schema":"itd02.mg03.two-independent-original-doorkey-source-processes.v1",
        "classification":PASS,"independent_runner_processes":2,
        "same_original_public_reward_trace":True,
        "canonical_sha256":x["canonical_original_source_trace_sha"],
        "wingless_new_go_seven_action":True,
        "wingless_R8_upgraded":False,
        "yggdrasil_R12_original_unchanged":True,
        "scientific_first_use":False}
    p.output.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    print("MG03_VERIFIED_TWO_PROCESS_CLASSIFICATION",summary["classification"])
    print("MG03_VERIFIED_SHA",summary["canonical_sha256"])
if __name__=="__main__":
    main()
