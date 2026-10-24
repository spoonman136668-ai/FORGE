#!/usr/bin/env python3
"""K4E: prospectively frozen pushing reward-history ablation, public DEV only.

No modified upstream code or K4D rerun. Arm A is the unchanged K4B in-memory
repair; arm B only snapshots/restores the three pushing-task reward fields.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import random
import sys
import traceback

from k4a_control_replay import portable, verify_source, EXPECTED_SOURCE_SHA
from k4c_intervention_pair import PairFailure, rollout
from k4d_crossfamily import varied_target, digest

FROZEN=Path(__file__).with_name("k4e_frozen_reward_ablation.json")
SCHEMA="mass.lcrm01.k4e.pushing-reward-state-ablation-results.v1"
FROZEN_SCHEMA="mass.lcrm01.k4e.frozen-pushing-reward-memory-causal-ablation.v1"
BASE="A_BASELINE_K4B_UNMODIFIED"
REPAIR="B_K4B_PLUS_PUSHING_REWARD_MEMORY_ONLY"

class ExperimentFailure(Exception):
    def __init__(self,phase,step,fields):
        self.phase,self.step,self.fields=phase,step,fields
        super().__init__(phase+":"+str(step)+":"+",".join(fields))

def first_difference(left,right):
    if len(left)!=len(right):
        return {"step":-1,"fields":["length"]}
    for i,(a,b) in enumerate(zip(left,right)):
        changed=sorted(k for k in set(a)|set(b) if a.get(k)!=b.get(k))
        if changed:
            return {"step":i,"fields":changed}
    return None

def cases(frozen):
    d=frozen["preregistered_design"]
    if d["task"]!="pushing" or d["fresh_seeds"]!=[67,79] or d["interventions"]!=[
        {"joint_index":0,"delta_radians":0.04},
        {"joint_index":2,"delta_radians":-0.03}]:
        raise ValueError("FROZEN_CASE_DRIFT")
    return [{"task":"pushing","seed":seed,**joint}
            for seed in d["fresh_seeds"] for joint in d["interventions"]]

def memory_snapshot(task,fields):
    if type(fields) is not list or fields!=[
            "previous_end_effector_positions","previous_object_position",
            "previous_object_orientation"]:
        raise ExperimentFailure("HISTORY_SCHEMA",-1,["fields"])
    result={}
    for name in fields:
        if not hasattr(task,name):
            raise ExperimentFailure("HISTORY_MISSING",-1,[name])
        value=getattr(task,name)
        if value is None:
            raise ExperimentFailure("HISTORY_UNINITIALIZED",-1,[name])
        result[name]=copy.deepcopy(value)
    return result

def memory_restore(task,snapshot):
    for field,value in snapshot.items():
        setattr(task,field,copy.deepcopy(value))
    observed=memory_snapshot(task,list(snapshot))
    if portable(observed)!=portable(snapshot):
        raise ExperimentFailure("HISTORY_RESTORE_FAILED",-1,sorted(snapshot))

def run_arm(np,CausalWorld,generate_task,frozen,spec,arm):
    d=frozen["preregistered_design"]
    if arm not in (BASE,REPAIR):
        raise ExperimentFailure("UNKNOWN_ARM",-1,["arm"])
    env=CausalWorld(
        task=generate_task(task_generator_id="pushing"),
        enable_visualization=False,seed=spec["seed"],
        skip_frame=d["skip_frame"],action_mode=d["action_mode"],
        observation_mode=d["observation_mode"],
        normalize_actions=d["normalize_actions"],
        normalize_observations=d["normalize_observations"],
        max_episode_length=d["max_episode_length"])
    saved=None
    try:
        env.reset()
        action=np.array(env.action_space.low,dtype=np.float64,copy=True)
        for _ in range(d["prefix_steps"]):
            env.step(action)
        checkpoint={
            "world_state":portable(env.get_current_state_variables()),
            "episode_length":int(env._episode_length),
            "control_index":int(env._robot.get_control_index()),
            "numpy_rng":portable(np.random.get_state()),
            "python_rng":portable(random.getstate())}
        fields=d["pushing_memory_fields"]
        reward_memory=memory_snapshot(env._task,fields)
        memory_sha256=digest(portable(reward_memory))
        original_joints=np.array(
            env.get_current_state_variables()["joint_positions"],dtype=np.float64,copy=True)
        target=varied_target(np,original_joints,
            env.get_variable_space_used()["joint_positions"],
            spec["joint_index"],spec["delta_radians"])
        saved=env.get_state()

        def restore(label):
            env.set_state(saved)
            actual={
                "world_state":portable(env.get_current_state_variables()),
                "episode_length":int(env._episode_length),
                "control_index":int(env._robot.get_control_index()),
                "numpy_rng":portable(np.random.get_state()),
                "python_rng":portable(random.getstate())}
            wrong=[k for k in checkpoint if checkpoint[k]!=actual[k]]
            if wrong:
                raise ExperimentFailure("PHYSICS_RNG_RESTORE_"+label,-1,wrong)
            if arm==REPAIR:
                memory_restore(env._task,reward_memory)
            after=portable(memory_snapshot(env._task,fields))
            if arm==REPAIR and after!=portable(reward_memory):
                raise ExperimentFailure("REWARD_STATE_NOT_RESTORED_"+label,-1,fields)

        control_a=rollout(env,action,d["continuation_steps"])
        restore("CONTROL_B")
        control_b=rollout(env,action,d["continuation_steps"])
        mismatch=first_difference(control_a,control_b)
        row={"case":spec,"arm":arm,"checkpoint_reward_history_sha256":memory_sha256,
             "control_A_sha256":digest(control_a),"control_B_sha256":digest(control_b),
             "control_mismatch":mismatch,"physics_rng_restore_exact":True,
             "only_pushing_history_changed":arm==REPAIR}
        if arm==BASE:
            row["status"]="BASELINE_REWARD_DRIFT" if mismatch=={"step":0,"fields":["reward"]} else "BASELINE_DIFFERENT_FINDING"
            return row
        if mismatch is not None:
            row["status"]="REPAIR_FAILED_CONTROL_REPLAY"
            return row

        def treated(tag):
            restore("TREATED_"+tag)
            success,obs=env.do_intervention(
                {"joint_positions":np.array(target,copy=True)},check_bounds=True)
            if success is not True and success!=True:
                raise ExperimentFailure("INTERVENTION_"+tag,-1,["rejected"])
            positions=np.asarray(env.get_current_state_variables()["joint_positions"],dtype=np.float64)
            idx=spec["joint_index"]
            if (np.array_equal(positions,original_joints) or
                not np.isclose(positions[idx],target[idx],rtol=0,atol=1e-10) or
                int(env._episode_length)!=checkpoint["episode_length"]):
                raise ExperimentFailure("INTERVENTION_"+tag,-1,["target_or_counter"])
            immediate={"observation":portable(obs),"positions":portable(positions),
                       "world_state":portable(env.get_current_state_variables())}
            return immediate,rollout(env,action,d["continuation_steps"])

        immediate_a,treated_a=treated("A")
        effect=next((i for i,(a,b) in enumerate(zip(control_a,treated_a))
                     if a["observation"]!=b["observation"] or
                        a["world_state"]!=b["world_state"]),None)
        if effect is None:
            raise ExperimentFailure("NO_PHYSICAL_EFFECT",-1,["observation","world_state"])
        immediate_b,treated_b=treated("B")
        if first_difference([immediate_a],[immediate_b]) is not None:
            raise ExperimentFailure("TREATED_IMMEDIATE_DIFFER",-1,["immediate"])
        bad=first_difference(treated_a,treated_b)
        if bad is not None:
            raise ExperimentFailure("TREATED_CONTINUATION_DIFFER",bad["step"],bad["fields"])
        restore("CONTROL_C")
        control_c=rollout(env,action,d["continuation_steps"])
        bad=first_difference(control_a,control_c)
        if bad is not None:
            raise ExperimentFailure("POST_TREATMENT_CONTAMINATION",bad["step"],bad["fields"])
        row.update({"status":"REPAIR_ALL_CHECKS_PASS","first_effect_step":effect,
                    "control_C_sha256":digest(control_c),
                    "treated_sha256":digest({"immediate":immediate_a,"steps":treated_a})})
        return row
    finally:
        if saved is not None:
            env._task._remove_pybullet_state(saved["pybullet_state"])
        env.close()

def execute(repo,frozen):
    if frozen["schema"]!=FROZEN_SCHEMA or frozen["gate"]!="LCRM01-K4E":
        raise RuntimeError("FROZEN_PROTOCOL_INVALID")
    if frozen["source"]["commit"]!=EXPECTED_SOURCE_SHA:
        raise RuntimeError("SOURCE_IDENTITY_MISMATCH")
    root=repo.resolve()
    verify_source(root)
    sys.path.insert(0,str(root))
    import numpy as np
    from causal_world.envs.causalworld import CausalWorld
    from causal_world.task_generators.task import generate_task
    if root not in Path(sys.modules[CausalWorld.__module__].__file__).resolve().parents:
        raise RuntimeError("PINNED_SOURCE_IMPORT_MISMATCH")
    entries=[]
    for spec in cases(frozen):
        for arm in (BASE,REPAIR):
            try:
                entries.append(run_arm(np,CausalWorld,generate_task,frozen,spec,arm))
            except (PairFailure,ExperimentFailure) as e:
                entries.append({"case":spec,"arm":arm,"status":"NEGATIVE",
                    "failure":{"phase":getattr(e,"phase","UNKNOWN"),"step":getattr(e,"step",-1),
                               "fields":getattr(e,"fields",["unknown"])}})
            except Exception as e:
                entries.append({"case":spec,"arm":arm,"status":"INFRASTRUCTURE_BLOCKED",
                                "error_type":type(e).__name__,"error":str(e)})
    verify_source(root)
    baseline=[x for x in entries if x["arm"]==BASE]
    repaired=[x for x in entries if x["arm"]==REPAIR]
    result=("HYPOTHESIS_SUPPORTED_FOR_FROZEN_DEV_CASES"
        if (len(baseline)==len(repaired)==4 and
            all(x["status"]=="BASELINE_REWARD_DRIFT" for x in baseline) and
            all(x["status"]=="REPAIR_ALL_CHECKS_PASS" for x in repaired))
        else "INFRASTRUCTURE_BLOCKED" if any(x["status"]=="INFRASTRUCTURE_BLOCKED" for x in entries)
        else "HYPOTHESIS_NOT_ESTABLISHED_RETAIN_NEGATIVES")
    return {"schema":SCHEMA,"gate":"LCRM01-K4E",
        "protocol_sha256":hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
        "source_sha":EXPECTED_SOURCE_SHA,"cases":entries,"result":result,
        "K4D_negative_preserved":True,
        "scientific_first_use":False,"learned_transfer":False,
        "scientific_accepted":False,"dispatch_authorized":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--causalworld-repo",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        raise RuntimeError("EVIDENCE_OUTPUT_NOT_FRESH")
    frozen=json.loads(FROZEN.read_text(encoding="utf-8"))
    try:
        report=execute(args.causalworld_repo,frozen)
    except Exception as e:
        report={"schema":SCHEMA,"gate":"LCRM01-K4E",
            "result":"INFRASTRUCTURE_BLOCKED","error_type":type(e).__name__,
            "error":str(e),"traceback_tail":traceback.format_exc().splitlines()[-8:],
            "K4D_negative_preserved":True,"scientific_first_use":False,
            "learned_transfer":False,"scientific_accepted":False,"dispatch_authorized":False}
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("K4E_RESULT="+report["result"])
    print("K4E_REPORT="+str(args.output))
    # A valid negative is preserved and is not an infrastructure failure.
    return 1 if report["result"]=="INFRASTRUCTURE_BLOCKED" else 0

if __name__=="__main__":
    sys.exit(main())
