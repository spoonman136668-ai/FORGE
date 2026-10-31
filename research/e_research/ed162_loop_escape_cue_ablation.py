#!/usr/bin/env python3
"""E-D162 paired loop-escape policy with/without an unverified cue register.

Engineering-only exposed seeds. A cue-based policy switch is NOT learned memory
or identification of the original starting-room cue.
"""
import hashlib
import json
import gymnasium as gym
import minigrid
from minigrid.core.constants import OBJECT_TO_IDX
SEEDS=(84000,84001,84002,84003)
ENV="MiniGrid-MemoryS13Random-v0"
WALL=OBJECT_TO_IDX["wall"]
CUES={OBJECT_TO_IDX["key"],OBJECT_TO_IDX["ball"]}
LIMIT=128

def episode(seed, use_register):
    env=gym.make(ENV)
    try:
        obs,_=env.reset(seed=seed)
        obs,reward,done,truncated,_=env.step(0)
        actions=[0]
        register=None
        visited={}
        repeat_count=0
        for _ in range(LIMIT-1):
            if done or truncated:break
            visible={int(v) for v in obs["image"][:,:,0].flat if int(v) in CUES}
            if register is None and len(visible)==1:
                register=next(iter(visible))
            sig=hashlib.sha256(obs["image"].tobytes()+bytes([int(obs["direction"])])).digest()
            visits=visited.get(sig,0)
            visited[sig]=visits+1
            if visits:
                repeat_count+=1
                # Hold all inputs and movement logic constant except a
                # retained-cue-dependent turn preference on recurring views.
                prefer_right=bool(use_register and register==OBJECT_TO_IDX["ball"])
                action=(1 if visits%2 else 0) if not prefer_right else (0 if visits%2 else 1)
            else:
                action=0 if int(obs["image"][3,5,0])==WALL else 2
            obs,reward,done,truncated,_=env.step(action)
            actions.append(action)
        return {"seed":seed,"policy":"cue_switch" if use_register else "frozen_loop_escape",
                "register":register,"verified_initial_cue":False,
                "reward":float(reward),"actions":len(actions),
                "terminated":bool(done),"truncated":bool(truncated),
                "budget_exhausted":not(done or truncated),
                "repeated_views":repeat_count,
                "action_sha256":hashlib.sha256(bytes(actions)).hexdigest()}
    finally:env.close()

def main():
    assert minigrid.__version__=="3.2.0"
    rows=[]
    for seed in SEEDS:
        base=episode(seed,False)
        candidate=episode(seed,True)
        assert base==episode(seed,False) and candidate==episode(seed,True)
        rows.append({"seed":seed,"baseline":base,"candidate":candidate,
                     "reward_delta":candidate["reward"]-base["reward"]})
    print(json.dumps({"status":"PASS_ENGINEERING_LOOP_ESCAPE_CUE_ABLATION",
                      "scope":"EXPOSED_ENGINEERING_SEEDS_ONLY",
                      "warning":"UNVERIFIED_CUE_NOT_CAUSAL_MEMORY_OR_TRAINED_LEARNING",
                      "rows":rows},sort_keys=True))
if __name__=="__main__":main()
