"""F124-AM actual whole-process RAM CPU wall and Python allocation costs.

Four raw measurements per arm? EXACT three fresh processes each, same
96 publicly masked variable-four DEV graph inputs per hosted OS.
"""
from __future__ import annotations
import argparse,hashlib,json,os,platform,statistics,subprocess,sys,time,tracemalloc
from pathlib import Path
ARMS=("fixed_maskset","learned_masked","untrained_masked")
SCHEMA="forge.research.f124am.physical-total-cost.v1"
def need(ok,msg):
    if not ok:raise ValueError("F124AM_COST_"+msg)
def worker(a):
    import f124am_masked_source as S
    import f124am_masked_learner as L
    import f124v_wingless_hardware as Hardware
    S.frozen()
    data=json.loads(Path(a.train_receipt).read_text())
    need(data["schema"]==L.SCHEMA and
         data["freeze_blob"]==S.PROTOCOL_BLOB and
         data["no_DEV_training_or_selection"],"TRAINED_FIT_PROVENANCE")
    graphs=[]
    for vector in S.VECTORS:
        for seed in S.COHORTS["variable_four"]["DEV"]:
            p,n=S.build("variable_four",seed,vector,"DEV")
            graphs.extend((p,n))
    need(len(graphs)==96,"GRAPH_96")
    def predict(graph):
        if a.arm=="fixed_maskset":
            res=L.inference(graph,None,0.,"fixed")
        elif a.arm=="learned_masked":
            res=L.inference(graph,data["learned"]["model"],
                 data["selected_threshold"],"learned")
        else:
            res=L.inference(graph,data["learned"]["initial"],.5,"untrained")
        need(not res.get("blocked",False) and
             res["actual_cell_peak"]<=16,"PERSISTENT_BUDGET_OR_FAILED")
        return (bool(res["prediction"]),res["actual_cell_peak"],
             res["edge_scans"],res["public_bit_comparisons"],
             res["maximum_packed_score_bit_length"])
    predict(graphs[0])
    start_RSS=Hardware.hwm_bytes()
    tracemalloc.start();tracemalloc.reset_peak()
    wall=time.perf_counter_ns();cpu=time.process_time_ns()
    predictions=[predict(g) for g in graphs]
    cpu_ns=time.process_time_ns()-cpu
    wall_ns=time.perf_counter_ns()-wall
    _,heap=tracemalloc.get_traced_memory();tracemalloc.stop()
    peak=Hardware.hwm_bytes()
    need(cpu_ns>0 and wall_ns>0 and peak>=start_RSS,"OS_REAL_CLOCK_OR_RSS")
    row={"schema":SCHEMA,"arm":a.arm,"rep":a.rep,
       "OS":platform.platform(),"graphs":96,
       "source_sha256":hashlib.sha256(json.dumps(
            graphs,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
       "predictions_sha256":hashlib.sha256(json.dumps(
            predictions,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
       "max_original_cells":max(v[1] for v in predictions),
       "largest_integer_score_bits":max(v[4] for v in predictions),
       "global_learned_model_values":7 if a.arm!="fixed_maskset" else 0,
       "edge_scans":sum(v[2] for v in predictions),
       "bit_comparisons":sum(v[3] for v in predictions),
       "OS_RSS_before_bytes":start_RSS,"process_peak_RSS_bytes":peak,
       "Python_inference_peak_bytes":heap,"CPU_ns":cpu_ns,"wall_ns":wall_ns}
    p=Path(a.output);need(not p.exists(),"OUTPUT_ALREADY_EXISTS")
    with p.open("x") as f:json.dump(row,f,sort_keys=True)
    print("F124AM_PROCESS_"+a.arm+":RSS="+str(peak)+
          ":wall="+str(wall_ns),flush=True)
def benchmark(a):
    import f124am_masked_source as S
    S.frozen()
    conf=json.loads(S.PROTOCOL.read_text())["hardware"]
    need(conf["arms"]==list(ARMS) and conf["graphs"]==96 and
         conf["repetitions"]==3,"RESOURCE_FROZEN_IDENTITY")
    dest=Path(a.output);need(dest.parent.is_dir() and not dest.exists(),
                             "IMMUTABLE_FINAL_RESOURCE")
    runs=[]
    for rep in range(3):
        for i in range(len(ARMS)):
            arm=ARMS[(i+rep)%len(ARMS)]
            out=dest.parent/("f124am_run_"+str(rep)+"_"+arm+".json")
            cmd=[sys.executable,"-B",__file__,"--worker","--arm",arm,
                 "--rep",str(rep),"--train-receipt",a.train_receipt,
                 "--output",str(out)]
            r=subprocess.run(cmd,text=True,capture_output=True,timeout=180,
                             env={**os.environ,"PYTHONHASHSEED":"0"})
            need(r.returncode==0 and out.exists(),
                 "SUBPROCESS_"+arm+":"+r.stderr[-700:])
            item=json.loads(out.read_text())
            need(item["rep"]==rep and item["arm"]==arm and
                 item["graphs"]==96,"SUBPROCESS_ID_DRIFT")
            runs.append(item)
    need(len(runs)==9 and len({r["source_sha256"] for r in runs})==1,
         "RESOURCE_INCONSISTENT_SOURCE")
    summary={}
    for arm in ARMS:
        q=[r for r in runs if r["arm"]==arm]
        need(len(q)==3 and len({r["predictions_sha256"] for r in q})==1,
             "OUTPUT_NOT_REPRODUCIBLE_"+arm)
        summary[arm]={"repetitions":3,
          "median_wall_ns":int(statistics.median(x["wall_ns"] for x in q)),
          "median_CPU_ns":int(statistics.median(x["CPU_ns"] for x in q)),
          "median_OS_peak_RSS_bytes":int(statistics.median(
               x["process_peak_RSS_bytes"] for x in q)),
          "median_Python_peak_bytes":int(statistics.median(
               x["Python_inference_peak_bytes"] for x in q)),
          "largest_integer_score_bits":max(x["largest_integer_score_bits"] for x in q),
          "max_original_cells":max(x["max_original_cells"] for x in q),
          "global_learned_values":q[0]["global_learned_model_values"],
          "edge_scans":q[0]["edge_scans"],"bit_comparisons":q[0]["bit_comparisons"]}
    report={"schema":SCHEMA,"freeze_blob":S.PROTOCOL_BLOB,
       "host_OS":platform.platform(),"same_worker_all_arms":True,
       "identical_public_masked_96_graphs":True,"fresh_runs_per_arm":3,
       "original_three_field_cells_cap":16,
       "total_byte_and_CPU_equality_NOT_assumed":True,
       "large_packed_python_integer_score_recorded":True,
       "global_params_counted":True,"summary":summary,"raw":runs,
       "protected_first_use":False,"science_accepted":False,
       "optimizer_promoted":False}
    raw=(json.dumps(report,sort_keys=True,indent=2)+"\n").encode()
    with dest.open("xb") as f:f.write(raw)
    print("F124AM_RESOURCE_SHA256="+hashlib.sha256(raw).hexdigest(),flush=True)
    for arm,z in summary.items():
        print("F124AM_COST_"+arm+":wall_ns="+str(z["median_wall_ns"])+
           ":rss="+str(z["median_OS_peak_RSS_bytes"])+
           ":cpu_ns="+str(z["median_CPU_ns"])+
           ":heap="+str(z["median_Python_peak_bytes"])+
           ":score_bits="+str(z["largest_integer_score_bits"]),flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--worker",action="store_true")
    p.add_argument("--bench",action="store_true")
    p.add_argument("--arm",choices=ARMS)
    p.add_argument("--rep",type=int,default=0)
    p.add_argument("--train-receipt",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    if a.worker:worker(a)
    elif a.bench:benchmark(a)
    else:p.error("choose --worker or --bench")
