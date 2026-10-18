"""F124-AC passive source-blind original-parity model instrumentation.

No ground-truth path, case label, or route validation in observer functions.
Both observers reproduce the original model's score operation ordering and
return original work counters plus a separately owned diagnostic trace.
"""
from __future__ import annotations
from collections import defaultdict
import math
import f124ac_frozen_source as frozen
import f124ab_soft_hamming_pareto as ab
import f124aa_packed_transfer as aa
import f124q_independent_binding as q
import f124o_native_learners as original_o

GAMMA=.25
PENALTY=.25
CHECKSUM=(1,3,4,2)

def observe_ygg(graph,base,delta):
    """Record all original 7+9 hard decisions, scores and soft-key evidence."""
    frozen.original.parent.validate_extended(graph)
    frozen.need(len(base)==7 and len(delta)==2,"ORIGINAL_MODEL_DIMENSIONS")
    edges=original_o.sorted_edges(graph)
    active=[(graph["start"],None,0.,0.)]
    retained=[];depth=len(graph["roles"])
    work={"public_edge_scans":0,"raw_bit_ops":0,"max_active":1,"max_retained":0,
          "evictions":0,"prospective_key_comparisons":0,"active_cell_limit":7,
          "retained_cell_limit":9,"hamming_bit_comparisons":0,"soft_counter_slots_max":1}
    trace=[]
    def compare(carry,src):
        if carry is None:return 1.
        work["raw_bit_ops"]+=16
        return sum(base[j]*sum(int(a==b) for a,b in zip(
            carry[j*4:j*4+4],src[j*4:j*4+4]))/4.
            for j in range(4))/4.
    for step,role in enumerate(graph["roles"]):
        nxt=graph["roles"][step+1] if step+1<depth else None
        candidates=[]
        for node,carry,score,history in active+retained:
            work["public_edge_scans"]+=len(edges)
            for edge in edges:
                if edge["from"]!=node or edge["role"]!=role:continue
                similarity=compare(carry,edge["src_bits"])
                value=score+base[4]*(similarity-.35)
                competition=base[5]*(similarity-.5)
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
                    mismatch=sum(x!=y for x,y in zip(carry,edge["src_bits"]))
                    contribution=max(0.,1.-GAMMA*mismatch)
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
        frozen.need(len(active)<=7 and len(retained)<=9,"ORIGINAL_SEVEN_PLUS_NINE")
        def compact(cell):
            return (cell[0],cell[1],cell[2],cell[3])
        trace.append({"hop":step+1,"role":role,
                      "candidate_count":len(candidates),
                      "evictions_this_hop":max(0,len(candidates)-16),
                      "candidate":[compact(x[2]) for x in candidates],
                      "active":[compact(x) for x in active],
                      "retained":[compact(x) for x in retained],
                      "top_scored_value":max((x[2][2] for x in candidates),default=None)})
    terminal=[cell for cell in active+retained if cell[0]==graph["target"]]
    best=max((c[2] for c in terminal),default=-2.*depth)
    raw=4.*(best/max(1,depth-1)-base[6])
    ratio=max((c[3]/depth for c in terminal),default=0.)
    logit=raw-PENALTY*(1.-ratio)
    frozen.need(math.isfinite(logit) and 0<=ratio<=1,"FINITE_TERMINAL_OBSERVATION")
    return logit,raw,ratio,work,trace

def observe_wing(graph,base,delta):
    """Exact original AA single packed slot with passive public diagnostics."""
    frozen.original.parent.validate_extended(graph)
    weights=q.wingless_anchored_weights(list(base),list(delta))
    edges=original_o.sorted_edges(graph)
    index=defaultdict(list)
    work={"edge_inspections":len(edges),"raw_bit_reads":0,"affinity_ops":0,
          "max_active":1,"max_states_per_node":1,"max_packed_bits_per_state":12,
          "max_index_entries":len(edges),"max_encoded_cache":0,"max_lookahead_cache":0}
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
    trace=[]
    for step,role in enumerate(graph["roles"]):
        nxt=graph["roles"][step+1] if step+1<len(graph["roles"]) else None
        following=defaultdict(list)
        for node in sorted(states):
            score,carried=states[node]
            eligible=index.get((node,role),())
            work["edge_inspections"]+=len(eligible)
            for edge in eligible:
                src=packed(edge["src_bits"]);dst=packed(edge["dst_bits"])
                match=1. if carried is None else affinity(carried,src)
                value=score+weights[4]*(match-.6)
                look=0.
                if nxt is not None:
                    successors=index.get((edge["to"],nxt),())
                    work["edge_inspections"]+=len(successors)
                    look=max((affinity(dst,packed(n["src_bits"]))
                              for n in successors),default=0.)
                rank=value+weights[5]*(look-.6)
                following[edge["to"]].append((rank,value,dst))
        states={}
        all_candidates=sum(len(v) for v in following.values())
        for node,rows in following.items():
            rows.sort(key=lambda x:(-x[0],-x[1],x[2]))
            states[node]=(rows[0][1],rows[0][2])
        work["max_active"]=max(work["max_active"],len(states))
        frozen.need(work["max_active"]<=64,"SINGLE_NODE_STATE_GUARD")
        trace.append({"hop":step+1,"candidate_count":all_candidates,
                      "discarded_count":all_candidates-len(states),
                      "kept":tuple((node,*states[node]) for node in sorted(states)),
                      "all_public_candidate_keys":tuple(
                       (node,tuple(sorted((v,score,dst) for _,v,dst in rows)))
                        for node,rows in sorted(following.items()))})
    best=states.get(graph["target"],(-2.*len(graph["roles"]),None))[0]
    result=4.*(best/max(1,len(graph["roles"])-1)-weights[6])
    frozen.need(math.isfinite(result),"FINITE_COMPRESSED_SCORE")
    return result,work,trace

def pack_public(bits):
    """Reporter-only nibble collisions on public encodings; no graph labels."""
    frozen.need(type(bits) is list and len(bits)==16,"PUBLIC_16_BIT_ONLY")
    return tuple(sum(CHECKSUM[i]*bits[4*j+i] for i in range(4))%5
                 for j in range(4))
