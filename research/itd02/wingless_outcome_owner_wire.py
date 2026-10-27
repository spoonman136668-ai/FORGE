#!/usr/bin/env python3
"""FORGE-owned ITD-02 Wingless outcome-wire custody contract.

This module NEVER executes an environment, authenticates supplied source
observations, or grants FSA/first-use. Original F5 code and evidence are frozen.
An eventual FORGE source owner must validate original MiniGrid source identity,
issue its own execution receipt and supply only source-public observations.
"""
import hashlib
import json
import math

SCHEMA = "forge.itd02.wingless-outcome-owner-wire.v1"
BRIDGE_OPS = frozenset(("choose", "feedback", "episode_start", "snapshot", "load"))
PUBLIC_KEYS = frozenset(("X", "Y", "Direction", "GoalX", "GoalY", "FrontBlocked"))

def public_grid(record):
    if type(record) is not dict or set(record) != PUBLIC_KEYS:
        raise ValueError("OUTCOME_OWNER_PUBLIC_FIELDS")
    values = {k: record[k] for k in PUBLIC_KEYS}
    for k in ("X", "Y", "GoalX", "GoalY"):
        if type(values[k]) is not int or not 0 <= values[k] <= 64:
            raise ValueError("OUTCOME_OWNER_PUBLIC_GRID_BOUNDS")
    if type(values["Direction"]) is not int or not 0 <= values["Direction"] <= 3:
        raise ValueError("OUTCOME_OWNER_PUBLIC_HEADING")
    if type(values["FrontBlocked"]) is not bool:
        raise ValueError("OUTCOME_OWNER_PUBLIC_FRONT")
    return {k: values[k] for k in ("X","Y","Direction","GoalX","GoalY","FrontBlocked")}

def strict_reply(reply, expected):
    if type(reply) is not dict or reply.get("ok") is not True:
        raise ValueError("OUTCOME_OWNER_BRIDGE_REJECTED")
    if expected == "choose":
        if type(reply.get("action")) is not int or reply["action"] not in (0,1,2):
            raise ValueError("OUTCOME_OWNER_BRIDGE_ACTION")
    elif expected == "feedback":
        if type(reply.get("updates")) is not int or reply["updates"] < 1:
            raise ValueError("OUTCOME_OWNER_BRIDGE_UPDATE")
    return reply

class SourceCustody:
    """Source owner invokes choose then source step then feedback, never reverse.

    The bridge is a callable accepting a JSON-shaped request and returning
    a reply. Source authenticity is deliberately NOT inferred from this.
    """
    def __init__(self, bridge):
        if not callable(bridge):
            raise TypeError("bridge must be callable")
        self.bridge = bridge
        self.pending = None
        self.next_id = 1
        self.closed = False
        self.transcript = []

    def _call(self, request, operation):
        response = strict_reply(self.bridge(request), operation)
        return response

    def choose(self, before, min_count=2):
        public = public_grid(before)
        if self.pending is not None or self.closed or type(min_count) is not int or min_count < 2:
            raise ValueError("OUTCOME_OWNER_PENDING_OR_CLOSED")
        response = self._call({"op":"choose","before":public,"min_count":min_count},"choose")
        self.pending = (public, response["action"])
        return response["action"]

    def feedback(self, before, action, after, reward, terminal, truncated, event_id):
        old = public_grid(before)
        nxt = public_grid(after)
        if (self.closed or self.pending != (old,action)
            or type(action) is not int or action not in (0,1,2)
            or type(event_id) is not int or event_id != self.next_id
            or type(terminal) is not bool or type(truncated) is not bool
            or (terminal and truncated) or type(reward) not in (int,float)
            or not math.isfinite(reward) or abs(reward)>1000000):
            raise ValueError("OUTCOME_OWNER_FEEDBACK_CUSTODY")
        request = {"op":"feedback","before":old,"after":nxt,
                   "action":action,"reward":float(reward),
                   "terminal":terminal,"truncated":truncated,
                   "event_id":event_id}
        reply=self._call(request,"feedback")
        if reply["updates"] != self.next_id:
            raise ValueError("OUTCOME_OWNER_UPDATE_MISMATCH")
        wire=json.dumps(request,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
        self.transcript.append(hashlib.sha256(wire).hexdigest())
        self.next_id += 1
        self.pending = None
        self.closed = terminal or truncated

    def begin_episode(self):
        if self.pending is not None or not self.closed:
            raise ValueError("OUTCOME_OWNER_RESET_BOUNDARY")
        self._call({"op":"episode_start"},"episode_start")
        self.closed=False

    def engineering_receipt(self):
        if self.pending is not None:
            raise ValueError("OUTCOME_OWNER_UNRESOLVED_ACTION")
        return {"schema":SCHEMA,"observed_feedback_count":self.next_id-1,
                "public_wire_sha256":hashlib.sha256(
                    json.dumps(self.transcript,separators=(",",":")).encode()).hexdigest(),
                "source_authenticated":False,"scientific_first_use":False,
                "scientific_accepted":False,"evidence_class":"public-wire-engineering-only"}
