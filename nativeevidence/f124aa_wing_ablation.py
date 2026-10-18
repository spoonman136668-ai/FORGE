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

CAPS=(24,22,20)
ARMS=("S_packed","T_full_index","U_microindex")
STAGES=("pre_import","after_import","after_fixtures","after_cap_attach",
        "after_warmup","after_inference")
SCHEMA="forge.research.f124aa.wingless-tracer-isolation.v1"


def mark(stage,detail=""):
    print("F124AA_STAGE="+stage+(":"+detail if detail else ""),flush=True)


def worker(a):
    mark("pre_import")
    import f124y_wing_memory_boundary as prior
    import tracemalloc
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
    models={"S_packed":lambda g:S.wingless_packed(g,base,delta),
            "T_full_index":lambda g:T.wingless_indexed(g,base,delta),
            "U_microindex":lambda g:U.wingless_microindex(g,base,delta)}
    fn=models[a.arm]
    fn(graphs[0])
    mark("after_warmup")
    if a.instrument=="tracemalloc":
        tracemalloc.start()
        tracemalloc.reset_peak()
    t0=time.perf_counter_ns()
    logits=[fn(g)[0].hex() for g in graphs]
    ns=time.perf_counter_ns()-t0
    tracer_peak=None
    if a.instrument=="tracemalloc":
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
    print("F124AA_WORKER_SUCCESS="+a.arm+":"+str(a.cap_mib),flush=True)


def bench(a):
    import f124aa_source as source
    source.frozen()
    p=json.loads(source.PROTOCOL.read_text())
    if (p["W_ablation"]["caps_mib"]!=list(CAPS) or
        p["W_ablation"]["instruments"]!=["none","tracemalloc"]):
        raise ValueError("F124AA_ABLATION_FREEZE")
    dest=Path(a.output)
    if dest.exists():raise ValueError("F124AA_IMMUTABLE_OUTPUT_EXISTS")
    rows=[]
    for cap in CAPS:
        for rep in range(2):
            # Same fresh process with only tracer toggled, rotating the order.
            for arm_index in range(3):
                arm=ARMS[(arm_index+rep)%3]
                for mode in (("none","tracemalloc") if rep%2==0
                             else ("tracemalloc","none")):
                    sub=dest.parent/("f124aa_"+str(cap)+"_"+str(rep)+"_"+
                                     arm+"_"+mode+".json")
                    cmd=[sys.executable,"-B",__file__,"--worker",
                         "--arm",arm,"--instrument",mode,
                         "--cap-mib",str(cap),"--rep",str(rep),
                         "--original-o",a.original_o,
                         "--original-s",a.original_s,
                         "--original-u",a.original_u,"--output",str(sub)]
                    env=dict(os.environ);env["PYTHONHASHSEED"]="0"
                    proc=subprocess.run(cmd,text=True,capture_output=True,
                                        env=env,timeout=120)
                    markers=[t.split("=",1)[1] for t in proc.stdout.splitlines()
                             if t.startswith("F124AA_STAGE=")]
                    ordered=all(markers[i].startswith(stage)
                          for i,stage in enumerate(STAGES[:len(markers)]))
                    if not ordered:
                        raise ValueError("F124AA_UNORDERED_WITNESS_MARKERS")
                    success=(proc.returncode==0 and sub.exists() and
                             len(markers)==len(STAGES))
                    row={"cap_mib":cap,"rep":rep,"arm":arm,"instrument":mode,
                         "completed":success,"returncode":proc.returncode,
                         "markers":markers,
                         "last_witnessed_stage":markers[-1] if markers else None,
                         "stderr_tail":proc.stderr[-2500:],
                         "stdout_tail":proc.stdout[-800:]}
                    if success:
                        measure=json.loads(sub.read_text())
                        if measure["arm"]!=arm or measure["cap_mib"]!=cap or (
                            measure["instrument"]!=mode or
                            measure["graphs"]!=96):
                            raise ValueError("F124AA_WORKER_INCORRECT")
                        row["measured"]=measure
                    rows.append(row)
        subset=[row for row in rows if row["cap_mib"]==cap]
        print("F124AA_W_CAP_"+str(cap)+"MiB="+
              str(sum(x["completed"] for x in subset))+"/12",flush=True)
    if len(rows)!=3*2*3*2:
        raise ValueError("F124AA_36_TRIAL_DENOMINATOR")
    contrasts={}
    for cap in CAPS:
        contrasts[str(cap)]={}
        for arm in ARMS:
            x=[z for z in rows if z["cap_mib"]==cap and z["arm"]==arm]
            if len(x)!=4:raise ValueError("F124AA_MATCHED_DENOMINATOR")
            good=[z for z in x if z["completed"]]
            modes={}
            for mode in ("none","tracemalloc"):
                sub=[z for z in good if z["instrument"]==mode]
                modes[mode]={"passed":len(sub),
                  "median_ns":int(statistics.median(z["measured"]["ns"]
                               for z in sub)) if sub else None,
                  "median_RSS_peak_bytes":int(statistics.median(
                     z["measured"]["RSS_peak_bytes"] for z in sub))
                      if sub else None,
                  "median_tracer_py_peak_bytes":int(statistics.median(
                     z["measured"]["tracer_peak_python_bytes"] for z in sub))
                      if sub and mode=="tracemalloc" else None}
            if len(good)==4:
                if len({z["measured"]["logits_sha256"] for z in good})!=1:
                    raise ValueError("F124AA_OUTPUTS_DIFFER_BY_INSTRUMENT")
            contrasts[str(cap)][arm]=modes
    receipt={"schema":SCHEMA,"freeze_blob":source.PROTOCOL_BLOB,
        "caps_mib":list(CAPS),"per_case_graphs":96,
        "fixed_same_original_weights_and_graphs":True,
        "only_inference_tracemalloc_toggle":True,
        "same_OS_runner_host_per_job":True,"cross_OS_limits_incomparable":True,
        "blocked_not_attributed_to_inference_oom":True,
        "matching_workers_per_cap_arm":4,
        "raw":rows,"contrasts":contrasts,"platform":platform.platform(),
        "original_protected_first_use":False,"science_accepted":False,
        "optimizer_promoted":False}
    raw=(json.dumps(receipt,sort_keys=True,indent=2)+"\n").encode()
    with dest.open("xb") as f:f.write(raw)
    print("F124AA_W_SHA256="+hashlib.sha256(raw).hexdigest(),flush=True)
    for cap,cells in contrasts.items():
        for arm,modes in cells.items():
            print("F124AA_W_"+cap+"MiB_"+arm+
                  ":plain="+str(modes["none"]["passed"])+"/2"+
                  ":trace="+str(modes["tracemalloc"]["passed"])+"/2"+
                  ":plain_ns="+str(modes["none"]["median_ns"])+
                  ":traced_ns="+str(modes["tracemalloc"]["median_ns"]),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--bench",action="store_true")
    p.add_argument("--worker",action="store_true")
    p.add_argument("--arm",choices=ARMS)
    p.add_argument("--cap-mib",type=int,default=28)
    p.add_argument("--rep",type=int,default=0)
    p.add_argument("--instrument",choices=("none","tracemalloc"),default="none")
    for n in ("o","s","u"):p.add_argument("--original-"+n,required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    if a.worker:worker(a)
    elif a.bench:bench(a)
    else:p.error("specify --worker or --bench")
