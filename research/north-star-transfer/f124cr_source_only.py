"""F124-CR source-only internally originated J/K causal trajectories.

Origin has NO model import and NEVER scores candidate/control predictions.
Unknown OS seeds generated only after frozen preregistration, in separate job.
Private oracle/parameters remain solely in the sealed birth artifact.
"""
import copy
import hashlib
import json
import random

BASE={"J":934000,"K":935000}
ROLES=("north","south")

def need(ok,msg):
    if not ok: raise ValueError("F124CR_SOURCE_"+msg)

def rot(x,n):
    return ((x<<n)|(x>>(4-n)))&15

def law(family,event,current,lagged,secret):
    need(family in BASE and all(type(x) is int and 0<=x<16 for x in
         (event,current,lagged,*secret)) and len(secret)==4,"HIDDEN_LAW_INPUT")
    k0,k1,k2,k3=secret
    if family=="J":
        # Intervention changes whether a delayed state or local source drives
        # the future state; coefficients are independent of learned-model code.
        switch=((event^k0)&3)==((lagged^k1)&3)
        return ((rot(current^event,1)+lagged+k2)&15) if switch else (
            (rot(lagged,2)^current^event^k3)&15)
    # Distinct nonlinear delayed law with context-conditioned causal order:
    branch=((current^lagged^k1)&1)
    first=((current*(event|1))+lagged+k0)&15
    second=((lagged*(current|1))+rot(event,3)+k2)&15
    return (first^rot(second,2)) if branch else (second^rot(first,1)^k3)&15

def truth(graph,family,secret):
    states={role:list(pair) for role,pair in graph["initial"].items()}
    correct=True
    for row in graph["events"]:
        curr,lag=states[row["role"]]
        target=law(family,row["event"],curr,lag,secret)
        correct=bool(correct and row["observed"]==target)
        states[row["role"]]=[target,curr]
    return correct

def digest(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def task(family,index,seed):
    need(family in BASE and type(index) is int and 0<=index<12 and
         type(seed) is int and seed>0,"ONLY_NEW_DEVELOPMENT_ROSTER")
    rng=random.Random(seed)
    key=tuple(rng.randrange(16) for _ in range(4))
    public_samples=rng.sample(range(4096),48)
    rows=[]
    for x in public_samples:
        event=x&15;current=(x>>4)&15;lag=(x>>8)&15
        rows.append([event,current,lag,law(family,event,current,lag,key)])
    count=8+2*(index%2)
    initial={role:[rng.randrange(16),rng.randrange(16)] for role in ROLES}
    states=copy.deepcopy(initial)
    events=[]
    for j in range(count):
        role=ROLES[j%2]
        event=rng.randrange(16)
        current,lag=states[role]
        target=law(family,event,current,lag,key)
        events.append({"role":role,"event":event,"observed":target})
        states[role]=[target,current]
    positive={"initial":initial,"events":events}
    negative=copy.deepcopy(positive)
    pair=next(((i,j) for i in range(count) for j in range(i+1,count)
             if events[i]["role"]!=events[j]["role"] and
             events[i]["observed"]!=events[j]["observed"]),None)
    need(pair is not None,"HARD_NEGATIVE_PAIR_NOT_BORN")
    i,j=pair
    negative["events"][i]["observed"],negative["events"][j]["observed"]=(
        negative["events"][j]["observed"],negative["events"][i]["observed"])
    need(truth(positive,family,key) and not truth(negative,family,key),
         "ORACLE_MATCHED_CAUSAL_PAIR")
    need(positive["initial"]==negative["initial"] and
         [(x["role"],x["event"]) for x in positive["events"]]==
         [(x["role"],x["event"]) for x in negative["events"]] and
         sorted(x["observed"] for x in positive["events"])==
         sorted(x["observed"] for x in negative["events"]),
         "EQUAL_OBSERVATION_INVENTORY_AND_TOPOLOGY")
    case=BASE[family]+index
    pub={"case_id":case,"FIT":rows[:40],"CHECK":rows[40:],
         "positive":positive,"hard_negative":negative}
    return {"schema":"mass.f124cr.original-source-private-case.v1",
      "case_id":case,"private_family":family,"private_seed":str(seed),
      "private_law_parameters":key,
      "oracle_positive":True,"oracle_negative":False,
      "public_task":pub,"public_sha256":digest(pub),
      "internal_source_only_not_external_replication":True,
      "old_924_through_933_cases_used":False,"protected_cohort_opened":False}

if __name__=="__main__":raise SystemExit("SOURCE_ONLY_NO_AUTOMATIC_CASE_BIRTH")
