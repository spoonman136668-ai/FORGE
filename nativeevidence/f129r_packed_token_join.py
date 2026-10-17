"""F129-R exact public packed token join with frozen eligible fast references."""
from collections import defaultdict
import statistics,time,tracemalloc
import f129r_train_environment as env
import f129r_freeze_admission as freeze
import f128r_bit_order_model as old_native

METHODS=("CTRL_NATIVE_INDEXED_16_ELEMENT_VECTOR_EQUALITY",
         "CTRL_PACKED_INTEGER_INDEXED_EQUALITY_WITHOUT_JOIN",
         "CTRL_NATIVE_BYTES_INDEXED_EQUALITY",
         "F129R_PACKED_TOKEN_HASH_JOIN_NO_LEARNING_NO_SELECTION")
def need(ok,key):env.need(bool(ok),"VERIFIER_"+key)
def pack(bits):return sum(int(b)<<i for i,b in enumerate(bits))

def packed_verify(g,method,trace=False):
    env.validate(g)
    need(method in METHODS[1:],"CONTROL_NAME")
    cfg,_=freeze.frozen()
    limits=cfg["hypothesis"]["limits"]
    need(len(g["edges"])<=limits["maximum_edges"] and
         limits["maximum_active_states"]==256 and
         limits["maximum_candidate_expansions"]==512 and
         limits["maximum_public_paths"]==16,"FROZEN_LIMITS")
    counters={k:0 for k in ("edges_indexed","edge_visits","hash_lookup_attempts",
            "bit_pack_operations","token_compares","state_allocations",
            "public_graph_input_conversion")}
    counters["peak_states"]=1
    by_role=defaultdict(list)
    by_token=defaultdict(list)
    join=method==METHODS[3]
    is_packed=method in (METHODS[1],METHODS[3])
    for e in g["edges"]:
        if is_packed:
            src,dst=pack(e["src_bits"]),pack(e["dst_bits"])
            counters["bit_pack_operations"]+=32
            counters["public_graph_input_conversion"]+=2
        else:
            src,dst=bytes(e["src_bits"]),bytes(e["dst_bits"])
            counters["public_graph_input_conversion"]+=2
        by_role[(e["from"],e["role"])].append((e["to"],src,dst))
        if join:by_token[(e["from"],e["role"],src)].append((e["to"],dst))
        counters["edges_indexed"]+=1
    states=[(g["start"],None)]
    expanded=0
    for idx,role in enumerate(g["roles"]):
        new=[]
        for node,last in states:
            counters["hash_lookup_attempts"]+=1
            if join and idx>0:
                candidates=((to,last,dst) for to,dst in
                            by_token.get((node,role,last),()))
            else:
                candidates=iter(by_role.get((node,role),()))
            for to,src,dst in candidates:
                counters["edge_visits"]+=1
                expanded+=1
                need(expanded<=512,"EXPANSION_LIMIT")
                if idx>0:
                    counters["token_compares"]+=1
                    if last!=src:continue
                new.append((to,dst))
                counters["state_allocations"]+=1
        need(len(new)<=256,"STATE_LIMIT")
        states=new
        counters["peak_states"]=max(counters["peak_states"],len(states))
    need(len(states)<=16,"PUBLIC_FINAL_PATHS")
    result=int(any(node==g["target"] for node,last in states))
    return (result,counters) if trace else result

def invoke(g,method,trace=False):
    env.validate(g)
    if method==METHODS[0]:
        if not trace:return old_native.verify(g,mode="native")
        result,w=old_native.verify(g,mode="native",trace=True)
        counters={"edges_indexed":len(g["edges"]),
                  "edge_visits":w["edge_visits"],
                  "hash_lookup_attempts":w["candidate_expansions"],
                  "bit_pack_operations":0,
                  "token_compares":w["bit_mismatch_checks"]//16,
                  "state_allocations":w["state_allocations"],
                  "peak_states":w["peak_states"],
                  "public_graph_input_conversion":0}
        return result,counters
    return packed_verify(g,method,trace)

def compare(rows):
    need(type(rows) is list and len(rows)==64 and
         all(rows[i][1]==1 and rows[i+1][1]==0 for i in range(0,64,2)),
         "SCORE_DENOMINATOR")
    result={}
    for name in METHODS:
        paired=pos=neg=0
        costs={}
        for i in range(0,64,2):
            p,a=invoke(rows[i][0],name,True)
            n,b=invoke(rows[i+1][0],name,True)
            paired+=int(p==1 and n==0)
            pos+=int(p==1)
            neg+=int(n==0)
            for w in (a,b):
                for key,val in w.items():
                    costs[key]=max(costs.get(key,0),val) if key=="peak_states" else costs.get(key,0)+val
        result[name]={"pairs":32,"paired_correct":paired,
                     "positive_correct":pos,"negative_correct":neg,
                     "named_operations":costs}
    need(all(v["paired_correct"]==32 for v in result.values()),
         "EXACTNESS_OR_BASELINE_FAILED")
    return result

def benchmark(rows):
    need(len(rows)==64,"BENCH_DENOMINATOR")
    graphs=[g for g,y in rows]
    funcs={name:(lambda method=name:[invoke(g,method) for g in graphs])
           for name in METHODS}
    for _ in range(5):
        for name in METHODS:
            need(len(funcs[name]())==64,"WARM_DENOMINATOR")
    sample={name:[] for name in METHODS}
    for cycle in range(30):
        order=METHODS if cycle%2==0 else tuple(reversed(METHODS))
        for name in order:
            t=time.perf_counter_ns()
            observations=funcs[name]()
            sample[name].append(time.perf_counter_ns()-t)
            need(len(observations)==64,"MEASURED_DENOMINATOR")
    memory={}
    for name in METHODS:
        tracemalloc.start()
        try:
            tracemalloc.reset_peak()
            observations=funcs[name]()
            current,peak=tracemalloc.get_traced_memory()
            need(len(observations)==64,"TRACED_DENOMINATOR")
            memory[name]={"traced_peak":peak,"traced_end":current}
        finally:tracemalloc.stop()
    stats={}
    for name in METHODS:
        vals=sorted(sample[name])
        stats[name]={"median_ns":statistics.median(vals),
                     "p95_ns":vals[28],
                     "traced_peak_bytes":memory[name]["traced_peak"],
                     "traced_end_bytes":memory[name]["traced_end"]}
    native=stats[METHODS[0]]
    candidate=stats[METHODS[3]]
    time_ratio=candidate["median_ns"]/max(1,native["median_ns"])
    mem_ratio=candidate["traced_peak_bytes"]/max(1,native["traced_peak_bytes"])
    return {"warmup_passes":5,"measured_interleaved_passes":30,
            "graphs_per_pass":64,"alternating_order":True,
            "index_and_input_packing_timed":True,
            "all_native_comparators_eligible":True,
            "benchmarks":stats,
            "packed_to_native_median_walltime_ratio":round(time_ratio,8),
            "packed_to_native_traced_peak_ratio":round(mem_ratio,8),
            "passes_frozen_runtime_target":time_ratio<=.75,
            "passes_frozen_memory_target":mem_ratio<=1.25,
            "traced_peak_is_not_RSS":True,"no_validation_retuning":True}
