#!/usr/bin/env python3
"""E-D146: bounded observation-driven navigation feasibility, exposed seeds only.

Not a trained learner or a memory benefit test. No hidden-state APIs.
"""
import hashlib
import json
import time
import gymnasium as gym
import minigrid
from minigrid.core.constants import OBJECT_TO_IDX

ENV = "MiniGrid-MemoryS13Random-v0"
SEEDS = (84000,84001,84002,84003)
LIMIT = 128
WALL = OBJECT_TO_IDX["wall"]
KEY = OBJECT_TO_IDX["key"]
BALL = OBJECT_TO_IDX["ball"]

def run(seed):
    env = gym.make(ENV)
    try:
        obs, _ = env.reset(seed=seed)
        actions = []
        first_unique_cue = None
        uncertainty = True
        reward = 0.0
        done = truncated = False
        start = time.perf_counter()
        for t in range(LIMIT):
            image = obs["image"]
            visible = {int(x) for x in image[:,:,0].flat if int(x) in (KEY,BALL)}
            if first_unique_cue is None and len(visible)==1:
                first_unique_cue = next(iter(visible))
            # A single visible object is NOT independently verified as the original cue.
            # Rule: turn when a wall is directly in front; otherwise move.
            # MiniGrid egocentric image center column and forward-neighbor row.
            forward_is_wall = int(image[3,5,0]) == WALL
            action = 0 if forward_is_wall else 2
            obs, reward, done, truncated, _ = env.step(action)
            actions.append(int(action))
            if done or truncated:
                break
        payload = json.dumps(actions,separators=(",",":")).encode()
        return {"seed":seed,"actions":len(actions),"reward":float(reward),
                "terminated":bool(done),"truncated":bool(truncated),
                "budget_exhausted":not (done or truncated),
                "first_unique_visible_type":first_unique_cue,
                "initial_cue_identified":False,
                "actions_sha256":hashlib.sha256(payload).hexdigest(),
                "elapsed_seconds":time.perf_counter()-start}
    finally: env.close()

def main():
    assert minigrid.__version__=="3.2.0"
    rows=[]
    for seed in SEEDS:
        a,b=run(seed),run(seed)
        for key in ("seed","actions","reward","terminated","truncated",
                    "budget_exhausted","first_unique_visible_type",
                    "initial_cue_identified","actions_sha256"):
            assert a[key]==b[key], (seed,key)
        rows.append(a)
    print(json.dumps({"status":"PASS_ENGINEERING_OBSERVATION_NAVIGATION",
                      "scope":"EXPOSED_SEEDS_ONLY","max_actions":LIMIT,
                      "policy":"forward-wall-reactive, no hidden-state calls",
                      "not_memory_reward_comparison":True,"rows":rows},sort_keys=True))

if __name__=="__main__":main()
