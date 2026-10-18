"""F124-AE measured same-worker physical memory, wall and CPU cost.

Exactly fixed F124-AD coefficients, source-distinct rekey and near-break DEV
graphs; 3 fresh processes per family/O-U/unchanged-combined arm, all on the
same OS GitHub runner. Process peak RSS is observed rather than assumed from
the 16 persistent cell count.
"""
from __future__ import annotations
import argparse,hashlib,json,os,platform,statistics,subprocess,sys,time,tracemalloc
from pathlib import Path

ARMS=("O_original","O_combined","U_original","U_combined")
FAMILIES=("rekey","near_break")
SCHEMA="forge.research.f124ae.cross-platform-matched-physical-cost.v1"

def need(ok,why):
    if not ok:raise ValueError("F124AE_COST_"+why)

def worker(a):
    import f124ae_source as source
    import f124ad_intermediate_credit as AD
    import f124v_yggdrasil_causal_trace as V
    import f124v_wingless_hardware as hardware
    source.frozen()
    need(a.family in FAMILIES and a.arm in ARMS,"FAMILY_ARM")
    weights=V.original_weights(a.original_o,a.original_r,a.original_s,a.original_u)
    graphs=[]
    for vector in source.VECTORS:
        for seed in source.COHORTS["AE_"+a.family]["DEV"]:
            pos,neg=source.transfer_pair(seed,vector,"DEV",a.family)
            graphs.extend((pos,neg))
    need(len(graphs)==96,"EXACT_INPUT_96")
    arm,variant=a.arm.split("_",1)
    kw={} if variant=="original" else {"gamma":.1,"penalty":1.}
    AD.forward(arm,graphs[0],weights,**kw)
    pre=hardware.hwm_bytes()
    tracemalloc.start();tracemalloc.reset_peak()
    t=time.perf_counter_ns();cpu=time.process_time_ns()
    scores=[AD.forward(arm,g,weights,**kw)["logit_hex"] for g in graphs]
    cpu_ns=time.process_time_ns()-cpu
    wall_ns=time.perf_counter_ns()-t
    _,heap=tracemalloc.get_traced_memory();tracemalloc.stop()
    peak=hardware.hwm_bytes()
    need(wall_ns>0 and cpu_ns>0 and peak>=pre,"UNTRUSTWORTHY_RESOURCE_COUNTER")
    record={"schema":SCHEMA,"family":a.family,"arm":a.arm,"rep":a.rep,
        "platform":platform.platform(),"python":platform.python_version(),
        "machine":platform.machine(),"cpu_count":os.cpu_count(),
        "source_cases":96,"original_model_weights_unchanged":True,
        "original_7active_9retained_cells":True,
        "FIT_selected_gamma":0 if variant=="original" else .1,
        "FIT_selected_penalty":0 if variant=="original" else 1.,
        "source_sha256":hashlib.sha256(json.dumps(
           graphs,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
        "model_logit_sha256":hashlib.sha256(json.dumps(
           scores,separators=(",",":")).encode()).hexdigest(),
        "preinference_peak_RSS_bytes":pre,
        "actual_process_peak_RSS_bytes":peak,
        "inference_peak_Python_alloc_bytes":heap,
        "wall_ns":wall_ns,"cpu_ns":cpu_ns}
    output=Path(a.output)
    need(not output.exists(),"OUTPUT_EXISTS")
    with output.open("x") as f:json.dump(record,f,sort_keys=True)
    print("F124AE_WORKER="+a.family+":"+a.arm+":RSS="+str(peak)+
          ":WALL="+str(wall_ns),flush=True)

def bench(a):
    import f124ae_source as source
    source.frozen()
    p=json.loads(source.PROTOCOL.read_text())
    need(p["resource_trial"]["source_families"]==list(FAMILIES)
         and p["resource_trial"]["arms"]==list(ARMS)
         and p["resource_trial"]["repetitions_per_arm_family"]==3,
         "FROZEN_RESOURCE_DESIGN_MISMATCH")
    dest=Path(a.output)
    need(dest.parent.is_dir() and not dest.exists(),"OUTPUT_EXCLUSIVE")
    data=[]
    for family in FAMILIES:
        for rep in range(3):
            for k in range(4):
                arm=ARMS[(k+rep)%4]
                out=dest.parent/("f124ae_cost_"+family+"_"+str(rep)+"_"+arm+".json")
                cmd=[sys.executable,"-B",__file__,"--worker",
                     "--family",family,"--arm",arm,"--rep",str(rep),
                     "--original-o",a.original_o,"--original-r",a.original_r,
                     "--original-s",a.original_s,"--original-u",a.original_u,
                     "--output",str(out)]
                child=subprocess.run(cmd,text=True,capture_output=True,timeout=160,
                                     env={**os.environ,"PYTHONHASHSEED":"0"})
                need(child.returncode==0 and out.exists(),
                     "FRESH_SUBPROCESS_"+family+"_"+arm+"_"+child.stderr[-700:])
                row=json.loads(out.read_text())
                need(row["arm"]==arm and row["family"]==family and row["rep"]==rep
                     and row["source_cases"]==96,"CORRUPTED_SOURCE_RECEIPT")
                data.append(row)
    need(len(data)==24,"COMPLETE_24_REPS")
    results={}
    for family in FAMILIES:
        group=[row for row in data if row["family"]==family]
        need(len({row["source_sha256"] for row in group})==1,
             "MISMATCHED_PUBLIC_INPUTS")
        results[family]={}
        for arm in ARMS:
            rows=[row for row in group if row["arm"]==arm]
            need(len(rows)==3 and len({r["model_logit_sha256"]
                                       for r in rows})==1,
                 "NONDETERMINISTIC_HISTORICAL_MODEL_"+arm)
            results[family][arm]={
              "repetitions":3,
              "median_process_peak_RSS_bytes":int(statistics.median(
                 r["actual_process_peak_RSS_bytes"] for r in rows)),
              "median_inference_Python_heap_bytes":int(statistics.median(
                 r["inference_peak_Python_alloc_bytes"] for r in rows)),
              "median_wall_ns":int(statistics.median(r["wall_ns"] for r in rows)),
              "median_cpu_ns":int(statistics.median(r["cpu_ns"] for r in rows)),
              "model_output_sha256":rows[0]["model_logit_sha256"]}
    receipt={"schema":SCHEMA,"freeze_blob":source.PROTOCOL_BLOB,
      "independently_salted":True,"same_runner_per_platform":True,
      "source_input_equal_in_family":True,"all_processes_fresh":True,
      "original_7active_9retained_cells":True,
      "not_a_universal_equal_RAM_or_CPU_claim":True,
      "platform":platform.platform(),"results":results,"raw":data,
      "protected_first_use":False,"science_accepted":False,
      "optimizer_promoted":False}
    raw=(json.dumps(receipt,sort_keys=True,indent=2)+"\n").encode()
    with dest.open("xb") as f:f.write(raw)
    print("F124AE_COST_SHA256="+hashlib.sha256(raw).hexdigest(),flush=True)
    for family,x in results.items():
        for arm,r in x.items():
            print("F124AE_COST_"+family+"_"+arm+
              ":RSS="+str(r["median_process_peak_RSS_bytes"])+
              ":heap="+str(r["median_inference_Python_heap_bytes"])+
              ":wall_ns="+str(r["median_wall_ns"])+
              ":cpu_ns="+str(r["median_cpu_ns"]),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--worker",action="store_true")
    p.add_argument("--bench",action="store_true")
    p.add_argument("--family",choices=FAMILIES)
    p.add_argument("--arm",choices=ARMS)
    p.add_argument("--rep",type=int,default=0)
    for n in ("o","r","s","u"):p.add_argument("--original-"+n,required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    if a.worker:worker(a)
    elif a.bench:bench(a)
    else:p.error("choose worker or bench")
