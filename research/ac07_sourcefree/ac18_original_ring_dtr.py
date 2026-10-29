"""AC-18 authentic DTR public records -> unchanged Ygg eight-cell ring.

Historical development-only NativeRingMemoryDev; NOT current active Ygg or
LocalTaskRuntime, not protected science, no new source-owned episodes.
Original full native bridge refuses DTR reward 1 and terminal None.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import importlib
import json
import math
from pathlib import Path
import sys
import time
import tracemalloc
import ac10_upstream_contract as ac10
import ac15_native_public_adapter as ac15

SCHEMA="forge.ac18.authentic-dtr-historical-eight-cell-dev.v1"
YGG_COMMIT="a39171a76d0d7817e3563682bb139a9d7ecf37c4"
RING_PATH="yggdrasil/itd02_local_ring_memory_dev.py"
RING_BLOB="1db0835d5c99456bcf99a013d4836f49314a9d39"
BRIDGE_PATH="yggdrasil/itd02_native_task_bridge_dev.py"
BRIDGE_BLOB="b311ea7ea00c15d23e7bd43ff97bd10ce3d8b87c"
CURRENT_ACTIVE_YGG="92c421a5475a27015a390efb88c373eb5f15379d"
OBS0=("LRV","MRV")
OBS1=("docked_MRV","docked_LRV")
ACTIONS=("TurnAround","GoForward")
EMA_ALPHA=0.5
A_B_A=(760000,760001,760004)

def digest(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def original_native(root:Path):
    root=root.resolve(strict=True)
    if ac10.git(root,"rev-parse","HEAD")!=YGG_COMMIT:
        raise RuntimeError("AC18_HISTORICAL_NATIVE_COMMIT_DRIFT")
    for path,sha in ((RING_PATH,RING_BLOB),(BRIDGE_PATH,BRIDGE_BLOB)):
        f=root/path
        if not f.is_file() or f.is_symlink() or not f.resolve().is_relative_to(root):
            raise RuntimeError("AC18_NATIVE_FILE_UNSAFE:"+path)
        if ac10.git(root,"hash-object","--",path)!=sha:
            raise RuntimeError("AC18_HISTORICAL_NATIVE_BLOB_DRIFT:"+path)
    if ac10.git(root,"status","--porcelain","--untracked-files=no"):
        raise RuntimeError("AC18_NATIVE_SOURCE_WORKTREE_CHANGED")
    if str(root) not in sys.path:
        sys.path.insert(0,str(root))
    native=importlib.import_module("yggdrasil.itd02_local_ring_memory_dev")
    bridge=importlib.import_module("yggdrasil.itd02_native_task_bridge_dev")
    if (native.CELLS!=8 or native.ROUNDS!=2 or
        native.OBSERVATIONS!=( "LRV","MRV","docked_MRV","Nothing","docked_LRV") or
        native.ACTIONS!=("TurnAround","GoForward","Backup") or
        bridge.REWARDS!=(-3,0,10)):
        raise RuntimeError("AC18_NATIVE_SOURCE_INTERFACE_DRIFT")
    return native,bridge

def bridge_direct_admission(bridge):
    try:
        bridge.public_outcome("docked_LRV",1)
    except ValueError:
        reject_reward=True
    else:
        raise RuntimeError("AC18_NATIVE_BRIDGE_ACCEPTED_FORGED_REWARD")
    try:
        bridge.public_outcome(None,0)
    except ValueError:
        reject_terminal=True
    else:
        raise RuntimeError("AC18_NATIVE_BRIDGE_ACCEPTED_FORGED_SUCCESSOR")
    return {"source_terminal_reward_one_accepted":False,
            "source_terminal_successor_none_accepted":False,
            "actual_original_bridge_tested":True,
            "source_action_projection_is_complete":False,
            "full_native_runtime_admission":"NO_GO_PUBLIC_TYPE_MISMATCH"}

def episode_context(episode):
    e0,e1=episode["events"]
    return (e0["observation"],e1["observation"],e1["action"])

def obs_name(event):
    return (OBS0 if event["stage"]==0 else OBS1)[event["observation"]]

def action_name(event):
    return ACTIONS[event["action"]]

def exact_source(doc):
    if (doc.get("schema")!=ac15.SCHEMA or
        doc.get("scope")!="AUTHENTIC_PUBLIC_DEVELOPMENT_LEARNER_CONTROL_ONLY" or
        doc.get("upstream_sha")!=ac10.SOURCE_COMMIT or
        doc.get("upstream_tree_sha")!=ac10.SOURCE_TREE or
        doc.get("existing_ygg_commit")!=ac15.YGG_COMMIT or
        doc.get("fit_observed_action_outcome_updates")!=16 or
        doc.get("dev_updates")!=0 or
        doc.get("scientific_first_use") is not False or
        doc.get("protected_science_family_used") is not False or
        doc.get("native_wingless_or_yggdrasil_source_modified") is not False):
        raise RuntimeError("AC18_PARENT_REAL_ORIGINAL_SOURCE_EVIDENCE_INVALID")
    fit=doc.get("source_fit");dev=doc.get("source_dev")
    ac15.validate_source(fit,"FIT")
    ac15.validate_source(dev,"DEV")
    return fit,dev

def same_information_controls(fit,dev):
    rewards=[int(row["events"][1]["reward"]) for row in fit]
    prior=sum(rewards)/len(rewards)
    table=defaultdict(lambda:[0,0])
    ema={}
    for episode,reward in zip(fit,rewards):
        key=episode_context(episode)
        table[key][reward]+=1
        ema[key]=EMA_ALPHA*reward+(1-EMA_ALPHA)*ema.get(key,prior)
    records=[]
    for episode in dev:
        key=episode_context(episode)
        c=table.get(key,[0,0])
        n=sum(c)
        records.append({
            "seed":episode["seed"],"public_history_action":list(key),
            "actual_terminal_source_reward":episode["events"][1]["reward"],
            "fitted_tabular_probability":(1+c[1])/(2+n) if n else prior,
            "fitted_acting_ema_probability":ema.get(key,prior),
            "pooled_fit_probability":prior,
            "fit_context_support":n})
    return records

def score(prob,truth):
    return {"count":len(truth),
            "correct_at_half":sum(int(p>=.5)==y for p,y in zip(prob,truth)),
            "brier":sum((p-y)**2 for p,y in zip(prob,truth))/len(truth)}

def frozen_walk(model,episode,*,record_features=False):
    # Only the documented source-public tuple reaches the original memory.
    model.reset_episode()
    records=[]
    for event in episode["events"]:
        model.advance(obs_name(event))
        original_q=model.q_values()
        chosen=model.choose()
        a=action_name(event)
        predicted=original_q[model_action_index(a)]
        features=None
        if record_features:
            now,hist=model._signals()
            site=model_action_site(a)
            features=[1.0,now[site],16.0*hist[site]]
        records.append({
            "stage":event["stage"],"public_obs":event["observation"],
            "source_action":event["action"],"source_reward":event["reward"],
            "raw_native_q_for_source_action":predicted,
            "clipped_native_reward_proxy":min(1.0,max(0.0,predicted)),
            "native_chosen_action":chosen,
            "native_chosen_action_illegal_for_dtr":chosen=="Backup",
            "local_action_features":features})
        model.feedback(a,event["reward"],learning=False,
                       terminal=event["terminated"])
    if model.pending:
        raise RuntimeError("AC18_FROZEN_EPISODE_DID_NOT_TERMINATE")
    return records

def model_action_index(a):
    return ACTIONS.index(a)

def model_action_site(a):
    return (0,2)[ACTIONS.index(a)]

def local_collisions(fit_rows):
    grouped=defaultdict(list)
    for episode in fit_rows:
        for record in episode["records"]:
            x=record["local_action_features"]
            if x is None:raise RuntimeError("AC18_MISSING_NATIVE_LOCAL_FEATURES")
            key=(record["stage"],record["source_action"],
                 tuple(round(v,12) for v in x))
            grouped[key].append((record["source_reward"],episode["seed"],
                                 record["public_obs"]))
    mixed=[]
    for key,values in sorted(grouped.items()):
        if len({x[0] for x in values})>1:
            mixed.append({
                "stage":key[0],"source_action":key[1],
                "native_action_features":list(key[2]),
                "conflicting_original_source_rewards":sorted({v[0] for v in values}),
                "source_seeds":[v[1] for v in values],
                "source_public_observed_bits":[v[2] for v in values]})
    return {"distinct_native_local_action_feature_groups":len(grouped),
            "groups_with_source_reward_conflict":len(mixed),
            "conflicting_groups":mixed,
            "no_proof_of_global_original_causal_nonidentifiability":True}

def run(ygg:Path,ac15_file:Path,out:Path):
    native,bridge=original_native(ygg)
    refusal=bridge_direct_admission(bridge)
    parent=json.loads(ac15_file.read_text(encoding="utf-8"))
    fit,dev=exact_source(parent)
    if len(fit["episodes"])!=8 or len(dev["episodes"])!=4:
        raise RuntimeError("AC18_PUBLIC_SOURCE_EPISODE_COUNT_DRIFT")
    labels=[row["events"][1]["reward"] for row in fit["episodes"]]
    if set(labels)!={0,1}:
        raise RuntimeError("AC18_PUBLIC_TERMINAL_REWARD_CLASS_COLLAPSE")
    controls=same_information_controls(fit["episodes"],dev["episodes"])
    model=native.NativeRingMemoryDev()
    initial=model.parameter_sha256()
    start=time.perf_counter_ns()
    tracemalloc.start()
    fitted=[]
    for episode in fit["episodes"]:
        model.reset_episode()
        for event in episode["events"]:
            model.advance(obs_name(event))
            # Source action is fixed by original recorded policy; choice is
            # never actuated, and forbidden third action stays unrepresented.
            model.feedback(action_name(event),event["reward"],
                           learning=True,terminal=event["terminated"])
        fitted.append(episode["seed"])
    fit_wall=time.perf_counter_ns()-start
    peak=tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    after=model.parameter_sha256()
    if after==initial or model.updates!=16:
        raise RuntimeError("AC18_ORIGINAL_RING_REWARD_FIT_NOT_APPLIED")
    checkpoint=model.checkpoint()
    initial_gates=model.gates[:]
    frozen=model.parameter_sha256()
    model.start_frozen_evaluation(frozen)
    restored=native.NativeRingMemoryDev.restore(checkpoint)
    if restored.parameter_sha256()!=frozen or restored.checkpoint()!=checkpoint:
        raise RuntimeError("AC18_ORIGINAL_RING_COLD_RESTORE_INVALID")
    restored.start_frozen_evaluation(frozen)
    # Snapshot BEFORE DEV used as cold replay: no DEV gradient updates.
    dev_rows=[]
    for episode in dev["episodes"]:
        warm=frozen_walk(model,episode)
        cold=frozen_walk(restored,episode)
        if warm!=cold:
            raise RuntimeError("AC18_RING_COLD_DEV_PARITY_LOST")
        terminal=warm[1]
        dev_rows.append({"seed":episode["seed"],
                         "public_history_action":list(episode_context(episode)),
                         "source_terminal_reward":episode["events"][1]["reward"],
                         "native_terminal_reward_proxy":terminal["clipped_native_reward_proxy"],
                         "native_terminal_raw_q":terminal["raw_native_q_for_source_action"],
                         "native_chosen_action":terminal["native_chosen_action"],
                         "native_chosen_action_illegal_for_dtr":terminal["native_chosen_action_illegal_for_dtr"],
                         "stage_records":warm})
    if model.updates!=16 or restored.updates!=16 or model.parameter_sha256()!=frozen:
        raise RuntimeError("AC18_FROZEN_DEV_UPDATED_ORIGINAL_RING_PARAMETERS")
    replay=[]
    for episode in fit["episodes"]:
        rec=frozen_walk(restored,episode,record_features=True)
        replay.append({"seed":episode["seed"],"records":rec})
    ids={x["seed"]:x for x in replay}
    if any(seed not in ids for seed in A_B_A):
        raise RuntimeError("AC18_AUTHENTIC_RETURN_A_SEED_NOT_PRESENT")
    aba=[{"seed":seed,"history_action":list(
             episode_context(next(e for e in fit["episodes"] if e["seed"]==seed))),
          "terminal_native_q":ids[seed]["records"][1]["raw_native_q_for_source_action"]}
         for seed in A_B_A]
    if aba[0]["history_action"]!=aba[2]["history_action"]:
        raise RuntimeError("AC18_REAL_RETURN_A_PUBLIC_CONTEXT_DRIFT")
    # Frozen source replay has deterministic same A input before/after B.
    if aba[0]["terminal_native_q"]!=aba[2]["terminal_native_q"]:
        raise RuntimeError("AC18_FROZEN_RETURN_A_CHANGED_WITHOUT_LEARNING")
    collisions=local_collisions(replay)
    predictions=[r["native_terminal_reward_proxy"] for r in dev_rows]
    outcome=[r["source_terminal_reward"] for r in dev_rows]
    baseline={}
    for name,key in (("contextual_tabular","fitted_tabular_probability"),
                     ("acting_ema","fitted_acting_ema_probability"),
                     ("pooled_fit_prior","pooled_fit_probability")):
        baseline[name]=score([r[key] for r in controls],outcome)
    native_metric=score(predictions,outcome)
    all_q=[x["raw_native_q_for_source_action"] for row in dev_rows
           for x in row["stage_records"]]
    gate_movement=[float(g-1.0) for g in initial_gates]
    original_native(ygg)
    result={
        "schema":SCHEMA,"scope":"HISTORICAL_EIGHT_CELL_PUBLIC_DEV_ONLY",
        "upstream_original_commit":parent["upstream_sha"],
        "historical_ygg_original_commit":YGG_COMMIT,
        "historical_ring_original_git_blob":RING_BLOB,
        "historical_native_bridge_original_git_blob":BRIDGE_BLOB,
        "current_active_ygg_commit_not_containing_ring":CURRENT_ACTIVE_YGG,
        "full_native_task_bridge_admission":refusal,
        "public_original_fit_episodes_reused":8,
        "public_original_dev_episodes_reused":4,
        "new_source_owned_episodes":0,
        "source_fit_seed_ids":fitted,
        "source_dev_seed_ids":[e["seed"] for e in dev["episodes"]],
        "original_fit_reward_updates":model.updates,
        "original_ring_parameter_sha_before":initial,
        "original_ring_parameter_sha_after":frozen,
        "original_ring_gates_after_fit":model.gates[:],
        "original_ring_gate_delta_from_initial":gate_movement,
        "ring_gates_changed":any(abs(z)>1e-14 for z in gate_movement),
        "ring_checkpoint_bytes":len(checkpoint),
        "ring_checkpoint_sha256":digest(checkpoint),
        "cold_replay_byte_exact":True,
        "fit_wall_ns":fit_wall,
        "fit_python_tracemalloc_peak_bytes":peak,
        "native_ring_neighbor_messages":model.messages,
        "original_native_dev_terminal_score":native_metric,
        "fitted_conventional_controls":baseline,
        "terminal_dev_original_records":dev_rows,
        "terminal_dev_fitted_control_predictions":controls,
        "dev_unseen_context_action_count":sum(r["fit_context_support"]==0 for r in controls),
        "native_predictions_clipped_to_unit_interval":sum(x<0.0 or x>1.0 for x in all_q),
        "native_illegal_third_action_choices_on_dev":sum(r["native_chosen_action_illegal_for_dtr"] for row in dev_rows for r in row["stage_records"]),
        "local_action_signal_aliasing_on_frozen_fit_replay":collisions,
        "source_public_return_a_b_a":aba,
        "return_a_frozen_q_identical":True,
        "return_a_intervening_learning_tested":False,
        "true_source_counterfactual_policy_value_measured":False,
        "independent_cell_local_plasticity_proven":False,
        "native_production_runtime_connected":False,
        "original_dtr_source_edited":False,
        "ygg_native_repo_edited":False,
        "scientific_first_use":False,
        "scientific_admission":False,
        "forge_controller_or_queue_modified":False,
        "dev_fit_updates":0,
        "native_beats_all_fitted_controls":all(native_metric["brier"]<x["brier"] for x in baseline.values())
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--ygg",type=Path,required=True)
    p.add_argument("--ac15-report",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    x=run(a.ygg,a.ac15_report,a.out)
    print("AC18_NATIVE_EIGHT_CELL_ORIGINAL_FIT_UPDATES="+str(x["original_fit_reward_updates"]))
    print("AC18_RING_GATES_MOVED="+str(x["ring_gates_changed"]))
    print("AC18_NATIVE_TERMINAL_BRIER="+str(x["original_native_dev_terminal_score"]["brier"]))
    print("AC18_EMA_TERMINAL_BRIER="+str(x["fitted_conventional_controls"]["acting_ema"]["brier"]))
    print("AC18_FULL_NATIVE_BRIDGE="+x["full_native_task_bridge_admission"]["full_native_runtime_admission"])
    print("AC18_SCIENTIFIC_FIRST_USE=FALSE")
