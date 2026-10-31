#!/usr/bin/env python3
"""E-D131: observation-only *decision probe*, not a learned navigation policy.

Uses exposed engineering seeds only. Compares a fixed no-memory cue decision
with a cue retained from the earliest unambiguous visible Key/Ball. Does not
inspect env internals or choose navigation actions. Coverage failures are explicit.
"""
import hashlib
import json

import gymnasium as gym
import minigrid
from minigrid.core.constants import OBJECT_TO_IDX

SEEDS = (84000, 84001, 84002, 84003)
ACTIONS = (2, 0, 2, 1, 2, 0, 2, 1, 2, 2, 0, 2)
ENV = "MiniGrid-MemoryS13Random-v0"
KEY, BALL = OBJECT_TO_IDX["key"], OBJECT_TO_IDX["ball"]

def visible_cues(obs):
    return {int(v) for v in obs["image"][:, :, 0].flat if int(v) in (KEY, BALL)}

def run(seed):
    env = gym.make(ENV)
    try:
        obs, _ = env.reset(seed=seed)
        first_cue = None
        ambiguous = False
        blind_frames = 0
        coverage = 0
        decisions = []
        frames = 0
        for act in (None,) + ACTIONS:
            if act is not None:
                obs, reward, done, truncated, _ = env.step(act)
            else:
                reward, done, truncated = 0.0, False, False
            frames += 1
            cues = visible_cues(obs)
            if first_cue is None and len(cues) == 1:
                first_cue = next(iter(cues))
                # Crucial caveat: earliest visible object is not proven to be
                # start-room cue; do NOT infer hidden object identity.
            if len(cues) != 1:
                ambiguous |= len(cues) > 1
            if first_cue is not None and not cues:
                blind_frames += 1
            if first_cue is not None and len(cues) == 1:
                current = next(iter(cues))
                # This is a *cue equality classification*, not an action policy.
                # Baseline has no initial cue and always predicts "not match".
                memory_prediction = int(current == first_cue)
                baseline_prediction = 0
                if memory_prediction != baseline_prediction:
                    decisions.append({"frame":frames,"memory_predicts_match":bool(memory_prediction),
                                      "baseline_predicts_match":False})
                coverage += 1
            if done or truncated:
                break
        return {"seed":seed, "frames":frames, "initial_cue_seen":first_cue is not None,
                "ambiguous_observation_seen":ambiguous,
                "blind_frames":blind_frames,"comparable_cue_frames":coverage,
                "decisions_differ":len(decisions),
                "decision_sha256":hashlib.sha256(json.dumps(decisions,sort_keys=True).encode()).hexdigest(),
                "terminal_reward_from_fixed_script":float(reward)}
    finally:
        env.close()

def main():
    assert minigrid.__version__ == "3.2.0"
    rows = []
    for seed in SEEDS:
        a,b=run(seed),run(seed)
        assert a==b, seed
        rows.append(a)
    print(json.dumps({"status":"PASS_ENGINEERING_CUE_DECISION_PROBE",
                      "environment":ENV,"scope":"EXPOSED_SMOKE_SEEDS_ONLY",
                      "warning":"NOT_ACTION_POLICY_NOT_GROUND_TRUTH_INITIAL_CUE_NOT_SUCCESS_ACCURACY",
                      "rows":rows},sort_keys=True))

if __name__=="__main__":
    main()
