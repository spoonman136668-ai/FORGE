#!/usr/bin/env python3
"""E-D133 exposed-seed observation-only cue-acquisition feasibility audit.

No access to env.unwrapped, success_pos, goal, or ground-truth initial cue.
Do not interpret first visible object as authenticated starting-room cue.
"""
import hashlib
import json
import gymnasium as gym
import minigrid
from minigrid.core.constants import OBJECT_TO_IDX

SEEDS=(84000,84001,84002,84003)
ENV="MiniGrid-MemoryS13Random-v0"
TYPES={OBJECT_TO_IDX["key"],OBJECT_TO_IDX["ball"]}

def sight(obs):
    return sorted({int(x) for x in obs["image"][:,:,0].flat if int(x) in TYPES})

def inspect(seed):
    env=gym.make(ENV)
    try:
        obs,_=env.reset(seed=seed)
        frames=[sight(obs)]
        for _ in range(4):
            obs, reward, terminated, truncated, _=env.step(0) # turn LEFT in place
            assert not terminated and not truncated and reward==0
            frames.append(sight(obs))
        seen=sorted({x for frame in frames for x in frame})
        # Classifying the *actual starting cue* is impossible without a
        # grounded localization/cue-acquisition policy; mark unverified.
        return {"seed":seed,"reset_visible":frames[0],
                "turn_scan_visible":frames[1:],"unique_object_types_seen":seen,
                "candidate_cue_unambiguous":len(seen)==1,
                "original_start_cue_identity":"UNVERIFIED",
                "scan_sha256":hashlib.sha256(json.dumps(frames,separators=(',',':')).encode()).hexdigest()}
    finally:
        env.close()

def main():
    assert minigrid.__version__=="3.2.0"
    rows=[]
    for seed in SEEDS:
        a,b=inspect(seed),inspect(seed)
        assert a==b
        rows.append(a)
    print(json.dumps({"status":"PASS_ENGINEERING_OBSERVATION_AUDIT",
                      "scope":"REUSED_EXPOSED_SMOKE_SEEDS_ONLY",
                      "warning":"NOT_GROUND_TRUTH_CUE_NOT_BEHAVIORAL_POLICY_NOT_SCIENTIFIC_FIRST_USE",
                      "rows":rows},sort_keys=True))

if __name__=="__main__": main()
