#!/usr/bin/env python3
"""E-D125 engineering-only reproducible random-action baseline on reused smoke seeds.
NOT a learning experiment, scientific first-use, or reserved FIT/VAL/DEV/HOLDOUT run.
"""
import hashlib
import json
import random
import time

import gymnasium as gym
import minigrid

ENV = "MiniGrid-MemoryS13Random-v0"
SEEDS = (84000, 84001, 84002, 84003)
MAX_ACTIONS = 128
EXPECTED_MINIGRID = "3.2.0"

def episode(seed):
    env = gym.make(ENV)
    rng = random.Random(seed + 125000)
    start = time.perf_counter()
    try:
        observation, info = env.reset(seed=seed)
        assert observation["image"].shape == (7, 7, 3)
        log = []
        last_reward = 0.0
        terminated = truncated = False
        for _ in range(MAX_ACTIONS):
            action = rng.randrange(env.action_space.n)
            observation, reward, terminated, truncated, info = env.step(action)
            last_reward = float(reward)
            log.append((action, last_reward, bool(terminated), bool(truncated),
                        hashlib.sha256(observation["image"].tobytes()).hexdigest()))
            if terminated or truncated:
                break
        return {"seed":seed, "actions":len(log),
                "reward":last_reward,
                "terminated":bool(terminated),"truncated":bool(truncated),
                "budget_exhausted":not (terminated or truncated),
                "trace_sha256":hashlib.sha256(json.dumps(log,separators=(',',':')).encode()).hexdigest(),
                "elapsed_seconds":time.perf_counter()-start}
    finally:
        env.close()

def main():
    assert minigrid.__version__ == EXPECTED_MINIGRID
    rows = [episode(seed) for seed in SEEDS]
    for seed, original in zip(SEEDS, rows):
        repeated = episode(seed)
        assert (original["trace_sha256"],original["actions"],original["reward"]) == (
            repeated["trace_sha256"],repeated["actions"],repeated["reward"]), seed
    print(json.dumps({"status":"PASS_ENGINEERING_RANDOM_BASELINE",
                      "environment":ENV,"version":minigrid.__version__,
                      "seed_scope":"REUSED_SMOKE_ONLY_NOT_SCIENTIFIC_COHORT",
                      "policy":"uniform-random-actions with per-seed Python RNG",
                      "max_actions":MAX_ACTIONS,"episodes":rows},sort_keys=True))

if __name__=="__main__":
    main()
