"""F124-AN 3-arm fresh-process physical total model memory and CPU.

Each OS evaluates SAME 96 public inputs: 24 resolvable POS, 24 NEG,
and 48 identical-observation ambiguous cases in repeated-role family.
Measure actual process OS RSS, Python heap, CPU/wall, packed-state bits,
original 16 persistent cells, learned total global params 16.
"""
from __future__ import annotations
import argparse,hashlib,json,os,platform,statistics,subprocess,sys,time,tracemalloc
from pathlib import Path
ARMS=("fixed_triage","trained_abstain","untrained_abstain")
SCHEMA="forge.research.f124an.same-host-full-physical.v1"
def need(ok,desc):
    if not ok:raise ValueError("F124AN_COST_"+desc)
def worker(a):
    import f124an_observable_source as S
    import f124an_identifiability as M
    import f124v_wingless_hardware as Hardware
    S.frozen()
    receipt=json.loads(Path(a.trained_receipt).read_text())
    need(receipt["schema"]==M.SCHEMA and
         receipt["freeze_blob"]==S.PROTOCOL_BLOB and
         receipt["no_DEV_training_or_threshold_selection"],
         "ORIGINAL_FIT_LOCK")
    graph_inputs=[]
    for v in S.VECTORS:
        for seed in S.COHORTS["role_repeat_mask"]["DEV"]:
            d=S.build("role_repeat_mask",seed,v,"DEV")
            graph_inputs.append(d["ambiguous_public"])
            if seed%2==0:graph_inputs.append(d["positive"])
            else:graph_inputs.append(d["negative"])
    need(len(graph_inputs)==96,"SOURCE_96")
    def act(g):
        obs=M.observe(g)
        if a.arm=="fixed_triage":
            label,_=M.decide(obs,None,0.,"fixed")
        elif a.arm=="trained_abstain":
            label,_=M.decide(obs,receipt["training"]["model"],
                                receipt["selected_threshold"],"trained")
        else:
            label,_=M.decide(obs,receipt["training"]["initial"],.5,"untrained")
        need(obs["cell_peak"]<=16 and label in M.LABELS,
             "CELL_OR_TRIAGE")
        return (label,obs["cell_peak"],obs["edge_scans"],
                obs["raw_bit_ops"],obs["packed_score_bits"])
    act(graph_inputs[0])
    before=Hardware.hwm_bytes()
    tracemalloc.start();tracemalloc.reset_peak()
    wall=time.perf_counter_ns();cpu=time.process_time_ns()
    pred=[act(g) for g in graph_inputs]
    CPU=time.process_time_ns()-cpu
    wall_ns=time.perf_counter_ns()-wall
    _,heap=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak=Hardware.hwm_bytes()
    need(CPU>0 and wall_ns>0 and peak>=before,"REAL_OS_WITNESS")
    out={"schema":SCHEMA,"arm":a.arm,"rep":a.rep,
      "OS":platform.platform(),"cases":96,
      "source_sha256":hashlib.sha256(json.dumps(
         graph_inputs,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
      "output_sha256":hashlib.sha256(json.dumps(
         pred,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
      "max_original_cells":max(v[1] for v in pred),
      "maximum_integer_score_bits":max(v[4] for v in pred),
      "global_params":16 if a.arm!="fixed_triage" else 0,
      "edge_scans":sum(v[2] for v in pred),
      "raw_bit_ops":sum(v[3] for v in pred),
      "before_RSS_bytes":before,"peak_process_RSS_bytes":peak,
      "Python_inference_heap_peak_bytes":heap,
      "CPU_ns":CPU,"wall_ns":wall_ns}
    path=Path(a.output);need(not path.exists(),"PROCESS_ALREADY_RUN")
    with path.open("x") as f:json.dump(out,f,sort_keys=True)
    print("F124AN_PROCESS_"+a.arm+":rss="+str(peak)+
          ":wall="+str(wall_ns),flush=True)
def benchmark(a):
    import f124an_observable_source as S
    S.frozen()
    conf=json.loads(S.PROTOCOL.read_text())["hardware"]
    need(conf["arms"]==list(ARMS) and
         conf["fixed_96_public_cases"] and conf["repetitions"]==3,
         "PREREGISTERED_RESOURCE_CONTRACT")
    dest=Path(a.output)
    need(dest.parent.is_dir() and not dest.exists(),"FINAL_EVIDENCE_ALREADY_EXISTS")
    collected=[]
    for rep in range(3):
        for i in range(len(ARMS)):
            arm=ARMS[(i+rep)%len(ARMS)]
            out=dest.parent/("f124an_resource_"+str(rep)+"_"+arm+".json")
            cmd=[sys.executable,"-B",__file__,"--worker","--arm",arm,
                 "--rep",str(rep),"--trained-receipt",a.trained_receipt,
                 "--output",str(out)]
            child=subprocess.run(cmd,text=True,capture_output=True,timeout=180,
                                 env={**os.environ,"PYTHONHASHSEED":"0"})
            need(child.returncode==0 and out.exists(),
                 "SUBPROCESS_"+arm+":"+child.stderr[-600:])
            row=json.loads(out.read_text())
            need(row["rep"]==rep and row["arm"]==arm and row["cases"]==96,
                 "REPEAT_IDENTITY")
            collected.append(row)
    need(len(collected)==9 and
         len({x["source_sha256"] for x in collected})==1,
         "PUBLIC_SOURCE_CHANGED_AMONG_ARMS")
    summary={}
    for arm in ARMS:
        same=[x for x in collected if x["arm"]==arm]
        need(len(same)==3 and len({x["output_sha256"] for x in same})==1,
             "NONDETERMINISTIC_REPLAY_"+arm)
        summary[arm]={"repetitions":3,
          "median_wall_ns":int(statistics.median(x["wall_ns"] for x in same)),
          "median_CPU_ns":int(statistics.median(x["CPU_ns"] for x in same)),
          "median_process_peak_RSS_bytes":int(statistics.median(
                 x["peak_process_RSS_bytes"] for x in same)),
          "median_Python_heap_peak_bytes":int(statistics.median(
                 x["Python_inference_heap_peak_bytes"] for x in same)),
          "max_original_cells":max(x["max_original_cells"] for x in same),
          "maximum_integer_score_bits":max(x["maximum_integer_score_bits"] for x in same),
          "global_model_params":same[0]["global_params"],
          "edge_scans":same[0]["edge_scans"],"bit_operations":same[0]["raw_bit_ops"]}
    record={"schema":SCHEMA,"freeze_blob":S.PROTOCOL_BLOB,
       "OS":platform.platform(),"identical_public_graphs_all_arms":True,
       "same_worker_per_OS":True,"fresh_processes_per_arm":3,
       "original_cell_cap":16,"total_memory_compute_not_assumed_equal":True,
       "new_global_params_counted":True,"packed_score_integer_bytes_tracked":True,
       "summary":summary,"raw":collected,
       "protected_first_use":False,"independent_science_accepted":False,
       "optimizer_promoted":False}
    raw=(json.dumps(record,sort_keys=True,indent=2)+"\n").encode()
    with dest.open("xb") as f:f.write(raw)
    print("F124AN_RESOURCE_SHA256="+hashlib.sha256(raw).hexdigest(),flush=True)
    for arm,z in summary.items():
        print("F124AN_COST_"+arm+":wall_ns="+str(z["median_wall_ns"])+
              ":rss="+str(z["median_process_peak_RSS_bytes"])+
              ":cpu_ns="+str(z["median_CPU_ns"])+
              ":heap="+str(z["median_Python_heap_peak_bytes"]),flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--worker",action="store_true")
    p.add_argument("--bench",action="store_true")
    p.add_argument("--arm",choices=ARMS)
    p.add_argument("--rep",type=int,default=0)
    p.add_argument("--trained-receipt",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    if a.worker:worker(a)
    elif a.bench:benchmark(a)
    else:p.error("choose --worker or --bench")
