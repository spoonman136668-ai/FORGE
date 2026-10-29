"""AC32 source-free diagnostic repair of MG15's two-mission conventional control.

Standalone opt-in THREE original-public-mission conventional arm. No original
simulator imported/called. Historical MG15, MG16, AC31/AC32 source evaluators,
native DK15/R19, protected main and consumed seed results remain unchanged.
Only the conventional arm internally retains the previously documented
DoorKey visual-only parent projection; native actors never receive this.
"""
from __future__ import annotations
import hashlib,json,math

SCHEMA="forge.ac32.development-three-real-mission-conventional.v1"
MISSIONS=frozenset(("use the key to open the door and then get to the goal",
    "get to the green goal square","open the door"))
LEGACY="use the key to open the door and then get to the goal"
MAX_BYTES=2500000
def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=True,
        allow_nan=False).encode("utf-8")
def sha(data):
    return hashlib.sha256(data).hexdigest()
def original_public(p):
    if type(p)is not dict or set(p)!={"image","direction","mission"}:
        raise ValueError("AC32_CONVENTIONAL_PUBLIC_PRIVATE_FIELDS")
    if type(p["mission"])is not str or p["mission"] not in MISSIONS:
        raise ValueError("AC32_UNKNOWN_ORIGINAL_PUBLIC_MISSION")
    if type(p["direction"])is not int or p["direction"] not in range(4):
        raise ValueError("AC32_PUBLIC_DIRECTION")
    image=p["image"]
    if type(image)is not list or len(image)!=7 or not all(
        type(row)is list and len(row)==7 and all(
            type(px)is list and len(px)==3 and all(
                type(v)is int and 0<=v<=255 for v in px) for px in row)
        for row in image):
        raise ValueError("AC32_PUBLIC_IMAGE")
    return p
def blind_public(p):
    # Source-original mission preserved outside this explicitly conventional
    # mission-blind parent. Never pass the internally projected copy to native.
    q=original_public(p)
    return {"image":q["image"],"direction":q["direction"],"mission":LEGACY}

class ThreeMissionControl:
    def __init__(self,parent):
        self.parent=parent
        self.missions={}
    @property
    def samples(self):return self.parent.samples
    def begin_episode(self):return self.parent.begin_episode()
    def learn(self,before,action,after,reward):
        original_public(before);original_public(after)
        if before["mission"]!=after["mission"]:
            raise ValueError("AC32_ORIGINAL_MISSION_DRIFT")
        if (type(action)is not int or action not in range(7)
            or type(reward)not in (int,float) or not math.isfinite(reward)
            or reward<0 or reward>1):
            raise ValueError("AC32_SELECTED_ACTION_OR_SOURCE_REWARD")
        self.parent.learn(blind_public(before),action,blind_public(after))
        rows=self.missions.setdefault(before["mission"],[
            {"count":0,"success":0} for _ in range(7)])
        rows[action]["count"]+=1
        rows[action]["success"]+=int(reward>0)
    def choose(self,before):
        original_public(before)
        rows=self.missions.get(before["mission"],[])
        choices=[(4096*cell["success"]//(cell["count"]+64),a)
                 for a,cell in enumerate(rows) if cell["success"]>0]
        if choices:
            best=max(score for score,_ in choices)
            return min(a for score,a in choices if score==best)
        return self.parent.choose(blind_public(before))
    def checkpoint(self):
        state={"schema":SCHEMA,"parent":self.parent.checkpoint().decode("utf-8"),
               "missions":self.missions}
        blob=canonical({"state":state,"sha256":sha(canonical(state))})
        if len(blob)>MAX_BYTES:raise ValueError("AC32_CONVENTIONAL_SNAPSHOT_SIZE")
        return blob
    @classmethod
    def restore(cls,blob,parent_restore):
        if type(blob)is not bytes or not 0<len(blob)<=MAX_BYTES:
            raise ValueError("AC32_INVALID_CONVENTIONAL_SNAPSHOT_SIZE")
        try:
            env=json.loads(blob)
            if type(env)is not dict or set(env)!={"state","sha256"}:
                raise ValueError("AC32_CONVENTIONAL_SNAPSHOT_FIELDS")
            state=env["state"]
            if (type(state)is not dict or set(state)!={"schema","parent","missions"}
                or state["schema"]!=SCHEMA or sha(canonical(state))!=env["sha256"]):
                raise ValueError("AC32_CONVENTIONAL_SNAPSHOT_HASH")
            parent=parent_restore(state["parent"].encode("utf-8"))
            out=cls(parent)
            rows=state["missions"]
            if (type(rows)is not dict or set(rows)-MISSIONS
                or any(type(sub)is not list or len(sub)!=7 or any(
                    type(x)is not dict or set(x)!={"count","success"} or
                    type(x["count"])is not int or type(x["success"])is not int or
                    not 0<=x["success"]<=x["count"]<=4096 for x in sub)
                    for sub in rows.values())):
                raise ValueError("AC32_CONVENTIONAL_SNAPSHOT_MISSION_OR_ROW")
            out.missions=rows
            if sum(x["count"] for sub in rows.values() for x in sub)!=out.samples:
                raise ValueError("AC32_CONVENTIONAL_FIT_SAMPLE_MISMATCH")
            if out.checkpoint()!=blob:
                raise ValueError("AC32_CONVENTIONAL_NONCANONICAL_CHECKPOINT")
            return out
        except (KeyError,TypeError,AttributeError,UnicodeError,OverflowError,
                RecursionError) as e:
            raise ValueError("AC32_CONVENTIONAL_INVALID_SNAPSHOT") from e
