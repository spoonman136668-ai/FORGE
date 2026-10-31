"""G88 single-query online-softmax attention CPU proxy, not model inference."""
import json, time, statistics, os
import numpy as np

def dense(q,k,v):
    scores=k@q
    weights=np.exp(scores-np.max(scores))
    return (weights@v)/np.sum(weights)

def stream(q,k,v,block=256):
    m=np.float32(-np.inf); z=np.float32(0); acc=np.zeros(v.shape[1],dtype=np.float32)
    for a in range(0,k.shape[0],block):
        kb=k[a:a+block]; vb=v[a:a+block]
        s=kb@q
        new_m=np.maximum(m,np.max(s))
        factor=np.exp(m-new_m)
        w=np.exp(s-new_m)
        acc=acc*factor+w@vb
        z=z*factor+np.sum(w)
        m=new_m
    return acc/z

def benchmark():
    rng=np.random.default_rng(88)
    result=[]
    for n in (512,2048,8192):
        q=rng.normal(size=64).astype(np.float32)/8
        k=rng.normal(size=(n,64)).astype(np.float32)
        v=rng.normal(size=(n,64)).astype(np.float32)
        expected=dense(q,k,v); actual=stream(q,k,v)
        maxdiff=float(np.max(np.abs(expected-actual)))
        assert np.allclose(expected,actual,atol=2e-6,rtol=2e-5),maxdiff
        for _ in range(5): dense(q,k,v);stream(q,k,v)
        timings={"dense":[],"stream":[]}
        for i in range(31):
            order=('dense','stream') if i%2==0 else ('stream','dense')
            for arm in order:
                start=time.perf_counter_ns()
                (dense if arm=='dense' else stream)(q,k,v)
                timings[arm].append((time.perf_counter_ns()-start)/1e6)
        dm=statistics.median(timings['dense']);sm=statistics.median(timings['stream'])
        result.append(dict(tokens=n,dense_ms=dm,stream_ms=sm,speedup=dm/sm,max_abs_error=maxdiff,
                           dense_attention_scratch_bytes=n*4*2,
                           streamed_attention_scratch_upper_bytes=256*4*2+64*4,
                           correctness='PASS'))
    payload=dict(schema='g88.single_query.online_softmax.cpu_proxy.v1',numpy=np.__version__,
                 threads={k:os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')},
                 samples_per_arm=31,block=256,results=result,model='SYNTHETIC',gpu='NOT_RUN',
                 scientific_acceptance='NOT_GRANTED')
    print(json.dumps(payload,indent=2));return payload
if __name__=='__main__':
    with open('/mnt/data/g88/results.json','w') as f:json.dump(benchmark(),f,indent=2)
