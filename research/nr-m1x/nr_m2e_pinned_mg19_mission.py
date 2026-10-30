"""MG19: opt-in original MiniGrid mission and independently local source-credit cells.

Exact source mission survives outside the frozen DoorKey-only R20 adapter.
R17 contextual native selector remains the new-mission fallback. The inside
R20/R18/DoorKey compatibility projection is not a semantic language model.
This is source-only, no new original-world scientific results.
"""
from __future__ import annotations
import hashlib
import json
import math

from research.native.itd02.r10.public_adapter import canonical,digest,MISSION
from research.native.itd02.r18.mission_cells import (
    OriginalMissionAdapter as OriginalMissionAdapterR18,
    projected as old_projected
)
from research.native.itd02.r20.state_credit_cells import StateCreditCells

SCHEMA="yggdrasil.itd02.mg19.genuine-mission-selected-local-credit.v1"
MAX_SAMPLES=4096
MAX_CONTEXTS=4096
MAX_CHECKPOINT=3500000
LEGACY=(MISSION,"get to the green goal square")


def admitted(mission):
    if type(mission) is not str:
        return False
    if mission in LEGACY:
        return True
    if not mission.startswith("pick up the ") or len(mission)>96:
        return False
    parts=mission[len("pick up the "):].split(" ")
    return 2<=len(parts)<=4 and all(
        word and all("a"<=ch<="z" for ch in word) for word in parts
    )


def original_public(p):
    if type(p) is not dict or set(p)!={"image","direction","mission"}:
        raise ValueError("MG19_ORIGINAL_PUBLIC_FIELDS")
    if not admitted(p["mission"]):
        raise ValueError("MG19_UNADMITTED_GENUINE_SOURCE_MISSION")
    legacy=dict(p,mission=MISSION)
    old_projected(legacy)  # frozen exact image/direction public verification
    if type(p["direction"]) is not int:
        raise ValueError("MG19_NONCANONICAL_DIRECTION")
    return p


def legacy_public(p):
    original_public(p)
    if p["mission"] in LEGACY:
        return p  # preserve exact DoorKey and goal-only parent behavior
    return old_projected(dict(p,mission=MISSION))


def blank():
    return [{"count":0,"positive":0} for _ in range(7)]


class OriginalMissionAdapter:
    """Exact original source mission provenance above R18's DoorKey-only adapter."""
    def __init__(self):
        self.inner=OriginalMissionAdapterR18()
        self.current=None
        self.pending=None
        self.events=0
        self.ledger=[]

    def reset_public(self,frame):
        original_public(frame)
        if self.pending is not None:
            raise ValueError("MG19_RESET_WITH_OUTSTANDING_SOURCE_ACTION")
        self.inner.reset_public(legacy_public(frame))
        self.current=frame
        self.pending=None
        self.events=0
        self.ledger=[]

    def submit(self,action):
        if self.current is None or self.pending is not None:
            raise ValueError("MG19_NO_ORIGINAL_SOURCE_SELECTION")
        if type(action) is not int or action not in range(7):
            raise ValueError("MG19_NON_NATIVE_ACTION")
        returned=self.inner.submit(action)
        if returned!=action:
            raise ValueError("MG19_ORIGINAL_ACTION_REMAP")
        self.pending=action
        return action

    def complete(self,after,reward,terminated,truncated):
        original_public(after)
        if self.pending is None or self.current is None:
            raise ValueError("MG19_SOURCE_FEEDBACK_NOT_SELECTED")
        if self.current["mission"]!=after["mission"]:
            raise ValueError("MG19_ORIGINAL_SOURCE_MISSION_CHANGED")
        if type(reward) not in (int,float) or not math.isfinite(reward) or not -1<=reward<=1:
            raise ValueError("MG19_UNTRUSTED_ORIGINAL_REWARD")
        if type(terminated) is not bool or type(truncated) is not bool:
            raise ValueError("MG19_ORIGINAL_TERMINATION_TYPE")
        before=self.current
        selected=self.pending
        result=self.inner.complete(legacy_public(after),float(reward),terminated,truncated)
        self.ledger.append({"index":self.events+1,"action":selected,
            "before_sha":digest(before),"after_sha":digest(after),
            "mission":before["mission"],"reward":float(reward),
            "terminal":terminated or truncated})
        self.current=after
        self.pending=None
        self.events+=1
        return result

