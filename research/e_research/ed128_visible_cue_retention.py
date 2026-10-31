#!/usr/bin/env python3
"""E-D128: official-observation cue-retention diagnostic on EXPOSED smoke seeds only.

This is NOT a learned policy, reward comparison, or scientific first-use.
Never inspect env.unwrapped.grid, success_pos, failure_pos or RNG internals.
"""
import json
import hashlib
import gymnasium as gym
import minigrid
from minigrid.core.constants import OBJECT_TO_IDX

ENV = "MiniGrid-MemoryS13Random-v0"
SEEDS = (84000, 84001, 84002, 84003)
ACTIONS = (2, 0, 2, 1, 2, 0, 2, 1, 2, 2, 0, 2)
OBJECT_IDS = (OBJECT_TO_IDX["key"], OBJECT_TO_IDX["ball"])

def unique_cue(obs):
    # Only directly visible, non-wall Key/Ball; ambiguous views are excluded.
    items = set(int(v) for v in obs["image"][:, :, 0].flat) & set(OBJECT_IDS)
    return next(iter(items)) if len(items) == 1 else None

def sequence(seed):
    env = gym.make(ENV)
    try:
        obs, _ = env.reset(seed=seed)
        memory = None
        events = []
        for action in (None,) + ACTIONS:
            if action is not None:
                obs, reward, done, truncated, _ = env.step(action)
            else:
                reward, done, truncated = 0., False, False
            cue = unique_cue(obs)
            # "memoryless" uses only the current observation; persistent register
            # keeps last unambiguous cue, not privileged hidden world identity.
            if cue is not None: memory = cue
            events.append({"cue":cue, "retained":memory, "current":cue,
                           "blind_memory_available":cue is None and memory is not None,
                           "reward":float(reward),"done":bool(done),"truncated":bool(truncated)})
            if done or truncated: break
        raw = json.dumps(events,sort_keys=True,separators=(",",":"))
        return {"seed":seed,"frames":len(events),
                "observed_cue_frames":sum(e["cue"] is not None for e in events),
                "retention_only_frames":sum(e["blind_memory_available"] for e in events),
                "terminal_reward":events[-1]["reward"],
                "trace_sha256":hashlib.sha256(raw.encode()).hexdigest()}
    finally: env.close()

def main():
    assert minigrid.__version__ == "3.2.0"
    rows=[]
    for seed in SEEDS:
        a,b=sequence(seed),sequence(seed)
        assert a==b, ("replay mismatch",seed)
        rows.append(a)
    print(json.dumps({"status":"PASS_OBSERVATION_ABLATION_ONLY",
                      "environment":ENV,"source_scope":"REUSED_EXPOSED_ENGINEERING_SEEDS",
                      "not_reward_policy_or_science":True,"rows":rows},sort_keys=True))

if __name__=="__main__": main()
