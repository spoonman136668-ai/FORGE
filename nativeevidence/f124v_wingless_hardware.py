"""F124-VW: same-worker, cold-subprocess, actual wall/RSS Wingless benchmark.

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
import sys
import time
import tracemalloc

import f124v_fresh_source as fresh
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
SCHEMA="forge.research.f124v.wingless-hardware-measurement.v1"


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
        raise ValueError("F124V_NO_LINUX_HIGH_WATER_MARK")
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
    raise ValueError("F124V_UNSUPPORTED_OS_FOR_REAL_RSS")


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
    raise ValueError("F124V_UNKNOWN_BENCH_ARM")


def worker(a):
    base,delta=weights(a.original_o,a.original_s,a.original_u)
    data=graphs()
    control=adapter.clone_single_validator(reference.fixed_comparator,"graph")
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
       "python":platform.python_version(),"machine":platform.machine(),
       "processor":platform.processor(),"host":platform.node(),
       "cpu_count":os.cpu_count(),"arm":a.arm,"repetition":a.rep,
       "graph_count":96,"pair_count":48,"duration_ns":duration,
       "baseline_peak_rss_bytes":before,"process_peak_rss_bytes":after,
       "inference_python_peak_bytes":py_peak,
       "cpu_measurement_unit":"wall_perf_counter_ns",
       "peak_rss_includes_import_fixture_and_warmup":True,
       "peak_python_allocations_inference_only":True,
       "source_phase":"DEV","source_birth":"F124V_Wingless",
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
    need(duration>0 and after>0 and py_peak>=0,"NO_VALID_MEASUREMENTS")
    Path(a.output).write_text(json.dumps(value,sort_keys=True)+"\n")
    print("F124V_WORKER:"+a.arm+":rep="+str(a.rep)+
          ":ns="+str(duration)+":rss="+str(after),flush=True)


def bench(a):
    fresh.frozen()
    proto=json.loads(fresh.PROTOCOL.read_text())
    need(proto["experiment"]["repetitions_per_arm"]==4 and
         proto["experiment"]["sample_graphs_per_run"]==96,
         "FROZEN_BENCH_IDENTITY")
    target=Path(a.output);need(not target.exists(),"EXCLUSIVE_BENCH_OUTPUT")
    calls=[]
    for rep in range(4):
        # Same physical GitHub runner in same job, counterbalanced arm order.
        for i in range(len(ARMS)):
            arm=ARMS[(i+rep)%len(ARMS)]
            sub=target.parent/("f124v_"+str(rep)+"_"+arm+".json")
            need(not sub.exists(),"NO_BENCH_OVERRIDE")
            cmd=[sys.executable,"-B",__file__,"--worker","--arm",arm,
                 "--rep",str(rep),"--original-o",a.original_o,
                 "--original-s",a.original_s,"--original-u",a.original_u,
                 "--output",str(sub)]
            env=dict(os.environ);env["PYTHONHASHSEED"]="0"
            subprocess.run(cmd,check=True,env=env)
            calls.append(json.loads(sub.read_text()))
    need(len(calls)==20,"COMPLETE_FOUR_REP_FIVE_ARM_CENSUS")
    by={}
    for arm in ARMS:
        v=[c for c in calls if c["arm"]==arm]
        need(len(v)==4 and len({c["prediction_sha256"] for c in v})==1
             and len({c["logit_hex_sha256"] for c in v})==1
             and len({c["paired_correct"] for c in v})==1,
             "NONDETERMINISM_OR_MISSING_REPETITION")
        by[arm]={"paired_correct":v[0]["paired_correct"],
                 "logit_hex_sha256":v[0]["logit_hex_sha256"],
                 "prediction_sha256":v[0]["prediction_sha256"],
                 "median_duration_ns":int(statistics.median(c["duration_ns"] for c in v)),
                 "median_process_peak_rss_bytes":int(statistics.median(
                     c["process_peak_rss_bytes"] for c in v)),
                 "median_inference_python_peak_bytes":int(statistics.median(
                     c["inference_python_peak_bytes"] for c in v)),
                 "min_duration_ns":min(c["duration_ns"] for c in v),
                 "max_duration_ns":max(c["duration_ns"] for c in v),
                 "max_index_entries":max(c["max_index_entries"] for c in v),
                 "max_cache_entries":max(c["max_cache_entries"] for c in v),
                 "public_edge_scans":v[0]["sum_public_edge_scans"],
                 "raw_bit_ops":v[0]["sum_raw_bit_ops"]}
    for arm in ("T_full_index","U_microindex"):
        need(by[arm]["logit_hex_sha256"]==by["S_packed"]["logit_hex_sha256"]
             and by[arm]["prediction_sha256"]==
                 by["S_packed"]["prediction_sha256"]
             and by[arm]["paired_correct"]==by["S_packed"]["paired_correct"],
             "NOT_EXACT_S_T_U_REPLAY")
    need(by["U_microindex"]["max_index_entries"]<=8 and
         by["U_microindex"]["max_cache_entries"]<=8,
         "SCRATCH_FROZEN_BOUND")
    result={"schema":SCHEMA,"host_environment":{"platform":calls[0]["platform"],
        "machine":calls[0]["machine"],"python":calls[0]["python"],
        "processor":calls[0]["processor"],"cpu_count":calls[0]["cpu_count"],
        "host":calls[0]["host"]},"source_pairs":48,"graphs_each_run":96,
        "repetitions_per_arm":4,"sequential_one_runner_true":True,
        "fresh_process_each_repetition":True,"frozen_wingless_blob":fresh.PROTOCOL_BLOB,
        "benchmark_arms":by,"raw_repetitions":calls,
        "whole_process_hwm_includes_fixture_and_import":True,
        "allocation_peak_measured_during_inference":True,
        "total_memory_equal_proven":False,"equal_information_capacity_proven":False,
        "wall_time_and_ram_measured_same_worker":True,
        "compute_matched_scientific_superiority_proven":False,
        "protected_original_first_use":False,"science_accepted":False,
        "optimizer_promoted":False}
    target.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("F124VW_BENCH:"+calls[0]["platform"]+
          ":S_ns="+str(by["S_packed"]["median_duration_ns"])+
          ":T_ns="+str(by["T_full_index"]["median_duration_ns"])+
          ":U_ns="+str(by["U_microindex"]["median_duration_ns"])+
          ":S_RSS="+str(by["S_packed"]["median_process_peak_rss_bytes"])+
          ":U_RSS="+str(by["U_microindex"]["median_process_peak_rss_bytes"]))
    print("F124VW_SHA256="+hashlib.sha256(target.read_bytes()).hexdigest())


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--worker",action="store_true")
    p.add_argument("--bench",action="store_true")
    p.add_argument("--arm",choices=ARMS)
    p.add_argument("--rep",type=int,default=0)
    p.add_argument("--original-o",required=True)
    p.add_argument("--original-s",required=True)
    p.add_argument("--original-u",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    if args.worker:worker(args)
    elif args.bench:bench(args)
    else:p.error("select worker or bench")
