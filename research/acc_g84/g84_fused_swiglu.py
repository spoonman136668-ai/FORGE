"""G84 offline CPU proxy: fused elementwise SwiGLU after dense GEMM. Not a GPU benchmark."""
import json, os, time
import numpy as np
import numexpr as ne

rng=np.random.default_rng(84)
results=[]
for batch in (1, 8, 32):
    d,h=512,2048
    x=rng.standard_normal((batch,d),dtype=np.float32)
    wg=rng.standard_normal((d,h),dtype=np.float32)/np.sqrt(d)
    wu=rng.standard_normal((d,h),dtype=np.float32)/np.sqrt(d)
    gate=x@wg; up=x@wu
    def baseline():
        return (gate/(1+np.exp(-gate)))*up
    def fused():
        return ne.evaluate('gate * up / (1 + exp(-gate))',local_dict={'gate':gate,'up':up})
    a=baseline();b=fused()
    err=float(np.max(np.abs(a-b)))
    assert np.allclose(a,b,rtol=2e-6,atol=2e-6)
    trials=101
    tb=[];tf=[]
    for j in range(trials+10):
        first,second=(baseline,fused) if j%2==0 else (fused,baseline)
        s=time.perf_counter_ns();first();m=time.perf_counter_ns();second();e=time.perf_counter_ns()
        if j>=10:
            if j%2==0:tb.append((m-s)/1e6);tf.append((e-m)/1e6)
            else:tf.append((m-s)/1e6);tb.append((e-m)/1e6)
    mb=float(np.median(tb));mf=float(np.median(tf))
    results.append(dict(batch=batch,baseline_ms=mb,fused_ms=mf,speedup=mb/mf,max_abs_error=err,correct=True))
print(json.dumps(results,indent=2))
with open('/mnt/data/g84/results.json','w') as f:json.dump({'method':'NumExpr elementwise expression (precomputed GEMM outputs)','environment':'CPU NumPy NumExpr synthetic FP32','results':results,'gpu_qualification':'UNVERIFIED','end_to_end':'NOT_MEASURED'},f,indent=2)
