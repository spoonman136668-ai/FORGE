import os,json,time,statistics
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
rng=np.random.default_rng(8701)
d=1024;o=2048
W=rng.standard_normal((d,o),dtype=np.float32)*0.02
gamma=(1+rng.standard_normal(d,dtype=np.float32)*0.05).astype(np.float32)
Wfold=(gamma[:,None]*W).copy()
eps=1e-6

def baseline(x):
    return ((x*np.reciprocal(np.sqrt(np.mean(x*x,axis=-1,keepdims=True)+eps)))*gamma)@W

def folded(x):
    return (x@Wfold)*np.reciprocal(np.sqrt(np.mean(x*x,axis=-1,keepdims=True)+eps))

rows=[]
for batch in [1,4,16,64]:
    x=rng.standard_normal((batch,d),dtype=np.float32)
    a=baseline(x);b=folded(x)
    absmax=float(np.max(np.abs(a-b)));rel=float(np.max(np.abs(a-b)/(np.maximum(np.abs(a),1e-3))))
    for _ in range(12): baseline(x);folded(x)
    samples={'baseline':[],'folded':[]}
    for j in range(60):
        for name,fn in ([('baseline',baseline),('folded',folded)] if j%2==0 else [('folded',folded),('baseline',baseline)]):
            t=time.perf_counter_ns();fn(x);samples[name].append((time.perf_counter_ns()-t)/1e6)
    base=statistics.median(samples['baseline']);new=statistics.median(samples['folded'])
    rows.append({'batch':batch,'baseline_ms':base,'folded_ms':new,'speedup':base/new,'max_abs_error':absmax,'max_relative_error_floor_1e-3':rel,'allclose_rtol_1e-4_atol_1e-5':bool(np.allclose(a,b,rtol=1e-4,atol=1e-5))})
result={'gate':'G87','method':'Fold RMSNorm channel gain into adjacent dense weight','kind':'synthetic CPU mathematical screen','dtype':'float32','matrix_shape':[d,o], 'rounds':60, 'measurements':rows, 'weight_setup_charged':False,'model_token_parity':'UNVERIFIED','gpu':'NOT_RUN','scientific_acceptance':'NOT_GRANTED'}
print(json.dumps(result,indent=2))
with open('/mnt/data/g87/results.json','w') as f:json.dump(result,f,indent=2)
