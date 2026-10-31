import numpy as np, time, json, statistics
from threadpoolctl import threadpool_limits

def dense_argmax(w, h):
    return int(np.argmax(w @ h))

def streamed_argmax(w, h, block=1024):
    best=-np.inf; best_index=0
    for i in range(0,len(w),block):
        scores=w[i:i+block]@h
        j=int(np.argmax(scores)); val=float(scores[j])
        if val>best: best=val; best_index=i+j
    return best_index

def benchmark(n,d,seed):
    rng=np.random.default_rng(seed)
    w=rng.standard_normal((n,d),dtype=np.float32)
    h=rng.standard_normal(d,dtype=np.float32)
    with threadpool_limits(limits=1):
        assert dense_argmax(w,h)==streamed_argmax(w,h)
        for fn in (dense_argmax,streamed_argmax):
            for _ in range(5):fn(w,h)
        arr={}
        for name,fn in [('dense',dense_argmax),('streamed',streamed_argmax)]:
            durations=[]
            for _ in range(35):
                t=time.perf_counter_ns(); fn(w,h);durations.append((time.perf_counter_ns()-t)/1e6)
            arr[name]=statistics.median(durations)
    return dict(n=n,d=d,seed=seed,**arr,speedup=arr['dense']/arr['streamed'])

def test():
    rng=np.random.default_rng(1)
    for n,d in [(1,1),(31,4),(1024,32),(4096,128)]:
        w=rng.standard_normal((n,d),dtype=np.float32);h=rng.standard_normal(d,dtype=np.float32)
        assert dense_argmax(w,h)==streamed_argmax(w,h,block=17)
    w=np.zeros((40,4),dtype=np.float32);h=np.ones(4,dtype=np.float32)
    assert dense_argmax(w,h)==streamed_argmax(w,h,7)==0
    w[39]=10
    assert dense_argmax(w,h)==streamed_argmax(w,h,7)==39
    print('CORRECTNESS: 6/6 PASS')

if __name__=='__main__':
    test()
    data=[benchmark(4096,256,1),benchmark(16384,256,2),benchmark(32768,512,3)]
    print(json.dumps(data,indent=2))
    with open('/mnt/data/g79/result.json','w') as f:json.dump({'status':'CPU_PROXY_ONLY','results':data,'tests':'6/6 PASS','model':'synthetic random projection, not LLM'},f,indent=2)
