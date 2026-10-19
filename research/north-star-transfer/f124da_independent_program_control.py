"""F124-DA independently authored fully exhaustive syntax-search control.

Exact SAME four operations, six public features, and 3456 tree hypotheses
as candidate. Independent implementation, no candidate imports, no hidden
generator/oracle imports. Exact fit on complete 24 sequential FIT episodes.
No CHECK/holdout model updates. Role-neutral (pooled) strong control.
"""
from __future__ import annotations

ROLES=("alpha","beta","gamma")
OP_NAMES=("xor4","add4","and4","or4")
FEATURES=("target_current","target_lag","source_current","source_lag",
          "event","rotl1_event")

def verify(ep):
    if not isinstance(ep,dict) or set(ep)!={"initial","events"} or set(ep["initial"])!=set(ROLES):
        raise ValueError("DA_PEER_PUBLIC_EPISODE")
    if len(ep["events"])!=8 or not all(set(e)=={"target","source","event","observed"}
      and e["target"] in ROLES and e["source"] in ROLES and e["target"]!=e["source"]
      and type(e["event"]) is int and 0<=e["event"]<16 and type(e["observed"]) is int
      and 0<=e["observed"]<16 for e in ep["events"]):
        raise ValueError("DA_PEER_EIGHT_PUBLIC_EVENTS")
    if not all(len(pair)==2 and all(type(x) is int and 0<=x<16 for x in pair)
               for pair in ep["initial"].values()):
        raise ValueError("DA_PEER_BOUNDED_INIT")

def primitives(index,x,y):
    return (x^y,(x+y)&15,x&y,x|y)[index]

def vector(memory,event):
    t=memory[event["target"]];s=memory[event["source"]];e=event["event"]
    return (t[0],t[1],s[0],s[1],e,((e*2)|(e>>3))&15)

def compute(program,values):
    i,j,a,b,c=program
    return primitives(j,primitives(i,values[a],values[b]),values[c])

def candidate_programs():
    return ((i,j,a,b,c) for i in range(4) for j in range(4)
             for a in range(6) for b in range(6) for c in range(6))

def learn_from_rows(rows):
    best=None;count=0
    for program in candidate_programs():
        if all(compute(program,v)==y for v,y in rows):
            count+=1
            if best is None:best=program
    return best,count

def train(fit):
    if type(fit) is not list or len(fit)!=24:raise ValueError("DA_PEER_FIT_ONLY")
    records=[]
    for ep in fit:
        verify(ep)
        memory={k:list(v) for k,v in ep["initial"].items()}
        for e in ep["events"]:
            records.append((vector(memory,e),e["observed"]))
            previous=memory[e["target"]][0]
            memory[e["target"]]=[e["observed"],previous]
    best,total=learn_from_rows(records)
    model=({"program":best} if best is not None else None)
    return model,{"fully_fit_24_episodes":True,"FIT_rows":len(records),
        "programs_exhaustively_considered":3456,
        "consistent_programs":total,"model_found":model is not None,
        "same_six_features_and_four_ops_as_candidate":True,
        "no_CHECK_or_HELDOUT_fit":True}

def predict(model,ep):
    verify(ep)
    if model is None:raise ValueError("DA_PEER_UNFITTED")
    memory={k:list(v) for k,v in ep["initial"].items()}
    predicted=[]
    for e in ep["events"]:
        y=compute(model["program"],vector(memory,e))
        previous=memory[e["target"]][0]
        memory[e["target"]]=[y,previous]
        predicted.append(y)
    return predicted

def score(model,ep):
    guess=predict(model,ep);true=[e["observed"] for e in ep["events"]]
    return {"correct":guess==true,"bit_errors":sum((a^b).bit_count() for a,b in zip(guess,true)),
      "native_event_calls":8}
