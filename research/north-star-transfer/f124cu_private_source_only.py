"""F124-CU independent SOURCE-ONLY nonlinear three-entity episode origin.

Private OS entropy source birth runs separately BEFORE any learned model.
No prior causal-source generator, candidate, trained peer or evaluator import.
Never select source seeds or symbolic oracles based on model outcomes.
"""
from __future__ import annotations
import copy
import hashlib
import json
import random

ROLES=("alpha","beta","gamma")
BASE={"L":936000,"M":937000}

def need(ok,reason):
    if not ok:raise ValueError("F124CU_PRIVATE_SOURCE_"+reason)

def rot4(v,n):
    return ((v<<n)|(v>>(4-n)))&15

def law(family,event,target_cur,target_lag,source_cur,source_lag,key):
    need(family in BASE and len(key)==4 and
         all(type(x) is int and 0<=x<16 for x in
         (event,target_cur,target_lag,source_cur,source_lag,*key)),
         "BOUNDED_NEW_UNKNOWN_CAUSAL_RULE")
    k0,k1,k2,k3=key
    if family=="L":
        if (event^k0)&1:
            return (source_cur+rot4(target_lag,1)+k1)&15
        return (source_lag ^ ((target_cur+k2)&15) ^ k3)&15
    switch=((event^k0)&2)==((source_lag^target_cur)&2)
    if switch:
        return (rot4(source_cur,1)^rot4(target_cur,2)^((event+k1)&15))&15
    return ((source_cur*3+target_lag+k2)^rot4(source_lag^k3,1))&15

def episode(rng,family,key):
    initial={name:[rng.randrange(16),rng.randrange(16)] for name in ROLES}
    active=copy.deepcopy(initial)
    events=[]
    for i in range(8):
        target=ROLES[(i+rng.randrange(3))%3]
        source=ROLES[(ROLES.index(target)+1+rng.randrange(2))%3]
        event=rng.randrange(16)
        tc,tl=active[target]
        sc,sl=active[source]
        observed=law(family,event,tc,tl,sc,sl,key)
        events.append({"target":target,"source":source,
                       "event":event,"observed":observed})
        active[target]=[observed,tc]
    return {"initial":initial,"events":events}

def truth(ep,family,key):
    memory={role:list(v) for role,v in ep["initial"].items()}
    ok=True
    for x in ep["events"]:
        tc,tl=memory[x["target"]];sc,sl=memory[x["source"]]
        actual=law(family,x["event"],tc,tl,sc,sl,key)
        ok=bool(ok and actual==x["observed"])
        memory[x["target"]]=[actual,tc]
    return ok

def sha(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,
                 separators=(",",":")).encode()).hexdigest()

def task(family,ordinal,seed):
    need(family in BASE and type(ordinal) is int and 0<=ordinal<12
         and type(seed) is int and seed>0,"EXACT_NEW_FIRSTUSE_ID")
    rng=random.Random(seed)
    key=tuple(rng.randrange(16) for _ in range(4))
    fit=[episode(rng,family,key) for _ in range(24)]
    check=[episode(rng,family,key) for _ in range(8)]
    positive=episode(rng,family,key)
    negative=copy.deepcopy(positive)
    events=positive["events"]
    pair=next(((i,j) for i in range(8) for j in range(i+1,8)
               if events[i]["target"]!=events[j]["target"] and
               events[i]["observed"]!=events[j]["observed"]),None)
    need(pair is not None,"DISTINCT_CROSS_ROLE_HARD_NEGATIVE")
    i,j=pair
    negative["events"][i]["observed"],negative["events"][j]["observed"]=(
         negative["events"][j]["observed"],negative["events"][i]["observed"])
    need(truth(positive,family,key) and not truth(negative,family,key),
         "PRIVATE_SYMBOLIC_CAUSAL_ORACLE")
    need(positive["initial"]==negative["initial"] and
         [(e["target"],e["source"],e["event"]) for e in positive["events"]]==
         [(e["target"],e["source"],e["event"]) for e in negative["events"]] and
         sorted(e["observed"] for e in positive["events"])==
         sorted(e["observed"] for e in negative["events"]),
         "IDENTICAL_ROLE_INTERVENTION_AND_OBSERVATION_INVENTORY")
    identity=BASE[family]+ordinal
    public={"case_id":identity,"FIT":fit,"CHECK":check,
            "positive":positive,"hard_negative":negative}
    return {"schema":"mass.f124cu.internal-original-sequence-case.v1",
      "case_id":identity,
      "private_family":family,"private_OS_seed":str(seed),
      "private_causal_law_key":key,
      "symbolic_oracle":{"positive":True,"hard_negative":False},
      "public_task":public,"public_sha256":sha(public),
      "source_origin":"INTERNAL_NOT_EXTERNAL_REPLICATION",
      "previous_924_through_935_source_reused":False,
      "protected_source_opened":False}

if __name__=="__main__":
    raise SystemExit("SOURCE_ONLY_NO_AUTOMATIC_PRESCIENCE_BIRTH")
