"""F124-WW: same-worker, cold-subprocess, actual wall/RSS Wingless benchmark.

Each arm is a new interpreter process, repetitions are Latin-square ordered,
fixture construction/import/warmup excluded from perf_counter_ns window.
Peak RSS includes OS process plus fixture objects; tracemalloc peak measures
inference Python heap allocations. Windows uses psapi PeakWorkingSetSize;
Linux uses VmHWM. No equal-RAM or compute-matched superiority is implied.
"""
from __future__ import annotations
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import os
import sys
import time
import tracemalloc

import f124x_source as fresh
import f124o_native_learners as O
import f124s_native_mechanisms as S
import f124t_variants as T
import f124u_microindex_causal_rank as U
import f124n_development_evidence as adapter
import f124h_train_receipt as reference

O_SHA="025c97abc8eb69079d7d7d0f59bfdb81235b9ad9ab83e230f32b542d2cfbdb5d"
S_SHA="fb28a06ca4e0bfde9b4053734d61f2e3d1e760a8a3dda29e834780abe2339f25"
U_SHA="5634fa8b1acb02abf0640a558d268dccb751ace43093efd518f265ed44a56a49"
ARMS=("S_packed","T_full_index","U_microindex","O_learned","fixed_12of16")
SCHEMA="forge.research.f124x.wingless-hardware-hard-capped.v1"


def need(ok,code):
    fresh.need(ok,"BENCH_"+code)


def authenticate(path,sha):
    raw=Path(path).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==sha,"AUTHENTIC_ANCESTOR_"+sha[:10])
    return json.loads(raw)


def weights(o_path,s_path,u_path):
    o=authenticate(o_path,O_SHA)
    s=authenticate(s_path,S_SHA)
    u=authenticate(u_path,U_SHA)
    a=next(x for x in o["lanes"] if x["lane"]=="Wingless")
    b=next(x for x in s["lanes"] if x["lane"]=="Wingless")
    need(b["training_status"]=="GENUINE_FIT_PASS" and
         b["training"]["fit_only"] is True and
         b["training"]["training_steps"]==72 and
         u["wingless_original_S_weights_unchanged"] is True and
         u["wingless_new_trained_parameters"]==0 and
         u["source_parent_qualified_head"]==
             "becf7829c7a5521b234a1c25b659b614570f1af7",
         "ORIGINAL_MODEL_TRAINING_IDENTITY")
    base=a["training"]["trained_weights"]
    delta=b["training"]["delta"]
    need(O.sha(base)==a["training"]["trained_weight_sha256"] and
         S.digest(delta)==b["training"]["delta_sha256"],
         "ORIGINAL_WINGLESS_SIGNED_WEIGHTS")
    return list(base),list(delta)


def hwm_bytes():
    if sys.platform=="linux":
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmHWM:"):
                return int(line.split()[1])*1024
        raise ValueError("F124X_NO_LINUX_HIGH_WATER_MARK")
    if sys.platform=="win32":
        from ctypes import wintypes
        class PMC(ctypes.Structure):
            _fields_=[("cb",wintypes.DWORD),("PageFaultCount",wintypes.DWORD),
                      ("PeakWorkingSetSize",ctypes.c_size_t),
                      ("WorkingSetSize",ctypes.c_size_t),
                      ("QuotaPeakPagedPoolUsage",ctypes.c_size_t),
                      ("QuotaPagedPoolUsage",ctypes.c_size_t),
                      ("QuotaPeakNonPagedPoolUsage",ctypes.c_size_t),
                      ("QuotaNonPagedPoolUsage",ctypes.c_size_t),
                      ("PagefileUsage",ctypes.c_size_t),
                      ("PeakPagefileUsage",ctypes.c_size_t)]
        out=PMC();out.cb=ctypes.sizeof(PMC)
        api=ctypes.WinDLL("psapi",use_last_error=True)
        api.GetProcessMemoryInfo.argtypes=[ctypes.c_void_p,ctypes.POINTER(PMC),wintypes.DWORD]
        api.GetProcessMemoryInfo.restype=wintypes.BOOL
        kernel=ctypes.WinDLL("kernel32",use_last_error=True)
        kernel.GetCurrentProcess.restype=ctypes.c_void_p
        ok=api.GetProcessMemoryInfo(kernel.GetCurrentProcess(),
                                    ctypes.byref(out),out.cb)
        need(ok,"WIN32_RSS_PROVIDER_UNAVAILABLE")
        return int(out.PeakWorkingSetSize)
    raise ValueError("F124X_UNSUPPORTED_OS_FOR_REAL_RSS")


def enforce_process_memory_cap(cap):
    """Fail closed unless kernel-enforced process address/commit limit is active.

    Linux RLIMIT_AS limits total virtual address space, not just measured RSS.
    Windows JOB_OBJECT_LIMIT_PROCESS_MEMORY limits committed process memory.
    Both are STRICTER than merely observing peak RSS and have different kernel
    accounting semantics, so cross-OS hard-memory equivalence is NOT claimed.
    """
    need(cap in (67108864,50331648,41943040),"FROZEN_CAP_SET")
    if sys.platform=="linux":
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(cap,cap))
        soft,hard=resource.getrlimit(resource.RLIMIT_AS)
        need(soft==hard==cap,"LINUX_LIMIT_UNCONFIRMED")
        return ("linux_RLIMIT_AS",None)
    if sys.platform=="win32":
        from ctypes import wintypes
        SIZE_T=ctypes.c_size_t
        class BLI(ctypes.Structure):
            _fields_=[("PerProcessUserTimeLimit",ctypes.c_int64),
                      ("PerJobUserTimeLimit",ctypes.c_int64),
                      ("LimitFlags",wintypes.DWORD),
                      ("MinimumWorkingSetSize",SIZE_T),
                      ("MaximumWorkingSetSize",SIZE_T),
                      ("ActiveProcessLimit",wintypes.DWORD),
                      ("Affinity",SIZE_T),
                      ("PriorityClass",wintypes.DWORD),
                      ("SchedulingClass",wintypes.DWORD)]
        class IOC(ctypes.Structure):
            _fields_=[(k,ctypes.c_uint64) for k in
                    ("ReadOperationCount","WriteOperationCount","OtherOperationCount",
                     "ReadTransferCount","WriteTransferCount","OtherTransferCount")]
        class EXT(ctypes.Structure):
            _fields_=[("BasicLimitInformation",BLI),("IoInfo",IOC),
                      ("ProcessMemoryLimit",SIZE_T),("JobMemoryLimit",SIZE_T),
                      ("PeakProcessMemoryUsed",SIZE_T),("PeakJobMemoryUsed",SIZE_T)]
        kernel=ctypes.WinDLL("kernel32",use_last_error=True)
        kernel.CreateJobObjectW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p]
        kernel.CreateJobObjectW.restype=ctypes.c_void_p
        kernel.SetInformationJobObject.argtypes=[
            ctypes.c_void_p,wintypes.INT,ctypes.c_void_p,wintypes.DWORD]
        kernel.SetInformationJobObject.restype=wintypes.BOOL
        kernel.AssignProcessToJobObject.argtypes=[ctypes.c_void_p,ctypes.c_void_p]
        kernel.AssignProcessToJobObject.restype=wintypes.BOOL
        kernel.GetCurrentProcess.restype=ctypes.c_void_p
        job=kernel.CreateJobObjectW(None,None)
        need(bool(job),"WINDOWS_CREATE_JOB_FAILED")
        lim=EXT();lim.BasicLimitInformation.LimitFlags=0x100
        lim.ProcessMemoryLimit=cap
        need(bool(kernel.SetInformationJobObject(job,9,ctypes.byref(lim),
                                                  ctypes.sizeof(lim))),
             "WINDOWS_SET_HARD_PROCESS_LIMIT_FAILED")
        need(bool(kernel.AssignProcessToJobObject(job,kernel.GetCurrentProcess())),
             "WINDOWS_ATTACH_HARD_PROCESS_LIMIT_FAILED")
        return ("windows_JOB_OBJECT_PROCESS_MEMORY",job)
    raise ValueError("F124X_NO_ENFORCEABLE_HARD_BUDGET")


def graphs():
    fresh.frozen()
    g=[]
    for vec in fresh.VECTORS:
        for seed in fresh.COHORTS["Wingless"]["DEV"]:
            p,n=fresh.build("Wingless",seed,vec,"DEV")
            need(fresh.public_routes(p)==1 and fresh.public_routes(n)==0,
                 "PUBLIC_PAIR_ADMISSION")
            g.extend((p,n))
    need(len(g)==96,"NINETY_SIX_FIXED_GRAPHS")
    return g


def forward(arm,g,base,delta,control):
    if arm=="S_packed":return S.wingless_packed(g,base,delta)
    if arm=="T_full_index":return T.wingless_indexed(g,base,delta)
    if arm=="U_microindex":return U.wingless_microindex(g,base,delta)
    if arm=="O_learned":return O.wingless_forward(g,base)
    if arm=="fixed_12of16":
        pred,counts=control(g)
        return float(bool(pred)),counts
    raise ValueError("F124X_UNKNOWN_BENCH_ARM")


def worker(a):
    base,delta=weights(a.original_o,a.original_s,a.original_u)
    data=graphs()
    control=adapter.clone_single_validator(reference.fixed_comparator,"graph")
    enforcement,job=enforce_process_memory_cap(a.cap)
    forward(a.arm,data[0],base,delta,control)  # frozen warmup excluded
    before=hwm_bytes()
    tracemalloc.start()
    tracemalloc.reset_peak()
    start=time.perf_counter_ns()
    logit_hex=[]
    predictions=[]
    sum_edges=sum_bits=0
    max_index=max_cache=max_slots=0
    for graph in data:
        raw,c=forward(a.arm,graph,base,delta,control)
        pred=bool(raw) if a.arm=="fixed_12of16" else O.sigmoid(raw)>=.5
        logit_hex.append(raw.hex())
        predictions.append(pred)
        sum_edges+=c["public_edge_scans"]
        sum_bits+=c.get("raw_bit_ops",c.get("bit_comparisons",0))
        max_index=max(max_index,c.get("index_entries",0))
        max_cache=max(max_cache,c.get("max_key_cache_entries",0))
        max_slots=max(max_slots,c.get("max_active",0))
    duration=time.perf_counter_ns()-start
    _,py_peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    after=hwm_bytes()
    correct=sum(predictions[i] and not predictions[i+1]
                for i in range(0,len(predictions),2))
    value={"schema":SCHEMA,"platform":sys.platform,
       "hard_process_memory_limit_bytes":a.cap,
       "hard_budget_enforcement":enforcement,
       "python":platform.python_version(),"machine":platform.machine(),
       "processor":platform.processor(),"host":platform.node(),
       "cpu_count":os.cpu_count(),"arm":a.arm,"repetition":a.rep,
       "graph_count":96,"pair_count":48,"duration_ns":duration,
       "baseline_peak_rss_bytes":before,"process_peak_rss_bytes":after,
       "inference_python_peak_bytes":py_peak,
       "cpu_measurement_unit":"wall_perf_counter_ns",
       "peak_rss_includes_import_fixture_and_warmup":True,
       "peak_python_allocations_inference_only":True,
       "source_phase":"DEV","source_birth":"F124X_Wingless",
       "paired_correct":correct,"sum_public_edge_scans":sum_edges,
       "sum_raw_bit_ops":sum_bits,"max_index_entries":max_index,
       "max_cache_entries":max_cache,"max_cognitive_slots":max_slots,
       "serialized_state_bytes_per_record":(
          10 if a.arm in ("S_packed","T_full_index","U_microindex")
          else 40 if a.arm=="O_learned" else None),
       "prediction_sha256":hashlib.sha256(
          json.dumps(predictions,separators=(",",":")).encode()).hexdigest(),
       "logit_hex_sha256":hashlib.sha256(
          json.dumps(logit_hex,separators=(",",":")).encode()).hexdigest()}
    need(duration>0 and after>0 and py_peak>=0 and after<=a.cap,
         "NO_VALID_MEASUREMENTS_OR_MEMORY_BUDGET_EXCEEDED")
    Path(a.output).write_text(json.dumps(value,sort_keys=True)+"\n")
    print("F124X_WORKER:"+a.arm+":rep="+str(a.rep)+
          ":ns="+str(duration)+":rss="+str(after),flush=True)


def bench(a):
    fresh.frozen()
    parent=json.loads(fresh.PROTOCOL.read_text())
    need(parent["experiments"]["W_low_memory"]["caps_mib"]==[64,48,40]
         and parent["experiments"]["W_low_memory"]["repetitions"]==2,
         "PREREGISTERED_BUDGETS")
    # Authenticate all original receipt SHA256 BEFORE starting any workers.
    weights(a.original_o,a.original_s,a.original_u)
    dest=Path(a.output)
    need(dest.parent.is_dir() and not dest.exists(),"NONOVERWRITE_RESULT")
    sets={}
    for mib in (64,48,40):
        cap=mib*1048576
        rows=[]
        for rep in range(2):
            for ix in range(len(ARMS)):
                arm=ARMS[(ix+rep)%len(ARMS)]
                out=dest.parent/("f124x_"+str(mib)+"_"+str(rep)+"_"+arm+".json")
                need(not out.exists(),"REPEATED_BENCH_FILE")
                cmd=[sys.executable,"-B",__file__,"--worker","--arm",arm,
                    "--cap",str(cap),"--rep",str(rep),
                    "--original-o",a.original_o,"--original-s",a.original_s,
                    "--original-u",a.original_u,"--output",str(out)]
                env=dict(os.environ);env["PYTHONHASHSEED"]="0"
                result=subprocess.run(cmd,env=env,text=True,
                                      capture_output=True,timeout=100)
                if result.returncode==0 and out.is_file():
                    row=json.loads(out.read_text())
                    need(row["hard_process_memory_limit_bytes"]==cap
                         and row["process_peak_rss_bytes"]<=cap
                         and row["graph_count"]==96
                         and row["arm"]==arm
                         and row["repetition"]==rep,
                         "KERNEL_BUDGET_OR_CASE_DRIFT")
                    rows.append(row)
                else:
                    # Fail closed: never claim an unsupported allocation or
                    # subprocess exit was a successful memory measurement.
                    rows.append({"arm":arm,"repetition":rep,
                        "status":"BLOCKED_NOT_QUALIFIED",
                        "cap_bytes":cap,"return_code":result.returncode,
                        "stderr_tail":result.stderr[-2500:],
                        "stdout_tail":result.stdout[-1000:]})
        good=[x for x in rows if x.get("status")!="BLOCKED_NOT_QUALIFIED"]
        blocked=len(rows)-len(good)
        group={}
        for arm in ARMS:
            sub=[x for x in good if x["arm"]==arm]
            group[arm]={"completed_repetitions":len(sub),
                "median_ns":int(statistics.median(x["duration_ns"] for x in sub))
                              if sub else None,
                "median_peak_rss":int(statistics.median(
                     x["process_peak_rss_bytes"] for x in sub)) if sub else None,
                "prediction_sha256":sub[0]["prediction_sha256"] if sub else None,
                "logit_hex_sha256":sub[0]["logit_hex_sha256"] if sub else None}
        complete=blocked==0 and len(good)==10
        if complete:
            need(all(group[a]["logit_hex_sha256"]==
                     group["S_packed"]["logit_hex_sha256"]
                     for a in ("T_full_index","U_microindex")),
                     "S_T_U_BITEXACT_DRIFT")
            need(all(group[a]["prediction_sha256"]==
                     group["S_packed"]["prediction_sha256"]
                     for a in ("T_full_index","U_microindex")),
                     "S_T_U_PREDICTION_DRIFT")
            need(all(len({x["logit_hex_sha256"] for x in good
                          if x["arm"]==arm})==1 for arm in ARMS),
                 "NONDETERMINISTIC_LOGIT")
        sets[str(mib)]={"status":"COMPLETE_HARD_CAP_PASS" if complete else
                        "RESOURCE_OR_EXECUTION_BLOCKED_INCONCLUSIVE",
            "hard_cap_bytes":cap,"successful_workers":len(good),
            "blocked_workers":blocked,"arms":group,"raw":rows}
        print("F124XW_CAP_"+str(mib)+"MiB:"+sets[str(mib)]["status"]+
              ":S_ns="+str(group["S_packed"]["median_ns"])+
              ":T_ns="+str(group["T_full_index"]["median_ns"])+
              ":U_ns="+str(group["U_microindex"]["median_ns"]),flush=True)
    report={"schema":SCHEMA,"preimplementation_blob":fresh.PROTOCOL_BLOB,
        "platform":platform.platform(),"python":platform.python_version(),
        "host":platform.node(),"caps_mib":[64,48,40],"cases":96,
        "repetitions_per_arm":2,"kernel_caps_distinct_across_OS":True,
        "all_caps_have_qualified_success":all(
            x["status"]=="COMPLETE_HARD_CAP_PASS" for x in sets.values()),
        "science_accepted":False,"optimizer_promoted":False,
        "protected_first_use":False,"equal_total_memory_proven":False,
        "experiments":sets}
    with dest.open("xb") as f:
        f.write((json.dumps(report,sort_keys=True,indent=2)+"\n").encode())
    print("F124XW_SHA256="+hashlib.sha256(dest.read_bytes()).hexdigest())


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--worker",action="store_true")
    p.add_argument("--bench",action="store_true")
    p.add_argument("--arm",choices=ARMS)
    p.add_argument("--rep",type=int,default=0)
    p.add_argument("--cap",type=int,default=67108864)
    p.add_argument("--original-o",required=True)
    p.add_argument("--original-s",required=True)
    p.add_argument("--original-u",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    if args.worker:worker(args)
    elif args.bench:bench(args)
    else:p.error("select worker or bench")
