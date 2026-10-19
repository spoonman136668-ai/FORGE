"""F124-DA source-neutral FIT-learned causal PROGRAM SYNTAX discovery.

Searches all 3456 public depth-two syntax trees
    y = OP_OUTER(OP_INNER(xA,xB),xC)
from four primitive ALU operators and six public role/event inputs.
The architecture supplies a finite *operator library*, NOT the selected
source program nor its AST topology. Source hidden programs not imported.
All 24 FIT sequences used for model discovery; veto-only CHECK never used
to select or retune. Full online eight-step predictions are autoregressive.
"""
from __future__ import annotations
import hashlib
import itertools
import json

ROLES=("alpha","beta","gamma")
OPERATIONS=("xor4","add4","and4","or4")
ARGNAMES=("target_current","target_lag","source_current",
          "source_lag","event","rotl1_event")
COUNT=4*4*6*6*6

def need(ok,msg):
    if not ok:raise ValueError("F124DA_PROGRAM_"+msg)

def validate(ep):
    need(type(ep) is dict and set(ep)=={"initial","events"} and
         type(ep["initial"]) is dict and set(ep["initial"])==set(ROLES),
         "PUBLIC_EPISODE_BOUNDARY")
    need(all(type(v) is list and len(v)==2 and all(type(x) is int and 0<=x<16
         for x in v) for v in ep["initial"].values()),"ROLE_INIT")
    need(type(ep["events"]) is list and len(ep["events"])==8 and all(
         type(e) is dict and set(e)=={"target","source","event","observed"} and
         e["target"] in ROLES and e["source"] in ROLES and e["target"]!=e["source"] and
         type(e["event"]) is int and 0<=e["event"]<16 and
         type(e["observed"]) is int and 0<=e["observed"]<16
         for e in ep["events"]),"EIGHT_PUBLIC_CAUSAL_STEPS")

def op(i,a,b):
    if i==0:return a^b
    if i==1:return (a+b)&15
    if i==2:return a&b
    if i==3:return a|b
    raise ValueError("F124DA_INVALID_ALU_OPERATION")

def public_values(state,event):
    t=event["target"];s=event["source"];e=event["event"]
    tc,tl=state[t];sc,sl=state[s]
    return tc,tl,sc,sl,e,((e<<1)|(e>>3))&15

def all_programs():
    for inner in range(4):
        for outer in range(4):
            for a in range(6):
                for b in range(6):
                    for c in range(6):
                        yield inner,outer,a,b,c

def invoke(program,vals):
    inner,outer,a,b,c=program
    return op(outer,op(inner,vals[a],vals[b]),vals[c])

def fit_rows(episodes):
    need(type(episodes) is list and len(episodes)==24,"FIXED_24_FULL_FIT")
    rows=[]
    for ep in episodes:
        validate(ep)
        state={k:list(v) for k,v in ep["initial"].items()}
        for e in ep["events"]:
            rows.append((public_values(state,e),e["observed"]))
            previous=state[e["target"]][0]
            state[e["target"]]=[e["observed"],previous]
    return rows

def choose_from_rows(rows):
    best=None;count=0
    for program in all_programs():
        if all(invoke(program,values)==observed for values,observed in rows):
            count+=1
            if best is None:best=program
    return best,count

def train(fit):
    rows=fit_rows(fit)
    selected,total=choose_from_rows(rows)
    return ({"discovered_program":selected} if selected is not None else None),{
        "syntax_trees_searched":COUNT,"all_24_FIT_sequences_consumed":True,
        "FIT_event_rows":len(rows),"FIT_consistent_programs":total,
        "FIT_exact_program_found":selected is not None,
        "program_discovered_not_given":True,
        "operator_library_disclosed":True,"grammar_complete_search":True,
        "CHECK_or_HELDOUT_in_fit":False}

def trajectory(model,episode):
    validate(episode)
    need(model is not None and model["discovered_program"] is not None,
         "NATURALLY_FITTED_PROGRAM_REQUIRED")
    state={role:list(v) for role,v in episode["initial"].items()}
    result=[]
    for event in episode["events"]:
        y=invoke(model["discovered_program"],public_values(state,event))
        old=state[event["target"]][0]
        state[event["target"]]=[y,old]
        result.append(y)
    return result

def score(model,episode):
    found=trajectory(model,episode)
    observed=[e["observed"] for e in episode["events"]]
    return {"correct":found==observed,
            "bit_errors":sum((a^b).bit_count() for a,b in zip(found,observed)),
            "native_event_calls":8}

def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,
      separators=(",",":")).encode()).hexdigest()
