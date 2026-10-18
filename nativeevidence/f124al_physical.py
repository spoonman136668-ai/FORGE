"""F124-AL same-OS-worker four-arm source-identical physical RSS/CPU/wall/heap.

Original AK model/threshold loaded read-only via verified original FIT
artifact. Capacity only <=16 original cell fields; the 39 globals and packed
score scalar are separately acknowledged, never called byte/computation parity.
"""
import argparse,hashlib,json,os,platform,statistics,subprocess,sys,time,tracemalloc
from pathlib import Path

ARMS=("ak_original_frozen","fixed_consistency16","fixed_collisionfree",
      "fixed_generalized_mask")
SCHEMA="forge.research.f124al.real-total-transfer-cost.v1"

def need(ok,msg):
    if not ok:raise ValueError("F124AL_COST_"+msg)
def worker(a):
    import f124al_transfer_source as S
    import f124al_transfer as T
    import f124v_wingless_hardware as Hardware
    S.frozen()
    original=T.load_receipt(a.original_ak_receipt)
    graphs=[]
    for vector in S.VECTORS:
        for seed in S.COHORTS["three_events"]["DEV"]:
            pos,neg=S.build("three_events",seed,vector,"DEV")
            graphs.extend((pos,neg))
    need(len(graphs)==96,"FROZEN_96_SOURCE")
    model=original["trained"]["model"]
    threshold=original["selected_threshold"]
    def observe(g):
        r=T.predict(a.arm,g,model,threshold)
        cells=r.get("actual_cell_peak",0)
        need(not r.get("blocked",False) and cells<=16,
             "BUDGET_OR_UNKNOWN_ARM")
        return (bool(r["prediction"]),cells,r.get("edge_scans"),
                r.get("raw_bit_comparisons",r.get("bit_comparisons")),
                r.get("score_packed_mask_event_count",False))
    observe(graphs[0])
    before=Hardware.hwm_bytes()
    tracemalloc.start();tracemalloc.reset_peak()
    t=time.perf_counter_ns();cpu=time.process_time_ns()
    allresults=[observe(g) for g in graphs]
    cpu_ns=time.process_time_ns()-cpu
    wall_ns=time.perf_counter_ns()-t
    _,heap=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rss=Hardware.hwm_bytes()
    need(wall_ns>0 and cpu_ns>0 and rss>=before,
         "OS_RESOURCE_WITNESS_INVALID")
    result={"schema":SCHEMA,"arm":a.arm,"rep":a.rep,
      "platform":platform.platform(),"cases":96,
      "source_sha256":hashlib.sha256(json.dumps(
          graphs,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
      "predictions_sha256":hashlib.sha256(json.dumps(
          allresults,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
      "actual_peak_cells":max(x[1] for x in allresults),
      "full_AK_global_model_parameters":39 if a.arm=="ak_original_frozen" else 0,
      "original_three_cell_fields":True,
      "integer_packed_score_payload":a.arm in (
           "ak_original_frozen","fixed_generalized_mask"),
      "public_edge_scans":sum(x[2] for x in allresults)
             if all(x[2] is not None for x in allresults) else None,
      "raw_bit_comparisons":sum(x[3] for x in allresults)
             if all(x[3] is not None for x in allresults) else None,
      "pre_inference_RSS_bytes":before,
      "process_peak_RSS_bytes":rss,"Python_inference_peak_bytes":heap,
      "cpu_ns":cpu_ns,"wall_ns":wall_ns}
    p=Path(a.output);need(not p.exists(),"PROCESS_RECEIPT_EXISTS")
    with p.open("x") as f:json.dump(result,f,sort_keys=True)
    print("F124AL_WORKER_"+a.arm+":rss="+str(rss)+
          ":wall="+str(wall_ns),flush=True)
def bench(a):
    import f124al_transfer_source as S
    S.frozen()
    protocol=json.loads(S.PROTOCOL.read_text())["physical"]
    need(protocol["arms"]==list(ARMS) and protocol["graphs"]==96
         and protocol["new_process_repetitions"]==3,
         "FROZEN_RESOURCE_PROTOCOL_CHANGED")
    target=Path(a.output)
    need(target.parent.is_dir() and not target.exists(),"FINAL_RECEIPT_EXISTS")
    observations=[]
    for rep in range(3):
        for i in range(len(ARMS)):
            arm=ARMS[(i+rep)%len(ARMS)]
            p=target.parent/("f124al_"+str(rep)+"_"+arm+".json")
            args=[sys.executable,"-B",__file__,"--worker","--rep",str(rep),
                  "--arm",arm,"--original-ak-receipt",a.original_ak_receipt,
                  "--output",str(p)]
            proc=subprocess.run(args,text=True,capture_output=True,timeout=180,
                     env={**os.environ,"PYTHONHASHSEED":"0"})
            need(proc.returncode==0 and p.exists(),
                 "SUBPROCESS_"+arm+":"+proc.stderr[-450:])
            d=json.loads(p.read_text())
            need(d["rep"]==rep and d["arm"]==arm and d["cases"]==96,
                 "SUBPROCESS_WRONG_DENOMINATOR")
            observations.append(d)
    need(len(observations)==12 and
         len({x["source_sha256"] for x in observations})==1,
         "NOT_SOURCE_IDENTICAL")
    summary={}
    for arm in ARMS:
        group=[x for x in observations if x["arm"]==arm]
        need(len(group)==3 and
             len({x["predictions_sha256"] for x in group})==1,
             "NO_DETERMINISTIC_REPLAY_"+arm)
        summary[arm]={"repetitions":3,
          "median_wall_ns":int(statistics.median(x["wall_ns"] for x in group)),
          "median_cpu_ns":int(statistics.median(x["cpu_ns"] for x in group)),
          "median_RSS_peak_bytes":int(statistics.median(
              x["process_peak_RSS_bytes"] for x in group)),
          "median_Python_heap_peak_bytes":int(statistics.median(
              x["Python_inference_peak_bytes"] for x in group)),
          "max_original_cells":max(x["actual_peak_cells"] for x in group),
          "global_parameter_count":group[0]["full_AK_global_model_parameters"],
          "public_edge_scans":group[0]["public_edge_scans"],
          "raw_bit_comparisons":group[0]["raw_bit_comparisons"]}
    report={"schema":SCHEMA,"freeze_blob":S.PROTOCOL_BLOB,
      "host_OS":platform.platform(),"same_OS_host_across_arms":True,
      "all_arms_same_96_graphs":True,"fresh_repetitions_per_arm":3,
      "original_cell_count_maximum":16,
      "equal_total_RAM_and_compute_NOT_assumed":True,
      "global_parameters_accounted":True,"score_payload_type_accounted":True,
      "summary":summary,"raw":observations,
      "protected_first_use":False,"science_accepted":False,
      "optimizer_promoted":False}
    b=(json.dumps(report,sort_keys=True,indent=2)+"\n").encode()
    with target.open("xb") as f:f.write(b)
    print("F124AL_RESOURCE_SHA256="+hashlib.sha256(b).hexdigest(),flush=True)
    for arm,r in summary.items():
        print("F124AL_COST_"+arm+
           ":RSS="+str(r["median_RSS_peak_bytes"])+
           ":WALL="+str(r["median_wall_ns"])+
           ":CPU="+str(r["median_cpu_ns"])+
           ":HEAP="+str(r["median_Python_heap_peak_bytes"]),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--worker",action="store_true")
    p.add_argument("--bench",action="store_true")
    p.add_argument("--arm",choices=ARMS)
    p.add_argument("--rep",type=int,default=0)
    p.add_argument("--original-ak-receipt",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    if a.worker:worker(a)
    elif a.bench:bench(a)
    else:p.error("choose --worker or --bench")
