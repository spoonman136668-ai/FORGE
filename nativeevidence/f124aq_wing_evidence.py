"""F124-AQ authentic frozen Wingless first-use evaluator and TRAIN preflight.

Protected scientific holdouts are not used. The prospective DEV source is
constructed only when --mode dev is explicitly selected by the separately
qualified one-time workflow. Original Yggdrasil DEV stays unconsumed.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,math,os,platform,statistics,sys,time,tracemalloc
from pathlib import Path
import f124aq_train_source as s
import f124aq_wing_first_dev_source as devsource
import f124aq_local_contrast as new
import f124aq_train_selection as prev
import f124am_terminal_competition as original
import f124al_packed_confidence as cap
import f124ae_scoring_transfer as prior
import f124q_independent_binding as q

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124aq-posttrain-selected-wing-dev.json"
FREEZE_BLOB="e60bd99d881ba213a9ad2f65750fa486bff2ebc4"
TRAIN_RAW="d3a3935cc58d0fe69f46a496ae130a434360bee4169dc22bdad72385af3aa5b0"
SCHEMA="forge.research.f124aq.verified-single-wing-first-dev-evidence.v1"

def need(ok,tag):s.need(ok,"EVIDENCE_"+tag)

def lineage(o,t,an,ao,ap,aq):
    s.frozen()
    need(s.witness.blob(FREEZE)==FREEZE_BLOB,"PARAMETERS_PREDEV_FROZEN")
    freeze=json.loads(FREEZE.read_text(encoding="utf-8"))
    raw=Path(aq).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==TRAIN_RAW,"ORIGINAL_AQ_RAW")
    r=json.loads(raw)
    need(freeze["schema"]=="forge.research.f124aq.posttrain-frozen-single-lane-dev.v1"
         and freeze["status"]=="POST_TRAIN_FROZEN_DEV_UNCONSUMED"
         and freeze["preregistration_blob"]==s.FREEZE_BLOB
         and freeze["train"]["run"]==39124962572
         and freeze["train"]["raw_sha256"]==TRAIN_RAW
         and freeze["Yggdrasil"]["DEV_admitted"] is False
         and freeze["Yggdrasil"]["DEV_cases_generated"]==0
         and freeze["Wingless"]["DEV_admitted_as_candidate"]
         and freeze["Wingless"]["DEV_cases_generated"]==0
         and freeze["Wingless"]["selected"]["mode"]=="relative_lookahead_contrast"
         and freeze["Wingless"]["selected"]["alpha"]==.12
         and freeze["Wingless"]["selected"]==r["selected"]["Wingless"]
         and r["schema"]==prev.SCHEMA
         and r["freeze_blob"]==s.FREEZE_BLOB
         and r["DEV_cases_generated"]==0
         and r["DEV_consumed"] is False
         and r["TRAIN_eligible_to_consider_DEV"]["Wingless"] is True
         and r["TRAIN_eligible_to_consider_DEV"]["Yggdrasil"] is False
         and not r["protected_first_use"] and not r["optimizer_promotion"]
         and not r["production_activation"]
         and all(v is False for v in freeze["safety"].values()
                 if type(v) is bool and v is False),
         "TRAIN_FROZEN_NO_AUTHORITY")
    base,delta=prev.ancestry(o,t,an,ao,ap)
    need(r["original_model_identity"]["Wingless"]["base_sha256"]==
         q.digest(base["Wingless"]) and
         r["original_model_identity"]["Wingless"]["delta_sha256"]==
         q.digest(delta["Wingless"]),
         "AUTHENTIC_WING_WEIGHTS")
    return base["Wingless"],delta["Wingless"],freeze

def models(graph,base,delta,choice):
    newval,newwork=new.score(graph,base,delta,choice["mode"],choice["alpha"])
    oldval,oldwork=original.terminal_competitive(graph,base,delta,0.)
    capval,capwork=cap.competitive_capped(graph,base,delta,.2)
    aaval,aawork=prior.frozen_packed(graph,base,delta)
    return {"AQ_selected":(newval,newwork),"original_gamma0":(oldval,oldwork),
            "AL_cap02":(capval,capwork),"AA_one_packed":(aaval,aawork)}

def blank():
    return {"pairs":0,"paired":0,"FP":0,"FN":0,
            "by_family":{f:{"pairs":0,"paired":0,"FP":0,"FN":0}
                         for f in s.FAMILIES},
            "accepted_long_ids":[],"case_sha256":[],
            "max_active":0,"max_states_per_node":0,"max_packed_bits_per_state":0,
            "extra_hop_ops":0,"edge_inspections":0,"raw_bit_reads":0}

def score(cases,base,delta,selected,phase):
    tab={name:blank() for name in ("AQ_selected","original_gamma0",
                                  "AL_cap02","AA_one_packed")}
    diagnostic={"correct_positive_truth":0,"correct_negative_truth":0,
                "three_corrupted_examples":0,
                "literal_shortcut_positive":0,
                "source_only_normalization":True,
                "model_was_never_passed_oracle":True}
    ref=s.parent.parent.parent.am.old.prior.parent.original.parent.prior.parent.routes15
    resource_graphs=[]
    for seed,vec,fam,op,nonce,p,n in cases:
        identity=q.digest([seed,list(vec),fam])
        # Only evaluator receives operator identity and source restoration.
        pos=s.plain(p,op,nonce)
        neg=s.plain(n,op,nonce)
        if len(resource_graphs)<24:resource_graphs.append(pos)
        outcomes={}
        for label,graph in (("positive",pos),("negative",neg)):
            result=models(graph,base,delta,selected)
            for arm,(val,work) in result.items():
                need(math.isfinite(val),"FINITE_CANDIDATE")
                outcomes[(arm,label)]=val>=0
                row=tab[arm]
                row["max_active"]=max(row["max_active"],work["max_active"])
                row["max_states_per_node"]=max(
                    row["max_states_per_node"],work.get("max_states_per_node",0))
                row["max_packed_bits_per_state"]=max(
                    row["max_packed_bits_per_state"],work.get("max_packed_bits_per_state",0))
                row["extra_hop_ops"]+=work.get("extra_hop_evidence_ops",0)
                row["edge_inspections"]+=work.get("edge_inspections",0)
                row["raw_bit_reads"]+=work.get("raw_bit_reads",0)
                if arm in ("AQ_selected","original_gamma0","AL_cap02","AA_one_packed"):
                    need(work.get("max_states_per_node")==1 and
                         work.get("max_packed_bits_per_state")==12 and
                         work["max_active"]<=64,"ORIGINAL_ONE_STATE_BOUND")
        for arm,row in tab.items():
            positive=outcomes[(arm,"positive")]
            negative=outcomes[(arm,"negative")]
            pair=int(positive and not negative)
            for dest in (row,row["by_family"][fam]):
                dest["pairs"]+=1
                dest["paired"]+=pair
                dest["FP"]+=int(negative)
                dest["FN"]+=int(not positive)
            if len(p["roles"])>=13 and positive:
                row["accepted_long_ids"].append(identity)
            row["case_sha256"].append(q.digest([identity,fam,positive,negative]))
        relax=fam=="rotate4_tolerant"
        diagnostic["correct_positive_truth"]+=int(ref(pos,relaxed=relax)==1)
        diagnostic["correct_negative_truth"]+=int(ref(neg,relaxed=relax)==0)
        diagnostic["three_corrupted_examples"]+=int(
            sum(s.relation(d["input_bits"],op)!=d["output_bits"]
                for d in p["demos"])==3)
        diagnostic["literal_shortcut_positive"]+=int(
            ref({k:p[k] for k in ("start","target","roles","edges")},
                relaxed=True)>0)
    need(len(cases)==48 and diagnostic["correct_positive_truth"]==48
         and diagnostic["correct_negative_truth"]==48
         and diagnostic["three_corrupted_examples"]==48
         and diagnostic["literal_shortcut_positive"]==0,
         "FROZEN_FRESH_SOURCE_AND_LABEL_INVENTORY")
    for t in tab.values():
        need(t["pairs"]==48 and len(t["case_sha256"])==48 and
             all(v["pairs"]==12 for v in t["by_family"].values()),
             "COMPLETE_FOUR_FAMILY_PAIRED_CENSUS")
    a,b=tab["AQ_selected"],tab["original_gamma0"]
    preserved=set(b["accepted_long_ids"]).issubset(a["accepted_long_ids"])
    strict=preserved and a["FP"]<b["FP"] and a["paired"]>=b["paired"]
    return {"lane":"Wingless","phase":phase,
            "source_diagnostic":diagnostic,
            "models":tab,
            "strict_long_positive_preserved":preserved,
            "strict_FP_reduced":a["FP"]<b["FP"],
            "strict_paired_not_worse":a["paired"]>=b["paired"],
            "strict_scientific_candidate_win":strict,
            "resources_input":resource_graphs}

def resources(graphs,base,delta,choice):
    need(len(graphs)==24,"MATCHED_TWENTY_FOUR_GRAPH_RESOURCE")
    names=("AQ_selected","original_gamma0")
    result={}
    for arm in names:
        times=[];peaks=[]
        for g in graphs:
            def runner():
                if arm=="AQ_selected":
                    return new.score(g,base,delta,choice["mode"],choice["alpha"])
                return original.terminal_competitive(g,base,delta,0.)
            runner()
            for _ in range(3):
                t=time.perf_counter_ns()
                runner()
                times.append(time.perf_counter_ns()-t)
            gc.collect()
            tracemalloc.start()
            runner()
            _,peak=tracemalloc.get_traced_memory()
            tracemalloc.stop()
            peaks.append(peak)
        result[arm]={"graphs":24,"timed_calls":72,
                     "p50_model_only_ns":int(statistics.median(times)),
                     "p50_python_peak_bytes":int(statistics.median(peaks)),
                     "samples_sha256":q.digest([times,peaks])}
    return {"host":platform.platform(),"python":platform.python_version(),
            "same_host_model_only":True,"evaluator_normalization_not_timed":True,
            "hardware_equalized_superiority_claim":False,"arms":result}

def run(mode,o,t,an,ao,ap,aq):
    need(mode in ("preflight","dev"),"EXACT_ADMITTED_EVALUATOR_MODE")
    base,delta,freeze=lineage(o,t,an,ao,ap,aq)
    case_list=s.pairs("Wingless","TRAIN") if mode=="preflight" else devsource.pairs()
    result=score(case_list,base,delta,freeze["Wingless"]["selected"],
                 "TRAIN" if mode=="preflight" else "DEV")
    if mode=="preflight":
        a=result["models"]["AQ_selected"]
        need(a["paired"]==39 and a["FP"]==7 and a["FN"]==2 and
             len(a["accepted_long_ids"])==22 and
             result["strict_long_positive_preserved"] and
             result["strict_FP_reduced"],
             "ORIGINAL_TRAIN_SELECTION_CANNOT_REPRODUCE")
        result.pop("resources_input")
    else:
        result["resources"]=resources(result.pop("resources_input"),base,delta,
                                      freeze["Wingless"]["selected"])
    return {"schema":SCHEMA,"mode":mode,
            "selected_config_blob":FREEZE_BLOB,
            "original_AQ_TRAIN_raw_sha256":TRAIN_RAW,
            "source_blob":s.FREEZE_BLOB,
            "Wingless":result,
            "Yggdrasil":{"DEV_cases_generated":0,"DEV_consumed":False,
                         "rejected_on_TRAIN":True},
            "no_DEV_retuning":True,"source_truth_evaluator_only":True,
            "protected_first_use":False,"independent_science_acceptance":False,
            "optimizer_promotion":False,"production_activation":False}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mode",choices=("preflight","dev"),required=True)
    for k in ("o","t","an","ao","ap","aq","output"):
        ap.add_argument("--"+k,required=True)
    a=ap.parse_args()
    p=Path(a.output)
    need(p.parent.is_dir() and not p.exists(),"NO_RECEIPT_OVERWRITE")
    data=run(a.mode,a.o,a.t,a.an,a.ao,a.ap,a.aq)
    raw=json.dumps(data,sort_keys=True,indent=2).encode()+b"\n"
    with p.open("xb") as f:f.write(raw)
    print("F124AQ_"+a.mode.upper()+"_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    w=data["Wingless"]
    print("F124AQ_"+a.mode.upper()+"_WING=selected:"+
          str(w["models"]["AQ_selected"]["paired"])+"/48;control:"+
          str(w["models"]["original_gamma0"]["paired"])+"/48;FP:"+
          str(w["models"]["AQ_selected"]["FP"])+";strict:"+
          str(w["strict_scientific_candidate_win"]))
    print("F124AQ_YGG_DEV_CONSUMED=false")
if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as exc:
        print("F124AQ_EVALUATOR_FAIL_CLOSED:"+str(exc),file=sys.stderr)
        sys.exit(1)
