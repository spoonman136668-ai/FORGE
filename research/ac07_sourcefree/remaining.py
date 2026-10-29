"""AC-07: nine bounded synthetic engineering probes for the 15 AC-06 omissions.

No private source, physical analog/NUMA control, GPU, scientifically sealed
outcomes, autonomous controllers or original first-use. Python >= 3.11 stdlib.
The goal is evidence of *limits* and restricted functions, not AI superiority.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json
import marshal
import os
from pathlib import Path
import random
import tempfile
import time
import tracemalloc
import zlib

SCHEMA="forge.ac07.remaining-originals.sourcefree.v1"
SEEDS=(701,709,719)
PREVIOUSLY_EXERCISED=set("U07 U08 U10 U18 U19 U20 U21 U22 U23 U24 U26 U27 U28 U29 U30".split())
MISSING=set("U01 U02 U03 U04 U05 U06 U09 U11 U12 U13 U14 U15 U16 U17 U25".split())
PHYSICAL_ONLY={"U03","U06"}

def checksum(data):
    return hashlib.sha256(data).hexdigest()

def compression(seed):
    rng=random.Random(seed)
    structured=(b"causal-rule|x|y|"*512)
    noise=rng.randbytes(len(structured))
    cases={}
    for kind,source in (("repetitive",structured),("random",noise)):
        t_encode=time.perf_counter_ns()
        compressed=zlib.compress(source,level=6)
        encode_ns=time.perf_counter_ns()-t_encode
        t0=time.perf_counter_ns()
        decoded=zlib.decompress(compressed)
        decode_ns=time.perf_counter_ns()-t0
        t1=time.perf_counter_ns()
        direct=source  # zero-copy reference: NOT a measured memory-copy baseline
        direct_ns=time.perf_counter_ns()-t1
        cases[kind]={
            "source_bytes":len(source),
            "compressed_bytes":len(compressed),
            "codebook_metadata_counted":True,
            "lossless":checksum(decoded)==checksum(source)==checksum(direct),
            "decode_wall_ns":decode_ns,
            "direct_reference_wall_ns":direct_ns,
            "one_time_encode_wall_ns":encode_ns,
            "comparable_model_tensor":False
        }
    # Procedural generation does not encode arbitrary learned parameters.
    n=4096
    structured_values=bytes((i*3+seed)%8 for i in range(n))
    generated=bytes((i*3+seed)%8 for i in range(n))
    arbitrary=rng.randbytes(n)
    return {"ids":["U01","U09","U14","U17"],
        "cases":cases,
        "procedural_structured_reproduced":generated==structured_values,
        "procedural_arbitrary_reproduced":generated==arbitrary,
        "procedural_seed_bytes_assumed":8,
        "arbitrary_source_bytes":n,
        "seed_generates_all_arbitrary_weight_arrays":False,
        "model_accuracy_tested":False,
        "negative":"Unstructured data compressed poorly; one-time compression and decode cost are recorded. No fair decode-vs-copy benchmark is claimed."}

def compiled_constants(seed):
    rng=random.Random(seed)
    n=100
    values=[rng.randrange(1000) for _ in range(n)]
    literal="def f():\n return "+ "+".join(map(str,values))
    small="def f():\n return "+ "+".join(map(str,values[:8]))
    code=compile(literal,"<restricted-constant>","exec")
    code_small=compile(small,"<restricted-constant>","exec")
    env={}
    exec(code,{"__builtins__":{}},env)
    result=env["f"]()
    serialized=marshal.dumps(code)
    return {"ids":["U16"],"literal_count":n,
        "small_code_bytes":len(marshal.dumps(code_small)),
        "large_code_bytes":len(serialized),
        "source_text_bytes":len(literal.encode()),
        "correct_sum":result==sum(values),
        "machine_instructions_measured":False,
        "negative":"Python bytecode/constants retain storage; code compilation cannot bypass I-cache capacity."}

def speculative(seed):
    rng=random.Random(seed)
    # FIT bigram counts; independent heldout sequence contains unseen switches.
    fit=[rng.randrange(4) for _ in range(400)]
    transitions={}
    for a,b in zip(fit,fit[1:]):
        transitions.setdefault(a,Counter())[b]+=1
    preferred={a:count.most_common(1)[0][0] for a,count in transitions.items()}
    target=[rng.randrange(4) for _ in range(128)]
    accepted=0
    target_checks=0
    draft_checks=0
    # Draft is never accepted without target comparison. No target computation skipped.
    for a,b in zip(target,target[1:]):
        guess=preferred.get(a,-1)
        draft_checks+=1
        target_checks+=1
        accepted+=guess==b
    return {"ids":["U02"],"fit_tokens":len(fit),"heldout_targets":len(target)-1,
        "draft_accepted":accepted,"draft_mismatch":len(target)-1-accepted,
        "target_verifications":target_checks,"draft_operations":draft_checks,
        "unguarded_mismatch_error":len(target)-1-accepted,
        "claimed_target_work_reduction":False,
        "negative":"Verification still checks every target step; no verified throughput win or realistic LLM decoding."}

def exact_cache(seed):
    rng=random.Random(seed)
    def process(key):
        return hashlib.sha256(("small-rule:"+key).encode()).hexdigest()
    repeated=[f"state-{i%13}" for i in range(80)]
    novel=[f"novel-{seed}-{i}" for i in range(30)]
    requests=repeated+novel
    cache={}
    hits=0
    computed=0
    actual=[]
    for k in requests:
        if k in cache:
            hits+=1
        else:
            cache[k]=process(k)
            computed+=1
        actual.append(cache[k])
    reference=[process(k) for k in requests]
    alias="state-0 "
    return {"ids":["U05"],"requests":len(requests),"cache_hits":hits,
        "computed_misses":computed,
        "exact_parity":actual==reference,
        "perturbed_input_distinct":process(alias)!=process("state-0"),
        "approximate_semantic_hit_authorized":False,
        "retained_record_count":len(cache),
        "negative":"Safe exact caching trades persistent storage for reduced repeated work; not learned semantic reuse."}

def shards(seed):
    rng=random.Random(seed)
    length=80
    gradients=[[rng.randint(-10,10) for _ in range(length)] for _ in range(4)]
    summed=[sum(row[i] for row in gradients) for i in range(length)]
    aggregate=[0]*length
    for row in gradients:
        for i,v in enumerate(row):
            aggregate[i]+=v
    # For one central gather and rebroadcast of aggregated float32 vectors.
    bytes_gather=(len(gradients)-1)*length*4
    bytes_broadcast=(len(gradients)-1)*length*4
    return {"ids":["U04"],"shard_count":len(gradients),
        "gradient_width":length,"aggregation_parity":aggregate==summed,
        "minimum_topology_bytes_including_return":bytes_gather+bytes_broadcast,
        "real_network_tested":False,"trained_lora_adapter":False,
        "negative":"Exact sharded reduction has communication cost; no Wi-Fi or distributed learning speedup shown."}

def arithmetic(seed):
    rng=random.Random(seed)
    inputs=[rng.randint(-256,256) for _ in range(1000)]
    ternary=[rng.choice((-1,0,1)) for _ in inputs]
    t0=time.perf_counter_ns()
    mul=sum(w*x for w,x in zip(ternary,inputs))
    mul_ns=time.perf_counter_ns()-t0
    t1=time.perf_counter_ns()
    add=sum((x if w==1 else -x if w==-1 else 0) for w,x in zip(ternary,inputs))
    add_ns=time.perf_counter_ns()-t1
    t2=time.perf_counter_ns()
    separate=[2*x for x in inputs]
    separate=[x+3 for x in separate]
    separate_ns=time.perf_counter_ns()-t2
    t3=time.perf_counter_ns()
    fused=[2*x+3 for x in inputs]
    fused_ns=time.perf_counter_ns()-t3
    return {"ids":["U11","U15"],"elements":len(inputs),
        "ternary_dot_parity":mul==add,"arithmetic_mul_wall_ns":mul_ns,
        "ternary_branch_wall_ns":add_ns,
        "operator_fusion_parity":separate==fused,
        "unfused_python_wall_ns":separate_ns,
        "fused_python_wall_ns":fused_ns,
        "native_kernel_measured":False,
        "negative":"Python overhead is not GPU/AVX kernel performance; no weight-quantization accuracy tested."}

def out_of_core(seed):
    rng=random.Random(seed)
    payload=rng.randbytes(192*1024)
    with tempfile.TemporaryDirectory(prefix="ac07-sourcefree-") as tmp:
        path=Path(tmp)/"payload.bin"
        path.write_bytes(payload)
        t0=time.perf_counter_ns()
        direct=path.read_bytes()
        whole_ns=time.perf_counter_ns()-t0
        t1=time.perf_counter_ns()
        chunks=[]
        with path.open("rb") as f:
            while True:
                data=f.read(8192)
                if not data:
                    break
                chunks.append(data)
        streaming_ns=time.perf_counter_ns()-t1
        parsed=b"".join(chunks)
    return {"ids":["U12"],"file_bytes":len(payload),
        "stream_chunk_bytes":8192,"chunk_count":len(chunks),
        "source_bytes_equal":parsed==direct==payload,
        "whole_read_wall_ns":whole_ns,"stream_read_wall_ns":streaming_ns,
        "os_page_cache_controlled":False,"measured_physical_disk_bandwidth":False,
        "negative":"OS cache and file-system page policy are not controlled; no SSD-prefetch efficiency claim."}

def sketch_search(seed):
    rng=random.Random(seed)
    rows=[f"k{rng.randrange(650)}" for _ in range(1800)]
    exact=Counter(rows)
    n=53
    sketches=[[0]*n for _ in range(4)]
    def hashes(key):
        return [int.from_bytes(hashlib.blake2b((str(i)+":"+key).encode(),
                       digest_size=4).digest(),"big")%n for i in range(4)]
    for key in rows:
        for i,h in enumerate(hashes(key)):
            sketches[i][h]+=1
    estimates={key:min(sketches[i][h] for i,h in enumerate(hashes(key)))
               for key in exact}
    overcounts=sum(estimates[k]>v for k,v in exact.items())
    # Bounded search budget records a negative for target outside grammar.
    grammar=[lambda x,m=m:x+m for m in range(12)]
    fit=[(0,20),(1,21),(2,22)]
    checks=0; matched=False
    for rule in grammar:
        checks+=1
        if all(rule(x)==y for x,y in fit):
            matched=True;break
    present=[(x,4+x) for x in range(3)]
    checks_yes=0; solved=False
    for rule in grammar:
        checks_yes+=1
        if all(rule(x)==y for x,y in present):
            solved=True;break
    return {"ids":["U13","U25"],"observation_count":len(rows),
        "distinct_keys":len(exact),"sketch_slots":4*n,
        "sketch_overcount_key_count":overcounts,
        "sketch_underestimate_key_count":sum(estimates[k]<v for k,v in exact.items()),
        "full_exact_retained_key_count":len(exact),
        "bounded_search_budget":len(grammar),
        "unsolved_target_fit_checks":checks,"unsolved_target_flag":not matched,
        "solved_target_fit_checks":checks_yes,"solved_target_flag":solved,
        "negative":"Fixed sketches collide; finite grammar does not solve rules outside its hypothesis class."}

def physical_substitutes(seed):
    rng=random.Random(seed)
    # U03: software can rearrange allocations, not program memory channels.
    source=list(range(200))
    even=source[::2];odd=source[1::2]
    restored=[x for pair in zip(even,odd) for x in pair]
    # U06: digital arithmetic only, no analog/DRAM arrays involved.
    w=[rng.randint(-4,4) for _ in range(64)]
    x=[rng.randint(-4,4) for _ in range(64)]
    digital=sum(a*b for a,b in zip(w,x))
    return {"ids":["U03","U06"],"kind":"SOFTWARE_SUBSTITUTE_NOT_PHYSICAL_EXPERIMENT",
        "interleave_roundtrip":restored==source,
        "digital_matmul_or_dot_reproducible":digital==sum(w[i]*x[i] for i in range(64)),
        "hbm_bandwidth_measured":False,
        "numa_channel_affinity_configured":False,
        "dram_in_situ_analog_arithmetic_executed":False,
        "physical_claim_tested":False,
        "negative":"A layout permutation and digital dot product do not create HBM or analog DRAM."}

CASES={
 "compression_procedural":compression,
 "compiled_constants":compiled_constants,
 "verified_speculation":speculative,
 "exact_cache":exact_cache,
 "gradient_shards":shards,
 "ternary_fusion":arithmetic,
 "out_of_core":out_of_core,
 "sketch_bounded_search":sketch_search,
 "hardware_substitutes":physical_substitutes
}
def run():
    results=[]
    for seed in SEEDS:
        for name,f in CASES.items():
            tracemalloc.start()
            start=time.perf_counter_ns()
            value=f(seed)
            elapsed=time.perf_counter_ns()-start
            peak=tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            results.append({"seed":seed,"family":name,"claim_ids":value["ids"],
                            "wall_ns":elapsed,"python_traced_peak_bytes":peak,
                            "result":value})
    ids={id for v in results for id in v["claim_ids"]}
    assert len(results)==27 and ids==MISSING
    assert len(PREVIOUSLY_EXERCISED|ids)==30
    assert not (PREVIOUSLY_EXERCISED&ids)
    return {"schema":SCHEMA,"scope":"SYNTHETIC_DEVELOPMENT_ONLY",
        "families":len(CASES),"seeds":list(SEEDS),"observations":results,
        "restricted_new_original_ids":sorted(ids),
        "physical_substitute_not_physical_result":sorted(PHYSICAL_ONLY),
        "combined_ac06_ac07_original_id_coverage":30,
        "relevant_baseline_improvement_proven":False,
        "native_model_or_architecture_changed":False,
        "independent_itd02_consequence_source_verified":False,
        "scientific_first_use":False,"scientific_admission":False,
        "accepted_results_updated":False,"controller_or_queue_modified":False,
        "all_six_new_ac_candidates_retained":True}
if __name__=="__main__":
    print(json.dumps(run(),sort_keys=True,indent=2))
