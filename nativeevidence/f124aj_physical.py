"""F124-AJ real same-host measured 6-arm resource comparison.
Only same graph identity, original 16-cell limit and actual CPU/RSS/heap
support a fair cost statement. Larger 33-bit packed score and 50 neural
parameters are explicitly NOT free and are instrumented.
"""
from __future__ import annotations
import argparse,hashlib,json,os,platform,statistics,subprocess,sys,time,tracemalloc
from pathlib import Path
ARMS=("historical_O_combined","historical_U_combined",
      "fixed_consistency16","fixed_collisionfree",
      "untrained_raw_neural","trained_raw_neural")
SCHEMA="forge.research.f124aj.six-arm-total-physical-cost.v1"
def need(ok,s):
    if not ok:raise ValueError("F124AJ_COST_"+s)
def worker(a):
    import f124aj_source as S
    import f124aj_raw_neural as N
    import f124aj_comparison as C
    import f124v_yggdrasil_causal_trace as V
    import f124v_wingless_hardware as H
    S.frozen()
    receipt=json.loads(Path(a.trained_receipt).read_text())
    need(receipt["schema"]==N.SCHEMA and
         receipt["freeze_blob"]==S.PROTOCOL_BLOB,"FIT_IDENTITY")
    trained=receipt["trained"];threshold=receipt["selected_threshold"]
    weights=V.original_weights(a.original_o,a.original_r,a.original_s,a.original_u)
    old=C.original()
    graphs=[]
    for v in S.VECTORS:
        for seed in S.COHORTS["far_event"]["DEV"]:
            p,n=S.build("far_event",seed,v,"DEV")
            graphs.extend((p,n))
    need(len(graphs)==96,"GRAPH_DENOMINATOR")
    def infer(g):
        x=C.predict(a.arm,g,trained,threshold,weights,old)
        cells=x.get("actual_cell_peak",
                    x.get("final_active",0)+x.get("final_retained",0))
        need(cells<=16,"CAPACITY_DRIFT")
        return (x.get("logit_hex",bool(x["prediction"])),cells,
                x.get("edge_scans"),x.get("raw_bit_comparisons"))
    infer(graphs[0])
    before=H.hwm_bytes()
    tracemalloc.start();tracemalloc.reset_peak()
    wall=time.perf_counter_ns();cpu=time.process_time_ns()
    predictions=[infer(g) for g in graphs]
    cpu_ns=time.process_time_ns()-cpu
    wall_ns=time.perf_counter_ns()-wall
    _,heap=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak=H.hwm_bytes()
    need(cpu_ns>0 and wall_ns>0 and peak>=before,"PHYSICAL_MEASUREMENT")
    row={"schema":SCHEMA,"arm":a.arm,"rep":a.rep,
        "platform":platform.platform(),"graphs":96,
        "source_sha256":hashlib.sha256(json.dumps(
            graphs,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
        "predictions_sha256":hashlib.sha256(json.dumps(
            predictions,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
        "max_cells":max(x[1] for x in predictions),
        "global_model_param_values":50 if a.arm=="trained_raw_neural" else (
            49 if a.arm=="untrained_raw_neural" else 0),
        "packed_33bit_first_edge_state":a.arm.endswith("raw_neural"),
        "original_cell_fields":3,"original_cell_limit":16,
        "edge_scans":(sum(x[2] for x in predictions) if
                      all(x[2] is not None for x in predictions) else None),
        "bit_compares":(sum(x[3] for x in predictions) if
                        all(x[3] is not None for x in predictions) else None),
        "RSS_before_bytes":before,"peak_process_RSS_bytes":peak,
        "peak_inference_Python_heap_bytes":heap,
        "cpu_ns":cpu_ns,"wall_ns":wall_ns}
    p=Path(a.output);need(not p.exists(),"OUTPUT_EXISTS")
    with p.open("x") as f:json.dump(row,f,sort_keys=True)
    print("F124AJ_PROCESS_"+a.arm+":wall_ns="+str(wall_ns)+
          ":rss="+str(peak),flush=True)
def bench(a):
    import f124aj_source as S
    S.frozen()
    conf=json.loads(S.PROTOCOL.read_text())["resources"]
    need(conf["arms"]==list(ARMS)
         and conf["graphs_per_trial"]==96
         and conf["repetitions"]==3,"FROZEN_RESOURCE_DESIGN_DRIFT")
    dst=Path(a.output)
    need(dst.parent.is_dir() and not dst.exists(),"FINAL_EVIDENCE_EXISTS")
    rows=[]
    for rep in range(3):
        for i in range(len(ARMS)):
            arm=ARMS[(i+rep)%len(ARMS)]
            out=dst.parent/("f124aj_resource_"+str(rep)+"_"+arm+".json")
            cmd=[sys.executable,"-B",__file__,"--worker",
                 "--rep",str(rep),"--arm",arm,
                 "--original-o",a.original_o,"--original-r",a.original_r,
                 "--original-s",a.original_s,"--original-u",a.original_u,
                 "--trained-receipt",a.trained_receipt,"--output",str(out)]
            ch=subprocess.run(cmd,text=True,capture_output=True,timeout=180,
                              env={**os.environ,"PYTHONHASHSEED":"0"})
            need(ch.returncode==0 and out.exists(),
                 "CHILD_FAILED_"+arm+":"+ch.stderr[-650:])
            z=json.loads(out.read_text())
            need(z["rep"]==rep and z["arm"]==arm and z["graphs"]==96,
                 "CHILD_IDENTITY")
            rows.append(z)
    need(len(rows)==18 and len({x["source_sha256"] for x in rows})==1,
         "SOURCE_MISMATCH_OR_INCOMPLETE_RUN")
    summaries={}
    for arm in ARMS:
        v=[x for x in rows if x["arm"]==arm]
        need(len(v)==3 and len({x["predictions_sha256"] for x in v})==1,
             "OUTPUT_NONDETERMINISTIC_"+arm)
        summaries[arm]={"repetitions":3,
            "median_wall_ns":int(statistics.median(x["wall_ns"] for x in v)),
            "median_cpu_ns":int(statistics.median(x["cpu_ns"] for x in v)),
            "median_peak_process_RSS_bytes":int(statistics.median(
                x["peak_process_RSS_bytes"] for x in v)),
            "median_Python_heap_bytes":int(statistics.median(
                x["peak_inference_Python_heap_bytes"] for x in v)),
            "max_original_cell_count":max(x["max_cells"] for x in v),
            "global_parameter_count":v[0]["global_model_param_values"],
            "packed_33bit_cell":v[0]["packed_33bit_first_edge_state"],
            "total_edge_scans":v[0]["edge_scans"],
            "total_bit_comparisons":v[0]["bit_compares"]}
    data={"schema":SCHEMA,"freeze_blob":S.PROTOCOL_BLOB,
        "platform":platform.platform(),"same_worker_per_OS":True,
        "source_equal_for_all_arms":True,"original_max_cells":16,
        "actual_process_RSS_not_assumed_equal":True,
        "larger_packed_state_counted":True,"extra_global_params_counted":True,
        "summary":summaries,"raw":rows,
        "protected_first_use":False,"science_accepted":False,
        "optimizer_promoted":False}
    raw=(json.dumps(data,sort_keys=True,indent=2)+"\n").encode()
    with dst.open("xb") as f:f.write(raw)
    print("F124AJ_RESOURCE_SHA256="+hashlib.sha256(raw).hexdigest(),flush=True)
    for arm,x in summaries.items():
        print("F124AJ_COST_"+arm+":rss="+str(x["median_peak_process_RSS_bytes"])+
              ":wall_ns="+str(x["median_wall_ns"])+
              ":cpu_ns="+str(x["median_cpu_ns"])+
              ":heap="+str(x["median_Python_heap_bytes"]),flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--worker",action="store_true")
    p.add_argument("--bench",action="store_true")
    p.add_argument("--rep",type=int,default=0)
    p.add_argument("--arm",choices=ARMS)
    for n in ("o","r","s","u"):p.add_argument("--original-"+n,required=True)
    p.add_argument("--trained-receipt",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    if a.worker:worker(a)
    elif a.bench:bench(a)
    else:p.error("choose --worker or --bench")
