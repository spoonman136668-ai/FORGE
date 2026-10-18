"""F124-AU 12-bit single-packed-state local causal witness discriminators.

All candidate evidence is calculated ephemerally from PUBLIC local handoffs.
The sole retained per-node code remains exactly 12 bits. No oracle path, true
inverse, graph label or extra alternative node/path state is used.
"""
from __future__ import annotations
from collections import defaultdict
import math

import f124am_terminal_competition as control
import f124ae_frozen_source as structural
import f124q_independent_binding as origq
import f124o_native_learners as oldo

MODES=("original_gamma0","packed_local_witness_margin",
       "packed_successor_support")
ALPHAS=(0.,.02,.06,.12)
CHECKSUM=(1,3,4,2)

def need(condition,label):
    structural.need(condition,"F124AU_WITNESS_"+label)

def score(graph,base,delta,mode,alpha):
    need(mode in MODES and alpha in ALPHAS,"FROZEN_SEVEN_ARM_GRID")
    if mode=="original_gamma0":
        need(alpha==0.,"ORIGINAL_UNCHANGED_GAMMA")
        value,work=control.terminal_competitive(graph,base,delta,0.)
        return value,{**work,"extra_evidence_ops":0,
                      "extra_retained_states":0,"oracle_used":False}
    need(alpha>0.,"NONZERO_NEW_EVIDENCE_ONLY")
    structural.validate_15(graph)
    weights=origq.wingless_anchored_weights(list(base),list(delta))
    edges=oldo.sorted_edges(graph)
    index=defaultdict(list)
    for edge in edges:
        index[(edge["from"],edge["role"])].append(edge)
    work={"edge_inspections":len(edges),"raw_bit_reads":0,
          "affinity_ops":0,"max_active":1,
          "max_states_per_node":1,"max_packed_bits_per_state":12,
          "max_index_entries":len(edges),"max_encoded_cache":0,
          "max_lookahead_cache":0,"extra_evidence_ops":0,
          "extra_retained_states":0,"oracle_used":False}
    def pack(bits):
        need(len(bits)==16 and all(bit in (0,1) for bit in bits),
             "ORIGINAL_PUBLIC_BIT_SHAPE")
        work["raw_bit_reads"]+=16
        val=0
        for j in range(4):
            val|=(sum(CHECKSUM[i]*bits[4*j+i]
                      for i in range(4))%5)<<(3*j)
        need(0<=val<4096,"EXACT_12_BIT_CODE")
        return val
    def similarity(a,b):
        work["affinity_ops"]+=4
        av=[weights[j]*(((a>>(3*j))&7)-2)/2 for j in range(4)]
        bv=[weights[j]*(((b>>(3*j))&7)-2)/2 for j in range(4)]
        return 1.-sum(abs(x-y) for x,y in zip(av,bv))/8.
    states={graph["start"]:(0.,None)}
    for t,role in enumerate(graph["roles"]):
        next_role=graph["roles"][t+1] if t+1<len(graph["roles"]) else None
        following=defaultdict(list)
        for node in sorted(states):
            score_so_far,carried=states[node]
            eligible=index.get((node,role),())
            work["edge_inspections"]+=len(eligible)
            # Local ephemeral evidence only, not carried to the next node.
            rival_matches=[(1. if carried is None else
                            similarity(carried,pack(e["src_bits"])))
                           for e in eligible]
            work["extra_evidence_ops"]+=len(eligible)
            for i,edge in enumerate(eligible):
                src=pack(edge["src_bits"])
                dst=pack(edge["dst_bits"])
                match=1. if carried is None else similarity(carried,src)
                value=score_so_far+weights[4]*(match-.6)
                strongest=max((r for j,r in enumerate(rival_matches)
                               if i!=j),default=match)
                value+=.5*(match-strongest)
                look=0.
                successors=index.get((edge["to"],next_role),()) if next_role else ()
                if next_role:
                    work["edge_inspections"]+=len(successors)
                    look=max((similarity(dst,pack(n["src_bits"]))
                              for n in successors),default=0.)
                if carried is not None:
                    if mode=="packed_local_witness_margin":
                        # A witness is insufficiently selective if local
                        # sibling scores are nearly tied and an alternative
                        # (nonpersistent) handoff exists.
                        ambiguity=max(0.,1.-abs(match-strongest))
                        penalty=(ambiguity if len(eligible)>1 else 0.)
                        work["extra_evidence_ops"]+=len(eligible)
                    else:
                        # On-the-fly successor support; empty next role is
                        # not penalized. No memoized lookahead/path state.
                        penalty=max(0.,.7-look) if successors else 0.
                        work["extra_evidence_ops"]+=len(successors)
                    value-=alpha*penalty
                rank=value+weights[5]*(look-.6)
                following[edge["to"]].append((rank,value,dst))
        states={}
        for node,rows in following.items():
            rows.sort(key=lambda x:(-x[0],-x[1],x[2]))
            states[node]=(rows[0][1],rows[0][2])
        work["max_active"]=max(work["max_active"],len(states))
        need(work["max_active"]<=64 and work["max_states_per_node"]==1
             and work["max_packed_bits_per_state"]==12,
             "BOUNDED_ONE_STATE_PER_NODE")
    best=states.get(graph["target"],(-2.*len(graph["roles"]),None))[0]
    out=4.*(best/max(1,len(graph["roles"])-1)-weights[6])
    need(math.isfinite(out),"FINITE_CAUSAL_OUTPUT")
    return out,work
