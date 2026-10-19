"""F124-CY learned compositional parity transitions with causal role binding.

The candidate fits ONE shared causal transition matrix for all source-target
relationships (two matrices for pre-frozen event-bit switch), then maintains
three explicit online entity states. The basis is disclosed and privileged:
bitwise affine GF(2) composition, NOT arbitrary-rule discovery.

All fit state transitions are supervised with FIT ground truth. During CHECK
and HELDOUT evaluation no target label is fed to the state; all eight event
updates use the model's own autoregressive predictions.
"""
from __future__ import annotations
import hashlib
import json

ROLES=("alpha","beta","gamma")
REGIMES=("ungated_shared_linear_GF2","event_bit_gated_GF2")
VARS=21

def need(ok,reason):
    if not ok:raise ValueError("F124CY_COMPOSITION_"+reason)

def nib(x):
    return type(x) is int and 0<=x<16

def fbits(tc,tl,sc,sl,event):
    need(all(nib(v) for v in (tc,tl,sc,sl,event)),"ONLY_FIVE_PUBLIC_NIBBLES")
    return tc|(tl<<4)|(sc<<8)|(sl<<12)|(event<<16)|(1<<20)

def check_episode(ep):
    need(type(ep) is dict and set(ep)=={"initial","events"} and
         type(ep["initial"]) is dict and set(ep["initial"])==set(ROLES),
         "PUBLIC_ROLE_INIT_ONLY")
    need(all(type(v) is list and len(v)==2 and all(nib(x) for x in v)
         for v in ep["initial"].values()),"STATE_INIT_VALID")
    ev=ep["events"]
    need(type(ev) is list and len(ev)==8 and all(
        type(e) is dict and set(e)=={"target","source","event","observed"} and
        e["target"] in ROLES and e["source"] in ROLES and
        e["target"]!=e["source"] and nib(e["event"]) and nib(e["observed"])
        for e in ev),"EIGHT_CAUSAL_EVENTS_PUBLIC_ONLY")
    return True

def training_features(episodes,regime):
    need(regime in REGIMES,"FROZEN_OPERATOR_CLASS")
    buckets=[[] for _ in range(2 if regime==REGIMES[1] else 1)]
    for ep in episodes:
        check_episode(ep)
        state={k:list(v) for k,v in ep["initial"].items()}
        for row in ep["events"]:
            t=row["target"];source=row["source"]
            tc,tl=state[t];sc,sl=state[source]
            x=fbits(tc,tl,sc,sl,row["event"])
            gate=(row["event"]&1) if len(buckets)==2 else 0
            buckets[gate].append((x,row["observed"]))
            # Supervised assimilation allowed ONLY during FIT.
            state[t]=[row["observed"],tc]
    return buckets

def solve_gf2(rows,bit):
    # Exact Gauss-Jordan with deterministic leftmost pivot; zero free vars.
    # Train all bit outputs independently, never adapt based on CHECK.
    eq=[x | (((y>>bit)&1)<<VARS) for x,y in rows]
    pivot=[];top=0
    for col in range(VARS):
        i=next((i for i in range(top,len(eq)) if (eq[i]>>col)&1),None)
        if i is None:continue
        eq[top],eq[i]=eq[i],eq[top]
        for j in range(len(eq)):
            if j!=top and ((eq[j]>>col)&1):eq[j]^=eq[top]
        pivot.append(col)
        top+=1
        if top==len(eq):break
    impossible=any((row&((1<<VARS)-1))==0 and ((row>>VARS)&1)
                   for row in eq)
    if impossible:return None,top
    solution=0
    for i in reversed(range(len(pivot))):
        col=pivot[i]
        desired=(eq[i]>>VARS)&1
        remainder=(eq[i]&solution).bit_count()&1
        if desired^remainder:solution|=1<<col
    return solution,top

def fit(episodes,regime):
    need(type(episodes) is list and len(episodes)==24,
         "FROZEN_24_COMPLETE_FIT_EPISODES_ONLY")
    rows=training_features(episodes,regime)
    masks=[];ranks=[]
    for bucket in rows:
        fitted=[];rank=0
        for bit in range(4):
            m,k=solve_gf2(bucket,bit)
            if m is None:
                return None,{"FIT_inconsistent":True,"FIT_rows":len(episodes)*8,
                    "FIT_error_bits":None,"natural_admission":False}
            fitted.append(m);rank=max(rank,k)
        masks.append(tuple(fitted));ranks.append(rank)
    model={"regime":regime,"learned_bit_masks":tuple(masks),
           "independently_observed_gate_ranks":ranks,
           "learned_shared_operator_per_branch":True}
    mismatch=0
    for xs,ms in zip(rows,masks):
        mismatch+=sum(((predict_features(x,ms)^y).bit_count())
                      for x,y in xs)
    need(mismatch==0,"FIT_ALGEBRAIC_TRAINING_NOT_INTERPOLATED")
    return model,{"FIT_inconsistent":False,
        "FIT_rows":len(episodes)*8,"FIT_error_bits":mismatch,
        "gate_ranks":ranks,"natural_admission":True,
        "operator_basis":"public 20 raw bits and constant GF2 affine",
        "learned_equations":4*len(rows),
        "learned_shared_role_equivariant_parameters":True}

def predict_features(x,masks):
    return sum(((x&m).bit_count()&1)<<bit for bit,m in enumerate(masks))

def predict_event(model,event,state):
    t=event["target"];s=event["source"]
    tc,tl=state[t];sc,sl=state[s]
    gate=(event["event"]&1) if model["regime"]==REGIMES[1] else 0
    return predict_features(fbits(tc,tl,sc,sl,event["event"]),
                            model["learned_bit_masks"][gate])

def trajectory(model,ep):
    check_episode(ep)
    need(model is not None and model["regime"] in REGIMES,
         "FITTED_REUSABLE_COMPOSITION_ONLY")
    state={role:list(v) for role,v in ep["initial"].items()}
    outputs=[]
    for row in ep["events"]:
        t=row["target"]
        prior=state[t][0]
        y=predict_event(model,row,state)
        outputs.append(y)
        state[t]=[y,prior]
    return outputs

def score(model,ep):
    predictions=trajectory(model,ep)
    gold=[e["observed"] for e in ep["events"]]
    return {"correct":predictions==gold,
            "bit_errors":sum((y^t).bit_count() for y,t in zip(predictions,gold)),
            "native_event_calls":len(predictions)}

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,
                      separators=(",",":")).encode()).hexdigest()

if __name__=="__main__":
    raise SystemExit("F124CY_MODEL_ONLY_NO_SCIENTIFIC_CASE_BIRTH")
