#!/usr/bin/env python3
"""MG23 independently coded conventional selected-public context/eligibility baseline.

Gets precisely a selected original public before/action/after plus real reward.
No privileged map, inventory, external navigator, task routes, or imagined events.
Not a claim of equal algorithmic prior, capacity, or compute to native agents.
"""
from __future__ import annotations
import hashlib,json,math,re

SCHEMA="itd02.mg23.conventional-source-public-count-target-delayed-baseline.v1"
WINDOW=32
MAX_SAMPLES=4096
MAX_CONTEXTS=4096
MAX_CHECKPOINT=5500000
COLORS={"red":0,"green":1,"blue":2,"purple":3,"yellow":4,"grey":5}
OBJECTS={"key":5,"ball":6,"box":7}
LEGACY=("use the key to open the door and then get to the goal",
        "get to the green goal square")

def canonical(v):
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("ascii")

def hash_value(v):
    return hashlib.sha256(canonical(v)).hexdigest()

def source_public(p):
    if type(p) is not dict or set(p)!={"image","direction","mission"}:
        raise ValueError("MG23_CONVENTIONAL_PUBLIC_FIELDS")
    if type(p["direction"]) is not int or p["direction"] not in range(4):
        raise ValueError("MG23_CONVENTIONAL_SOURCE_HEADING")
    m=p["mission"]
    if (type(m) is not str or len(m)>96 or
        (m not in LEGACY and not (m.startswith("pick up the ") and
         len(m.split(" "))>=5 and all(t and t.isascii() and t.islower() and t.isalpha()
                                     for t in m[len("pick up the "):].split(" "))))):
        raise ValueError("MG23_CONVENTIONAL_MISSION_REJECT")
    image=p["image"]
    if (type(image) is not list or len(image)!=7 or any(type(row) is not list or len(row)!=7
        or any(type(cell) is not list or len(cell)!=3 or
        any(type(v) is not int or v not in range(256) for v in cell)
        for cell in row) for row in image)):
        raise ValueError("MG23_CONVENTIONAL_SOURCE_PUBLIC_IMAGE")
    return p

def observed_context(p):
    p=source_public(p)
    return hash_value({"mission":p["mission"],"direction":p["direction"],
                       "front":p["image"][3][5]})

def target_disappeared(b,a,selected):
    if selected!=3 or b["direction"]!=a["direction"]:
        return False
    terms=b["mission"].split(" ")
    if len(terms)!=5 or terms[:3]!=["pick","up","the"]:
        return False
    obj=OBJECTS.get(terms[-1])
    col=COLORS.get(terms[-2])
    return obj is not None and col is not None and b["image"][3][5][0]==obj and b["image"][3][5][1]==col and a["image"][3][5][0]==1

def empty():
    return [{"count":0,"target":0,"delayed":0} for _ in range(7)]

class ConventionalSelected:
    def __init__(self):
        self.table={}
        self.trace=[]
        self.pending=None
        self.samples=0
        self.episodes=0

    def _check(self):
        if (type(self.table) is not dict or len(self.table)>MAX_CONTEXTS or
            type(self.trace) is not list or len(self.trace)>WINDOW or
            type(self.samples) is not int or not 0<=self.samples<=MAX_SAMPLES):
            raise ValueError("MG23_CONVENTIONAL_MEMORY_BOUNDS")
        count=0
        for k,row in self.table.items():
            if not re.fullmatch("[a-f0-9]{64}",k) or type(row)is not list or len(row)!=7:
                raise ValueError("MG23_CONVENTIONAL_CORRUPT_CONTEXT")
            for cell in row:
                if (type(cell)is not dict or set(cell)!={"count","target","delayed"} or
                    any(type(v)is not int or v<0 for v in cell.values()) or
                    cell["target"]>cell["count"]):
                    raise ValueError("MG23_CONVENTIONAL_CORRUPT_LOCAL_CREDIT")
                count+=cell["count"]
        if count!=self.samples:
            raise ValueError("MG23_CONVENTIONAL_SOURCE_RECEIPT_MISMATCH")
        for x in self.trace:
            if (type(x)is not dict or set(x)!={"context","action"} or
                x["context"] not in self.table or
                type(x["action"]) is not int or x["action"] not in range(7)):
                raise ValueError("MG23_CONVENTIONAL_UNTRUSTED_ELIGIBILITY")
        if self.pending is not None and (type(self.pending) is not dict or
            set(self.pending)!={"before","action"} or
            type(self.pending["action"]) is not int or
            self.pending["action"] not in range(7) or
            not re.fullmatch("[a-f0-9]{64}",self.pending["before"])):
            raise ValueError("MG23_CONVENTIONAL_UNSELECTED_PENDING")

    def begin_episode(self):
        self._check()
        if self.pending is not None:
            raise ValueError("MG23_CONVENTIONAL_PENDING_EPISODE")
        self.episodes+=1
        self.trace=[]

    def choose(self,before):
        self._check()
        if self.pending is not None:
            raise ValueError("MG23_CONVENTIONAL_UNRECEIPTED_ACTION")
        key=observed_context(before)
        row=self.table.get(key,empty())
        top=max(8*c["target"]+c["delayed"] for c in row)
        if top>0:
            choices=[a for a,c in enumerate(row) if 8*c["target"]+c["delayed"]==top]
            # Source-stable hash tie; not external task or action oracle.
            return choices[int(key[:4],16)%len(choices)]
        counts=[c["count"] for c in row]
        choices=[i for i,n in enumerate(counts) if n==min(counts)]
        return choices[int(key[:4],16)%len(choices)]

    def commit(self,before,action):
        self._check()
        if self.pending is not None or type(action) is not int or action not in range(7):
            raise ValueError("MG23_CONVENTIONAL_INVALID_SELECTED_COMMIT")
        self.pending={"before":hash_value(source_public(before)),"action":action}

    def observe_fit(self,before,action,after,reward,terminal):
        return self._learn(before,action,after,reward,terminal,live=False)

    def feedback(self,before,action,after,reward,terminal):
        return self._learn(before,action,after,reward,terminal,live=True)

    def _learn(self,before,action,after,reward,terminal,live):
        self._check()
        source_public(before);source_public(after)
        if (before["mission"]!=after["mission"] or
            type(action) is not int or action not in range(7) or
            type(reward) not in (float,int) or not math.isfinite(reward) or
            not -1<=reward<=1 or type(terminal)is not bool or
            self.samples>=MAX_SAMPLES):
            raise ValueError("MG23_CONVENTIONAL_SELECTED_SOURCE_BAD")
        if live:
            if self.pending!={"before":hash_value(before),"action":action}:
                raise ValueError("MG23_CONVENTIONAL_WRONG_SELECTED_ACTION")
        elif self.pending is not None:
            raise ValueError("MG23_CONVENTIONAL_FIT_WHILE_PENDING")
        key=observed_context(before)
        if key not in self.table and len(self.table)>=MAX_CONTEXTS:
            raise ValueError("MG23_CONVENTIONAL_CONTEXT_CAP")
        row=self.table.setdefault(key,empty())
        row[action]["count"]+=1
        if target_disappeared(before,after,action):
            row[action]["target"]+=1
        self.trace.append({"context":key,"action":action})
        if len(self.trace)>WINDOW:self.trace=self.trace[-WINDOW:]
        if terminal and reward>0:
            for age,step in enumerate(reversed(self.trace)):
                self.table[step["context"]][step["action"]]["delayed"]+=WINDOW-age
        self.samples+=1
        self.pending=None
        self._check()
        return self.samples

    def checkpoint(self):
        self._check()
        if self.pending is not None:
            raise ValueError("MG23_CONVENTIONAL_PENDING_CHECKPOINT")
        state={"schema":SCHEMA,"table":self.table,"trace":self.trace,
               "samples":self.samples,"episodes":self.episodes}
        raw=canonical({"state":state,"sha256":hash_value(state)})
        if len(raw)>MAX_CHECKPOINT:
            raise ValueError("MG23_CONVENTIONAL_CHECKPOINT_CAP")
        return raw

    @classmethod
    def restore(cls,raw):
        try:
            if type(raw) is not bytes or not 0<len(raw)<=MAX_CHECKPOINT:
                raise ValueError("MG23_CONVENTIONAL_CHECKPOINT_SIZE")
            record=json.loads(raw)
            if type(record)is not dict or set(record)!={"state","sha256"}:
                raise ValueError("MG23_CONVENTIONAL_CHECKPOINT_FIELDS")
            s=record["state"]
            if (type(s)is not dict or set(s)!={"schema","table","trace","samples","episodes"} or
                s["schema"]!=SCHEMA or hash_value(s)!=record["sha256"] or
                type(s["episodes"])is not int or s["episodes"]<0):
                raise ValueError("MG23_CONVENTIONAL_CHECKPOINT_SHA")
            obj=cls()
            obj.table=s["table"];obj.trace=s["trace"]
            obj.samples=s["samples"];obj.episodes=s["episodes"]
            obj._check()
            if obj.checkpoint()!=raw:
                raise ValueError("MG23_CONVENTIONAL_NONCANONICAL_CHECKPOINT")
            return obj
        except (KeyError,TypeError,ValueError,AttributeError,UnicodeError) as exc:
            raise ValueError("MG23_CONVENTIONAL_UNTRUSTED_SOURCE_SNAPSHOT") from exc
