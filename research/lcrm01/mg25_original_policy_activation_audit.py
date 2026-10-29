#!/usr/bin/env python3
"""MG25 source-authenticated falsification of MG23 policy activation.

Retrospective on exposed MG24 DEV, never new training or original environment
actions. Identical original actions and public consequences can demonstrate no
policy effect on this cohort, but not prove general impossibility.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, statistics
from pathlib import Path

HERE=Path(__file__).resolve().parent
PREREG=HERE/"mg25_policy_activation_prereg.json"
SCHEMA="itd02.mg25.original-nine-arm-selected-policy-activation-falsification.v1"
SOURCE_SHA="e2dda4721d6d96ffd083faac5960013380b29c3325f560defa989c4eef0852a9"
FAMILIES=("MiniGrid-DoorKey-6x6-v0","MiniGrid-UnlockPickup-v0",
          "MiniGrid-BlockedUnlockPickup-v0","MiniGrid-KeyCorridorS3R1-v0")
SEEDS=((948101,948103),(948201,948203),(948301,948303),(948401,948403))
ROLES=("wingless_MG23","wingless_MG19","yggdrasil_MG23","yggdrasil_MG19",
       "conventional_full","conventional_no_target","conventional_no_delayed",
       "conventional_no_both","unassisted_original_random")
PAIRS=(("wingless_MG23","wingless_MG19"),
       ("yggdrasil_MG23","yggdrasil_MG19"),
       ("conventional_full","conventional_no_target"),
       ("conventional_full","conventional_no_delayed"),
       ("conventional_full","conventional_no_both"))

def canon(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("ascii")
def digest(x):
    return hashlib.sha256(canon(x)).hexdigest()

def freeze():
    p=json.loads(PREREG.read_text(encoding="utf-8"))
    source=p["source"]
    if (p.get("schema")!=SCHEMA or
        p["phase"]!="RETROSPECTIVE_EXPOSED_DEV_DIAGNOSTIC_NOT_SCIENTIFIC_FIRST_USE" or
        source["source_sha"]!=SOURCE_SHA or source["original_actions"]!=9186 or
        source["episodes"]!=72 or source["artifact_id"]!=12897771185 or
        p["seed_cohort"]["families"]!=list(FAMILIES) or
        p["seed_cohort"]["seeds"]!=[list(x) for x in SEEDS] or
        p["roles"]!=list(ROLES) or
        p["expected_classification"]!="TO_BE_MEASURED_NOT_PRESUPPOSED" or
        not all(p["audits"].values()) or not all(p["prohibited"].values())):
        raise ValueError("MG25_FROZEN_RETROSPECTIVE_METHOD_DRIFT")
    return p

def verify_public(frame,mission):
    if type(frame)is not dict or set(frame)!={"image","direction","mission"} or frame["mission"]!=mission:
        raise ValueError("MG25_NOT_AUTHENTIC_FULL_PUBLIC_MISSION")
    if type(frame["direction"])is not int or frame["direction"] not in (0,1,2,3):
        raise ValueError("MG25_NONORIGINAL_HEADING")
    pic=frame["image"]
    if (type(pic)is not list or len(pic)!=7 or
        any(type(row)is not list or len(row)!=7 or
            any(type(cell)is not list or len(cell)!=3 or
                any(type(x)is not int or not 0<=x<=255 for x in cell)
                for cell in row) for row in pic)):
        raise ValueError("MG25_NONORIGINAL_PUBLIC_PIXELS")

def get_source(path):
    r=json.loads(path.read_text(encoding="utf-8"))
    if (r.get("schema")!="itd02.mg24.real-original-nine-arm-selected-source-development.v1"
        or r.get("canonical_source_sha256")!=SOURCE_SHA or
        type(r.get("source")) is not dict or digest(r["source"])!=SOURCE_SHA):
        raise ValueError("MG25_ORIGINAL_COMPLETE_9_ARM_SOURCE_DIGEST_MISMATCH")
    s=r["source"]
    if (s["schema"]!="itd02.mg24.real-original-nine-arm-selected-source-development.v1" or
        s["classification"]!="EXPOSED_ORIGINAL_DEV_NOT_SEALED_NOT_SCIENCE" or
        s["pinned_original_farama"]!="7f5853792ea7f04f75614661006d87fcf949f26d" or
        s["external_source_actions"]!=0 or
        s["sealed_first_use"] is not False or
        s["new_source_development_actions"]!=9186 or
        s["accepted_native_models_changed"] is not False or
        s["forge_original_controller_changed"] is not False):
        raise ValueError("MG25_NOT_REAL_ORIGINAL_DEV_OR_CONTROLLER_BOUNDARY")
    return r

def inspect(source):
    s=source["source"]; records=s["full_original_selected_source_72_episodes"]
    if type(records)is not list or len(records)!=72:
        raise ValueError("MG25_MISSING_ORIGINAL_72_INDEPENDENT_ROLE_EPISODES")
    indexed={}
    total=0
    policy=collections.defaultdict(collections.Counter)
    metrics={}
    timing={}
    for row in records:
        fam,seed,role=row["family"],row["dev_seed_exposed"],row["role"]
        if (fam not in FAMILIES or seed not in SEEDS[FAMILIES.index(fam)] or
            role not in ROLES or (fam,seed,role) in indexed):
            raise ValueError("MG25_FALSE_OR_DUPLICATE_ORIGINAL_EXPOSED_COHORT")
        indexed[(fam,seed,role)]=row
        steps=row["selected_source_events"]
        if (len(steps)!=row["selected_actions"] or not 1<=len(steps)<=128 or
            row["selected_source_events_sha256"]!=digest(steps)):
            raise ValueError("MG25_INCOMPLETE_AUTHENTIC_ORIGINAL_EPISODE")
        mission=row["original_mission"]; previously=None
        target=[]; terminal=[];door=[]
        for i,event in enumerate(steps,1):
            b,a=event["before"],event["after"]
            verify_public(b,mission);verify_public(a,mission)
            if (event["index"]!=i or type(event["action"])is not int or
                event["action"] not in range(7) or type(event["reward"])is not float or
                type(event["terminated"])is not bool or type(event["truncated"])is not bool or
                type(event["policy"])is not str or not event["policy"] or
                type(event["public_mission_target_pickup"])is not bool or
                type(event["public_locked_door_open"])is not bool or
                digest(b)!=event["before_sha256"] or digest(a)!=event["after_sha256"] or
                (i==1 and row["original_start_sha256"]!=event["before_sha256"]) or
                (previously is not None and previously!=b) or
                (i<len(steps) and (event["terminated"] or event["truncated"]))):
                raise ValueError("MG25_ORIGINAL_SOURCE_SELECTED_ACTION_OR_CHAIN_INVALID")
            previously=a
            policy[role][event["policy"]]+=1
            if event["public_mission_target_pickup"]:target.append(i)
            if event["public_locked_door_open"]:door.append(i)
            if event["reward"]>0:
                if not event["terminated"]:
                    raise ValueError("MG25_FALSE_NONTERMINAL_SOURCE_POSITIVE_GOAL")
                terminal.append(i)
        if (row["original_terminal_goal_reward_count"]!=len(terminal) or
            row["selected_public_target_pickup_count"]!=len(target) or
            row["selected_public_locked_door_open_count"]!=len(door)):
            raise ValueError("MG25_SOURCE_PER_EPISODE_ORIGINAL_METRIC_DRIFT")
        if role!="unassisted_original_random":
            if (row["selected_source_samples_after"]-row["prior_selected_source_samples"]!=len(steps)
                or not isinstance(row["checkpoint_sha256"],str) or
                len(row["checkpoint_sha256"])!=64):
                raise ValueError("MG25_NATIVE_AND_CONTROL_SELECTED_SOURCE_COLD_MISSING")
        timing[(fam,seed,role)]={"target_event_ordinals":target,
                                 "positive_terminal_event_ordinals":terminal,
                                 "door_open_ordinals":door}
        metrics[(fam,seed,role)]=dict(actions=len(steps),goals=len(terminal),
                                      target_events=len(target),door_events=len(door))
        total+=len(steps)
    if total!=9186 or len(indexed)!=72:
        raise ValueError("MG25_ORIGINAL_SELECTED_SOURCE_COUNT_UNAUTHENTIC")
    for fam in FAMILIES:
        for seed in SEEDS[FAMILIES.index(fam)]:
            group=[indexed[(fam,seed,role)] for role in ROLES]
            if len({x["original_start_sha256"] for x in group})!=1:
                raise ValueError("MG25_ACTOR_ORIGINAL_SOURCE_RESET_NOT_EQUAL")
    paired=[]
    for a,b in PAIRS:
        aligned_actions=0; all_actions=0; identical_episodes=0;first_divergence=[]
        for fam in FAMILIES:
            for seed in SEEDS[FAMILIES.index(fam)]:
                x=indexed[(fam,seed,a)]["selected_source_events"]
                y=indexed[(fam,seed,b)]["selected_source_events"]
                compare=lambda event:(event["action"],event["before_sha256"],event["after_sha256"],event["reward"],event["terminated"],event["truncated"])
                aa=[compare(e) for e in x];bb=[compare(e) for e in y]
                common=sum(left==right for left,right in zip(aa,bb))
                aligned_actions+=common;all_actions+=max(len(aa),len(bb))
                equal=aa==bb;identical_episodes+=int(equal)
                diff=next((i+1 for i,(v,w) in enumerate(zip(aa,bb)) if v!=w),None)
                if diff is None and len(aa)!=len(bb):diff=min(len(aa),len(bb))+1
                first_divergence.append({"family":fam,"seed_exposed":seed,
                                         "first_divergent_source_step":diff,
                                         "identical":equal})
        paired.append({"candidate":a,"baseline":b,"equal_original_episodes":identical_episodes,
                       "original_episode_count":8,"same_original_action_effect_steps":aligned_actions,
                       "alignment_step_budget":all_actions,"first_divergences":first_divergence})
    receipt={"schema":"itd02.mg25.original-public-policy-activation-forensic.v1",
            "source_sha256":SOURCE_SHA,"original_real_selected_actions_checked":total,
            "episodes":72,"original_public_source_authentic":True,
            "paired_native_and_ablated_controls":paired,
            "policy_status_frequency":{k:dict(sorted(v.items())) for k,v in sorted(policy.items())},
            "per_original_episode_timing":[
                {"family":fam,"seed_exposed":seed,"role":role,
                 **metrics[(fam,seed,role)],**timing[(fam,seed,role)]}
                for fam in FAMILIES for seed in SEEDS[FAMILIES.index(fam)] for role in ROLES],
            "new_original_source_steps":0,
            "scientific_first_use":False,
            "native_model_or_controller_changed":False}
    zero=(all(item["equal_original_episodes"]==8 for item in paired) and
          not any("MG23" in label for role in ("wingless_MG23","yggdrasil_MG23")
                  for label in policy[role]) and
          not any("TARGET" in label or "DELAYED" in label
                  for label in policy["conventional_full"]))
    receipt["classification"]=(
       "MG25_NO_NEW_POLICY_ACTIVATION_IN_EXPOSED_MG24_SOURCE__NO_SCIENCE"
       if zero else "MG25_SOME_NEW_SELECTED_POLICY_EFFECT_IN_EXPOSED_MG24_SOURCE__NO_SCIENCE")
    receipt["native_candidate_actions_changed_on_dev"]=sum(
       x["original_episode_count"]-x["equal_original_episodes"] for x in paired[:2])
    return receipt

def main():
    parser=argparse.ArgumentParser()
    for name in ("first","second","output"):
        parser.add_argument("--"+name,type=Path,required=True)
    a=parser.parse_args();p=freeze()
    source_first=get_source(a.first);source_second=get_source(a.second)
    if source_first["source"]!=source_second["source"] or (
        source_first["canonical_source_sha256"]!=source_second["canonical_source_sha256"]):
        raise ValueError("MG25_TWO_AUTHENTIC_ORIGINAL_SOURCE_PROCESS_REPRO_MISMATCH")
    out=inspect(source_first)
    out["source_immutable_artifact_id"]=p["source"]["artifact_id"]
    out["analytic_prereg_sha256"]=hashlib.sha256(PREREG.read_bytes()).hexdigest()
    out["canonical_receipt_sha256"]=digest(out)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("MG25_CLASSIFICATION",out["classification"])
    print("MG25_SOURCE_ACTIONS",out["original_real_selected_actions_checked"])
    print("MG25_NATIVE_OR_CONTROL_FULL_ACTION_COMPARISONS",
          json.dumps([{k:v for k,v in item.items() if k!="first_divergences"} for item in out["paired_native_and_ablated_controls"]],sort_keys=True))
    print("MG25_POLICY_COUNTS",json.dumps(out["policy_status_frequency"],sort_keys=True))
    print("MG25_RECEIPT",out["canonical_receipt_sha256"])
if __name__=="__main__":
    main()
