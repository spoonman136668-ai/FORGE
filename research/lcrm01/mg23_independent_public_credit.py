"""MG23-C: independently coded conventional public action/context credit control.

Separate from native Wingless/Yggdrasil sources. Accepts only source-public
image/direction/mission and selected original actions/outcomes. Its mission
binding is a literal public observation matcher, not a task-action oracle.
No original-world episodes in this module.
"""
from __future__ import annotations
import hashlib
import json
import math

SCHEMA="itd02.mg23.independent-public-selected-delayed-credit-control.v1"
MAX_EVENTS=4096
MAX_CONTEXTS=4096
WINDOW=32
MAX_SNAPSHOT=5500000
COLORS={"red":0,"green":1,"blue":2,"purple":3,"yellow":4,"grey":5}
OBJECTS={"key":5,"ball":6,"box":7}
DOORKEY="use the key to open the door and then get to the goal"
GOAL="get to the green goal square"

def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=True,
                      allow_nan=False).encode("ascii")

def digest(x):
    return hashlib.sha256(canonical(x)).hexdigest()

def allowed(frame):
    if type(frame) is not dict or set(frame)!={"image","direction","mission"}:
        raise ValueError("MG23C_SOURCE_PUBLIC_FIELDS")
    m=frame["mission"]
    if type(m) is not str or len(m)>96:
        raise ValueError("MG23C_SOURCE_MISSION")
    if m not in (DOORKEY,GOAL):
        if not m.startswith("pick up the "):
            raise ValueError("MG23C_SOURCE_MISSION")
        words=m[len("pick up the "):].split(" ")
        if not 2<=len(words)<=4 or any(not w or not all("a"<=c<="z" for c in w)
                                        for w in words):
            raise ValueError("MG23C_SOURCE_MISSION")
    d=frame["direction"]
    if type(d) is not int or d not in range(4):
        raise ValueError("MG23C_SOURCE_DIRECTION")
    image=frame["image"]
    if type(image) is not list or len(image)!=7:
        raise ValueError("MG23C_SOURCE_IMAGE")
    for row in image:
        if type(row) is not list or len(row)!=7:
            raise ValueError("MG23C_SOURCE_IMAGE_ROW")
        for pixel in row:
            if (type(pixel) is not list or len(pixel)!=3 or
                any(type(n) is not int or n<0 or n>255 for n in pixel)):
                raise ValueError("MG23C_SOURCE_PIXEL")
    return frame

def context(frame):
    allowed(frame)
    return digest({"mission":frame["mission"],"direction":frame["direction"],
                   "front":frame["image"][3][5]})

def selected_target(before,selected,after):
    if selected!=3 or before["direction"]!=after["direction"]:
        return False
    m=before["mission"]
    if not m.startswith("pick up the "):
        return False
    words=m[len("pick up the "):].split(" ")
    if len(words)!=2 or words[0] not in COLORS or words[1] not in OBJECTS:
        return False
    old=before["image"][3][5]
    new=after["image"][3][5]
    return old[0]==OBJECTS[words[1]] and old[1]==COLORS[words[0]] and new[0]==1

def blank():
    return [{"count":0,"target":0,"delayed":0} for _ in range(7)]

class Conventional:
    def __init__(self,target=True,delayed=True):
        if type(target) is not bool or type(delayed) is not bool:
            raise ValueError("MG23C_ABLATION_FLAGS")
        self.target=target
        self.delayed=delayed
        self.cells={}
        self.trace=[]
        self.samples=0
        self.pending=None

    def _valid(self):
        if (type(self.cells) is not dict or type(self.trace) is not list or
            type(self.samples) is not int or self.samples<0 or
            self.samples>MAX_EVENTS or len(self.cells)>MAX_CONTEXTS or
            len(self.trace)>WINDOW):
            raise ValueError("MG23C_BOUNDS")
        total=0
        for key,row in self.cells.items():
            if (type(key) is not str or len(key)!=64 or
                any(c not in "0123456789abcdef" for c in key) or
                type(row) is not list or len(row)!=7):
                raise ValueError("MG23C_CELL_CONTEXT")
            for stat in row:
                if (type(stat) is not dict or set(stat)!={"count","target","delayed"}
                    or any(type(stat[k]) is not int or stat[k]<0 for k in stat)
                    or stat["target"]>stat["count"]
                    or (not self.target and stat["target"]!=0)
                    or (not self.delayed and stat["delayed"]!=0)):
                    raise ValueError("MG23C_CELL_VALUE")
                total+=stat["count"]
        if total!=self.samples:
            raise ValueError("MG23C_SOURCE_EVENT_COUNT")
        for entry in self.trace:
            if (type(entry) is not dict or set(entry)!={"context","action"} or
                entry["context"] not in self.cells or
                type(entry["action"]) is not int or entry["action"] not in range(7)):
                raise ValueError("MG23C_ELIGIBILITY")
        if self.pending is not None:
            p=self.pending
            if (type(p) is not dict or set(p)!={"source_sha256","action"} or
                type(p["source_sha256"]) is not str or len(p["source_sha256"])!=64 or
                type(p["action"]) is not int or p["action"] not in range(7)):
                raise ValueError("MG23C_OUTSTANDING_SELECTED_SOURCE")

    def begin_episode(self):
        self._valid()
        if self.pending is not None:
            raise ValueError("MG23C_PENDING_CANNOT_RESET")
        self.trace=[]

    def choose(self,before):
        self._valid()
        if self.pending is not None:
            raise ValueError("MG23C_PENDING_CANNOT_CHOOSE")
        key=context(before)
        row=self.cells.get(key,blank())
        counts=[v["count"] for v in row]
        least=min(counts)
        start=int(key[:2],16)%7
        baseline=next((start+i)%7 for i in range(7)
                      if counts[(start+i)%7]==least)
        high=0
        best=baseline
        for action,cell in enumerate(row):
            if cell["count"]==0:
                continue
            score=8*cell["target"]+cell["delayed"]
            if score>high:
                high=score
                best=action
        if high:
            return best,"CONVENTIONAL_SELECTED_PUBLIC_TARGET_OR_TERMINAL_CREDIT"
        return baseline,"CONVENTIONAL_PUBLIC_LEAST_SELECTED"

    def submit(self,before,action):
        self._valid()
        if self.pending is not None or type(action) is not int or action not in range(7):
            raise ValueError("MG23C_INVALID_SELECTED_SUBMISSION")
        allowed(before)
        self.pending={"source_sha256":digest(before),"action":action}
        return action

    def learn(self,before,action,after,reward,terminal,selected=False):
        self._valid()
        allowed(before)
        allowed(after)
        if (before["mission"]!=after["mission"] or
            type(action) is not int or action not in range(7) or
            type(reward) not in (int,float) or not math.isfinite(reward) or
            type(terminal) is not bool or not -1<=reward<=1):
            raise ValueError("MG23C_ORIGINAL_SOURCE_FEEDBACK_INVALID")
        if selected:
            if (self.pending is None or
                self.pending!={"source_sha256":digest(before),"action":action}):
                raise ValueError("MG23C_NOT_OWN_SELECTED_ACTION")
        elif self.pending is not None:
            raise ValueError("MG23C_FIT_DURING_PENDING_LIVE_ACTION")
        if self.samples>=MAX_EVENTS:
            raise ValueError("MG23C_SOURCE_EVENT_CAP")
        key=context(before)
        if key not in self.cells and len(self.cells)>=MAX_CONTEXTS:
            raise ValueError("MG23C_SOURCE_CONTEXT_CAP")
        item=self.cells.setdefault(key,blank())[action]
        item["count"]+=1
        if self.target and selected_target(before,action,after):
            item["target"]+=1
        self.samples+=1
        self.trace.append({"context":key,"action":action})
        if len(self.trace)>WINDOW:
            self.trace=self.trace[-WINDOW:]
        if self.delayed and terminal and reward>0:
            for age,entry in enumerate(reversed(self.trace)):
                self.cells[entry["context"]][entry["action"]]["delayed"]+=WINDOW-age
        self.pending=None
        self._valid()

    def snapshot(self):
        self._valid()
        if self.pending is not None:
            raise ValueError("MG23C_SNAPSHOT_WITH_SELECTED_UNRETURNED_ACTION")
        state={"schema":SCHEMA,"target":self.target,"delayed":self.delayed,
               "cells":self.cells,"trace":self.trace,"samples":self.samples}
        raw=canonical({"state":state,"sha256":digest(state)})
        if len(raw)>MAX_SNAPSHOT:
            raise ValueError("MG23C_CHECKPOINT_SIZE")
        return raw

    @classmethod
    def restore(cls,raw):
        try:
            if type(raw) is not bytes or not 0<len(raw)<=MAX_SNAPSHOT:
                raise ValueError("MG23C_CHECKPOINT_SIZE")
            envelope=json.loads(raw)
            if type(envelope) is not dict or set(envelope)!={"state","sha256"}:
                raise ValueError("MG23C_CHECKPOINT_WIRE")
            s=envelope["state"]
            if (type(s) is not dict or set(s)!={"schema","target","delayed","cells","trace","samples"} or
                s["schema"]!=SCHEMA):
                raise ValueError("MG23C_CHECKPOINT_SCHEMA")
            if digest(s)!=envelope["sha256"]:
                raise ValueError("MG23C_CHECKPOINT_SHA")
            obj=cls(s["target"],s["delayed"])
            obj.cells=s["cells"];obj.trace=s["trace"];obj.samples=s["samples"]
            obj._valid()
            if obj.snapshot()!=raw:
                raise ValueError("MG23C_CHECKPOINT_NOT_CANONICAL")
            return obj
        except (ValueError,TypeError,KeyError,OverflowError) as exc:
            raise ValueError("MG23C_UNTRUSTED_ORIGINAL_SOURCE_CHECKPOINT") from exc
