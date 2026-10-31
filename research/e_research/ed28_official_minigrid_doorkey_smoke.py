#!/usr/bin/env python3
"""Official source-pinned MiniGrid DoorKey engineering smoke; no training."""
# E-D33: trigger the scoped research-only qualification after path-filter repair.
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback

import gymnasium as gym
import minigrid  # noqa: F401 -- registers environments
import numpy as np

ENV_ID = "MiniGrid-DoorKey-8x8-v0"
SEEDS = (81400, 81401, 81402, 81403)
ACTIONS = (2, 0, 2, 1, 2, 3, 5, 2, 1, 2, 0, 2)
EXPECTED_VERSION = "3.2.0"


def observation_record(obs):
    assert isinstance(obs, dict), type(obs)
    assert isinstance(obs.get("image"), np.ndarray)
    assert obs["image"].shape == (7, 7, 3), obs["image"].shape
    assert obs["image"].dtype == np.uint8, obs["image"].dtype
    assert isinstance(obs.get("direction"), (int, np.integer))
    assert 0 <= int(obs["direction"]) <= 3
    assert obs.get("mission") == "use the key to open the door and then get to the goal"
    return (hashlib.sha256(obs["image"].tobytes()).hexdigest(),
            int(obs["direction"]), obs["mission"])


def run(seed):
    env = gym.make(ENV_ID, render_mode=None)
    try:
        assert env.action_space.n == 7, env.action_space
        obs, info = env.reset(seed=seed)
        assert isinstance(info, dict)
        log = [("reset", observation_record(obs))]
        for a in ACTIONS:
            assert env.action_space.contains(a)
            obs, reward, terminated, truncated, info = env.step(a)
            assert isinstance(terminated, bool) and isinstance(truncated, bool)
            assert 0 <= float(reward) <= 1
            log.append((a, observation_record(obs), float(reward), terminated, truncated))
            if terminated or truncated:
                break
        return log
    finally:
        env.close()


def main():
    assert minigrid.__version__ == EXPECTED_VERSION, minigrid.__version__
    rows = []
    traces = {}
    for seed in SEEDS:
        first, second = run(seed), run(seed)
        assert first == second, f"replay mismatch on {seed}"
        traces[str(seed)] = first
        rows.append({"seed": seed, "steps": len(first)-1,
                     "digest": hashlib.sha256(json.dumps(first).encode()).hexdigest()})
    if os.environ.get("GITHUB_ACTIONS") == "true":
        path = Path(os.environ["RUNNER_TEMP"]) / "ed37-doorkey" / "full-traces.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"env_id": ENV_ID, "version": minigrid.__version__,
                                    "traces": traces}, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": "PASS", "source_version": minigrid.__version__,
                      "environment_id": ENV_ID, "seed_results": rows}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            path = Path(os.environ["RUNNER_TEMP"]) / "ed37-doorkey" / "failure.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"status": "FAIL", "environment_id": ENV_ID,
                                        "traceback": traceback.format_exc()},
                                       sort_keys=True), encoding="utf-8")
        raise
