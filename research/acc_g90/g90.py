import json,time,statistics
import numpy as np
rng=np.random.default_rng(90)
results=[]
for n in (512,2048,8192):
 d=64; q=rng.normal(size=d).astype('float32'); keys=rng.normal(size=(n,d)).astype('float32'); values=rng.normal(size=(n,d)).astype('float32')
 vmax=float(np.linalg.norm(values,axis=1).max())
 def dense():
  scores=keys@q/np.sqrt(d); z=np.exp(scores-scores.max()); p=z/z.sum(); return p@values
 def bounded(eps=0.01):
  scores=keys@q/np.sqrt(d); order=np.argsort(-scores,kind='stable'); x=np.exp(scores-scores.max()); total=x.sum()
  cumulative=np.cumsum(x[order]); omitted=1-cumulative/total
  # Bound for normalized retained output: ||full - kept|| <= 2 vmax * omitted_mass
  k=int(np.searchsorted(omitted<=eps/(2*vmax), True)+1)
  k=min(max(k,1),n)
  selected=order[:k]; weights=x[selected]; out=(weights/weights.sum())@values[selected]
  return out,k,float(max(0,1-cumulative[k-1]/total))
 a=dense(); b,k,tail=bounded(); err=float(np.linalg.norm(a-b)); bound=2*vmax*tail
 def timeit(fn):
  for _ in range(5):fn()
  data=[]
  for _ in range(31):
   t=time.perf_counter_ns();fn();data.append((time.perf_counter_ns()-t)/1e6)
  return statistics.median(data)
 td=timeit(dense); tb=timeit(bounded)
 results.append(dict(tokens=n,retained=k,retained_pct=100*k/n,omitted_mass=tail,actual_l2_error=err,certified_bound=bound,bound_pass=err<=bound+1e-5,epsilon_pass=err<=0.01+1e-5,dense_ms=td,bounded_ms=tb,speedup=td/tb))
print(json.dumps(results,indent=2));open('/mnt/data/g90/results.json','w').write(json.dumps({'schema':'g90.cpu.synthetic.v1','seed':90,'epsilon_l2':0.01,'trials':31,'results':results},indent=2))
