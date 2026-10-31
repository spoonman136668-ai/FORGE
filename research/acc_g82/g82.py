import numpy as np, time, json, statistics, os
from threadpoolctl import threadpool_limits
rng=np.random.default_rng(82)
# Exact zero-block skipping, without gathering operands: fixed-block dot products.
# Candidate only skips entirely zero input tiles; dense reference uses optimized GEMV.
D=2048; H=2048; B=128
W=rng.standard_normal((H,D),dtype=np.float32)
results=[]
with threadpool_limits(limits=1):
 for sparsity in (0.0,0.25,0.5,0.75,0.9):
  x=rng.standard_normal(D,dtype=np.float32)
  nzero=int((D//B)*sparsity)
  x[:nzero*B]=0
  active=[j for j in range(0,D,B) if np.any(x[j:j+B])]
  def dense(): return W@x
  def sparse():
   out=np.zeros(H,dtype=np.float32)
   for j in active: out += W[:,j:j+B]@x[j:j+B]
   return out
  a=dense(); b=sparse(); diff=float(np.max(np.abs(a-b)))
  def bench(fn):
   for _ in range(10): fn()
   ts=[]
   for _ in range(51):
    t=time.perf_counter_ns();fn();ts.append((time.perf_counter_ns()-t)/1e6)
   return statistics.median(ts)
  d=bench(dense);s=bench(sparse)
  results.append(dict(zero_fraction=sparsity,active_blocks=len(active),dense_ms=d,candidate_ms=s,speedup=d/s,max_abs_error=diff,allclose=bool(np.allclose(a,b,rtol=1e-4,atol=1e-4))))
print(json.dumps(results,indent=2))
with open('/mnt/data/g82/results.json','w') as f:json.dump({'method':'zero-block skip without gathering; fixed Python block loop','seed':82,'threads':1,'shape':[H,D],'block':B,'repetitions':51,'results':results,'real_model':False,'gpu':False},f,indent=2)
