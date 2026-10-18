"""F124-AA source-matched Yggdrasil CPU/heap/process memory measurements.

Four original FIT-weight arms (O/U, original/destination diverse), two fresh
worker processes per arm on each platform. This benchmark measures source-only
inference, not posthoc true-path evaluator or reference double replay.
"""
from __future__ import annotations
import argparse,hashlib,json,os,platform,statistics,subprocess,sys,time,tracemalloc
from pathlib import Path

ARMS=("O_original","O_diverse","U_original","U_diverse")
SCHEMA="forge.research.f124aa.ygg-real-memory-compute.v1"

def worker(a):
    import f124aa_source as source
    import f124aa_ygg_transfer as model
    import f124v_yggdrasil_causal_trace as V
    import f124v_wingless_hardware as mem
    source.frozen()
    w=V.original_weights(a.original_o,a.original_r,a.original_s,a.original_u)
    graphs=[]
    for vec in source.VECTORS:
        for seed in source.COHORTS["YggdrasilStress"]["DEV"]:
            p,n=source.stress_pair(seed,vec,"DEV")
            graphs.extend((p,n))
    if len(graphs)!=96:raise ValueError("NO_SAME_96_GRAPHS")
    arm,mode=a.arm.split("_")
    model.forward(arm,graphs[0],w,mode)
    baseline=mem.hwm_bytes()
    tracemalloc.start();tracemalloc.reset_peak()
    start=time.perf_counter_ns()
    logits=[model.forward(arm,g,w,mode)["logit_hex"] for g in graphs]
    duration=time.perf_counter_ns()-start
    _,py_peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak=mem.hwm_bytes()
    if not(duration>0 and peak>0 and len(logits)==96):
        raise ValueError("INVALID_HARDWARE_RESULT")
    digest=hashlib.sha256(json.dumps(logits,separators=(",",":")).encode()).hexdigest()
    raw={"schema":SCHEMA,"arm":a.arm,"rep":a.rep,
         "source_graphs":96,"duration_ns":duration,
         "python_inference_heap_peak_bytes":py_peak,
         "baseline_process_hwm_bytes":baseline,
         "peak_process_hwm_bytes":peak,
         "host":platform.node(),"OS":platform.platform(),
         "Python":platform.python_version(),"CPU_count":os.cpu_count(),
         "logit_hex_sha256":digest,
         "original_frozen_weights":True,
         "protected_first_use":False}
    Path(a.output).write_text(json.dumps(raw,sort_keys=True)+"\n")
    print("F124AAYC_WORKER="+a.arm+":"+str(a.rep)+
          ":ns="+str(duration)+":rss="+str(peak),flush=True)

def bench(a):
    import f124aa_source as source
    source.frozen()
    p=json.loads(source.PROTOCOL.read_text())
    if p["ygg_transfer"]["benchmark"]["runs_each_arm"]!=2:
        raise ValueError("BENCH_FROZEN_DRIFT")
    target=Path(a.output)
    if target.exists():raise ValueError("IMMUTABLE_OUTPUT")
    rows=[]
    for rep in range(2):
        for i in range(4):
            arm=ARMS[(i+rep)%4]
            out=target.parent/("f124aa-cost-"+arm+"-"+str(rep)+".json")
            cmd=[sys.executable,"-B",__file__,"--worker",
                 "--arm",arm,"--rep",str(rep),
                 "--original-o",a.original_o,"--original-r",a.original_r,
                 "--original-s",a.original_s,"--original-u",a.original_u,
                 "--output",str(out)]
            env=dict(os.environ);env["PYTHONHASHSEED"]="0"
            subprocess.run(cmd,check=True,env=env,timeout=120)
            rows.append(json.loads(out.read_text()))
    agg={}
    for arm in ARMS:
        subset=[x for x in rows if x["arm"]==arm]
        if len(subset)!=2 or len({x["logit_hex_sha256"] for x in subset})!=1:
            raise ValueError("NONDETERMINISM_OR_LOST_REPETITION")
        agg[arm]={"median_ns":int(statistics.median(x["duration_ns"] for x in subset)),
            "median_python_heap_peak_bytes":int(statistics.median(
                x["python_inference_heap_peak_bytes"] for x in subset)),
            "median_whole_process_peak_RSS_bytes":int(statistics.median(
                x["peak_process_hwm_bytes"] for x in subset)),
            "logit_hash":subset[0]["logit_hex_sha256"]}
    raw={"schema":SCHEMA,"freeze_blob":source.PROTOCOL_BLOB,
         "platform":rows[0]["OS"],"same_host":len({x["host"] for x in rows})==1,
         "exactly_two_reps_each":True,"graphs_each":96,
         "new_source_only":True,"raw":rows,"arms":agg,
         "equal_total_memory_proven":False,"compute_matched_superiority_proven":False,
         "science_accepted":False,"protected_first_use":False,
         "optimizer_promoted":False}
    if not raw["same_host"]:raise ValueError("BENCH_HOST_DRIFT")
    data=(json.dumps(raw,sort_keys=True,indent=2)+"\n").encode()
    with target.open("xb") as f:f.write(data)
    print("F124AAYC="+json.dumps(agg,sort_keys=True),flush=True)
    print("F124AAYC_SHA256="+hashlib.sha256(data).hexdigest(),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--worker",action="store_true")
    p.add_argument("--bench",action="store_true")
    p.add_argument("--arm",choices=ARMS)
    p.add_argument("--rep",type=int,default=0)
    for x in ("o","r","s","u"):p.add_argument("--original-"+x,required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    if a.worker:worker(a)
    elif a.bench:bench(a)
    else:p.error("--worker or --bench required")
