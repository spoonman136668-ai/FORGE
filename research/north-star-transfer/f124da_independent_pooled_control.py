"""F124-DA independent FULLY TRAINED pooled two-stage program competitor.

Separate implementation, no import of candidate or source. Learns over
identical 3456-program grammar, identical 24 FIT sequential public examples,
same frozen ordering and no CHECK/heldout tuning. This is the principal
strongest comparator; a candidate tie cannot count as unique advance.
"""
from __future__ import annotations

ROLES=("alpha","beta","gamma")
OPS=("xor4","add4","and4","or4")
POSITIONS=range(6)

def valid(ep):
    if type(ep) is not dict or set(ep)!={"initial","events"} or set(ep["initial"])!=set(ROLES):
        raise ValueError("DA_PEER_PUBLIC_EPISODE")
    if not all(type(x) is list and len(x)==2 and
               all(type(t) is int and 0<=t<16 for t in x)
               for x in ep["initial"].values()):
        raise ValueError("DA_PEER_BOUND_INIT")
    if type(ep["events"]) is not list or len(ep["events"])!=8 or not all(
       type(x) is dict and set(x)=={"target","source","event","observed"}
       and x["target"] in ROLES and x["source"] in ROLES
       and x["target"]!=x["source"]
       and type(x["event"]) is int and 0<=x["event"]<16
       and type(x["observed"]) is int and 0<=x["observed"]<16
       for x in ep["events"]):raise ValueError("DA_PEER_PUBLIC_EVENTS")

def binop(which,x,y):
    if which==0:return x^y
    if which==1:return (x+y)&15
    if which==2:return x&y
    if which==3:return x|y
    raise ValueError("PEER_OP_OUTSIDE_FROZEN_GRAMMAR")

def state_inputs(state,row):
    own=state[row["target"]]
    origin=state[row["source"]]
    e=row["event"]
    return (own[0],own[1],origin[0],origin[1],e,
            ((e<<1)|(e>>3))&15)

def build_examples(episodes):
    if type(episodes) is not list or len(episodes)!=24:
        raise ValueError("DA_PEER_NO_COMPLETE_FIT")
    out=[]
    for ep in episodes:
        valid(ep)
        state={k:list(v) for k,v in ep["initial"].items()}
        for row in ep["events"]:
            out.append((state_inputs(state,row),row["observed"]))
            old=state[row["target"]][0]
            state[row["target"]]=[row["observed"],old]
    if len(out)!=192:raise ValueError("DA_PEER_192_FIT_EVENTS")
    return out

def evaluate(program,features):
    i,j,a,b,c=program
    return binop(j,binop(i,features[a],features[b]),features[c])

def fully_train(fit):
    observations=build_examples(fit)
    retained=[]
    n=0
    for outerop in range(4):
        for innerop in range(4):
            for a in POSITIONS:
                for b in POSITIONS:
                    for c in POSITIONS:
                        # Order is mapped to same public grammar priority
                        # via the canonical tuple (inner,outer,a,b,c).
                        prog=(innerop,outerop,a,b,c)
                        n+=1
                        for x,y in observations:
                            if evaluate(prog,x)!=y:
                                break
                        else:retained.append(prog)
    if n!=3456:raise RuntimeError("DA_PEER_NOT_FULLY_EXHAUSTIVE")
    retained.sort()
    if not retained:return None,{
        "fit_consistent":False,"natural_model_fitted":False,
        "independently_tested_programs":n,"consistent_programs":0,
        "training_events":192}
    chosen=retained[0]
    return {"program":chosen},{
        "fit_consistent":True,"natural_model_fitted":True,
        "independently_tested_programs":n,
        "consistent_programs":len(retained),
        "training_events":192,"FIT_bit_errors":0,
        "independent_source_neutral_exhaustive_search":True,
        "CHECK_and_HELDOUT_never_train":True}

def trajectory(model,episode):
    valid(episode)
    if model is None:raise ValueError("DA_PEER_UNFITTED")
    memory={role:list(values) for role,values in episode["initial"].items()}
    output=[]
    for e in episode["events"]:
        y=evaluate(model["program"],state_inputs(memory,e))
        old=memory[e["target"]][0]
        memory[e["target"]]=[y,old]
        output.append(y)
    return output

def score(model,ep):
    predicted=trajectory(model,ep)
    actual=[e["observed"] for e in ep["events"]]
    return {"correct":predicted==actual,
            "bit_errors":sum((a^b).bit_count() for a,b in zip(predicted,actual)),
            "native_event_count":len(predicted)}
