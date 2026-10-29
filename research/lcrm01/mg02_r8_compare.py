#!/usr/bin/env python3
"""Fail-closed comparison of two independent MG02 original MiniGrid processes."""
import argparse
import json
from pathlib import Path
from k4r_minigrid_source import canon,sha
from mg02_r8_paired_live import SCHEMA,PASS

def check(r):
    if (r.get("schema")!=SCHEMA or r.get("classification")!=PASS
        or r.get("scientific_first_use") is not False
        or r.get("accepted_model_promoted") is not False
        or r.get("FORGE_controller_modified") is not False
        or r.get("r12_currently_connected") is not False
        or r.get("authentic_original_source") is not True
        or r.get("original_live_episode_count")!=8
        or r.get("both_native_fit_feedback_count",0)<500
        or r.get("same_six_field_public_interface") is not True):
        raise ValueError("MG02_ORIGINAL_MODEL_OR_WORLD_CONTRACT_NOT_VERIFIED")
    evidence=r.get("canonical_original_evidence")
    if not isinstance(evidence,dict):
        raise ValueError("MG02_CANONICAL_SOURCE_MISSING")
    if sha(canon(evidence).encode())!=r.get("canonical_original_trace_sha256"):
        raise ValueError("MG02_CANONICAL_ORIGINAL_TRACE_INVALID")
    eps=evidence.get("original_environment_live_pairings")
    if type(eps) is not list or len(eps)!=8:
        raise ValueError("MG02_ORIGINAL_PAIRINGS_MISSING")
    for family in ("empty","fourrooms"):
        for seed in (9200,9201):
            pair=[x for x in eps if x["family"]==family and x["seed_evaluator_only"]==seed]
            if len(pair)!=2 or {x["native_model"] for x in pair}!={"wingless_go_r8","yggdrasil_r1_local_cells"}:
                raise ValueError("MG02_INDEPENDENT_SAME_SEED_PAIR_MISSING")
            if (pair[0]["initial_full_original_public_image_sha256"]!=
                    pair[1]["initial_full_original_public_image_sha256"] or
                pair[0]["initial_exact_six_public_fields"]!=
                    pair[1]["initial_exact_six_public_fields"]):
                raise ValueError("MG02_EQUAL_PUBLIC_START_MISMATCH")
            for e in pair:
                actual=e["actual_selected_public_consequences"]
                if not actual or len(actual)!=e["true_original_step_count"]:
                    raise ValueError("MG02_FAKE_OR_MISSING_REAL_CONSEQUENCE")
                for i,s in enumerate(actual):
                    if (s["ordinal"]!=i+1 or s["local_native_online_feedback_count"]!=i+1
                        or s["actual_selected_action"] not in (0,1,2)
                        or not isinstance(s["actual_original_reward"],float)
                        or type(s["terminated"]) is not bool
                        or type(s["truncated"]) is not bool
                        or set(s["before_six_public_fields"])!=set(e["initial_exact_six_public_fields"])
                        or set(s["after_six_public_fields"])!=set(e["initial_exact_six_public_fields"])):
                        raise ValueError("MG02_SOURCE_PUBLIC_SELECTED_REWARD_OR_FEEDBACK_DRIFT")
    if evidence.get("r12_original_sixfield_contract_compatible") is not False:
        raise ValueError("MG02_R12_FALSE_COMPATIBILITY_CLAIM")
    return evidence

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--first",required=True,type=Path)
    a.add_argument("--second",required=True,type=Path)
    a.add_argument("--output",required=True,type=Path)
    args=a.parse_args()
    x=json.loads(args.first.read_text(encoding="utf-8"))
    y=json.loads(args.second.read_text(encoding="utf-8"))
    one=check(x)
    two=check(y)
    if one!=two or x["canonical_original_trace_sha256"]!=y["canonical_original_trace_sha256"]:
        raise ValueError("MG02_INDEPENDENT_PROCESS_REPRODUCTION_FAILED")
    result={"schema":"itd02.mg02.two-independent-original-source-process-custody.v1",
            "classification":PASS,
            "independent_full_source_processes":2,
            "canonical_source_and_public_selected_trace_equal":True,
            "canonical_original_public_trace_sha256":x["canonical_original_trace_sha256"],
            "wingless_go_r8_connected":True,
            "yggdrasil_r1_connected":True,
            "yggdrasil_r12_not_connected":True,
            "scientific_first_use":False,
            "model_promoted":False}
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("MG02_TWO_PROCESS_NATIVE_CLASSIFICATION",result["classification"])
    print("MG02_TWO_PROCESS_SOURCE_SHA",result["canonical_original_public_trace_sha256"])
    return 0

if __name__=="__main__":
    raise SystemExit(main())
