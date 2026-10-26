"""Matched statistical episode control; no original-world run on import."""
import math
from k4r_minigrid_source import public,canon,sha
from k4u_native_minigrid import public_grid
from k4y_native_affordance import make_env,STEPS
from itd02_r8_episode_contract import validate_episode_request

def run_statistical_episode(family,seed,model,base_action,method):
    if method not in ("independent_conditional_beta","r8_previous_action_ablated"):
        raise ValueError("R8_STATISTICAL_METHOD_UNREGISTERED")
    validate_episode_request(family,seed,"wingless_r8_online_beliefs")
    if not callable(base_action):
        raise ValueError("R8_BASE_ACTION_NOT_CALLABLE")
    env=make_env(family)
    trace=[]
    total=0.0
    try:
        model.begin_episode()
        obs,_=env.reset(seed=seed)
        state=public(obs)
        initial=state["grid_sha256"]
        for tick in range(STEPS[family]):
            before=public_grid(state)
            chosen=model.turn_choice(bool(before["FrontBlocked"]))
            action=base_action(state) if chosen is None else chosen
            if type(action) is not int or action not in (0,1,2):
                raise ValueError("R8_STATISTICAL_ILLEGAL_ACTION")
            next_obs,reward,terminated,truncated,_=env.step(action)
            if not math.isfinite(float(reward)):
                raise ValueError("R8_STATISTICAL_NONFINITE_REWARD")
            nxt=public(next_obs,state["goal"])
            after=public_grid(nxt)
            model.observe(bool(before["FrontBlocked"]),action,bool(after["FrontBlocked"]))
            trace.append({"t":tick,"action":action,"reward":float(reward),
                          "terminated":bool(terminated),"truncated":bool(truncated)})
            total+=float(reward)
            state=nxt
            if terminated or truncated:break
        if not trace:raise ValueError("R8_STATISTICAL_EMPTY_EPISODE")
        return {"family":family,"seed":seed,"method":method,
                "initial_grid_sha256":initial,"success":bool(trace[-1]["terminated"] and total>0),
                "real_total_reward":total,"steps":len(trace),"trace_sha256":sha(canon(trace).encode()),
                "trace":trace,"scientific_accepted":False}
    finally:
        env.close()
