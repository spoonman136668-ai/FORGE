"""F124-AK physically measured 7-arm model+packed-state budget, exact
same graph set on each OS worker, three fresh processes per arm."""
from __future__ import annotations
import argparse,hashlib,json,os,platform,statistics,subprocess,sys,time,tracemalloc
from pathlib import Path
ARMS=("historical_O_combined","historical_U_combined",
      "fixed_consistency16","fixed_collisionfree",
      "untrained_hop_relation","intermediate_trained_untrained_binder",
      "trained_hop_relation")
SCHEMA="forge.research.f124ak.actual-whole-model-resource.v1"
def need(ok,code):
    if not ok:raise ValueError("F124AK_COST_"+code)
def worker(a):
    import f124ak_source as S
    import f124ak_learned as L
    import f124ak_comparison as C
    import f124v_yggdrasil_causal_trace as V
    import f124v_wingless_hardware as Hardware
    S.frozen()
    data=json.loads(Path(a.trained_receipt).read_text())
    need(data["schema"]==L.SCHEMA and data["freeze_blob"]==S.PROTOCOL_BLOB,
         "ORIGINAL_FIT_RECEIPT")
    trained=data["trained"];threshold=data["selected_threshold"]
    historical=V.original_weights(a.original_o,a.original_r,
                                  a.original_s,a.original_u)
    old=C.old_original()
    graphs=[]
    for v in S.VECTORS:
        for seed in S.COHORTS["far_weave"]["DEV"]:
            p,n=S.build("far_weave",seed,v,"DEV")
            graphs.extend((p,n))
    need(len(graphs)==96,"FROZEN_GRAPH_DENOMINATOR")
    def run(g):
        z=C.predict(a.arm,g,trained,threshold,historical,old)
        cells=z.get("actual_cell_peak",
                    z.get("final_active",0)+z.get("final_retained",0))
        need(cells<=16,"PERSISTENT_CELLS_MORE_THAN_16")
        return (z.get("logit_hex",bool(z["prediction"])),cells,
                z.get("edge_scans"),z.get("public_bit_lane_predictor_calls"))
    run(graphs[0])
    before=Hardware.hwm_bytes()
    tracemalloc.start();tracemalloc.reset_peak()
    tic=time.perf_counter_ns();cpu=time.process_time_ns()
    predictions=[run(g) for g in graphs]
    cpu_ns=time.process_time_ns()-cpu
    wall_ns=time.perf_counter_ns()-tic
    _,heap=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    RSS=Hardware.hwm_bytes()
    need(cpu_ns>0 and wall_ns>0 and RSS>=before,"INVALID_REAL_CLOCK_OR_RSS")
    raw={"schema":SCHEMA,"arm":a.arm,"rep":a.rep,
         "host_OS":platform.platform(),"graphs":len(graphs),
         "source_hash":hashlib.sha256(json.dumps(
             graphs,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
         "predictions_hash":hashlib.sha256(json.dumps(
             predictions,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
         "max_cell_count":max(z[1] for z in predictions),
         "global_model_parameter_count":39 if a.arm=="trained_hop_relation" else (
             38 if a.arm in ("untrained_hop_relation",
              "intermediate_trained_untrained_binder") else 0),
         "learned_mask_stored_as_integer_in_original_score":(
             a.arm.endswith("hop_relation") or
             a.arm=="intermediate_trained_untrained_binder"),
         "total_public_edge_scans":sum(z[2] for z in predictions)
                if all(z[2] is not None for z in predictions) else None,
         "bit_lane_predictor_calls":sum(z[3] for z in predictions)
                if all(z[3] is not None for z in predictions) else None,
         "RSS_before_bytes":before,"peak_process_RSS_bytes":RSS,
         "Python_inference_alloc_peak_bytes":heap,
         "cpu_ns":cpu_ns,"wall_ns":wall_ns}
    path=Path(a.output);need(not path.exists(),"REPEATED_PROCESS_FILE")
    with path.open("x") as f:json.dump(raw,f,sort_keys=True)
    print("F124AK_WORKER_"+a.arm+":rss="+str(RSS)+":wall_ns="+str(wall_ns),
          flush=True)

def benchmark(a):
    import f124ak_source as S
    S.frozen()
    conf=json.loads(S.PROTOCOL.read_text())["resources"]
    need(conf["arms"]==list(ARMS) and conf["graphs"]==96
         and conf["fresh_subprocess_repetitions"]==3,
         "PREREGISTERED_HARDWARE_DESIGN_DRIFT")
    path=Path(a.output)
    need(path.parent.is_dir() and not path.exists(),"FINAL_RECEIPT_EXISTS")
    observations=[]
    for rep in range(3):
        for index in range(len(ARMS)):
            arm=ARMS[(index+rep)%len(ARMS)]
            dest=path.parent/("f124ak_"+str(rep)+"_"+arm+".json")
            args=[sys.executable,"-B",__file__,"--worker","--rep",str(rep),
                  "--arm",arm,"--trained-receipt",a.trained_receipt,
                  "--original-o",a.original_o,"--original-r",a.original_r,
                  "--original-s",a.original_s,"--original-u",a.original_u,
                  "--output",str(dest)]
            child=subprocess.run(args,text=True,capture_output=True,timeout=180,
                  env={**os.environ,"PYTHONHASHSEED":"0"})
            need(child.returncode==0 and dest.exists(),
                 "CHILD_FAILED_"+arm+":"+child.stderr[-500:])
            r=json.loads(dest.read_text())
            need(r["rep"]==rep and r["arm"]==arm and r["graphs"]==96,
                 "CHILD_PROVENANCE_DRIFT")
            observations.append(r)
    need(len(observations)==21 and len({x["source_hash"] for x in observations})==1,
         "RESOURCE_SOURCE_OR_DENOMINATOR_NOT_IDENTICAL")
    results={}
    for arm in ARMS:
        v=[x for x in observations if x["arm"]==arm]
        need(len(v)==3 and len({x["predictions_hash"] for x in v})==1,
             "NONDETERMINISTIC_REPLAY_"+arm)
        results[arm]={"repetitions":3,
            "median_wall_ns":int(statistics.median(x["wall_ns"] for x in v)),
            "median_cpu_ns":int(statistics.median(x["cpu_ns"] for x in v)),
            "median_process_peak_RSS_bytes":int(statistics.median(
                x["peak_process_RSS_bytes"] for x in v)),
            "median_Python_inference_heap_bytes":int(statistics.median(
                x["Python_inference_alloc_peak_bytes"] for x in v)),
            "max_original_persistent_cells":max(x["max_cell_count"] for x in v),
            "global_model_parameter_count":v[0]["global_model_parameter_count"],
            "larger_integer_score_payload":v[0][
               "learned_mask_stored_as_integer_in_original_score"],
            "public_edge_scans":v[0]["total_public_edge_scans"],
            "bit_lane_predictor_calls":v[0]["bit_lane_predictor_calls"]}
    doc={"schema":SCHEMA,"freeze_blob":S.PROTOCOL_BLOB,
         "platform":platform.platform(),
         "same_OS_worker_for_all_arms":True,"same_exact_96_sources":True,
         "three_fresh_processes_per_arm":True,"original_cell_cap":16,
         "same_total_byte_cost_NOT_assumed":True,
         "additional_global_parameter_RAM_recorded":True,
         "packed_state_integer_payload_recorded":True,
         "results":results,"raw":observations,
         "protected_first_use":False,"science_accepted":False,
         "optimizer_promoted":False}
    payload=(json.dumps(doc,sort_keys=True,indent=2)+"\n").encode()
    with path.open("xb") as f:f.write(payload)
    print("F124AK_RESOURCE_SHA256="+hashlib.sha256(payload).hexdigest(),flush=True)
    for arm,item in results.items():
        print("F124AK_COST_"+arm+
              ":RSS="+str(item["median_process_peak_RSS_bytes"])+
              ":WALL="+str(item["median_wall_ns"])+
              ":CPU="+str(item["median_cpu_ns"])+
              ":HEAP="+str(item["median_Python_inference_heap_bytes"]),flush=True)
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--worker",action="store_true")
    ap.add_argument("--bench",action="store_true")
    ap.add_argument("--rep",type=int,default=0)
    ap.add_argument("--arm",choices=ARMS)
    for x in ("o","r","s","u"):ap.add_argument("--original-"+x,required=True)
    ap.add_argument("--trained-receipt",required=True)
    ap.add_argument("--output",required=True)
    a=ap.parse_args()
    if a.worker:worker(a)
    elif a.bench:benchmark(a)
    else:ap.error("choose --bench or --worker")
