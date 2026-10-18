"""F124-AA source-blind frozen predictors: 1 packed state/node and exact Z head.

Extended validator is scoped to cloned functions. Original models are never
mutated or imported with altered global source, and protected references
remain unavailable at inference.
"""
from __future__ import annotations
from collections import defaultdict
import math,types

import f124aa_frozen_source as experiment
import f124z_sparse_continuity as original_z
import f124q_independent_binding as original_q
import f124o_native_learners as original_o

CHECKSUM=(1,3,4,2)


def ygg_original(graph,base,delta):
    """Run the UNCHANGED historical T bytecode with only 7-12 validator."""
    proxy=types.SimpleNamespace(validate_public=experiment.validate_extended)
    env=dict(original_q.yggdrasil_lookahead.__globals__)
    env["source"]=proxy
    fn=types.FunctionType(original_q.yggdrasil_lookahead.__code__,
                          env,original_q.yggdrasil_lookahead.__name__,
                          original_q.yggdrasil_lookahead.__defaults__)
    return fn(graph,list(base),list(delta))


def ygg_continuity(graph,base,delta):
    """Original frozen Z bytecode, scoped extended graph-shape admission."""
    proxy=types.SimpleNamespace(validate_public=experiment.validate_extended)
    env=dict(original_z.continuity_head.__globals__)
    env["source"]=proxy
    fn=types.FunctionType(original_z.continuity_head.__code__,env,
                          original_z.continuity_head.__name__,
                          original_z.continuity_head.__defaults__)
    raw,ratio,work=fn(graph,list(base),list(delta))
    return original_z.corrected_logit(raw,ratio,.5),ratio,raw,work


def packed_one_state(graph,base,delta):
    """Fundamentally reduced memory: one packed 12-bit 4-channel state/node.

    Unlike Z: one state (not three) per public node. No encoded-edge cache,
    lookahead memo, retained alternatives, or additional graph-copy buffers.
    The checksum is the originally frozen winning W/Y/Z checksum.
    """
    experiment.validate_extended(graph)
    weights=original_q.wingless_anchored_weights(list(base),list(delta))
    edges=original_o.sorted_edges(graph)
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
            code=sum(CHECKSUM[i]*bits[4*j+i] for i in range(4))%5
            result|=code<<(3*j)
        return result
    def affinity(a,b):
        work["affinity_ops"]+=4
        # The original compressed floating scalar is reconstructed ON DEMAND.
        av=[weights[j]*(((a>>(3*j))&7)-2)/2 for j in range(4)]
        bv=[weights[j]*(((b>>(3*j))&7)-2)/2 for j in range(4)]
        return 1.-sum(abs(x-y) for x,y in zip(av,bv))/8.
    states={graph["start"]:(0.,None)}
    for step,role in enumerate(graph["roles"]):
        nxt=graph["roles"][step+1] if step+1<len(graph["roles"]) else None
        following=defaultdict(list)
        for node in sorted(states):
            score,carried=states[node]
            eligible=index.get((node,role),())
            work["edge_inspections"]+=len(eligible)
            for e in eligible:
                src=packed(e["src_bits"])
                dst=packed(e["dst_bits"])
                match=1. if carried is None else affinity(carried,src)
                value=score+weights[4]*(match-.6)
                look=0.
                if nxt is not None:
                    next_edges=index.get((e["to"],nxt),())
                    work["edge_inspections"]+=len(next_edges)
                    look=max((affinity(dst,packed(n["src_bits"]))
                              for n in next_edges),default=0.)
                rank=value+weights[5]*(look-.6)
                following[e["to"]].append((rank,value,dst))
        states={}
        for node,rows in following.items():
            rows.sort(key=lambda x:(-x[0],-x[1],x[2]))
            states[node]=(rows[0][1],rows[0][2])
        work["max_active"]=max(work["max_active"],len(states))
        experiment.need(work["max_active"]<=64,"ONE_STATE_PER_NODE_GLOBAL_BOUND")
    best=states.get(graph["target"],(-2.*len(graph["roles"]),None))[0]
    output=4.*(best/max(1,len(graph["roles"])-1)-weights[6])
    experiment.need(math.isfinite(output),"FINITE_PACKED_STATE")
    return output,work
