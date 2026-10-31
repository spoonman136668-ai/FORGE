#!/usr/bin/env python3
"""E-D151 paired exploratory behavior ablation; four EXPOSED seeds only.

Heuristic cue is NOT verified as the original starting-room cue. No learning,
scientific first-use or claim of memory utility is permitted.
"""
import hashlib
import json
import gymnasium as gym
import minigrid
from minigrid.core.constants import OBJECT_TO_IDX

SEEDS=(84000,84001,84002,84003)
ENV="MiniGrid-MemoryS13Random-v0"
WALL=OBJECT_TO_IDX["wall"]
KEY=OBJECT_TO_IDX["key"]
BALL=OBJECT_TO_IDX["ball"]
LIMIT=128

def unique_visible(obs):
    kinds={int(v) for v in obs["image"][:,:,0].flat if int(v) in (KEY,BALL)}
    return next(iter(kinds)) if len(kinds)==1 else None

def episode(seed,retain):
    env=gym.make(ENV)
    try:
        obs,_=env.reset(seed=seed)
        actions=[]
        # Both policies take exactly the same sensor-acquisition turn.
        obs,reward,done,truncated,_=env.step(0)
        actions.append(0)
        heuristic=unique_visible(obs)
        # Identical movement rule except turn direction at observed wall.
        # Without a verified original cue this is an exploratory switch,
        # NOT a valid comparison of task-relevant memory.
        for _ in range(LIMIT-1):
            if done or truncated: break
            wall=int(obs["image"][3,5,0])==WALL
            action=(1 if retain and heuristic==BALL else 0) if wall else 2
            obs,reward,done,truncated,_=env.step(action)
            actions.append(action)
        return {"seed":seed,"retention_enabled":retain,"heuristic_type":heuristic,
                "verified_initial_cue":False,"actions":len(actions),
                "reward":float(reward),"terminated":bool(done),
                "truncated":bool(truncated),
                "budget_exhausted":not (done or truncated),
                "action_sha256":hashlib.sha256(bytes(actions)).hexdigest()}
    finally:env.close()

def main():
    assert minigrid.__version__=="3.2.0"
    rows=[]
    for seed in SEEDS:
        a,b=episode(seed,False),episode(seed,True)
        assert a==episode(seed,False) and b==episode(seed,True)
        rows.append({"seed":seed,"memoryless":a,"retention_heuristic":b,
                     "reward_delta":b["reward"]-a["reward"]})
    print(json.dumps({"status":"PASS_EXPLORATORY_PAIRED_HEURISTIC",
                      "scope":"EXPOSED_ENGINEERING_SEEDS_ONLY",
                      "warning":"HEURISTIC_CUE_UNVERIFIED_NOT_MEMORY_CAUSAL_EVIDENCE",
                      "rows":rows},sort_keys=True))
if __name__=="__main__":main()
