#!/usr/bin/env python3
"""LCRM01-K4A source-pinned, unprivileged CausalWorld control replay probe.

Read-only qualification harness; no scientific cohort, dataset, model training,
intervention, controller dispatch or admission. Intended for an independently
AUTHORIZED existing runner only. The test is deliberately a no-intervention
control; K4B intervention tests MUST NOT proceed until this test passes.

Example on a qualified runner that has already installed the pinned environment:
  python -B lcrm01_k4a_control_replay.py \
    --causalworld-repo /scratch/CausalWorld \
    --output /scratch/lcrm01-k4a-control.json
"""
import argparse
import hashlib
import json
import os
import random
from pathlib import Path
import subprocess
import sys
import time
import traceback

EXPECTED_SOURCE_SHA = "1045277101a92c506db42704da28f6e7227d401b"
SCHEMA = "mass.lcrm01.k4a.readonly-control-replay-probe.v1"


def git_output(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True,
        check=True, timeout=15,
    ).stdout.strip()


def verify_source(repo):
    if not (repo / ".git").exists():
        raise RuntimeError("SOURCE_REPOSITORY_NOT_A_GIT_CHECKOUT")
    actual = git_output(repo, "rev-parse", "HEAD")
    if actual != EXPECTED_SOURCE_SHA:
        raise RuntimeError("SOURCE_IDENTITY_DRIFT:" + actual)
    modified = git_output(repo, "status", "--porcelain", "--untracked-files=no")
    if modified:
        raise RuntimeError("TRACKED_SOURCE_DIRTY")
    return actual


def portable(value):
    """Record observations without rounding away reproducibility differences."""
    import numpy as np
    if isinstance(value, np.ndarray):
        arr = np.ascontiguousarray(value)
        return {"dtype": str(arr.dtype), "shape": list(arr.shape),
                "sha256": hashlib.sha256(arr.tobytes()).hexdigest()}
    if isinstance(value, np.generic):
        return portable(value.item())
    if isinstance(value, float):
        return {"float_hex": value.hex()}
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): portable(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [portable(v) for v in value]
    raise TypeError("UNSUPPORTED_EVIDENCE_TYPE:" + type(value).__name__)


def equality(a, b):
    return portable(a) == portable(b)


def probe_case(np, CausalWorld, generate_task, *, name, seed, max_episode_length, prefix, horizon):
    # Fixed task, fixed actions, same process, no random action sampling.
    env = CausalWorld(
        task=generate_task(task_generator_id="reaching"),
        enable_visualization=False, seed=seed, skip_frame=10,
        action_mode="joint_positions", observation_mode="structured",
        normalize_actions=False, normalize_observations=False,
        max_episode_length=max_episode_length,
    )
    saved = None
    try:
        env.reset()
        action = np.array(env.action_space.low, copy=True)
        actions = [action.copy() for _ in range(prefix + horizon)]
        for a in actions[:prefix]:
            env.step(a)
        checkpoint_counter = int(env._episode_length)
        checkpoint_control_index = int(env._robot.get_control_index())
        checkpoint_numpy_rng = portable(np.random.get_state())
        checkpoint_python_rng = portable(random.getstate())
        saved = env.get_state()
        def rollout():
            results=[]
            for a in actions[prefix:]:
                obs, reward, done, info = env.step(a)
                results.append({"observation": portable(obs), "reward":portable(reward),
                                "done":portable(done), "info":portable(info),
                                "episode_length":int(env._episode_length),
                                "control_index":int(env._robot.get_control_index())})
            return results
        control = rollout()
        env.set_state(saved)
        restored_counter = int(env._episode_length)
        restored_control_index = int(env._robot.get_control_index())
        restored_numpy_rng = portable(np.random.get_state())
        restored_python_rng = portable(random.getstate())
        replay = rollout()
        # Report the first difference; compare every field, not just observations.
        first_mismatch = None
        for i, (left, right) in enumerate(zip(control, replay)):
            diffs=[k for k in left if left[k]!=right[k]]
            if diffs:
                first_mismatch={"step":i, "fields":diffs}
                break
        counter_ok=(restored_counter==checkpoint_counter)
        control_index_ok=(restored_control_index==checkpoint_control_index)
        numpy_rng_ok=(restored_numpy_rng==checkpoint_numpy_rng)
        python_rng_ok=(restored_python_rng==checkpoint_python_rng)
        return {
            "case":name, "seed":seed, "prefix":prefix, "horizon":horizon,
            "max_episode_length":max_episode_length,
            "checkpoint_episode_length":checkpoint_counter,
            "restored_episode_length":restored_counter,
            "checkpoint_control_index":checkpoint_control_index,
            "restored_control_index":restored_control_index,
            "episode_counter_exact":counter_ok,
            "control_index_exact":control_index_ok,
            "numpy_rng_exact":numpy_rng_ok,
            "python_rng_exact":python_rng_ok,
            "replay_exact":first_mismatch is None,
            "first_mismatch":first_mismatch,
            "conclusion":"PASS" if counter_ok and control_index_ok and numpy_rng_ok and python_rng_ok and first_mismatch is None else "FAIL",
            "control":control,
            "replay":replay,
        }
    finally:
        if saved is not None:
            # The public API does not dispose saved PyBullet state handles.
            env._task._remove_pybullet_state(saved["pybullet_state"])
        env.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--causalworld-repo", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args=p.parse_args()
    report={"schema":SCHEMA,"source_sha_expected":EXPECTED_SOURCE_SHA,
            "kind":"SOURCE_ONLY_RUNTIME_QUALIFICATION_NOT_SCIENTIFIC_FIRST_USE",
            "scientific_firstuse":0, "intervention_performed":False,
            "dataset_downloaded":False,"trained_models":False,
            "result":"UNTESTED", "cases":[]}
    begin=time.perf_counter()
    try:
        source=verify_source(args.causalworld_repo.resolve())
        # Use the exact checkout, not a pip-installed unrelated source revision.
        sys.path.insert(0, str(args.causalworld_repo.resolve()))
        import numpy as np
        from causal_world.envs.causalworld import CausalWorld
        from causal_world.task_generators.task import generate_task
        imported=Path(sys.modules[CausalWorld.__module__].__file__).resolve()
        if args.causalworld_repo.resolve() not in imported.parents:
            raise RuntimeError("IMPORT_SOURCE_MISMATCH:" + str(imported))
        report["verified_source_sha"]=source
        report["python"]=sys.version.split()[0]
        report["numpy"]=np.__version__
        try:
            import pybullet
            report["pybullet_api_version"]=pybullet.getAPIVersion()
        except Exception:
            report["pybullet_api_version"]="NOT_RETRIEVED"
        # Early and near-terminal horizons, including the counter-restoration check.
        specs=[
            dict(name="early_checkpoint",seed=37,max_episode_length=40,prefix=5,horizon=6),
            dict(name="near_episode_limit",seed=37,max_episode_length=14,prefix=8,horizon=5),
        ]
        for spec in specs:
            case=probe_case(np,CausalWorld,generate_task,**spec)
            report["cases"].append(case)
            if case["conclusion"]!="PASS":
                report["result"]="FAIL_CONTROL_REPLAY"
                break # Fail closed; never reach an intervention branch.
        else:
            report["result"]="PASS_CONTROL_REPLAY_ONLY"
    except Exception as exc:
        report["result"]="INFRASTRUCTURE_OR_RUNTIME_BLOCKED"
        report["error_type"]=type(exc).__name__
        report["error"]=str(exc)
        report["traceback_last_lines"]=traceback.format_exc().splitlines()[-8:]
    finally:
        report["wall_seconds"]=round(time.perf_counter()-begin,6)
        output=args.output.resolve()
        if output.exists():
            raise RuntimeError("EVIDENCE_PATH_ALREADY_EXISTS")
        if not output.parent.is_dir():
            raise RuntimeError("EVIDENCE_PARENT_MISSING")
        output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        print("LCRM01_K4A_RESULT="+report["result"])
        print("LCRM01_K4A_EVIDENCE="+str(output))
    return 0 if report["result"]=="PASS_CONTROL_REPLAY_ONLY" else 1


if __name__ == "__main__":
    sys.exit(main())
