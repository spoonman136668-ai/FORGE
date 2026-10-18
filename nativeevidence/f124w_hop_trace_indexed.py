"""F124-W frozen new-source indexed Wingless and source-blind Ygg hop trace.

This module has *no* labels/route witness. Scientific reference paths are
recovered solely in the downstream evaluator, after the trace is emitted.
All original F124-Q/T/V models remain byte-identical.
"""
from __future__ import annotations
from collections import defaultdict
import json
import math
from pathlib import Path
import types

import f124v_collision_centered as old
import f124q_fresh_source as source
import f124q_independent_binding as q
import f124o_native_learners as original

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124w-frozen-hop-survival-indexed-checksum.json"
FREEZE_BLOB="54489aa0ec10cd487270ff2925dd502f86f5d169"
OLD_MODEL_BLOB="5612093f7c7642388f8946316b4cfe669964c60e"
COHORTS={
 "Wingless":{"FIT":range(980000,980024),"DEV":range(980100,980124)},
 "Yggdrasil":{"FIT":range(990000,990024),"DEV":range(990100,990124)}
}
VECTORS=old.VECTORS
PRIMARY=(1,2,3,4)
ALTERNATE=(1,3,4,2)


def need(ok,code):
    source.need(ok,"F124W_"+code)


def blob(path):
    return source.git_blob(Path(path).read_bytes().replace(b"\r\n",b"\n"))


def frozen():
    old.frozen()
    need(blob(FREEZE)==FREEZE_BLOB,"FROZEN_PROTOCOL_DRIFT")
    p=json.loads(FREEZE.read_text(encoding="utf-8"))
    need(p["schema"]=="forge.research.f124w.frozen-hop-path-survival-and-indexed-compression.v1"
         and p["state"]=="PREIMPLEMENTATION_FROZEN"
         and p["lineage"]["parent_qualified_head"]==
             "163e67995f57e4be9543be4b5451aef1982cfca4"
         and p["lineage"]["source_blob"]==OLD_MODEL_BLOB
         and p["source"]["unique_salted_cohorts"]==
              {lane:{phase:[cohort.start,cohort.stop-1] for phase,cohort in stages.items()}
               for lane,stages in COHORTS.items()}
         and p["Wingless"]["checksum_primary"]==list(PRIMARY)
         and p["Wingless"]["checksum_alternate"]==list(ALTERNATE)
         and p["Yggdrasil"]["memory"]=={"active":7,"retained":9}
         and all(x is False for k,x in p["qualification"].items() if
                 k not in ("fresh_FIT_DEV","original_artifact_sha_authentication",
                           "ubuntu_windows_source_guard","one_Go_full_regression",
                           "negative_results_retained"))
         and blob(old.__file__)==OLD_MODEL_BLOB,
         "PREIMPLEMENTATION_FROZEN_METHOD_IDENTITY")
    return p


def build(lane,seed,vector,phase):
    need(lane in COHORTS and phase in ("FIT","DEV")
         and type(seed) is int and seed in COHORTS[lane][phase]
         and tuple(vector) in VECTORS
         and seed not in old.COHORTS[lane]["FIT"]
         and seed not in old.COHORTS[lane]["DEV"]
         and seed not in source.COHORTS[lane]["FIT"]
         and seed not in source.COHORTS[lane]["DEV"]
         and seed not in source.FORBIDDEN[lane],
         "NEW_NONRESERVED_COHORT_ONLY")
    env=dict(old.build.__globals__)
    env["COHORTS"]=COHORTS
    fn=types.FunctionType(old.build.__code__,env,
                          old.build.__name__,old.build.__defaults__)
    a,b=fn(lane,seed,vector,phase)
    need(source.paired_admit(a,b),"INDEPENDENT_CAUSAL_SOURCE_ADMISSION")
    return a,b


def pairs(lane,phase):
    need(lane in COHORTS and phase in ("FIT","DEV"),"KNOWN_PUBLIC_PHASE")
    return [(seed,tuple(v),*build(lane,seed,v,phase))
            for v in VECTORS for seed in COHORTS[lane][phase]]


def indexed_wingless(graph,base,delta,coeffs=PRIMARY):
    """Only public adjacency, checksum and encoded-edge memoization.

    Original V primary predictions must be bitwise equal. Caches are
    extra inference memory; report peak entries, never call resource-matched.
    """
    source.validate_public(graph)
    need(coeffs in (PRIMARY,ALTERNATE),"ONLY_FROZEN_TWO_CHECKSUMS")
    weights=q.wingless_anchored_weights(list(base),list(delta))
    edges=original.sorted_edges(graph)
    n=len(edges)
    adjacency=defaultdict(list)
    work={"index_build_edge_inspections":n,
          "public_edge_inspections":n,"compressed_bit_reads":0,
          "compressed_affinity_operations":0,
          "lookahead_cache_misses":0,"lookahead_cache_hits":0,
          "max_index_entries":n,"max_encoded_entries":2*n,
          "max_lookahead_cache_entries":0,"max_active":1,
          "evictions":0,"state_limit":3,
          "compression_levels":5,"compression_channels":4}
    for idx,e in enumerate(edges):
        adjacency[(e["from"],e["role"])].append(idx)
    def encode(bits):
        work["compressed_bit_reads"]+=16
        return tuple(weights[j]*
            ((sum(coeffs[k]*bits[4*j+k] for k in range(4))%5)-2)/2
            for j in range(4))
    # One-time immutable public edge encodings. This EXTRA buffer is measured.
    enc=[(encode(e["src_bits"]),encode(e["dst_bits"])) for e in edges]
    def affinity(a,b):
        work["compressed_affinity_operations"]+=4
        return 1.-sum(abs(x-y) for x,y in zip(a,b))/8.
    look_cache={}
    def look(edge_idx,role):
        key=(edge_idx,role)
        if key in look_cache:
            work["lookahead_cache_hits"]+=1
            return look_cache[key]
        work["lookahead_cache_misses"]+=1
        edge=edges[edge_idx]
        possible=adjacency.get((edge["to"],role),())
        work["public_edge_inspections"]+=len(possible)
        result=max((affinity(enc[edge_idx][1],enc[j][0])
                    for j in possible),default=0.)
        look_cache[key]=result
        work["max_lookahead_cache_entries"]=max(
            work["max_lookahead_cache_entries"],len(look_cache))
        return result
    states={graph["start"]:[(0.,None)]}
    for step,role in enumerate(graph["roles"]):
        nxt=graph["roles"][step+1] if step+1<len(graph["roles"]) else None
        following=defaultdict(list)
        for node in sorted(states):
            allowed=adjacency.get((node,role),())
            for score,carried in states[node]:
                work["public_edge_inspections"]+=len(allowed)
                for idx in allowed:
                    e=edges[idx]
                    src,dst=enc[idx]
                    compat=1. if carried is None else affinity(carried,src)
                    value=score+weights[4]*(compat-.6)
                    prospective=0. if nxt is None else look(idx,nxt)
                    priority=value+weights[5]*(prospective-.6)
                    following[e["to"]].append((priority,value,dst))
        states={}
        for node,items in following.items():
            items.sort(key=lambda x:(-x[0],-x[1],x[2]))
            work["evictions"]+=max(0,len(items)-3)
            states[node]=[(val,vec) for _,val,vec in items[:3]]
        work["max_active"]=max(work["max_active"],sum(len(x) for x in states.values()))
        need(work["max_active"]<=192 and
             all(len(x)<=3 for x in states.values()),
             "ORIGINAL_NODE_STATE_CAPACITY")
    scores=[s for s,_ in states.get(graph["target"],[])]
    best=max(scores,default=-2.*len(graph["roles"]))
    result=4.*(best/max(1,len(graph["roles"])-1)-weights[6])
    need(math.isfinite(result),"NONFINITE_CHECKSUM_RESULT")
    return result,work


def ygg_hop_trace(graph,base,delta,mode):
    """Observer-only exact replica of T / V forward, plus per-hop snapshots.

    Neither the ground-truth path nor any paired label is ever available here.
    Fail-closed agreement with original untouched model in evaluation/tests.
    """
    source.validate_public(graph)
    need(mode in ("T_rank_only","V_centered")
         and len(base)==7 and len(delta)==2,"FROZEN_OBSERVER_MODEL")
    edges=original.sorted_edges(graph)
    active=[(graph["start"],None,0.)]
    retained=[]
    depth=len(graph["roles"])
    work={"public_edge_scans":0,"raw_bit_ops":0,"max_active":1,
          "max_retained":0,"evictions":0,"prospective_key_comparisons":0,
          "centered_arithmetic":0,"active_cell_limit":7,"retained_cell_limit":9}
    trace=[]
    def comp(left,right):
        if left is None:return 1.
        work["raw_bit_ops"]+=16
        return sum(base[j]*sum(int(a==b) for a,b in zip(
            left[j*4:j*4+4],right[j*4:j*4+4]))/4.
            for j in range(4))/4.
    for step,role in enumerate(graph["roles"]):
        nextrole=graph["roles"][step+1] if step+1<depth else None
        pre=[]
        for node,carried,score in active+retained:
            work["public_edge_scans"]+=len(edges)
            for edge in edges:
                if edge["from"]!=node or edge["role"]!=role:continue
                similarity=comp(carried,edge["src_bits"])
                value=score+base[4]*(similarity-.35)
                competition=base[5]*(similarity-.5)
                if nextrole is None:
                    look=0.
                else:
                    options=[e for e in edges if e["from"]==edge["to"]
                             and e["role"]==nextrole]
                    work["public_edge_scans"]+=len(edges)
                    look=max((comp(tuple(edge["dst_bits"]),item["src_bits"])
                              for item in options),default=0.)
                    work["prospective_key_comparisons"]+=len(options)
                pre.append((value,competition,look,edge["to"],tuple(edge["dst_bits"])))
        mean=(sum(row[2] for row in pre)/len(pre) if pre else 0.) if mode=="V_centered" else None
        candidates=[]
        increments=[]
        for value,competition,look,node,key in pre:
            if mode=="V_centered":
                raw=.15*(delta[0]+delta[1])*(look-mean)/depth
                inc=max(-.1,min(.1,raw))
                work["centered_arithmetic"]+=4
            else:
                inc=0.
            increments.append(inc)
            new_value=value+inc
            cell=(node,key,new_value)
            candidates.append((new_value+competition+delta[0]*(look-.5),
                               new_value-competition+delta[1]*(look-.5),cell))
        candidates.sort(key=lambda x:(-x[0],-x[1],x[2][0],x[2][1]))
        active=[x[2] for x in candidates[:7]]
        selected={id(x) for x in candidates[:7]}
        extras=[x for x in candidates if id(x) not in selected]
        extras.sort(key=lambda x:(-x[1],-x[0],x[2][0],x[2][1]))
        retained=[x[2] for x in extras[:9]]
        work["evictions"]+=max(0,len(candidates)-16)
        work["max_active"]=max(work["max_active"],len(active))
        work["max_retained"]=max(work["max_retained"],len(retained))
        need(len(active)<=7 and len(retained)<=9 and
             len(active)+len(retained)<=16,"EXACT_7_ACTIVE_9_RETAINED")
        trace.append({
            "hop":step+1,"total_depth":depth,"candidate_count":len(candidates),
            "evictions_at_hop":max(0,len(candidates)-16),
            "mean_public_lookahead":mean,
            "centered_increment_min":min(increments,default=0.),
            "centered_increment_max":max(increments,default=0.),
            "active":[[node,list(key) if key is not None else None,score]
                      for node,key,score in active],
            "retained":[[node,list(key) if key is not None else None,score]
                      for node,key,score in retained],
            "candidate_states":[[row[2][0],list(row[2][1]),row[2][2]]
                                for row in candidates],
            "top_candidate_score":candidates[0][2][2] if candidates else None
        })
    terminals=[score for node,_,score in active+retained if node==graph["target"]]
    best=max(terminals,default=-2.*depth)
    logit=4.*(best/max(1,depth)-base[6])
    need(math.isfinite(logit),"NONFINITE_OBSERVATION")
    return logit,work,trace
