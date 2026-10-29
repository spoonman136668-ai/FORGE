#!/usr/bin/env python3
"""MG30: read-only opportunity vs selected effect, original Farama mission worlds.

Never uses hidden map/agent inventory, never executes proposed actions.
Precommitted before this executable, but 9,186 MG24 development events
are already exposed and never eligible as unseen transfer/first use.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,re
from pathlib import Path
from mg25_original_policy_activation_audit import (
    get_source,inspect as authenticate,FAMILIES,SEEDS,digest
)
HERE=Path(__file__).resolve().parent
FROZEN=HERE/"mg30_public_decision_opportunity_prereg.json"
ORIGINAL="e2dda4721d6d96ffd083faac5960013380b29c3325f560defa989c4eef0852a9"
PARENT="e4d794e46e6ca39b4f400fbd3c17e68dd6270d11"
ROLES=("wingless_MG23","yggdrasil_MG23","conventional_full")
PICKUP=re.compile(r"^pick up the (red|green|blue|purple|yellow|grey) (key|ball|box)$")
COLORS={"red":0,"green":1,"blue":2,"purple":3,"yellow":4,"grey":5}
OBJECTS={"key":5,"ball":6,"box":7}

def freeze():
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    decision=p["decision_rule"]
    if (p.get("schema")!="itd02.mg30.original-public-decision-opportunity-sufficiency.v1"
        or p["phase"]!="PROSPECTIVE_TO_AUDIT_ONLY__ORIGINAL_MG24_DEV_ALREADY_EXPOSED"
        or p["parents"]["original_mg29_strong_action_only"]!=PARENT
        or p["parents"]["original_mg24_source_sha"]!=ORIGINAL
        or p["parents"]["original_farama"]!="7f5853792ea7f04f75614661006d87fcf949f26d"
        or p["parents"]["actual_selected_source_actions"]!=9186
        or p["cohort"]["actors"]!=list(ROLES)
        or p["cohort"]["families"]!=list(FAMILIES)
        or p["cohort"]["full_episode_matrix"]!=24
        or p["public_observation"]["front_pixel_image_index"]!=[3,5]
        or p["public_observation"]["farama_colors"]!=COLORS
        or p["public_observation"]["portable_target_types"]!=OBJECTS
        or decision["minimum_distinct_positive_target_effects_per_unfamiliar_family"]!=10
        or decision["minimum_distinct_seed_episodes_with_target_effect_per_unfamiliar_family"]!=2
        or decision["minimum_distinct_positive_locked_door_openings_per_unfamiliar_family"]!=10
        or not decision["require_context_increment_over_action_only"]
        or not all(p["safety"].values())):
        raise ValueError("MG30_UNFROZEN_OR_CHANGED_PRECOMMITTED_SOURCE_AUDIT")
    return p

def observable(before,after,action,mission):
    # Classification strictly from source-public before and actual source after.
    # MiniGrid original egocentric front pixel is image[x=3][y=5].
    if type(action)is not int or action not in range(7):
        raise ValueError("MG30_ORIGINAL_ACTION_ID_BAD")
    if (before["mission"]!=mission or after["mission"]!=mission
        or before["direction"] not in range(4)
        or after["direction"] not in range(4)):
        raise ValueError("MG30_ORIGINAL_SOURCE_MISSION_OR_DIRECTION_DRIFT")
    x=before["image"][3][5];y=after["image"][3][5]
    if len(x)!=3 or len(y)!=3:
        raise ValueError("MG30_SOURCE_ORIGINAL_FRONT_MISSING")
    m=PICKUP.fullmatch(mission)
    front_target=bool(m and x[0]==OBJECTS[m.group(2)] and x[1]==COLORS[m.group(1)])
    front_locked=bool(x[0]==4 and x[2]==2)
    same_dir=before["direction"]==after["direction"]
    selected_target=bool(front_target and same_dir and action==3 and y[0]==1)
    selected_locked=bool(front_locked and same_dir and action==5
                         and y[0]==4 and y[1]==x[1] and y[2]==0)
    return {"mission_target_visible_front":front_target,
        "locked_door_visible_front":front_locked,
        "pickup_selected_at_target":front_target and action==3,
        "toggle_selected_at_locked_door":front_locked and action==5,
        "actual_target_pickup_visible":selected_target,
        "actual_locked_door_open_visible":selected_locked}

def synthetic():
    def frame(m="pick up the red box",cell=(7,0,0),direction=0):
        img=[[[1,0,0] for _ in range(7)] for _ in range(7)]
        img[3][5]=list(cell)
        return {"image":img,"direction":direction,"mission":m}
    b=frame();after=frame(cell=(1,0,0))
    pos=observable(b,after,3,b["mission"])
    assert pos["mission_target_visible_front"] and pos["actual_target_pickup_visible"]
    assert not observable(b,after,5,b["mission"])["actual_target_pickup_visible"]
    blue=frame(m="pick up the blue box")
    assert not observable(blue,frame(m="pick up the blue box",cell=(1,0,0)),3,blue["mission"])["actual_target_pickup_visible"]
    door=frame(cell=(4,2,2))
    opened=frame(cell=(4,2,0))
    assert observable(door,opened,5,door["mission"])["actual_locked_door_open_visible"]
    assert not observable(door,opened,3,door["mission"])["actual_locked_door_open_visible"]
    assert not observable(door,opened,5,door["mission"])["actual_target_pickup_visible"]

def report(a,b):
    p=freeze()
    first=get_source(a);second=get_source(b)
    if (first["canonical_source_sha256"]!=ORIGINAL or
        second["canonical_source_sha256"]!=ORIGINAL or
        first["source"]!=second["source"]):
        raise ValueError("MG30_NOT_TWO_AUTHENTIC_INDEPENDENT_ORIGINAL_WORLD_PROCESSES")
    authenticate(first);authenticate(second)
    rows=first["source"]["full_original_selected_source_72_episodes"]
    index={(r["family"],r["dev_seed_exposed"],r["role"]):r for r in rows}
    if len(rows)!=72 or len(index)!=72:
        raise ValueError("MG30_ORIGINAL_SOURCE_72_EPISODE_CUSTODY_MISSING")
    result={}
    total=collections.Counter()
    for family,seeds in zip(FAMILIES,SEEDS):
        for role in ROLES:
            counts=collections.Counter()
            target_sha=set()
            door_sha=set()
            success_seeds=set()
            prior_events=0
            for seed in seeds:
                rec=index[(family,seed,role)]
                events=rec["selected_source_events"]
                prev=None
                for i,e in enumerate(events,1):
                    if (type(e.get("action")) is not int or
                        e["index"]!=i or e["before_sha256"]!=digest(e["before"]) or
                        e["after_sha256"]!=digest(e["after"]) or
                        e["before"]["mission"]!=rec["original_mission"] or
                        e["after"]["mission"]!=rec["original_mission"] or
                        (prev is not None and prev!=e["before_sha256"]) or
                        type(e["public_mission_target_pickup"]) is not bool or
                        type(e["public_locked_door_open"]) is not bool):
                        raise ValueError("MG30_ORIGINAL_SELECTED_SOURCE_CONTINUITY_TAMPER")
                    seen=observable(e["before"],e["after"],e["action"],rec["original_mission"])
                    if (seen["actual_target_pickup_visible"]!=e["public_mission_target_pickup"] or
                        seen["actual_locked_door_open_visible"]!=e["public_locked_door_open"]):
                        raise ValueError("MG30_UNTRUSTED_SOURCE_PUBLIC_ACTION_EFFECT_FLAG")
                    counts["source_selected_actions"]+=1
                    counts["public_scene_changes"]+=int(e["before_sha256"]!=e["after_sha256"])
                    counts["public_repeated_exact"]+=int(e["before_sha256"]==e["after_sha256"])
                    counts["original_goal_rewards"]+=int(e["terminated"] and e["reward"]>0)
                    for name,val in seen.items():
                        counts[name]+=int(val)
                    if seen["mission_target_visible_front"]:target_sha.add(e["before_sha256"])
                    if seen["locked_door_visible_front"]:door_sha.add(e["before_sha256"])
                    if seen["actual_target_pickup_visible"]:success_seeds.add(seed)
                    prev=e["after_sha256"]
                    prior_events+=1
            counts["unique_original_target_front_public_frames"]=len(target_sha)
            counts["unique_original_locked_door_front_public_frames"]=len(door_sha)
            counts["distinct_source_seed_episodes_with_true_target_effect"]=len(success_seeds)
            result[family+"|"+role]=dict(sorted(counts.items()))
            total.update(counts)
    eligible={}
    for family in FAMILIES[1:]:
        pooled={k:sum(result[family+"|"+role][k] for role in ROLES) for k in
                ("actual_target_pickup_visible","actual_locked_door_open_visible",
                 "mission_target_visible_front","locked_door_visible_front")}
        pooled["distinct_role_seed_pairs_with_selected_target"]=sum(
            result[family+"|"+role]["distinct_source_seed_episodes_with_true_target_effect"] for role in ROLES)
        eligible[family]=pooled
    d=p["decision_rule"]
    enough=all(v["actual_target_pickup_visible"]>=d["minimum_distinct_positive_target_effects_per_unfamiliar_family"]
        and v["distinct_role_seed_pairs_with_selected_target"]>=d["minimum_distinct_seed_episodes_with_target_effect_per_unfamiliar_family"]
        and v["actual_locked_door_open_visible"]>=d["minimum_distinct_positive_locked_door_openings_per_unfamiliar_family"]
        for v in eligible.values())
    # Previously published exact same-supported earlier-only event Brier:
    # full mission/context/action 0.1023041387 WORSE than action-only 0.0711625756.
    native_incremental_action_control=(0.1023041387<=0.0711625756-0.02)
    promotion_eligible=enough and native_incremental_action_control
    if sum(result[k]["source_selected_actions"] for k in result)>9186:
        raise ValueError("MG30_SELECTED_SOURCE_EXCEEDED_9186_ACTION_LEDGER")
    out={"schema":"itd02.mg30.actual-original-public-decision-opportunity-receipt.v1",
         "classification":d["if_pass"] if promotion_eligible else d["if_fail"],
         "source_original_sha256":ORIGINAL,
         "all_original_episodes_authenticated":72,
         "all_original_actions_authenticated":9186,
         "observed_own_original_actions_subset":sum(z["source_selected_actions"] for z in result.values()),
         "per_family_role":result,"per_unfamiliar_family_target_and_door_support":eligible,
         "native_full_context_brier":0.1023041387,
         "matched_same_event_action_only_brier":0.0711625756,
         "native_full_context_increment_over_action_only":native_incremental_action_control,
         "public_decision_support_threshold_pass":enough,
         "authorize_new_original_native_live_rollout":promotion_eligible,
         "no_hidden_world_or_inventory_claim":True,
         "no_new_original_world_actions":True,
         "scientific_first_use":False,
         "accepted_model_controller_main_or_g29_unchanged":True}
    out["sha256"]=digest(out)
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--first",type=Path)
    ap.add_argument("--second",type=Path)
    ap.add_argument("--output",type=Path)
    ap.add_argument("--self-test",action="store_true")
    o=ap.parse_args()
    synthetic()
    if o.self_test:
        print("MG30_SYNTHETIC_ORIGINAL_PUBLIC_OPPORTUNITY_NEGATIVE_CONTROLS_PASS");return
    if not (o.first and o.second and o.output):
        ap.error("required --first, --second, --output")
    x=report(o.first,o.second)
    o.output.parent.mkdir(parents=True,exist_ok=True)
    o.output.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("MG30_ORIGINAL_SELECTED_PUBLIC_DECISION_OPPORTUNITY",x["classification"])
    print("MG30_ORIGINAL_PUBLIC_OPPORTUNITY_SUMMARY",json.dumps(x["per_unfamiliar_family_target_and_door_support"],sort_keys=True))
    print("MG30_SOURCE_RECEIPT_SHA",x["sha256"])
if __name__=="__main__":main()
