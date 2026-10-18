"""F124-Z stage-authenticated low-memory Wingless diagnostic.

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

CAPS=(28,26,24,22,20)
ARMS=("S_packed","T_full_index","U_microindex")
STAGES=("pre_import","after_import","after_fixtures","after_cap_attach",
        "after_warmup","after_inference")
SCHEMA="forge.research.f124z.wingless-failure-stage-development.v1"


def mark(stage,detail=""):
    print("F124Z_STAGE="+stage+(":"+detail if detail else ""),flush=True)


def worker(a):
    mark("pre_import")
    import f124y_wing_memory_boundary as prior
    import f124z_source as source
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
    if len(graphs)!=96:raise ValueError("F124Z_CASE_COUNT")
    mark("after_fixtures")
    cap=a.cap_mib*1048576
    method,handle=prior.enforce_process_memory_cap(cap) if False else (None,None)
    # Prior F124-Y enforcer is source-scoped to its older caps;
    # qualify these new caps with same kernel provider in this frozen gate.
    if sys.platform=="linux":
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(cap,cap))
        lo,hi=resource.getrlimit(resource.RLIMIT_AS)
        if (lo,hi)!=(cap,cap):raise ValueError("F124Z_LINUX_LIMIT_FAIL")
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
        if not handle:raise ValueError("F124Z_NO_WINDOWS_JOB")
        x=Extended();x.basic.flags=0x100;x.per_process=cap
        if not k.SetInformationJobObject(handle,9,ctypes.byref(x),
                                         ctypes.sizeof(x)):
            raise ValueError("F124Z_WINDOWS_JOB_CAP_FAIL")
        if not k.AssignProcessToJobObject(handle,k.GetCurrentProcess()):
            raise ValueError("F124Z_WINDOWS_JOB_ATTACH_FAIL")
        method="windows_JOB_PROCESS_MEMORY"
    else:
        raise ValueError("F124Z_UNSUPPORTED_OS")
    mark("after_cap_attach",method)
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
    raw={"schema":SCHEMA,"arm":a.arm,"cap_mib":a.cap_mib,
        "rep":a.rep,"graphs":len(logits),"ns":ns,"method":method,
        "logits_sha256":hashlib.sha256(json.dumps(
            logits,separators=(",",":")).encode()).hexdigest(),
        "stage":"after_inference",
        "RSS_peak_bytes":prior.hwm_bytes()}
    Path(a.output).write_text(json.dumps(raw,sort_keys=True)+"\n")
    print("F124Z_WORKER_SUCCESS="+a.arm+":"+str(a.cap_mib),flush=True)


def bench(a):
    import f124z_source as source
    source.frozen()
    proto=json.loads(source.PROTOCOL.read_text())
    if proto["experiments"]["W_failure_stages"]["caps_mib"]!=list(CAPS):
        raise ValueError("F124Z_CAP_PROTOCOL")
    out=Path(a.output)
    if out.exists():raise ValueError("F124Z_RESULT_ALREADY_EXISTS")
    rows=[]
    for cap in CAPS:
        for rep in range(2):
            for ix in range(3):
                arm=ARMS[(ix+rep)%3]
                result=out.parent/("f124z_"+str(cap)+"_"+str(rep)+"_"+arm+".json")
                cmd=[sys.executable,"-B",__file__,"--worker","--arm",arm,
                     "--cap-mib",str(cap),"--rep",str(rep),
                     "--original-o",a.original_o,
                     "--original-s",a.original_s,
                     "--original-u",a.original_u,"--output",str(result)]
                env=dict(os.environ);env["PYTHONHASHSEED"]="0"
                p=subprocess.run(cmd,text=True,capture_output=True,
                                 env=env,timeout=100)
                markers=[line.split("=",1)[1] for line in p.stdout.splitlines()
                         if line.startswith("F124Z_STAGE=")]
                valid=(markers and all(markers[i].startswith(stage)
                       for i,stage in enumerate(STAGES[:len(markers)])))
                if not valid:raise ValueError("F124Z_UNORDERED_STAGE_MARKERS")
                complete=p.returncode==0 and result.exists() and len(markers)==6
                item={"cap_mib":cap,"rep":rep,"arm":arm,
                      "completed":complete,"returncode":p.returncode,
                      "markers":markers,"last_witnessed_stage":markers[-1],
                      "stderr_tail":p.stderr[-2500:],
                      "stdout_tail":p.stdout[-500:]}
                if complete:item["worker"]=json.loads(result.read_text())
                rows.append(item)
        group=[x for x in rows if x["cap_mib"]==cap]
        print("F124ZW_CAP_"+str(cap)+"MiB="+str(sum(x["completed"] for x in group))+
              "/6:blocked="+str(6-sum(x["completed"] for x in group)),flush=True)
    for cap in CAPS:
        by=[z for z in rows if z["cap_mib"]==cap]
        s=[z for z in by if z["completed"]]
        if len(s)==6:
            hashes={arm:{x["worker"]["logits_sha256"] for x in s
                         if x["arm"]==arm} for arm in ARMS}
            if any(len(v)!=1 for v in hashes.values()) or len({
               next(iter(v)) for v in hashes.values()})!=1:
                raise ValueError("F124Z_ORIGINAL_S_T_U_MODEL_IDENTITY")
    receipt={"schema":SCHEMA,"freeze_blob":source.PROTOCOL_BLOB,
      "parent_sha":"1d23873d64fedd02fbd3bfa8aa3bbbc701a3b3d7",
      "platform":platform.platform(),"caps_mib":list(CAPS),
      "fresh_process_per_arm_rep":True,"source_pairs":48,
      "resource_blocked_is_not_inference_OOM":True,
      "process_stages":list(STAGES),"results":rows,
      "protected_first_use":False,"science_accepted":False,
      "optimizer_promoted":False}
    data=(json.dumps(receipt,sort_keys=True,indent=2)+"\n").encode()
    with out.open("xb") as f:f.write(data)
    print("F124ZW_SHA256="+hashlib.sha256(data).hexdigest(),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--bench",action="store_true")
    p.add_argument("--worker",action="store_true")
    p.add_argument("--arm",choices=ARMS)
    p.add_argument("--cap-mib",type=int,default=28)
    p.add_argument("--rep",type=int,default=0)
    for n in ("o","s","u"):p.add_argument("--original-"+n,required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    if a.worker:worker(a)
    elif a.bench:bench(a)
    else:p.error("specify --worker or --bench")
