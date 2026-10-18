"""F124-AO within-final-hop ambiguity evidence retaining ONE packed state/node.

Same frozen F124-AM beta0.5 packed transition as AN gamma0. Distinct causal
penalties use only ephemeral final-hop candidate ranks and their already-packed
12-bit codes. Extra temporary comparisons counted; no per-node alternative
state or encoded cache survives a hop. Only certified source-normalized inputs
may be supplied by the external evaluator for this conditional experiment.
"""
from __future__ import annotations
from collections import defaultdict
import math
import f124ae_frozen_source as structural
import f124q_independent_binding as q
import f124o_native_learners as o
import f124am_terminal_competition as original

CHECKSUM=original.CHECKSUM
MODES=("gamma0","sibling","alternative")
ALPHAS=(0.,.05,.1,.2)

def need(ok,tag): structural.need(ok,"F124AO_"+tag)

def score(graph,base,delta,mode,alpha):
    need(mode in MODES and alpha in ALPHAS,"PRESELECTED_CANDIDATE")
    if mode=="gamma0" or alpha==0.:
        out,work=original.terminal_competitive(graph,base,delta,0.)
        return out,dict(work,model_extra_candidate_inspections=0,
                        extra_retained_states=0,
                        source_evaluator_normalization_included=False)
    structural.validate_15(graph)
    weights=q.wingless_anchored_weights(list(base),list(delta))
    edges=o.sorted_edges(graph)
    index=defaultdict(list)
    work={"edge_inspections":len(edges),"raw_bit_reads":0,
          "affinity_ops":0,"max_active":1,"max_states_per_node":1,
          "max_packed_bits_per_state":12,"max_index_entries":len(edges),
          "max_encoded_cache":0,"max_lookahead_cache":0,
          "model_extra_candidate_inspections":0,"extra_retained_states":0,
          "source_evaluator_normalization_included":False}
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
    states={graph["start"]:(0.,None)}
    penalty=0.
    for step,role in enumerate(graph["roles"]):
        following=defaultdict(list)
        next_role=(graph["roles"][step+1]
                   if step+1<len(graph["roles"]) else None)
        for node in sorted(states):
            prior,carried=states[node]
            eligible=index.get((node,role),())
            work["edge_inspections"]+=len(eligible)
            rivals=[1. if carried is None else
                    affinity(carried,packed(e["src_bits"]))
                    for e in eligible]
            work["extra_competitor_packed_evaluations"]=work.get(
                "extra_competitor_packed_evaluations",0)+len(rivals)
            for k,e in enumerate(eligible):
                src=packed(e["src_bits"])
                dst=packed(e["dst_bits"])
                match=1. if carried is None else affinity(carried,src)
                value=prior+weights[4]*(match-.6)
                strongest=max((m for j,m in enumerate(rivals) if j!=k),
                              default=match)
                value+=.5*(match-strongest)
                look=0.
                if next_role is not None:
                    next_edges=index.get((e["to"],next_role),())
                    work["edge_inspections"]+=len(next_edges)
                    look=max((affinity(dst,packed(n["src_bits"]))
                              for n in next_edges),default=0.)
                rank=value+weights[5]*(look-.6)
                following[e["to"]].append((rank,value,dst))
        states={}
        for node,rows in following.items():
            rows.sort(key=lambda x:(-x[0],-x[1],x[2]))
            states[node]=(rows[0][1],rows[0][2])
        # All extra comparison values are transient for THIS terminal hop.
        if step==len(graph["roles"])-1:
            rows=following.get(graph["target"],())
            if mode=="sibling" and len(rows)>1:
                gap=max(0.,rows[0][0]-rows[1][0])
                mismatch=(rows[0][2]^rows[1][2]).bit_count()/12.
                penalty=alpha*max(0.,1.-gap)*(1.-mismatch)
                work["model_extra_candidate_inspections"]+=2
            elif mode=="alternative" and rows:
                highest=rows[0][0]
                other=max((v[0][0] for node,v in following.items()
                           if node!=graph["target"] and v),default=None)
                work["model_extra_candidate_inspections"]+=sum(
                    bool(v) for v in following.values())
                if other is not None:
                    penalty=alpha*min(1.,max(0.,1.+other-highest))
        work["max_active"]=max(work["max_active"],len(states))
        need(work["max_active"]<=64,"SINGLE_PACKED_STATE_LIMIT")
    best=states.get(graph["target"],(-2.*len(graph["roles"]),None))[0]
    output=4.*(best/max(1,len(graph["roles"])-1)-weights[6])-penalty
    need(math.isfinite(output),"FINITE_OUTPUT")
    work["extra_ambiguity_penalty"]=penalty
    return output,work

def select(cases,base,delta):
    """Filter by identical AN gamma0 accepted long-positives on TRAIN first."""
    need(len(cases)==48,"TRAIN_ONLY")
    rows=[]
    # Cases are evaluator-certified source-normalized tuples (id,family,pos,neg).
    # This module never handles the hidden operation, inverse or truth oracle.
    need(all(len(row)==4 and set(row[2])=={"start","target","roles","edges"}
             and set(row[3])=={"start","target","roles","edges"}
             for row in cases),"EVALUATOR_CERTIFIED_GRAPH_SHAPE")
    protected=set()
    for identity,family,pos,neg in cases:
        result,_=score(pos,base,delta,"gamma0",0.)
        if len(pos["roles"])>=13 and result>=0:
            protected.add(identity)
    results=[]
    for mode in MODES:
        for alpha in ((0.,) if mode=="gamma0" else ALPHAS[1:]):
            paired=fp=fn=extra=0
            accepted=set()
            for identity,family,pos,neg in cases:
                yes,wa=score(pos,base,delta,mode,alpha)
                no,wb=score(neg,base,delta,mode,alpha)
                paired+=int(yes>=0 and no<0)
                fp+=int(no>=0)
                fn+=int(yes<0)
                extra+=wa["model_extra_candidate_inspections"]
                extra+=wb["model_extra_candidate_inspections"]
                if len(pos["roles"])>=13 and yes>=0:accepted.add(identity)
                for work in (wa,wb):
                    need(work["max_states_per_node"]==1 and
                         work["max_packed_bits_per_state"]==12 and
                         work["max_active"]<=64,"FROZEN_STATE_BUDGET")
            results.append({"mode":mode,"alpha":alpha,"paired":paired,
                            "FP":fp,"FN":fn,"extra_inspections":extra,
                            "accepted_long":len(accepted),
                            "protected_long":len(protected),
                            "strict_train_preservation":protected.issubset(accepted)})
    eligible=[r for r in results if r["strict_train_preservation"]]
    need(any(r["mode"]=="gamma0" for r in eligible),"CONTROL_ELIGIBLE")
    chosen=sorted(eligible,key=lambda r:(-r["paired"],r["FP"],
           r["extra_inspections"],r["mode"]!="gamma0",
           r["mode"],r["alpha"]))[0]
    return chosen,results
