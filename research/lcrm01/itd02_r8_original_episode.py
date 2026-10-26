"""Original MiniGrid R8/R5 episode execution; no automatic experiment runs."""
import math
import time

from k4r_minigrid_source import public, canon, sha
from k4u_native_minigrid import public_grid, wingless_wire_grid
from k4y_native_affordance import make_env, STEPS
from itd02_r8_episode_contract import validate_episode_request

def run_episode(family, seed, method, bridge):
    validate_episode_request(family,seed,method)
    env=make_env(family)
    trace=[]
    total=0.0
    start=time.perf_counter()
    try:
        bridge.request("episode_start")
        obs,_=env.reset(seed=seed)
        state=public(obs)
        initial=state["grid_sha256"]
        for tick in range(STEPS[family]):
            before=wingless_wire_grid(public_grid(state))
            action=bridge.request("choose",before=before)["action"]
            if type(action) is not int or action not in (0,1,2):
                raise ValueError("R8_ILLEGAL_NATIVE_ACTION")
            next_obs,reward,terminated,truncated,_=env.step(action)
            if not math.isfinite(float(reward)):
                raise ValueError("R8_NONFINITE_ORIGINAL_REWARD")
            nxt=public(next_obs,state["goal"])
            after=wingless_wire_grid(public_grid(nxt))
            receipt=bridge.request("feedback",before=before,action=action,after=after)
            if receipt.get("steps") != tick+1:
                raise ValueError("R8_EPISODE_FEEDBACK_STEP_DRIFT")
            trace.append({"t":tick,"action":action,"before":before,"after":after,
                          "reward":float(reward),"terminated":bool(terminated),
                          "truncated":bool(truncated)})
            total+=float(reward)
            state=nxt
            if terminated or truncated:
                break
        if not trace:
            raise ValueError("R8_EMPTY_ORIGINAL_EPISODE")
        return {"family":family,"seed":seed,"method":method,
                "initial_grid_sha256":initial,"success":bool(trace[-1]["terminated"] and total>0),
                "real_total_reward":total,"steps":len(trace),"trace":trace,
                "trace_sha256":sha(canon(trace).encode()),
                "episode_wall_seconds":time.perf_counter()-start,
                "scientific_first_use":False,"scientific_accepted":False}
    finally:
        env.close()
