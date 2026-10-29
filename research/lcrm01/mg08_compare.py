#!/usr/bin/env python3
"""MG08 two independent real-source process public key+door diagnostic witness."""
import argparse,json
from pathlib import Path
from k4r_minigrid_source import canon,sha
from mg08_key_door_alignment import (
 SCHEMA,BLOCKED,ABSENT,MISSING,OBSERVED,NATIVE,public_diagnostic,parent
)
VALID=(ABSENT,MISSING,OBSERVED)

def verify(r):
    if (r.get("schema")!=SCHEMA or r.get("classification") not in VALID
        or r.get("scientific_first_use") is not False
        or r.get("controller_modified") is not False
        or r.get("native_model_promoted") is not False
        or r.get("original_source_actors_unchanged") is not True
        or r.get("actual_source_episode_count")!=15
        or r.get("same_source_selected_fit_per_actor")!=1664
        or r.get("external_live_actions")!=0):
        raise ValueError("MG08_UNTRUSTED_SOURCE_OR_DECLARED_AUTHORITY")
    evidence=r.get("canonical_public_diagnostic_evidence")
    if (type(evidence)is not dict or
        sha(canon(evidence).encode())!=r.get("canonical_source_diagnostic_sha256")
        or evidence.get("preregistered_before_new_source_execution") is not True
        or evidence.get("no_native_source_or_scoring_rule_change") is not True
        or evidence.get("no_hidden_world_state_or_external_navigation") is not True):
        raise ValueError("MG08_NOT_PINNED_SOURCE_ONLY_EVIDENCE")
    records=evidence["real_original_public_selected_actions_and_outcomes"]
    diag=evidence["public_source_alignment_per_episode"]
    if len(records)!=15 or len(diag)!=15:
        raise ValueError("MG08_INCOMPLETE_ORIGINAL_SOURCE_SELECTED_EVENTS")
    for seed in (68301,68303,68307):
        selected=[x for x in records if x["evaluator_seed_only"]==seed]
        if len(selected)!=5 or {x["role"] for x in selected}!=set(parent.ROLES):
            raise ValueError("MG08_MISSING_ONE_ORIGINAL_ROLE")
        if len({x["original_public_start_sha256"] for x in selected})!=1:
            raise ValueError("MG08_ORIGINAL_SOURCE_PUBLIC_RESET_NOT_EQUAL")
    for original,e in zip(records,diag):
        if e!=public_diagnostic(original):
            raise ValueError("MG08_FALSE_PUBLIC_SOURCE_EFFECT_RECOUNT")
    totals=evidence["public_source_alignment_per_actor"]
    for role in parent.ROLES:
        entries=[x for x in diag if x["role"]==role]
        if len(entries)!=3 or totals[role]["actual_original_seed_episodes"]!=3:
            raise ValueError("MG08_ROLE_NOT_COMPLETE")
        for key,value in totals[role].items():
            if key!="actual_original_seed_episodes" and value!=sum(
                x["source_only_counters"][key] for x in entries
            ):
                raise ValueError("MG08_ORIGINAL_PUBLIC_SUMMARY_MISMATCH")
    both=all(totals[r]["real_original_visible_door_state_changes"]>=1 for r in NATIVE)
    seen=any(totals[r]["key_held_and_door_directly_in_front_frames"]>=1 for r in NATIVE)
    status=OBSERVED if both else MISSING if seen else ABSENT
    if r["classification"]!=status:
        raise ValueError("MG08_FROZEN_DIAGNOSTIC_OUTCOME_FALSIFIED")
    return evidence

def main():
    parser=argparse.ArgumentParser()
    for n in ("first","second","output"):
        parser.add_argument("--"+n,type=Path,required=True)
    x=parser.parse_args()
    a=json.loads(x.first.read_text(encoding="utf-8"))
    b=json.loads(x.second.read_text(encoding="utf-8"))
    ea=verify(a);eb=verify(b)
    if (ea!=eb or a["classification"]!=b["classification"]
        or a["canonical_source_diagnostic_sha256"]!=b["canonical_source_diagnostic_sha256"]):
        raise ValueError("MG08_INDEPENDENT_AUTHENTIC_REPLAY_DIVERGED")
    out={"schema":"itd02.mg08.original-public-key-door-two-process.v1",
      "classification":a["classification"],
      "independent_original_source_processes":2,
      "real_original_public_source_sha256":a["canonical_source_diagnostic_sha256"],
      "per_role_public_key_door_results":ea["public_source_alignment_per_actor"],
      "zero_external_source_actions":True,
      "scientific_first_use":False}
    x.output.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print("MG08_TWO_PROCESS",out["classification"])
    print("MG08_TWO_PROCESS_SHA",out["real_original_public_source_sha256"])
    print("MG08_VERIFIED_ACTOR_DIAGNOSTIC",json.dumps(out["per_role_public_key_door_results"],sort_keys=True))
if __name__=="__main__":main()
