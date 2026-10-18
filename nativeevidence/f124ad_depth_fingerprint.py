"""F124-AD frozen readout-only long-chain evidence and one-slot fingerprint.

Inference consumes ONLY public source graph/ original trained parameters.
FIT chooses either denominator anchor or fingerprint coefficient, then fixes
it before DEV. No oracle, protected reference or label in predictions.
"""
from __future__ import annotations
from collections import defaultdict
import math
import f124ad_frozen_source as source
import f124ab_soft_hamming_pareto as ab
import f124aa_packed_transfer as aa
import f124q_independent_binding as q
import f124o_native_learners as original_o

def anchored_readout(graph,base,delta,anchor):
    source.need(anchor in source.ANCHORS,"FROZEN_DEPTH_ANCHOR")
    raw,ratio,work=ab.soft_continuity(graph,base,delta,.25)
    depth=len(graph["roles"])
    best=(raw/4.+base[6])*(depth-1)
    # At anchor=16 this MUST return unchanged AB logit exactly.
    score=ab.logit(raw,ratio,.25) if anchor==16 else (
        4.*(best/min(depth-1,anchor)-base[6])-.25*(1.-ratio))
    source.need(math.isfinite(score),"FINITE_LONG_CHAIN_HEAD")
    return score,raw,ratio,work

def readout_fit(cases,base,delta):
    source.need(len(cases)==48 and
                all(c[2] in source.FAMILIES for c in cases),
                "COMPLETE_NEW_FIT_ONLY")
    scored=[]
    for _,_,_,pos,neg in cases:
        p,pr,_=ab.soft_continuity(pos,base,delta,.25)
        n,nr,_=ab.soft_continuity(neg,base,delta,.25)
        scored.append((p,pr,len(pos["roles"]),n,nr,len(neg["roles"])))
    grid=[]
    for anchor in source.ANCHORS:
        def transform(raw,ratio,depth):
            if anchor==16:return ab.logit(raw,ratio,.25)
            best=(raw/4.+base[6])*(depth-1)
            return 4.*(best/min(depth-1,anchor)-base[6])-.25*(1.-ratio)
        paired=sum(transform(p,pr,pd)>=0 and transform(n,nr,nd)<0
                   for p,pr,pd,n,nr,nd in scored)
        grid.append({"anchor":anchor,"paired":paired})
    winner=sorted(grid,key=lambda x:(-x["paired"],-x["anchor"]))[0]
    return winner,grid

def four_bit_fingerprint(bits):
    source.need(type(bits) is list and len(bits)==16
                and all(type(b) is int and b in (0,1) for b in bits),
                "PUBLIC_FOUR_BIT_WITNESS")
    return (sum(bits[i]<<i for i in range(4)) ^
            sum(bits[4+i]<<i for i in range(4)) ^
            sum(bits[8+i]<<i for i in range(4)) ^
            sum(bits[12+i]<<i for i in range(4)))&15

def packed_with_fingerprint(graph,base,delta,alpha):
    source.need(alpha in source.ALPHAS,"FROZEN_FINGERPRINT_ALPHA")
    source.previous.original.parent.validate_extended(graph)
    weights=q.wingless_anchored_weights(list(base),list(delta))
    edges=original_o.sorted_edges(graph)
    index=defaultdict(list)
    work={"edge_inspections":len(edges),"raw_bit_reads":0,"affinity_ops":0,
          "max_active":1,"max_states_per_node":1,"max_packed_bits_per_state":12,
          "max_index_entries":len(edges),"max_encoded_cache":0,
          "max_lookahead_cache":0,"fingerprint_raw_bit_reads":0,
          "fingerprint_comparisons":0,"max_fingerprint_bits_per_state":4,
          "max_total_key_bits_per_state":16}
    for edge in edges:index[(edge["from"],edge["role"])].append(edge)
    def packed(bits):
        work["raw_bit_reads"]+=16
        result=0
        for j in range(4):
            code=sum((1,3,4,2)[i]*bits[4*j+i] for i in range(4))%5
            result|=code<<(3*j)
        return result
    def signature(bits):
        work["fingerprint_raw_bit_reads"]+=16
        return four_bit_fingerprint(bits)
    def affinity(a,b):
        work["affinity_ops"]+=4
        av=[weights[j]*(((a>>(3*j))&7)-2)/2 for j in range(4)]
        bv=[weights[j]*(((b>>(3*j))&7)-2)/2 for j in range(4)]
        return 1.-sum(abs(x-y) for x,y in zip(av,bv))/8.
    def adjust(left,right):
        work["fingerprint_comparisons"]+=1
        return alpha*(1. if left==right else -1.)
    states={graph["start"]:(0.,None,None)}
    for step,role in enumerate(graph["roles"]):
        nxt=graph["roles"][step+1] if step+1<len(graph["roles"]) else None
        following=defaultdict(list)
        for node in sorted(states):
            score,carry,carry_signature=states[node]
            eligible=index.get((node,role),())
            work["edge_inspections"]+=len(eligible)
            for edge in eligible:
                src=packed(edge["src_bits"]);dst=packed(edge["dst_bits"])
                src_sig=signature(edge["src_bits"])
                dst_sig=signature(edge["dst_bits"])
                match=1. if carry is None else affinity(carry,src)
                if alpha and carry is not None:match+=adjust(carry_signature,src_sig)
                value=score+weights[4]*(match-.6)
                look=0.
                if nxt is not None:
                    successors=index.get((edge["to"],nxt),())
                    work["edge_inspections"]+=len(successors)
                    # Original 12-bit model operation ordering when alpha=0.
                    if not alpha:
                        look=max((affinity(dst,packed(n["src_bits"]))
                                  for n in successors),default=0.)
                    else:
                        look=max((affinity(dst,packed(n["src_bits"]))+
                                  adjust(dst_sig,signature(n["src_bits"]))
                                  for n in successors),default=0.)
                rank=value+weights[5]*(look-.6)
                following[edge["to"]].append((rank,value,dst,dst_sig))
        states={}
        for node,rows in following.items():
            rows.sort(key=lambda x:(-x[0],-x[1],x[2]))
            best=rows[0]
            states[node]=(best[1],best[2],best[3])
        work["max_active"]=max(work["max_active"],len(states))
        source.need(work["max_active"]<=64,"UNCHANGED_ONE_STATE_PER_NODE")
    best=states.get(graph["target"],(-2.*len(graph["roles"]),None,None))[0]
    result=4.*(best/max(1,len(graph["roles"])-1)-weights[6])
    source.need(math.isfinite(result),"FINITE_FINGERPRINT_HEAD")
    return result,work

def fingerprint_fit(cases,base,delta):
    source.need(len(cases)==48,"FULL_NEW_WING_FIT")
    grid=[]
    for alpha in source.ALPHAS:
        wins=0
        for _,_,_,pos,neg in cases:
            p,_=packed_with_fingerprint(pos,base,delta,alpha)
            n,_=packed_with_fingerprint(neg,base,delta,alpha)
            wins+=int(p>=0 and n<0)
        grid.append({"alpha":alpha,"paired":wins})
    winner=sorted(grid,key=lambda x:(-x["paired"],x["alpha"]))[0]
    return winner,grid
