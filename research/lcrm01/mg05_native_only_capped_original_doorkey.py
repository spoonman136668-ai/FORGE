#!/usr/bin/env python3
"""MG05: stop on abstention (zero assistance) or spend capped public fallback.

Runs genuine upstream Farama DoorKey. The original native Go DK8, original
Yggdrasil R12/R11 and independently sourced conventional C30 all begin from
exactly the same 1664 selected FIT examples. No action is magically supplied
in the native-only arm. This tests action agency, not learned mission parsing.
"""
import argparse
import base64
import json
from pathlib import Path
import random
import resource
import time
import traceback

from k4r_minigrid_source import canon,sha
from k4u_native_minigrid import WingBridge
import mg03_equal_public_doorkey_live as public_parent
import mg04_public_effect_native_agency as original

HERE=Path(__file__).resolve().parent
PREREG=HERE/"mg05_native_only_assistance_prereg.json"
SCHEMA="itd02.mg05.authentic-doorkey-native-only-budgeted.source-only.v1"
BLOCKED="MG05_SOURCE_INTEGRITY_OR_NATIVE_ONLY_CUSTODY_BLOCKED__NO_SCIENCE"
NEGATIVE="MG05_NATIVE_ONLY_COMPLETE_TASK_NOT_ESTABLISHED__NO_SCIENCE"
POSITIVE="MG05_BOUNDED_NATIVE_ONLY_COMPLETE_TASK_ENGINEERING_POSITIVE__NO_SCIENCE"

def freeze():
    p=json.loads(PREREG.read_text(encoding="utf-8"))
    if (p.get("schema")!="itd02.mg05.real-doorkey-nativeonly-and-capped-external-sourceonly.v1"
        or p["parent"]["head"]!="f4e08d27776248f6f075db6fb93d3f4195bd941c"
        or p["source"]["wingless_dk8_source_blob"]!="01484d331e9df9035be045b31d0e015f1f8652e2"
        or p["protocol"]["external_assistance_cap_per_episode"]!=[0,32,64]
        or p["protocol"]["new_development_seeds"]!=[65301,65303,65307]
        or p["protocol"]["identical_original_selected_source_FIT_training"]!=1664
        or p["protocol"]["roles"]!=list(original.ROLES)
        or p["outcomes"]["no_native_only_goal"]!=NEGATIVE
        or p["outcomes"]["native_only_bounded_positive"]!=POSITIVE):
        raise ValueError("MG05_FROZEN_NATIVE_ONLY_PROTOCOL_NOT_AUTHENTIC")
    return p

def prepare_source(p):
    # Original MG04 exact 1664 selected FIT code, unmodified; only the public
    # evaluation budget changes. No new FIT exemplars or pseudo labels.
    return {"FIT":{"seeds":p["protocol"]["selected_source_FIT_seeds"],
                   "cap":256,
                   "observations":p["protocol"]["identical_original_selected_source_FIT_training"]}}

def episode(role,seed,seed_index,cap,trained,go_binary,p):
    gym,owner,Cell,select,collector,conv=original.get_modules()
    env=gym.make("MiniGrid-DoorKey-8x8-v0")
    adapter=owner.DoorKeyPublicAdapter()
    wing=None;native=None;baseline=None
    rng=random.Random(93617+7919*seed_index+999)
    try:
        raw,_=env.reset(seed=seed)
        first_public=public_parent.normalize(collector,owner,raw)
        first_sha=owner.digest(first_public)
        adapter.reset_public(first_public)
        if role=="wingless_go_dk8":
            wing=WingBridge(go_binary)
            ack=wing.request("load",state=base64.b64encode(trained["native_go"]).decode("ascii"))
            if ack.get("updates",0)!=trained["samples"] or ack.get("live",0)!=0:
                raise ValueError("MG05_GO_FIT_RESTORE_INVALID")
            wing.request("begin_episode")
        elif role=="yggdrasil_r12_on_r11":
            native=Cell.restore(trained["native_ygg"])
            if native.samples!=trained["samples"]:
                raise ValueError("MG05_YGG_FIT_RESTORE_INVALID")
            native.start_session(adapter,"mg05-"+str(seed)+"-cap"+str(cap))
        elif role=="conventional_public_categorical":
            baseline=conv.Control.restore(trained["conventional"])
            if baseline.samples!=trained["samples"]:
                raise ValueError("MG05_CONVENTIONAL_FIT_RESTORE_INVALID")
        else:
            raise ValueError("MG05_ROLE_NOT_REGISTERED")

        steps=[];proposals=abstentions=external=goals=0
        actual_key=actual_door=own_key=own_door=0
        key_seen=False;door_after_key=False
        complete_chain=False
        stop="max_episode_actions"
        for i in range(p["protocol"]["live_max_real_steps_per_episode"]):
            before=public_parent.normalize(collector,owner,raw)
            if adapter.current!=before:
                raise ValueError("MG05_NOT_ACTUAL_ORIGINAL_PUBLIC_STATE")
            obj=original.objective(owner,before)
            if obj not in ("carrying_changed","visible_door_state_changed"):
                raise ValueError("MG05_EXTERNAL_OBJECTIVE_UNDECLARED")
            cues=owner.public_cues(before)
            if wing is not None:
                answer=wing.request("choose",before=before,objective=obj)
            elif native is not None:
                answer=select(native,before,obj)
            else:
                answer=original.conventional_choice(baseline,conv,before,obj)
            proposed=answer.get("action")
            proposal_status=answer.get("status")
            if proposed is None:
                if proposal_status!="ABSTAIN_NO_LEARNED_POSITIVE_ACTION":
                    raise ValueError("MG05_UNTRUSTED_ABSTENTION")
                abstentions+=1
                if external>=cap:
                    stop=("native_only_abstained_before_env_step" if cap==0
                          else "external_budget_exhausted_before_env_step")
                    break
                # Only assisted arms may query the fixed original, handcoded
                # source-public collector. Never call it in native-only.
                action=collector.policy({"image":before["image"],"cues":cues},
                                         rng,i,{})
                external+=1
                origin="handcoded_public_collector_budgeted"
            else:
                if (proposal_status!="SELECT_LEARNED_PUBLIC_ACTION" or
                    type(proposed) is not int or proposed not in range(7)):
                    raise ValueError("MG05_INVALID_LEARNED_ACTION_SOURCE")
                proposals+=1
                action=proposed
                origin="model_selected_original_public_effect"
            if type(action)is not int or action not in range(7):
                raise ValueError("MG05_EXECUTED_ACTION_NOT_ORIGINAL_SEVEN")
            if wing is not None:
                ack=wing.request("commit",before=before,action=action)
                if ack.get("updates",0)!=trained["samples"]+i:
                    raise ValueError("MG05_GO_ACTUAL_COMMIT_PROVENANCE")
            if adapter.submit(action)!=action:
                raise ValueError("MG05_UNEXPECTED_ORIGINAL_ACTION_REMAP")
            # Exactly one authenticated source transition, no reward lookup
            # for any other action, and no leak of the common source seed.
            next_raw,reward,terminated,truncated,_=env.step(action)
            after=public_parent.normalize(collector,owner,next_raw)
            event=adapter.complete(after,float(reward),bool(terminated),bool(truncated))
            if wing is not None:
                receipt=wing.request("feedback",before=before,action=action,
                    after=after,reward=float(reward),terminal=bool(terminated or truncated))
                n=receipt.get("live",0)
                if n!=i+1 or receipt.get("updates",0)!=trained["samples"]+i+1:
                    raise ValueError("MG05_GO_NATIVE_SELECTED_FEEDBACK_MISCOUNT")
            elif native is not None:
                rec=native.learn_selected(adapter)
                n=native.samples-trained["samples"]
                if n!=i+1 or rec["sample_index"]!=trained["samples"]+i+1:
                    raise ValueError("MG05_YGG_ORIGINAL_SELECTED_FEEDBACK_MISCOUNT")
            else:
                baseline.learn(event)
                n=baseline.samples-trained["samples"]
                if n!=i+1:
                    raise ValueError("MG05_CONVENTIONAL_ORIGINAL_SELECTED_FEEDBACK_MISCOUNT")
            carry=event["carried_before"]!=event["carried_after"]
            f0,f1=event["front_before"],event["front_after"]
            visible_door=(f0[0]==4 and f1[0]==4 and f0[2]!=f1[2])
            # Count *actual visible change* and separately original task
            # goal reward: no externally supplied task stage is an answer.
            if carry:
                actual_key+=1
                key_seen=True
                if proposed is not None:own_key+=1
            if visible_door:
                actual_door+=1
                if key_seen:door_after_key=True
                if proposed is not None:own_door+=1
            if float(reward)>0:
                goals+=1
                if key_seen and door_after_key:complete_chain=True
            steps.append({
                "index":i+1,"public_before":before,"public_after":after,
                "external_objective":obj,"native_or_control_proposal":proposed,
                "proposal_status":proposal_status,"action_origin":origin,
                "selected_real_env_action":action,"selected_actual_reward":float(reward),
                "real_public_carrying_changed":bool(carry),
                "real_public_visible_door_changed":bool(visible_door),
                "real_original_goal_reward":float(reward)>0,
                "terminated":bool(terminated),"truncated":bool(truncated),
                "selected_feedback_count":n,
                "external_actions_spent_cumulative":external,
                "source_public_before_sha256":owner.digest(before),
                "source_public_after_sha256":owner.digest(after)
            })
            raw=next_raw
            if terminated or truncated:
                stop="original_env_terminated" if terminated else "original_env_truncated"
                break

        # Native-only abstention is not an error. Zero steps and 0 native
        # choices are a legitimate, highly relevant negative result.
        cp=wing.snapshot() if wing is not None else (
            native.checkpoint() if native is not None else baseline.checkpoint())
        if wing is not None:
            cold=WingBridge(go_binary)
            try:
                receipt=cold.request("load",state=base64.b64encode(cp).decode("ascii"))
                if (receipt.get("updates",0)!=trained["samples"]+len(steps)
                    or receipt.get("live",0)!=len(steps)
                    or cold.snapshot()!=cp):
                    raise ValueError("MG05_GO_NATIVE_COLD_RESTORE_MISMATCH")
            finally:
                cold.close()
        elif native is not None:
            restored=Cell.restore(cp)
            if restored.samples!=trained["samples"]+len(steps) or restored.checkpoint()!=cp:
                raise ValueError("MG05_YGG_COLD_RESTORE_MISMATCH")
        else:
            restored=conv.Control.restore(cp)
            if restored.samples!=trained["samples"]+len(steps) or restored.checkpoint()!=cp:
                raise ValueError("MG05_CONVENTIONAL_COLD_RESTORE_MISMATCH")
        if proposals+external!=len(steps) or external>cap:
            raise ValueError("MG05_ACTION_OR_EXTERNAL_BUDGET_CONSERVATION")
        if cap==0 and (external!=0 or any(s["action_origin"]!="model_selected_original_public_effect" for s in steps)):
            raise ValueError("MG05_NATIVE_ONLY_EXTERNAL_ACTION_CONTAMINATION")
        if complete_chain and not (actual_key and actual_door and goals):
            raise ValueError("MG05_IMPOSSIBLE_COMPLETE_TASK_TRACE")
        return {"role":role,"seed_evaluator_only":seed,
          "allowed_external_budget":cap,"stop_reason":stop,
          "original_public_start_sha256":first_sha,
          "source_public_initial_frame":first_public,
          "original_real_env_steps":len(steps),"native_or_control_actions":proposals,
          "abstention_attempts":abstentions,"external_collector_actions":external,
          "carrying_changes_all_actions":actual_key,
          "visible_door_changes_all_actions":actual_door,
          "carrying_changes_model_selected":own_key,
          "door_changes_model_selected":own_door,
          "original_goal_rewards":goals,
          "ordered_key_door_goal_sequence":complete_chain,
          "native_only_complete_task":bool(complete_chain and external==0 and cap==0),
          "cold_restored_checkpoint_sha256":sha(cp),
          "all_original_env_selected_feedback":steps}
    finally:
        env.close()
        if wing is not None:wing.close()

def run(binary,p):
    original_fit=original.fit(binary,prepare_source(p))
    if original_fit["samples"]!=1664:
        raise ValueError("MG05_DIFFERENT_SOURCE_SELECTED_FIT")
    events=[]
    for seed_index,seed in enumerate(p["protocol"]["new_development_seeds"]):
        for cap in p["protocol"]["external_assistance_cap_per_episode"]:
            trio=[episode(role,seed,seed_index,cap,original_fit,binary,p)
                  for role in original.ROLES]
            if len({rec["original_public_start_sha256"] for rec in trio})!=1:
                raise ValueError("MG05_NOT_SAME_ORIGINAL_PUBLIC_RESET")
            if len({canon(rec["source_public_initial_frame"]) for rec in trio})!=1:
                raise ValueError("MG05_NOT_SAME_EXACT_PUBLIC_FRAME")
            events.extend(trio)
    if len(events)!=27:
        raise ValueError("MG05_INCOMPLETE_NATIVE_ONLY_AND_CAPPED_MATRIX")
    summary={}
    for role in original.ROLES:
        summary[role]={}
        for cap in (0,32,64):
            subset=[x for x in events if x["role"]==role and x["allowed_external_budget"]==cap]
            summary[role][str(cap)]={"episodes":len(subset),
              "original_live_steps":sum(x["original_real_env_steps"] for x in subset),
              "model_selected_steps":sum(x["native_or_control_actions"] for x in subset),
              "external_collector_steps":sum(x["external_collector_actions"] for x in subset),
              "native_abstentions":sum(x["abstention_attempts"] for x in subset),
              "key_carry_changes":sum(x["carrying_changes_all_actions"] for x in subset),
              "visible_door_changes":sum(x["visible_door_changes_all_actions"] for x in subset),
              "goals":sum(x["original_goal_rewards"] for x in subset),
              "ordered_key_door_goal_sequences":sum(x["ordered_key_door_goal_sequence"] for x in subset),
              "native_only_complete_tasks":sum(x["native_only_complete_task"] for x in subset),
              "episode_stop_reasons":{str(x["seed_evaluator_only"]):x["stop_reason"] for x in subset}}
    primary_both=all(summary[role]["0"]["native_only_complete_tasks"]>=1
                     for role in ("wingless_go_dk8","yggdrasil_r12_on_r11"))
    classification=POSITIVE if primary_both else NEGATIVE
    evidence={"schema":SCHEMA,
       "source_parent_sha256":"f4e08d27776248f6f075db6fb93d3f4195bd941c",
       "authentic_original_farama_commit":p["source"]["farama_minigrid"],
       "native_original_source_pins":p["source"],
       "same_initial_1664_selected_fit_sha256":original_fit["source_history_sha256"],
       "fit_selected_actual_action_counts":original_fit["seven_actual_action_counts"],
       "native_and_conventional_fit_checkpoint_sha256":original_fit["checkpoint_sha256"],
       "frozen_equal_source_actor_and_caps":list(original.ROLES),
       "honest_external_budget_per_episode":[0,32,64],
       "source_only_stage_objective_not_learned":True,
       "native_go_dk8_is_not_original_wingless_r8":True,
       "real_original_minigrid_new_seed_events":events,
       "per_actor_per_budget_summary":summary}
    digest=sha(canon(evidence).encode())
    return {"schema":SCHEMA,"classification":classification,
       "scientific_first_use":False,"scientific_acceptance":False,
       "model_or_checkpoint_promoted":False,"FORGE_controller_modified":False,
       "original_go_r8_modified":False,"original_ygg_r12_modified":False,
       "same_source_public_training_per_actor":1664,
       "authenticated_original_episode_count":27,
       "total_real_original_steps":sum(x["original_real_env_steps"] for x in events),
       "native_only_success_both_models":primary_both,
       "canonical_original_selected_actions_sha256":digest,
       "source_only_canonical_evidence":evidence}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--wingless-dk8-go",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    t=time.perf_counter();cpu=time.process_time()
    try:
        result=run(args.wingless_dk8_go,freeze())
    except Exception as e:
        result={"schema":SCHEMA,"classification":BLOCKED,
           "scientific_first_use":False,"error_type":type(e).__name__,"error":str(e),
           "traceback_tail":traceback.format_exc().splitlines()[-14:]}
    result["host_wall_seconds"]=round(time.perf_counter()-t,5)
    result["host_cpu_seconds"]=round(time.process_time()-cpu,5)
    result["host_rss_peak_kib"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("MG05_CLASSIFICATION",result["classification"])
    print("MG05_CANONICAL_SOURCE_SHA",result.get("canonical_original_selected_actions_sha256","NONE"))
    print("MG05_SOURCE_RESULTS",json.dumps(
         result.get("source_only_canonical_evidence",{}).get("per_actor_per_budget_summary",{}),
         sort_keys=True))
    if result["classification"]==BLOCKED:
        print("MG05_BLOCKER",result.get("error_type"),result.get("error"))
    return 1 if result["classification"]==BLOCKED else 0

if __name__=="__main__":
    raise SystemExit(main())
