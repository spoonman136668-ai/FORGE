"""F124-AA stage-authenticated low-memory Wingless diagnostic.

No failure is called inference OOM without an inference-stage witness.
Kernel cap attaches after authentic imports and public fixture materialization.
Each tested arm/repetition runs in a new independent subprocess.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

CAPS=(28,24,20)
ARMS=("S_packed","T_full_index","U_microindex")
STAGES=("pre_import","after_import","after_fixtures","after_cap_attach",
        "after_warmup","after_inference")
SCHEMA="forge.research.f124aa.wingless-matched-tracemalloc-ablation.v1"


def mark(stage,detail=""):
    print("F124AA_STAGE="+stage+(":"+detail if detail else ""),flush=True)


def worker(a):
    mark("pre_import")
    import f124y_wing_memory_boundary as prior
    import f124aa_source as source
    import f124o_native_learners as O
    import f124s_native_mechanisms as S
    import f124t_variants as T
    import f124u_microindex_causal_rank as U
    import f124n_development_evidence as adapter
    import f124h_train_receipt as reference
    source.frozen()
    base,delta=prior.weights(a.original_o,a.original_s,a.original_u)
    control=adapter.clone_single_validator(reference.fixed_comparator,"graph")
    mark("after_import")
    graphs=[]
    for v in source.VECTORS:
        for seed in source.COHORTS["Wingless"]["DEV"]:
            p,n=source.build("Wingless",seed,v,"DEV")
            graphs.extend((p,n))
    if len(graphs)!=96:raise ValueError("F124AA_CASE_COUNT")
    mark("after_fixtures")
    cap=a.cap_mib*1048576
    method,handle=prior.enforce_process_memory_cap(cap) if False else (None,None)
    # Prior F124-Y enforcer is source-scoped to its older caps;
    # qualify these new caps with same kernel provider in this frozen gate.
    if sys.platform=="linux":
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(cap,cap))
        lo,hi=resource.getrlimit(resource.RLIMIT_AS)
        if (lo,hi)!=(cap,cap):raise ValueError("F124AA_LINUX_LIMIT_FAIL")
        method="linux_RLIMIT_AS"
    elif sys.platform=="win32":
        import ctypes
        from ctypes import wintypes
        class Basic(ctypes.Structure):
            _fields_=[("t1",ctypes.c_int64),("t2",ctypes.c_int64),
                ("flags",wintypes.DWORD),("minws",ctypes.c_size_t),
                ("maxws",ctypes.c_size_t),("active",wintypes.DWORD),
                ("affinity",ctypes.c_size_t),("priority",wintypes.DWORD),
                ("schedule",wintypes.DWORD)]
        class IO(ctypes.Structure):
            _fields_=[("q"+str(i),ctypes.c_uint64) for i in range(6)]
        class Extended(ctypes.Structure):
            _fields_=[("basic",Basic),("io",IO),("per_process",ctypes.c_size_t),
                      ("per_job",ctypes.c_size_t),("peak_process",ctypes.c_size_t),
                      ("peak_job",ctypes.c_size_t)]
        k=ctypes.WinDLL("kernel32",use_last_error=True)
        k.CreateJobObjectW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p]
        k.CreateJobObjectW.restype=ctypes.c_void_p
        k.GetCurrentProcess.restype=ctypes.c_void_p
        k.SetInformationJobObject.argtypes=[
            ctypes.c_void_p,wintypes.INT,ctypes.c_void_p,wintypes.DWORD]
        k.SetInformationJobObject.restype=wintypes.BOOL
        k.AssignProcessToJobObject.argtypes=[ctypes.c_void_p,ctypes.c_void_p]
        k.AssignProcessToJobObject.restype=wintypes.BOOL
        handle=k.CreateJobObjectW(None,None)
        if not handle:raise ValueError("F124AA_NO_WINDOWS_JOB")
        x=Extended();x.basic.flags=0x100;x.per_process=cap
        if not k.SetInformationJobObject(handle,9,ctypes.byref(x),
                                         ctypes.sizeof(x)):
            raise ValueError("F124AA_WINDOWS_JOB_CAP_FAIL")
        if not k.AssignProcessToJobObject(handle,k.GetCurrentProcess()):
            raise ValueError("F124AA_WINDOWS_JOB_ATTACH_FAIL")
        method="windows_JOB_PROCESS_MEMORY"
    else:
        raise ValueError("F124AA_UNSUPPORTED_OS")
    mark("after_cap_attach",method)
    trace=None
    if a.tracing=="tracemalloc_only":
        import tracemalloc
        tracemalloc.start()
        tracemalloc.reset_peak()
        trace=tracemalloc
    models={"S_packed":lambda g:S.wingless_packed(g,base,delta),
            "T_full_index":lambda g:T.wingless_indexed(g,base,delta),
            "U_microindex":lambda g:U.wingless_microindex(g,base,delta)}
    fn=models[a.arm]
    fn(graphs[0])
    mark("after_warmup")
    t0=time.perf_counter_ns()
    logits=[fn(g)[0].hex() for g in graphs]
    ns=time.perf_counter_ns()-t0
    mark("after_inference")
    py_peak=trace.get_traced_memory()[1] if trace is not None else None
    if trace is not None: trace.stop()
    raw={"schema":SCHEMA,"arm":a.arm,"cap_mib":a.cap_mib,
        "rep":a.rep,"graphs":len(logits),"ns":ns,"method":method,
        "logits_sha256":hashlib.sha256(json.dumps(
            logits,separators=(",",":")).encode()).hexdigest(),
        "stage":"after_inference","tracing":a.tracing,
        "inference_python_peak_bytes":py_peak,
        "RSS_peak_bytes":prior.hwm_bytes()}
    Path(a.output).write_text(json.dumps(raw,sort_keys=True)+"\n")
    print("F124AA_WORKER_SUCCESS="+a.arm+":"+str(a.cap_mib),flush=True)


def bench(a):
    import f124aa_source as source
    source.frozen()
    protocol=json.loads(source.PROTOCOL.read_text())
    e=protocol["wing_instrumentation"]
    if e["caps_mib"]!=list(CAPS) or e["instrumentation"]!=["off","tracemalloc_only"]:
        raise ValueError("F124AA_FROZEN_ABLATION_DRIFT")
    dest=Path(a.output)
    if dest.exists():raise ValueError("F124AA_RESULT_EXISTS")
    rows=[]
    for cap in CAPS:
        for rep in range(2):
            for ix in range(3):
                arm=ARMS[(ix+rep)%3]
                for tracing in ("off","tracemalloc_only"):
                    result=dest.parent/("f124aa_"+str(cap)+"_"+str(rep)+"_"+
                            arm+"_"+tracing+".json")
                    cmd=[sys.executable,"-B",__file__,"--worker","--arm",arm,
                         "--cap-mib",str(cap),"--rep",str(rep),
                         "--tracing",tracing,
                         "--original-o",a.original_o,
                         "--original-s",a.original_s,
                         "--original-u",a.original_u,
                         "--output",str(result)]
                    env=dict(os.environ);env["PYTHONHASHSEED"]="0"
                    try:
                        p=subprocess.run(cmd,text=True,capture_output=True,
                                         env=env,timeout=120)
                        stdout,stderr,code=p.stdout,p.stderr,p.returncode
                    except subprocess.TimeoutExpired as exc:
                        stdout=(exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout,bytes) else (exc.stdout or "")
                        stderr=(exc.stderr or b"").decode(errors="replace") if isinstance(exc.stderr,bytes) else (exc.stderr or "")
                        code=None
                    markers=[line.split("=",1)[1] for line in stdout.splitlines()
                             if line.startswith("F124AA_STAGE=")]
                    valid=all(markers[i].startswith(stage)
                              for i,stage in enumerate(STAGES[:len(markers)]))
                    if not valid:raise ValueError("F124AA_UNORDERED_STAGE_MARKER")
                    complete=(code==0 and result.exists() and len(markers)==6)
                    item={"cap_mib":cap,"rep":rep,"arm":arm,
                          "tracing":tracing,"completed":complete,
                          "returncode":code,"markers":markers,
                          "last_stage":markers[-1] if markers else "no_marker",
                          "stderr_tail":stderr[-1200:],"stdout_tail":stdout[-400:]}
                    if complete:
                        item["worker"]=json.loads(result.read_text())
                        if item["worker"]["tracing"]!=tracing:
                            raise ValueError("F124AA_TRACE_IDENTITY")
                    rows.append(item)
        group=[x for x in rows if x["cap_mib"]==cap]
        for tracing in ("off","tracemalloc_only"):
            comp=[x for x in group if x["tracing"]==tracing]
            print("F124AAW_"+str(cap)+"MiB_"+tracing+"="+
                  str(sum(x["completed"] for x in comp))+"/6",flush=True)
    for cap in CAPS:
        group=[x for x in rows if x["cap_mib"]==cap]
        for tracing in ("off","tracemalloc_only"):
            done=[x for x in group if x["tracing"]==tracing and x["completed"]]
            if len(done)==6:
                hashes={arm:{x["worker"]["logits_sha256"] for x in done
                            if x["arm"]==arm} for arm in ARMS}
                if any(len(y)!=1 for y in hashes.values()) or len(
                      {next(iter(y)) for y in hashes.values()})!=1:
                    raise ValueError("F124AA_WING_ORIGINAL_OUTPUT_DRIFT")
    for cap in CAPS:
        for rep in range(2):
            for arm in ARMS:
                pair=[x for x in rows if x["cap_mib"]==cap and
                      x["rep"]==rep and x["arm"]==arm and x["completed"]]
                if len(pair)==2 and pair[0]["worker"]["logits_sha256"]!=pair[1]["worker"]["logits_sha256"]:
                    raise ValueError("F124AA_ON_OFF_DIFFERENT_INFERENCE")
    receipt={"schema":SCHEMA,"freeze_blob":source.PROTOCOL_BLOB,
      "parent_sha":"c98fceb45200d65fc5be6d83ab9964bb1eaa5865",
      "platform":platform.platform(),"caps_mib":list(CAPS),
      "original_source_96_graphs_identical":True,
      "single_instrumentation_factor":"tracemalloc_only",
      "workloads_identical_except_instrumentation":True,
      "resource_blocked_is_not_inference_OOM":True,
      "process_stages":list(STAGES),"results":rows,
      "protected_first_use":False,"science_accepted":False,
      "optimizer_promoted":False}
    data=(json.dumps(receipt,sort_keys=True,indent=2)+"\n").encode()
    with dest.open("xb") as f:f.write(data)
    print("F124AAW_SHA256="+hashlib.sha256(data).hexdigest(),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--bench",action="store_true")
    p.add_argument("--worker",action="store_true")
    p.add_argument("--arm",choices=ARMS)
    p.add_argument("--cap-mib",type=int,default=28)
    p.add_argument("--rep",type=int,default=0)
    p.add_argument("--tracing",choices=("off","tracemalloc_only"),default="off")
    for n in ("o","s","u"):p.add_argument("--original-"+n,required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    if a.worker:worker(a)
    elif a.bench:bench(a)
    else:p.error("specify --worker or --bench")
