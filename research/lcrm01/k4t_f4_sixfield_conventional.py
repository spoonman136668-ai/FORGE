#!/usr/bin/env python3
"""Fully FIT-trained conventional dynamics and routing with six public fields."""
from collections import Counter, defaultdict
import hashlib
import heapq
import json

NAMES=("X","Y","GoalX","GoalY","Direction","FrontBlocked")
def valid(s):
    return (type(s) is dict and set(s)==set(NAMES)
        and all(type(s[k]) is int and 0<=s[k]<=64 for k in NAMES[:4])
        and type(s["Direction"]) is int and s["Direction"] in (0,1,2,3)
        and type(s["FrontBlocked"]) is bool)
def pose(s):return (s["X"],s["Y"],s["Direction"])
def cell(s):return (s["X"],s["Y"])
def md(s):return abs(s["GoalX"]-s["X"])+abs(s["GoalY"]-s["Y"])

def fit(stream):
    if len(stream)!=12000:raise ValueError("F4_SIXFIELD_FIT_COUNT")
    learned=defaultdict(Counter)
    for event in stream:
        b,n,a=event["before"],event["after"],event["action"]
        if not valid(b) or not valid(n) or type(a) is not int or a not in (0,1,2):
            raise ValueError("F4_SIXFIELD_ILLEGAL_TRAINING")
        dx,dy=n["X"]-b["X"],n["Y"]-b["Y"]
        if abs(dx)>1 or abs(dy)>1:raise ValueError("F4_SIXFIELD_NONLOCAL_FIT")
        learned[(b["Direction"],b["FrontBlocked"],a)][(dx,dy,n["Direction"])]+=1
    if len(learned)!=24 or any(sum(c.values())<4 for c in learned.values()):
        raise ValueError("F4_SIXFIELD_INCOMPLETE_TRAINING")
    canonical=[(list(k),[(list(a),n) for a,n in sorted(c.items())])
               for k,c in sorted(learned.items())]
    digest=hashlib.sha256(json.dumps(canonical,separators=(",",":")).encode()).hexdigest()
    return learned,digest

class SixFieldConventional:
    def __init__(self,learned):
        self.learned=learned
        self.visits=Counter()
        self.blocked={}
        self.steps=0
        self.pending=None
    def predict(self,s,a):
        c=self.learned.get((s["Direction"],s["FrontBlocked"],a))
        if not c:return None
        v,count=sorted(c.items(),key=lambda item:(-item[1],item[0]))[0]
        total=sum(c.values())
        if total<4 or count*4<total*3:return None
        dx,dy,heading=v
        x,y=s["X"]+dx,s["Y"]+dy
        if not 0<=x<=64 or not 0<=y<=64:return None
        n=dict(s,X=x,Y=y,Direction=heading)
        n["FrontBlocked"]=self.blocked.get((x,y,heading),False)
        return n
    def choose(self,s):
        if not valid(s) or self.pending is not None:
            raise ValueError("F4_SIXFIELD_INVALID_CHOICE")
        start=dict(s)
        # Actual current public observation always outranks old local memory.
        search=[(0,0,0,start,None)]
        best={pose(start):0}
        counter=0
        winner=None
        best_score=1<<30
        while search and counter<2048:
            travel,depth,_,at,first=heapq.heappop(search)
            if depth>=36:continue
            for a in (0,1,2):
                nxt=self.predict(at,a)
                if nxt is None or pose(nxt)==pose(at):continue
                start_action=a if first is None else first
                cost=travel+18+(6 if a!=2 else 0)+32*self.visits[cell(nxt)]
                key=pose(nxt)
                if cost>=best.get(key,1<<30):continue
                best[key]=cost
                if len(best)>2048:continue
                if cell(nxt)!=cell(start):
                    score=cost+6*md(nxt)-(24 if self.visits[cell(nxt)]==0 else 0)
                    if score<best_score:best_score=score;winner=start_action
                counter+=1
                if counter<2048:
                    heapq.heappush(search,(cost,depth+1,counter,nxt,start_action))
        if winner is None:
            for action in (2,0,1):
                n=self.predict(start,action)
                if n is not None and pose(n)!=pose(start):
                    winner=action
                    break
            if winner is None:winner=0
        self.pending=(dict(s),winner)
        return winner
    def feedback(self,b,action,n):
        if (not valid(b) or not valid(n) or self.pending is None
            or self.pending!=(b,action)):
            raise ValueError("F4_SIXFIELD_UNSELECTED_ACTION_OR_INVALID_FEEDBACK")
        if abs(b["X"]-n["X"])>1 or abs(b["Y"]-n["Y"])>1:
            raise ValueError("F4_SIXFIELD_NONLOCAL_ACTUAL_CONSEQUENCE")
        self.visits[cell(b)]+=1
        self.blocked[pose(b)]=b["FrontBlocked"]
        self.steps+=1
        self.pending=None
