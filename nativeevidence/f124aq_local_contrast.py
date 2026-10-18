"""F124-AQ relative local ambiguity evidence with ORIGINAL one 12-bit state/node.

Contrast within-hop sibling and relative handoff alternatives using temporary
scores; original single retained-state semantics are unchanged. Exact alpha-zero delegates to original
qualified AN, making unmodified baseline byte-for-byte identical.
No second retained state, beam, path cache or additional active capacity.
"""
from __future__ import annotations
from collections import defaultdict
import math
import f124ae_frozen_source as structural
import f124q_independent_binding as q
import f124o_native_learners as o
import f124am_terminal_competition as original

MODES=("original_gamma0","local_sibling_ambiguity",
       "relative_lookahead_contrast")
ALPHAS=(0.,.02,.06,.12)
CHECKSUM=original.CHECKSUM

def need(ok,tag):structural.need(ok,"F124AQ_"+tag)

def score(graph,base,delta,mode,alpha):
    need(mode in MODES and alpha in ALPHAS,"PRESELECTED_HOP_MODE")
    if mode=="original_gamma0" or alpha==0.:
        val,work=original.terminal_competitive(graph,base,delta,0.)
        return val,dict(work,extra_hop_evidence_ops=0,
                        extra_retained_states=0,
                        source_oracle_in_model=False)
    structural.validate_15(graph)
    weights=q.wingless_anchored_weights(list(base),list(delta))
    edges=o.sorted_edges(graph)
    index=defaultdict(list)
    work={"edge_inspections":len(edges),"raw_bit_reads":0,
          "affinity_ops":0,"max_active":1,
          "max_states_per_node":1,"max_packed_bits_per_state":12,
          "max_index_entries":len(edges),"max_encoded_cache":0,
          "max_lookahead_cache":0,"extra_hop_evidence_ops":0,
          "extra_retained_states":0,"source_oracle_in_model":False}
    for e in edges:index[(e["from"],e["role"])].append(e)
    def packed(bits):
        work["raw_bit_reads"]+=16
        ret=0
        for j in range(4):
            code=sum(CHECKSUM[i]*bits[4*j+i] for i in range(4))%5
            ret|=code<<(3*j)
        return ret
    def affinity(a,b):
        work["affinity_ops"]+=4
        av=[weights[j]*(((a>>(3*j))&7)-2)/2 for j in range(4)]
        bv=[weights[j]*(((b>>(3*j))&7)-2)/2 for j in range(4)]
        return 1.-sum(abs(x-y) for x,y in zip(av,bv))/8.
    states={graph["start"]:(0.,None)}
    for step,role in enumerate(graph["roles"]):
        nxt=(graph["roles"][step+1]
             if step+1<len(graph["roles"]) else None)
        candidates=defaultdict(list)
        for node in sorted(states):
            previous,carried=states[node]
            eligible=index.get((node,role),())
            work["edge_inspections"]+=len(eligible)
            rival=[(1. if carried is None else
                    affinity(carried,packed(e["src_bits"])))
                   for e in eligible]
            work["extra_competitor_packed_evaluations"]=work.get(
                "extra_competitor_packed_evaluations",0)+len(rival)
            future=[]
            if mode=="relative_lookahead_contrast" and nxt is not None:
                for outgoing in eligible:
                    next_edges=index.get((outgoing["to"],nxt),())
                    code=packed(outgoing["dst_bits"])
                    future.append(max((affinity(code,packed(n["src_bits"]))
                                       for n in next_edges),default=0.))
                    work["extra_hop_evidence_ops"]+=len(next_edges)+1
            for k,e in enumerate(eligible):
                src=packed(e["src_bits"])
                dst=packed(e["dst_bits"])
                continuity=(1. if carried is None else affinity(carried,src))
                value=previous+weights[4]*(continuity-.6)
                strongest=max((m for j,m in enumerate(rival) if j!=k),
                              default=continuity)
                value+=.5*(continuity-strongest)
                look=0.
                if nxt is not None:
                    following=index.get((e["to"],nxt),())
                    work["edge_inspections"]+=len(following)
                    look=max((affinity(dst,packed(n["src_bits"]))
                              for n in following),default=0.)
                if mode=="local_sibling_ambiguity" and carried is not None and len(eligible)>1:
                    gap=abs(continuity-strongest)
                    value-=alpha*max(0.,(.15-gap)/.15)
                    work["extra_hop_evidence_ops"]+=3
                if mode=="relative_lookahead_contrast" and nxt is not None and len(future)>1:
                    other=max((v for j,v in enumerate(future) if j!=k),
                              default=look)
                    value-=alpha*max(0.,other-look)
                    work["extra_hop_evidence_ops"]+=len(future)
                rank=value+weights[5]*(look-.6)
                candidates[e["to"]].append((rank,value,dst))
        states={}
        for node,rows in candidates.items():
            rows.sort(key=lambda x:(-x[0],-x[1],x[2]))
            states[node]=(rows[0][1],rows[0][2])
        work["max_active"]=max(work["max_active"],len(states))
        need(work["max_active"]<=64,"ORIGINAL_64_ACTIVE_NODES")
    best=states.get(graph["target"],(-2.*len(graph["roles"]),None))[0]
    val=4.*(best/max(1,len(graph["roles"])-1)-weights[6])
    need(math.isfinite(val) and work["max_states_per_node"]==1 and
         work["max_packed_bits_per_state"]==12,"NO_CAPACITY_GROWTH")
    return val,work

def select(normalized_cases,base,delta):
    """Normalized pairs from source/evaluator only; no model source oracle."""
    need(len(normalized_cases)==48 and
         all(len(row)==4 for row in normalized_cases),"TRAIN_NORMALIZED_CASES")
    baseline_long=set()
    for identity,family,pos,neg in normalized_cases:
        val,_=score(pos,base,delta,"original_gamma0",0.)
        if len(pos["roles"])>=13 and val>=0:
            baseline_long.add(identity)
    results=[]
    configs=[("original_gamma0",0.)]+[
        (m,a) for m in MODES[1:] for a in ALPHAS[1:]]
    for mode,alpha in configs:
        paired=fp=fn=work=0
        accepted=set()
        for identity,family,pos,neg in normalized_cases:
            vp,wp=score(pos,base,delta,mode,alpha)
            vn,wn=score(neg,base,delta,mode,alpha)
            paired+=int(vp>=0 and vn<0)
            fp+=int(vn>=0)
            fn+=int(vp<0)
            work+=wp["extra_hop_evidence_ops"]+wn["extra_hop_evidence_ops"]
            if len(pos["roles"])>=13 and vp>=0: accepted.add(identity)
            for w in (wp,wn):
                need(w["max_states_per_node"]==1 and
                     w["max_packed_bits_per_state"]==12 and
                     w["max_active"]<=64 and
                     w["extra_retained_states"]==0,"ONE_PACKED_LIMIT")
        results.append({"mode":mode,"alpha":alpha,"paired":paired,
                        "FP":fp,"FN":fn,"extra_hop_ops":work,
                        "accepted_long":len(accepted),
                        "baseline_long":len(baseline_long),
                        "strict_train_preservation":baseline_long.issubset(accepted)})
    eligible=[r for r in results if r["strict_train_preservation"]]
    need(any(r["mode"]=="original_gamma0" for r in eligible),
         "BASELINE_MUST_BE_ELIGIBLE")
    chosen=sorted(eligible,key=lambda r:(
        -r["paired"],r["FP"],r["extra_hop_ops"],
        r["mode"]!="original_gamma0",r["mode"],r["alpha"]))[0]
    return chosen,results
