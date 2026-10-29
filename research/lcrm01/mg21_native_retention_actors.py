"""MG21 original MiniGrid shared FIT and cold native actor provisioning.

All FIT transitions originate from one unchanged original source public stream.
Probe decisions remain independent native actions in genuine original worlds.
"""
import base64
import hashlib
import random

from mg17_original_family_source_qual import public,digest
from mg18_native_mission_boundary_audit import WingBridge
from mg21_original_tabular_control import Tabular
from research.native.itd02.mg19.original_mission_cells import OriginalMissionAdapter
from research.native.itd02.mg19.genuine_mission_cells import MissionCells

ROLES=("go_fit","go_fresh","ygg_fit","ygg_fresh",
       "tabular_fit","tabular_fresh","random")
def family_fit(gym,name,seed,cap):
    env=gym.make(name)
    rng=random.Random("mg21-shared-source:"+name+":"+str(seed))
    events=[]
    try:
        raw,_=env.reset(seed=seed);before=public(raw);first=before
        for index in range(1,cap+1):
            action=rng.randrange(7)
            raw_next,reward,term,trunc,_=env.step(action)
            after=public(raw_next)
            if before["mission"]!=after["mission"]:
                raise ValueError("MG21_SOURCE_FIT_MISSION_CHANGED")
            events.append({"before":before,"action":action,"after":after,
                           "reward":float(reward),"terminated":bool(term),
                           "truncated":bool(trunc)})
            before=after
            if term or trunc:break
        if not events:raise ValueError("MG21_NO_REAL_SOURCE_FIT")
        return first,events
    finally:env.close()

def prepare(role,events,go_binary,name):
    trained=role.endswith("_fit")
    if role.startswith("go_"):
        actor=WingBridge(go_binary)
        if trained:
            for index,event in enumerate(events,1):
                ack=actor.request("fit",before=event["before"],
                    action=event["action"],after=event["after"],
                    reward=event["reward"],
                    terminal=event["terminated"] or event["truncated"])
                if ack.get("updates",0)!=index:
                    raise ValueError("MG21_GO_SHARED_FIT_COUNT")
            raw=actor.snapshot()
            cold=WingBridge(go_binary)
            ack=cold.request("load",state=base64.b64encode(raw).decode("ascii"))
            if ack.get("updates",0)!=len(events) or cold.snapshot()!=raw:
                raise ValueError("MG21_GO_FIT_COLD_RESTORE")
            actor.close();actor=cold
        return actor,None
    if role.startswith("ygg_"):
        actor=MissionCells()
        if trained:
            original=OriginalMissionAdapter()
            original.reset_public(events[0]["before"])
            actor.start_session(original,"mg21-real-shared-fit:"+name,live=False)
            for index,event in enumerate(events,1):
                original.submit(event["action"])
                original.complete(event["after"],event["reward"],
                    event["terminated"],event["truncated"])
                actor.learn_selected(original,event["before"],event["after"])
                if actor.samples!=index:raise ValueError("MG21_YGG_SHARED_FIT_COUNT")
            snap=actor.checkpoint()
            actor=MissionCells.restore(snap)
            if actor.checkpoint()!=snap:raise ValueError("MG21_YGG_FIT_COLD_RESTORE")
        return actor,OriginalMissionAdapter()
    if role.startswith("tabular_"):
        actor=Tabular()
        if trained:
            for e in events:
                actor.learn(e["before"],e["action"],e["after"],
                            e["reward"],e["terminated"] or e["truncated"])
            snap=actor.checkpoint();actor=Tabular.restore(snap)
            if actor.checkpoint()!=snap:raise ValueError("MG21_CONTROL_COLD_RESTORE")
        return actor,None
    if role=="random":
        return random.Random("mg21-independent-probe:"+name),None
    raise ValueError("MG21_UNREGISTERED_ACTOR")
