#!/usr/bin/env python3
"""LCRM01-K4C: preregistered source-only matched intervention-pair replay.

Pinned CausalWorld original source plus the already qualified K4B in-memory
candidate overlay. No protected dataset, learned model, scientific first-use,
scientific acceptance, or controller dispatch. Never alter the original source.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys
import time
import traceback

from k4a_control_replay import EXPECTED_SOURCE_SHA, portable, verify_source

SCHEMA = "mass.lcrm01.k4c.sourceonly-paired-intervention-probe.v1"
FROZEN = Path(__file__).with_name("k4c_frozen_intervention_pair.json")


class PairFailure(Exception):
    def __init__(self, phase, step, fields):
        super().__init__(phase + ":" + ",".join(fields))
        self.phase, self.step, self.fields = phase, step, fields


def compare_records(left, right, phase):
    if len(left) != len(right):
        raise PairFailure(phase, -1, ["length"])
    for index, (a, b) in enumerate(zip(left, right)):
        keys = sorted(set(a) | set(b))
        fields = [key for key in keys if a.get(key) != b.get(key)]
        if fields:
            raise PairFailure(phase, index, fields)
    return True


def intervention_target(np, checkpoint_joints, bounds):
    joints = np.asarray(checkpoint_joints, dtype=np.float64)
    limits = np.asarray(bounds, dtype=np.float64)
    if joints.shape != (9,) or limits.shape != (2, 9):
        raise PairFailure("INTERVENTION_DOMAIN", -1, ["shape"])
    if not np.all(np.isfinite(joints)) or not np.all(np.isfinite(limits)):
        raise PairFailure("INTERVENTION_DOMAIN", -1, ["not_finite"])
    low, high = limits[0, 0] + 0.01, limits[1, 0] - 0.01
    if not low < high:
        raise PairFailure("INTERVENTION_DOMAIN", -1, ["bounds"])
    target = joints.copy()
    target[0] = min(max(float(joints[0]) + 0.04, low), high)
    if np.array_equal(target, joints) or not np.all(target >= limits[0]) or not np.all(target <= limits[1]):
        raise PairFailure("INTERVENTION_DOMAIN", -1, ["no_valid_in_bound_change"])
    return target


def rollout(env, action, count):
    result = []
    for _ in range(count):
        observation, reward, done, info = env.step(action)
        result.append({
            "observation": portable(observation),
            "reward": portable(reward),
            "done": portable(done),
            "info": portable(info),
            "episode_length": int(env._episode_length),
            "control_index": int(env._robot.get_control_index()),
            "world_state": portable(env.get_current_state_variables()),
        })
    return result


def run_case(np, CausalWorld, generate_task, frozen):
    config = frozen["case"]
    env = CausalWorld(
        task=generate_task(task_generator_id=config["task"]),
        enable_visualization=False,
        seed=config["seed"],
        skip_frame=config["skip_frame"],
        action_mode=config["action_mode"],
        observation_mode=config["observation_mode"],
        normalize_actions=config["normalize_actions"],
        normalize_observations=config["normalize_observations"],
        max_episode_length=config["max_episode_length"],
    )
    saved = None
    phase = "INITIALIZING"
    audit = {"controls": {}, "treated": {}, "first_mismatch": None}
    try:
        env.reset()
        action = np.array(env.action_space.low, dtype=np.float64, copy=True)
        for _ in range(config["prefix_steps"]):
            env.step(action)
        baseline_state = portable(env.get_current_state_variables())
        baseline_episode = int(env._episode_length)
        baseline_index = int(env._robot.get_control_index())
        baseline_numpy_rng = portable(np.random.get_state())
        baseline_python_rng = portable(random.getstate())
        checkpoint_joints = np.array(env.get_current_state_variables()["joint_positions"], dtype=np.float64, copy=True)
        bounds = env.get_variable_space_used()["joint_positions"]
        target = intervention_target(np, checkpoint_joints, bounds)
        audit["assignment"] = {
            "variable": "joint_positions", "index": 0,
            "before": portable(checkpoint_joints),
            "target": portable(target),
            "bounded": True,
            "requested_delta_0": portable(float(target[0] - checkpoint_joints[0])),
        }
        saved = env.get_state()

        def reset_branch(phase_name):
            nonlocal phase
            phase = phase_name
            env.set_state(saved)
            check = {
                "world_state": portable(env.get_current_state_variables()) == baseline_state,
                "episode_counter": int(env._episode_length) == baseline_episode,
                "control_index": int(env._robot.get_control_index()) == baseline_index,
                "numpy_rng": portable(np.random.get_state()) == baseline_numpy_rng,
                "python_rng": portable(random.getstate()) == baseline_python_rng,
            }
            bad = [name for name, ok in check.items() if not ok]
            if bad:
                raise PairFailure(phase_name, -1, bad)
            return check

        phase = "CONTROL_A"
        control_a = rollout(env, action, config["continuation_steps"])
        audit["controls"]["A"] = control_a

        audit["restored_control_B"] = reset_branch("RESTORE_CONTROL_B")
        control_b = rollout(env, action, config["continuation_steps"])
        compare_records(control_a, control_b, "CONTROL_A_B_NOT_EQUAL")
        audit["controls"]["B"] = control_b

        def treated_branch(tag):
            reset_branch("RESTORE_TREATED_" + tag)
            local_phase = "TREATED_INTERVENTION_" + tag
            success, intervention_obs = env.do_intervention(
                {"joint_positions": np.array(target, copy=True)},
                check_bounds=True)
            if success is not True and success != True:
                raise PairFailure(local_phase, -1, ["intervention_not_successful"])
            after = np.asarray(env.get_current_state_variables()["joint_positions"], dtype=np.float64)
            if np.array_equal(after, checkpoint_joints):
                raise PairFailure(local_phase, -1, ["no_target_change"])
            if not np.allclose(after[0], target[0], rtol=0, atol=1e-10):
                raise PairFailure(local_phase, -1, ["assignment_not_applied"])
            if int(env._episode_length) != baseline_episode:
                raise PairFailure(local_phase, -1, ["intervention_advanced_episode_counter"])
            immediate = {
                "observation": portable(intervention_obs),
                "post_joint_positions": portable(after),
                "state": portable(env.get_current_state_variables()),
                "control_index": int(env._robot.get_control_index()),
                "episode_length": int(env._episode_length),
            }
            trajectory = rollout(env, action, config["continuation_steps"])
            return immediate, trajectory

        phase = "TREATED_A"
        treated_a_0, treated_a = treated_branch("A")
        audit["treated"]["A"] = {"immediate": treated_a_0, "continuation": treated_a}
        first_physical_effect = next(
            (i for i, (c, t) in enumerate(zip(control_a, treated_a))
             if c["observation"] != t["observation"] or c["world_state"] != t["world_state"]), None)
        if first_physical_effect is None:
            raise PairFailure("NO_ATTRIBUTABLE_PHYSICAL_TRAJECTORY_CHANGE", -1, ["observation", "world_state"])
        audit["first_attributable_effect_step"] = first_physical_effect

        phase = "TREATED_B"
        treated_b_0, treated_b = treated_branch("B")
        compare_records([treated_a_0], [treated_b_0], "TREATED_IMMEDIATE_A_B_NOT_EQUAL")
        compare_records(treated_a, treated_b, "TREATED_CONTINUATION_A_B_NOT_EQUAL")
        audit["treated"]["B"] = {"immediate": treated_b_0, "continuation": treated_b}

        phase = "CONTROL_C"
        audit["restored_control_C"] = reset_branch("RESTORE_CONTROL_C_AFTER_TREATMENTS")
        control_c = rollout(env, action, config["continuation_steps"])
        compare_records(control_a, control_c, "CONTROL_AFTER_INTERVENTION_CONTAMINATED")
        audit["controls"]["C"] = control_c
        audit["verdict"] = "PASS_PAIRED_JOINT_INTERVENTION_ONLY"
        return audit
    finally:
        if saved is not None:
            env._task._remove_pybullet_state(saved["pybullet_state"])
        env.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--causalworld-repo", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    assert frozen["schema"] == "mass.lcrm01.k4c.preregistered-intervention-pair-development.v1"
    assert frozen["source"]["commit"] == EXPECTED_SOURCE_SHA
    output = args.output.resolve()
    if output.exists() or not output.parent.is_dir():
        raise RuntimeError("OUTPUT_PATH_NOT_FRESH")
    report = {
        "schema": SCHEMA, "gate": "LCRM01-K4C",
        "scientific_firstuse": 0, "trained_models": False, "protected_main_mutated": False,
        "scientific_acceptance": False, "counterfactual_oracle_qualified": False,
        "result": "UNTESTED", "original_negative_preserved": True,
        "frozen_protocol_sha256": hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
    }
    started = time.perf_counter()
    try:
        repo = args.causalworld_repo.resolve()
        report["verified_source"] = verify_source(repo)
        sys.path.insert(0, str(repo))
        import numpy as np
        from causal_world.envs.causalworld import CausalWorld
        from causal_world.task_generators.task import generate_task
        module = Path(sys.modules[CausalWorld.__module__].__file__).resolve()
        if repo not in module.parents:
            raise RuntimeError("SOURCE_MODULE_IDENTITY_DRIFT")
        report["python"] = sys.version.split()[0]
        report["numpy"] = np.__version__
        report["evaluation"] = run_case(np, CausalWorld, generate_task, frozen)
        if verify_source(repo) != EXPECTED_SOURCE_SHA:
            raise RuntimeError("ORIGINAL_SOURCE_DIRTY_AFTER_TEST")
        report["result"] = "PASS_PAIRED_JOINT_INTERVENTION_ONLY"
    except PairFailure as exc:
        report["result"] = "FAIL_INTERVENTION_PAIR"
        report["first_failure"] = {"phase": exc.phase, "step": exc.step, "fields": exc.fields}
    except Exception as exc:
        report["result"] = "RUNTIME_OR_INFRASTRUCTURE_BLOCKED"
        report["error"] = type(exc).__name__ + ":" + str(exc)
        report["traceback_tail"] = traceback.format_exc().splitlines()[-12:]
    finally:
        report["elapsed_seconds"] = round(time.perf_counter() - started, 6)
        output.write_text(json.dumps(report, sort_keys=True, indent=2)+"\n", encoding="utf-8")
        print("LCRM01_K4C_RESULT=" + report["result"])
        print("LCRM01_K4C_EVIDENCE=" + str(output))
    return 0 if report["result"] == "PASS_PAIRED_JOINT_INTERVENTION_ONLY" else 1


if __name__ == "__main__":
    sys.exit(main())
