"""F124-BF sourceblind graded counterfactual causal path margin.

No source oracle, graph family identity, source-birth edits or protected labels.
An unchanged original-joint positive is only vetoed when the best PUBLIC
role-ordered route requires a continuity error and another *distinct*
complete public route has nearly the same summed bit-continuity cost.
"""
from __future__ import annotations
import f124az_joint_public_inverse as joint
import f124bb_public_consensus as public
import f124q_fresh_source as q

POLICIES=(1,2,4)
BOUND=65536
def need(ok,tag):q.need(ok,"F124BF_CONTEXT_MARGIN_"+tag)

def route_margin(graph):
    roles=graph["roles"];edges=graph["edges"]
    need(7<=len(roles)<=15 and 12<=len(edges)<=128,
         "REGISTERED_SOURCE_GRAPH_BOUNDS")
    index={}
    for i,e in enumerate(edges):
        need(len(e["src_bits"])==len(e["dst_bits"])==16,
             "PUBLIC_DECODED_EDGE_BITS16")
        index.setdefault((e["from"],e["role"]),[]).append((i,e))
    frontier=[(graph["start"],None,0,())]
    peak=1;scans=0;compared_bits=0
    for role in roles:
        future=[]
        for node,carry,cost,path in frontier:
            for i,e in index.get((node,role),()):
                scans+=1
                incoming=tuple(e["src_bits"])
                step=0 if carry is None else sum(a!=b for a,b in zip(carry,incoming))
                if carry is not None:compared_bits+=16
                future.append((e["to"],tuple(e["dst_bits"]),cost+step,path+(i,)))
                need(len(future)<=BOUND,"BOUNDED_COUNTERFACTUAL_FRONTIER")
        frontier=future
        peak=max(peak,len(frontier))
        if not frontier:break
    terminal=sorted((cost,path) for node,carry,cost,path in frontier
                    if node==graph["target"])
    need(len(terminal)<=BOUND,"BOUNDED_COUNTERFACTUAL_TARGET_PATHS")
    best=terminal[0][0] if terminal else 256
    second=next((cost for cost,path in terminal[1:]
                 if path!=terminal[0][1]),256) if terminal else 256
    need(0<=best<=256 and 0<=second<=256 and second>=best,
         "COUNTERFACTUAL_PATH_MARGINS")
    return {"best_causal_bit_cost":best,
       "second_distinct_path_bit_cost":second,
       "public_competitor_gap":second-best,
       "public_path_count":len(terminal),
       "counterfactual_frontier_peak":peak,
       "public_graph_scans":scans,
       "public_bit_comparisons":compared_bits,
       "lower_bound_graph_bits":len(edges)*32,
       "lower_bound_frontier_bits":peak*(64+16+16+15*32),
       "source_oracle_used":False,
       "graph_family_used":False}

def score(graph,base,delta,model,demos,gap):
    need(gap in POLICIES and len(demos)==48 and model["margin"]==0,
         "ONLY_FROZEN_PUBLIC_POLICY")
    initial,work,_=joint.score(graph,base,delta,model,demos)
    if initial<0:
        return initial,work,{"veto":False,"margin_checked":False,
                             "public_graph_scans":0,
                             "public_bit_comparisons":0,
                             "lower_bound_graph_bits":0,
                             "lower_bound_frontier_bits":0}
    decoded=public.public_graph(graph,demos,model)
    d=route_margin(decoded)
    veto=(d["best_causal_bit_cost"]>=1 and
          d["public_competitor_gap"]<=gap)
    return initial if not veto else -1e9,work,dict(d,veto=veto,
         margin_checked=True,precommitted_gap_threshold=gap)
