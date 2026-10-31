#!/usr/bin/env python3
"""E-D167 west-end cue-acquisition feasibility on exposed MiniGrid seeds.

Official source geometry motivates westward exploration; agent receives only
reset/step observations. No env.unwrapped or hidden ground-truth fields.
A detected object remains a *candidate*, not verified original cue.
"""
import hashlib
import json
import gymnasium as gym
import minigrid
from minigrid.core.constants import OBJECT_TO_IDX

ENV="MiniGrid-MemoryS13Random-v0"
SEEDS=(84000,84001,84002,84003)
WALL=OBJECT_TO_IDX["wall"]
CUES={OBJECT_TO_IDX["key"],OBJECT_TO_IDX["ball"]}
CAP=128

def types(obs):
    return sorted({int(v) for v in obs["image"][:,:,0].flat if int(v) in CUES})

def trial(seed):
    env=gym.make(ENV)
    try:
        obs,_=env.reset(seed=seed)
        actions=[]
        reward=0.0
        done=truncated=False
        def step(action):
            nonlocal obs,reward,done,truncated
            obs,reward,done,truncated,_=env.step(action)
            actions.append(action)
        # Source-grounded geometry: all starts face east; rotate toward west.
        step(0)
        if not(done or truncated):step(0)
        found_wall=False
        candidate=None
        while not(done or truncated) and len(actions)<CAP-1:
            # The immediate cell ahead is observation image [3,5],
            # since agent is at [3,6] in original 7x7 egocentric view.
            if int(obs["image"][3,5,0])==WALL:
                found_wall=True
                break
            step(2)
        if found_wall and not(done or truncated) and len(actions)<CAP:
            step(1) # west->north; scan from west end of hallway
            visible=types(obs)
            if len(visible)==1:
                candidate=visible[0]
        return {"seed":seed,"actions":len(actions),"west_wall_detected":found_wall,
                "candidate_type":candidate,"candidate_authenticated":False,
                "reward":float(reward),"terminated":bool(done),
                "truncated":bool(truncated),
                "action_hash":hashlib.sha256(bytes(actions)).hexdigest()}
    finally:env.close()

def main():
    assert minigrid.__version__=="3.2.0"
    rows=[]
    for seed in SEEDS:
        a=trial(seed)
        assert a==trial(seed),seed
        rows.append(a)
    print(json.dumps({"status":"PASS_ENGINEERING_WEST_CUE_EXPLORATION",
                      "scope":"EXPOSED_ENGINEERING_SEEDS_ONLY",
                      "warning":"SOURCE_INFORMED_GEOMETRY_CANDIDATES_UNVERIFIED_NOT_LEARNING",
                      "rows":rows},sort_keys=True))
if __name__=="__main__":main()
