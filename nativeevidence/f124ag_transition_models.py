"""F124-AG genuine within-chain transition evidence, not a final threshold.

Two hypotheses change accumulated transition value BEFORE hard pruning.
At eta=0 the source-blind original predictor's raw outputs and original
operation counters must match byte-for-byte, as enforced by focused tests.
Neither sees true path, paired labels or independent oracle.
"""
from __future__ import annotations
from collections import defaultdict
import math
import f124ag_frozen_source as frozen
import f124ae_scoring_transfer as original
import f124q_independent_binding as q
import f124o_native_learners as old_o

CHECKSUM=(1,3,4,2)

def ygg_transition(g,base,delta,eta):
    frozen.need(eta in frozen.ETAS and len(base)==7 and len(delta)==2,
                "FROZEN_YGG_TRANSITION")
    frozen.prior.parent.validate_15(g)
    edges=old_o.sorted_edges(g)
    active=[(g["start"],None,0.,0.)]
    retained=[]
    depth=len(g["roles"])
    work={"public_edge_scans":0,"raw_bit_ops":0,"max_active":1,"max_retained":0,
          "evictions":0,"prospective_key_comparisons":0,
          "active_cell_limit":7,"retained_cell_limit":9,
          "hamming_bit_comparisons":0,"soft_counter_slots_max":1,
          "transition_penalty_evaluations":0,
          "violating_transitions":0,"sum_transition_violation_bits":0}
    def compare(carry,src):
        if carry is None:return 1.
        work["raw_bit_ops"]+=16
        return sum(base[j]*sum(int(a==b) for a,b in zip(
            carry[j*4:j*4+4],src[j*4:j*4+4]))/4.
            for j in range(4))/4.
    for step,role in enumerate(g["roles"]):
        nxt=g["roles"][step+1] if step+1<depth else None
        candidates=[]
        for node,carry,score,history in active+retained:
            work["public_edge_scans"]+=len(edges)
            for edge in edges:
                if edge["from"]!=node or edge["role"]!=role:continue
                match=compare(carry,edge["src_bits"])
                value=score+base[4]*(match-.35)
                competition=base[5]*(match-.5)
                if nxt is None:look=0.
                else:
                    possible=[e for e in edges if e["from"]==edge["to"]
                              and e["role"]==nxt]
                    work["public_edge_scans"]+=len(edges)
                    look=max((compare(tuple(edge["dst_bits"]),p["src_bits"])
                              for p in possible),default=0.)
                    work["prospective_key_comparisons"]+=len(possible)
                if carry is None:contribution=1.
                else:
                    work["hamming_bit_comparisons"]+=16
                    distance=sum(x!=y for x,y in zip(carry,edge["src_bits"]))
                    contribution=max(0.,1.-.25*distance)
                    if eta:
                        work["transition_penalty_evaluations"]+=1
                        excess=max(0,distance-1)
                        work["violating_transitions"]+=int(excess>0)
                        work["sum_transition_violation_bits"]+=excess
                        value-=eta*excess
                cell=(edge["to"],tuple(edge["dst_bits"]),value,
                      history+contribution)
                candidates.append((value+competition+delta[0]*(look-.5),
                                   value-competition+delta[1]*(look-.5),cell))
        candidates.sort(key=lambda x:(-x[0],-x[1],x[2][0],x[2][1]))
        active=[row[2] for row in candidates[:7]]
        picked={id(row) for row in candidates[:7]}
        extras=[row for row in candidates if id(row) not in picked]
        extras.sort(key=lambda x:(-x[1],-x[0],x[2][0],x[2][1]))
        retained=[row[2] for row in extras[:9]]
        work["evictions"]+=max(0,len(candidates)-16)
        work["max_active"]=max(work["max_active"],len(active))
        work["max_retained"]=max(work["max_retained"],len(retained))
        work["soft_counter_slots_max"]=max(work["soft_counter_slots_max"],
                                             len(active)+len(retained))
        frozen.need(len(active)<=7 and len(retained)<=9,"HARD_SEVEN_PLUS_NINE")
    terminal=[c for c in active+retained if c[0]==g["target"]]
    best=max((c[2] for c in terminal),default=-2.*depth)
    raw=4.*(best/max(1,depth-1)-base[6])
    ratio=max((c[3]/depth for c in terminal),default=0.)
    anchored=4.*(((raw/4.+base[6])*(depth-1))/
                 min(depth-1,10)-base[6])-.25*(1.-ratio)
    frozen.need(math.isfinite(anchored) and 0<=ratio<=1,
                "FINITE_CAUSAL_TRANSITION")
    return anchored,raw,ratio,work

def wing_transition(g,base,delta,eta):
    frozen.need(eta in frozen.ETAS and len(base)==7 and len(delta)==4,
                "FROZEN_WING_TRANSITION")
    frozen.prior.parent.validate_15(g)
    weights=q.wingless_anchored_weights(list(base),list(delta))
    edges=old_o.sorted_edges(g)
    index=defaultdict(list)
    work={"edge_inspections":len(edges),"raw_bit_reads":0,"affinity_ops":0,
          "max_active":1,"max_states_per_node":1,"max_packed_bits_per_state":12,
          "max_index_entries":len(edges),"max_encoded_cache":0,
          "max_lookahead_cache":0,"transition_packed_channel_comparisons":0,
          "violating_transition_candidates":0,"sum_excess_channel_mismatch":0}
    for e in edges:index[(e["from"],e["role"])].append(e)
    def packed(bits):
        work["raw_bit_reads"]+=16
        result=0
        for j in range(4):
            code=sum(CHECKSUM[i]*bits[4*j+i] for i in range(4))%5
            result|=code<<(3*j)
        return result
    def affinity(a,b):
        work["affinity_ops"]+=4
        av=[weights[j]*(((a>>(3*j))&7)-2)/2 for j in range(4)]
        bv=[weights[j]*(((b>>(3*j))&7)-2)/2 for j in range(4)]
        return 1.-sum(abs(x-y) for x,y in zip(av,bv))/8.
    states={g["start"]:(0.,None)}
    for step,role in enumerate(g["roles"]):
        nxt=g["roles"][step+1] if step+1<len(g["roles"]) else None
        following=defaultdict(list)
        for node in sorted(states):
            score,carried=states[node]
            eligible=index.get((node,role),())
            work["edge_inspections"]+=len(eligible)
            for e in eligible:
                src=packed(e["src_bits"]);dst=packed(e["dst_bits"])
                match=1. if carried is None else affinity(carried,src)
                value=score+weights[4]*(match-.6)
                if eta and carried is not None:
                    work["transition_packed_channel_comparisons"]+=4
                    mismatch=sum(((carried>>(3*j))&7)!=((src>>(3*j))&7)
                                 for j in range(4))
                    extra=max(0,mismatch-1)
                    work["violating_transition_candidates"]+=int(extra>0)
                    work["sum_excess_channel_mismatch"]+=extra
                    value-=eta*extra
                look=0.
                if nxt is not None:
                    successors=index.get((e["to"],nxt),())
                    work["edge_inspections"]+=len(successors)
                    look=max((affinity(dst,packed(n["src_bits"]))
                              for n in successors),default=0.)
                rank=value+weights[5]*(look-.6)
                following[e["to"]].append((rank,value,dst))
        states={}
        for node,rows in following.items():
            rows.sort(key=lambda x:(-x[0],-x[1],x[2]))
            states[node]=(rows[0][1],rows[0][2])
        work["max_active"]=max(work["max_active"],len(states))
        frozen.need(work["max_active"]<=64,"ONE_STATE_PER_NODE_ONLY")
    best=states.get(g["target"],(-2.*len(g["roles"]),None))[0]
    score=4.*(best/max(1,len(g["roles"])-1)-weights[6])
    frozen.need(math.isfinite(score),"FINITE_PACKED_HOP_SCORE")
    return score,work

def fit(lane,cases,base,delta):
    frozen.need(lane in ("Yggdrasil","Wingless") and len(cases)==48,
                "FRESH_TRAIN_SELECTION")
    scoring=ygg_transition if lane=="Yggdrasil" else wing_transition
    grid=[]
    for eta in frozen.ETAS:
        correct=0
        for _,_,_,positive,negative in cases:
            p=scoring(positive,base,delta,eta)[0]
            n=scoring(negative,base,delta,eta)[0]
            correct+=int(p>=0 and n<0)
        grid.append({"eta":eta,"paired":correct})
    chosen=sorted(grid,key=lambda x:(-x["paired"],x["eta"]))[0]
    return chosen,grid
