"""F127-R immutable saved-weight, same-run public TRAIN_CHECK cost diagnostic.

Source freeze did not predefine a common event tariff: collect original named
events and wall clock, but NEVER declare homogeneous-cost superiority.
"""
import argparse,hashlib,json,math,statistics,time
from collections import defaultdict
from pathlib import Path
import f120_generated_environment as sources
import f127r_train_environment as env
import f127r_calibrated_model as model
import f127r_freeze_admission as freeze

SCHEMA="forge.research.f127r.saved-weight-cost-audit.v1"
SAVED_SHA="6ff85a82acca1fb0f57495c277fd5ed764670c9e"
REPORT_HASH="7e784f77a78aa0e7def04fcb8024b69a9ec392e6a13a720924dbe78d40528a45"
def need(ok,reason):env.need(bool(ok),"COST_"+reason)
def exact_indexed(g):
    """Use indexed public edges, not the earlier deliberately full-scan oracle."""
    env.validate(g)
    table=defaultdict(list)
    for e in g["edges"]:table[(e["from"],e["role"])].append(e)
    work={"indexed_edges":len(g["edges"]),"edge_visits":0,
          "bit_comparisons":0,"state_allocations":0,"state_peak":1}
    states=[(g["start"],None)]
    for role in g["roles"]:
        nxt=[]
        for node,token in states:
            for e in table.get((node,role),()):
                work["edge_visits"]+=1
                if token is not None:
                    work["bit_comparisons"]+=16
                    if token!=e["src_bits"]:continue
                nxt.append((e["to"],e["dst_bits"]))
                work["state_allocations"]+=1
        states=nxt
        work["state_peak"]=max(work["state_peak"],len(states))
    return int(any(node==g["target"] for node,token in states)),work

def bench(report,advisory):
    freeze.frozen()
    need(report["source_sha"]==SAVED_SHA and
         report["schema"]=="forge.research.f127r.fit-train-check-controls.v1"
         and report["frozen_blob"]==freeze.FREEZE_BLOB and
         report["protected_CONFIRM_read"] is False,"AUTHENTIC_SAVED_SOURCE")
    candidates=sources.validate(advisory,SAVED_SHA)
    lanes=[]
    for prior in report["lanes"]:
        name=prior["lane"]
        rows=env.cohort_rows(name,[r["vector"] for r in candidates[name]],
                             "TRAIN_CHECK")
        weights=prior["weights"]
        need(len(rows)==64 and len(weights)==22 and
             env.digest(rows)==prior["TRAIN_CHECK_sha256"] and
             env.digest(weights)==prior["weights_sha256"],"UNMODIFIED_DATA")
        for graph,y in rows:
            need(exact_indexed(graph)[0]==y,"REFERENCE_DISAGREES")
        graphs=[graph for graph,y in rows]
        def learned():return [model.forward(g,weights)[0] for g in graphs]
        def exact():return [exact_indexed(g)[0] for g in graphs]
        for i in range(5):learned();exact()
        durations={"learned":[],"indexed_exact":[]}
        for i in range(30):
            pair=(("learned",learned),("indexed_exact",exact))
            if i%2:pair=tuple(reversed(pair))
            for key,fn in pair:
                start=time.perf_counter_ns()
                result=fn()
                durations[key].append(time.perf_counter_ns()-start)
                need(len(result)==64,"DENOMINATOR")
        measured_model,measured_exact={},{}
        for g in graphs:
            _,_,trace=model.forward(g,weights,True)
            _,reference=exact_indexed(g)
            for k,v in trace["work"].items():
                measured_model[k]=measured_model.get(k,0)+v
            for k,v in reference.items():
                measured_exact[k]=measured_exact.get(k,0)+v
        a=statistics.median(durations["learned"])
        b=statistics.median(durations["indexed_exact"])
        ratio=a/max(1,b)
        lanes.append({"lane":name,"graphs":64,"warm_passes":5,
          "interleaved_passes":30,"alternating_order":True,
          "weights_sha256":env.digest(weights),
          "train_check_sha256":env.digest(rows),
          "learned_median_ns":a,"indexed_exact_median_ns":b,
          "learned_p95_ns":sorted(durations["learned"])[28],
          "indexed_exact_p95_ns":sorted(durations["indexed_exact"])[28],
          "median_walltime_ratio":round(ratio,6),
          "frozen_walltime_ratio_limit":.75,
          "passes_walltime_requirement":ratio<=.75,
          "learner_operation_classes":measured_model,
          "indexed_exact_operation_classes":measured_exact,
          "common_event_tariff_precommitted":False,
          "resource_superiority_qualified":False})
    need([x["lane"] for x in lanes]==["Wingless","Yggdrasil"],"BOTH_LANES")
    return {"schema":SCHEMA,"source_sha":SAVED_SHA,"lanes":lanes,
      "original_report_sha256":REPORT_HASH,
      "scope":"SAVED_PUBLIC_TRAIN_CHECK_COST_ONLY",
      "protected_CONFIRM_read":False,"weights_updated":False,
      "scientific_first_use":False,"scientific_acceptance":False,
      "optimizer_promotion":False,"cost_superiority_established":False}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--report",required=True)
    parser.add_argument("--advisory",required=True)
    parser.add_argument("--output",required=True)
    a=parser.parse_args()
    data=Path(a.report).read_bytes()
    need(hashlib.sha256(data).hexdigest()==REPORT_HASH,"RECEIPT_DIGEST")
    out=bench(json.loads(data),json.loads(Path(a.advisory).read_text()))
    destination=Path(a.output)
    need(destination.parent.is_dir() and not destination.exists(),
         "NO_OVERWRITE")
    raw=(json.dumps(out,sort_keys=True,separators=(",",":"))+"\n").encode()
    destination.open("xb").write(raw)
    print("F127R_COST_SHA256="+hashlib.sha256(raw).hexdigest())
    for x in out["lanes"]:
        print("F127R_"+x["lane"].upper()+"_RATIO="+
              str(x["median_walltime_ratio"]))
    print("F127R_HOMOGENEOUS_COST_SUCCESS=false")
if __name__=="__main__":main()
