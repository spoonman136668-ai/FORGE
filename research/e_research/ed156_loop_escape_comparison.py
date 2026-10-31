#!/usr/bin/env python3
"""E-D156 exposed-seed observation-loop escape versus frozen E-D151 baseline.

No hidden-state access, learning, verified starting cue, or scientific first-use.
"""
import hashlib
import json
import gymnasium as gym
import minigrid
from minigrid.core.constants import OBJECT_TO_IDX

SEEDS=(84000,84001,84002,84003)
ENV="MiniGrid-MemoryS13Random-v0"
WALL=OBJECT_TO_IDX["wall"]
LIMIT=128

def episode(seed,escape):
    env=gym.make(ENV)
    try:
        obs,_=env.reset(seed=seed)
        actions=[]
        seen={}
        reward=0.0
        done=truncated=False
        # Maintain the same initial sensing turn as the E-D151 paired control.
        obs,reward,done,truncated,_=env.step(0)
        actions.append(0)
        repeated=0
        forced_turns=0
        for step in range(LIMIT-1):
            if done or truncated:break
            signature=hashlib.sha256(obs["image"].tobytes()+bytes([int(obs["direction"])])).hexdigest()
            prior=seen.get(signature,0)
            seen[signature]=prior+1
            wall=int(obs["image"][3,5,0])==WALL
            action=0 if wall else 2
            if prior:
                repeated+=1
                if escape:
                    # Bounded deterministic avoidance; no privileged pose/map.
                    action=1 if prior%2 else 0
                    forced_turns+=1
            obs,reward,done,truncated,_=env.step(action)
            actions.append(action)
        return {"seed":seed,"policy":"loop_escape" if escape else "frozen_E151_memoryless",
                "actions":len(actions),"reward":float(reward),
                "terminated":bool(done),"truncated":bool(truncated),
                "budget_exhausted":not (done or truncated),
                "repeated_views":repeated,"escape_turns":forced_turns,
                "action_sha256":hashlib.sha256(bytes(actions)).hexdigest()}
    finally:env.close()

def main():
    assert minigrid.__version__=="3.2.0"
    rows=[]
    for seed in SEEDS:
        a,b=episode(seed,False),episode(seed,True)
        assert a==episode(seed,False) and b==episode(seed,True)
        rows.append({"seed":seed,"baseline":a,"loop_escape":b,
                     "reward_delta":b["reward"]-a["reward"]})
    print(json.dumps({"status":"PASS_ENGINEERING_LOOP_ESCAPE_COMPARISON",
                      "scope":"REUSED_EXPOSED_ENGINEERING_SEEDS_ONLY",
                      "warning":"REACTIVE_CONTROLLER_NOT_MEMORY_LEARNING_OR_SCIENTIFIC_RESULT",
                      "rows":rows},sort_keys=True))
if __name__=="__main__":main()
