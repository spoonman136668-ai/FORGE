#!/usr/bin/env python3
"""MG09 original Farama DoorKey: prospective public orientation/key-retention audit.

Seven independently acting original native/conventional/no-learning roles.
Do not modify their policy or add a route; use real original env.step outcomes
and only original R10 public image, direction, mission. All other state private.
"""
import argparse
import json
import resource
import time
import traceback
from pathlib import Path

from k4r_minigrid_source import canon,sha
import mg07_temporal_original_doorkey as parent
import mg06_original_doorkey_exploration as controls

HERE=Path(__file__).resolve().parent
FROZEN=HERE/"mg09_orientation_retention_prereg.json"
SCHEMA="itd02.mg09.authentic-public-egocentric-retention-audit.v1"
BLOCKED="MG09_PUBLIC_ORIGINAL_SOURCE_OR_CONTROL_INTEGRITY_BLOCKED__NO_SCIENCE"
DOOR="MG09_BOTH_NATIVE_REAL_DOOR_EFFECTS_OBSERVED__NO_SCIENCE"
EXPOSED="MG09_KEYED_DOOR_ALIGNMENT_WITHOUT_BOTH_NATIVE_DOOR_EFFECTS__NO_SCIENCE"
ABSENT="MG09_ORIENTATION_KEY_RETENTION_ALIGNMENT_NOT_ESTABLISHED__NO_SCIENCE"
FROZEN_CONTROLS=("frozen_r13_no_learning","conventional_seeded_random")
ROLES=parent.ROLES+FROZEN_CONTROLS
NATIVE=("wingless_go_dk10","yggdrasil_r14")
CONDITIONS=("key_door_visible","key_no_door_visible","front_door_no_key",
            "key_front_door","no_key_no_door_visible")

def freeze():
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    x=p["protocol"]
    if (p.get("schema")!="itd02.mg09.original-source-egocentric-orientation-key-retention.v1"
        or p["parent"]["head"]!="688c6654c3709123793c1c0429a7ec10ad7f11f5"
        or p["source"]["mg07_original_evaluator_blob"]!="c028d36c8cc45ab1ba7d3acd7aa0ef78c3ceebc3"
        or p["source"]["mg06_original_evaluator_blob"]!="afadf926978721de852f5d49179562340908348e"
        or x["new_original_development_seeds"]!=[69301,69303,69307]
        or x["live_real_steps_per_seed_role"]!=192
        or x["original_FIT_real_selected_steps_per_learner"]!=1664
        or x["roles"]!=list(ROLES)
        or x["actual_live_external_actions"]!=0
        or x["original_public_fields"]!=["image","direction","mission"]
        or x["real_legal_actions"]!=list(range(7))
        or p["classification"]["BLOCKED"]!=BLOCKED
        or p["classification"]["BOTH_DOOR_EFFECT"]!=DOOR
        or p["classification"]["KEYED_FRONT_NO_BOTH_EFFECT"]!=EXPOSED
        or p["classification"]["NO_KEYED_FRONT"]!=ABSENT):
        raise ValueError("MG09_FROZEN_SOURCE_PROTO_DRIFT")
    return p

def normalize_event(row,sourcekind):
    if sourcekind=="mg07":
        b=row["original_public_before"];a=row["original_public_after"]
        act=row["original_selected_action"]
        external=row["external_selected_actions"]
        door=row["visible_door_changed"]
    elif sourcekind=="mg06":
        b=row["real_source_before"];a=row["real_source_after"]
        act=row["selected_action"]
        external=row["external_assistance_count"]
        door=row["real_door_change"]
    else:raise ValueError("MG09_UNDECLARED_SOURCE_EVENT")
    if (type(act)is not int or act not in range(7) or external!=0
        or set(b)!={"image","direction","mission"} or
        set(a)!={"image","direction","mission"} or
        type(row["original_reward"])is not float
        or type(row["terminated"])is not bool
        or type(row["truncated"])is not bool
        or type(door)is not bool):
        raise ValueError("MG09_SPOOFED_OR_ORACLE_SELECTED_EVENT")
    if (len(b["image"])!=7 or len(a["image"])!=7 or
        any(len(r)!=7 or any(len(c)!=3 for c in r) for r in b["image"]) or
        any(len(r)!=7 or any(len(c)!=3 for c in r) for r in a["image"])):
        raise ValueError("MG09_NOT_REAL_PUBLIC_7X7_IMAGE")
    return {"public_before":b,"public_after":a,"action":act,
            "selected_original_reward":row["original_reward"],
            "visible_door_changed":door,
            "terminated":row["terminated"],"truncated":row["truncated"],
            "external_action_count":0,
            "original_public_before_sha":sha(canon(b).encode()),
            "original_public_after_sha":sha(canon(a).encode())}

def doors(public):
    return [(x,y) for x,row in enumerate(public["image"])
                  for y,pixel in enumerate(row) if pixel[0]==4]

def new_counts():
    return {k:0 for k in (
        "original_selected_action_count","real_door_state_changes","true_original_goal_rewards",
        "key_held_decision_frames","door_any_visible_decision_frames",
        "front_door_decision_frames","key_door_visible_frames",
        "key_front_door_frames","front_door_without_key_frames",
        "true_public_key_pickups","true_public_key_losses",
        "selected_drop_action_while_key_held","turn_left_selected",
        "turn_right_selected","turns_expected_public_direction",
        "turns_wrong_public_direction","nonturn_public_direction_changes",
        "door_visible_before_and_after_turns",
        "door_visible_before_and_after_forward",
        "door_distance_closer_after_selected_turn",
        "door_distance_farther_after_selected_turn",
        "door_distance_equal_after_selected_turn",
        "door_distance_closer_after_selected_forward",
        "door_distance_farther_after_selected_forward",
        "door_distance_equal_after_selected_forward",
        "selected_toggle_key_front_door",
        "selected_toggle_front_door_without_key",
        "selected_forward_key_door_visible",
        "unchanged_original_public_frame",
        "key_pickups_lost_within_1_action",
        "key_pickups_lost_within_5_actions",
        "key_pickups_lost_within_10_actions",
        "key_pickups_censored_at_episode_end",
        "key_total_held_followup_steps",
        "key_max_held_followup_steps"
    )}

def diagnostic(original_record,sourcekind):
    events=[normalize_event(e,sourcekind) for e in
            (original_record["all_original_public_selected_action_consequences"]
             if sourcekind=="mg07" else original_record["real_selected_source_feedback"])]
    if not events or len(events)>192:raise ValueError("MG09_BAD_ORIGINAL_EPISODE_LENGTH")
    n=len(events)
    c=new_counts()
    chosen={str(i):0 for i in range(7)}
    conditional={name:{str(a):0 for a in range(7)} for name in CONDITIONS}
    latest_key_pickup=None
    completed_spans=[]
    censored_spans=[]
    states=[]
    for index,e in enumerate(events):
        before=e["public_before"];after=e["public_after"]
        act=e["action"]
        b=before["image"];a=after["image"]
        key=b[3][6][0]==5
        key_after=a[3][6][0]==5
        front=b[3][5][0]==4
        bdoors=doors(before);adoors=doors(after)
        visible=bool(bdoors)
        joint=key and front
        turn=act in (0,1)
        c["original_selected_action_count"]+=1
        c["real_door_state_changes"]+=int(e["visible_door_changed"])
        c["true_original_goal_rewards"]+=int(e["selected_original_reward"]>0)
        c["key_held_decision_frames"]+=int(key)
        c["door_any_visible_decision_frames"]+=int(visible)
        c["front_door_decision_frames"]+=int(front)
        c["key_door_visible_frames"]+=int(key and visible)
        c["key_front_door_frames"]+=int(joint)
        c["front_door_without_key_frames"]+=int(front and not key)
        c["true_public_key_pickups"]+=int(not key and key_after)
        c["true_public_key_losses"]+=int(key and not key_after)
        c["selected_drop_action_while_key_held"]+=int(key and act==4)
        c["turn_left_selected"]+=int(act==0)
        c["turn_right_selected"]+=int(act==1)
        if turn:
            expect=(before["direction"]+(-1 if act==0 else 1))%4
            c["turns_expected_public_direction"]+=int(after["direction"]==expect)
            c["turns_wrong_public_direction"]+=int(after["direction"]!=expect)
        elif after["direction"]!=before["direction"]:
            c["nonturn_public_direction_changes"]+=1
        if bdoors and adoors and (turn or act==2):
            d0=min(abs(x-3)+abs(y-5) for x,y in bdoors)
            d1=min(abs(x-3)+abs(y-5) for x,y in adoors)
            typ="turn" if turn else "forward"
            c["door_visible_before_and_after_"+("turns" if turn else "forward")]+=1
            c["door_distance_"+("closer" if d1<d0 else "farther" if d1>d0 else "equal")+
              "_after_selected_"+typ]+=1
        c["selected_toggle_key_front_door"]+=int(joint and act==5)
        c["selected_toggle_front_door_without_key"]+=int(front and not key and act==5)
        c["selected_forward_key_door_visible"]+=int(key and visible and act==2)
        c["unchanged_original_public_frame"]+=int(
            e["original_public_before_sha"]==e["original_public_after_sha"])
        chosen[str(act)]+=1
        if key and visible:conditional["key_door_visible"][str(act)]+=1
        if key and not visible:conditional["key_no_door_visible"][str(act)]+=1
        if front and not key:conditional["front_door_no_key"][str(act)]+=1
        if joint:conditional["key_front_door"][str(act)]+=1
        if not key and not visible:conditional["no_key_no_door_visible"][str(act)]+=1
        if not key and key_after:
            if latest_key_pickup is not None:
                raise ValueError("MG09_PUBLIC_KEY_CREDIT_STALE_PICKUP")
            latest_key_pickup=index
        if key and not key_after:
            if latest_key_pickup is not None:
                duration=index-latest_key_pickup
                completed_spans.append(duration)
                c["key_pickups_lost_within_1_action"]+=int(duration<=1)
                c["key_pickups_lost_within_5_actions"]+=int(duration<=5)
                c["key_pickups_lost_within_10_actions"]+=int(duration<=10)
                latest_key_pickup=None
        states.append({"ordinal":index+1,"action":act,"public_held_key_before":key,
            "public_held_key_after":key_after,
            "door_in_public_view_before":visible,"door_in_front_before":front,
            "door_key_conjunction_before":joint,
            "actual_selected_reward":e["selected_original_reward"],
            "visible_door_state_changed":e["visible_door_changed"],
            "original_direction_before":before["direction"],
            "original_direction_after":after["direction"],
            "original_source_public_before_sha":e["original_public_before_sha"],
            "original_source_public_after_sha":e["original_public_after_sha"]})
    if latest_key_pickup is not None:
        censored_spans.append(n-latest_key_pickup-1)
        c["key_pickups_censored_at_episode_end"]+=1
    all_spans=completed_spans+censored_spans
    c["key_total_held_followup_steps"]=sum(all_spans)
    c["key_max_held_followup_steps"]=max(all_spans,default=0)
    if (c["original_selected_action_count"]!=n or
        c["real_door_state_changes"]!=original_record.get(
            "observed_public_door_changes",original_record.get("original_door_changes")) or
        c["true_original_goal_rewards"]!=original_record.get(
            "original_goal_rewards") or
        c["true_public_key_pickups"]<c["true_public_key_losses"]-1):
        raise ValueError("MG09_PUBLIC_SELECTED_CONSEQUENCE_TALLY_CHANGED")
    return {"role":original_record["role"],
        "evaluator_seed_only":original_record.get("evaluator_seed_only",original_record.get("seed_evaluator_only")),
        "original_public_start_sha":original_record.get("original_public_start_sha",original_record.get("original_public_start_sha256")),
        "source_role_kind":sourcekind,
        "source_only_counts":c,
        "source_selected_action_counts":chosen,
        "conditional_real_selected_action_counts":conditional,
        "key_retention_completed_spans":completed_spans,
        "key_retention_censored_spans":censored_spans,
        "original_public_observed_states":states}

def run(new_go,old_go,p):
    # Source-locked unchanged MG07 evaluator and accepted learning rules.
    original_fit=parent.fit(new_go,old_go,{
        "source_fit_seeds":p["protocol"]["original_FIT_seeds"]})
    if original_fit["samples"]!=1664:
        raise ValueError("MG09_NOT_EQUAL_ORIGINAL_SELECTED_FIT")
    all_original=[]
    all_diag=[]
    for seed in p["protocol"]["new_original_development_seeds"]:
        batch=[]
        for role in ROLES:
            if role in parent.ROLES:
                episode=parent.episode(role,seed,original_fit,new_go,old_go,
                                       {"max_original_steps":192})
                kind="mg07"
            else:
                original_frozen=dict(original_fit,native_go=original_fit["parent_go"])
                episode=controls.episode(role,seed,original_frozen,new_go,
                                          {"steps_per_episode":192})
                kind="mg06"
            batch.append(episode)
            all_original.append(episode)
            all_diag.append(diagnostic(episode,kind))
        if len({e.get("original_public_start_sha",e.get("original_public_start_sha256")) for e in batch})!=1:
            raise ValueError("MG09_SOURCE_PUBLIC_START_NOT_EQUAL")
    if len(all_original)!=21 or any(
        not 1<=c["source_only_counts"]["original_selected_action_count"]<=192
        for c in all_diag):
        raise ValueError("MG09_NOT_ALL_AUTHENTIC_REAL_SELECTED_EXPOSURES")
    summary={}
    for role in ROLES:
        eps=[x for x in all_diag if x["role"]==role]
        if len(eps)!=3:raise ValueError("MG09_MISSING_INDEPENDENT_CONTROL")
        totals={k:sum(e["source_only_counts"][k] for e in eps)
                for k in new_counts()}
        totals["original_real_episodes"]=3
        summary[role]=totals
    positive=all(summary[x]["real_door_state_changes"]>=1 for x in NATIVE)
    opportunity=any(summary[x]["key_front_door_frames"]>0 for x in NATIVE)
    status=DOOR if positive else EXPOSED if opportunity else ABSENT
    evidence={"schema":SCHEMA,
        "original_source_environment_commit":p["source"]["farama"],
        "unchanged_native_parent_and_conventional_pins":p["source"],
        "exact_original_FIT_selected_public_sha":original_fit["source_history_sha256"],
        "identical_original_FIT_selected_samples_per_model":original_fit["samples"],
        "original_native_source_fit_cold_checkpoints":original_fit["checkpoint_sha256"],
        "source_only_new_real_original_selected_step_records":all_original,
        "source_only_orientation_retention_per_episode":all_diag,
        "source_only_orientation_retention_per_role":summary,
        "external_live_actions":0,
        "original_models_unchanged":True,
        "source_original_public_data_only":True}
    return {"schema":SCHEMA,"classification":status,
        "scientific_first_use":False,"FORGE_controller_changed":False,
        "accepted_native_model_changed":False,
        "original_Wingless_R8_or_Ygg_R10_R12_changed":False,
        "three_new_original_source_seeds":True,"real_original_episode_count":21,
        "original_source_selected_FIT_each":1664,"actual_original_live_external_actions":0,
        "canonical_original_source_sha":sha(canon(evidence).encode()),
        "canonical_original_source_evidence":evidence}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--wingless-dk10",type=Path,required=True)
    ap.add_argument("--wingless-dk9",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    t=time.perf_counter();cpu=time.process_time()
    try:
        report=run(args.wingless_dk10,args.wingless_dk9,freeze())
    except Exception as exc:
        report={"schema":SCHEMA,"classification":BLOCKED,"scientific_first_use":False,
          "error_type":type(exc).__name__,"error":str(exc),
          "trace_tail":traceback.format_exc().splitlines()[-14:]}
    report["host_wall_s"]=round(time.perf_counter()-t,6)
    report["host_cpu_s"]=round(time.process_time()-cpu,6)
    report["host_max_rss_kib"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("MG09_CLASSIFICATION",report["classification"])
    print("MG09_CANONICAL_SOURCE_SHA",report.get("canonical_original_source_sha","NONE"))
    print("MG09_ROLE_PUBLIC_SUMMARY",json.dumps(
        report.get("canonical_original_source_evidence",{}).get(
            "source_only_orientation_retention_per_role",{}),sort_keys=True))
    if report["classification"]==BLOCKED:
        print("MG09_BLOCKER",report.get("error_type"),report.get("error"))
    return 1 if report["classification"]==BLOCKED else 0
if __name__=="__main__":
    raise SystemExit(main())
