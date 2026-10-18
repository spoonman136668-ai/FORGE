"""F124-AH measured same-host 7-arm noisy reasoning resource competition.

Original O/U (base and frozen combined), the original successful bounded
fixed exact16 and two preregistered tolerance/consistency fixed16 policies.
Each run evaluates EXACT 96 same-source graphs in a fresh process. Peak OS
RSS, Python tracemalloc peak, CPU and wall time retained for BOTH OS.
"""
from __future__ import annotations
import argparse,hashlib,json,os,platform,statistics,subprocess,sys,time,tracemalloc
from pathlib import Path

ARMS=("O_original","O_combined","U_original","U_combined",
      "untrained_fp","trained_fp","fixed_consistency16")
SCHEMA="forge.research.f124ah.cross-platform-seven-arm-real-cost.v1"

def need(ok,reason):
    if not ok:raise ValueError("F124AH_COST_"+reason)

def worker(a):
    import f124ah_source as S
    import f124ah_comparison as C
    import f124ah_learned_fingerprint as L
    import f124v_yggdrasil_causal_trace as V
    import f124v_wingless_hardware as H
    S.frozen()
    weights=V.original_weights(a.original_o,a.original_r,a.original_s,a.original_u)
    receipt=json.loads(Path(a.trained_receipt).read_text())
    need(receipt["schema"]==L.SCHEMA and receipt["freeze_blob"]==S.PROTOCOL_BLOB,
         "FIT_RECEIPT_SOURCE_DRIFT")
    trained=receipt["trained"];threshold=receipt["selected_threshold"]
    graphs=[]
    for v in S.VECTORS:
        for seed in S.COHORTS["delayed_noise"]["DEV"]:
            p,n=S.build("delayed_noise",seed,v,"DEV")
            graphs.extend((p,n))
    need(len(graphs)==96,"96_GRAPH_DENOMINATOR")
    forward=C.historical()
    def evaluate(g):
        if a.arm in ("untrained_fp","trained_fp","fixed_consistency16"):
            result=C.predict(a.arm,g,weights,trained,threshold)
            need(not result["blocked"],"UNEXECUTABLE_FINGERPRINT_OR_FIXED")
            return (bool(result["prediction"]),result["edge_scans"],
                    result["raw_bit_comparisons"],result["actual_cell_peak"])
        who,which=a.arm.split("_",1)
        kw={} if which=="original" else {"gamma":.1,"penalty":1.}
        result=forward(who,g,weights,**kw)
        return (result["logit_hex"],None,None,
                result["final_active"]+result["final_retained"])
    evaluate(graphs[0])
    before=H.hwm_bytes()
    tracemalloc.start();tracemalloc.reset_peak()
    t=time.perf_counter_ns();cpu=time.process_time_ns()
    outputs=[evaluate(g) for g in graphs]
    cpu_ns=time.process_time_ns()-cpu
    wall_ns=time.perf_counter_ns()-t
    _,heap=tracemalloc.get_traced_memory();tracemalloc.stop()
    peak=H.hwm_bytes()
    need(wall_ns>0 and cpu_ns>0 and peak>=before
         and all(v[3]<=16 for v in outputs),"INVALID_PHYSICAL_RESULT")
    result={"schema":SCHEMA,"arm":a.arm,"rep":a.rep,
       "platform":platform.platform(),"python":platform.python_version(),
       "cpu_count":os.cpu_count(),"graphs":96,
       "original_7_active_9_retained_max":16,
       "source_sha256":hashlib.sha256(json.dumps(
          graphs,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
       "output_sha256":hashlib.sha256(json.dumps(
          outputs,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
       "peak_cells":max(v[3] for v in outputs),
       "edge_scans":sum(v[1] for v in outputs)
           if all(v[1] is not None for v in outputs) else None,
       "raw_bit_compares":sum(v[2] for v in outputs)
           if all(v[2] is not None for v in outputs) else None,
       "preinference_peak_RSS_bytes":before,"process_peak_RSS_bytes":peak,
       "Python_inference_peak_bytes":heap,"wall_ns":wall_ns,"cpu_ns":cpu_ns}
    out=Path(a.output);need(not out.exists(),"OUTPUT_EXISTS")
    with out.open("x") as f:json.dump(result,f,sort_keys=True)
    print("F124AH_WORKER="+a.arm+":rss="+str(peak)+
          ":cpu_ns="+str(cpu_ns)+":wall_ns="+str(wall_ns),flush=True)

def bench(a):
    import f124ah_source as S
    S.frozen()
    conf=json.loads(S.PROTOCOL.read_text())["physical"]
    need(conf["arms"]==list(ARMS) and conf["family"]=="delayed_noise"
         and conf["cases"]==96 and conf["fresh_repetitions"]==3,
         "PRECOMMITTED_PHYSICAL_DESIGN_DRIFT")
    target=Path(a.output)
    need(target.parent.is_dir() and not target.exists(),"TARGET_EXISTS")
    raw=[]
    for rep in range(3):
        for i in range(len(ARMS)):
            arm=ARMS[(i+rep)%len(ARMS)]
            dest=target.parent/("f124ag_cost_"+str(rep)+"_"+arm+".json")
            cmd=[sys.executable,"-B",__file__,"--worker","--arm",arm,
                 "--rep",str(rep),"--original-o",a.original_o,
                 "--original-r",a.original_r,"--original-s",a.original_s,
                 "--original-u",a.original_u,"--trained-receipt",a.trained_receipt,
                 "--output",str(dest)]
            p=subprocess.run(cmd,text=True,capture_output=True,timeout=180,
                             env={**os.environ,"PYTHONHASHSEED":"0"})
            need(p.returncode==0 and dest.exists(),
                 "INCOMPLETE_PROCESS_"+arm+"_"+p.stderr[-500:])
            row=json.loads(dest.read_text())
            need(row["rep"]==rep and row["arm"]==arm and row["graphs"]==96,
                 "CHILD_IDENTITY")
            raw.append(row)
    need(len(raw)==21 and len({z["source_sha256"] for z in raw})==1,
         "UNMATCHED_OR_INCOMPLETE_SOURCE")
    summaries={}
    for arm in ARMS:
        rows=[x for x in raw if x["arm"]==arm]
        need(len(rows)==3 and len({x["output_sha256"] for x in rows})==1,
             "NONDETERMINISTIC_REPLAY_"+arm)
        summaries[arm]={"repetitions":3,
         "median_wall_ns":int(statistics.median(r["wall_ns"] for r in rows)),
         "median_cpu_ns":int(statistics.median(r["cpu_ns"] for r in rows)),
         "median_process_RSS_bytes":int(statistics.median(
                  r["process_peak_RSS_bytes"] for r in rows)),
         "median_Python_peak_bytes":int(statistics.median(
                  r["Python_inference_peak_bytes"] for r in rows)),
         "max_persistent_cell_entries":max(r["peak_cells"] for r in rows),
         "edge_scans":rows[0]["edge_scans"],
         "raw_bit_compares":rows[0]["raw_bit_compares"],
         "model_output_sha256":rows[0]["output_sha256"]}
    report={"schema":SCHEMA,"freeze_blob":S.PROTOCOL_BLOB,
      "three_new_process_repetitions":True,"same_OS_host":True,
      "same_identical_96_graphs":True,
      "unchanged_fitted_O_U_weights":True,
      "unchanged_f124ad_gamma_penalty":True,
      "process_RSS_not_assumed_equal":True,"CPU_not_assumed_equal":True,
      "persistent_cell_upper_bound":16,"platform":platform.platform(),
      "summary":summaries,"raw":raw,
      "protected_first_use":False,"science_accepted":False,
      "optimizer_promoted":False}
    data=(json.dumps(report,sort_keys=True,indent=2)+"\n").encode()
    with target.open("xb") as f:f.write(data)
    print("F124AH_RESOURCE_SHA256="+hashlib.sha256(data).hexdigest(),flush=True)
    for arm,s in summaries.items():
        print("F124AH_COST_"+arm+":RSS="+str(s["median_process_RSS_bytes"])+
              ":wall_ns="+str(s["median_wall_ns"])+
              ":cpu_ns="+str(s["median_cpu_ns"])+
              ":heap="+str(s["median_Python_peak_bytes"]),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--worker",action="store_true")
    p.add_argument("--bench",action="store_true")
    p.add_argument("--arm",choices=ARMS)
    p.add_argument("--rep",type=int,default=0)
    for k in ("o","r","s","u"):p.add_argument("--original-"+k,required=True)
    p.add_argument("--trained-receipt",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    if a.worker:worker(a)
    elif a.bench:bench(a)
    else:p.error("choose worker or bench")
