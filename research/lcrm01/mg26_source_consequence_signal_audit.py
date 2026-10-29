#!/usr/bin/env python3
"""MG26 read-only nonterminal public-consequence signal sufficiency audit.

Recompute from strictly EARLIER original source-selected events, never future
outcomes. Offline proposed actions do not actuate a world or predict outcomes.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
from pathlib import Path

from mg25_original_policy_activation_audit import (
    get_source, inspect as attest_mg25, digest, canon, FAMILIES, SEEDS
)

HERE=Path(__file__).resolve().parent
PREREG=HERE/"mg26_source_public_consequence_signal_prereg.json"
ROLES=("wingless_MG23","yggdrasil_MG23","conventional_full")
SOURCE_SHA="e2dda4721d6d96ffd083faac5960013380b29c3325f560defa989c4eef0852a9"

def freeze():
    p=json.loads(PREREG.read_text(encoding="utf-8"))
    spec=p["policy_proposal_protocol"]
    if (p["schema"]!="itd02.mg26.exposed-original-source-nonterminal-consequence-signal-audit.v1" or
        p["phase"]!="FROZEN_RETROSPECTIVE_ANALYSIS_BEFORE_EXECUTABLE_NOT_SCIENTIFIC_FIRST_USE" or
        p["pinned"]["MG24_original_source_sha"]!=SOURCE_SHA or
        p["pinned"]["MG25_head"]!="af216e646fb30d4c233e2a7f47184bf7282df22d" or
        spec["actors"]!=list(ROLES) or
        spec["lookback_steps"]!=32 or
        spec["minimum_original_selected_action_samples_for_positive_proposal"]!=1 or
        not p["eligibility"]["original_two_processes_equal"] or
        p["eligibility"]["source_actions"]!=9186 or
        not all(p["prohibitions"].values())):
        raise ValueError("MG26_PROSPECTIVE_ANALYSIS_NOT_FROZEN")
    return p

def context(before):
    return digest({"mission":before["mission"],"direction":before["direction"],
                   "front":before["image"][3][5]})

def propose(before,actual,history):
    """Use strictly previous source-selected observations, not the current result."""
    key=context(before)
    scores={}
    support=0
    for action in range(7):
        seen=[(event["before"],event["after"]) for event in history
              if context(event["before"])==key and event["action"]==action]
        changed=[digest(a) for b,a in seen if digest(a)!=digest(b)]
        if seen:
            support+=1
            # Changed successor diversity: no-op never receives positive evidence.
            scores[action]=4*len(set(changed))+len(changed)-len(seen)
    if not scores:return actual,False,0,False
    high=max(scores.values())
    if high<=0:return actual,False,support,False
    # Exact parent action wins ties, preserving no invented tie-breaking plan.
    best=actual if scores.get(actual)==high else min(a for a,v in scores.items() if v==high)
    return best,True,support,best!=actual

def inspect(s):
    attest_mg25(s)
    rows=s["full_original_selected_source_72_episodes"]
    lookup={(row["family"],row["dev_seed_exposed"],row["role"]):row for row in rows}
    results={}
    per_family={}
    for role in ROLES:
        tally=collections.Counter()
        family_rows=[]
        for family,seedpair in zip(FAMILIES,SEEDS):
            history=[]
            for seed in seedpair:
                row=lookup[(family,seed,role)]
                for event in row["selected_source_events"]:
                    before=event["before"];after=event["after"]
                    actual=event["action"]
                    predicted,has_signal,supported,diverges=propose(before,actual,history[-32:])
                    tally["selected_source_steps"]+=1
                    tally["evidence_contexts_seen"]+=int(supported>0)
                    tally["positive_nonterminal_signal_proposals"]+=int(has_signal)
                    tally["offline_evidence_backed_action_divergences"]+=int(diverges)
                    tally["prior_actions_supported_max"]=max(tally["prior_actions_supported_max"],supported)
                    tally["observed_public_changes"]+=int(digest(before)!=digest(after))
                    tally["original_goal_rewards"]+=int(event["reward"]>0 and event["terminated"])
                    tally["exact_original_target_events"]+=int(event["public_mission_target_pickup"])
                    tally["no_signal_control_proposal_equal_actual"]+=int(actual==actual)
                    if has_signal and predicted not in range(7):
                        raise ValueError("MG26_INVALID_OFFLINE_POLICY_PROPOSAL")
                    # This happens AFTER the proposal, forbidding future leakage.
                    history.append(event)
            family_rows.append({"family":family,"source_selected_events":len(history)})
        if sum(x["source_selected_events"] for x in family_rows)!=tally["selected_source_steps"]:
            raise ValueError("MG26_SOURCE_WINDOW_NOT_CONSERVED")
        results[role]=dict(tally)
        per_family[role]=family_rows
    return {"schema":"itd02.mg26.original-source-public-consequence-sufficiency.v1",
            "source_sha256":SOURCE_SHA,"read_only_original_source_episodes":72,
            "read_only_original_source_actions":9186,
            "nonterminal_signal_results":results,
            "per_role_family_source_event_counts":per_family,
            "off_policy_proposals_are_not_real_actions":True,
            "no_generalization_or_success_claim":True,
            "new_original_environment_steps":0,
            "scientific_first_use":False,
            "accepted_models_and_forge_controller_modified":False}

def execute(a,b):
    freeze()
    first=get_source(Path(a))
    second=get_source(Path(b))
    if first["source"]!=second["source"]:
        raise ValueError("MG26_SOURCE_PROCESS_MISMATCH")
    report=inspect(first["source"])
    report["canonical_sha256"]=digest(report)
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--first",type=Path)
    p.add_argument("--second",type=Path)
    p.add_argument("--output",type=Path)
    p.add_argument("--compare",nargs=2,type=Path)
    a=p.parse_args()
    if a.compare:
        r,s=[json.loads(x.read_text(encoding="utf-8")) for x in a.compare]
        if (r!=s or r["canonical_sha256"]!=digest({k:v for k,v in r.items()
                   if k!="canonical_sha256"}) or r["new_original_environment_steps"]!=0):
            raise ValueError("MG26_CROSS_PLATFORM_EXPOSED_SOURCE_DIVERGENCE")
        print("MG26_CROSS_PLATFORM_EARLY_CONSEQUENCE_SIGNAL_AUDIT_PASS_NOT_SCIENCE "+r["canonical_sha256"])
        return
    if not all((a.first,a.second,a.output)):
        p.error("need both original source process receipts")
    result=execute(a.first,a.second)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("MG26_ORIGINAL_EXPOSED_SOURCE_SIGNAL_AUDIT_PASS_NO_NEW_ACTIONS "+result["canonical_sha256"])
    print("MG26_ACTUAL_NONTERMINAL_EVIDENCE_AND_OFFLINE_PROPOSALS "+
          json.dumps(result["nonterminal_signal_results"],sort_keys=True,separators=(",",":")))
if __name__=="__main__":main()
