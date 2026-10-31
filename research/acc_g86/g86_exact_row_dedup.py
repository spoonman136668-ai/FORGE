import json,time,statistics,hashlib
import numpy as np
from threadpoolctl import threadpool_limits
rng=np.random.default_rng(860)
rows,cols=4096,512
x=rng.normal(size=cols).astype(np.float32)
results=[]
with threadpool_limits(limits=1, user_api='blas'):
 for duplicate_fraction in (0.,.25,.5,.75,.9):
  unique_count=int(rows*(1-duplicate_fraction))
  unique=rng.normal(size=(unique_count,cols)).astype(np.float32)
  indices=np.concatenate([np.arange(unique_count),rng.integers(0,unique_count,rows-unique_count)])
  rng.shuffle(indices)
  dense=np.ascontiguousarray(unique[indices])
  a= dense@x; b=(unique@x)[indices]
  assert np.array_equal(a,b), f'parity fail {duplicate_fraction}'
  for _ in range(5): dense@x; (unique@x)[indices]
  timings={'dense':[], 'dedup':[]}
  for j in range(65):
   for label in (('dense','dedup') if j%2==0 else ('dedup','dense')):
    t=time.perf_counter_ns()
    if label=='dense': dense@x
    else: (unique@x)[indices]
    timings[label].append((time.perf_counter_ns()-t)/1e6)
  d=statistics.median(timings['dense']); c=statistics.median(timings['dedup'])
  results.append(dict(duplicates=duplicate_fraction,unique_rows=unique_count,dense_ms=d,dedup_ms=c,speedup=d/c,weight_memory_ratio=(unique.nbytes+indices.nbytes)/dense.nbytes,parity='EXACT',n=65))
print(json.dumps(results,indent=2))
with open('/mnt/data/g86/results.json','w') as f: json.dump({'scope':'synthetic CPU FP32 exact duplicate-row weight projection, not TinyLlama','method':'repeated output rows represented with unique rows plus index, no dequantization','results':results,'scientific_acceptance':False},f,indent=2)
