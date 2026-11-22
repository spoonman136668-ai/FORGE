#!/usr/bin/env python3
"""F41 preregistered original MountainCar development experiment; never first-use."""
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import sys
import time

import numpy as np

SOURCE = "e6be96abfb0a9df36da5e7884522c4f1f2432e53"
TRAIN_SEEDS = (811, 821, 827, 829)
EVAL_SEEDS = (911, 919, 929, 937, 941, 947, 953, 967)
FIRST_USE_FORBIDDEN = (59, 83)
KINDS = (
    "regime-residual-mpc", "velocity-rule", "trained-behavior-cloning",
    "trained-fitted-q", "global-linear-mpc", "wrong-action-mpc",
    "no-dynamics-mpc",
)
SEQUENCES = np.asarray(tuple(itertools.product(range(3), repeat=4)), dtype=int)
REGIME_BOUNDARY = 0.002


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def public_obs(obs):
    vals = obs.tolist() if hasattr(obs, "tolist") else obs
    if not isinstance(vals, (list, tuple)) or len(vals) != 2:
        raise ValueError("F41_BAD_PUBLIC_OBSERVATION_SHAPE")
    result = [float(v) for v in vals]
    if not all(math.isfinite(v) for v in result):
        raise ValueError("F41_BAD_PUBLIC_OBSERVATION")
    return result


def velocity_rule(state):
    return 2 if state[1] >= 0.0 else 0


def dyn_design(states, actions):
    states = np.asarray(states, dtype=float).reshape(-1, 2)
    actions = np.asarray(actions, dtype=int).reshape(-1)
    if len(states) != len(actions) or np.any((actions < 0) | (actions > 2)):
        raise ValueError("F41_INVALID_DYNAMICS_ACTIONS")
    return np.column_stack((
        states, *(actions == a for a in range(3)),
        np.ones(len(actions), dtype=float),
    ))


def features(states):
    states = np.asarray(states, dtype=float).reshape(-1, 2)
    p, v = states[:, 0], states[:, 1]
    return np.column_stack((np.ones(len(states)), p, v, p*p, v*v, p*v))


def ridge(x, y, penalty):
    return np.linalg.solve(x.T @ x + penalty * np.eye(x.shape[1]), x.T @ y)


def regimes(states):
    v = np.asarray(states, dtype=float).reshape(-1, 2)[:, 1]
    return np.where(v < -REGIME_BOUNDARY, 0, np.where(v > REGIME_BOUNDARY, 2, 1))


def fit_dynamics(samples, *, wrong=False):
    s = np.asarray([z["s"] for z in samples], dtype=float)
    a = np.asarray([z["a"] for z in samples], dtype=int)
    nxt = np.asarray([z["next"] for z in samples], dtype=float)
    effective_a = 2 - a if wrong else a
    x = dyn_design(s, effective_a)
    base = ridge(x, nxt, 0.001)
    residual_targets = nxt - x @ base
    residuals = np.zeros((3, 6, 2), dtype=float)
    for reg in range(3):
        mask = regimes(s) == reg
        if np.any(mask):
            residuals[reg] = ridge(x[mask], residual_targets[mask], 0.05)
    return {"global": base.tolist(), "residual": residuals.tolist()}


def predict(states, actions, dynamics, *, with_residual=False):
    s = np.asarray(states, dtype=float).reshape(-1, 2)
    x = dyn_design(s, actions)
    nxt = x @ np.asarray(dynamics["global"], dtype=float)
    if with_residual:
        r = np.asarray(dynamics["residual"], dtype=float)
        rg = regimes(s)
        for kind in range(3):
            sel = rg == kind
            if np.any(sel):
                nxt[sel] += x[sel] @ r[kind]
    if not np.all(np.isfinite(nxt)):
        raise ValueError("F41_DYNAMICS_DIVERGED")
    return nxt


def validation_gate(samples):
    internal_train = [x for x in samples if x["episode_index"] % 5 != 0]
    internal_val = [x for x in samples if x["episode_index"] % 5 == 0]
    if not internal_train or not internal_val:
        raise ValueError("F41_TRAIN_ONLY_VALIDATION_MISSING")
    dyn = fit_dynamics(internal_train)
    s = [x["s"] for x in internal_val]
    a = [x["a"] for x in internal_val]
    y = np.asarray([x["next"] for x in internal_val], dtype=float)
    base_error = float(np.sum((y - predict(s, a, dyn)) ** 2))
    local_error = float(np.sum((y - predict(s, a, dyn, with_residual=True)) ** 2))
    return local_error < base_error


def fit_models(samples):
    if not samples:
        raise ValueError("F41_NO_REAL_TRAINING_TRANSITIONS")
    s = np.asarray([x["s"] for x in samples], dtype=float)
    a = np.asarray([x["a"] for x in samples], dtype=int)
    nxt = np.asarray([x["next"] for x in samples], dtype=float)
    rew = np.asarray([x["reward"] for x in samples], dtype=float)
    done = np.asarray([x["done"] for x in samples], dtype=float)
    if s.shape[1:] != (2,) or nxt.shape[1:] != (2,):
        raise ValueError("F41_INVALID_TRAINING_SHAPE")
    if not np.all(np.isfinite(s)) or not np.all(np.isfinite(nxt)) or not np.all(np.isfinite(rew)):
        raise ValueError("F41_NONFINITE_TRAINING")
    if np.any((a < 0) | (a > 2)) or np.any((done != 0) & (done != 1)):
        raise ValueError("F41_INVALID_TRAINING_LABEL")
    if not all(np.any(a == k) for k in range(3)):
        raise ValueError("F41_MISSING_REAL_ACTION")
    gate = validation_gate(samples)
    base = fit_dynamics(samples)
    wrong = fit_dynamics(samples, wrong=True)
    bc_input = np.column_stack((s, np.ones(len(s))))
    bc = ridge(bc_input, (a[:, None] == np.arange(3)).astype(float), 0.001)
    phi, next_phi = features(s), features(nxt)
    q = np.zeros((3, 6), dtype=float)
    masks = [a == k for k in range(3)]
    for _ in range(30):
        targets = rew + .99 * (1-done) * np.max(next_phi @ q.T, axis=1)
        q = np.stack([ridge(phi[mask], targets[mask], 0.01) for mask in masks])
    model = {
        "regime-residual-mpc": {**base, "gate": bool(gate)},
        "global-linear-mpc": {**base, "gate": False},
        "wrong-action-mpc": {**wrong, "gate": False},
        "trained-behavior-cloning": bc.tolist(),
        "trained-fitted-q": q.tolist(),
        "no-dynamics-mpc": "identity",
    }
    return json.loads(canonical(model))


def mpc_action(state, kind, model):
    positions = np.repeat(np.asarray(state, dtype=float)[None, :], len(SEQUENCES), axis=0)
    cumulative = np.zeros(len(SEQUENCES), dtype=float)
    for horizon in range(4):
        act = SEQUENCES[:, horizon]
        if kind == "no-dynamics-mpc":
            predicted = positions.copy()
        else:
            dynamics = model[kind]
            predicted = predict(
                positions, act, dynamics,
                with_residual=(kind == "regime-residual-mpc" and dynamics["gate"]),
            )
        cumulative += (.92 ** horizon) * (-predicted[:, 0] - 10 * np.abs(predicted[:, 1]))
        positions = predicted
    return int(SEQUENCES[int(np.argmin(cumulative)), 0])


def choose(state, kind, model):
    if kind == "velocity-rule":
        return velocity_rule(state)
    if kind == "trained-behavior-cloning":
        f = np.asarray([state[0], state[1], 1.0])
        return int(np.argmax(f @ np.asarray(model[kind], dtype=float)))
    if kind == "trained-fitted-q":
        return int(np.argmax(np.asarray(model[kind], dtype=float) @ features([state])[0]))
    if kind not in KINDS:
        raise ValueError("F41_UNKNOWN_POLICY")
    return mpc_action(state, kind, model)


def episode(gym, seed, policy, *, model=None, episode_index=None, cap=200):
    if seed in FIRST_USE_FORBIDDEN:
        raise ValueError("F41_PROTECTED_FIRST_USE_REFUSED")
    env = gym.make("MountainCar-v0", render_mode=None)
    try:
        if env.action_space.n != 3:
            raise ValueError("F41_ORIGINAL_ACTION_GRAMMAR_DRIFT")
        obs, _ = env.reset(seed=int(seed))
        state = public_obs(obs)
        initial = state[:]
        transitions = []
        action_ns = 0
        rng = None
        if policy == "training":
            if episode_index is None:
                raise ValueError("F41_EPISODE_INDEX_REQUIRED")
            base_seed = seed - 1000 * episode_index
            rng = random.Random(0xF410000 + base_seed*1000 + episode_index)
        for _t in range(cap):
            start = time.perf_counter_ns()
            action = velocity_rule(state) if policy == "training" else choose(state, policy, model)
            if rng is not None and rng.random() < 0.50:
                action = rng.randrange(3)
            action_ns += time.perf_counter_ns() - start
            if action not in (0, 1, 2):
                raise ValueError("F41_INVALID_REAL_ACTION")
            next_obs, reward, terminated, truncated, _ = env.step(action)
            nxt = public_obs(next_obs)
            reward = float(reward)
            if not math.isfinite(reward) or type(terminated) is not bool or type(truncated) is not bool:
                raise ValueError("F41_INVALID_ORIGINAL_STEP")
            done = terminated or truncated
            transitions.append({
                "s": state, "a": action, "next": nxt,
                "reward": reward, "done": done, "terminated": terminated,
                "truncated": truncated,
            })
            state = nxt
            if done:
                break
        return {
            "initial": initial, "transitions": transitions,
            "return": sum(t["reward"] for t in transitions),
            "decision_ns": action_ns,
        }
    finally:
        env.close()


def training(gym):
    out, coverage = [], [0, 0, 0]
    for seed in TRAIN_SEEDS:
        for ep in range(24):
            result = episode(gym, seed + 1000 * ep, "training", episode_index=ep)
            for step in result["transitions"]:
                rec = {**step, "episode_index": ep}
                out.append(rec)
                coverage[step["a"]] += 1
    if not all(coverage):
        raise ValueError("F41_NO_THREE_ACTION_COVERAGE")
    return out, coverage


def assess(gym, models, train_hash, source):
    cold_bytes = canonical(models)
    cold = json.loads(cold_bytes)
    if canonical(cold) != cold_bytes:
        raise ValueError("F41_COLD_CHECKPOINT_DRIFT")
    report = {
        "schema": "forge.eureka.original-mountaincar-dev.f41.v1",
        "source": source, "training_sha256": train_hash,
        "checkpoint_sha256": digest(models),
        "train_seeds": TRAIN_SEEDS, "eval_seeds": EVAL_SEEDS,
        "development_only": True, "first_use_consumed": False,
        "scientific_accepted": False, "owner_eligible": False,
        "matched_whole_process_compute_proven": False,
        "residual_gate": models["regime-residual-mpc"]["gate"],
        "arms": {},
    }
    for kind in KINDS:
        result = {"worlds": [], "decision_ns": 0}
        for seed in EVAL_SEEDS:
            a = episode(gym, seed, kind, model=cold)
            b = episode(gym, seed, kind, model=models)
            if canonical(a["transitions"]) != canonical(b["transitions"]) or a["initial"] != b["initial"]:
                raise ValueError("F41_ORIGINAL_COLD_WARM_TRACE_MISMATCH")
            steps = a["transitions"]
            if not steps:
                raise ValueError("F41_EMPTY_ORIGINAL_EPISODE")
            result["worlds"].append({
                "seed": seed, "return": a["return"], "steps": len(steps),
                "action_sha256": digest([v["a"] for v in steps]),
                "observation_sha256": digest([a["initial"], [v["next"] for v in steps]]),
                "reward_sha256": digest([v["reward"] for v in steps]),
                "terminated": steps[-1]["terminated"], "truncated": steps[-1]["truncated"],
                "cold_matches": True,
            })
            result["decision_ns"] += a["decision_ns"]
        result["mean_return"] = sum(x["return"] for x in result["worlds"]) / len(EVAL_SEEDS)
        report["arms"][kind] = result
    conventional = max(
        ("velocity-rule", "trained-behavior-cloning", "trained-fitted-q", "global-linear-mpc"),
        key=lambda k: report["arms"][k]["mean_return"],
    )
    selected = report["arms"]["regime-residual-mpc"]
    strongest = report["arms"][conventional]
    report["strongest_conventional"] = conventional
    report["candidate_mean_gain"] = selected["mean_return"] - strongest["mean_return"]
    report["candidate_seed_wins_ge10"] = sum(
        x["return"] >= y["return"] + 10
        for x, y in zip(selected["worlds"], strongest["worlds"])
    )
    report["reward_ceiling_guard"] = strongest["mean_return"] <= -100
    report["frozen_thresholds_met"] = bool(
        report["candidate_mean_gain"] >= 15
        and report["candidate_seed_wins_ge10"] >= 6
        and report["reward_ceiling_guard"]
        and all(selected["mean_return"] >= report["arms"][k]["mean_return"] + 15
                for k in ("wrong-action-mpc", "no-dynamics-mpc"))
    )
    # Fake Gym fixtures and direct calls can never create a source-verified result.
    report["classification"] = "F41_ORIGINAL_RUNTIME_UNVERIFIED"
    report["report_sha256"] = digest(report)
    return report


def original_gym(root):
    from itd02_original_gymnasium_dev_smoke import original_pin, git
    original_pin(root)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    import gymnasium as gym
    if not Path(gym.__file__).resolve().is_relative_to(root):
        raise ValueError("F41_IMPORTED_NONPINNED_GYMNASIUM")
    return gym, git


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        raise ValueError("F41_USAGE: script.py /pinned/Gymnasium /out/dev.json")
    root = Path(argv[0]).resolve(strict=True)
    dest = Path(argv[1]).resolve()
    if dest.is_relative_to(root):
        raise ValueError("F41_OUTPUT_INSIDE_PINNED_ORIGINAL")
    try:
        gym, git = original_gym(root)
    except (ImportError, FileNotFoundError) as exc:
        raise RuntimeError("F41_ORIGINAL_RUNTIME_BLOCKED") from exc
    before = time.perf_counter()
    transcript, coverage = training(gym)
    after_training = time.perf_counter()
    models = fit_models(transcript)
    after_fit = time.perf_counter()
    result = assess(gym, models, digest(transcript), SOURCE)
    result["train_episodes"] = 96
    result["train_transitions"] = len(transcript)
    result["train_action_counts"] = coverage
    result["training_environment_seconds"] = after_training - before
    result["fitting_seconds"] = after_fit - after_training
    result["evaluation_seconds"] = time.perf_counter() - after_fit
    # Reattest pinned original source and pristine checkout before classification.
    original_gym(root)
    if git(root, "status", "--porcelain=v1", "--untracked-files=all", "--ignored=matching"):
        raise ValueError("F41_PINNED_ORIGINAL_MUTATED")
    if result["classification"] != "F41_ORIGINAL_RUNTIME_UNVERIFIED":
        raise ValueError("F41_PREATTESTED_RESULT_REFUSED")
    result["classification"] = (
        "F41_DEV_POSITIVE_DIAGNOSTIC_ONLY" if result["frozen_thresholds_met"]
        else "F41_DEV_NO_GO"
    )
    result["report_sha256"] = digest({k: v for k, v in result.items() if k != "report_sha256"})
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(canonical(result) + b"\n")
    print("F41_ORIGINAL_GYMNASIUM_DEV=" + result["classification"] + " digest=" + result["report_sha256"])
    print("F41_REAL_TRAIN_TRANSITIONS=" + str(len(transcript)) + " action_counts=" + str(coverage))
    print("F41_STRONGEST_CONVENTIONAL=" + result["strongest_conventional"]
          + " candidate_gain=" + str(result["candidate_mean_gain"]))
    return result


if __name__ == "__main__":
    main()
