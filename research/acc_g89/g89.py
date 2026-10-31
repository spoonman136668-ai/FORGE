import numpy as np, time, json, statistics
from threadpoolctl import threadpool_limits
rng=np.random.default_rng(89)
results=[]
with threadpool_limits(limits=1):
 for n in (512,2048,8192):
  d=64; q=rng.normal(size=d).astype('float32'); k=rng.normal(size=(n,d)).astype('float32'); v=rng.normal(size=(n,d)).astype('float32')
  def dense():
   logits=k@q/np.sqrt(d); p=np.exp(logits-logits.max()); p/=p.sum();return p@v
  ref=dense()
  for fraction in (.125,.25,.5):
   # Selection uses full scores; thus this tests whether sparse value aggregation
   # is enough to offset selection overhead, NOT QK compute removal.
   top=max(1,int(n*fraction))
   def candidate():
    logits=k@q/np.sqrt(d)
    sel=np.argpartition(logits,-top)[-top:]
    l=logits[sel]; p=np.exp(l-l.max());p/=p.sum();return p@v[sel]
   out=candidate()
   error=float(np.linalg.norm(out-ref)/max(np.linalg.norm(ref),1e-12))
   for fn in (dense,candidate):fn()
   t0=[];t1=[]
   for i in range(31):
    a=time.perf_counter_ns();(dense if i%2==0 else candidate)();b=time.perf_counter_ns();(candidate if i%2==0 else dense)();c=time.perf_counter_ns()
    (t0 if i%2==0 else t1).append((b-a)/1e6);(t1 if i%2==0 else t0).append((c-b)/1e6)
   med0=statistics.median(t0);med1=statistics.median(t1)
   results.append(dict(tokens=n,keep_fraction=fraction,relative_l2_error=error,dense_ms=med0,candidate_ms=med1,speedup=med0/med1))
print(json.dumps(results,indent=2))
open('/mnt/data/g89/results.json','w').write(json.dumps({'method':'exact top-k selected from fully computed attention scores; renormalized approximate attention','samples':31,'results':results},indent=2))
