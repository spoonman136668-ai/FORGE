"""F124-AF public-key consistency contrast and one-state terminal margin.

Only public graph fields and previously frozen original parameter vectors
are consulted. No label, oracle path or paired graph enters a predictor.
No new hard retained cells or Wingless per-node states are introduced.
"""
from __future__ import annotations
from collections import defaultdict
import math
import f124af_frozen_source as f
import f124ae_scoring_transfer as original
import f124ab_soft_hamming_pareto as ab
import f124q_independent_binding as q
import f124o_native_learners as original_o

def ygg_contrast(g,base,delta,lam):
    f.need(lam in f.LAMBDAS,"FROZEN_YGG_LAMBDA")
    anchored,raw,soft,work=original.anchored_score(g,base,delta,10)
    frozen_z,other_raw,hard,zw=original.frozen_z(g,base,delta)
    f.need(raw==other_raw and 0<=hard<=1 and 0<=soft<=1
           and all(work[k]==zw[k] for k in work
                   if k in zw and k not in ("hamming_bit_comparisons","soft_counter_slots_max")),
           "ORIGINAL_T_AND_Z_RAW_CUSTODY")
    # Exact-match ratio is measured on the original *same ranked 7+9 cells*;
    # the original Z lineage holds its own per-cell consistency counter.
    # The only new decision signal is the gap between original soft and hard.
    gap=max(0.,soft-hard)
    score=anchored if lam==0 else anchored-lam*gap
    f.need(math.isfinite(score),"FINITE_CONTRAST_SCORE")
    return score,anchored,soft,hard,work,zw

def ygg_fit(cases,base,delta):
    f.need(len(cases)==48,"FULL_DISJOINT_YGG_FIT")
    measured=[]
    for _,_,_,p,n in cases:
        a,_,sp,hp,_,_=ygg_contrast(p,base,delta,0.)
        b,_,sn,hn,_,_=ygg_contrast(n,base,delta,0.)
        measured.append((a,max(0.,sp-hp),b,max(0.,sn-hn)))
    grid=[{"lambda":lam,"paired":sum(
             (p-lam*gp)>=0 and (n-lam*gn)<0
             for p,gp,n,gn in measured)}
          for lam in f.LAMBDAS]
    win=sorted(grid,key=lambda x:(-x["paired"],x["lambda"]))[0]
    return win,grid

def wing_terminal(g,base,delta,beta):
    """One and only one retained 12-bit packed state/node, no raw witness.

    Margin is computed from terminal *already-retained* states; none are
    added or preserved along the causal trajectory just for diagnosis.
    """
    f.need(beta in f.BETAS,"FROZEN_WING_BETA")
    f.parent.validate_15(g)
    weights=q.wingless_anchored_weights(list(base),list(delta))
    edges=original_o.sorted_edges(g)
    index=defaultdict(list)
    work={"edge_inspections":len(edges),"raw_bit_reads":0,"affinity_ops":0,
          "max_active":1,"max_states_per_node":1,"max_packed_bits_per_state":12,
          "max_index_entries":len(edges),"max_encoded_cache":0,
          "max_lookahead_cache":0}
    for e in edges:index[(e["from"],e["role"])].append(e)
    def packed(bits):
        work["raw_bit_reads"]+=16
        result=0
        for j in range(4):
            code=sum((1,3,4,2)[i]*bits[4*j+i] for i in range(4))%5
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
            prev,carry=states[node]
            eligible=index.get((node,role),())
            work["edge_inspections"]+=len(eligible)
            for edge in eligible:
                src=packed(edge["src_bits"])
                dst=packed(edge["dst_bits"])
                match=1. if carry is None else affinity(carry,src)
                value=prev+weights[4]*(match-.6)
                look=0.
                if nxt is not None:
                    next_edges=index.get((edge["to"],nxt),())
                    work["edge_inspections"]+=len(next_edges)
                    look=max((affinity(dst,packed(e["src_bits"]))
                              for e in next_edges),default=0.)
                rank=value+weights[5]*(look-.6)
                following[edge["to"]].append((rank,value,dst))
        states={}
        for node,rows in following.items():
            rows.sort(key=lambda x:(-x[0],-x[1],x[2]))
            states[node]=(rows[0][1],rows[0][2])
        work["max_active"]=max(work["max_active"],len(states))
        f.need(work["max_active"]<=64,"ORIGINAL_ONE_STATE_CELL_BOUND")
    depth=len(g["roles"])
    target_score=states.get(g["target"],(-2.*depth,None))[0]
    raw=4.*(target_score/max(1,depth-1)-weights[6])
    competitors=[row[0] for node,row in states.items() if node!=g["target"]]
    # Only a scalar derived from the final original state collection, with no
    # persistent score competitor stored for the next hop.
    contrast=max(-1.,min(1.,(target_score-max(competitors))/depth)) if competitors else 0.
    score=raw if beta==0 else raw+beta*contrast
    f.need(math.isfinite(raw) and math.isfinite(score),"FINITE_ONE_SLOT_MARGIN")
    return score,raw,contrast,work

def wing_fit(cases,base,delta):
    f.need(len(cases)==48,"FULL_DISJOINT_WING_FIT")
    rows=[]
    for _,_,_,p,n in cases:
        _,a,ma,_=wing_terminal(p,base,delta,0.)
        _,b,mb,_=wing_terminal(n,base,delta,0.)
        rows.append((a,ma,b,mb))
    grid=[{"beta":beta,"paired":sum(
             (p+beta*mp)>=0 and (n+beta*mn)<0
             for p,mp,n,mn in rows)}
          for beta in f.BETAS]
    win=sorted(grid,key=lambda x:(-x["paired"],x["beta"]))[0]
    return win,grid
