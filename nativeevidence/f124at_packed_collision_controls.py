"""F124-AT source-blind one-state checksum alternatives and overbudget diagnostic.

The exact original packed scorer's CODE is reused; only its global four
checksum coefficients differ. This is not a retuned score or a learned
operator. Each alternative retains one 12-bit code/node, max 64 nodes.
The full16 scorer is an intentionally OVER-CAPACITY measurement only.
"""
from __future__ import annotations
import math
import types
from collections import defaultdict
import f124am_terminal_competition as original
import f124ae_frozen_source as structural
import f124o_native_learners as old
import f124q_independent_binding as q

CHECKSUMS={
    "original_gamma0_checksum_1342":(1,3,4,2),
    "fixed_12bit_checksum_1234":(1,2,3,4),
    "fixed_12bit_checksum_2413":(2,4,1,3)}
def need(ok,tag):structural.need(ok,"F124AT_PACK_"+tag)
def code12(bits,coeff):
    need(len(bits)==16 and len(coeff)==4,"ORIGINAL_CODE_WIDTH")
    out=0
    for j in range(4):
        chunk=sum(coeff[i]*bits[j*4+i] for i in range(4))%5
        out|=chunk<<(3*j)
    need(0<=out<4096,"ONE_12BIT_STATE")
    return out

def score12(graph,base,delta,name):
    need(name in CHECKSUMS,"PREREGISTERED_CODE_ONLY")
    if name=="original_gamma0_checksum_1342":
        value,work=original.terminal_competitive(graph,base,delta,0.)
    else:
        env=dict(original.terminal_competitive.__globals__,
                 CHECKSUM=CHECKSUMS[name])
        cloned=types.FunctionType(original.terminal_competitive.__code__,env,
                original.terminal_competitive.__name__,
                original.terminal_competitive.__defaults__)
        value,work=cloned(graph,base,delta,0.)
    need(work["max_states_per_node"]==1 and
         work["max_packed_bits_per_state"]==12 and
         work["max_active"]<=64,"FIXED_ONE_STATE_TWELVE_BITS")
    return value,work

def full16_diagnostic(graph,base,delta):
    """Overcapacity original-style scorer, 16 raw bits per node, NOT eligible."""
    structural.validate_15(graph)
    weights=q.wingless_anchored_weights(list(base),list(delta))
    edges=old.sorted_edges(graph)
    index=defaultdict(list)
    for e in edges:index[(e["from"],e["role"])].append(e)
    ops=0
    def affinity(a,b):
        nonlocal ops
        ops+=16
        return 1.-sum(weights[j]*sum(
                 a[j*4+i]!=b[j*4+i] for i in range(4))/4.
                 for j in range(4))/8.
    states={graph["start"]:(0.,None)}
    peak=1
    for step,role in enumerate(graph["roles"]):
        next_role=graph["roles"][step+1] if step+1<len(graph["roles"]) else None
        following=defaultdict(list)
        for node in sorted(states):
            score,carried=states[node]
            eligible=index.get((node,role),())
            rivals=[1. if carried is None else affinity(carried,e["src_bits"]) for e in eligible]
            for j,e in enumerate(eligible):
                src=e["src_bits"]
                dst=e["dst_bits"]
                match=1. if carried is None else affinity(carried,src)
                value=score+weights[4]*(match-.6)
                strongest=max((v for k,v in enumerate(rivals) if k!=j),default=match)
                value+=.5*(match-strongest)
                look=0.
                if next_role is not None:
                    look=max((affinity(dst,n["src_bits"])
                              for n in index.get((e["to"],next_role),())),default=0.)
                rank=value+weights[5]*(look-.6)
                following[e["to"]].append((rank,value,tuple(dst)))
        states={}
        for node,rows in following.items():
            rows.sort(key=lambda a:(-a[0],-a[1],a[2]))
            states[node]=(rows[0][1],rows[0][2])
        peak=max(peak,len(states))
        need(peak<=64,"FIXED_NODE_COUNT_OVERBUDGET_PACKET")
    best=states.get(graph["target"],(-2.*len(graph["roles"]),None))[0]
    value=4.*(best/max(1,len(graph["roles"])-1)-weights[6])
    need(math.isfinite(value),"FINITE_FULL16_DIAGNOSTIC")
    return value,{"max_active":peak,"max_states_per_node":1,
                  "max_packed_bits_per_state":16,
                  "extra_retained_states":0,"affinity_ops":ops,
                  "overbudget_only":True}

def collisions(graph,coeff):
    # Detect intrinsically lost distinctions at the packed-code boundary.
    values=set()
    for e in graph["edges"]:
        values.add(tuple(e["src_bits"]))
        values.add(tuple(e["dst_bits"]))
    buckets=defaultdict(set)
    for v in values:buckets[code12(v,coeff)].add(v)
    return {"distinct_original_vectors":len(values),
            "distinct_packed_codes":len(buckets),
            "colliding_raw_vectors":sum(len(v) for v in buckets.values()
                                        if len(v)>1),
            "collision_pairs":sum(len(v)*(len(v)-1)//2
                                  for v in buckets.values())}
