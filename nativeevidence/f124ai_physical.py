"""F124-AI matched source-and-runner actual 6-arm peak RAM, heap, CPU, wall.
Three fresh subprocesses per frozen mode on each Ubuntu and Windows worker;
never assume 16 original cells make global learned parameters free.
"""
import argparse,hashlib,json,os,platform,statistics,subprocess,sys,time,tracemalloc
from pathlib import Path
ARMS=("historical_O_combined","historical_U_combined",
      "fixed_consistency16","fixed_collisionfree_index",
      "untrained_collisionfree_calibrator",
      "trained_collisionfree_calibrator")
SCHEMA="forge.research.f124ai.same-host-total-model-cost.v1"

def need(ok,desc):
    if not ok:raise ValueError("F124AI_COST_"+desc)

def worker(a):
    import f124ai_source as S
    import f124ai_calibration as C
    import f124v_yggdrasil_causal_trace as V
    import f124v_wingless_hardware as Hardware
    S.frozen()
    receipt=json.loads(Path(a.trained_receipt).read_text())
    need(receipt["schema"]==C.SCHEMA_TRAIN
         and receipt["freeze_blob"]==S.PROTOCOL_BLOB,
         "TRAINED_WEIGHT_SOURCE_RECEIPT")
    fitted=receipt["fitted"]
    threshold=receipt["diagnostic_threshold"]
    oldweights=V.original_weights(a.original_o,a.original_r,
                                  a.original_s,a.original_u)
    old=C.original_learner()
    graphs=[]
    for vector in S.VECTORS:
        for seed in S.COHORTS["delayed_noise"]["DEV"]:
            p,n=S.build("delayed_noise",seed,vector,"DEV")
            graphs.extend((p,n))
    need(len(graphs)==96,"96_GRAPH_DENOMINATOR")
    def measure_one(g):
        out=C.make_prediction(a.arm,g,fitted,threshold,oldweights,old)
        cells=out.get("actual_cell_peak",
               out.get("final_active",0)+out.get("final_retained",0))
        need(cells<=16,"CELL_BOUND")
        return (out.get("logit_hex",bool(out["prediction"])),
                cells,out.get("edge_scans"),
                out.get("raw_bit_comparisons"))
    measure_one(graphs[0])
    before=Hardware.hwm_bytes()
    tracemalloc.start();tracemalloc.reset_peak()
    t=time.perf_counter_ns();cpu=time.process_time_ns()
    results=[measure_one(g) for g in graphs]
    cpu_ns=time.process_time_ns()-cpu
    wall_ns=time.perf_counter_ns()-t
    _,heap=tracemalloc.get_traced_memory();tracemalloc.stop()
    peak=Hardware.hwm_bytes()
    need(cpu_ns>0 and wall_ns>0 and peak>=before,"INVALID_HARDWARE_READ")
    record={"schema":SCHEMA,"arm":a.arm,"rep":a.rep,
       "platform":platform.platform(),"python":platform.python_version(),
       "cpu_count":os.cpu_count(),"graphs":96,"persisted_cell_budget":16,
       "global_parameter_count":3 if a.arm=="trained_collisionfree_calibrator" else 0,
       "source_sha256":hashlib.sha256(json.dumps(
           graphs,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
       "output_sha256":hashlib.sha256(json.dumps(
           results,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
       "max_cell_entries":max(z[1] for z in results),
       "total_edge_scans":sum(z[2] for z in results)
                         if all(z[2] is not None for z in results) else None,
       "total_bit_compares":sum(z[3] for z in results)
                         if all(z[3] is not None for z in results) else None,
       "before_RSS_bytes":before,"actual_process_peak_RSS_bytes":peak,
       "Python_inference_peak_bytes":heap,"cpu_ns":cpu_ns,
       "wall_ns":wall_ns}
    dest=Path(a.output);need(not dest.exists(),"PROCESS_FILE_ALREADY_EXISTS")
    with dest.open("x") as f:json.dump(record,f,sort_keys=True)
    print("F124AI_PROCESS_"+a.arm+":wall_ns="+str(wall_ns)+
          ":RSS="+str(peak),flush=True)

def benchmark(a):
    import f124ai_source as S
    S.frozen()
    p=json.loads(S.PROTOCOL.read_text())["resources"]
    need(p["arms"]==list(ARMS) and
         p["each_arm_96_exact_same_source_graphs"] and
         p["three_new_process_repetitions"],
         "RESOURCE_PROTOCOL_CHANGED")
    dest=Path(a.output)
    need(dest.parent.is_dir() and not dest.exists(),"IMMUTABLE_OUTPUT")
    rows=[]
    for rep in range(3):
        for i in range(len(ARMS)):
            arm=ARMS[(i+rep)%len(ARMS)]
            out=dest.parent/("f124ai_process_"+str(rep)+"_"+arm+".json")
            cmd=[sys.executable,"-B",__file__,"--worker","--arm",arm,
                 "--rep",str(rep),"--trained-receipt",a.trained_receipt,
                 "--original-o",a.original_o,"--original-r",a.original_r,
                 "--original-s",a.original_s,"--original-u",a.original_u,
                 "--output",str(out)]
            child=subprocess.run(cmd,text=True,capture_output=True,
                   timeout=160,env={**os.environ,"PYTHONHASHSEED":"0"})
            need(child.returncode==0 and out.exists(),
                 "PROCESS_FAILED_"+arm+":"+child.stderr[-750:])
            row=json.loads(out.read_text())
            need(row["arm"]==arm and row["rep"]==rep and row["graphs"]==96,
                 "CHILD_RECEIPT_IDENTITY_DRIFT")
            rows.append(row)
    need(len(rows)==18 and len({x["source_sha256"] for x in rows})==1,
         "WRONG_DENOMINATOR_OR_DIFFERENT_SOURCE")
    summary={}
    for arm in ARMS:
        records=[x for x in rows if x["arm"]==arm]
        need(len(records)==3 and len({x["output_sha256"] for x in records})==1,
             "ORIGINAL_MODEL_NOT_DETERMINISTIC_"+arm)
        summary[arm]={"repetitions":3,
            "median_wall_ns":int(statistics.median(x["wall_ns"] for x in records)),
            "median_cpu_ns":int(statistics.median(x["cpu_ns"] for x in records)),
            "median_process_peak_RSS_bytes":int(statistics.median(
                x["actual_process_peak_RSS_bytes"] for x in records)),
            "median_Python_alloc_peak_bytes":int(statistics.median(
                x["Python_inference_peak_bytes"] for x in records)),
            "maximum_cell_entries":max(x["max_cell_entries"] for x in records),
            "global_parameter_count":records[0]["global_parameter_count"],
            "total_edge_scans":records[0]["total_edge_scans"],
            "total_bit_compares":records[0]["total_bit_compares"],
            "model_output_sha256":records[0]["output_sha256"]}
    result={"schema":SCHEMA,"freeze_blob":S.PROTOCOL_BLOB,
       "platform":platform.platform(),"same_OS_worker":True,
       "source_identical_all_arms":True,"three_fresh_processes_each":True,
       "original_per_cell_field_count":3,
       "original_persistent_cell_limit":16,
       "entire_parameter_memory_not_guaranteed_equal":True,
       "summary":summary,"raw":rows,"protected_first_use":False,
       "independent_science_accepted":False,"optimizer_promoted":False}
    data=(json.dumps(result,sort_keys=True,indent=2)+"\n").encode()
    with dest.open("xb") as f:f.write(data)
    print("F124AI_RESOURCE_SHA256="+hashlib.sha256(data).hexdigest(),flush=True)
    for arm,x in summary.items():
        print("F124AI_RESOURCE_"+arm+":rss="+str(x["median_process_peak_RSS_bytes"])+
              ":wall_ns="+str(x["median_wall_ns"])+
              ":cpu_ns="+str(x["median_cpu_ns"])+
              ":heap="+str(x["median_Python_alloc_peak_bytes"]),flush=True)

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--worker",action="store_true")
    a.add_argument("--bench",action="store_true")
    a.add_argument("--rep",type=int,default=0)
    a.add_argument("--arm",choices=ARMS)
    a.add_argument("--trained-receipt",required=True)
    for name in ("o","r","s","u"):a.add_argument("--original-"+name,required=True)
    a.add_argument("--output",required=True)
    opt=a.parse_args()
    if opt.worker:worker(opt)
    elif opt.bench:benchmark(opt)
    else:a.error("choose --worker or --bench")
