"""F128-R one-pass label-blind learned bit-order, EXACT public relational verifier.

In FIT: count per-coordinate mismatches of source/destination at EVERY
candidate query-role-adjacent public junction; no labels or true path.
In inference: index by (node, role), enumerate all states and short-circuit
bit equality in the frozen learned priority order. Only exact 16-bit
matches pass. Every non-learnt control sees the identical observation.
"""
from __future__ import annotations
from collections import defaultdict
import hashlib
import json
import random
import statistics
import time
import f128r_train_environment as env
import f128r_freeze_admission as freeze

BITS=16
MAX_STATES=256
MAX_EXPANSIONS=512
MAX_PATHS=16
NATURAL=tuple(range(BITS))
REVERSED=tuple(reversed(NATURAL))
def need(ok,code):env.need(bool(ok),"MODEL_"+code)
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def fixed_uniform():
    # A fixed predeclared label-blind shuffled permutation, not a winner
    # selected using CHECK outcomes or original labels.
    order=list(NATURAL)
    random.Random(12820261017).shuffle(order)
    return tuple(order)
UNIFORM=fixed_uniform()
def validate_order(order):
    need(isinstance(order,(tuple,list)) and len(order)==BITS and
         all(type(i) is int for i in order) and set(order)==set(NATURAL),
         "BIT_ORDER")
def public_index(graph):
    env.validate(graph)
    grouped=defaultdict(list)
    for edge in graph["edges"]:
        grouped[(edge["from"],edge["role"])].append(edge)
    return grouped
def fit(graphs):
    protocol,_=freeze.frozen()
    need(protocol["hypothesis"]["trainable_statistics"]==BITS and
         protocol["hypothesis"]["boundaries"]["training_passes"]==1 and
         type(graphs) is list and len(graphs)==64,"FROZEN_FIT_DENOMINATOR")
    histogram=[0]*BITS
    total=0
    for graph in graphs:
        env.validate(graph)
        index=public_index(graph)
        states=[(graph["start"],None)]
        expanded=0
        for role in graph["roles"]:
            new=[]
            for node,last in states:
                for e in index.get((node,role),()):
                    expanded+=1
                    need(expanded<=MAX_EXPANSIONS,"FIT_EXPANSIONS")
                    if last is not None:
                        for bit in NATURAL:
                            histogram[bit]+=int(last[bit]!=e["src_bits"][bit])
                        total+=1
                    # Learning visitation is topology-only; every public
                    # role-compatible candidate stays in the FIT inventory.
                    new.append((e["to"],e["dst_bits"]))
            states=new
            need(len(states)<=MAX_STATES,"FIT_STATES")
    need(total>0,"NO_TRAINABLE_JUNCTIONS")
    order=tuple(sorted(NATURAL,key=lambda i:(-histogram[i],i)))
    validate_order(order)
    return order,{"mismatch_counts":histogram,"training_junctions":total,
        "fit_graphs":len(graphs),"labels_accessed":False,
        "complete_passes":1,"order_sha256":digest(order)}
def verify(graph,order=None,mode="ordered",trace=False):
    env.validate(graph)
    if mode=="ordered":validate_order(order)
    else:need(mode=="native","INVALID_REFERENCE_MODE")
    index=public_index(graph)
    work={"index_builds":1,"edge_visits":0,"candidate_expansions":0,
          "bit_accesses":0,"bit_mismatch_checks":0,"state_allocations":0,
          "peak_states":1,"raw_input_conversion":0,"sort_comparisons":0}
    states=[(graph["start"],None)]
    for role in graph["roles"]:
        nxt=[]
        for node,last in states:
            for e in index.get((node,role),()):
                work["edge_visits"]+=1
                work["candidate_expansions"]+=1
                need(work["candidate_expansions"]<=MAX_EXPANSIONS,
                     "EXPANSION_LIMIT")
                if last is not None:
                    if mode=="native":
                        # Actual native Python 16-element list equality,
                        # not a slow Python for-loop posing as a baseline.
                        work["bit_accesses"]+=BITS
                        work["bit_mismatch_checks"]+=BITS
                        keep=(last==e["src_bits"])
                    else:
                        keep=True
                        for i in order:
                            work["bit_accesses"]+=1
                            work["bit_mismatch_checks"]+=1
                            if last[i]!=e["src_bits"][i]:
                                keep=False
                                break
                    if not keep:continue
                nxt.append((e["to"],e["dst_bits"]))
                work["state_allocations"]+=1
        need(len(nxt)<=MAX_STATES,"STATE_LIMIT")
        states=nxt
        work["peak_states"]=max(work["peak_states"],len(states))
    result=int(any(node==graph["target"] for node,last in states))
    need(len(states)<=MAX_PATHS,"PUBLIC_END_PATH_LIMIT")
    return (result,work) if trace else result
def compare(rows,learned):
    need(type(rows) is list and len(rows)==64 and
         all(rows[i][1]==1 and rows[i+1][1]==0
         for i in range(0,64,2)),"FROZEN_CHECK_ROWS")
    controls={"CTRL_OPTIMIZED_INDEXED_EXACT_VECTOR_EQUALITY":None,
        "CTRL_FIXED_NATURAL_0_TO_15":NATURAL,
        "CTRL_FIXED_REVERSE_15_TO_0":REVERSED,
        "CTRL_LABEL_BLIND_UNIFORM_BIT_ORDER":UNIFORM,
        "F128R_FIT_ONLY_LEARNED_EARLY_REJECT":learned}
    scores={}
    for name,order in controls.items():
        paired=positive=negative=0
        operation={}
        for k in range(0,len(rows),2):
            g,_=rows[k];h,_=rows[k+1]
            a,wa=verify(g,order,mode="native" if order is None else "ordered",trace=True)
            b,wb=verify(h,order,mode="native" if order is None else "ordered",trace=True)
            paired+=int(a==1 and b==0)
            positive+=int(a==1);negative+=int(b==0)
            for work in (wa,wb):
                for key,n in work.items():
                    operation[key]=max(operation.get(key,0),n) if key=="peak_states" else operation.get(key,0)+n
        scores[name]={"pairs":32,"paired_correct":paired,
                "positive_correct":positive,"negative_correct":negative,
                "named_operations":operation}
    need(all(s["paired_correct"]==32 for s in scores.values()),
         "INEXACT_PREDICTION_FAIL_CLOSED")
    native=scores["CTRL_OPTIMIZED_INDEXED_EXACT_VECTOR_EQUALITY"]["named_operations"]
    learned_ops=scores["F128R_FIT_ONLY_LEARNED_EARLY_REJECT"]["named_operations"]
    ratio=learned_ops["bit_accesses"]/max(1,native["bit_accesses"])
    return scores,ratio
def benchmark(graphs,learned):
    need(len(graphs)==64,"SAME_COHORT")
    methods=(("learned",lambda:[verify(g,learned) for g in graphs]),
             ("optimized_exact",lambda:[verify(g,mode="native") for g in graphs]))
    for _ in range(5):
        for label,fn in methods:need(len(fn())==64,"WARM_PASS")
    samples={"learned":[],"optimized_exact":[]}
    for cycle in range(30):
        for label,fn in (methods if cycle%2==0 else tuple(reversed(methods))):
            start=time.perf_counter_ns();output=fn()
            samples[label].append(time.perf_counter_ns()-start)
            need(len(output)==64,"FULL_PASS")
    l=statistics.median(samples["learned"])
    e=statistics.median(samples["optimized_exact"])
    return {"warmup_passes":5,"measured_interleaved_passes":30,
            "alternating_order":True,"learned_median_ns":l,
            "optimized_exact_median_ns":e,
            "learned_p95_ns":sorted(samples["learned"])[28],
            "optimized_exact_p95_ns":sorted(samples["optimized_exact"])[28],
            "median_walltime_ratio":round(l/max(1,e),6),
            "passes_walltime_target":l<=.75*e,
            "source_graphs":64}
