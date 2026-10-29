#!/usr/bin/env python3
"""MG15: source-faithful post-FIT online vs bundled no-online/no-episode-memory ablation.

Original Wingless DK13, Ygg R17, classical successor and random, same authentic
Farama original DoorKey public 7x7 observation. No model source replacement.
Source-trained learned FIT checkpoint reloaded at EACH frozen policy decision;
frozen actor never receives own source-selected feedback. Does NOT isolate
online learning from episode memory (both disabled together by prereg).
"""
import argparse
import base64
import json
import random
import resource
import time
import traceback
from pathlib import Path
from k4r_minigrid_source import canon,sha
from k4u_native_minigrid import WingBridge
import mg03_equal_public_doorkey_live as source
import mg14_original_successor as parent
from mg14_original_successor import ConventionalSuccessor

HERE=Path(__file__).resolve().parent
SCHEMA="itd02.mg15.original-postfit-learning-vs-freeze.v1"
BLOCKED="MG15_ORIGINAL_POSTFIT_ABLATION_SOURCE_BLOCKED__NO_SCIENCE"
NEGATIVE="MG15_ONLINE_NATIVE_GOAL_ADVANTAGE_NOT_ESTABLISHED__NO_SCIENCE"
POSITIVE="MG15_BOTH_NATIVE_ONLINE_GOAL_ADVANTAGE_ENGINEERING_POSITIVE__NO_SCIENCE"
ROLES=("wingless_go_dk13_online","wingless_go_dk13_frozen",
       "yggdrasil_r17_online","yggdrasil_r17_frozen",
       "conventional_successor_online","conventional_successor_frozen",
       "conventional_seeded_random")
PARENT_ROLES=("wingless_go_dk13","yggdrasil_r17",
              "conventional_public_successor","conventional_seeded_random")
SEEDS=(74301,74303,74307)
NATIVE=(("wingless_go_dk13_online","wingless_go_dk13_frozen"),
        ("yggdrasil_r17_online","yggdrasil_r17_frozen"))

def freeze():
    p=json.loads((HERE/"mg15_online_frozen_prereg.json").read_text(encoding="utf-8"))
    s=p["source"];q=p["protocol"];a=p["primary"]
    if (p["schema"]!="itd02.mg15.authentic-original-postfit-online-learning-ablation.v1"
        or p["parent"]["exact_head"]!="1bf88f162a4dd105091dc54cf75efa9ffd0caf7b"
        or s["unchanged_mg14_evaluator_blob"]!="0374e659f3d77db571018e2121f07fbdd3001c26"
        or s["unchanged_mg14_go_ipc_blob"]!="a775d24b8dae9879e79e12a4a3af74eb01bb934f"
        or s["farama"]!="7f5853792ea7f04f75614661006d87fcf949f26d"
        or s["wingless_DK13"]!="2992a25e3fe05783bfa80ecf70d737bb2a21e281"
        or s["ygg_R17"]!="770244b04d011466458b2335d3951daf7653dc8f"
        or q["fresh_development_seeds"]!=list(SEEDS)
        or q["max_true_steps_per_episode"]!=192
        or q["all_roles"]!=list(ROLES)
        or q["original_public_fields"]!=["image","direction","mission"]
        or q["actions"]!=list(range(7))
        or q["original_FIT_selected_samples_each_learned_arm"]!=1664
        or q["original_FIT_selected_SHA"]!="9c640b0ae6a0865b9db7147d4b816643962ee69141950e7639dcc09b832d0e24"
        or q["actual_external_actions_live"]!=0
        or a["results"]["blocked"]!=BLOCKED or a["results"]["negative"]!=NEGATIVE
        or a["results"]["engineering_positive"]!=POSITIVE):
        raise ValueError("MG15_ORIGINAL_SOURCE_PREREG_DRIFT")
    return p

def parent_protocol(p):
    q=p["protocol"]
    return {"FIT":{"seeds":q["original_FIT_seeds"],"cap_per_seed":256,
                   "required_original_selected_samples":1664,
                   "require_canonical_history_sha256":q["original_FIT_selected_SHA"]},
            "DEV":{"seeds":q["fresh_development_seeds"],"limit":192,
                   "random_seed_offset":78173},
            "native":{"wingless_exact_head":p["source"]["wingless_DK13"],
                      "ygg_exact_head":p["source"]["ygg_R17"]},
            "parent":{"original_farama":p["source"]["farama"]}}

def frozen_episode(role,seed,trained,binary,protocol):
    gym,owner,collector,MotionCells=parent.modules()
    env=gym.make("MiniGrid-DoorKey-8x8-v0")
    adapter=owner.DoorKeyPublicAdapter()
    go=WingBridge(binary) if role=="wingless_go_dk13_frozen" else None
    rng=random.Random(78173+seed)
    try:
        raw,_=env.reset(seed=seed)
        first=source.normalize(collector,owner,raw)
        adapter.reset_public(first)
        original_start_sha=owner.digest(first)
        events=[]
        for i in range(192):
            before=source.normalize(collector,owner,raw)
            if before!=adapter.current:
                raise ValueError("MG15_NOT_GENUINE_PUBLIC_BEFORE")
            if go is not None:
                ack=go.request("load",state=base64.b64encode(trained["go"]).decode("ascii"))
                if ack.get("updates")!=1664 or ack.get("live",0)!=0:
                    raise ValueError("MG15_GO_NOT_FROZEN_TO_IDENTICAL_ORIGINAL_FIT")
                ack=go.request("begin_episode")
                if ack.get("updates")!=1664 or ack.get("live",0)!=0:
                    raise ValueError("MG15_GO_BEGIN_EPISODE_NO_CREDIT")
                choice=go.request("choose",before=before)
                act=choice.get("action");reason=choice.get("status")
                if go.request("snapshot").get("updates")!=1664:
                    raise ValueError("MG15_FROZEN_GO_CHOSE_AND_LEARNED")
            elif role=="yggdrasil_r17_frozen":
                ygg=MotionCells.restore(trained["ygg"])
                if ygg.samples!=1664:raise ValueError("MG15_YGG_ORIGINAL_SOURCE_FIT_NOT_RESTORED")
                fresh_public_adapter=owner.DoorKeyPublicAdapter()
                fresh_public_adapter.reset_public(before)
                ygg.start_session(fresh_public_adapter,"mg15-frozen-original-source",live=True)
                option=ygg.choose(before)
                act=option["action"];reason=option["status"]
                if ygg.samples!=1664:raise ValueError("MG15_YGG_FROZEN_CHOOSE_UPDATED")
            elif role=="conventional_successor_frozen":
                classical=ConventionalSuccessor.restore(trained["conventional"])
                if classical.samples!=1664:
                    raise ValueError("MG15_CLASSICAL_ORIGINAL_SOURCE_FIT_NOT_RESTORED")
                classical.begin_episode()
                act=classical.choose(before);reason="FROZEN_CLASSICAL_SOURCE_FIT"
                if classical.samples!=1664:
                    raise ValueError("MG15_CLASSICAL_FROZEN_CHOOSE_UPDATED")
            else:
                raise ValueError("MG15_FROZEN_ROLE_NOT_REGISTERED")
            if type(act)is not int or act not in range(7):
                raise ValueError("MG15_FROZEN_AGENT_ILLEGAL_CHOICE")
            if adapter.submit(act)!=act:
                raise ValueError("MG15_FROZEN_ORIGINAL_ACTION_REMAP")
            after_raw,reward,term,trunc,_=env.step(act)
            after=source.normalize(collector,owner,after_raw)
            source_receipt=adapter.complete(after,float(reward),bool(term),bool(trunc))
            held=before["image"][3][6][0] in (5,6,7)
            next_held=after["image"][3][6][0] in (5,6,7)
            keyfront=held and before["image"][3][5][0]==4
            item={"step":i+1,"role":role,
                "native_or_control_origin":"FROZEN_ORIGINAL_POST_FIT_SOURCE_NO_ONLINE_AND_NO_EPISODE_MEMORY",
                "selected_reason":reason,"actual_original_source_action":act,
                "public_before":before,"public_after":after,
                "original_public_before_sha256":owner.digest(before),
                "original_public_after_sha256":owner.digest(after),
                "source_reward":float(reward),"terminated":bool(term),"truncated":bool(trunc),
                "source_visible_door_opened":bool(source_receipt["visible_door_opened"]),
                "public_pickup":bool(not held and next_held),
                "public_drop":bool(held and not next_held),
                "public_forward_while_held":bool(held and act==2),
                "public_door_front_while_held":bool(keyfront),
                "repeated_before_public_view":bool(any(x["original_public_before_sha256"]==owner.digest(before) for x in events)),
                "external_live_actions":0}
            events.append(item)
            raw=after_raw
            if term or trunc:break
        if go is not None:
            ack=go.request("load",state=base64.b64encode(trained["go"]).decode("ascii"))
            if ack.get("updates")!=1664 or ack.get("live",0)!=0 or go.snapshot()!=trained["go"]:
                raise ValueError("MG15_GO_FROZEN_FIT_CHECKPOINT_CHANGED")
            checkpoint=trained["go"]
        elif role=="yggdrasil_r17_frozen":
            if MotionCells.restore(trained["ygg"]).checkpoint()!=trained["ygg"]:
                raise ValueError("MG15_YGG_FROZEN_FIT_CHECKPOINT_CHANGED")
            checkpoint=trained["ygg"]
        else:
            if ConventionalSuccessor.restore(trained["conventional"]).checkpoint()!=trained["conventional"]:
                raise ValueError("MG15_CLASSICAL_FROZEN_FIT_CHECKPOINT_CHANGED")
            checkpoint=trained["conventional"]
        seen={e["original_public_before_sha256"] for e in events}
        return {"role":role,"seed_evaluator_only":seed,
            "original_start_public_sha256":original_start_sha,
            "original_live_selected_steps":len(events),
            "external_actions":0,
            "source_key_pickups":sum(x["public_pickup"] for x in events),
            "source_key_drops":sum(x["public_drop"] for x in events),
            "forward_while_held":sum(x["public_forward_while_held"] for x in events),
            "front_door_while_held":sum(x["public_door_front_while_held"] for x in events),
            "source_visible_door_openings":sum(x["source_visible_door_opened"] for x in events),
            "source_goal_rewards":sum(x["source_reward"]>0 for x in events),
            "distinct_public_views":len(seen),
            "distinct_action_ids":len({e["actual_original_source_action"] for e in events}),
            "same_heading_scene_change_count":sum(
                e["public_before"]["direction"]==e["public_after"]["direction"]
                and e["public_before"]["image"]!=e["public_after"]["image"] for e in events),
            "heading_change_count":sum(e["public_before"]["direction"]!=e["public_after"]["direction"] for e in events),
            "cold_checkpoint_sha256":sha(checkpoint),
            "frozen_original_fit_samples_unchanged":1664,
            "real_source_events":events}
    finally:
        env.close()
        if go is not None:go.close()

def run(binary,p):
    options=parent_protocol(p)
    trained=parent.fit(binary,options)
    rows=[]
    mapping={"wingless_go_dk13":"wingless_go_dk13_online",
             "yggdrasil_r17":"yggdrasil_r17_online",
             "conventional_public_successor":"conventional_successor_online",
             "conventional_seeded_random":"conventional_seeded_random"}
    resources=[]
    for seed in SEEDS:
        batch=[]
        for role in ROLES:
            if role.endswith("_frozen"):
                row=frozen_episode(role,seed,trained,binary,options)
            else:
                original_role=next(k for k,v in mapping.items() if v==role)
                row=parent.episode(original_role,seed,trained,binary,options)
                for metric in ("episode_host_wall_s","episode_python_cpu_only_s",
                  "go_child_cpu_included","go_child_cpu_s","go_child_max_rss_kib"):
                    row.pop(metric,None)
                row["role"]=role
            if row["original_live_selected_steps"]!=len(row["real_source_events"]):
                raise ValueError("MG15_ACTUAL_SELECTED_STEP_COUNT_MISMATCH")
            batch.append(row)
        if len(batch)!=7 or len({r["original_start_public_sha256"] for r in batch})!=1:
            raise ValueError("MG15_UNEQUAL_ORIGINAL_SEED_PUBLIC_START")
        rows.extend(batch)
    if len(rows)!=21:
        raise ValueError("MG15_NOT_SEVEN_INDEPENDENT_AUTHENTIC_ROLES")
    summary={}
    fields=("original_live_selected_steps","source_key_pickups","source_key_drops",
            "forward_while_held","front_door_while_held","source_visible_door_openings",
            "source_goal_rewards","distinct_public_views","distinct_action_ids",
            "same_heading_scene_change_count","heading_change_count")
    for role in ROLES:
        group=[r for r in rows if r["role"]==role]
        if len(group)!=3:raise ValueError("MG15_MISSING_ORIGINAL_SOURCE_ROLE")
        summary[role]={key:sum(r[key] for r in group) for key in fields}
        summary[role]["episodes"]=3;summary[role]["external_actions"]=0
    gain={live:summary[live]["source_goal_rewards"]-summary[frozen]["source_goal_rewards"]
          for live,frozen in NATIVE}
    both=all(summary[live]["source_goal_rewards"]>=1 and gain[live]>=1
             for live,_ in NATIVE)
    evidence={"schema":SCHEMA,"original_farama":p["source"]["farama"],
        "original_native_go_head":p["source"]["wingless_DK13"],
        "original_native_ygg_head":p["source"]["ygg_R17"],
        "original_FIT_selected_sha":trained["selected_history_sha256"],
        "original_FIT_samples_per_learner":trained["samples"],
        "original_FIT_cold_checkpoints_sha":trained["checkpoints_sha"],
        "frozen_no_online_and_no_episode_memory_bundled":True,
        "source_original_selected_episode_events":rows,
        "original_source_per_role":summary,
        "live_vs_frozen_native_goal_differences":gain,
        "external_live_selected_actions":0,
        "no_original_native_source_changed":True,
        "zero_oracle_hidden_state_or_manual_stage":True}
    return {"schema":SCHEMA,"classification":POSITIVE if both else NEGATIVE,
        "scientific_first_use":False,"accepted_model_changed":False,
        "FORGE_controller_changed":False,"original_seeds":list(SEEDS),
        "independent_original_episodes":21,"FIT_original_selected_count":1664,
        "live_external_actions":0,"canonical_source_sha":sha(canon(evidence).encode()),
        "canonical_source_evidence":evidence}

def main():
    x=argparse.ArgumentParser()
    x.add_argument("--native-go-dk13",type=Path,required=True)
    x.add_argument("--output",type=Path,required=True)
    args=x.parse_args();start=time.perf_counter();cpu=time.process_time()
    try:result=run(args.native_go_dk13,freeze())
    except Exception as exc:
        result={"schema":SCHEMA,"classification":BLOCKED,"scientific_first_use":False,
          "error_type":type(exc).__name__,"error":str(exc),
          "trace_tail":traceback.format_exc().splitlines()[-16:]}
    result["host_wall_s"]=round(time.perf_counter()-start,6)
    result["host_python_cpu_only_s"]=round(time.process_time()-cpu,6)
    result["host_peak_rss_kib"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("MG15_CLASSIFICATION",result["classification"])
    print("MG15_SOURCE_SHA",result.get("canonical_source_sha","NONE"))
    print("MG15_RESULTS",json.dumps(result.get("canonical_source_evidence",{}).get("original_source_per_role",{}),sort_keys=True))
    print("MG15_NATIVE_ONLINE_VS_FROZEN_GOAL_DELTA",json.dumps(result.get("canonical_source_evidence",{}).get("live_vs_frozen_native_goal_differences",{}),sort_keys=True))
    if result["classification"]==BLOCKED:
        print("MG15_BLOCKER",result.get("error_type"),result.get("error"))
    return int(result["classification"]==BLOCKED)
if __name__=="__main__":raise SystemExit(main())
