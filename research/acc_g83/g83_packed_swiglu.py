import os,time,json,statistics
import numpy as np
rng=np.random.default_rng(8301)
# Dense SwiGLU input projections. No sparsity assumptions. Comparison includes gate, multiplication.
D,H=512,2048
Wg=rng.standard_normal((D,H),dtype=np.float32)*.02
Wu=rng.standard_normal((D,H),dtype=np.float32)*.02
Wp=np.concatenate((Wg,Wu),axis=1)

def sigmoid(x):
    return 1/(1+np.exp(-x))

def baseline(x):
    a=x@Wg;b=x@Wu
    return (a*sigmoid(a))*b

def packed(x):
    z=x@Wp
    a,b=np.split(z,2,axis=-1)
    return (a*sigmoid(a))*b

results=[]
for batch in [1,4,16,64]:
    x=rng.standard_normal((batch,D),dtype=np.float32)
    a=baseline(x);b=packed(x)
    max_abs=float(np.max(np.abs(a-b)))
    assert np.allclose(a,b,rtol=1e-5,atol=1e-5),(batch,max_abs)
    for _ in range(8):baseline(x);packed(x)
    ta=[];tb=[]
    for j in range(45):
        if j%2:
            st=time.perf_counter_ns();packed(x);tb.append((time.perf_counter_ns()-st)/1e6)
            st=time.perf_counter_ns();baseline(x);ta.append((time.perf_counter_ns()-st)/1e6)
        else:
            st=time.perf_counter_ns();baseline(x);ta.append((time.perf_counter_ns()-st)/1e6)
            st=time.perf_counter_ns();packed(x);tb.append((time.perf_counter_ns()-st)/1e6)
    row=dict(batch=batch,baseline_ms=statistics.median(ta),packed_ms=statistics.median(tb),max_abs_error=max_abs)
    row['speedup']=row['baseline_ms']/row['packed_ms']
    results.append(row)
print(json.dumps(dict(method='G83 packed dense SwiGLU input projection',numpy=np.__version__,threads_env={k:os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')},dimensions=[D,H],samples=45,results=results,authentic_llm='NOT_RUN',gpu='NOT_RUN'),indent=2))
