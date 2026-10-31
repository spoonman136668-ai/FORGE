"""G85 controlled CPU proxy: int8 weights dequantized by contiguous row blocks.
Not representative of a fused GPU kernel or a language model. No acceptance authority.
"""
import json, os, time, statistics
import numpy as np
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
rng=np.random.default_rng(85)
D=1024; O=4096; R=128
x=rng.standard_normal(D).astype(np.float32)
w=rng.standard_normal((O,D)).astype(np.float32)*0.05
scale=np.maximum(np.max(np.abs(w),axis=1,keepdims=True)/127.0,1e-9)
q=np.rint(w/scale).clip(-127,127).astype(np.int8)
scale=scale.astype(np.float32)
def dense():return w @ x
def quant():
 out=np.empty(O,dtype=np.float32)
 for j in range(0,O,R):
  out[j:j+R]=(q[j:j+R].astype(np.float32)*scale[j:j+R])@x
 return out
ref=dense(); val=quant(); rel=float(np.linalg.norm(val-ref)/np.linalg.norm(ref)); maxerr=float(np.max(np.abs(val-ref)))
# warmup, alternating pairs
for _ in range(8):dense();quant()
measure={'dense':[],'quant':[]}
for i in range(31):
 for key,fn in ((('dense',dense),('quant',quant)) if i%2==0 else (('quant',quant),('dense',dense))):
  t=time.perf_counter_ns();fn();measure[key].append((time.perf_counter_ns()-t)/1e6)
med={k:statistics.median(v) for k,v in measure.items()}
result={'method':'G85 int8 rowwise per-channel quantization + CPU dequant-by-block','environment':'NumPy CPU synthetic single-vector GEMV','dimensions':[O,D],'block_rows':R,'samples':31,'dense_median_ms':med['dense'],'candidate_median_ms':med['quant'],'speedup':med['dense']/med['quant'],'relative_l2_error':rel,'max_abs_error':maxerr,'weight_bytes_dense':int(w.nbytes),'weight_bytes_quantized_plus_scales':int(q.nbytes+scale.nbytes),'exact_output_parity':bool(np.array_equal(ref,val)),'real_model':'UNVERIFIED','gpu':'NOT_RUN','scientific_acceptance':'NOT_GRANTED'}
print(json.dumps(result,indent=2));open('/mnt/data/g85/results.json','w').write(json.dumps(result,indent=2)+'\n')
