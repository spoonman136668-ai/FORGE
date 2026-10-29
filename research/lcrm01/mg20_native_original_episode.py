"""MG20 authentic source engineering actors; exact original public observations only."""
import base64
import hashlib
import random

from mg17_original_family_source_qual import public,digest
from mg18_native_mission_boundary_audit import WingBridge
from research.native.itd02.mg19.original_mission_cells import OriginalMissionAdapter
from research.native.itd02.mg19.genuine_mission_cells import MissionCells

ROLES=("Wingless_MG19","Yggdrasil_MG19","unassisted_uniform_random_control")


def episode(gym,family,role,seed,cap,go_exe):
    env=gym.make(family)
    if role==ROLES[0]:
        actor=WingBridge(go_exe)
        adapter=None
        actor.request("begin_episode")
    elif role==ROLES[1]:
        actor=MissionCells()
        adapter=OriginalMissionAdapter()
    else:
        actor=random.Random("mg20-source-only:"+family+":"+str(seed))
        adapter=None
    try:
        if getattr(env.action_space,"n",None)!=7:
            raise ValueError("MG20_BAD_ORIGINAL_ACTION_SPACE")
        raw,_=env.reset(seed=seed)
        first=public(raw)
        if adapter is not None:
            adapter.reset_public(first)
            actor.start_session(adapter,"mg20-quarantine:"+family,live=True)
        before=first;events=[]
        for index in range(1,cap+1):
            if role==ROLES[0]:
                proposal=actor.request("choose",before=before)
                action,status=proposal.get("action"),proposal.get("status")
            elif role==ROLES[1]:
                proposal=actor.choose(before)
                if proposal.get("external_fallback"):
                    raise ValueError("MG20_EXTERNAL_ACTION_ORACLE")
                action,status=proposal["action"],proposal["status"]
            else:
                action=actor.randrange(7)
                status="UNASSISTED_RANDOM_ORIGINAL_ACTION_CONTROL"
            if type(action) is not int or action not in range(7) or not status:
                raise ValueError("MG20_SOURCE_ACTION_NOT_NATIVE")
            if role==ROLES[0]:
                actor.request("commit",before=before,action=action)
            elif role==ROLES[1] and adapter.submit(action)!=action:
                raise ValueError("MG20_SOURCE_ACTION_REMAP")
            raw_next,reward,term,trunc,_=env.step(action)
            after=public(raw_next)
            if after["mission"]!=first["mission"] or type(term)is not bool or type(trunc)is not bool:
                raise ValueError("MG20_SOURCE_MISSION_OR_TERMINATION_DRIFT")
            reward=float(reward)
            if role==ROLES[0]:
                ack=actor.request("feedback",before=before,action=action,after=after,
                                  reward=reward,terminal=term or trunc)
                count=ack.get("updates",0)
            elif role==ROLES[1]:
                adapter.complete(after,reward,term,trunc)
                actor.learn_selected(adapter,before,after)
                count=actor.samples
            else:
                count=None
            if role!=ROLES[2] and count!=index:
                raise ValueError("MG20_NATIVE_SELECTED_FEEDBACK_COUNT")
            events.append({"index":index,"before":before,"chosen_action":action,
                           "native_status":status,"after":after,"source_reward":reward,
                           "terminated":term,"truncated":trunc,"sample_count":count})
            before=after
            if term or trunc:
                break
        checkpoint_sha=None
        if role==ROLES[0]:
            state=actor.snapshot()
            cold=WingBridge(go_exe)
            try:
                ack=cold.request("load",state=base64.b64encode(state).decode("ascii"))
                if ack.get("updates",0)!=len(events) or cold.snapshot()!=state:
                    raise ValueError("MG20_WINGLESS_COLD_NATIVE_STATE_CHANGED")
            finally:
                cold.close()
            checkpoint_sha=hashlib.sha256(state).hexdigest()
        elif role==ROLES[1]:
            state=actor.checkpoint()
            if MissionCells.restore(state).checkpoint()!=state:
                raise ValueError("MG20_YGG_NATIVE_COLD_STATE_CHANGED")
            checkpoint_sha=hashlib.sha256(state).hexdigest()
        return {"family":family,"role":role,"quarantine_seed":seed,
                "original_mission":first["mission"],"start_sha256":digest(first),
                "steps":len(events),"events":events,"trace_sha256":digest(events),
                "checkpoint_sha256":checkpoint_sha}
    finally:
        if role==ROLES[0]:
            actor.close()
        env.close()
