"""R18 genuine original mission boundary and mission-specific selected-outcome cells.

The untouched native R17 only supports DoorKey's constant mission. R18 accepts
the true original mission and privately projects legacy input to R17, retaining
actual source mission and learning reward-conditioned action evidence. No
mission->action oracle, tokenizer, or hardwired navigation behavior.
"""
from __future__ import annotations
import hashlib,json
from research.native.itd02.r10.public_adapter import DoorKeyPublicAdapter,canonical,digest,public_observation,MISSION
from research.native.itd02.r17.successor_cells import SuccessorCells

SCHEMA="yggdrasil.itd02.r18.actual-original-mission-native.v1"
MISSIONS=(MISSION,"get to the green goal square")
MAX_CHECKPOINT=850000

def projected(original):
    if type(original)is not dict or set(original)!={"image","direction","mission"}:
        raise ValueError("R18_ORIGINAL_PUBLIC_KEYS")
    if type(original["mission"])is not str or original["mission"] not in MISSIONS:
        raise ValueError("R18_UNREGISTERED_ORIGINAL_MISSION")
    # Original source image and direction reach unchanged native R17 verbatim.
    return public_observation(dict(original,mission=MISSION))

def validate(original):
    return projected(original)

def new_stat():
    return [{"count":0,"success":0} for _ in range(7)]

class OriginalMissionAdapter:
    """Genuine source mission custody linked to original R10 selected ledger."""
    def __init__(self):
        self.inner=DoorKeyPublicAdapter()
        self.current=None
        self.pending=None
        self.ledger=[]
        self.events=0
    def reset_public(self,source):
        p=projected(source)
        self.inner.reset_public(p)
        self.current=source
        self.pending=None
        self.ledger=[]
        self.events=0
    def submit(self,action):
        if self.current is None or self.pending is not None:
            raise ValueError("R18_ORIGINAL_SELECTED_PHASE")
        if type(action)is not int or action not in range(7):
            raise ValueError("R18_SOURCE_ACTION_RANGE")
        value=self.inner.submit(action)
        self.pending=action
        return value
    def complete(self,after,reward,terminated,truncated):
        if self.pending is None or self.current is None:
            raise ValueError("R18_SOURCE_FEEDBACK_NOT_SELECTED")
        p=projected(after)
        if after["mission"]!=self.current["mission"]:
            raise ValueError("R18_MISSION_CHANGED_IN_ONE_SOURCE_EPISODE")
        before=self.current
        result=self.inner.complete(p,reward,terminated,truncated)
        self.ledger.append({
            "action":self.pending,"before_sha":digest(before),
            "after_sha":digest(after),"mission":before["mission"],
            "reward":float(reward),"terminal":bool(terminated or truncated)
        })
        self.current=after
        self.events+=1
        self.pending=None
        return result

class MissionCells:
    def __init__(self,parent=None):
        self.parent=SuccessorCells() if parent is None else parent
        if type(self.parent)is not SuccessorCells:
            raise ValueError("R18_INVALID_NATIVE_PARENT")
        self.missions={}
        self.consumed=0
    @property
    def samples(self):
        return self.parent.samples
    def _valid(self):
        if (len(self.missions)>2 or self.consumed!=self.samples or
            set(self.missions)-set(MISSIONS)):
            raise ValueError("R18_SELECTED_ORIGINAL_MISSION_DRIFT")
        count=0
        for mission,stats in self.missions.items():
            if type(stats)is not list or len(stats)!=7:
                raise ValueError("R18_MISSION_STAT_SHAPE")
            for row in stats:
                if (type(row)is not dict or set(row)!={"count","success"} or
                    type(row["count"])is not int or type(row["success"])is not int or
                    row["count"]<0 or row["success"]<0 or row["success"]>row["count"]):
                    raise ValueError("R18_MISSION_STAT_COUNT")
                count+=row["count"]
        if count!=self.consumed:
            raise ValueError("R18_SOURCE_COUNTERS")
    def start_session(self,adapter,name,live=False):
        self._valid()
        if type(adapter)is not OriginalMissionAdapter:
            raise ValueError("R18_NATIVE_SOURCE_ADAPTER")
        self.parent.start_session(adapter.inner,name,live=live)
    def choose(self,before):
        self._valid()
        p=projected(before)
        proposal=self.parent.choose(p)
        highest=0;best=None
        for action,stat in enumerate(self.missions.get(before["mission"],new_stat())):
            if not stat["success"]:
                continue
            value=4096*stat["success"]//(stat["count"]+64)
            if value>highest:highest=value;best=action
        if best is not None:
            return {"schema":SCHEMA,"action":best,
                    "status":"SELECT_NATIVE_GENUINE_MISSION_SELECTED_REWARD",
                    "external_fallback":False}
        return {"schema":SCHEMA,"action":proposal["action"],
                "status":proposal["status"],"external_fallback":False}
    def learn_selected(self,adapter,before,after):
        self._valid()
        p=projected(before);q=projected(after)
        if (type(adapter)is not OriginalMissionAdapter or
            before["mission"]!=after["mission"] or
            adapter.pending is not None or adapter.current!=after or
            adapter.inner.current!=q or not adapter.ledger or
            adapter.events!=adapter.inner.events or
            adapter.inner.events!=self.parent.parent.local.local.cursor+1):
            raise ValueError("R18_NO_AUTHENTIC_SELECTED_FEEDBACK")
        entry=adapter.ledger[-1]
        if (entry["before_sha"]!=digest(before) or
            entry["after_sha"]!=digest(after) or
            entry["mission"]!=before["mission"] or
            type(entry["action"])is not int or entry["action"] not in range(7) or
            adapter.inner.ledger[-1]["action"]!=entry["action"]):
            raise ValueError("R18_SOURCE_MISSION_RECEIPT_MISMATCH")
        receipt=self.parent.learn_selected(adapter.inner,p,q)
        stats=self.missions.setdefault(before["mission"],new_stat())
        one=stats[entry["action"]]
        one["count"]+=1
        if entry["reward"]>0:one["success"]+=1
        self.consumed+=1
        self._valid()
        return receipt
    def checkpoint(self):
        self._valid()
        state={"schema":SCHEMA,"parent":self.parent.checkpoint().decode(),
               "missions":self.missions,"consumed":self.consumed}
        result=canonical({"state":state,"sha256":hashlib.sha256(canonical(state)).hexdigest()})
        if len(result)>MAX_CHECKPOINT:
            raise ValueError("R18_SNAPSHOT_SIZE")
        return result
    @classmethod
    def restore(cls,blob):
        try:
            if type(blob)is not bytes or not 0<len(blob)<=MAX_CHECKPOINT:
                raise ValueError("R18_CHECKPOINT_SIZE")
            wire=json.loads(blob)
            if type(wire)is not dict or set(wire)!={"state","sha256"}:
                raise ValueError("R18_CHECKPOINT_ENVELOPE")
            s=wire["state"]
            if (type(s)is not dict or set(s)!={"schema","parent","missions","consumed"}
                or s["schema"]!=SCHEMA or
                hashlib.sha256(canonical(s)).hexdigest()!=wire["sha256"] or
                type(s["consumed"])is not int or type(s["missions"])is not dict):
                raise ValueError("R18_CHECKPOINT_SHA")
            p=SuccessorCells.restore(s["parent"].encode())
            agent=cls(p);agent.consumed=s["consumed"];agent.missions=s["missions"]
            agent._valid()
            if agent.checkpoint()!=blob:
                raise ValueError("R18_CHECKPOINT_NONCANONICAL")
            return agent
        except (ValueError,TypeError,KeyError,UnicodeError,AttributeError) as exc:
            raise ValueError("R18_UNTRUSTED_CHECKPOINT") from exc
