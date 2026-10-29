"""ACC35 cross-host native Go memory evidence and immutable 36-idea register audit."""
from __future__ import annotations
import argparse,json,math,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"research"/"acceleration"))
import acc34_scoreboard

SCHEMA="forge.acc35.acd3.native-go-reversible-history-sourcefree.v1"
NEG="ACC35_ACD3_NO_CROSSHOST_TOTAL_CPU_AND_STRONG_COMPRESSION_WIN"
POS="ACC35_ACD3_NATIVE_GO_SOURCEFREE_RESOURCE_POSITIVE_NOT_MODEL"

def check(r,host):
    if (not isinstance(r,dict) or r.get("schema")!=SCHEMA or r.get("candidate")!="AC-D3" or
        r.get("total_portfolio")!=36 or r.get("original_native_model_integrated") is not False or
        r.get("scientific_first_use") is not False or r.get("scientific_admission") is not False or
        r.get("os_peak_rss_measured") is not False or
        r.get("classification") not in (NEG,POS)):
        raise ValueError("ACC35_BAD_SOURCE_SCOPE_"+host)
    trials=r.get("trials")
    s=r.get("summaries")
    if not isinstance(trials,list) or len(trials)!=24 or not isinstance(s,list) or len(s)!=2:
        raise ValueError("ACC35_MISSING_24_COLD_WORKERS_"+host)
    expected={(env,rep,arm) for env in ("BENIGN","DELAYED") for rep in range(3)
              for arm in ("raw","radix","zlib","unsafe")}
    if {(v.get("scenario"),v.get("trial"),v.get("mode")) for v in trials}!=expected:
        raise ValueError("ACC35_WORKER_MATRIX_DRIFT_"+host)
    for t in trials:
        w=t["worker"]
        if (w.get("mode")!=t["mode"] or w.get("scenario")!=t["scenario"] or
            w.get("trial")!=t["trial"] or w.get("events")!=1024*16 or
            w.get("queries")!=512*16 or w.get("sessions")!=16 or
            not isinstance(w.get("snapshot_bytes"),int) or w["snapshot_bytes"]<=0 or
            not isinstance(w.get("digest"),str) or len(w["digest"])!=64 or
            not isinstance(t.get("cpu_seconds"),(int,float)) or t["cpu_seconds"]<=0 or
            not math.isfinite(t["cpu_seconds"]) or not isinstance(t.get("wall_seconds"),(int,float)) or
            t["wall_seconds"]<=0 or not math.isfinite(t["wall_seconds"])):
            raise ValueError("ACC35_BAD_WORKER_SOURCE_OR_CPU_"+host)
    positive=True
    for i,env in enumerate(("BENIGN","DELAYED")):
        x=s[i]
        if x["scenario"]!=env or x["exact_cold_restore"] is not True or x["radix_splits"]<=0:
            raise ValueError("ACC35_EXACT_MEMORY_OR_SPLIT_NOT_ESTABLISHED_"+host)
        for name in ("radix_cpu_over_raw","radix_bytes_over_raw","radix_bytes_over_zlib"):
            if not isinstance(x.get(name),(int,float)) or not math.isfinite(x[name]) or x[name]<=0:
                raise ValueError("ACC35_BAD_RESOURCE_RESULT_"+host)
        if (x["radix_cpu_over_raw"]>1.15 or x["radix_bytes_over_raw"]>0.75 or
            x["radix_bytes_over_zlib"]>1.0):
            positive=False
        if env=="DELAYED" and (x["unsafe_wrong"]<1 or x["late_contradictions"]<1):
            raise ValueError("ACC35_MISSING_DELayed_NEGATIVE_"+host)
        for rep in range(3):
            by={t["mode"]:t for t in trials if t["scenario"]==env and t["trial"]==rep}
            for mode in ("raw","radix","zlib"):
                if (by[mode]["worker"]["wrong"]!=0 or
                    by[mode]["worker"]["digest"]!=by["raw"]["worker"]["digest"]):
                    raise ValueError("ACC35_EXACT_RECALL_CHANGED_"+host)
    if r["classification"]!=(POS if positive else NEG):
        raise ValueError("ACC35_PREDECLARED_CLASSIFICATION_MISMATCH_"+host)
    return r

def cross(linux,windows):
    a=check(linux,"ubuntu")
    b=check(windows,"windows")
    # These source-free histories and returned answers are deterministic across OS.
    for q in ("BENIGN","DELAYED"):
        for rep in range(3):
            for mode in ("raw","radix","zlib","unsafe"):
                def digest(x):
                    return next(v["worker"]["digest"] for v in x["trials"]
                                if v["scenario"]==q and v["trial"]==rep and v["mode"]==mode)
                if digest(a)!=digest(b):
                    raise ValueError("ACC35_CROSSHOST_QUERY_DIGEST_DRIFT")
    ledger=acc34_scoreboard.scoreboard(run_full_screening=True)
    ids={r["claim_id"] for r in ledger["rows"]}
    if (len(ids)!=36 or ids!={*(f"U{x:02d}" for x in range(1,31)),
                              *(f"AC-D{x}" for x in range(1,7))} or
        ledger["stage2_qualified_native_model_speedups"]!=0 or
        ledger["hardware_substitutes_not_physical_results"]!=["U03","U06"] or
        ledger["separate_native_intelligence_gates_count_as_acceleration_wins"] is not False):
        raise ValueError("ACC35_ORIGINAL_PORTFOLIO_OR_SCIENCE_DRIFT")
    positive=a["classification"]==POS and b["classification"]==POS
    return {
        "schema":"forge.acc35.crosshost.original36-memory-acceleration-audit.v1",
        "all_36_portfolio_proposals_retained":True,
        "candidate":"AC-D3",
        "original_ACD1_negative_preserved":True,
        "strong_control_includes_zlib":True,
        "sourcefree_native_go_cold_worker_results":{"ubuntu":a["summaries"],"windows":b["summaries"]},
        "cross_host_classification":POS if positive else NEG,
        "original_native_model_speedup_established":False,
        "scientific_first_use":False,"scientific_admission":False,
        "protected_main_or_controller_modified":False
    }
if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("linux","windows","output"):p.add_argument("--"+k,required=True,type=pathlib.Path)
    args=p.parse_args()
    result=cross(json.loads(args.linux.read_text()),json.loads(args.windows.read_text()))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("ACC35_ACD3_CROSSHOST_ENGINEERING="+result["cross_host_classification"])
    print("ACC35_ALL_36_PRESERVED_AND_NO_NATIVE_MODEL_PROMOTION=PASS")
