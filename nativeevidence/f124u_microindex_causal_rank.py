"""F124-U: bounded Wingless microindex and learned ranking-only Yggdrasil.

No additional persistent Wingless key/latent state and no accumulated
Yggdrasil value-credit. This is a development source experiment, not
protected confirmation or compute-matched scientific acceptance.
"""
from __future__ import annotations
from collections import defaultdict
import hashlib
import json
import math
import random
import struct

import f124s_native_mechanisms as s_model
import f124o_native_learners as old
import f124u_fresh_source as source

EPOCHS=12
BATCH=8
PERTURB=.08
LR=.04
YGG_INIT=[0.,0.]


def need(x,msg):
    source.need(x,"F124U_MECHANISM_"+msg)


def sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,
         separators=(",",":")).encode()).hexdigest()


def wingless_microindex(g,base,delta):
    source.validate_public(g)
    need(len(base)==7 and len(delta)==2 and
         all(math.isfinite(v) for v in list(base)+list(delta)),
         "WING_WEIGHTS")
    edges=old.sorted_edges(g)
    # Frozen 4 candidate role/node keys and a hard maximum of 8 indexed
    # edges. Unknown keys fall back to full exact scan; never truncate data.
    keys=[]
    cost={"public_edge_scans":0,"raw_bit_ops":0,
          "causal_key_comparisons":0,"max_active":1,"max_retained":0,
          "evictions":0,"state_limit":3,
          "serialized_state_payload_bytes":10,
          "reference_serialized_state_payload_bytes":40,
          "index_entries":0,"index_candidate_keys":0,
          "index_lookups":0,"fallback_scans":0,"cache_hits":0,
          "max_key_cache_entries":0,"extra_scratch_memory_present":True}
    for e in edges:
        cost["public_edge_scans"]+=1
        key=(e["from"],e["role"])
        if key not in keys and len(keys)<4:
            keys.append(key)
    cost["index_candidate_keys"]=len(keys)
    index={}
    used=0
    for key in keys:
        matches=[e for e in edges if (e["from"],e["role"])==key]
        cost["public_edge_scans"]+=len(edges)
        if used+len(matches)<=8:
            index[key]=matches
            used+=len(matches)
    cost["index_entries"]=used
    need(used<=8 and len(keys)<=4,"MICROINDEX_CAPACITY")
    cache={}
    vectors={}
    def pack(raw):
        k=tuple(raw)
        if k in cache:
            cost["cache_hits"]+=1
            return cache[k]
        cost["raw_bit_ops"]+=16
        n=s_model.bits_to_uint16(raw)
        if len(cache)+len(vectors)<8:
            cache[k]=n
        cost["max_key_cache_entries"]=max(
            cost["max_key_cache_entries"],len(cache)+len(vectors))
        return n
    def vec(k):
        if k in vectors:
            cost["cache_hits"]+=1
            return vectors[k]
        cost["raw_bit_ops"]+=16
        v=tuple((2*((k>>(4*j))&15).bit_count()-4)/4. for j in range(4))
        if len(cache)+len(vectors)<8:
            vectors[k]=v
        cost["max_key_cache_entries"]=max(
            cost["max_key_cache_entries"],len(cache)+len(vectors))
        return v
    mix=old.sigmoid(delta[0])
    temp=1.+.2*math.tanh(delta[1])
    w=[1.,1.,1.,1.]+list(base[4:])
    def affinity(a,b):
        cost["raw_bit_ops"]+=20
        cost["causal_key_comparisons"]+=1
        av,bv=vec(a),vec(b)
        latent=1.-sum(abs(x-y) for x,y in zip(av,bv))/8.
        raw=(16-(a^b).bit_count())/16.
        return temp*((1.-mix)*latent+mix*raw)
    def lookup(node,role):
        cost["index_lookups"]+=1
        key=(node,role)
        if key in index:
            matches=index[key]
            cost["public_edge_scans"]+=len(matches)
            return matches
        cost["fallback_scans"]+=1
        cost["public_edge_scans"]+=len(edges)
        return [e for e in edges if (e["from"],e["role"])==key]
    state={g["start"]:[s_model.STATE.pack(0.,0)]}
    for hop,role in enumerate(g["roles"]):
        nextr=g["roles"][hop+1] if hop+1<len(g["roles"]) else None
        proposal=defaultdict(list)
        for node in sorted(state):
            available=lookup(node,role)
            for rec in state[node]:
                need(type(rec) is bytes and len(rec)==10,"PACKED_RECORD_ID")
                score,carried=s_model.STATE.unpack(rec)
                for e in available:
                    src=pack(e["src_bits"]); dst=pack(e["dst_bits"])
                    compat=1. if hop==0 else affinity(carried,src)
                    value=score+w[4]*(compat-.6)
                    if nextr is None:
                        look=0.
                    else:
                        query=lookup(e["to"],nextr)
                        look=max((affinity(dst,pack(q["src_bits"]))
                                  for q in query),default=0.)
                    priority=value+w[5]*(look-.6)
                    proposal[e["to"]].append((priority,
                                            s_model.STATE.pack(value,dst)))
        state={}
        for node,options in proposal.items():
            options.sort(key=lambda x:(-x[0],x[1]))
            cost["evictions"]+=max(0,len(options)-3)
            state[node]=[rec for _,rec in options[:3]]
        cost["max_active"]=max(cost["max_active"],sum(len(x) for x in state.values()))
        need(cost["max_active"]<=192 and
             all(len(x)<=3 for x in state.values()) and
             cost["max_key_cache_entries"]<=8,
             "PERSISTENT_AND_TEMP_BUDGET")
    scores=[s_model.STATE.unpack(rec)[0]
            for rec in state.get(g["target"],[])]
    best=max(scores,default=-2.*len(g["roles"]))
    z=4.*(best/max(1,len(g["roles"])-1)-w[6])
    need(math.isfinite(z),"WING_FINITE")
    return z,cost


def ygg_rank(g,base,delta):
    source.validate_public(g)
    need(len(base)==7 and len(delta)==2 and
         all(math.isfinite(v) for v in list(base)+list(delta)),
         "YGG_WEIGHTS")
    edges=old.sorted_edges(g)
    active=[(g["start"],None,0.)]
    retained=[]
    cost={"public_edge_scans":0,"raw_bit_ops":0,
          "lookahead_comparisons":0,"max_active":1,
          "max_retained":0,"evictions":0,
          "active_cell_limit":7,"retained_cell_limit":9}
    def sim(carried,src):
        if carried is None:
            return 1.
        cost["raw_bit_ops"]+=16
        return sum(base[j]*sum(int(a==b) for a,b in zip(
            carried[j*4:j*4+4],src[j*4:j*4+4]))/4.
            for j in range(4))/4.
    def future(edge,nextrole):
        if nextrole is None:
            return .5
        candidates=[e for e in edges if e["from"]==edge["to"] and
                    e["role"]==nextrole]
        cost["public_edge_scans"]+=len(edges)
        cost["lookahead_comparisons"]+=len(candidates)
        cost["raw_bit_ops"]+=16*len(candidates)
        return max((sum(int(a==b) for a,b in zip(edge["dst_bits"],
                        q["src_bits"]))/16. for q in candidates),
                   default=0.)
    for h,role in enumerate(g["roles"]):
        nextr=g["roles"][h+1] if h+1<len(g["roles"]) else None
        choices=[]
        for node,carried,score in active+retained:
            cost["public_edge_scans"]+=len(edges)
            for e in edges:
                if e["from"]!=node or e["role"]!=role:
                    continue
                similarity=sim(carried,e["src_bits"])
                value=score+base[4]*(similarity-.35) # no learned value credit
                rank=base[5]*(similarity-.5)
                conf=old.sigmoid(6.*(similarity-.5))-.5
                prospect=future(e,nextr)-.5
                priority=rank+delta[0]*conf+delta[1]*prospect
                cell=(e["to"],tuple(e["dst_bits"]),value)
                choices.append((value+priority,value-priority,cell))
        choices.sort(key=lambda x:(-x[0],-x[1],x[2][0],x[2][1]))
        active=[row[2] for row in choices[:7]]
        ids={id(x) for x in choices[:7]}
        extras=[row for row in choices if id(row) not in ids]
        extras.sort(key=lambda x:(-x[1],-x[0],x[2][0],x[2][1]))
        retained=[row[2] for row in extras[:9]]
        cost["evictions"]+=max(0,len(choices)-16)
        cost["max_active"]=max(cost["max_active"],len(active))
        cost["max_retained"]=max(cost["max_retained"],len(retained))
        need(len(active)<=7 and len(retained)<=9 and
             len(active)+len(retained)<=16,"YGG_7_9_BUDGET")
    target=[v for node,_,v in active+retained if node==g["target"]]
    best=max(target,default=-2.*len(g["roles"]))
    z=4.*(best/max(1,len(g["roles"])-1)-base[6])
    need(math.isfinite(z),"YGG_FINITE")
    return z,cost


def soft_routing(g,delta):
    """Public role-constrained soft path continuity for FIT-only surrogate.

    No exact causal admission/oracle used. Candidate weights are smooth in
    both parameters even without a hard 7+9 ranking switch.
    """
    source.validate_public(g)
    edges=old.sorted_edges(g)
    states={(g["start"],None):1.}
    for h,role in enumerate(g["roles"]):
        nextr=g["roles"][h+1] if h+1<len(g["roles"]) else None
        nxt=defaultdict(float)
        for (node,carried),mass in states.items():
            for e in edges:
                if e["from"]!=node or e["role"]!=role:
                    continue
                if carried is None:
                    affinity=.5
                else:
                    affinity=sum(int(a==b) for a,b in zip(
                        carried,e["src_bits"]))/16.
                if nextr is None:
                    future=.5
                else:
                    future=max((sum(int(a==b) for a,b in zip(
                        e["dst_bits"],q["src_bits"]))/16.
                        for q in edges if q["from"]==e["to"] and
                        q["role"]==nextr),default=0.)
                x=delta[0]*(affinity-.5)+delta[1]*(future-.5)
                w=old.sigmoid(x)
                nxt[(e["to"],tuple(e["dst_bits"]))]+=mass*w
        states=nxt
        # Exact no capacity expansion within deployed cognition; this is
        # FIT loss generator only. Bound computational path enumeration.
        need(len(states)<=16384,"FIT_SURROGATE_STATE_EXPLOSION")
    return math.log(max(1e-12,sum(v for (node,_),v in states.items()
                                   if node==g["target"])))


def fit_pairs():
    source.frozen()
    return [source.build("Yggdrasil",seed,v,"FIT")
            for v in source.VECTORS
            for seed in source.COHORTS["Yggdrasil"]["FIT"]]


def loss(pairs,base,delta):
    total=0.
    def sp(x):return max(0.,x)+math.log1p(math.exp(-abs(x)))
    for pos,neg in pairs:
        a,_=ygg_rank(pos,base,delta)
        b,_=ygg_rank(neg,base,delta)
        # Both discrete real-model FIT log loss and independent differentiable
        # source-public causal-key surrogate; no DEV or protected examples.
        s1=soft_routing(pos,delta)
        s0=soft_routing(neg,delta)
        total+=sp(-a)+sp(b)+.15*sp(b-a)+.25*(sp(-s1)+sp(s0))
    return total/len(pairs)


def train_ygg(base):
    pairs=fit_pairs()
    need(len(pairs)==48 and len(base)==7,"YGG_FULL_FIT")
    delta=list(YGG_INIT)
    initial=loss(pairs,base,delta)
    rng=random.Random(int.from_bytes(hashlib.sha256(
        b"F124U/FIT/SPSA/v1/Yggdrasil").digest()[:12],"big"))
    steps=0
    for _ in range(EPOCHS):
        order=list(range(48));rng.shuffle(order)
        for k in range(0,48,BATCH):
            batch=[pairs[i] for i in order[k:k+BATCH]]
            signs=[1 if rng.getrandbits(1) else -1 for _ in delta]
            plus=[max(-3.,min(3.,x+PERTURB*s))
                  for x,s in zip(delta,signs)]
            minus=[max(-3.,min(3.,x-PERTURB*s))
                   for x,s in zip(delta,signs)]
            gradient=(loss(batch,base,plus)-loss(batch,base,minus))/(2*PERTURB)
            rate=LR/(1.+.01*steps)
            delta=[max(-3.,min(3.,x-rate*gradient*s))
                   for x,s in zip(delta,signs)]
            steps+=1
    magnitude=sum(x*x for x in delta)**.5
    need(steps==72 and magnitude>1e-9 and
         all(math.isfinite(x) for x in delta),
         "GENUINE_FIT_ONLY_UPDATE")
    return {"lane":"Yggdrasil","training":"FIT_ONLY",
            "training_steps":steps,"epochs":EPOCHS,"pairs":48,
            "learned_delta":delta,"delta_sha256":sha(delta),
            "update_l2":round(magnitude,9),
            "original_base_weights_sha256":old.sha(list(base)),
            "initial_fit_loss":round(initial,8),
            "final_fit_loss":round(loss(pairs,base,delta),8),
            "dev_access_during_training":0,
            "protected_access_during_training":0}
