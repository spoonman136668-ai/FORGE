"""F124-DA learn a reusable causal OPERATOR PROGRAM, not a supplied law.

FIT exhaustively identifies consistent two-step compositions from a frozen
public four-primitive six-operand grammar. Explicit role-current/lag memory
is maintained autoregressively on CHECK and heldout. No import of source
generator, hidden program, prior scientific evidence or independent peer.
"""
from __future__ import annotations
import hashlib
import itertools
import json

ROLES=("alpha","beta","gamma")
PRIMITIVES=("xor4","add4","and4","or4")
OPERANDS=6
GRAMMAR_SIZE=4*4*6**3

def ensure(ok,reason):
    if not ok: raise ValueError("F124DA_OPERATOR_"+reason)

def combine(name,left,right):
    if name=="xor4":return left^right
    if name=="add4":return (left+right)&15
    if name=="and4":return left&right
    if name=="or4":return left|right
    raise ValueError("UNREGISTERED_CAUSAL_OPERATOR")

def inputs(tc,tl,sc,sl,event):
    ensure(all(type(v) is int and 0<=v<16 for v in (tc,tl,sc,sl,event)),
           "PUBLIC_NIBBLE")
    return (tc,tl,sc,sl,event,((event<<1)|(event>>3))&15)

def compute(program,values):
    op1,op2,a,b,c=program
    return combine(op2,combine(op1,values[a],values[b]),values[c])

def validate(ep):
    ensure(type(ep) is dict and set(ep)=={"initial","events"} and
           type(ep["initial"]) is dict and set(ep["initial"])==set(ROLES),
           "PUBLIC_EPISODE_ONLY")
    ensure(all(type(s) is list and len(s)==2 and
           all(type(q) is int and 0<=q<16 for q in s)
           for s in ep["initial"].values()),"INITIAL_THREE_ROLES")
    es=ep["events"]
    ensure(type(es) is list and len(es)==8 and all(
        type(e) is dict and set(e)=={"target","source","event","observed"}
        and e["target"] in ROLES and e["source"] in ROLES
        and e["source"]!=e["target"]
        and type(e["event"]) is int and 0<=e["event"]<16
        and type(e["observed"]) is int and 0<=e["observed"]<16
        for e in es),"EXACT_PUBLIC_EIGHT_EVENT_CAUSAL_EPISODE")

def rows(fit):
    ensure(type(fit) is list and len(fit)==24,
           "EXACT_24_FIT_SUPERVISED_SEQUENCES")
    out=[]
    for ep in fit:
        validate(ep)
        states={role:list(v) for role,v in ep["initial"].items()}
        for e in ep["events"]:
            t=e["target"];s=e["source"]
            tc,tl=states[t];sc,sl=states[s]
            out.append((inputs(tc,tl,sc,sl,e["event"]),e["observed"]))
            states[t]=[e["observed"],tc] # TRAIN labels only
    ensure(len(out)==192,"ALL_192_FIT_TRANSITIONS")
    return out

def programs():
    for op1 in PRIMITIVES:
        for op2 in PRIMITIVES:
            for a,b,c in itertools.product(range(OPERANDS),repeat=3):
                yield (op1,op2,a,b,c)

def fit(episodes):
    observations=rows(episodes)
    survivors=[]
    tested=0
    for prog in programs():
        tested+=1
        if all(compute(prog,values)==target for values,target in observations):
            survivors.append(prog)
    ensure(tested==GRAMMAR_SIZE,"ENTIRE_3456_PROGRAM_CLASS_EVALUATED")
    if not survivors:
        return None,{"fit_consistent":False,"programs_exhaustively_checked":tested,
                     "consistent_programs":0,"natural_model_fitted":False,
                     "FIT_rows":192,"source_grammar_not_guaranteed":True}
    selected=survivors[0]
    return {"program":list(selected)},{
        "fit_consistent":True,"natural_model_fitted":True,
        "programs_exhaustively_checked":tested,
        "consistent_programs":len(survivors),
        "selected_program":list(selected),
        "FIT_rows":192,"FIT_bit_errors":0,
        "actual_operator_topology_fit_from_FIT_only":True,
        "CHECK_heldout_not_used_for_selection":True}

def predict(model,ep):
    validate(ep)
    ensure(type(model) is dict and set(model)=={"program"},
           "NATURALLY_FITTED_CAUSAL_PROGRAM_REQUIRED")
    pr=model["program"]
    state={role:list(v) for role,v in ep["initial"].items()}
    output=[]
    for row in ep["events"]:
        tc,tl=state[row["target"]];sc,sl=state[row["source"]]
        value=compute(pr,inputs(tc,tl,sc,sl,row["event"]))
        output.append(value)
        state[row["target"]]=[value,tc] # predict, NEVER gold
    return output

def score(model,ep):
    a=predict(model,ep)
    b=[x["observed"] for x in ep["events"]]
    return {"correct":a==b,"bit_errors":sum((x^y).bit_count() for x,y in zip(a,b)),
            "native_event_count":len(a)}

def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,
       separators=(",",":")).encode()).hexdigest()

if __name__=="__main__":
    raise SystemExit("SOURCEFREE_LEARNED_CAUSAL_PROGRAM_ONLY")
