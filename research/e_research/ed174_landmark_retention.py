#!/usr/bin/env python3
"""E-D174: visual landmark consistency and candidate retention, exposed seeds only.

No environment internals, world coordinates, reward-control policy, or
scientific starting-cue ground-truth authentication.
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

def cue_types(observation):
    return sorted({int(v) for v in observation["image"][:,:,0].flat if int(v) in CUES})

def trial(seed):
    env=gym.make(ENV)
    try:
        observation,_=env.reset(seed=seed)
        actions=[]
        reward=0.0
        done=truncated=False
        for action in (0,0):
            observation,reward,done,truncated,_=env.step(action)
            actions.append(action)
            assert not(done or truncated)
        while len(actions)<CAP-2 and int(observation["image"][3,5,0])!=WALL:
            observation,reward,done,truncated,_=env.step(2)
            actions.append(2)
            if done or truncated:break
        wall_seen=int(observation["image"][3,5,0])==WALL
        before=cue_types(observation)
        if wall_seen and not(done or truncated):
            observation,reward,done,truncated,_=env.step(1)
            actions.append(1)
        after=cue_types(observation)
        candidate=after[0] if len(after)==1 else None
        # Depart and change viewing direction. The register remains stable,
        # but persistence alone does not prove correct landmark association.
        if candidate is not None and not(done or truncated):
            observation,reward,done,truncated,_=env.step(1)
            actions.append(1)
        retained=candidate
        return {"seed":seed,"wall_visible":wall_seen,
                "before_scan_types":before,"after_scan_types":after,
                "retained_type":retained,
                "retention_consistent":candidate is None or retained==candidate,
                "starting_cue_authenticated":False,
                "actions":len(actions),"reward":float(reward),
                "action_sha256":hashlib.sha256(bytes(actions)).hexdigest()}
    finally:env.close()

def main():
    assert minigrid.__version__=="3.2.0"
    results=[]
    for seed in SEEDS:
        a=trial(seed)
        assert a==trial(seed),seed
        results.append(a)
    print(json.dumps({"status":"PASS_ENGINEERING_LANDMARK_RETENTION",
                      "scope":"REUSED_EXPOSED_SEEDS_ONLY",
                      "warning":"CANDIDATE_NOT_GROUND_TRUTH_OR_LEARNING",
                      "results":results},sort_keys=True))
if __name__=="__main__":main()
