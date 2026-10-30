#!/usr/bin/env python3
"""ACC64 U04: real synthetic LoRA SGD with local persistent subprocess sharding.

No real LLM, remote network, total-process CPU, RSS, or production admission.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import random
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
REGISTRY=ROOT/"research/ac07_sourcefree/ac08_portfolio.py"
PREREG=ROOT/"docs/research/ACC-64-U04-PREREG-20261030.md"
REGISTRY_SHA="5126c860771fb024ccfc14c3f7ee8925edf29787"
PRE_SHA="b220304101f8944f2738c3f318dbd68a9208c661"
RANK=4
DIMENSIONS=(16,32)
SEEDS=(211,223,227)
REPEATS=2
FIT=64
VALID=16
STEPS=4
LR=0.05
MODES=("serial","process_1","process_2","process_4")

def blob(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def custody()->dict:
    if not REGISTRY.is_file() or blob(REGISTRY.read_bytes().replace(b"\r\n",b"\n"))!=REGISTRY_SHA:
        raise RuntimeError("ACC64_ORIGINAL_U04_REGISTRY_DRIFT")
    if '"distributed micro-LoRA gradients"' not in REGISTRY.read_text(encoding="utf-8"):
        raise RuntimeError("ACC64_U04_TITLE_DRIFT")
    if not PREREG.is_file() or "local multi-process micro-LoRA" not in PREREG.read_text(encoding="utf-8"):
        raise RuntimeError("ACC64_FROZEN_PREREG_MISSING")
    return {"original_claim":"U04","registry_git_blob":REGISTRY_SHA,
            "prereg_commit":PRE_SHA,"scientific_first_use":False}

def w0(o:int,i:int,n:int)->float:
    return (((o*17+i*11)%13)-6)*0.005

def predict(a:list[float],b:list[float],x:list[float],n:int)->list[float]:
    if len(a)!=RANK*n or len(b)!=n*RANK or len(x)!=n:
        raise ValueError("LoRA parameter or input dimensions changed")
    hidden=[math.fsum(a[j*n+i]*x[i] for i in range(n)) for j in range(RANK)]
    return [math.fsum(w0(o,i,n)*x[i] for i in range(n))+
            math.fsum(b[o*RANK+j]*hidden[j] for j in range(RANK))
            for o in range(n)]

def samples(n:int,seed:int):
    if n not in DIMENSIONS or seed not in SEEDS:raise ValueError("unfrozen cases")
    rnd=random.Random(seed*1000+n)
    teacher_a=[rnd.uniform(-.4,.4) for _ in range(RANK*n)]
    teacher_b=[rnd.uniform(-.4,.4) for _ in range(n*RANK)]
    a=[rnd.uniform(-.2,.2) for _ in range(RANK*n)]
    b=[rnd.uniform(-.2,.2) for _ in range(n*RANK)]
    def make(count:int):
        ret=[]
        for _ in range(count):
            x=[rnd.choice((-1.0,-.5,0.0,.5,1.0)) for _ in range(n)]
            ret.append([x,predict(teacher_a,teacher_b,x,n)])
        return ret
    return a,b,make(FIT),make(VALID)

def grad(a:list[float],b:list[float],cases:list,n:int)->dict:
    if not cases:raise ValueError("empty shard")
    ga=[0.0]*(RANK*n)
    gb=[0.0]*(n*RANK)
    total=0.0
    for x,target in cases:
        if len(x)!=n or len(target)!=n:raise ValueError("corrupt shard shape")
        h=[math.fsum(a[j*n+i]*x[i] for i in range(n)) for j in range(RANK)]
        dh=[0.0]*RANK
        for o in range(n):
            pred=math.fsum(w0(o,i,n)*x[i] for i in range(n))+
                 math.fsum(b[o*RANK+j]*h[j] for j in range(RANK))
            err=pred-target[o]
            total+=.5*err*err
            for j in range(RANK):
                gb[o*RANK+j]+=err*h[j]
                dh[j]+=err*b[o*RANK+j]
        for j in range(RANK):
            for i in range(n):
                ga[j*n+i]+=dh[j]*x[i]
    return {"ga":ga,"gb":gb,"sum_loss":total,"count":len(cases)}

def partition(cases:list,workers:int)->list:
    if workers not in (1,2,4) or len(cases)%workers:raise ValueError("bad shard")
    stride=len(cases)//workers
    result=[cases[i*stride:(i+1)*stride] for i in range(workers)]
    if sum(map(len,result))!=len(cases) or [c for shard in result for c in shard]!=cases:
        raise RuntimeError("MISSING_OR_DUPLICATE_MICROBATCH")
    return result

def aggregate(parts:list,total:int,n:int)->dict:
    if not parts or sum(p["count"] for p in parts)!=total:
        raise RuntimeError("INVALID_GRADIENT_AGGREGATION")
    if any(len(p["ga"])!=RANK*n or len(p["gb"])!=n*RANK for p in parts):
        raise RuntimeError("PARTIAL_GRADIENT_DIMENSION_DRIFT")
    return {"ga":[math.fsum(p["ga"][i] for p in parts)/total for i in range(RANK*n)],
            "gb":[math.fsum(p["gb"][i] for p in parts)/total for i in range(n*RANK)],
            "loss":math.fsum(p["sum_loss"] for p in parts)/total}

def loss(a:list[float],b:list[float],cases:list,n:int)->float:
    if not cases:raise ValueError("empty evaluation")
    return math.fsum(
        .5*math.fsum((v-t)**2 for v,t in zip(predict(a,b,x,n),target))
        for x,target in cases
    )/len(cases)

def fingerprint(a:list[float],b:list[float])->str:
    # Quantized only to catch cross-OS drift, never replace numeric tolerance checks.
    return hashlib.sha256((",".join(format(x,".7f") for x in a+b)).encode()).hexdigest()

def worker()->None:
    for line in sys.stdin:
        req=json.loads(line)
        if req.get("op")!="gradient":raise ValueError("UNKNOWN_WORKER_COMMAND")
        res=grad(req["a"],req["b"],req["cases"],req["n"])
        sys.stdout.write(json.dumps(res,separators=(",",":"))+"\n")
        sys.stdout.flush()

def train(n:int,seed:int,mode:str)->dict:
    if n not in DIMENSIONS or seed not in SEEDS or mode not in MODES:
        raise ValueError("unfrozen experiment")
    a,b,fit,valid=samples(n,seed)
    nworkers=0 if mode=="serial" else int(mode.rsplit("_",1)[1])
    shards=partition(fit,nworkers) if nworkers else [fit]
    workers=[]
    ipc=0
    t0=time.perf_counter_ns()
    try:
        for _ in range(nworkers):
            workers.append(subprocess.Popen([sys.executable,"-u",str(Path(__file__).resolve()),"--worker"],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                text=True,encoding="utf-8",bufsize=1))
        for step in range(STEPS):
            if nworkers:
                for process,shard in zip(workers,shards):
                    req=json.dumps({"op":"gradient","n":n,"a":a,"b":b,"cases":shard},
                                   separators=(",",":"))+"\n"
                    if process.poll() is not None:raise RuntimeError("WORKER_EARLY_EXIT")
                    process.stdin.write(req)
                    process.stdin.flush()
                    ipc+=len(req.encode("utf-8"))
                partial=[]
                for process in workers:
                    line=process.stdout.readline()
                    if not line:raise RuntimeError("WORKER_NO_RESPONSE")
                    ipc+=len(line.encode("utf-8"))
                    partial.append(json.loads(line))
            else:
                partial=[grad(a,b,fit,n)]
            g=aggregate(partial,len(fit),n)
            a=[x-LR*v for x,v in zip(a,g["ga"])]
            b=[x-LR*v for x,v in zip(b,g["gb"])]
        for process in workers:
            process.stdin.close()
        for process in workers:
            if process.wait(timeout=15)!=0:
                raise RuntimeError("WORKER_EXIT_FAILED:"+process.stderr.read()[-500:])
    finally:
        for process in workers:
            if process.poll() is None:process.kill()
            if process.stdin and not process.stdin.closed:process.stdin.close()
            if process.stdout:process.stdout.close()
            if process.stderr:process.stderr.close()
    wall_ns=time.perf_counter_ns()-t0
    return {"n":n,"seed":seed,"mode":mode,"steps":STEPS,"fit_count":len(fit),
        "workers":nworkers,"wall_ns":wall_ns,"ipc_bytes":ipc,
        "final_train_loss":loss(a,b,fit,n),
        "final_valid_loss":loss(a,b,valid,n),
        "a":a,"b":b,"param_fingerprint":fingerprint(a,b)}

def execute()->dict:
    iden=custody()
    observations=[]
    max_param_err=0.0
    max_valid_err=0.0
    for n in DIMENSIONS:
        for seed in SEEDS:
            for repeat in range(REPEATS):
                baseline=train(n,seed,"serial")
                for mode in MODES:
                    row=baseline if mode=="serial" else train(n,seed,mode)
                    param_err=max(abs(x-y) for x,y in zip(row["a"]+row["b"],baseline["a"]+baseline["b"]))
                    valid_err=abs(row["final_valid_loss"]-baseline["final_valid_loss"])
                    max_param_err=max(max_param_err,param_err)
                    max_valid_err=max(max_valid_err,valid_err)
                    observations.append({k:row[k] for k in ("n","seed","mode","steps","fit_count",
                            "workers","wall_ns","ipc_bytes","final_train_loss","final_valid_loss",
                            "param_fingerprint")} | {"repeat":repeat,"max_param_error":param_err,
                            "valid_loss_error":valid_err})
    if len(observations)!=len(DIMENSIONS)*len(SEEDS)*REPEATS*len(MODES):
        raise RuntimeError("INCOMPLETE_TRAINING_MATRIX")
    equivalent=max_param_err<=1e-9 and max_valid_err<=1e-9 and all(math.isfinite(x["final_valid_loss"]) for x in observations)
    def med(vals):
        a=sorted(vals)
        return (a[(len(a)-1)//2]+a[len(a)//2])/2
    cohorts=[]
    for n in DIMENSIONS:
        t={mode:med([row["wall_ns"] for row in observations if row["n"]==n and row["mode"]==mode])
           for mode in MODES}
        cohorts.append({"n":n,"median_wall_ns":t,
            "process4_over_serial":t["process_4"]/t["serial"],
            "process4_over_process1":t["process_4"]/t["process_1"]})
    speed=all(x["process4_over_serial"]<=.90 and x["process4_over_process1"]<=.90 for x in cohorts)
    valid_ipc=all(row["ipc_bytes"]>0 and row["workers"] in (1,2,4) for row in observations if row["mode"]!="serial")
    return {"schema":"forge.acc64.u04.original-local-process-lora.v1","identity":iden,
        "experiment":{"dimensions":list(DIMENSIONS),"seeds":list(SEEDS),"repeats":REPEATS,
                      "fit_samples":FIT,"valid_samples":VALID,"rank":RANK,"steps":STEPS,
                      "learning_rate":LR,"modes":list(MODES),"worker_topology":"persistent_local_subprocess_parameter_server"},
        "observations":observations,"cohorts":cohorts,
        "numerical":{"max_param_abs_error":max_param_err,"max_valid_loss_abs_error":max_valid_err,
                     "all_modes_equivalent":equivalent},
        "classification":{
            "analytic_lora_training_equivalence":"PASS" if equivalent else "U04_NO_GO_NUMERICAL_EQUIVALENCE",
            "four_worker_local_wall_speed":"U04_RESTRICTED_LOCAL_WALL_POSITIVE_ONLY" if equivalent and speed and valid_ipc else "U04_NO_GENERAL_VERIFIED_LOCAL_PROCESS_SPEED_WIN" if equivalent else "NOT_ADJUDICATED_CORRECTNESS_FAILED",
            "actual_cross_host_network":"UNVERIFIED","total_host_child_cpu":"UNVERIFIED",
            "peak_physical_rss":"UNVERIFIED","actual_pretrained_llm_training":"UNVERIFIED",
            "scientific_first_use":"NOT_ESTABLISHED","production_admission":"NOT_GRANTED"},
        "limit":"Small synthetic true-analytic LoRA SGD in persistent local Python subprocesses, not an original GPU, network cluster or full-model benchmark."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--worker",action="store_true")
    p.add_argument("--json",type=Path)
    args=p.parse_args()
    if args.worker:
        worker()
        return
    if args.json is None:raise ValueError("missing --json")
    result=execute()
    args.json.parent.mkdir(parents=True,exist_ok=True)
    args.json.write_bytes((json.dumps(result,indent=2,sort_keys=True)+"\n").encode())
    print("ACC64_U04_FULL_MATRIX="+str(len(result["observations"])))
    print("ACC64_U04_EQUIVALENCE="+result["classification"]["analytic_lora_training_equivalence"])
    print("ACC64_U04_SPEED="+result["classification"]["four_worker_local_wall_speed"])

if __name__=="__main__":main()
