"""F124-AB frozen soft-Hamming head and packed-state 1/2/3 Pareto.

Source-blind predictors: no paired cases/labels, oracle functions or
protected source are in any inference function. Original T sorting and
the 7 active + 9 retained cell limit are bytewise invariant.
"""
from __future__ import annotations
from collections import defaultdict
import math
import f124ab_frozen_source as fresh
import f124aa_packed_transfer as previous
import f124q_independent_binding as old_q
import f124o_native_learners as old_o
import f124z_sparse_continuity as old_z

GAMMAS=(0.,.25,.5,1.,2.)
PENALTIES=(0.,.25,.5,1.,2.)
CAPACITIES=(1,2,3)
CHECKSUM=(1,3,4,2)

def soft_continuity(graph,base,delta,gamma):
    """Original frozen T scores/ranking, one new bounded continuity scalar.

    No learned gamma applied to rank: only to public key-Hamming feature.
    First hop always 1. Same number of hard cells as original T.
    """
    fresh.parent.validate_extended(graph)
    fresh.need(gamma in GAMMAS and len(base)==7 and len(delta)==2,
               "FROZEN_SOFT_MODEL")
    edges=old_o.sorted_edges(graph)
    active=[(graph["start"],None,0.,0.)];retained=[]
    depth=len(graph["roles"])
    work={"public_edge_scans":0,"raw_bit_ops":0,"max_active":1,"max_retained":0,
          "evictions":0,"prospective_key_comparisons":0,
          "active_cell_limit":7,"retained_cell_limit":9,
          "hamming_bit_comparisons":0,"soft_counter_slots_max":1}
    def compare(carry,src):
        if carry is None:return 1.
        work["raw_bit_ops"]+=16
        return sum(base[j]*sum(int(a==b) for a,b in zip(
            carry[j*4:j*4+4],src[j*4:j*4+4]))/4.
            for j in range(4))/4.
    for step,role in enumerate(graph["roles"]):
        nxt=graph["roles"][step+1] if step+1<depth else None
        candidates=[]
        for node,carry,score,history in active+retained:
            work["public_edge_scans"]+=len(edges)
            for edge in edges:
                if edge["from"]!=node or edge["role"]!=role:continue
                match=compare(carry,edge["src_bits"])
                value=score+base[4]*(match-.35)
                competition=base[5]*(match-.5)
                if nxt is None: look=0.
                else:
                    possible=[e for e in edges if e["from"]==edge["to"]
                              and e["role"]==nxt]
                    work["public_edge_scans"]+=len(edges)
                    look=max((compare(tuple(edge["dst_bits"]),p["src_bits"])
                              for p in possible),default=0.)
                    work["prospective_key_comparisons"]+=len(possible)
                if carry is None:
                    contribution=1.
                else:
                    work["hamming_bit_comparisons"]+=16
                    distance=sum(x!=y for x,y in zip(carry,edge["src_bits"]))
                    contribution=max(0.,1.-gamma*distance)
                cell=(edge["to"],tuple(edge["dst_bits"]),value,
                      history+contribution)
                candidates.append((value+competition+delta[0]*(look-.5),
                                   value-competition+delta[1]*(look-.5),cell))
        candidates.sort(key=lambda x:(-x[0],-x[1],x[2][0],x[2][1]))
        active=[row[2] for row in candidates[:7]]
        picked={id(x) for x in candidates[:7]}
        extras=[row for row in candidates if id(row) not in picked]
        extras.sort(key=lambda x:(-x[1],-x[0],x[2][0],x[2][1]))
        retained=[row[2] for row in extras[:9]]
        work["evictions"]+=max(0,len(candidates)-16)
        work["max_active"]=max(work["max_active"],len(active))
        work["max_retained"]=max(work["max_retained"],len(retained))
        work["soft_counter_slots_max"]=max(work["soft_counter_slots_max"],
                                             len(active)+len(retained))
        fresh.need(len(active)<=7 and len(retained)<=9,"ORIGINAL_CELL_HARD_LIMIT")
    terminal=[cell for cell in active+retained if cell[0]==graph["target"]]
    best=max((cell[2] for cell in terminal),default=-2.*depth)
    raw=4.*(best/max(1,depth-1)-base[6])
    ratio=max((cell[3]/depth for cell in terminal),default=0.)
    fresh.need(math.isfinite(raw) and 0<=ratio<=1,
               "SOURCE_BLIND_HAMMING_READOUT")
    return raw,ratio,work

def logit(raw,ratio,penalty):
    fresh.need(math.isfinite(raw) and 0<=ratio<=1 and penalty in PENALTIES,
               "PREDECLARED_FIT_ONLY_PENALTY")
    return raw-penalty*(1.-ratio)

def learn_fit(fit_cases,base,delta):
    """FIT ONLY. Freeze selected gamma/penalty before new DEV exists."""
    selected=[(pos,neg) for _,_,family,pos,neg in fit_cases if
              family in ("permuted_bits","one_bit_relaxed_keys")]
    fresh.need(len(selected)==24,"FROZEN_FIT_TWO_FAMILIES")
    cache={}
    for gamma in GAMMAS:
        scored=[]
        for pos,neg in selected:
            p,pr,_=soft_continuity(pos,base,delta,gamma)
            n,nr,_=soft_continuity(neg,base,delta,gamma)
            scored.append((p,pr,n,nr))
        cache[gamma]=scored
    grid=[]
    for gamma in GAMMAS:
        for penalty in PENALTIES:
            points=sum(logit(p,pr,penalty)>=0 and logit(n,nr,penalty)<0
                       for p,pr,n,nr in cache[gamma])
            grid.append({"gamma":gamma,"penalty":penalty,"paired":points})
    winner=sorted(grid,key=lambda x:(-x["paired"],
                abs(x["gamma"]-1.)+abs(x["penalty"]-.5),
                x["gamma"],x["penalty"]))[0]
    return winner,grid

def packed_frontier(graph,base,delta,slots):
    """All three sizes use identical packed 12-bit channels & exact scoring."""
    fresh.parent.validate_extended(graph)
    fresh.need(slots in CAPACITIES and len(base)==7 and len(delta)==4,
               "ONE_TWO_THREE_FROZEN_SLOTS")
    weights=old_q.wingless_anchored_weights(list(base),list(delta))
    edges=old_o.sorted_edges(graph)
    index=defaultdict(list)
    work={"edge_inspections":len(edges),"raw_bit_reads":0,"affinity_ops":0,
          "max_active":1,"max_states_per_node":slots,"max_packed_bits_per_state":12,
          "max_index_entries":len(edges),"max_encoded_cache":0,
          "max_lookahead_cache":0}
    for e in edges:index[(e["from"],e["role"])].append(e)
    def pack(bits):
        work["raw_bit_reads"]+=16
        packed=0
        for j in range(4):
            nib=sum(CHECKSUM[i]*bits[4*j+i] for i in range(4))%5
            packed|=nib<<(3*j)
        return packed
    def unpack(bits):
        return tuple(weights[j]*(((bits>>(3*j))&7)-2)/2 for j in range(4))
    def affinity(a,b):
        work["affinity_ops"]+=4
        left=unpack(a);right=unpack(b)
        return 1.-sum(abs(u-v) for u,v in zip(left,right))/8.
    states={graph["start"]:[(0.,None)]}
    for step,role in enumerate(graph["roles"]):
        nxt=graph["roles"][step+1] if step+1<len(graph["roles"]) else None
        following=defaultdict(list)
        for node in sorted(states):
            eligible=index.get((node,role),())
            for score,carry in states[node]:
                work["edge_inspections"]+=len(eligible)
                for edge in eligible:
                    src=pack(edge["src_bits"]);dst=pack(edge["dst_bits"])
                    compat=1. if carry is None else affinity(carry,src)
                    value=score+weights[4]*(compat-.6)
                    if nxt is None:look=0.
                    else:
                        successors=index.get((edge["to"],nxt),())
                        work["edge_inspections"]+=len(successors)
                        look=max((affinity(dst,pack(e["src_bits"]))
                                  for e in successors),default=0.)
                    priority=value+weights[5]*(look-.6)
                    following[edge["to"]].append((priority,value,dst))
        states={}
        for node,items in following.items():
            # AA one-state breaks ties by packed integer; Z three-state by
            # decoded float channels. Preserve each frozen control exactly.
            items.sort(key=lambda x:(-x[0],-x[1],
                                     x[2] if slots==1 else unpack(x[2])))
            states[node]=[(value,packed) for _,value,packed in items[:slots]]
        work["max_active"]=max(work["max_active"],
                               sum(len(v) for v in states.values()))
        fresh.need(work["max_active"]<=slots*64 and
                   all(len(v)<=slots for v in states.values()),
                   "PACKED_STATE_SLOTS_LIMIT")
    best=max((value for value,_ in states.get(graph["target"],[])),
             default=-2.*len(graph["roles"]))
    result=4.*(best/max(1,len(graph["roles"])-1)-weights[6])
    fresh.need(math.isfinite(result),"PACKED_STATE_OUTPUT")
    return result,work
