#!/usr/bin/env python3
"""ACC-65 U28 exact NTT convolution vs sparse-aware naive Python; no LLM speed claim."""
from __future__ import annotations
import argparse
import hashlib
import json
import random
import statistics
import struct
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
REGISTRY=ROOT/"research/ac07_sourcefree/ac08_portfolio.py"
PREREG=ROOT/"docs/research/ACC-65-U28-PREREG-20261030.md"
REGISTRY_GIT_BLOB="5126c860771fb024ccfc14c3f7ee8925edf29787"
PREREG_COMMIT="7929942f1bfd97b663bd6c8444a07bce1f957cf4"
P=998244353
GENERATOR=3
SIZES=(32,128,512,1024)
REGIMES=("dense","sparse")
SEEDS=(28101,28103,28107)
REPEATS=3

def git_blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def source_check()->dict:
    if not REGISTRY.is_file() or git_blob(REGISTRY.read_bytes().replace(b"\r\n",b"\n"))!=REGISTRY_GIT_BLOB:
        raise RuntimeError("ACC65_U28_ORIGINAL_PORTFOLIO_DRIFT")
    if '"number-theoretic-transform semantics"' not in REGISTRY.read_text(encoding="utf-8"):
        raise RuntimeError("ACC65_U28_ORIGINAL_CLAIM_MISSING")
    if not PREREG.is_file() or "ACC-65 / U28" not in PREREG.read_text(encoding="utf-8"):
        raise RuntimeError("ACC65_U28_PREEXEC_NOT_FROZEN")
    return {"original_claim":"U28","original_registry_blob":REGISTRY_GIT_BLOB,
            "prereg_commit":PREREG_COMMIT,"source_scope":"RESTRICTED_EXACT_PYTHON_CPU_KERNEL_NOT_LANGUAGE_SEMANTICS"}

def transform(values:tuple[int,...],inverse:bool=False)->tuple[int,...]:
    n=len(values)
    if n<2 or n&(n-1) or (P-1)%n:
        raise ValueError("unsupported NTT length")
    a=[v%P for v in values]
    j=0
    for i in range(1,n):
        bit=n>>1
        while j&bit:
            j^=bit
            bit>>=1
        j^=bit
        if i<j:
            a[i],a[j]=a[j],a[i]
    size=2
    while size<=n:
        base=pow(GENERATOR,(P-1)//size,P)
        if inverse:base=pow(base,P-2,P)
        half=size//2
        for start in range(0,n,size):
            w=1
            for j in range(half):
                u=a[start+j]
                v=a[start+j+half]*w%P
                a[start+j]=(u+v)%P
                a[start+j+half]=(u-v)%P
                w=w*base%P
        size*=2
    if inverse:
        scale=pow(n,P-2,P)
        a=[v*scale%P for v in a]
    return tuple(a)

def ntt_convolution(a:tuple[int,...],b:tuple[int,...])->tuple[int,...]:
    if len(a)!=len(b):raise ValueError("convolution shape mismatch")
    fa=transform(a)
    fb=transform(b)
    return transform(tuple(x*y%P for x,y in zip(fa,fb)),inverse=True)

def naive_convolution(a:tuple[int,...],b:tuple[int,...])->tuple[int,...]:
    n=len(a)
    if n!=len(b) or n<2 or n&(n-1) or (P-1)%n:
        raise ValueError("convolution shape mismatch")
    out=[0]*n
    nonzero_a=[(i,x%P) for i,x in enumerate(a) if x%P]
    nonzero_b=[(i,x%P) for i,x in enumerate(b) if x%P]
    for i,x in nonzero_a:
        for j,y in nonzero_b:
            k=(i+j)&(n-1)
            out[k]=(out[k]+x*y)%P
    return tuple(out)

def inputs(n:int,regime:str,seed:int)->tuple[tuple[int,...],tuple[int,...]]:
    if n not in SIZES or regime not in REGIMES or seed not in SEEDS:
        raise ValueError("unfrozen input")
    rng=random.Random(seed+n*100+REGIMES.index(regime)*10000)
    def vector():
        return tuple((rng.randint(-100,100) if regime=="dense" or rng.randrange(10)==0 else 0)%P
                     for _ in range(n))
    return vector(),vector()

def digest(arr:tuple[int,...])->str:
    return hashlib.sha256(b"".join(struct.pack("<I",x%P) for x in arr)).hexdigest()

def shift(seq:tuple[int,...])->tuple[int,...]:
    return (seq[-1],)+seq[:-1]

def position_sensitive(seq:tuple[int,...])->tuple[int,...]:
    return tuple(i*x%P for i,x in enumerate(seq))

def semantic_falsifier()->dict:
    # Circular convolution with a fixed kernel is shift-equivariant; F is not.
    e0=(1,0,0,0,0,0,0,0)
    left=position_sensitive(shift(e0))
    right=shift(position_sensitive(e0))
    return {"domain_n":8,"map":"F_i(x)=i*x_i mod p",
        "input":"one_hot_position_0","left_F_of_shift":list(left),
        "right_shift_of_F":list(right),
        "fixed_convolution_must_shift_commute":True,
        "explicit_not_shift_equivariant":left!=right}

def run()->dict:
    original=source_check()
    witness=semantic_falsifier()
    if not witness["explicit_not_shift_equivariant"]:
        raise RuntimeError("SEMANTIC_SHIFT_COUNTEREXAMPLE_LOST")
    rows=[]
    for n in SIZES:
        for regime in REGIMES:
            for seed in SEEDS:
                a,b=inputs(n,regime,seed)
                expected=naive_convolution(a,b)
                if ntt_convolution(a,b)!=expected:
                    raise RuntimeError("ORIGINAL_EXACT_CONVOLUTION_DIVERGENCE")
                # Real warmup for both, excluded from paired sample timing.
                naive_convolution(a,b);ntt_convolution(a,b)
                for repeat in range(REPEATS):
                    t0=time.perf_counter_ns()
                    slow=naive_convolution(a,b)
                    naive_ns=time.perf_counter_ns()-t0
                    t0=time.perf_counter_ns()
                    candidate=ntt_convolution(a,b)
                    ntt_ns=time.perf_counter_ns()-t0
                    if slow!=candidate or slow!=expected or min(naive_ns,ntt_ns)<=0:
                        raise RuntimeError("INVALID_TIMED_SOURCE_EVIDENCE")
                    rows.append({"n":n,"regime":regime,"seed":seed,"repeat":repeat,
                        "source_a_sha256":digest(a),"source_b_sha256":digest(b),
                        "output_sha256":digest(expected),"naive_output_sha256":digest(slow),
                        "ntt_output_sha256":digest(candidate),"naive_wall_ns":naive_ns,
                        "ntt_wall_ns":ntt_ns,"speedup_naive_over_ntt":naive_ns/ntt_ns,
                        "nnz_a":sum(bool(x) for x in a),"nnz_b":sum(bool(x) for x in b)})
    if len(rows)!=len(SIZES)*len(REGIMES)*len(SEEDS)*REPEATS:
        raise RuntimeError("FROZEN_MATRIX_INCOMPLETE")
    summary=[]
    for n in SIZES:
        for regime in REGIMES:
            subset=[x for x in rows if x["n"]==n and x["regime"]==regime]
            summary.append({"n":n,"regime":regime,
                "naive_median_ns":statistics.median(x["naive_wall_ns"] for x in subset),
                "ntt_median_ns":statistics.median(x["ntt_wall_ns"] for x in subset),
                "paired_speedup_geomean":__import__("math").exp(
                    statistics.mean(__import__("math").log(x["speedup_naive_over_ntt"]) for x in subset)),
                "min_paired_speedup":min(x["speedup_naive_over_ntt"] for x in subset)})
    relevant=[x for x in summary if x["n"]>=512]
    speed=all(x["paired_speedup_geomean"]>=1.15 and x["min_paired_speedup"]>=.85 for x in relevant)
    return {"schema":"forge.acc65.u28.ntt-real-python-kernel.v1",
        "identity":original,
        "protocol":{"p":P,"primitive_root":GENERATOR,"sizes":list(SIZES),"regimes":list(REGIMES),
            "seeds":list(SEEDS),"repeats":REPEATS,"first_use_source_family":"synthetic deterministic only",
            "timing":"Python perf_counter_ns function wall, no process startup or model end-to-end"},
        "semantic_counterexample":witness,"observations":rows,"summary":summary,
        "classification":{
            "exact_cyclic_convolution":"U28_EXACT_CYCLIC_CONVOLUTION_PASS_RESTRICTED",
            "full_matrix_kernel_speed":"U28_RESTRICTED_PYTHON_KERNEL_SPEED_POSITIVE_ONLY" if speed else "U28_NO_GENERAL_VERIFIED_PYTHON_KERNEL_SPEED_WIN",
            "universal_fixed_convolution_semantics":"U28_UNIVERSAL_FIXED_CONVOLUTION_SEMANTICS_NO_GO",
            "pretrained_model_acceleration":"UNVERIFIED",
            "trained_semantic_quality":"UNVERIFIED",
            "peak_rss_and_total_cpu":"UNVERIFIED",
            "scientific_first_use":"NOT_ESTABLISHED",
            "production_acceptance":"NOT_GRANTED"},
        "limitations":"Exact cyclic polynomial arithmetic is not original language semantics. "
            "Fixed-convolution counterexample does not exclude learned/context-conditioned spectral models; "
            "no GPU, full LLM or energy/resource benchmark."}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--json",type=Path,required=True)
    args=ap.parse_args()
    result=run()
    args.json.parent.mkdir(parents=True,exist_ok=True)
    args.json.write_bytes((json.dumps(result,sort_keys=True,indent=2)+"\n").encode("utf-8"))
    print("ACC65_U28_EXACT="+result["classification"]["exact_cyclic_convolution"])
    print("ACC65_U28_SPEED="+result["classification"]["full_matrix_kernel_speed"])
    print("ACC65_U28_SEMANTIC_BOUNDARY="+result["classification"]["universal_fixed_convolution_semantics"])

if __name__=="__main__":main()
