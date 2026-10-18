"""F124-AU prospective original fresh TRAIN-only learned relation screen.

The model sees only PUBLIC demonstrations/edges, while the source/evaluator
alone sees operator labels and paired truths. All 8 Ygg and 7 Wing arms are
retained, with original controls on SAME fresh TRAIN cohort and resource
disclosure. DEV construction is not imported or available.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,math,platform,sys,time,tracemalloc
from pathlib import Path

import f124au_train_source as src
import f124au_public_relation_model as new_y
import f124au_packed_witness as new_w
import f124at_train_evidence as parent
import f124as_noisy_inverse as old_as
import f124ao_public_relation_learner as old_ao
import f124aq_sparse_composition as old_aq
import f124ag_transition_models as original_y
import f124q_independent_binding as key
import f124am_terminal_competition as original_w

SCHEMA="forge.research.f124au.first-authenticated-public-relations-packed-witness-TRAIN.v1"
AT_RAW="8050c9f4bae5821c4bc2d222d1c4985a41e3c86cb4af1c3cedf1a70c1a94422d"

def need(cond,name):
    src.need(cond,"TRAIN_ONLY_"+name)

def ancestry(o,t,an,ao,ap,aq,ar,as_train,as_dev,at):
    src.frozen()
    base,delta=parent.evidence_ancestry(
        o,t,an,ao,ap,aq,ar,as_train,as_dev)
    raw=Path(at).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==AT_RAW,"HISTORICAL_AT_RAW_BYTES")
    data=json.loads(raw)
    need(data["schema"]==parent.SCHEMA and
         data["frozen_source_blob"]==src.prior.FREEZE_BLOB and
         data["new_DEV_generated"]==0 and
         not data["new_DEV_consumed"] and
         data["Yggdrasil"]["models"]["AS_frozen"]["paired"]==0 and
         data["Yggdrasil"]["models"]["AG_true_inverse_ORACLE_ONLY"]["paired"]==48 and
         data["Wingless"]["models"]["fixed_12bit_checksum_2413"]["paired"]==41 and
         not data["Wingless"]["models"]["fixed_12bit_checksum_2413"]["new_candidate_eligible"],
         "AT_AUTHENTIC_PARENT_NEGATIVE")
    return base,delta

def ledger(fn):
    gc.collect()
    tracemalloc.start()
    cpu=time.process_time_ns()
    wall=time.perf_counter_ns()
    output=fn()
    elapsed=time.perf_counter_ns()-wall
    process=time.process_time_ns()-cpu
    _,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return output,{"arm_CPU_ns":process,"arm_wall_ns":elapsed,
                   "peak_Python_alloc_bytes":peak,
                   "source_preprocessing_in_timed_arm":True,
                   "isolated_model_only_RSS":False}

def blank():
    return {"paired":0,"FP":0,"FN":0,"pairs":0,
            "long_accepted_case_ids":[],
            "max_active":0,"max_retained":0,
            "max_states_per_node":0,"max_packet_bits":0,
            "extra_hop_ops":0,"case_outcome_digests":[],
            "by_family":{f:{"paired":0,"FP":0,"FN":0,"pairs":0}
                         for f in src.FAMILIES}}

def tally(row,seed,vec,fam,roles,pos,neg,wp=None,wn=None):
    positive=pos>=0
    negative=neg>=0
    identity=key.digest([seed,list(vec),fam])
    for dest in (row,row["by_family"][fam]):
        dest["pairs"]+=1
        dest["paired"]+=int(positive and not negative)
        dest["FP"]+=int(negative)
        dest["FN"]+=int(not positive)
    if positive and len(roles)>=13:
        row["long_accepted_case_ids"].append(identity)
    row["case_outcome_digests"].append(
        key.digest([identity,fam,positive,negative]))
    for w in (wp,wn):
        if w:
            row["max_active"]=max(row["max_active"],w.get("max_active",0))
            row["max_retained"]=max(row["max_retained"],w.get("max_retained",0))
            row["max_states_per_node"]=max(row["max_states_per_node"],
                                          w.get("max_states_per_node",0))
            row["max_packet_bits"]=max(row["max_packet_bits"],
                                       w.get("max_packed_bits_per_state",0))
            row["extra_hop_ops"]+=w.get("extra_evidence_ops",0)

def ygg_candidate(rows,base,delta,mode,width,threshold):
    # No hidden graph label/inverse/operator is passed to learning.
    tasks=[p["demos"] for _,_,_,_,_,p,_ in rows]
    model=new_y.train_shared(tasks,mode,width)
    row=blank()
    inference=0
    abstained=0
    for seed,vec,fam,op,nonce,p,n in rows:
        va,wa,oa=new_y.score(p,base,delta,model,threshold)
        vb,wb,ob=new_y.score(n,base,delta,model,threshold)
        tally(row,seed,vec,fam,p["roles"],va,vb,wa,wb)
        for obs in (oa,ob):
            need(obs["source_truth_used"] is False and
                 obs["operator_grammar_used"] is False and
                 obs["extra_memory_outside_original_cognitive_cells"] is True,
                 "MODEL_HAS_NO_ORACLE")
            inference+=obs["estimated_model_mul_add_lower"]
            abstained+=int(obs["abstained"])
        need(row["max_active"]<=7 and row["max_retained"]<=9,
             "ORIGINAL_YGG_CELLS")
    return {**row,"mode":mode,"width":width,"check_threshold":threshold,
            "shared_parameters":model["shared_parameters"],
            "shared_float_bytes_lower":model["shared_float_bytes_lower"],
            "shared_train_operations":model["supervised_update_ops"],
            "task_support_bits_lower":20*32,
            "estimated_inference_mul_add_lower":inference,
            "abstained_graphs":abstained}

def ygg_old(rows,base,delta,mode):
    row=blank()
    for seed,vec,fam,op,nonce,p,n in rows:
        if mode=="AS_robust":
            fit,info,_=old_as.public_fit(p,"robust_affine_syndrome")
            get=lambda g:old_as.ygg(g,base,delta,fit,info,3,56)[0]
        elif mode=="AO_nearest":
            get=lambda g:old_ao.ygg(g,base,delta,"neighbor1",2,1)[0]
        elif mode=="AQ_sparse":
            get=lambda g:old_aq.ygg(g,base,delta,"sparse_xor_basis",2,12)[0]
        elif mode=="AG_unparsed":
            get=lambda g:original_y.ygg_transition(
                old_as.public.public_task(g)[0],base,delta,.1)[0]
        else:
            # Evaluator-only true inverse, never eligible.
            get=lambda g:original_y.ygg_transition(
                src.plain(g,op,nonce),base,delta,.1)[0]
        a,b=get(p),get(n)
        tally(row,seed,vec,fam,p["roles"],a,b)
    return {**row,"mode":mode,
            "admissible_source_blind":mode!="AG_ORACLE_TRUE_INVERSE"}

def wing_candidate(rows,base,delta,mode,alpha):
    row=blank()
    for seed,vec,fam,op,nonce,p,n in rows:
        # Restore true graph only in source evaluator before calling every
        # identical source-blind packed predictor, never model input label.
        pos=src.plain(p,op,nonce)
        neg=src.plain(n,op,nonce)
        a,wa=new_w.score(pos,base,delta,mode,alpha)
        b,wb=new_w.score(neg,base,delta,mode,alpha)
        tally(row,seed,vec,fam,pos["roles"],a,b,wa,wb)
        need(wa["max_states_per_node"]==wb["max_states_per_node"]==1
             and wa["max_packed_bits_per_state"]==wb["max_packed_bits_per_state"]==12
             and max(wa["max_active"],wb["max_active"])<=64
             and not wa["oracle_used"] and not wb["oracle_used"]
             and wa["extra_retained_states"]==wb["extra_retained_states"]==0,
             "EXACT_SINGLE_PACKED_STATE")
    return {**row,"mode":mode,"alpha":alpha}

def run(o,t,an,ao,ap,aq,ar,as_train,as_dev,at):
    base,delta=ancestry(o,t,an,ao,ap,aq,ar,as_train,as_dev,at)
    yr=src.pairs("Yggdrasil","TRAIN")
    wr=src.pairs("Wingless","TRAIN")
    need(len(yr)==len(wr)==48,"ORIGINAL_NEW_SOURCE_DENOMINATORS")
    yg=[]
    for mode in new_y.MODES:
        for width in new_y.WIDTHS:
            for threshold in new_y.CHECK_THRESHOLDS:
                r,cost=ledger(lambda m=mode,w=width,t=threshold:
                    ygg_candidate(yr,base["Yggdrasil"],delta["Yggdrasil"],m,w,t))
                yg.append({**r,"resources":cost})
    yc={}
    for mode in ("AS_robust","AO_nearest","AQ_sparse","AG_unparsed",
                 "AG_ORACLE_TRUE_INVERSE"):
        r,cost=ledger(lambda m=mode:
            ygg_old(yr,base["Yggdrasil"],delta["Yggdrasil"],m))
        yc[mode]={**r,"resources":cost}
    strongest=max((x["paired"] for x in yc.values()
                   if x["admissible_source_blind"] and x["FP"]==0),default=0)
    yeligible=[r for r in yg if r["FP"]==0 and r["paired"]>0
               and r["paired"]>strongest]
    ypick=min(yeligible,key=lambda r:(
        -r["paired"],r["resources"]["arm_CPU_ns"],r["shared_float_bytes_lower"],
        r["mode"],r["width"],r["check_threshold"])) if yeligible else None
    wg=[]
    options=[("original_gamma0",0.)]+[
        (mode,a) for mode in new_w.MODES[1:] for a in new_w.ALPHAS[1:]]
    for mode,a in options:
        r,cost=ledger(lambda m=mode,x=a:
            wing_candidate(wr,base["Wingless"],delta["Wingless"],m,x))
        wg.append({**r,"resources":cost})
    baseline=wg[0]
    accepted=set(baseline["long_accepted_case_ids"])
    for r in wg:
        r["preserves_all_original_long_positive_ids"]=accepted.issubset(
            r["long_accepted_case_ids"])
    weligible=[r for r in wg[1:] if
              r["preserves_all_original_long_positive_ids"]
              and r["FP"]<baseline["FP"]
              and r["paired"]>=baseline["paired"]]
    wpick=min(weligible,key=lambda r:(
        -r["paired"],r["FP"],r["extra_hop_ops"],r["resources"]["arm_CPU_ns"],
        r["mode"],r["alpha"])) if weligible else None
    need(len(yg)==8 and len(wg)==7 and len(yc)==5
         and all(r["pairs"]==48 for r in yg+wg+list(yc.values()))
         and all(all(v["pairs"]==12 for v in r["by_family"].values())
                 for r in yg+wg+list(yc.values()))
         and not any(r["max_packet_bits"]>12 for r in wg),
         "ALL_FROZEN_CANDIDATES_AND_FAMILIES")
    return {
       "schema":SCHEMA,"freeze_blob":src.FREEZE_BLOB,
       "parent_AT_raw_sha256":AT_RAW,
       "source_rows":{"Yggdrasil":48,"Wingless":48},
       "candidate_grids":{"Yggdrasil":yg,"Wingless":wg},
       "same_source_controls":{"Yggdrasil":yc,"Wingless":baseline},
       "strongest_eligible_Ygg_control_paired":strongest,
       "selection":{"Yggdrasil":ypick,"Wingless":wpick},
       "eligible_to_consider_DEV":{"Yggdrasil":bool(ypick),
                                   "Wingless":bool(wpick)},
       "resource_scope":{"host":platform.platform(),
                         "python":platform.python_version(),
                         "model_plus_public_parsing_included":True,
                         "Python_peak_per_arm_measured":True,
                         "isolated_OS_RSS_per_arm_measured":False,
                         "not_hardware_equalized":True},
       "new_TRAIN_only":True,"new_DEV_cases_generated":0,
       "new_DEV_consumed":False,"science_accepted":False,
       "optimizer_promotion":False,"production_activation":False,
       "protected_first_use":False}

def main():
    ap=argparse.ArgumentParser()
    for name in ("o","t","an","ao","ap","aq","ar","as_train","as_dev",
                 "at","output"):
        ap.add_argument("--"+name,required=True)
    a=ap.parse_args()
    dest=Path(a.output)
    need(dest.parent.is_dir() and not dest.exists(),
         "APPEND_ONLY_ORIGINAL_SCIENTIFIC_RECEIPT")
    d=run(a.o,a.t,a.an,a.ao,a.ap,a.aq,a.ar,a.as_train,a.as_dev,a.at)
    raw=json.dumps(d,sort_keys=True,indent=2).encode()+b"\n"
    with dest.open("xb") as out:out.write(raw)
    print("F124AU_ORIGINAL_TRAIN_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in ("Yggdrasil","Wingless"):
        selected=d["selection"][lane]
        print("F124AU_TRAIN_"+lane+"="+json.dumps({
            "eligible":d["eligible_to_consider_DEV"][lane],
            "selection":{k:selected[k] for k in ("mode","paired","FP","FN")
                         if k in selected} if selected else None},sort_keys=True))
    print("F124AU_NEW_DEV_CONSUMED=false")

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,KeyError,TypeError,ArithmeticError,AssertionError) as exc:
        print("F124AU_FAIL_CLOSED:"+str(exc),file=sys.stderr)
        sys.exit(1)
