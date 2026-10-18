"""F124-T strictly source-frozen optimization and cell-credit ablations.

No retraining or post-hoc coefficients. Wingless S and indexed S logits must
be exactly equal per graph; logical 10-byte serialized persistent states remain
unchanged. Extra index/cache scratch capacity and hash lookups are exposed,
not misrepresented as free memory or matched wall-clock compute.
"""
from __future__ import annotations
from collections import defaultdict
import math

import f124o_native_learners as orig
import f124s_native_mechanisms as s_model
import f124t_fresh_source as source


def need(ok,code):
    source.need(ok,"VARIANT_"+code)


def wingless_indexed(g,base,delta):
    source.validate_public(g)
    need(len(base)==7 and len(delta)==2 and
         all(math.isfinite(x) for x in list(base)+list(delta)),
         "WING_ORIGINAL_WEIGHTS")
    edges=orig.sorted_edges(g)
    # One explicit scan constructs a bounded per-query adjacency index; this
    # index is EXTRA ephemeral memory, not part of persistent 10-byte state.
    by_from_role=defaultdict(list)
    for e in edges:
        by_from_role[(e["from"],e["role"])].append(e)
    adjacency_entries=sum(map(len,by_from_role.values()))
    cost={"public_edge_scans":len(edges),"raw_bit_ops":0,
          "causal_key_comparisons":0,"max_active":1,"max_retained":0,
          "evictions":0,"state_limit":3,
          "serialized_state_payload_bytes":10,
          "reference_serialized_state_payload_bytes":40,
          "max_serialized_payload_bytes":10,
          "index_entries":adjacency_entries,
          "index_buckets":len(by_from_role),
          "index_lookup_count":0,"cache_hits":0,
          "max_key_cache_entries":0,"extra_scratch_memory_present":True}
    raw_cache={}
    vector_cache={}
    def pack(raw):
        t=tuple(raw)
        if t in raw_cache:
            cost["cache_hits"]+=1
            return raw_cache[t]
        cost["raw_bit_ops"]+=16
        value=s_model.bits_to_uint16(raw)
        raw_cache[t]=value
        cost["max_key_cache_entries"]=max(cost["max_key_cache_entries"],
                                            len(raw_cache)+len(vector_cache))
        return value
    def vec(v):
        if v in vector_cache:
            cost["cache_hits"]+=1
            return vector_cache[v]
        cost["raw_bit_ops"]+=16
        z=tuple((2*((v>>(4*j))&15).bit_count()-4)/4. for j in range(4))
        vector_cache[v]=z
        cost["max_key_cache_entries"]=max(cost["max_key_cache_entries"],
                                            len(raw_cache)+len(vector_cache))
        return z
    mix=orig.sigmoid(delta[0])
    temp=1.+.2*math.tanh(delta[1])
    w=[1.,1.,1.,1.]+list(base[4:])
    def affinity(a,b):
        cost["raw_bit_ops"]+=20
        cost["causal_key_comparisons"]+=1
        va,vb=vec(a),vec(b)
        latent=1.-sum(abs(x-y) for x,y in zip(va,vb))/8.
        raw=(16-(a^b).bit_count())/16.
        return temp*((1.-mix)*latent+mix*raw)
    state={g["start"]:[s_model.STATE.pack(0.,0)]}
    for hop,role in enumerate(g["roles"]):
        nextrole=g["roles"][hop+1] if hop+1<len(g["roles"]) else None
        new=defaultdict(list)
        for node in sorted(state):
            cost["index_lookup_count"]+=1
            allowed=by_from_role.get((node,role),())
            for record in state[node]:
                need(type(record) is bytes and len(record)==10,
                     "PERSISTENT_STATE_10_BYTES")
                score,carried=s_model.STATE.unpack(record)
                cost["public_edge_scans"]+=len(allowed)
                for e in allowed:
                    src=pack(e["src_bits"])
                    dst=pack(e["dst_bits"])
                    compatibility=1. if hop==0 else affinity(carried,src)
                    value=score+w[4]*(compatibility-.6)
                    if nextrole is None:
                        look=0.
                    else:
                        cost["index_lookup_count"]+=1
                        q=by_from_role.get((e["to"],nextrole),())
                        cost["public_edge_scans"]+=len(q)
                        look=max((affinity(dst,pack(t["src_bits"]))
                                  for t in q),default=0.)
                    priority=value+w[5]*(look-.6)
                    record_next=s_model.STATE.pack(value,dst)
                    new[e["to"]].append((priority,record_next))
        state={}
        for node,options in new.items():
            options.sort(key=lambda x:(-x[0],x[1]))
            cost["evictions"]+=max(0,len(options)-3)
            state[node]=[rec for _,rec in options[:3]]
        cost["max_active"]=max(cost["max_active"],
                               sum(len(records) for records in state.values()))
        cost["max_serialized_payload_bytes"]=max(
            cost["max_serialized_payload_bytes"],cost["max_active"]*10)
        need(cost["max_active"]<=192 and
             all(len(x)<=3 for x in state.values()),"THREE_SLOTS_PER_NODE")
    vals=[s_model.STATE.unpack(x)[0] for x in state.get(g["target"],[])]
    best=max(vals,default=-2.*len(g["roles"]))
    logit=4.*(best/max(1,len(g["roles"])-1)-w[6])
    need(math.isfinite(logit),"FINITE_WING_LOGIT")
    return logit,cost


def yggdrasil_credit_ablation(g,base,delta,*,value_credit=True,
                               rank_credit=True):
    source.validate_public(g)
    need(len(base)==7 and len(delta)==2 and
         all(math.isfinite(x) for x in list(base)+list(delta)),
         "YGG_FROZEN_WEIGHTS")
    edges=orig.sorted_edges(g)
    active=[(g["start"],None,0.)]
    retained=[]
    cost={"public_edge_scans":0,"raw_bit_ops":0,
          "causal_key_comparisons":0,"max_active":1,"max_retained":0,
          "evictions":0,"active_cell_limit":7,"retained_cell_limit":9,
          "value_credit":value_credit,"rank_credit":rank_credit}
    def compatibility(carried,src):
        if carried is None:
            return 1.
        cost["raw_bit_ops"]+=16
        cost["causal_key_comparisons"]+=1
        return sum(base[j]*sum(int(a==b) for a,b in zip(
            carried[j*4:j*4+4],src[j*4:j*4+4]))/4.
            for j in range(4))/4.
    for role in g["roles"]:
        candidates=[]
        for node,carried,score in active+retained:
            cost["public_edge_scans"]+=len(edges)
            for e in edges:
                if e["from"]!=node or e["role"]!=role:
                    continue
                sim=compatibility(carried,e["src_bits"])
                confidence=orig.sigmoid(6.*(sim-.5))-.5
                value=score+base[4]*(sim-.35)+(
                    delta[0]*confidence if value_credit else 0.)
                ranking=base[5]*(sim-.5)+(
                    delta[1]*confidence if rank_credit else 0.)
                cell=(e["to"],tuple(e["dst_bits"]),value)
                candidates.append((value+ranking,value-ranking,cell))
        candidates.sort(key=lambda x:(-x[0],-x[1],x[2][0],x[2][1]))
        active=[row[2] for row in candidates[:7]]
        chosen={id(x) for x in candidates[:7]}
        extras=[x for x in candidates if id(x) not in chosen]
        extras.sort(key=lambda x:(-x[1],-x[0],x[2][0],x[2][1]))
        retained=[row[2] for row in extras[:9]]
        cost["evictions"]+=max(0,len(candidates)-16)
        cost["max_active"]=max(cost["max_active"],len(active))
        cost["max_retained"]=max(cost["max_retained"],len(retained))
        need(len(active)<=7 and len(retained)<=9 and
             len(active)+len(retained)<=16,"EXACT_YGG_CELL_BUDGET")
    scores=[v for node,_,v in active+retained if node==g["target"]]
    best=max(scores,default=-2.*len(g["roles"]))
    z=4.*(best/max(1,len(g["roles"])-1)-base[6])
    need(math.isfinite(z),"FINITE_YGG_LOGIT")
    return z,cost
