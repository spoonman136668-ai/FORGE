import json, time, statistics, numpy as np
rng=np.random.default_rng(8080)
D=64; P=512; S=32; N=12
prefix=rng.standard_normal((P,D)).astype('float32')
suffixes=[rng.standard_normal((S,D)).astype('float32') for _ in range(N)]
wk=rng.standard_normal((D,D)).astype('float32')*.05
wv=rng.standard_normal((D,D)).astype('float32')*.05
wq=rng.standard_normal((D,D)).astype('float32')*.05

def attention(q,k,v):
    s=q@k.T/np.sqrt(D)
    s=s-s.max(axis=-1,keepdims=True)
    ex=np.exp(s)
    return (ex/ex.sum(axis=-1,keepdims=True))@v

def baseline(suf):
    whole=np.concatenate((prefix,suf))
    return attention(suf@wq,whole@wk,whole@wv)

pk=prefix@wk;pv=prefix@wv
def candidate(suf):
    return attention(suf@wq,np.concatenate((pk,suf@wk)),np.concatenate((pv,suf@wv)))

errors=[float(np.max(np.abs(baseline(x)-candidate(x)))) for x in suffixes]
assert max(errors)<1e-4

def run(fn):
    t=time.perf_counter()
    if fn is candidate:
        # Charge cache initialization per request batch, not once per experiment.
        global pk,pv
        pk=prefix@wk; pv=prefix@wv
    for x in suffixes: fn(x)
    return (time.perf_counter()-t)*1000
for _ in range(3): run(baseline);run(candidate)
bs=[];cs=[]
for i in range(13):
    if i%2: cs.append(run(candidate));bs.append(run(baseline))
    else: bs.append(run(baseline));cs.append(run(candidate))
result={'schema':'acc.g80.cpu_prefix_kv_proxy.v1','status':'CPU_PROXY_ONLY','seed':8080,'context_prefix':P,'suffix_tokens':S,'requests':N,'dimensions':D,'rounds':13,'cache_build_cost':'INCLUDED_ONCE_PER_BATCH','max_abs_diff':max(errors),'correctness':'FLOAT32_TOLERANCE_PASS' if max(errors)<1e-4 else 'FAIL','baseline_ms_median':statistics.median(bs),'reuse_ms_median':statistics.median(cs),'speedup':statistics.median(bs)/statistics.median(cs),'note':'Synthetic one-head NumPy attention and repeated shared prefix, not an LLM decode benchmark; no token parity established.','scientific_acceptance':'NOT_GRANTED'}
open('/mnt/data/g80/result.json','w').write(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
