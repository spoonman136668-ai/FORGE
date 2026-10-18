"""F124-AF same-runner measured resource bound for unchanged original models
and executable independently designed 7-active/9-retained fixed control."""
from __future__ import annotations
import argparse,hashlib,json,os,platform,statistics,subprocess,sys,time,tracemalloc
from pathlib import Path

ARMS=("O_original","O_combined","U_original","U_combined","bounded_fixed16")
SCHEMA="forge.research.f124af.structural-resource-trial.v1"

def need(ok,s):
    if not ok:raise ValueError("F124AF_HARDWARE_"+s)

def worker(a):
    import f124af_sparse_source as src
    import f124af_fixed_controls as C
    import f124v_yggdrasil_causal_trace as V
    import f124v_wingless_hardware as HW
    src.frozen()
    weights=V.original_weights(a.original_o,a.original_r,a.original_s,a.original_u)
    graphs=[]
    for v in src.VECTORS:
        for seed in src.COHORTS["sparse_diamond"]["DEV"]:
            p,n=src.build("sparse_diamond",seed,v,"DEV")
            graphs.extend((p,n))
    need(len(graphs)==96,"GRAPH_DENOMINATOR")
    old=C.prior_model()
    def calculate(g):
        if a.arm=="bounded_fixed16":
            z=C.bounded_exact16(g)
            return ("1" if z["prediction"] else "0",z["edge_scans"],
                    z["raw_bit_comparisons"],z["actual_cell_peak"])
        who,kind=a.arm.split("_",1)
        params={} if kind=="original" else {"gamma":.1,"penalty":1.}
        z=old(who,g,weights,**params)
        return (z["logit_hex"],None,None,
                z["final_active"]+z["final_retained"])
    calculate(graphs[0])
    pre=HW.hwm_bytes()
    tracemalloc.start();tracemalloc.reset_peak()
    t=time.perf_counter_ns();cpu=time.process_time_ns()
    outputs=[calculate(g) for g in graphs]
    cpu_ns=time.process_time_ns()-cpu
    wall_ns=time.perf_counter_ns()-t
    _,heap=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak=HW.hwm_bytes()
    need(wall_ns>0 and cpu_ns>0 and peak>=pre,"INVALID_RESOURCE_MEASURE")
    need(all(x[3]<=16 for x in outputs),"PERSISTENT_STATE_CAP")
    sample={"schema":SCHEMA,"arm":a.arm,"rep":a.rep,"source_family":"sparse_diamond",
        "platform":platform.platform(),"python":platform.python_version(),
        "cpu_count":os.cpu_count(),"graphs":len(graphs),
        "original_total_cell_cap":16,
        "source_sha256":hashlib.sha256(json.dumps(
            graphs,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
        "outputs_sha256":hashlib.sha256(json.dumps(
            outputs,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
        "median_peak_cells":int(statistics.median(x[3] for x in outputs)),
        "raw_edge_scans":(sum(x[1] for x in outputs)
                         if all(x[1] is not None for x in outputs) else None),
        "raw_bit_comparisons":(sum(x[2] for x in outputs)
                         if all(x[2] is not None for x in outputs) else None),
        "actual_process_peak_RSS_bytes":peak,
        "preinference_peak_RSS_bytes":pre,"tracemalloc_peak_bytes":heap,
        "wall_ns":wall_ns,"cpu_ns":cpu_ns}
    target=Path(a.output);need(not target.exists(),"OUTPUT_ALREADY_EXISTS")
    with target.open("x") as f:json.dump(sample,f,sort_keys=True)
    print("F124AF_WORKER="+a.arm+":RSS="+str(peak)+":wall="+str(wall_ns),flush=True)

def bench(a):
    import f124af_sparse_source as src
    src.frozen()
    protocol=json.loads(src.PROTOCOL.read_text())
    trial=protocol["resources"]
    need(trial["arms"]==list(ARMS)
         and trial["fresh_repetitions"]==3
         and trial["graphs"]==96,"PRECOMMITTED_RESOURCE_TRIAL_DRIFT")
    destination=Path(a.output)
    need(destination.parent.is_dir() and not destination.exists(),"IMMUTABLE_FINAL")
    raw=[]
    for rep in range(3):
        for i in range(5):
            arm=ARMS[(i+rep)%5]
            out=destination.parent/("f124af_rss_"+str(rep)+"_"+arm+".json")
            cmd=[sys.executable,"-B",__file__,"--worker","--arm",arm,
              "--rep",str(rep),"--original-o",a.original_o,
              "--original-r",a.original_r,"--original-s",a.original_s,
              "--original-u",a.original_u,"--output",str(out)]
            child=subprocess.run(cmd,text=True,capture_output=True,timeout=150,
                    env={**os.environ,"PYTHONHASHSEED":"0"})
            need(child.returncode==0 and out.exists(),
                 "CHILD_INCOMPLETE_"+arm+"_"+child.stderr[-700:])
            z=json.loads(out.read_text())
            need(z["arm"]==arm and z["rep"]==rep and z["graphs"]==96,
                 "CHILD_SOURCE_DRIFT")
            raw.append(z)
    need(len(raw)==15 and len({x["source_sha256"] for x in raw})==1,
         "SOURCE_IDENTICAL_ALL_ARMS")
    result={}
    for arm in ARMS:
        q=[x for x in raw if x["arm"]==arm]
        need(len(q)==3 and len({x["outputs_sha256"] for x in q})==1,
             "NONDETERMINISTIC_RUN_"+arm)
        result[arm]={"repetitions":3,"median_wall_ns":int(statistics.median(
             x["wall_ns"] for x in q)),
          "median_cpu_ns":int(statistics.median(x["cpu_ns"] for x in q)),
          "median_process_peak_RSS_bytes":int(statistics.median(
             x["actual_process_peak_RSS_bytes"] for x in q)),
          "median_Python_alloc_bytes":int(statistics.median(
             x["tracemalloc_peak_bytes"] for x in q)),
          "median_cell_peak":int(statistics.median(x["median_peak_cells"] for x in q)),
          "raw_edge_scans":q[0]["raw_edge_scans"],
          "raw_bit_comparisons":q[0]["raw_bit_comparisons"],
          "model_hash":q[0]["outputs_sha256"]}
    doc={"schema":SCHEMA,"freeze_blob":src.PROTOCOL_BLOB,
         "same_OS_host":True,"original_source":True,"all_graphs_identical":True,
         "original_model_coefficient_frozen":True,"no_presumed_equal_compute":True,
         "same_max_cells":16,"platform":platform.platform(),
         "results":result,"raw":raw,
         "protected_first_use":False,"science_accepted":False,
         "optimizer_promoted":False}
    data=(json.dumps(doc,sort_keys=True,indent=2)+"\n").encode()
    with destination.open("xb") as f:f.write(data)
    print("F124AF_PHYSICAL_SHA256="+hashlib.sha256(data).hexdigest(),flush=True)
    for name,z in result.items():
        print("F124AF_PHYSICAL_"+name+
          ":rss="+str(z["median_process_peak_RSS_bytes"])+
          ":wall_ns="+str(z["median_wall_ns"])+
          ":cpu_ns="+str(z["median_cpu_ns"])+
          ":heap="+str(z["median_Python_alloc_bytes"]),flush=True)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--worker",action="store_true")
    ap.add_argument("--bench",action="store_true")
    ap.add_argument("--rep",type=int,default=0)
    ap.add_argument("--arm",choices=ARMS)
    for k in ("o","r","s","u"):ap.add_argument("--original-"+k,required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    if args.worker:worker(args)
    elif args.bench:bench(args)
    else:ap.error("select worker or bench")
