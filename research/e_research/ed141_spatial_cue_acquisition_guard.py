#!/usr/bin/env python3
"""E-D141: observation-only spatial landmark identity audit; exposed seeds only.

An object is NOT labeled the starting cue merely because it is first seen.
This test measures stability of local visual positions under full orientation
rotation and returns ABSTAIN when the original cue is not identifiable.
"""
import hashlib
import json
import gymnasium as gym
import minigrid
from minigrid.core.constants import OBJECT_TO_IDX

SEEDS=(84000,84001,84002,84003)
KINDS=(OBJECT_TO_IDX["key"],OBJECT_TO_IDX["ball"])
ENV="MiniGrid-MemoryS13Random-v0"

def acquire(seed):
    env=gym.make(ENV)
    try:
        obs,_=env.reset(seed=seed)
        views=[]
        for step in range(5):
            im=obs["image"]
            objects=sorted((int(x),int(y),int(im[x,y,0]))
                           for x in range(im.shape[0])
                           for y in range(im.shape[1])
                           if int(im[x,y,0]) in KINDS)
            views.append({"orientation":int(obs["direction"]),"objects":objects})
            if step<4:
                obs,reward,done,truncated,_=env.step(0)
                assert not (done or truncated) and reward==0
        assert views[0]==views[-1], "full-turn observation changed without translation"
        candidate_types={o[2] for frame in views for o in frame["objects"]}
        # A distinct type alone is not a spatially verified task cue.
        return {"seed":seed, "visible_object_types":sorted(candidate_types),
                "orientation_loop_closed":True,
                "initial_cue":"ABSTAIN_NOT_LOCALIZED",
                "view_trace_sha256":hashlib.sha256(
                    json.dumps(views,sort_keys=True,separators=(",",":")).encode()).hexdigest()}
    finally: env.close()

def main():
    assert minigrid.__version__=="3.2.0"
    rows=[]
    for seed in SEEDS:
        a=acquire(seed)
        assert a==acquire(seed), seed
        rows.append(a)
    print(json.dumps({"status":"PASS_SPATIAL_CUE_ACQUISITION_SAFETY_AUDIT",
                      "scope":"EXPOSED_SEEDS_ONLY","not_behavioral_success":True,
                      "rows":rows},sort_keys=True))

if __name__=="__main__": main()
