#!/usr/bin/env python3
"""Cross-process equality only of original source/public evidence, not timings."""
import argparse
import hashlib
import json
from pathlib import Path
from mg01_paired_live_minigrid import SCHEMA,NATIVE_TYPES,FAMILIES,SEEDS
from k4r_minigrid_source import canon,sha

PASS="MG01_TWO_INDEPENDENT_NATIVES_LIVE_ORIGINAL_MINIGRID_CONNECTED__NO_SCIENCE"

def compare(a,b):
    for name,r in (("A",a),("B",b)):
        if (r.get("schema")!=SCHEMA or r.get("classification")!=PASS
            or r.get("scientific_first_use") is not False
            or r.get("scientific_accepted") is not False
            or r.get("native_originals_untouched") is not True
            or r.get("FORGE_controller_mutated") is not False
            or r.get("one_authentic_source_both_natives") is not True
            or r.get("original_Farama_environment_not_emulated") is not True
            or r.get("identical_sixfield_semantics_for_both_actors") is not True
            or r.get("identical_initial_public_observation_per_pair") is not True
            or r.get("paired_episode_count")!=8
            or r.get("two_independent_native_fit_feedback_counts",0)<500):
            raise ValueError("MG01_PROCESS_NOT_ORIGINAL_NATIVE_EVIDENCE_"+name)
        canonical=r.get("canonical_full_science")
        if (type(canonical) is not dict or
            len(canonical.get("paired_live_original_world_episodes",[]))!=8):
            raise ValueError("MG01_ORIGINAL_FAMILY_EVIDENCE_MISSING_"+name)
        if sha(canon(canonical).encode())!=r.get("canonical_public_episode_and_model_custody_sha256"):
            raise ValueError("MG01_PUBLIC_CUSTODY_HASH_MISMATCH_"+name)
        episodes=canonical["paired_live_original_world_episodes"]
        for family in FAMILIES:
            for seed in SEEDS:
                pair=[x for x in episodes if x["family"]==family and
                      x["source_seed_evaluator_only"]==seed]
                if len(pair)!=2 or set(e["native"] for e in pair)!=set(NATIVE_TYPES):
                    raise ValueError("MG01_MISSING_EQUAL_SEEDED_NATIVE_PAIR_"+name)
                if (pair[0]["public_start_image_sha256"]!=pair[1]["public_start_image_sha256"] or
                    pair[0]["public_start_sixfield"]!=pair[1]["public_start_sixfield"]):
                    raise ValueError("MG01_SAME_WORLD_START_NOT_EQUAL_"+name)
                for e in pair:
                    trace=e["public_actual_action_consequence_trace"]
                    if (len(trace)==0 or
                        len(trace)!=e["real_original_env_step_calls"] or
                        len(trace)!=e["live_native_update_count"] or
                        any(row["selected_action"] not in (0,1,2) for row in trace) or
                        any(row["native_update_counter"]!=r["two_independent_native_fit_feedback_counts"]+i+1
                            for i,row in enumerate(trace))):
                        raise ValueError("MG01_NONCAUSAL_OR_LOST_REAL_FEEDBACK_"+name)
    identical=a["canonical_full_science"]==b["canonical_full_science"]
    sha_equal=a["canonical_public_episode_and_model_custody_sha256"]==b["canonical_public_episode_and_model_custody_sha256"]
    return {"schema":"itd02.mg01.two-independent-process-original-minigrid-custody.v1",
        "classification":PASS if identical and sha_equal else "MG01_ORIGINAL_MINIGRID_NATIVE_BOUNDARY_BLOCKED__NO_SCIENCE",
        "independent_host_runs":2,"original_world_source_sha":a["authentic_source_commit"],
        "same_source_and_native_policy_code":a["canonical_full_science"]["native_source_commits"],
        "canonical_source_and_live_trace_agree":identical,
        "canonical_sha_agrees":sha_equal,
        "canonical_original_live_trace_sha256":a["canonical_public_episode_and_model_custody_sha256"],
        "scientific_first_use":False,"scientific_accepted":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--a",type=Path,required=True)
    p.add_argument("--b",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        raise ValueError("MG01_COMPARISON_OUTPUT_MUST_BE_NEW")
    a=json.loads(args.a.read_text())
    b=json.loads(args.b.read_text())
    outcome=compare(a,b)
    args.output.write_text(json.dumps(outcome,indent=2,sort_keys=True)+"\n")
    print("MG01_TWO_PROCESS_CLASSIFICATION",outcome["classification"])
    print("MG01_IDENTICAL_AUTHENTIC_TRACES",outcome["canonical_source_and_live_trace_agree"])
    print("MG01_SHA",outcome["canonical_original_live_trace_sha256"])
    return 0 if outcome["canonical_sha_agrees"] and outcome["canonical_source_and_live_trace_agree"] else 1

if __name__=="__main__":
    raise SystemExit(main())
