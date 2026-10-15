"""FORGE F55: source-independent read-only FIT cohort recount and mechanism selection.

FIT observations can establish feasibility and an online-memory bottleneck,
not prospective scientific improvement or signed original acceptance.
"""
import argparse,hashlib,json
from pathlib import Path

class GateError(ValueError): pass
def require(ok,msg):
    if not ok:raise GateError("F55_"+msg)
def clean_pairs(pairs):
    o={}
    for k,v in pairs:
        require(k not in o,"DUPLICATE_JSON_KEY")
        o[k]=v
    return o
def load(path,max_size=4000000):
    raw=Path(path).read_bytes()
    require(0<len(raw)<max_size,"SOURCE_SIZE")
    return json.loads(raw,object_pairs_hook=clean_pairs),raw
def sha(raw):return hashlib.sha256(raw).hexdigest()
def verify_archive(folder,pin):
    root=Path(folder)
    doc,raw=load(root/pin["result"])
    require(sha(raw)==pin["result_sha256"],"DATA_HASH_DRIFT")
    require((root/"SOURCE_SHA").read_text().strip()==pin["sha"],"HEAD_DRIFT")
    lines=(root/"manifest.sha256").read_text().strip().splitlines()
    require(lines==[sha(raw)+"  "+pin["result"]],"MANIFEST_DRIFT")
    return doc

def check_identifiers(rows,seeds,families,lengths=None):
    seen=set()
    for row in rows:
        key=(row["seed"],row["family"])
        if lengths is not None:key=(*key,row["length"])
        require(key not in seen,"DUPLICATE_CASE")
        seen.add(key)
        require(seeds[0]<=row["seed"]<seeds[1] and row["family"] in families,
                "WRONG_FOLD")
        if lengths is not None:
            require(row["length"] in lengths,"UNEXPECTED_LENGTH")
    expected=(seeds[1]-seeds[0])*len(families)*(len(lengths) if lengths else 1)
    require(len(seen)==expected,"INCOMPLETE_COHORT")
def wingless(d):
    require(d["schema"]=="wingless.f55.public-role-source-feasibility.fit-only.v1"
       and d["frozen_fit_seeds"]==[601000,601016]
       and d["fit_families"]==[1100,1101,1102,1103]
       and d["train_fit_cases"]==128
       and d["disjoint_diagnostic_unused"] is True
       and d["originals_unused"] is True
       and d["native_576B_total_unverified"] is True,"W_AUTHORITY")
    rows=d["rows"]
    check_identifiers(rows,(601000,601016),(1100,1101,1102,1103),(6,8))
    count=sum(row["correct"] for row in rows)
    require(count==128 and d["public_constructive_correct"]==count
       and d["public_constructive_accuracy"]==count/128
       and d["eligible_for_future_learning_design"] is True
       and all(row["maps"]==4 and row["correct"]==1 for row in rows),
       "W_CONSTRUCTIVE_RECOUNT")
    return {"FIT_cases":128,"constructive_correct":count,"heldout_DIAG_used":False,
       "mechanism_priority":"LEARN_COMPACT_COMPOSITION_WITH_EXACT_PUBLIC_MAP_CONTROL",
       "not_scientific_gain":True}
def y_feasible(d):
    require(d["schema"]=="yggdrasil.f55.public-memory-constructive-fit-only.v1"
       and d["fit_seeds"]==[611000,611016]
       and d["fit_families"]==[1120,1121,1122,1123]
       and d["fit_streams"]==64
       and d["disjoint_DIAG_unused"] is True
       and d["originals_unused"] is True
       and d["future_question_never_used_by_witness"] is True
       and d["extra_public_offline_work_noncompetitive"] is True
       and d["native_576B_total_unverified"] is True,"Y_CONSTRUCTIVE_AUTHORITY")
    rows=d["rows"]
    check_identifiers(rows,(611000,611016),(1120,1121,1122,1123))
    count=sum(row["correct"] for row in rows)
    require(count==64 and d["public_reference_correct"]==count
       and d["public_reference_accuracy"]==1
       and d["memory_payload_bytes"]==144 and d["records"]==12
       and d["record_bytes"]==12
       and all(row["serialized_bytes"]==144 and row["work"]>0 for row in rows),
       "Y_CONSTRUCTIVE_RECOUNT")
    return {"FIT_cases":64,"constructive_correct":count,
       "offline_reference_extra_work":sum(x["work"] for x in rows),
       "online_feasibility_NOT_proven":True}
def y_online(d):
    require(d["schema"]=="yggdrasil.f55.fit-only.online-headroom.v1"
       and d["stage"]=="DISJOINT_WITHIN_FIT_TRAIN_AND_VALIDATION_NOT_DIAGNOSTIC"
       and d["fitting_seeds"]==[611000,611008]
       and d["fit_validation_seeds"]==[611008,611016]
       and d["registered_fit_families"]==[1120,1121,1122,1123]
       and d["fit_validation_cases"]==32
       and d["heldout_DIAG_untouched"] is True
       and d["originals_untouched"] is True
       and d["source_independent_F3"] is False
       and d["source_offline_reference_noncompetitive"] is True,"Y_FIT_ONLY")
    rows=d["rows"];check_identifiers(rows,(611008,611016),(1120,1121,1122,1123))
    expected={"learned_fit_global":1,"F54_frozen_global":3,"fixed_pair":3,
        "fixed_triple":3,"public_component":3,"public_DAG":3,
        "public_degree_FIFO":1,"public_hash":0,"public_full_graph_offline":32}
    totals={name:0 for name in expected};work=0
    for row in rows:
        require(set(row["online"])==set(expected)
           and set(row["payload_bytes"])==set(expected),"Y_ARM_SET")
        for arm,hit in row["online"].items():
            require(hit in (0,1) and row["payload_bytes"][arm]<=144
               and row["payload_bytes"][arm]>0,"Y_MEMORY_OR_RESULT")
            totals[arm]+=hit
        require(row["offline_extra_work"]>0,"Y_OFFLINE_WORK")
        work+=row["offline_extra_work"]
    require(totals==expected==d["correct"]
       and work==d["public_full_graph_offline_extra_work"]
       and d["fitting_examples"]>0
       and len(d["quantized_weight_codes"])==12,"Y_FIT_RECOUNT")
    return {"within_FIT_validation_cases":32,"learned_online_correct":1,
        "best_fixed_online_correct":3,"offline_constructive_correct":32,
        "online_memory_bottleneck_observed":True,
        "mechanism_priority":"INCREMENTAL_PUBLIC_COMPONENT_DISCOVERY_AND_LOSSLESS_8_HOP_COMPRESSION",
        "no_diagnostic_promotion":True}

def decide(directory,pins):
    require(set(pins)=={"Wingless","YggdrasilFeasibility","YggdrasilOnline"},
            "PIN_REGISTRY")
    seen=set();docs={}
    for study,pin in pins.items():
        require((pin["repo"],pin["run"],pin["artifact"]) not in seen,
                "DUPLICATE_FIRST_USE")
        seen.add((pin["repo"],pin["run"],pin["artifact"]))
        docs[study]=verify_archive(Path(directory)/study,pin)
    w=wingless(docs["Wingless"])
    yf=y_feasible(docs["YggdrasilFeasibility"])
    yo=y_online(docs["YggdrasilOnline"])
    return {"schema":"forge.f55.real-FIT-headroom-mechanism-intake.v1",
      "mode":"READ_ONLY_AUTOMATIC_MECHANISM_PRIORITY_FROM_AUTHENTIC_FIT_EVIDENCE",
      "Wingless":w,"Yggdrasil":{"public_feasibility":yf,"online_fit":yo},
      "candidate_priority":["Yggdrasil: incremental lossless path state, query blind, at most 144B",
        "Wingless: learned compositional state using proven public maps, equal-work controls"],
      "diagnostics_executed":0,"primary_originals_executed":0,
      "scientific_improvement_established":False,
      "dream_rsi_policy_prospective_gain_established":False,
      "theta_evolve_live_promotion_authorized":False,
      "experiment_dispatch_authorized":False,
      "separate_new_source_and_frozen_controls_required":True}
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--archive-root",required=True)
    ap.add_argument("--pins",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    pins,_=load(a.pins,50000)
    report=decide(a.archive_root,pins)
    Path(a.out).write_text(json.dumps(report,sort_keys=True,separators=(",",":"))+"\n")
