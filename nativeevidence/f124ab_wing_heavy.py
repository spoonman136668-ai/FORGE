"""F124-AB stage-authenticated low-memory Wingless diagnostic.

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

CAPS=(24,22,20)
ARMS=("S_packed","T_full_index","U_microindex")
STAGES=("pre_import","after_import","after_fixtures","after_cap_attach",
        "after_warmup","after_inference")
SCHEMA="forge.research.f124ab.wingless-two-factor-resource-attribution.v1"


def mark(stage,detail=""):
    print("F124AB_STAGE="+stage+(":"+detail if detail else ""),flush=True)


def worker(a):
    mark("pre_import")
    import f124y_wing_memory_boundary as prior
    import tracemalloc
    import f124ab_source as source
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
    if len(graphs)!=96:raise ValueError("F124AB_CASE_COUNT")
    mark("after_fixtures")
    cap=a.cap_mib*1048576
    method,handle=prior.enforce_process_memory_cap(cap) if False else (None,None)
    # Prior F124-Y enforcer is source-scoped to its older caps;
    # qualify these new caps with same kernel provider in this frozen gate.
    if sys.platform=="linux":
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(cap,cap))
        lo,hi=resource.getrlimit(resource.RLIMIT_AS)
        if (lo,hi)!=(cap,cap):raise ValueError("F124AB_LINUX_LIMIT_FAIL")
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
        if not handle:raise ValueError("F124AB_NO_WINDOWS_JOB")
        x=Extended();x.basic.flags=0x100;x.per_process=cap
        if not k.SetInformationJobObject(handle,9,ctypes.byref(x),
                                         ctypes.sizeof(x)):
            raise ValueError("F124AB_WINDOWS_JOB_CAP_FAIL")
        if not k.AssignProcessToJobObject(handle,k.GetCurrentProcess()):
            raise ValueError("F124AB_WINDOWS_JOB_ATTACH_FAIL")
        method="windows_JOB_PROCESS_MEMORY"
    else:
        raise ValueError("F124AB_UNSUPPORTED_OS")
    mark("after_cap_attach",method)
    models={"S_packed":lambda g:S.wingless_packed(g,base,delta),
            "T_full_index":lambda g:T.wingless_indexed(g,base,delta),
            "U_microindex":lambda g:U.wingless_microindex(g,base,delta)}
    fn=models[a.arm]
    fn(graphs[0])
    mark("after_warmup")
    if a.instrument in ("tracemalloc","tracemalloc_plus_retain"):
        tracemalloc.start()
        tracemalloc.reset_peak()
    t0=time.perf_counter_ns()
    logits=[]
    extra=[]
    for graph in graphs:
        raw,counters=fn(graph)
        logits.append(raw.hex())
        if a.instrument in ("retain_case_diagnostics","tracemalloc_plus_retain"):
            # Identical model computation; retain the already-available
            # per-case counters in extra Python objects until inference ends.
            extra.append({"source_edges":len(graph["edges"]),
                "source_roles":len(graph["roles"]),
                "public_node_ids":len({edge["from"] for edge in graph["edges"]}),
                "logit_hex":raw.hex(),"counters":dict(counters)})
    if a.instrument in ("retain_case_diagnostics","tracemalloc_plus_retain"):
        if len(extra)!=96:raise ValueError("F124AB_DIAGNOSTICS_NOT_RETAINED")
    ns=time.perf_counter_ns()-t0
    tracer_peak=None
    if a.instrument in ("tracemalloc","tracemalloc_plus_retain"):
        _,tracer_peak=tracemalloc.get_traced_memory()
        tracemalloc.stop()
    mark("after_inference")
    raw={"schema":SCHEMA,"arm":a.arm,"cap_mib":a.cap_mib,
        "instrument":a.instrument,
        "tracer_peak_python_bytes":tracer_peak,
        "rep":a.rep,"graphs":len(logits),"ns":ns,"method":method,
        "logits_sha256":hashlib.sha256(json.dumps(
            logits,separators=(",",":")).encode()).hexdigest(),
        "stage":"after_inference",
        "RSS_peak_bytes":prior.hwm_bytes()}
    Path(a.output).write_text(json.dumps(raw,sort_keys=True)+"\n")
    print("F124AB_WORKER_SUCCESS="+a.arm+":"+str(a.cap_mib),flush=True)


def bench(a):
    import f124ab_source as source
    source.frozen()
    proto=json.loads(source.PROTOCOL.read_text())
    conf=proto["experiments"]["W_heavy_factorial"]
    modes=tuple(conf["instruments"])
    if conf["caps_mib"]!=list(CAPS) or modes!=(
       "plain","tracemalloc","retain_case_diagnostics",
       "tracemalloc_plus_retain"):
        raise ValueError("F124AB_HARD_FROZEN_PROTOCOL")
    dest=Path(a.output)
    if dest.exists():raise ValueError("F124AB_IMMUTABLE_OUTPUT_EXISTS")
    data=[]
    for cap in CAPS:
        for rep in range(2):
            for ix in range(3):
                arm=ARMS[(ix+rep)%3]
                for j in range(4):
                    mode=modes[(j+rep+ix)%4]
                    path=dest.parent/("f124ab_"+str(cap)+"_"+str(rep)+"_"+
                                     arm+"_"+mode+".json")
                    cmd=[sys.executable,"-B",__file__,"--worker","--arm",arm,
                         "--instrument",mode,"--cap-mib",str(cap),
                         "--rep",str(rep),"--original-o",a.original_o,
                         "--original-s",a.original_s,"--original-u",a.original_u,
                         "--output",str(path)]
                    p=subprocess.run(cmd,text=True,capture_output=True,
                                     timeout=130)
                    markers=[line.split("=",1)[1] for line in p.stdout.splitlines()
                             if line.startswith("F124AB_STAGE=")]
                    if not all(markers[k].startswith(stage)
                               for k,stage in enumerate(STAGES[:len(markers)])):
                        raise ValueError("F124AB_UNORDERED_PROCESS_STAGE")
                    passed=p.returncode==0 and len(markers)==len(STAGES) and path.exists()
                    row={"arm":arm,"instrument":mode,"rep":rep,"cap_mib":cap,
                         "completed":passed,"returncode":p.returncode,
                         "markers":markers,"last_witnessed_stage":markers[-1]
                          if markers else None,"stderr_tail":p.stderr[-2500:],
                         "stdout_tail":p.stdout[-500:]}
                    if passed:
                        z=json.loads(path.read_text())
                        if z["instrument"]!=mode or z["cap_mib"]!=cap or z["graphs"]!=96:
                            raise ValueError("F124AB_COMPLETED_WORKER_NOT_COMPARABLE")
                        row["worker"]=z
                    data.append(row)
        rows=[x for x in data if x["cap_mib"]==cap]
        print("F124AB_W_CAP_"+str(cap)+"MiB="+
              str(sum(x["completed"] for x in rows))+"/24",flush=True)
    if len(data)!=72:raise ValueError("F124AB_FULL_FACTORIAL_DENOMINATOR")
    contrasts={}
    for cap in CAPS:
        contrasts[str(cap)]={}
        for arm in ARMS:
            by=[x for x in data if x["cap_mib"]==cap and x["arm"]==arm]
            if len(by)!=8:raise ValueError("F124AB_ARM_CAP_DENOMINATOR")
            fam={}
            for mode in modes:
                v=[x for x in by if x["instrument"]==mode]
                good=[x for x in v if x["completed"]]
                fam[mode]={"completed":len(good),"attempts":2,
                    "last_failure_stages":[x["last_witnessed_stage"]
                      for x in v if not x["completed"]],
                    "median_inference_ns":int(statistics.median(
                         x["worker"]["ns"] for x in good)) if good else None,
                    "median_peak_RSS_bytes":int(statistics.median(
                         x["worker"]["RSS_peak_bytes"] for x in good))
                          if good else None,
                    "median_traced_python_bytes":int(statistics.median(
                         x["worker"]["tracer_peak_python_bytes"] for x in good))
                          if good and mode in ("tracemalloc","tracemalloc_plus_retain")
                          else None}
            complete=[x for x in by if x["completed"]]
            if len(complete)==8 and len({
              x["worker"]["logits_sha256"] for x in complete})!=1:
                raise ValueError("F124AB_FACTOR_CHANGED_ORIGINAL_MODEL_PREDICTIONS")
            contrasts[str(cap)][arm]=fam
    doc={"schema":SCHEMA,"freeze_blob":source.PROTOCOL_BLOB,
         "factorial":"TRACEMALLOC x RETAIN_CASE_DIAGNOSTICS",
         "one_factor_toggle_with_all_else_equal":True,
         "original_source_and_FIT_weights_unchanged":True,
         "fresh_subprocesses_per_factor":True,
         "same_OS_host_for_all_factor_cells":True,
         "blocked_not_automatically_inference_OOM":True,
         "caps_mib":list(CAPS),"arms":list(ARMS),"raw":data,
         "contrasts":contrasts,"platform":platform.platform(),
         "protected_first_use":False,"science_accepted":False,
         "optimizer_promoted":False}
    raw=(json.dumps(doc,sort_keys=True,indent=2)+"\n").encode()
    with dest.open("xb") as f:f.write(raw)
    print("F124AB_W_SHA256="+hashlib.sha256(raw).hexdigest())
    for cap,groups in contrasts.items():
        for arm,c in groups.items():
            print("F124AB_W_"+cap+"MiB_"+arm+":"+
                  ":".join(mode+"="+str(v["completed"])+"/2"
                     for mode,v in c.items()),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--bench",action="store_true")
    p.add_argument("--worker",action="store_true")
    p.add_argument("--arm",choices=ARMS)
    p.add_argument("--cap-mib",type=int,default=28)
    p.add_argument("--rep",type=int,default=0)
    p.add_argument("--instrument",choices=("plain","tracemalloc","retain_case_diagnostics","tracemalloc_plus_retain"),default="plain")
    for n in ("o","s","u"):p.add_argument("--original-"+n,required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    if a.worker:worker(a)
    elif a.bench:bench(a)
    else:p.error("specify --worker or --bench")
