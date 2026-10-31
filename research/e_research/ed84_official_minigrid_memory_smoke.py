#!/usr/bin/env python3
"""E-D84: original source-pinned MiniGrid Memory engineering smoke, not scientific first-use."""
from __future__ import annotations
import hashlib
import json

import gymnasium as gym
import minigrid
import numpy as np

ENV_ID = "MiniGrid-MemoryS13Random-v0"
SEEDS = (84000, 84001, 84002, 84003)
ACTIONS = (2, 0, 2, 1, 2, 0, 2, 1, 2, 2, 0, 2)
EXPECTED_VERSION = "3.2.0"
MISSION = "go to the matching object at the end of the hallway"


def observation(obs):
    assert isinstance(obs, dict)
    assert isinstance(obs["image"], np.ndarray)
    assert obs["image"].shape == (7, 7, 3)
    assert obs["image"].dtype == np.uint8
    assert int(obs["direction"]) in range(4)
    assert obs["mission"] == MISSION
    return [hashlib.sha256(obs["image"].tobytes()).hexdigest(), int(obs["direction"]), obs["mission"]]


def replay(seed):
    env = gym.make(ENV_ID, render_mode=None)
    try:
        assert env.action_space.n == 7
        obs, info = env.reset(seed=seed)
        assert isinstance(info, dict)
        trace = [["reset", observation(obs)]]
        for action in ACTIONS:
            assert env.action_space.contains(action)
            obs, reward, terminated, truncated, info = env.step(action)
            assert isinstance(info, dict)
            assert isinstance(terminated, bool) and isinstance(truncated, bool)
            assert 0 <= float(reward) <= 1
            trace.append([action, observation(obs), float(reward), terminated, truncated])
            if terminated or truncated:
                break
        return trace
    finally:
        env.close()


def main():
    assert minigrid.__version__ == EXPECTED_VERSION
    rows = []
    for seed in SEEDS:
        a, b = replay(seed), replay(seed)
        assert a == b, f"non-deterministic replay seed={seed}"
        rows.append({"seed": seed, "steps": len(a)-1,
                     "sha256": hashlib.sha256(json.dumps(a, sort_keys=True).encode()).hexdigest()})
    print(json.dumps({"status": "PASS", "environment": ENV_ID,
                      "version": minigrid.__version__, "seeds": rows}, sort_keys=True))


if __name__ == "__main__":
    main()
