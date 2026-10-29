#!/usr/bin/env python3
"""MG06 native-only original Farama DoorKey prospective exploration.

Same source-proven authentic FIT, separate native Go DK9 and original Ygg R13
local-cell memory, independently acting source-only conventional and frozen
no-learning baseline. No original live action ever supplied by a collector.
"""
import argparse
import base64
import hashlib
import json
import random
import resource
import sys
import time
import traceback
from pathlib import Path

from k4r_minigrid_source import canon,sha
from k4u_native_minigrid import WingBridge
import mg03_equal_public_doorkey_live as earlier
import mg04_public_effect_native_agency as original

HERE=Path(__file__).resolve().parent
FROZEN=HERE/"mg06_native_exploration_prereg.json"
SCHEMA="itd02.mg06.authentic-native-only-self-chosen-doorkey.v1"
BLOCKED="MG06_ORIGINAL_SOURCE_OR_NATIVE_EXPLORATION_CUSTODY_BLOCKED__NO_SCIENCE"
NEGATIVE="MG06_NATIVE_EXPLORATION_DID_NOT_COMPLETE_DOORKEY__NO_SCIENCE"
POSITIVE="MG06_BOUNDED_NATIVE_EXPLORATION_GOAL_ENGINEERING_POSITIVE__NO_SCIENCE"
ROLES=("wingless_go_dk9","yggdrasil_r13","conventional_min_count",
       "conventional_seeded_random","frozen_r13_no_learning")

def freeze():
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    if (p.get("schema")!="itd02.mg06.original-doorkey-zero-external-exploration.v1"
        or p.get("parent_head")!="44897745c6cd9ab69f5e070bab11de79793ecfcd"
        or p.get("original_ygg_r13")!="b27372e6c670166749dc3dc41ab6cfe9b263292f"
        or p.get("ygg_r13_blob")!="51c421fbd34b5e88e02bf89acab0de7b11eee1c9"
        or p.get("training_count")!=1664
        or p.get("development_seeds")!=[66301,66303,66307]
        or p.get("steps_per_episode")!=192
        or p.get("external_navigation_budget")!=0
        or p.get("roles")!=list(ROLES)
        or p["classification"]["negative"]!=NEGATIVE):
        raise ValueError("MG06_FROZEN_ORIGINAL_WORLD_POLICY_DRIFT")
    if p.get("wingless_dk9")=="PIN_AFTER_GO_QUAL":
        raise ValueError("MG06_UNVERIFIED_GO_NATIVE_SOURCE_PIN")
    return p

def source_modules():
    gym,owner,Cell,select,collector,conv=original.get_modules()
    from research.native.itd02.r13.explore_choice import propose_native_action
    return gym,owner,Cell,collector,conv,propose_native_action

def conventional_min(control,conv,public):
    counts=[]
    for action in range(7):
        row=control.counts.get(conv.context(public,action),{})
        counts.append(sum(row.values()))
    minimum=min(counts)
    # fixed no-goal prior and deterministic local-public tie; this is a
    # conventional uncertainty control, not native reward-solving.
    key=sha(canon(public).encode())
    start=int(key[:2],16)%7
    for step in range(7):
        action=(start+step)%7
        if counts[action]==minimum:return action
    raise ValueError("MG06_CONVENTIONAL_UNREACHABLE")

def episode(role,seed,trained,binary,p):
    gym,owner,Cell,collector,conv,explore=source_modules()
    env=gym.make("MiniGrid-DoorKey-8x8-v0")
    a=owner.DoorKeyPublicAdapter()
    wing=None
    native=None
    conventional=None
    randomizer=random.Random(67177+seed)
    try:
        raw,_=env.reset(seed=seed)
        first=earlier.normalize(collector,owner,raw)
        start_sha=owner.digest(first)
        a.reset_public(first)
        if role=="wingless_go_dk9":
            wing=WingBridge(binary)
            ack=wing.request("load",state=base64.b64encode(trained["native_go"]).decode("ascii"))
            if ack.get("updates",0)!=trained["samples"] or ack.get("live",0)!=0:
                raise ValueError("MG06_GO_REAL_FIT_NOT_COLD_RESTORED")
            wing.request("begin_episode")
        elif role in ("yggdrasil_r13","frozen_r13_no_learning"):
            native=Cell.restore(trained["native_ygg"])
            if native.samples!=trained["samples"]:raise ValueError("MG06_R13_LOCAL_SOURCE_NOT_RESTORED")
            native.start_session(a,"mg06-"+str(seed)+"-"+role)
            if role=="frozen_r13_no_learning":frozen_native= native.checkpoint()
        elif role in ("conventional_min_count","conventional_seeded_random"):
            conventional=conv.Control.restore(trained["conventional"])
            if conventional.samples!=trained["samples"]:raise ValueError("MG06_CONVENTIONAL_SOURCE_NOT_RESTORED")
            if role=="conventional_seeded_random":frozen_conventional=conventional.checkpoint()
        else:raise ValueError("MG06_UNKNOWN_ACTOR")
        steps=[]
        carrying_seen=False
        door_after_carry=False
        goals=key_changes=door_changes=0
        for i in range(p["steps_per_episode"]):
            before=earlier.normalize(collector,owner,raw)
            if a.current!=before:raise ValueError("MG06_ORIGINAL_PUBLIC_STATE_DRIFT")
            if wing is not None:
                selected=wing.request("choose",before=before,objective=original.objective(owner,before))
                choice=selected.get("action");mode=selected.get("status")
            elif native is not None:
                selected=explore(native,before)
                choice=selected["action"];mode=selected["status"]
            elif role=="conventional_min_count":
                choice=conventional_min(conventional,conv,before)
                mode="CONVENTIONAL_PUBLIC_LEAST_SELECTED"
            else:
                choice=randomizer.randrange(7)
                mode="CONVENTIONAL_SEEDED_UNIFORM_RANDOM"
            if type(choice)is not int or choice not in range(7):
                raise ValueError("MG06_NATIVE_ABSTAIN_OR_UNTRUSTED_PUBLIC_ACTION")
            if wing is not None:
                ack=wing.request("commit",before=before,action=choice)
                if ack.get("updates",0)!=trained["samples"]+i:
                    raise ValueError("MG06_GO_PENDING_ACTION_NOT_COMMITTED")
            if a.submit(choice)!=choice:raise ValueError("MG06_SOURCE_ACTION_REMAP")
            next_raw,reward,terminated,truncated,_=env.step(choice)
            after=earlier.normalize(collector,owner,next_raw)
            event=a.complete(after,float(reward),bool(terminated),bool(truncated))
            if wing is not None:
                ack=wing.request("feedback",before=before,action=choice,after=after,
                    reward=float(reward),terminal=bool(terminated or truncated))
                if ack.get("updates",0)!=trained["samples"]+i+1 or ack.get("live",0)!=i+1:
                    raise ValueError("MG06_GO_SELECTED_NATIVE_CREDIT_MISSING")
            elif native is not None and role=="yggdrasil_r13":
                receipt=native.learn_selected(a)
                if receipt["sample_index"]!=trained["samples"]+i+1 or native.samples!=trained["samples"]+i+1:
                    raise ValueError("MG06_R13_SELECTED_LOCAL_FEEDBACK_MISSING")
            elif conventional is not None and role=="conventional_min_count":
                conventional.learn(event)
                if conventional.samples!=trained["samples"]+i+1:
                    raise ValueError("MG06_CONVENTIONAL_SELECTED_FEEDBACK_MISSING")
            elif native is not None:
                if native.samples!=trained["samples"] or native.checkpoint()!=frozen_native:
                    raise ValueError("MG06_NO_LEARNING_SHADOW_UPDATED")
            else:
                if conventional.checkpoint()!=frozen_conventional:
                    raise ValueError("MG06_RANDOM_CONTROL_MEMORY_UPDATED")
            carrying=event["carried_before"]!=event["carried_after"]
            f0,f1=event["front_before"],event["front_after"]
            door=f0[0]==4 and f1[0]==4 and f0[2]!=f1[2]
            key_changes+=int(carrying)
            door_changes+=int(door)
            if carrying:carrying_seen=True
            if door and carrying_seen:door_after_carry=True
            goals+=int(float(reward)>0)
            steps.append({"ordinal":i+1,"selected_action":choice,"selected_action_source":mode,
                          "real_source_before":before,"real_source_after":after,
                          "original_reward":float(reward),"real_key_change":bool(carrying),
                          "real_door_change":bool(door),
                          "terminated":bool(terminated),"truncated":bool(truncated),
                          "original_selected_after_sha":owner.digest(after),
                          "external_assistance_count":0})
            raw=next_raw
            if terminated or truncated:break
        if wing is not None:
            checkpoint=wing.snapshot()
            cold=WingBridge(binary)
            try:
                ack=cold.request("load",state=base64.b64encode(checkpoint).decode("ascii"))
                if (ack.get("updates",0)!=trained["samples"]+len(steps)
                    or ack.get("live",0)!=len(steps)
                    or cold.snapshot()!=checkpoint):
                    raise ValueError("MG06_GO_COLD_RESTORE_AFTER_LIVE")
            finally:cold.close()
        elif native is not None:
            checkpoint=native.checkpoint()
            restored=Cell.restore(checkpoint)
            expected=trained["samples"]+(len(steps) if role=="yggdrasil_r13" else 0)
            if restored.checkpoint()!=checkpoint or restored.samples!=expected:
                raise ValueError("MG06_YGG_COLD_RESTORE_AFTER_LIVE")
            if role=="frozen_r13_no_learning" and checkpoint!=frozen_native:
                raise ValueError("MG06_FROZEN_R13_FAILED_NO_LEARNING")
        else:
            checkpoint=conventional.checkpoint()
            restored=conv.Control.restore(checkpoint)
            expected=trained["samples"]+(len(steps) if role=="conventional_min_count" else 0)
            if restored.checkpoint()!=checkpoint or restored.samples!=expected:
                raise ValueError("MG06_CONVENTIONAL_COLD_RESTORE_AFTER_LIVE")
        return {"role":role,"seed_evaluator_only":seed,"original_public_start_sha":start_sha,
             "real_selected_action_count":len(steps),"external_actions":0,
             "original_key_changes":key_changes,"original_door_changes":door_changes,
             "original_goal_rewards":goals,"ordered_key_door_goal":
                bool(carrying_seen and door_after_carry and goals>0),
             "checkpoint_sha256_after_selected_experience":sha(checkpoint),
             "real_selected_source_feedback":steps}
    finally:
        env.close()
        if wing is not None:wing.close()

def run(binary,p):
    # Unchanged original FIT on 1664 selected public transitions shared by
    # Go DK9 (DK8 state), Ygg original R11 and conventional C30.
    fitted=original.fit(binary,{"FIT":{"seeds":p["training_seeds"],"cap":256}})
    if fitted["samples"]!=1664:raise ValueError("MG06_NOT_ORIGINAL_SOURCE_FIT")
    results=[]
    for seed in p["development_seeds"]:
        same=[episode(role,seed,fitted,binary,p) for role in ROLES]
        if len({x["original_public_start_sha"] for x in same})!=1:
            raise ValueError("MG06_NONMATCHED_AUTHENTIC_PUBLIC_RESET")
        results.extend(same)
    if len(results)!=15 or any(x["real_selected_action_count"]<1 for x in results):
        raise ValueError("MG06_MISSING_AUTHENTIC_NATIVE_DECISIONS")
    summary={}
    for role in ROLES:
        rows=[x for x in results if x["role"]==role]
        summary[role]={
            "original_episodes":len(rows),
            "original_actions_selected_by_actor":sum(x["real_selected_action_count"] for x in rows),
            "external_actions":0,
            "key_effects":sum(x["original_key_changes"] for x in rows),
            "door_effects":sum(x["original_door_changes"] for x in rows),
            "real_goal_rewards":sum(x["original_goal_rewards"] for x in rows),
            "complete_key_door_goal_chains":sum(x["ordered_key_door_goal"] for x in rows),
            "episodes_executing_at_least_64_native_actions_or_terminal":
                sum(x["real_selected_action_count"]>=64 or
                    any(y["terminated"] or y["truncated"] for y in x["real_selected_source_feedback"])
                    for x in rows)}
    both=all(summary[r]["real_goal_rewards"]>=1
         and summary[r]["episodes_executing_at_least_64_native_actions_or_terminal"]==3
         for r in ("wingless_go_dk9","yggdrasil_r13"))
    classification=POSITIVE if both else NEGATIVE
    evidence={"schema":SCHEMA,"source_training_public_sha256":fitted["source_history_sha256"],
        "source_fit_per_role":fitted["samples"],
        "original_source":p["source_farama"],"ygg_source":p["original_ygg_r13"],
        "go_source":p["wingless_dk9"],"public_action_set":p["actions"],
        "original_real_selected_traces":results,
        "per_actor_original_environment_summary":summary,
        "no_external_collector_used_during_any_live_episode":True,
        "no_learning_shadow_original_source_unchanged":True,
        "old_wingless_R8_unchanged":True}
    return {"schema":SCHEMA,"classification":classification,"scientific_first_use":False,
      "accepted_model_promoted":False,"FORGE_controller_modified":False,
      "original_Wingless_R8_modified":False,"original_Ygg_R12_modified":False,
      "matched_original_source_FIT_per_role":fitted["samples"],
      "zero_external_actions":True,"role_count":5,"real_episode_count":len(results),
      "canonical_original_selected_trace_sha256":sha(canon(evidence).encode()),
      "original_source_canonical_evidence":evidence}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--wingless-dk9-go",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    start=time.perf_counter();cpu=time.process_time()
    try:r=run(args.wingless_dk9_go,freeze())
    except Exception as e:
        r={"schema":SCHEMA,"classification":BLOCKED,"scientific_first_use":False,
           "error_type":type(e).__name__,"error":str(e),
           "trace_tail":traceback.format_exc().splitlines()[-12:]}
    r["host_wall_s"]=round(time.perf_counter()-start,6)
    r["host_cpu_s"]=round(time.process_time()-cpu,6)
    r["host_peak_rss_kib"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    args.output.write_text(json.dumps(r,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("MG06_CLASSIFICATION",r["classification"])
    print("MG06_CANONICAL_SHA",r.get("canonical_original_selected_trace_sha256","NONE"))
    print("MG06_PER_ROLE_RESULTS",json.dumps(r.get("original_source_canonical_evidence",{}).get("per_actor_original_environment_summary",{}),sort_keys=True))
    if r["classification"]==BLOCKED:print("MG06_BLOCKER",r.get("error_type"),r.get("error"))
    return 1 if r["classification"]==BLOCKED else 0
if __name__=="__main__":raise SystemExit(main())
