#!/usr/bin/env python3
"""CPU G75 synthetic native-shaped KV compression feasibility only; no GPT-2 inference."""
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import statistics
import sys
import time
import traceback

SEED=751975
LENGTHS=(64,256,512)
LAYERS=12
HEADS=12
HEAD_DIM=64
N_REPS=10
N_WARMUPS=5
PREREG="64db89c76b93581d36dae3cc90800535d866612e"
THRESHOLDS={"max_abs_error":0.05,"max_payload_ratio":0.30,
            "speedup_256_min":1.15,"min_pair_256":0.90,
            "rss_ratio_256_max":1.10,"slowdown_64_512_max":1.20}

def contract():
    assert (SEED,LENGTHS,LAYERS,HEADS,HEAD_DIM,N_REPS,N_WARMUPS)==(
        751975,(64,256,512),12,12,64,10,5)
    assert THRESHOLDS=={"max_abs_error":0.05,"max_payload_ratio":0.30,
                       "speedup_256_min":1.15,"min_pair_256":0.90,
                       "rss_ratio_256_max":1.10,"slowdown_64_512_max":1.20}

def validate(tensors,np):
    if len(tensors)!=LAYERS*2:
        raise ValueError("G75_LAYER_PAIR_COUNT_INVALID")
    for x in tensors:
        if x.dtype!=np.float32 or x.ndim!=4 or x.shape[0]!=1 or x.shape[1]!=HEADS or x.shape[-1]!=HEAD_DIM:
            raise ValueError("G75_NATIVE_SHAPE_DTYPE_INVALID")
        if not np.all(np.isfinite(x)):
            raise ValueError("G75_NONFINITE_ORIGINAL_INPUT")

def seed_inputs(length,np):
    rng=np.random.Generator(np.random.PCG64(SEED+length))
    tensor_shape=(1,HEADS,length,HEAD_DIM)
    return tuple(rng.standard_normal(tensor_shape,dtype=np.float32) for _ in range(LAYERS*2))

def original_digest(tensors):
    h=hashlib.sha256()
    for x in tensors:
        h.update(x.tobytes(order="C"))
    return h.hexdigest()

def deepcopy(tensors,np):
    return tuple(np.copy(x,order="C") for x in tensors)

def readonly(tensors):
    return tuple(tensors)

def codec(tensors,np):
    packed=[]
    for x in tensors:
        maximum=float(np.max(np.abs(x)))
        if not math.isfinite(maximum):raise ValueError("G75_NONFINITE_CODEC_VALUE")
        scale=np.float32(maximum/127.0) if maximum>0 else np.float32(1)
        if not math.isfinite(float(scale)) or scale<=0:
            raise ValueError("G75_INVALID_SCALE")
        q=np.rint(x/scale).clip(-127,127).astype(np.int8)
        packed.append((q,scale))
    return tuple(packed)

def decode(packed,np):
    return tuple((q.astype(np.float32)*scale) for q,scale in packed)

def payload_bytes(packed):
    return sum(q.nbytes+4 for q,scale in packed)

def p95(v):
    return sorted(v)[max(0,math.ceil(0.95*len(v))-1)]

def perform(length,np,proc):
    tensors=seed_inputs(length,np)
    validate(tensors,np)
    frozen_digest=original_digest(tensors)
    expected_bytes=sum(t.nbytes for t in tensors)
    if length not in LENGTHS or len(tensors)!=24:
        raise RuntimeError("G75_SEEDED_INPUT_FAILURE")
    reference=deepcopy(tensors,np)
    if not all(not np.shares_memory(a,b) and np.array_equal(a,b)
               for a,b in zip(tensors,reference)):
        raise RuntimeError("G75_DEEPCOPY_NOT_EXACT")
    alias=readonly(tensors)
    if not all(np.shares_memory(a,b) for a,b in zip(tensors,alias)):
        raise RuntimeError("G75_READONLY_ALIAS_INCORRECT")
    packed=codec(tensors,np)
    recovered=decode(packed,np)
    error=max(float(np.max(np.abs(a-b))) for a,b in zip(tensors,recovered))
    ratio=payload_bytes(packed)/expected_bytes
    changed=sum(int(not np.array_equal(a,b)) for a,b in zip(tensors,recovered))
    if changed==0:raise RuntimeError("G75_FAKE_LOSSLESS_CODEC")
    if error>THRESHOLDS["max_abs_error"]:
        raise RuntimeError("G75_FROZEN_ABSOLUTE_ERROR_EXCEEDED")
    if ratio>THRESHOLDS["max_payload_ratio"]:
        raise RuntimeError("G75_FROZEN_PAYLOAD_BUDGET_EXCEEDED")
    for _ in range(N_WARMUPS):
        deepcopy(tensors,np)
        decode(codec(tensors,np),np)
        readonly(tensors)
    trials=[]
    for rep in range(N_REPS):
        order=("deepcopy","int8_codec","readonly") if rep%2==0 else ("int8_codec","deepcopy","readonly")
        measure={}
        for arm in order:
            cpu0=time.process_time_ns()
            wall0=time.perf_counter_ns()
            if arm=="deepcopy":
                result=deepcopy(tensors,np)
            elif arm=="int8_codec":
                compressed=codec(tensors,np)
                result=decode(compressed,np)
            else:
                result=readonly(tensors)
            wall_ns=time.perf_counter_ns()-wall0
            cpu_ns=time.process_time_ns()-cpu0
            # Read RSS after timed payload; sample, not physical peak.
            rss=int(proc.memory_info().rss)
            if arm=="deepcopy":
                if not all(np.array_equal(a,b) and not np.shares_memory(a,b)
                           for a,b in zip(result,tensors)):
                    raise RuntimeError("G75_DEEPCOPY_PARITY_FAILURE")
            if arm=="readonly":
                if not all(np.shares_memory(a,b) for a,b in zip(result,tensors)):
                    raise RuntimeError("G75_READONLY_REFERENCE_FAILURE")
            if arm=="int8_codec" and not all(np.all(np.isfinite(x)) for x in result):
                raise RuntimeError("G75_BAD_CODEC_NONFINITE")
            measure[arm]={"wall_ns":wall_ns,"cpu_ns":cpu_ns,"sampled_rss_bytes":rss}
        if original_digest(tensors)!=frozen_digest:
            raise RuntimeError("G75_ORIGINAL_TENSOR_MUTATED")
        trials.append({"rep":rep+1,"order":order,"measure":measure})
    if len(trials)!=N_REPS:raise RuntimeError("G75_MISSING_MEASUREMENTS")
    median_copy=statistics.median(x["measure"]["deepcopy"]["wall_ns"] for x in trials)
    median_codec=statistics.median(x["measure"]["int8_codec"]["wall_ns"] for x in trials)
    ratios=[x["measure"]["deepcopy"]["wall_ns"]/
            max(1,x["measure"]["int8_codec"]["wall_ns"]) for x in trials]
    rss_codec=max(t["measure"]["int8_codec"]["sampled_rss_bytes"] for t in trials)
    rss_copy=max(t["measure"]["deepcopy"]["sampled_rss_bytes"] for t in trials)
    return {"length":length,"original_input_sha256":frozen_digest,"input_count":len(tensors),
            "original_float32_payload_bytes":expected_bytes,
            "compressed_logical_payload_bytes":payload_bytes(packed),
            "compressed_logical_payload_ratio":ratio,
            "actual_tensors_changed_by_codec":changed,
            "maximum_abs_reconstruction_error":error,
            "trials":trials,"summary":{"median_deepcopy_ns":median_copy,
              "median_codec_ns":median_codec,"median_codec_speedup_vs_copy":median_copy/max(1,median_codec),
              "minimum_paired_speedup":min(ratios),
              "codec_over_copy_sampled_rss_ratio":rss_codec/max(1,rss_copy),
              "p95_deepcopy_ns":p95([t["measure"]["deepcopy"]["wall_ns"] for t in trials]),
              "p95_codec_ns":p95([t["measure"]["int8_codec"]["wall_ns"] for t in trials])}}

def main():
    import numpy as np
    import psutil
    contract()
    receipt={"schema":"forge.cpu-llm-evaluation.g75.codec-sourcefree.v1",
      "gate":"CPU_G75","preregistration_commit":PREREG,
      "source_sha":os.getenv("GITHUB_SHA","UNSET"),
      "np_version":np.__version__,"python_version":sys.version,
      "platform":platform.platform(),"OMP_NUM_THREADS":os.getenv("OMP_NUM_THREADS"),
      "OPENBLAS_NUM_THREADS":os.getenv("OPENBLAS_NUM_THREADS"),
      "synthetic_native_shaped_only":True,"original_pretrained_model_executed":False,
      "original_model_acceptance":"NOT_EVALUATED","scientific_acceptance":"NOT_GRANTED",
      "promotion_allowed":False,"correctness":"UNVERIFIED","engineering":"UNVERIFIED",
      "feasibility":"UNVERIFIED","report_limitations":[
        "Synthetic native-shaped arrays only, no real pretrained KV or logits",
        "Input is a distributional pilot, not an original-model score or validation corpus",
        "Codec deliberately lossy, decoded token correctness NOT measured",
        "Logical codec bytes are not resident physical peak; process RSS sampled only",
        "No GPU inference, GPU ACC G75 unaffected, and no model production promotion"]}
    try:
        if np.__version__!="2.1.3":
            raise RuntimeError("G75_NUMPY_VERSION_MISMATCH")
        proc=psutil.Process()
        t0=time.perf_counter()
        rows=[perform(length,np,proc) for length in LENGTHS]
        receipt["experiment_wall_s"]=time.perf_counter()-t0
        receipt["measurements"]=rows
        receipt["correctness"]="PASS_SHAPE_MEMORY_CONTROLS_ONLY"
        receipt["engineering"]="PASS"
        mid=rows[1]
        stable=(mid["summary"]["median_codec_speedup_vs_copy"]>=THRESHOLDS["speedup_256_min"]
          and mid["summary"]["minimum_paired_speedup"]>=THRESHOLDS["min_pair_256"]
          and mid["summary"]["codec_over_copy_sampled_rss_ratio"]<=THRESHOLDS["rss_ratio_256_max"])
        edge=all(1/row["summary"]["median_codec_speedup_vs_copy"]<=THRESHOLDS["slowdown_64_512_max"]
                 for row in (rows[0],rows[2]))
        receipt["feasibility"]="FEASIBILITY_GO_FOR_SEPARATE_ORIGINAL_PREREG" if stable and edge else "NO_GO_FEASIBILITY"
    except BaseException as exc:
        receipt["error"]=type(exc).__name__+": "+str(exc)
        receipt["traceback_tail"]=traceback.format_exc()[-2500:]
        raise
    finally:
        Path("cpu_g75_sourcefree_result.json").write_text(json.dumps(receipt,sort_keys=True,indent=2,default=str)+"\n",encoding="utf-8")
        print(json.dumps({"gate":receipt["gate"],"engineering":receipt["engineering"],
         "feasibility":receipt["feasibility"],"error":receipt.get("error"),
         "summary":[{"length":x["length"],
                     "speedup_vs_copy":x["summary"]["median_codec_speedup_vs_copy"],
                     "payload_ratio":x["compressed_logical_payload_ratio"],
                     "max_abs_error":x["maximum_abs_reconstruction_error"]}
                    for x in receipt.get("measurements",[])]},sort_keys=True),flush=True)

if __name__=="__main__":main()
