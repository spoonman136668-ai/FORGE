"""F124-BD independent public-graph causal path certificate.

This is a model-blind FULL-CHAIN evidence check on the decoded PUBLIC graph:
start node -> ordered public roles -> target, with per-edge 16-bit continuity.
It cannot see source operator names, private key, oracle labels, near-miss
construction edits, or ground-truth routes. It uses the same learned inverse
trained on the original 40 public FIT rows, selected with 8 public CHECK rows.

No calls to historical evaluator's routes() or routes15() functions.
"""
from __future__ import annotations
import f124az_joint_public_inverse as joint
import f124bb_public_consensus as normal
import f124q_fresh_source as q

POLICIES=("exact0","tolerant1","public_adaptive")
FRONTIER_BOUND=65536
def need(ok,tag):q.need(ok,"F124BD_PUBLIC_WITNESS_"+tag)

def search_public_path(public_graph,max_hamming):
    need(max_hamming in (0,1),"REGISTERED_0_OR_1_MATCH")
    roles=public_graph["roles"]
    edges=public_graph["edges"]
    need(7<=len(roles)<=15 and 12<=len(edges)<=128,
         "UNCHANGED_PUBLIC_GRAPH_SHAPE")
    by_key={}
    for edge in edges:
        k=(edge["from"],edge["role"])
        by_key.setdefault(k,[]).append(edge)
    frontier={(public_graph["start"],None)}
    scans=0;bit_checks=0;peak=1
    for role in roles:
        after=set()
        for node,carry in frontier:
            for edge in by_key.get((node,role),()):
                scans+=1
                s=tuple(edge["src_bits"])
                need(len(s)==16 and len(edge["dst_bits"])==16,
                     "PUBLIC_16_BIT_GRAPH")
                if carry is not None:
                    distance=sum(a!=b for a,b in zip(carry,s))
                    bit_checks+=16
                    if distance>max_hamming:continue
                after.add((edge["to"],tuple(edge["dst_bits"])))
                need(len(after)<=FRONTIER_BOUND,
                     "NO_UNBOUNDED_MODEL_FRONTIER")
        frontier=after
        peak=max(peak,len(frontier))
        if not frontier:break
    certified=any(node==public_graph["target"] for node,_ in frontier)
    return {"certificate_found":certified,"frontier_peak":peak,
            "public_edge_scans":scans,"public_bit_comparisons":bit_checks,
            "frontier_lower_bound_bits":peak*(16+64),
            "role_depth":len(roles),
            "used_source_truth":False,
            "operator_key_or_graph_family_seen":False}

def policy_radius(policy,model):
    need(policy in POLICIES and
         model["choice"] in ("affine","feistel","abstain"),
         "ONLY_PRECOMMITTED_PUBLIC_GATE")
    if policy=="exact0":return 0
    if policy=="tolerant1":return 1
    correct=(model["affine_check"] if model["choice"]=="affine"
             else model["feistel_check"])
    need(isinstance(correct,int) and 0<=correct<=128,
         "EIGHT_PUBLIC_CHECK_ONLY")
    return 0 if correct>=120 else 1

def score(graph,base,delta,model,demos,policy):
    need(policy in POLICIES and
         model["margin"]==0 and len(demos)==48,
         "FROZEN_PUBLIC_CONFIDENCE_AND_UNCHANGED_ROUTER")
    baseline,work,_=joint.score(graph,base,delta,model,demos)
    if baseline<0:
        return baseline,work,{"baseline_positive":False,
           "veto":False,"certificate_searched":False,"certified":False,
           "radius":None,"extra_frontier_bits":0,
           "additional_16bit_inverse_graph_decoding":0,
           "source_truth_seen":False}
    public_graph=normal.public_graph(graph,demos,model)
    radius=policy_radius(policy,model)
    cert=search_public_path(public_graph,radius)
    return baseline if cert["certificate_found"] else -1e9,work,{
        "baseline_positive":True,"veto":not cert["certificate_found"],
        "certificate_searched":True,"certified":cert["certificate_found"],
        "radius":radius,
        "extra_frontier_bits":cert["frontier_lower_bound_bits"],
        "additional_16bit_inverse_graph_decoding":len(public_graph["edges"])*16,
        "public_edge_scans":cert["public_edge_scans"],
        "public_bit_comparisons":cert["public_bit_comparisons"],
        "source_truth_seen":False}
