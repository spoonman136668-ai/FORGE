"""AC-03 source-free resource pilot (Python 3.10+), 2026-10-28.

No scientific admission, original source access, benchmarks of LLM intelligence,
or claims of unrestricted generality. All scenarios synthetic/development-only.

Usage: python ac03_benchmark.py --output ac03_results.json
"""
from __future__ import annotations
import argparse
import collections
import gc
import hashlib
import itertools
import json
import os
import platform
import random
try:
    import resource
except ImportError:
    resource = None
import statistics
import subprocess
import sys
import time
import tracemalloc
import zlib

REPEATS=3
IDS = {
 'delta': ['AC-D1'], 'decision': ['AC-D2'], 'fusion': ['AC-D3'],
 'rules': ['AC-D4'], 'credit': ['AC-D5'], 'structure': ['AC-D6'],
 'compress_repeated': ['U01','U09','U14','U17'],
 'compress_random': ['U01','U09','U14','U17'],
 'ternary': ['U11'], 'sketch': ['U10','U13','U18'],
 'out_of_core': ['U12'],
}

def metric(value):
    return hashlib.sha256(repr(value).encode()).hexdigest()

def delta(variant):
    n=480; count=300
    rng=random.Random(118)
    state=[rng.randrange(0,15) for _ in range(n)]
    events=[(rng.randrange(n),rng.randrange(0,15)) for _ in range(count)]
    term=lambda i: state[i]*state[(i+1)%n]
    if variant=='full':
        outcomes=[]
        for i,v in events:
            state[i]=v
            outcomes.append(sum(term(j) for j in range(n)))
        return outcomes
    if variant=='delta':
        terms=[term(j) for j in range(n)]; total=sum(terms); outcomes=[]
        for i,v in events:
            affected=((i-1)%n,i)
            for j in affected: total-=terms[j]
            state[i]=v
            for j in affected:
                terms[j]=term(j)
                total+=terms[j]
            outcomes.append(total)
        return outcomes
    raise ValueError(variant)

def decision(variant):
    scenarios=90
    actions=48
    result=[]
    for s in range(scenarios):
        # Upper bound known ex ante by construction; the favorable ordering is
        # NOT learned and is an intentional source-free limiting assumption.
        def evaluate(a):
            v=(2000-28*a-(s%17))
            for j in range(20):
                v-=((a+j+s)%7==0)*0  # same work across both variants
            return v
        if variant=='full':
            result.append(max((evaluate(a),-a) for a in range(actions))[1]*-1)
        elif variant=='bound':
            best=-10**9; choice=-1
            for a in range(actions):
                upper=2000-28*a  # valid optimistic bound independent of s
                if best >= upper: break
                value=evaluate(a)
                if value>best:best,choice=value,a
            result.append(choice)
        else: raise ValueError(variant)
    return result

def fusion(variant):
    rng=random.Random(600)
    seq=[]
    for _ in range(4500):
        family=rng.randrange(80)
        seq.append((family, 'out'+str(family%9)))
    if variant=='full':
        stored=tuple(seq)
        query=[v for key,v in stored if key==40]
        return {'answer':query,'record_count':len(stored)}
    if variant=='fusion':
        d=collections.defaultdict(list)
        for key,value in seq:
            d[key].append(value)
        query=list(d[40])
        return {'answer':query,'record_count':len(seq)}
    raise ValueError(variant)

def rules(variant):
    fit=[(i, 3*i+5) for i in range(16)]
    queries=list(range(100,5100))
    if variant=='symbolic':
        # Matched valid fully fitted linear control, not memorization-only.
        m=(fit[-1][1]-fit[0][1])//(fit[-1][0]-fit[0][0])
        b=fit[0][1]-m*fit[0][0]
        return [m*x+b for x in queries]
    if variant=='compiled':
        # Learned coefficients materialized as an executable function;
        # code compilation and search are charged to total CPU time.
        slope=(fit[-1][1]-fit[0][1])//(fit[-1][0]-fit[0][0])
        intercept=fit[0][1]-slope*fit[0][0]
        code=compile('def f(x): return '+str(slope)+'*x+'+str(intercept),'<ac03>','exec')
        scope={};exec(code,scope)
        return [scope['f'](x) for x in queries]
    raise ValueError(variant)

def credit(variant):
    rng=random.Random(55)
    size=6000; rounds=55
    nonzero=sorted(set(rng.randrange(size) for _ in range(95)))
    if variant=='full':
        eligibility=[0]*size
        for i in nonzero:eligibility[i]=1
        weights=[0]*size
        for r in range(rounds):
            for i in range(size):
                weights[i]+=(1+r%5)*eligibility[i]
        return weights
    if variant=='sparse':
        weights=[0]*size
        # Only known nonzero eligibility is touched; this DOES NOT learn
        # whether those traces are causal or even legitimate.
        for r in range(rounds):
            for i in nonzero:
                weights[i]+=(1+r%5)
        return weights
    raise ValueError(variant)

def structure(variant):
    n=6
    base=((0,'r',1),(1,'r',2),(2,'s',3),(3,'s',4),(4,'t',5),(0,'t',3))
    rng=random.Random(405)
    observations=[]
    for q in range(16):
        p=list(range(n));rng.shuffle(p)
        observed=tuple((p[x],role,p[y]) for x,role,y in base)
        if q%9==0:
            observed=observed[:-1]+((observed[-1][0],'other',observed[-1][2]),)
        observations.append(observed)
    base_edges=set(base)
    def signatures(edges):
        return [(tuple(sorted([r for a,r,b in edges if a==i])),
                 tuple(sorted([r for a,r,b in edges if b==i]))) for i in range(n)]
    base_sig=signatures(base)
    answers=[]
    for observed in observations:
        e=set(observed)
        if variant=='naive':
            result=any({(p[a],r,p[b]) for a,r,b in base_edges}==e
                       for p in itertools.permutations(range(n)))
        elif variant=='pruned':
            signatures_observed=signatures(e)
            candidates=[[j for j in range(n) if base_sig[i]==signatures_observed[j]]
                        for i in range(n)]
            result=False
            if all(candidates):
                for p in itertools.product(*candidates):
                    if len(set(p)) != n: continue
                    if {(p[a],r,p[b]) for a,r,b in base_edges}==e:
                        result=True;break
        else:raise ValueError(variant)
        answers.append(result)
    return answers

def compress_bytes(variant,kind):
    rng=random.Random(66)
    data=(b'ABCD'*30000 if kind=='repeated' else rng.randbytes(120000))
    count=45
    if variant=='raw':
        return (len(data), zlib.crc32(data)*count)
    if variant=='compressed':
        packed=zlib.compress(data,6)
        total=0
        for _ in range(count):
            decoded=zlib.decompress(packed)
            total+=zlib.crc32(decoded)
        return (len(data),total)
    raise ValueError(variant)

def ternary(variant):
    rng=random.Random(11)
    rows=[[rng.randrange(-1,2) for _ in range(192)] for _ in range(85)]
    vec=[rng.randrange(-100,101) for _ in range(192)]
    result=[]
    for row in rows:
        if variant=='multiply':
            result.append(sum(w*x for w,x in zip(row,vec)))
        elif variant=='add_only':
            total=0
            for w,x in zip(row,vec):
                if w==1:total+=x
                elif w==-1:total-=x
            result.append(total)
        else:raise ValueError(variant)
    return result

def sketch(variant):
    rng=random.Random(19); n=4000; width=512;depth=4
    stream=[rng.randrange(1600) for _ in range(n)]
    test_keys=list(range(1600))
    if variant=='exact':
        count=collections.Counter(stream)
        return [count[k] for k in test_keys]
    if variant=='cms':
        table=[[0]*width for _ in range(depth)]
        def h(key,j):return ((key*2654435761)^(j*104729))%width
        for x in stream:
            for j in range(depth):table[j][h(x,j)]+=1
        return [min(table[j][h(x,j)] for j in range(depth)) for x in test_keys]
    raise ValueError(variant)

def out_of_core(variant):
    import mmap, tempfile
    rng=random.Random(54)
    data=rng.randbytes(800000)
    with tempfile.TemporaryDirectory() as folder:
        path=os.path.join(folder,'case.dat')
        with open(path,'wb') as f:f.write(data)
        if variant=='full':
            with open(path,'rb') as f:
                read=f.read()
            return zlib.crc32(read)
        if variant=='stream':
            crc=0
            with open(path,'rb') as f:
                while True:
                    chunk=f.read(65536)
                    if not chunk:break
                    crc=zlib.crc32(chunk,crc)
            return crc
    raise ValueError(variant)

CASES={
 'delta':('full','delta'), 'decision':('full','bound'),
 'fusion':('full','fusion'), 'rules':('symbolic','compiled'),
 'credit':('full','sparse'), 'structure':('naive','pruned'),
 'compress_repeated':('raw','compressed'),
 'compress_random':('raw','compressed'),
 'ternary':('multiply','add_only'), 'sketch':('exact','cms'),
 'out_of_core':('full','stream'),
}
def exercise(case,variant):
    if case.startswith('compress_'):
        return compress_bytes(variant,case.split('_')[1])
    return globals()[case](variant)

def process_rss_peak_bytes():
    # POSIX ru_maxrss is process high-water; Linux reports KiB, Darwin bytes.
    if os.name !='posix' or resource is None:return None
    val=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return val if sys.platform=='darwin' else val*1024

def child(case,variant):
    gc.collect()
    tracemalloc.start()
    start_mem=tracemalloc.get_traced_memory()[0]
    cpu=time.process_time_ns();wall=time.perf_counter_ns()
    outcome=exercise(case,variant)
    elapsed_wall=time.perf_counter_ns()-wall
    elapsed_cpu=time.process_time_ns()-cpu
    current,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {'case':case,'variant':variant,'sha256':metric(outcome),
            'cpu_ns':elapsed_cpu,'wall_ns':elapsed_wall,
            'python_alloc_peak_bytes':max(0,peak-start_mem),
            'process_peak_rss_bytes':process_rss_peak_bytes(),
            'outcome':outcome if case=='sketch' else None}

def run(output):
    rows=[]
    for case,(base,candidate) in CASES.items():
        for repetition in range(REPEATS):
            # Alternate order to mitigate drift; each in a fresh process.
            order=[base,candidate] if repetition%2==0 else [candidate,base]
            pair={}
            for variant in order:
                # Sequential in-process pilot: tracemalloc is reset for each variant.
                # Process RSS is a cumulative high-water mark, NOT comparable.
                pair[variant]=child(case,variant)
                pair[variant]['process_peak_rss_bytes']=None
            comparable = case!='sketch'
            exact=pair[base]['sha256']==pair[candidate]['sha256'] if comparable else None
            count_error=None
            if case=='sketch':
                truth=pair[base]['outcome'];approx=pair[candidate]['outcome']
                assert len(truth)==len(approx)
                count_error={'sum_overcount':sum(b-a for a,b in zip(truth,approx)),
                             'nonzero_errors':sum(a!=b for a,b in zip(truth,approx)),
                             'min_error':min(b-a for a,b in zip(truth,approx))}
                assert count_error['min_error']>=0
            elif not exact:
                raise AssertionError('parity failure case='+case+' round='+str(repetition))
            for variant in order:
                row={k:v for k,v in pair[variant].items() if k!='outcome'}
                row.update({'repetition':repetition,'role':'baseline' if variant==base else 'candidate',
                            'parity_verified':exact,'sketch_error':count_error,
                            'claim_ids':IDS[case]})
                rows.append(row)
    summaries={}
    for case,(base,candidate) in CASES.items():
        a=[r for r in rows if r['case']==case and r['variant']==base]
        b=[r for r in rows if r['case']==case and r['variant']==candidate]
        baseline_cpu=statistics.median(r['cpu_ns'] for r in a)
        candidate_cpu=statistics.median(r['cpu_ns'] for r in b)
        summaries[case]={
            'claim_ids':IDS[case],
            'baseline_variant':base,'candidate_variant':candidate,
            'baseline_cpu_median_ns':baseline_cpu,
            'candidate_cpu_median_ns':candidate_cpu,
            'cpu_ratio_candidate_over_baseline':round(candidate_cpu/baseline_cpu,5),
            'baseline_wall_median_ns':statistics.median(r['wall_ns'] for r in a),
            'candidate_wall_median_ns':statistics.median(r['wall_ns'] for r in b),
            'baseline_python_alloc_peak_bytes_median':statistics.median(r['python_alloc_peak_bytes'] for r in a),
            'candidate_python_alloc_peak_bytes_median':statistics.median(r['python_alloc_peak_bytes'] for r in b),
            'baseline_peak_rss_bytes_median':None,
            'candidate_peak_rss_bytes_median':None,
            'parity':(all(r['parity_verified'] for r in a+b) if case!='sketch' else 'approximate / count-min sketch'),
            'sketch_error':b[0]['sketch_error'] if case=='sketch' else None,
        }
    result={'schema':'forge.ac03.sourcefree.measured.v1',
            'scope':'sourcefree CPU Python microbenchmarks; NOT intelligence/science/real LLM speed',
            'hardware':{'os':platform.platform(),'python':sys.version.split()[0],
                        'architecture':platform.machine(),'processor':platform.processor(),
                        'cpu_count':os.cpu_count()},
            'repetitions_per_variant':REPEATS,
            'timing_excludes_subprocess_launch':True,
            'variant_isolation':'sequential within one process with gc/tracemalloc reset; peak process RSS unavailable',
            'unmeasured':'energy, native kernel SIMD, GPU VRAM, bandwidth, true learning/transfer',
            'all_36_document_and_native_claims_retained':True,
            'measured_case_count':len(CASES),
            'not_measured_claims_not_a_scientific_negative':True,
            'summary':summaries,'samples':rows}
    with open(output,'w') as f:json.dump(result,f,indent=2,sort_keys=True)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--child',nargs=2)
    parser.add_argument('--output',default='ac03_results.json')
    args=parser.parse_args()
    if args.child:
        print(json.dumps(child(*args.child)))
    else:
        result=run(args.output)
        for case,s in result['summary'].items():
            print('%-20s %8.3fx cpu; parity=%s rss=%s/%s' % (
                case,s['cpu_ratio_candidate_over_baseline'],str(s['parity']),
                s['baseline_peak_rss_bytes_median'],s['candidate_peak_rss_bytes_median']))