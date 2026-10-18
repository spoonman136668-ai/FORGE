"""F124-BE public edge-local contrast, independent of protected source oracle.

A one-bit-tolerant path is independently contradicted when another decoded
public edge carrying the same (from,role) has an exactly matching incoming
key; alternatively a mismatched hop without independently corroborating
public peer edges is unsupported. Three preregistered policies veto only
existing original AZ joint positives. No true operator, hidden family label,
or evaluator route function is imported into this model.
"""
from __future__ import annotations
import f124az_joint_public_inverse as joint
import f124bb_public_consensus as decoder
import f124q_fresh_source as q

POLICIES=("reject_peer_contradicted","reject_peer_unbacked","reject_peer_both")
BOUND=65536
def need(ok,name):q.need(ok,"F124BE_PUBLIC_CONTRAST_"+name)

def public_peer_decisions(graph):
    roles=graph["roles"];edges=graph["edges"]
    need(7<=len(roles)<=15 and 12<=len(edges)<=128,
         "PUBLIC_GRAPH_7_TO_15")
    indexed={}
    for i,e in enumerate(edges):
        need(len(e["src_bits"])==len(e["dst_bits"])==16,
             "PUBLIC_GRAPH_16_BITS")
        indexed.setdefault((e["from"],e["role"]),[]).append((i,e))
    # All paths use public node/role, decoded public values and no oracle.
    frontier=[(graph["start"],None,())]
    peak=1;scans=0;bitcompares=0
    for role in roles:
        nxt=[]
        for node,carry,gaps in frontier:
            for ix,e in indexed.get((node,role),()):
                scans+=1
                incoming=tuple(e["src_bits"])
                if carry is None:distance=0
                else:
                    distance=sum(a!=b for a,b in zip(carry,incoming))
                    bitcompares+=16
                if distance>1:continue
                add=gaps+(((ix,tuple(carry)),) if distance==1 else ())
                nxt.append((e["to"],tuple(e["dst_bits"]),add))
                need(len(nxt)<=BOUND,"PATH_ENUMERATION_CAP")
        frontier=nxt
        peak=max(peak,len(frontier))
        if not frontier:break
    paths=[gaps for node,carry,gaps in frontier
           if node==graph["target"]]
    need(len(paths)<=BOUND,"TARGET_PATH_CAP")
    # Evidence for each distinct mismatch edge: only OTHER PUBLIC edges.
    cache={};peer_checks=0
    for gaps in paths:
        for idx,carry in gaps:
            signature=(idx,carry)
            if signature in cache:continue
            e=edges[idx]
            peers=[p for j,p in indexed.get((e["from"],e["role"]),())
                   if j!=idx]
            any_exact=False
            any_near=False
            for other in peers:
                distance=sum(a!=b for a,b in zip(carry,other["src_bits"]))
                peer_checks+=16
                any_exact|=distance==0
                any_near|=distance<=1
            same_to=[other for j,other in enumerate(edges)
                if j!=idx and other["to"]==e["to"] and
                   other["role"]==e["role"]]
            same_dst=any(other["dst_bits"]==e["dst_bits"] for other in same_to)
            peer_checks+=16*len(same_to)
            cache[signature]={"contradicted":bool(any_exact),
                              "unbacked":not any_near and not same_dst,
                              "peer_count":len(peers)+len(same_to)}
    def rejected(key):
        # One pristine target path suffices to preserve an original positive.
        # All candidate paths must contain a separately contradicted/unsupported gap.
        return bool(paths and all(
            gaps and any(cache[(edge,carry)][key] for edge,carry in gaps)
            for gaps in paths))
    veto_contradicted=rejected("contradicted")
    veto_unbacked=rejected("unbacked")
    return {"witness_paths":len(paths),"frontier_peak":peak,
            "mismatch_witness_pairs":len(cache),
            "veto_contradicted":veto_contradicted,
            "veto_unbacked":veto_unbacked,
            "veto_both":veto_contradicted and veto_unbacked,
            "path_edge_scans":scans,
            "public_bit_compares":bitcompares+peer_checks,
            "public_graph_bits_lower":len(edges)*16*2,
            "frontier_bits_lower":peak*(16+64+15*24),
            "source_oracle_seen":False,
            "graph_family_token_seen":False}

def score(graph,base,delta,model,demos,policy):
    need(policy in POLICIES and len(demos)==48 and model["margin"]==0,
         "ONLY_PRECOMMITTED_ROUTER_AND_POLICY")
    original,work,_=joint.score(graph,base,delta,model,demos)
    if original<0:
        return original,work,{"original_positive":False,
             "contrast_performed":False,"veto":False,
             "path_edge_scans":0,"public_bit_compares":0,
             "public_graph_bits_lower":0,"frontier_bits_lower":0}
    public_graph=decoder.public_graph(graph,demos,model)
    evidence=public_peer_decisions(public_graph)
    value={"reject_peer_contradicted":evidence["veto_contradicted"],
           "reject_peer_unbacked":evidence["veto_unbacked"],
           "reject_peer_both":evidence["veto_both"]}[policy]
    return original if not value else -1e9,work,dict(evidence,
          original_positive=True,contrast_performed=True,veto=value)
