"""F124-Z separately frozen sparse compression and public-key continuity.

Both models use ONLY public graph fields, original model weights, and
unchanged inference capacity. No labels, route oracle, DEV training, or
hidden causal path is ever passed into a predictor.
"""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
import json, math, types

import f124y_frozen_models as parent
import f124w_hop_trace_indexed as old_index
import f124q_fresh_source as source
import f124q_independent_binding as original_q
import f124o_native_learners as model

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124z-frozen-sparse-continuity.json"
FREEZE_BLOB="83e82ec2d7ffdbd2fdea69c4cd6dbe0f94cd8f05"
PARENT_SOURCE_BLOB="49d16818a4e9db0e19e1a77d2f6703e5a7c69341"
ORIGINAL_Q_BLOB="ebad38ff22ef6b151fd5ff7f25da41a20d9fcf65"
COHORTS={
 "Wingless":{"FIT":range(1280000,1280024),"DEV":range(1280100,1280124)},
 "Yggdrasil":{"FIT":range(1290000,1290024),"DEV":range(1290100,1290124)}
}
VECTORS=parent.x.VECTORS
CHECKSUM=(1,3,4,2)
PENALTIES=(0.,.5,1.,2.,4.,8.)


def need(ok,label):
    source.need(ok,"F124Z_"+label)


def frozen():
    parent.frozen()
    need(old_index.blob(FREEZE)==FREEZE_BLOB,"FROZEN_PROTOCOL_BLOB")
    p=json.loads(FREEZE.read_text(encoding="utf-8"))
    need(p["schema"]=="forge.research.f124z.frozen-sparse-compression-and-cell-continuity.v1"
         and p["state"]=="PREIMPLEMENTATION_FROZEN"
         and p["lineage"]["qualified_parent"]==
             "f4d8770482cce0d0f282420b45a1bd931cf81bd5"
         and p["lineage"]["source_parent_blob"]==PARENT_SOURCE_BLOB
         and p["lineage"]["original_q_inference_blob"]==ORIGINAL_Q_BLOB
         and p["source"]["FIT"]==
           {lane:[d["FIT"].start,d["FIT"].stop-1] for lane,d in COHORTS.items()}
         and p["source"]["DEV"]==
           {lane:[d["DEV"].start,d["DEV"].stop-1] for lane,d in COHORTS.items()}
         and p["Wingless"]["selected_checksum"]==list(CHECKSUM)
         and p["Yggdrasil"]["penalties"]==list(PENALTIES)
         and p["Yggdrasil"]["cells"]=={"active":7,"retained":9}
         and all(x is False for x in p["authority"].values())
         and old_index.blob(parent.__file__)==PARENT_SOURCE_BLOB
         and old_index.blob(original_q.__file__)==ORIGINAL_Q_BLOB,
         "SOURCE_OR_ORIGINAL_MODEL_CHANGED")
    return p


def build(lane,seed,vec,phase):
    need(lane in COHORTS and phase in ("FIT","DEV")
         and type(seed) is int and seed in COHORTS[lane][phase]
         and tuple(vec) in VECTORS
         and seed not in parent.COHORTS[lane]["FIT"]
         and seed not in parent.COHORTS[lane]["DEV"]
         and seed not in source.COHORTS[lane]["FIT"]
         and seed not in source.COHORTS[lane]["DEV"]
         and seed not in source.FORBIDDEN[lane],"NONREUSED_PUBLIC_SOURCE")
    glob=dict(parent.build.__globals__)
    glob["COHORTS"]=COHORTS
    method=types.FunctionType(parent.build.__code__,glob,
                              parent.build.__name__,parent.build.__defaults__)
    positive,negative=method(lane,seed,vec,phase)
    need(source.paired_admit(positive,negative),"PUBLIC_SOURCE_ADMISSION")
    return positive,negative


def pairs(lane,phase):
    need(lane in COHORTS and phase in ("FIT","DEV"),"PHASE")
    return [(seed,tuple(vec),*build(lane,seed,vec,phase))
            for vec in VECTORS for seed in COHORTS[lane][phase]]


def sparse_wingless(graph,base,delta):
    """No compressed-edge or future-look cache: sparse on-demand adjacency.

    Reproduces EXACT V float update and sorting semantics. Reuses prior
    4 channels/5 bins/3 states/node/192 global state capacity. No full
    compressed-edge cache, no persistent lookahead cache.
    """
    source.validate_public(graph)
    weights=original_q.wingless_anchored_weights(list(base),list(delta))
    edges=model.sorted_edges(graph)
    adjacent=defaultdict(list)
    work={"adjacency_build_edges":len(edges),"edge_inspections":len(edges),
          "on_demand_raw_bit_reads":0,"affinity_operations":0,
          "max_adjacent_index_entries":len(edges),
          "max_encoded_cache_entries":0,"max_future_cache_entries":0,
          "max_active":1,"evictions":0,"state_limit":3,
          "compression_levels":5,"compression_channels":4}
    for edge in edges:
        adjacent[(edge["from"],edge["role"])].append(edge)

    def encode(bits):
        work["on_demand_raw_bit_reads"]+=16
        return tuple(weights[j]*(
            (sum(CHECKSUM[i]*bits[4*j+i] for i in range(4))%5)-2)/2
            for j in range(4))

    def affinity(a,b):
        work["affinity_operations"]+=4
        return 1.-sum(abs(x-y) for x,y in zip(a,b))/8.

    states={graph["start"]:[(0.,None)]}
    for step,role in enumerate(graph["roles"]):
        nxt=graph["roles"][step+1] if step+1<len(graph["roles"]) else None
        following=defaultdict(list)
        for node in sorted(states):
            choices=adjacent.get((node,role),())
            for score,carried in states[node]:
                work["edge_inspections"]+=len(choices)
                for edge in choices:
                    src=encode(edge["src_bits"])
                    dst=encode(edge["dst_bits"])
                    match=1. if carried is None else affinity(carried,src)
                    value=score+weights[4]*(match-.6)
                    if nxt is None:
                        look=0.
                    else:
                        prospect=adjacent.get((edge["to"],nxt),())
                        work["edge_inspections"]+=len(prospect)
                        look=max((affinity(dst,encode(e["src_bits"]))
                                  for e in prospect),default=0.)
                    priority=value+weights[5]*(look-.6)
                    following[edge["to"]].append((priority,value,dst))
        states={}
        for node,rows in following.items():
            rows.sort(key=lambda x:(-x[0],-x[1],x[2]))
            work["evictions"]+=max(0,len(rows)-3)
            states[node]=[(score,vec) for _,score,vec in rows[:3]]
        work["max_active"]=max(work["max_active"],
                               sum(len(rows) for rows in states.values()))
        need(work["max_active"]<=192 and
             all(len(rows)<=3 for rows in states.values()),"SAME_WING_STATE_BUDGET")
    terminals=[score for score,_ in states.get(graph["target"],[])]
    best=max(terminals,default=-2.*len(graph["roles"]))
    result=4.*(best/max(1,len(graph["roles"])-1)-weights[6])
    need(math.isfinite(result),"FINITE_WING_LOGIT")
    return result,work


def continuity_head(graph,base,delta):
    """Exact T ranking, cells & logit, plus causal-key continuity counter.

    Explicit equality checks are on *public* raw 16-bit keys; these are an
    added inference feature, not a scorer-provided label or symbolic oracle.
    """
    source.validate_public(graph)
    need(len(base)==7 and len(delta)==2 and
         all(math.isfinite(v) for v in (*base,*delta)),"MODEL_SHAPE")
    edges=model.sorted_edges(graph)
    active=[(graph["start"],None,0.,0)]
    retained=[]
    work={"public_edge_scans":0,"raw_bit_ops":0,"max_active":1,
          "max_retained":0,"evictions":0,"prospective_key_comparisons":0,
          "active_cell_limit":7,"retained_cell_limit":9,
          "continuity_raw_bit_comparisons":0,
          "continuity_counter_slots_max":1}
    def comp(carried,src):
        if carried is None:return 1.
        work["raw_bit_ops"]+=16
        return sum(base[j]*sum(int(a==b) for a,b in zip(
            carried[j*4:j*4+4],src[j*4:j*4+4]))/4. for j in range(4))/4.
    for step,role in enumerate(graph["roles"]):
        nextrole=graph["roles"][step+1] if step+1<len(graph["roles"]) else None
        candidates=[]
        for node,carried,score,consistent in active+retained:
            work["public_edge_scans"]+=len(edges)
            for edge in edges:
                if edge["from"]!=node or edge["role"]!=role:continue
                similarity=comp(carried,edge["src_bits"])
                value=score+base[4]*(similarity-.35)
                competition=base[5]*(similarity-.5)
                if nextrole is None:
                    look=0.
                else:
                    possible=[e for e in edges if e["from"]==edge["to"] and
                              e["role"]==nextrole]
                    work["public_edge_scans"]+=len(edges)
                    look=max((comp(tuple(edge["dst_bits"]),p["src_bits"])
                              for p in possible),default=0.)
                    work["prospective_key_comparisons"]+=len(possible)
                if carried is None:
                    chain=1
                else:
                    work["continuity_raw_bit_comparisons"]+=16
                    chain=consistent+int(tuple(carried)==tuple(edge["src_bits"]))
                cell=(edge["to"],tuple(edge["dst_bits"]),value,chain)
                candidates.append((value+competition+delta[0]*(look-.5),
                                   value-competition+delta[1]*(look-.5),cell))
        candidates.sort(key=lambda a:(-a[0],-a[1],a[2][0],a[2][1]))
        active=[row[2] for row in candidates[:7]]
        picked={id(row) for row in candidates[:7]}
        extras=[row for row in candidates if id(row) not in picked]
        extras.sort(key=lambda a:(-a[1],-a[0],a[2][0],a[2][1]))
        retained=[row[2] for row in extras[:9]]
        work["evictions"]+=max(0,len(candidates)-16)
        work["max_active"]=max(work["max_active"],len(active))
        work["max_retained"]=max(work["max_retained"],len(retained))
        work["continuity_counter_slots_max"]=max(
            work["continuity_counter_slots_max"],len(active)+len(retained))
        need(len(active)<=7 and len(retained)<=9 and
             len(active)+len(retained)<=16,"SEVEN_PLUS_NINE")
    terminal=[cell for cell in active+retained if cell[0]==graph["target"]]
    best=max((cell[2] for cell in terminal),default=-2.*len(graph["roles"]))
    original_logit=4.*(best/max(1,len(graph["roles"])-1)-base[6])
    ratio=max((cell[3]/len(graph["roles"]) for cell in terminal),default=0.)
    need(math.isfinite(original_logit) and 0<=ratio<=1,"FINITE_CONTINUITY_READOUT")
    return original_logit,ratio,work


def corrected_logit(original_logit,ratio,penalty):
    need(penalty in PENALTIES and 0<=ratio<=1
         and math.isfinite(original_logit),"FROZEN_FIT_ONLY_PENALTY")
    return original_logit-penalty*(1.-ratio)


def choose_fit_penalty(cases,base,delta):
    need(len(cases)==48,"FIT_ONLY_DENOMINATOR")
    rows=[]
    for _,_,pos,neg in cases:
        p,pr,_=continuity_head(pos,base,delta)
        n,nr,_=continuity_head(neg,base,delta)
        rows.append((p,pr,n,nr))
    scores=[]
    for penalty in PENALTIES:
        count=sum(corrected_logit(p,pr,penalty)>=0 and
                  corrected_logit(n,nr,penalty)<0
                  for p,pr,n,nr in rows)
        scores.append({"penalty":penalty,"paired":count})
    selected=sorted(scores,key=lambda x:(-x["paired"],x["penalty"]))[0]
    return selected,scores
