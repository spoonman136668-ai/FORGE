"""AC-19 source-faithful eight-bit typed bridge to original Ygg local predictor.

Historical original LocalTaskRuntime + NativeRingMemoryDev run unchanged.
Neither original source values nor historical original bridge are patched.
No additional original DTR episodes, no online acting, no protected science.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import time
import ac15_native_public_adapter as ac15
import ac18_original_ring_dtr as ac18

SCHEMA="forge.ac19.typed-public-terminal-native-local-control.v1"
RUNTIME_BLOB="68a1423e0bd7206af511212c14b6ce8534154cc2"
N=8

def digest(data):
    return hashlib.sha256(data).hexdigest()

def _bit(value,name):
    if type(value) is not int or value not in (0,1):
        raise ValueError("AC19_INVALID_PUBLIC_BINARY_"+name)
    return value

def encode_before(stage,obs,action):
    stage=_bit(stage,"STAGE")
    obs=_bit(obs,"OBS")
    action=_bit(action,"ACTION")
    values=[0]*N
    values[2*stage+obs]=1
    values[4+action]=1
    return values

def decode_before(bits):
    if (type(bits) is not list or len(bits)!=N or
        any(type(x) is not int or x not in (0,1) for x in bits) or
        sum(bits[:4])!=1 or sum(bits[4:6])!=1 or bits[6:]!=[0,0]):
        raise ValueError("AC19_INVALID_TYPED_BEFORE_BITS")
    context=bits[:4].index(1)
    return context//2,context%2,bits[4:6].index(1)

def encode_after(next_observation,terminated,reward):
    if type(terminated) is not bool:
        raise ValueError("AC19_INVALID_PUBLIC_TERMINAL")
    reward=_bit(reward,"REWARD")
    if terminated:
        if next_observation is not None:
            raise ValueError("AC19_TERMINAL_SUCCESSOR_MUST_REMAIN_NULL")
        context=2
    else:
        context=_bit(next_observation,"SUCCESSOR")
    bits=[0]*N
    bits[context]=1
    bits[3]=int(terminated)
    bits[4+reward]=1
    return bits

def decode_after(bits):
    if (type(bits) is not list or len(bits)!=N or
        any(type(x) is not int or x not in (0,1) for x in bits) or
        sum(bits[:3])!=1 or sum(bits[4:6])!=1 or bits[6:]!=[0,0]):
        raise ValueError("AC19_INVALID_TYPED_OUTCOME_BITS")
    index=bits[:3].index(1)
    terminal=bool(bits[3])
    if (index==2)!=terminal:
        raise ValueError("AC19_TERMINAL_MASK_AND_NULL_INCONSISTENT")
    return (None if terminal else index),terminal,bits[4:6].index(1)

def source_event_to_bits(event):
    if type(event) is not dict or set(event)!=ac15.FIELDS:
        raise ValueError("AC19_NOT_SOURCE_PUBLIC_EIGHT_FIELD_EVENT")
    stage,obs,arm=event["stage"],event["observation"],event["action"]
    terminal=event["terminated"]
    if stage==0:
        if terminal is not False or event["reward"]!=0:
            raise ValueError("AC19_SOURCE_STAGE0_SEMANTIC_DRIFT")
    elif stage==1:
        if terminal is not True:
            raise ValueError("AC19_SOURCE_STAGE1_NOT_TERMINAL")
    else:
        raise ValueError("AC19_SOURCE_STAGE_DRIFT")
    before=encode_before(stage,obs,arm)
    after=encode_after(event["next_observation"],terminal,event["reward"])
    if decode_before(before)!=(stage,obs,arm):
        raise RuntimeError("AC19_BEFORE_NOT_LOSSLESS")
    if decode_after(after)!=(event["next_observation"],terminal,event["reward"]):
        raise RuntimeError("AC19_AFTER_NOT_LOSSLESS")
    return before,after

def verify_native(ygg):
    native,bridge=ac18.original_native(ygg)
    if ac18.ac10.git(ygg,"hash-object","--","yggdrasil/task_runtime.py")!=RUNTIME_BLOB:
        raise RuntimeError("AC19_ORIGINAL_LOCAL_TASK_RUNTIME_BLOB_DRIFT")
    from yggdrasil.task_runtime import LocalTaskRuntime,LocalCountControl
    if (LocalTaskRuntime.__module__!="yggdrasil.task_runtime" or
        LocalCountControl.__module__!="yggdrasil.task_runtime"):
        raise RuntimeError("AC19_NATIVE_RUNTIME_OR_CONTROL_SOURCE_CHANGED")
    refusal=ac18.bridge_direct_admission(bridge)
    return native,LocalTaskRuntime,LocalCountControl,refusal

def native_identity(model):
    return digest(json.dumps({
        "genome":model.core.genome,
        "roles":model.core.roles,
        "neighbors":model.neighbors
    },sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8"))

def metrics(scores,labels):
    if len(scores)!=len(labels) or not scores:
        raise RuntimeError("AC19_EMPTY_OR_MISALIGNED_REAL_DEV")
    if any(not math.isfinite(p) or not 0<=p<=1 for p in scores):
        raise RuntimeError("AC19_INVALID_NATIVE_REWARD_PROBABILITY")
    return {
        "total":len(labels),
        "correct":sum((p>=.5)==bool(y) for p,y in zip(scores,labels)),
        "brier":sum((p-y)**2 for p,y in zip(scores,labels))/len(labels)
    }

def ensure_exhaustive_roundtrips():
    all_before=set()
    for s in range(2):
        for o in range(2):
            for a in range(2):
                b=encode_before(s,o,a)
                assert decode_before(b)==(s,o,a)
                all_before.add(tuple(b))
    all_after=set()
    for successor,terminal in ((0,False),(1,False),(None,True)):
        for reward in (0,1):
            b=encode_after(successor,terminal,reward)
            assert decode_after(b)==(successor,terminal,reward)
            all_after.add(tuple(b))
    if len(all_before)!=8 or len(all_after)!=6:
        raise RuntimeError("AC19_TYPED_SOURCE_COLLISION")
    return {"unique_input_vectors":8,"unique_output_vectors":6,
            "terminal_none_representation_distinct":True,
            "actual_reward_1_representation_distinct":True}

def run(ygg:Path,ac15_path:Path,ac18_path:Path,out:Path):
    native,Runtime,LocalCountControl,refusal=verify_native(ygg)
    parent15=json.loads(ac15_path.read_text(encoding="utf-8"))
    parent18=json.loads(ac18_path.read_text(encoding="utf-8"))
    fit,dev=ac18.exact_source(parent15)
    if (parent18.get("schema")!=ac18.SCHEMA or
        parent18.get("upstream_original_commit")!=parent15["upstream_sha"] or
        parent18.get("historical_ygg_original_commit")!=ac18.YGG_COMMIT or
        parent18.get("new_source_owned_episodes")!=0 or
        parent18.get("original_fit_reward_updates")!=16 or
        parent18.get("full_native_task_bridge_admission",{}).get("full_native_runtime_admission")!="NO_GO_PUBLIC_TYPE_MISMATCH" or
        parent18.get("scientific_first_use") is not False or
        parent18.get("ygg_native_repo_edited") is not False):
        raise RuntimeError("AC19_PARENT_AC18_AUTHENTIC_NEGATIVE_UNQUALIFIED")
    inversion=ensure_exhaustive_roundtrips()
    fitted=Runtime()
    count=LocalCountControl(fitted.neighbors)
    ring=native.NativeRingMemoryDev()
    initial_native=native_identity(fitted)
    initial_ring=ring.parameter_sha256()
    fit_start=time.perf_counter_ns()
    fitted_stage_events=0
    for episode in fit["episodes"]:
        ring.reset_episode()
        for event in episode["events"]:
            bits,outcomes=source_event_to_bits(event)
            # Original cell learner and conventional count learner receive
            # exactly the same source-owned before/outcome 8-bit pairs.
            fitted.observe(bits,outcomes)
            count.observe(bits,outcomes)
            ring.advance(ac18.obs_name(event))
            ring.feedback(ac18.action_name(event),event["reward"],
                          learning=True,terminal=event["terminated"])
            fitted_stage_events+=1
    fit_wall=time.perf_counter_ns()-fit_start
    if fitted_stage_events!=16 or ring.updates!=16 or fitted.core.events!=16:
        raise RuntimeError("AC19_ORIGINAL_NATIVE_FIT_UPDATES_UNEXPECTED")
    native_before_dev=native_identity(fitted)
    ring_before_dev=ring.parameter_sha256()
    if initial_native==native_before_dev or initial_ring==ring_before_dev:
        raise RuntimeError("AC19_NATIVE_LOCAL_LEARNING_DID_NOT_UPDATE")
    native_checkpoint=fitted.snapshot()
    ring_checkpoint=ring.checkpoint()
    cold_native=Runtime.restore(native_checkpoint)
    cold_ring=native.NativeRingMemoryDev.restore(ring_checkpoint)
    if (native_identity(cold_native)!=native_before_dev or
        cold_ring.parameter_sha256()!=ring_before_dev):
        raise RuntimeError("AC19_ORIGINAL_NATIVE_COLD_RESTORE_MISMATCH")
    ring.start_frozen_evaluation(ring_before_dev)
    cold_ring.start_frozen_evaluation(ring_before_dev)
    controls=ac18.same_information_controls(fit["episodes"],dev["episodes"])
    dev_rows=[]
    for i,episode in enumerate(dev["episodes"]):
        ring.reset_episode()
        cold_ring.reset_episode()
        for event in episode["events"]:
            bits,targets=source_event_to_bits(event)
            native_p=fitted.predict(bits)
            restored_p=cold_native.predict(bits)
            tab_p=count.predict(bits)
            if len(native_p)!=8 or len(tab_p)!=8 or native_p!=restored_p:
                raise RuntimeError("AC19_ORIGINAL_CELL_PREDICTIONS_COLD_DRIFT")
            ring.advance(ac18.obs_name(event))
            cold_ring.advance(ac18.obs_name(event))
            ring_q=ring.q_values()
            cold_q=cold_ring.q_values()
            if ring_q!=cold_q:
                raise RuntimeError("AC19_ORIGINAL_RING_COLD_Q_DRIFT")
            native_reward_prob=float(native_p[5])
            tabular_reward_prob=float(tab_p[5])
            if not (0<=native_reward_prob<=1 and 0<=tabular_reward_prob<=1):
                raise RuntimeError("AC19_LOCAL_SOURCE_REWARD_SCORE_NOT_PROBABILITY")
            # Never actuate predicted action. Preserve exact observed reward.
            ring.feedback(ac18.action_name(event),event["reward"],
                          learning=False,terminal=event["terminated"])
            cold_ring.feedback(ac18.action_name(event),event["reward"],
                               learning=False,terminal=event["terminated"])
            dev_rows.append({
                "seed":episode["seed"],"stage":event["stage"],
                "actual_observed_public_reward":event["reward"],
                "actual_observed_public_successor":event["next_observation"],
                "actual_terminal":event["terminated"],
                "original_native_reward1_probability":native_reward_prob,
                "original_equal_information_local_count_probability":tabular_reward_prob,
                "original_ring_q_for_source_action":ring_q[event["action"]],
                "native_input_bits":bits,"native_output_target_bits":targets,
                "native_reward1_target_bit":targets[5]
            })
    if (native_identity(fitted)!=native_before_dev or
        ring.parameter_sha256()!=ring_before_dev or
        fitted.core.events!=16 or ring.updates!=16):
        raise RuntimeError("AC19_DEV_WEIGHT_OR_EVENT_MUTATION")
    terminal=[r for r in dev_rows if r["stage"]==1]
    if len(terminal)!=4 or [r["actual_observed_public_reward"] for r in terminal]!=[
        e["events"][1]["reward"] for e in dev["episodes"]]:
        raise RuntimeError("AC19_DEV_TERMINAL_SOURCE_DATA_CHANGED")
    labels=[r["actual_observed_public_reward"] for r in terminal]
    native_score=metrics([r["original_native_reward1_probability"] for r in terminal],labels)
    native_count_score=metrics([r["original_equal_information_local_count_probability"] for r in terminal],labels)
    conventional={}
    for name,key in (("contextual_history_tabular","fitted_tabular_probability"),
                     ("acting_ema","fitted_acting_ema_probability"),
                     ("pooled_fit_prior","pooled_fit_probability")):
        conventional[name]=metrics([r[key] for r in controls],labels)
    restored_native=Runtime.restore(native_checkpoint)
    restored_ring=native.NativeRingMemoryDev.restore(ring_checkpoint)
    if (native_identity(restored_native)!=native_before_dev or
        restored_ring.checkpoint()!=ring_checkpoint):
        raise RuntimeError("AC19_NATIVE_CHECKPOINT_POST_DEV_RESTORE_DRIFT")
    verify_native(ygg)
    result={
        "schema":SCHEMA,"scope":"EXTERNAL_TYPED_ADAPTER_HISTORICAL_NATIVE_DEVELOPMENT_ONLY",
        "upstream_original_commit":parent15["upstream_sha"],
        "historical_ygg_commit":ac18.YGG_COMMIT,
        "original_local_task_runtime_blob":RUNTIME_BLOB,
        "original_ring_memory_blob":ac18.RING_BLOB,
        "source_fit_episodes_reused":8,"source_dev_episodes_reused":4,
        "new_source_owned_episodes":0,
        "lossless_public_binary_encoding":inversion,
        "terminal_null_encoded_without_forged_observation":True,
        "original_reward_1_preserved":True,
        "original_native_bridge_remains_incompatible":refusal,
        "fit_public_stage_transitions":fitted_stage_events,
        "original_local_task_runtime_fitted_events":fitted.core.events,
        "original_ring_memory_fitted_updates":ring.updates,
        "fit_wall_ns":fit_wall,
        "native_original_parameter_sha_before_fit":initial_native,
        "native_original_parameter_sha_after_fit":native_before_dev,
        "ring_original_parameter_sha_before_fit":initial_ring,
        "ring_original_parameter_sha_after_fit":ring_before_dev,
        "native_original_checkpoint_bytes":len(native_checkpoint.encode("utf-8")),
        "ring_original_checkpoint_bytes":len(ring_checkpoint),
        "native_original_checkpoint_sha256":digest(native_checkpoint.encode("utf-8")),
        "ring_original_checkpoint_sha256":digest(ring_checkpoint),
        "original_native_and_ring_checkpoint_restored":True,
        "dev_public_source_records":dev_rows,
        "native_local_runtime_dev_terminal_metric":native_score,
        "equal_information_original_local_count_control_metric":native_count_score,
        "additional_fitted_source_controls":conventional,
        "dev_native_optimizer_updates":0,
        "dev_ring_reward_updates":0,
        "native_beats_all_controls":all(native_score["brier"]<m["brier"] for m in
            [native_count_score,*conventional.values()]),
        "true_on_policy_return_measured":False,
        "live_native_actions_executed":False,
        "original_native_bridge_replaced_in_production":False,
        "current_ygg_native_branch_modified":False,
        "historical_ygg_source_modified":False,
        "new_original_source_calls":0,
        "scientific_first_use":False,
        "scientific_admission":False,
        "controller_or_queue_modified":False
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--ygg",type=Path,required=True)
    p.add_argument("--ac15-report",type=Path,required=True)
    p.add_argument("--ac18-report",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    r=run(a.ygg,a.ac15_report,a.ac18_report,a.out)
    print("AC19_LOSSLESS_TERMINAL_REWARD_COMPATIBILITY=PASS")
    print("AC19_ACTUAL_NATIVE_LOCAL_TASK_FIT="+str(r["fit_public_stage_transitions"]))
    print("AC19_NATIVE_DEV_BRIER="+str(r["native_local_runtime_dev_terminal_metric"]["brier"]))
    print("AC19_FITTED_LOCAL_COUNT_DEV_BRIER="+str(r["equal_information_original_local_count_control_metric"]["brier"]))
    print("AC19_EXISTING_BRIDGE_INCOMPATIBLE=TRUE")
    print("AC19_SCIENCE_ADMISSION=NO")
