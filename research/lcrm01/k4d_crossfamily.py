#!/usr/bin/env python3
"""LCRM01-K4D: two-family, two-seed paired physics interventions (PUBLIC DEV only).

K4A/K4B/K4C are immutable. This program never trains a model, edits the
upstream CausalWorld checkout, or claims scientific-first-use authority.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys
import traceback

from k4a_control_replay import portable, verify_source, EXPECTED_SOURCE_SHA
from k4c_intervention_pair import PairFailure, compare_records, rollout

FROZEN = Path(__file__).with_name("k4d_frozen_crossfamily.json")
SCHEMA = "mass.lcrm01.k4d.paired-crossfamily-development-result.v1"
ACCEPTED_FROZEN = "mass.lcrm01.k4d.frozen-multitask-cross-process-interventions.v1"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def varied_target(np, joints, bounds, index, delta):
    """A single, signed, bounded joint intervention; no silent clipping."""
    values = np.asarray(joints, dtype=np.float64)
    limits = np.asarray(bounds, dtype=np.float64)
    if values.shape != (9,) or limits.shape != (2, 9):
        raise PairFailure("JOINT_DOMAIN", -1, ["shape"])
    if (index, delta) not in ((0, 0.04), (2, -0.03)):
        raise PairFailure("JOINT_DOMAIN", -1, ["unfrozen_intervention"])
    if not np.all(np.isfinite(values)) or not np.all(np.isfinite(limits)):
        raise PairFailure("JOINT_DOMAIN", -1, ["nonfinite"])
    lower, upper = limits[0, index] + 0.01, limits[1, index] - 0.01
    proposed = float(values[index]) + delta
    if not lower < proposed < upper:
        raise PairFailure("JOINT_DOMAIN", -1, ["out_of_margin"])
    target = values.copy()
    target[index] = proposed
    if (np.array_equal(target, values) or
        np.any(target < limits[0]) or np.any(target > limits[1])):
        raise PairFailure("JOINT_DOMAIN", -1, ["invalid_target"])
    return target


def frozen_cases(frozen):
    design = frozen["design"]
    assert design["task_families"] == ["reaching", "pushing"]
    assert design["new_seeds"] == [41, 53]
    assert design["interventions"] == [
        {"joint_index": 0, "delta_radians": 0.04},
        {"joint_index": 2, "delta_radians": -0.03},
    ]
    return [
        {"task": task, "seed": seed, **intervention}
        for task in design["task_families"]
        for seed in design["new_seeds"]
        for intervention in design["interventions"]
    ]


def run_case(np, CausalWorld, generate_task, frozen, spec):
    design = frozen["design"]
    env = CausalWorld(
        task=generate_task(task_generator_id=spec["task"]),
        enable_visualization=False,
        seed=spec["seed"],
        skip_frame=design["skip_frame"],
        action_mode=design["action_mode"],
        observation_mode=design["observation_mode"],
        normalize_actions=design["normalize_actions"],
        normalize_observations=design["normalize_observations"],
        max_episode_length=design["max_episode_length"],
    )
    saved = None
    try:
        env.reset()
        action = np.array(env.action_space.low, dtype=np.float64, copy=True)
        for _ in range(design["prefix_steps"]):
            env.step(action)
        baseline = {
            "world_state": portable(env.get_current_state_variables()),
            "episode_counter": int(env._episode_length),
            "control_index": int(env._robot.get_control_index()),
            "numpy_rng": portable(np.random.get_state()),
            "python_rng": portable(random.getstate()),
        }
        original_joints = np.array(
            env.get_current_state_variables()["joint_positions"],
            dtype=np.float64, copy=True)
        target = varied_target(
            np, original_joints,
            env.get_variable_space_used()["joint_positions"],
            spec["joint_index"], spec["delta_radians"])
        saved = env.get_state()

        def restore(tag):
            env.set_state(saved)
            restored = {
                "world_state": portable(env.get_current_state_variables()),
                "episode_counter": int(env._episode_length),
                "control_index": int(env._robot.get_control_index()),
                "numpy_rng": portable(np.random.get_state()),
                "python_rng": portable(random.getstate()),
            }
            wrong = [k for k in baseline if restored[k] != baseline[k]]
            if wrong:
                raise PairFailure("RESTORE_" + tag, -1, wrong)

        control_a = rollout(env, action, design["continuation_steps"])
        restore("CONTROL_B")
        control_b = rollout(env, action, design["continuation_steps"])
        compare_records(control_a, control_b, "CONTROL_A_B_DIFFER")

        def treated(tag):
            restore("TREATED_" + tag)
            success, obs = env.do_intervention(
                {"joint_positions": np.array(target, copy=True)},
                check_bounds=True)
            if success is not True and success != True:
                raise PairFailure("INTERVENTION_" + tag, -1, ["rejected"])
            after = np.asarray(
                env.get_current_state_variables()["joint_positions"],
                dtype=np.float64)
            idx = spec["joint_index"]
            if (np.array_equal(after, original_joints) or
                not np.isclose(after[idx], target[idx], rtol=0, atol=1e-10) or
                int(env._episode_length) != baseline["episode_counter"]):
                raise PairFailure("INTERVENTION_" + tag, -1, ["unobserved_or_counter"])
            immediate = {
                "observation": portable(obs),
                "positions": portable(after),
                "world_state": portable(env.get_current_state_variables()),
            }
            return immediate, rollout(env, action, design["continuation_steps"])

        immediate_a, treated_a = treated("A")
        physical_effect = next(
            (step for step, (a, b) in enumerate(zip(control_a, treated_a))
             if a["world_state"] != b["world_state"] or
                a["observation"] != b["observation"]), None)
        if physical_effect is None:
            raise PairFailure("NO_CAUSAL_EFFECT", -1, ["world_state", "observation"])
        immediate_b, treated_b = treated("B")
        compare_records([immediate_a], [immediate_b], "TREATED_IMMEDIATE_NONDETERMINISTIC")
        compare_records(treated_a, treated_b, "TREATED_TRAJECTORY_NONDETERMINISTIC")
        restore("CONTROL_C")
        control_c = rollout(env, action, design["continuation_steps"])
        compare_records(control_a, control_c, "CONTROL_C_CONTAMINATED")
        return {
            "case": spec, "status": "PASS",
            "first_physical_effect_step": physical_effect,
            "control_sha256": digest(control_a),
            "treated_sha256": digest({"immediate": immediate_a, "trajectory": treated_a}),
            "restoration_exact": True, "uncontaminated": True,
        }
    finally:
        if saved is not None:
            env._task._remove_pybullet_state(saved["pybullet_state"])
        env.close()


def execute(repo, frozen):
    if frozen["schema"] != ACCEPTED_FROZEN or frozen["gate"] != "LCRM01-K4D":
        raise RuntimeError("FROZEN_CONTRACT_INVALID")
    if frozen["baseline"]["source_commit"] != EXPECTED_SOURCE_SHA:
        raise RuntimeError("SOURCE_COMMIT_MISMATCH")
    cases = frozen_cases(frozen)
    if len(cases) != 8 or len(set((x["task"],x["seed"],x["joint_index"]) for x in cases)) != 8:
        raise RuntimeError("CASE_IDENTITY_MISMATCH")
    root = repo.resolve()
    verify_source(root)
    sys.path.insert(0, str(root))
    import numpy as np
    from causal_world.envs.causalworld import CausalWorld
    from causal_world.task_generators.task import generate_task
    if root not in Path(sys.modules[CausalWorld.__module__].__file__).resolve().parents:
        raise RuntimeError("CAUSALWORLD_MODULE_DRIFT")
    out = []
    for spec in cases:
        try:
            out.append(run_case(np, CausalWorld, generate_task, frozen, spec))
        except PairFailure as err:
            out.append({"case":spec,"status":"NEGATIVE",
                        "first_failure":{"phase":err.phase,"step":err.step,"fields":err.fields}})
        except Exception as err:
            out.append({"case":spec,"status":"INFRASTRUCTURE_BLOCKED",
                        "error_type":type(err).__name__,"error":str(err)})
    verify_source(root)
    overall = ("PASS_ALL_EIGHT" if all(x["status"]=="PASS" for x in out)
               else "INFRASTRUCTURE_BLOCKED" if any(x["status"]=="INFRASTRUCTURE_BLOCKED" for x in out)
               else "NEGATIVE_RETAINED")
    return {"schema":SCHEMA,"gate":"LCRM01-K4D",
            "protocol_sha256":hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
            "causalworld_commit":EXPECTED_SOURCE_SHA,
            "cases":out,"result":overall,"scientific_first_use":False,
            "learned_transfer":False,"scientific_accepted":False,
            "dispatch_authorized":False,"protected_main_mutated":False,
            "prior_negative_preserved":True}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--causalworld-repo",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args = parser.parse_args(argv)
    if args.output.exists() or not args.output.parent.is_dir():
        raise RuntimeError("OUTPUT_DESTINATION_NOT_FRESH")
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    try:
        result = execute(args.causalworld_repo,frozen)
    except Exception as err:
        result={"schema":SCHEMA,"gate":"LCRM01-K4D",
                "result":"INFRASTRUCTURE_BLOCKED","error_type":type(err).__name__,
                "error":str(err),"traceback_tail":traceback.format_exc().splitlines()[-8:],
                "scientific_first_use":False,"scientific_accepted":False,
                "learned_transfer":False,"dispatch_authorized":False,
                "prior_negative_preserved":True}
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("LCRM01_K4D_RESULT="+result["result"])
    print("LCRM01_K4D_REPORT="+str(args.output))
    return 0 if result["result"]=="PASS_ALL_EIGHT" else 1

if __name__=="__main__":
    sys.exit(main())
