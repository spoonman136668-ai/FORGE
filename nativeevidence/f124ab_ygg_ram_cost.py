"""F124-AB actual same-host GitHub runner physical memory / CPU comparison.

Fresh subprocess on identical salted 7–9-hop stress graphs; no protected data.
Monitor OS actual peak RSS (not only Python heap), CPU and wall, with FIT
pretrained original O/U and frozen original versus public destination diversity.
"""
from __future__ import annotations
import argparse, hashlib, json, os, platform, statistics, subprocess, sys, time, tracemalloc
from pathlib import Path

ARMS=("O_original","O_diverse","U_original","U_diverse")
SCHEMA="forge.research.f124ab.ygg-samehost-physical-cost.v1"

def fail(ok,label):
    if not ok:raise ValueError("F124AB_COST_"+label)

def worker(a):
    import f124ab_source as source
    import f124ab_ygg_longscore as Y
    import f124v_wingless_hardware as resource
    import f124v_yggdrasil_causal_trace as V
    source.frozen()
    weights=V.original_weights(a.original_o,a.original_r,a.original_s,a.original_u)
    graphs=[]
    for vec in source.VECTORS:
        for seed in source.COHORTS["YggdrasilCost"]["DEV"]:
            pos,neg=source.stress_pair(seed,vec,"DEV",lane="YggdrasilCost")
            graphs.extend((pos,neg))
    fail(len(graphs)==96,"GRAPH_COUNT")
    arm,mode=a.arm.split("_",1)
    Y.forward(arm,graphs[0],weights,mode)
    baseline=resource.hwm_bytes()
    tracemalloc.start();tracemalloc.reset_peak()
    wall=time.perf_counter_ns();cpu=time.process_time_ns()
    logits=[Y.forward(arm,g,weights,mode)["logit_hex"] for g in graphs]
    cpu_ns=time.process_time_ns()-cpu
    wall_ns=time.perf_counter_ns()-wall
    _,python_peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak=resource.hwm_bytes()
    fail(wall_ns>0 and cpu_ns>0 and peak>=baseline and python_peak>=0,"MEASURE")
    data={"schema":SCHEMA,"arm":a.arm,"rep":a.rep,
        "python":platform.python_version(),"platform":platform.platform(),
        "machine":platform.machine(),"processor":platform.processor(),
        "cpu_count":os.cpu_count(),"host":platform.node(),
        "source_graphs":len(graphs),"public_graph_case_hash":hashlib.sha256(
            json.dumps(graphs,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
        "logit_sha256":hashlib.sha256(json.dumps(
            logits,separators=(",",":")).encode()).hexdigest(),
        "original_fitted_O_U_unchanged":True,"permanent_cells":16,
        "preinference_peak_RSS_bytes":baseline,
        "process_peak_RSS_bytes":peak,"python_inference_peak_bytes":python_peak,
        "wall_ns":wall_ns,"cpu_ns":cpu_ns}
    target=Path(a.output)
    fail(not target.exists(),"OUTPUT_ALREADY_EXISTS")
    with target.open("x") as f:json.dump(data,f,sort_keys=True)
    print("F124AB_COST_WORKER="+a.arm+":RSS="+str(peak)+
          ":heap="+str(python_peak)+":wall_ns="+str(wall_ns),flush=True)

def bench(a):
    import f124ab_source as source
    source.frozen()
    protocol=json.loads(source.PROTOCOL.read_text())
    x=protocol["experiments"]["Y_physical_cost"]
    fail(x["repetitions_per_arm"]==3 and
         x["arms"]==list(ARMS),"FROZEN_REPS_ARMS")
    dest=Path(a.output);fail(not dest.exists(),"OUTPUT_ALREADY_EXISTS")
    raw=[]
    for rep in range(3):
        for i in range(4):
            arm=ARMS[(i+rep)%4]
            output=dest.parent/("f124ab_y_cost_"+str(rep)+"_"+arm+".json")
            cmd=[sys.executable,"-B",__file__,"--worker",
                 "--arm",arm,"--rep",str(rep),
                 "--original-o",a.original_o,"--original-r",a.original_r,
                 "--original-s",a.original_s,"--original-u",a.original_u,
                 "--output",str(output)]
            p=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
            fail(p.returncode==0 and output.exists(),
                 "PHYSICAL_COST_WORKER_FAILED_"+arm+"_"+p.stderr[-350:])
            r=json.loads(output.read_text())
            fail(r["source_graphs"]==96 and r["arm"]==arm and r["rep"]==rep,
                 "SOURCE_WORKER_IDENTITY")
            raw.append(r)
    fail(len(raw)==12,"FULL_REPETITION_DENOMINATOR")
    cases={r["public_graph_case_hash"] for r in raw}
    fail(len(cases)==1,"ARMS_NOT_SAME_PUBLIC_GRAPHS")
    for arm in ARMS:
        fail(len({r["logit_sha256"] for r in raw if r["arm"]==arm})==1,
             "NONDETERMINISTIC_MODEL_REPLAY_"+arm)
    result={}
    for arm in ARMS:
        rows=[r for r in raw if r["arm"]==arm]
        result[arm]={"reps":len(rows),
            "median_wall_ns":int(statistics.median(r["wall_ns"] for r in rows)),
            "median_cpu_ns":int(statistics.median(r["cpu_ns"] for r in rows)),
            "median_process_peak_RSS_bytes":int(statistics.median(
                    r["process_peak_RSS_bytes"] for r in rows)),
            "median_preinference_RSS_bytes":int(statistics.median(
                    r["preinference_peak_RSS_bytes"] for r in rows)),
            "median_tracemalloc_peak_bytes":int(statistics.median(
                    r["python_inference_peak_bytes"] for r in rows)),
            "model_logit_sha256":rows[0]["logit_sha256"]}
    receipt={"schema":SCHEMA,"freeze_blob":source.PROTOCOL_BLOB,
        "same_host_per_OS":True,"repetitions":3,
        "same_source_graphs_across_arms":True,"public_graph_case_sha256":next(iter(cases)),
        "OS_process_peak_RSS_measured":True,
        "same_original_FIT_parameters_and_total_permanent_cell_slots":True,
        "physical_RAM_equal_proven":False,"same_CPU_proven":False,
        "protected_first_use":False,"accepted_science":False,
        "optimizer_promoted":False,
        "platform":platform.platform(),"arms":result,"raw":raw}
    data=(json.dumps(receipt,sort_keys=True,indent=2)+"\n").encode()
    with dest.open("xb") as f:f.write(data)
    print("F124AB_COST_SHA256="+hashlib.sha256(data).hexdigest(),flush=True)
    for arm,r in result.items():
        print("F124AB_COST_"+arm+":rss="+str(r["median_process_peak_RSS_bytes"])+
              ":heap="+str(r["median_tracemalloc_peak_bytes"])+
              ":wall_ns="+str(r["median_wall_ns"])+
              ":cpu_ns="+str(r["median_cpu_ns"]),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--bench",action="store_true")
    p.add_argument("--worker",action="store_true")
    p.add_argument("--arm",choices=ARMS)
    p.add_argument("--rep",type=int,default=0)
    for name in ("o","r","s","u"):p.add_argument("--original-"+name,required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    if args.worker:worker(args)
    elif args.bench:bench(args)
    else:p.error("Specify --worker or --bench")
