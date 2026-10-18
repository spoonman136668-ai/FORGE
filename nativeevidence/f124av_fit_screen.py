"""F124-AV one prospective TRAIN-FIT selection and held TRAIN-SCREEN.

Original F124-AU source/evidence checked by content digest, and only fresh
AV TRAIN generated. Source oracle answers additional paid public queries,
but never reveals operator identities or true inverse to learned models.
One 12bit packet is retained per Wingless graph node in every candidate.
"""
from __future__ import annotations
import argparse,hashlib,json,math,sys,time
from pathlib import Path
import f124av_train_source as source
import f124av_informative_inverse as model
import f124av_onepacked_handoff as handoff
import f124at_packed_collision_controls as old_wing
import f124as_noisy_inverse as old_ygg
import f124ao_public_relation_learner as nearest
import f124ag_transition_models as ag
import f124q_independent_binding as q
import f124au_fit_screen_evidence as parent

SCHEMA="forge.research.f124av.fresh-public-query-inverse-handoff-train.v1"
AU_SHA="7e0cc7b084e70fed69ac9f38eb5e66ecac1e33a14a4cccfa5919677d41e95fff"
def need(ok,tag):source.need(ok,"AV_SELECT_"+tag)

def parent_receipt(au):
    source.frozen()
    raw=Path(au).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==AU_SHA,"ORIGINAL_AU_BYTES")
    d=json.loads(raw)
    need(d["schema"]=="forge.research.f124au.authentic-noisy-parity-and-conditional-packed-train-screen.v1"
        and d["Yggdrasil"]["TRAIN_FIT"]["FIT_selected"] is None
        and d["Wingless"]["TRAIN_FIT"]["FIT_selected"] is None
        and not d["new_DEV_consumed"]
        and d["new_DEV_cases_generated"]==0
        and not d["optimizer_promotion"],"ORIGINAL_AU_SCIENTIFIC_NEGATIVE")
    return d

def rows(lane,stage):
    need(lane in ("Yggdrasil","Wingless") and
         stage in ("FIT","SCREEN"),"ORIGINAL_PHASE_ONLY")
    seeds=source.COHORTS[lane]["TRAIN"]
    selected=range(seeds.start,seeds.start+12) if stage=="FIT" else range(
                    seeds.start+12,seeds.stop)
    result=[]
    for vec in source.VECTORS:
        for seed in selected:
            fam,op,nonce,p,n,case=source.build(lane,seed,vec,"TRAIN")
            result.append((seed,tuple(vec),fam,op,nonce,p,n))
    need(len(result)==24 and
         len(set((v[0],v[1]) for v in result))==24,
         "DISJOINT_FIT_SCREEN_CASES")
    return result

def blank():
    return {"pairs":0,"paired":0,"FP":0,"FN":0,"max_active":0,
            "max_retained":0,"max_packet_bits":0,"max_states_per_node":0,
            "abstained_graphs":0,"public_queries":0,
            "extra_model_bits":0,"extra_ops":0,"cpu_ns":0,
            "long_baseline_accepted":[],"accepted_long_case_ids":[],
            "by_operator":{"affine":{"paired":0,"FP":0,"FN":0},
                           "feistel":{"paired":0,"FP":0,"FN":0}}}
def store(out,row,a,b,w1,w2,diags=(),cpu=0,extra_ops=0):
    seed,vec,fam,op,nonce,p,n=row
    op_family="affine" if op.startswith("affine_") else "feistel"
    pos=a>=0;neg=b>=0
    for s in (out,out["by_operator"][op_family]):
        if s is out:s["pairs"]+=1
        s["paired"]+=int(pos and not neg);s["FP"]+=int(neg);s["FN"]+=int(not pos)
    if pos and len(p["roles"])>=13:
        out["accepted_long_case_ids"].append(q.digest([seed,list(vec),fam]))
    out["cpu_ns"]+=cpu
    out["extra_ops"]+=extra_ops
    for w in (w1,w2):
        if w:
            out["max_active"]=max(out["max_active"],w.get("max_active",0))
            out["max_retained"]=max(out["max_retained"],w.get("max_retained",0))
            out["max_packet_bits"]=max(out["max_packet_bits"],
                                       w.get("max_packed_bits_per_state",0))
            out["max_states_per_node"]=max(out["max_states_per_node"],
                                            w.get("max_states_per_node",0))
    for d in diags:
        if d:
            out["abstained_graphs"]+=int(d.get("abstained",False))
            # Shared paired public queries billed separately exactly once.
            out["extra_model_bits"]=max(out["extra_model_bits"],
                                         d.get("extra_task_model_bits",0))
def original_ygg(p,n,base,delta):
    def fit(g):
        fitted,info,_=old_ygg.public_fit(g,"robust_affine_syndrome")
        return old_ygg.ygg(g,base,delta,fitted,info,3,56)
    a,wa,ma=fit(p);b,wb,mb=fit(n)
    return a,b,wa,wb,ma,mb

def ygg_evaluate(cases,base,delta,configs):
    need(len(cases)==24,"EXACT_FIT_OR_SCREEN")
    candidates={}
    for config in configs:candidates[config]=blank()
    old=blank();near=blank();oracle=blank()
    for row in cases:
        seed,vec,fam,op,nonce,p,n=row
        need(p["demos"]==n["demos"],"PAIR_PUBLIC_INDEPENDENCE")
        if configs:
            for cond in sorted(set(x[0] for x in configs)):
                pub=source.active_public_demos(seed,vec,op,cond,p["demos"])
                start_fit=time.process_time_ns()
                fitted,info=model.fit(pub,nonce)
                fit_cpu=time.process_time_ns()-start_fit
                checked=model.check(pub,fitted)
                for budget in model.BUDGETS:
                    for required in model.CHECK_LIMITS:
                        key=(cond,budget,required)
                        if key not in candidates:continue
                        cpu=time.process_time_ns()
                        a,wa,ma=model.score(p,base,delta,fitted,info,checked,
                                            budget,required)
                        b,wb,mb=model.score(n,base,delta,fitted,info,checked,
                                            budget,required)
                        cost=time.process_time_ns()-cpu
                        store(candidates[key],row,a,b,wa,wb,(ma,mb),cpu=cost+fit_cpu,
                              extra_ops=info["all_ransac_attempts"])
                        candidates[key]["public_queries"]+=len(pub)
        a,b,wa,wb,ma,mb=original_ygg(p,n,base,delta)
        store(old,row,a,b,wa,wb,(ma,mb))
        def near_call(g):return nearest.ygg(g,base,delta,"neighbor1",2,1)
        a,wa,ma=near_call(p);b,wb,mb=near_call(n)
        store(near,row,a,b,wa,wb,(ma,mb))
        # Original true inverse evaluator-only, after all candidate decisions.
        def eval_truth(g):
            v,_,_,w=ag.ygg_transition(g,list(base),list(delta),.1)
            need(w["max_active"]<=7 and w["max_retained"]<=9,
                 "ORIGINAL_BOUND")
            return v,w
        a,wa=eval_truth(source.plain(p,op,nonce))
        b,wb=eval_truth(source.plain(n,op,nonce))
        store(oracle,row,a,b,wa,wb)
    need(all(x["pairs"]==24 for x in [old,near,oracle]+list(candidates.values())),
         "YGG_COMPLETE_24")
    return {"candidates":[{"config":{"query_condition":k[0],
                           "fit_bit_budget":k[1],"min_CHECK_correct":k[2]},
                            "results":v} for k,v in candidates.items()],
            "original_controls":{"AS_24":old,"AO_24":near,
                                 "AG_inverse_ORACLE_ONLY":oracle},
            "extra_query_calls_are_model_cost":True,
            "source_inverse_or_operator_revealed_to_models":False}

def wing_evaluate(cases,base,delta,configs):
    from f124am_terminal_competition import terminal_competitive
    names=configs
    candidates={name:blank() for name in names}
    baseline=blank()
    for row in cases:
        seed,vec,fam,op,nonce,p,n=row
        # Same evaluator-only inverse supplied to all controls.
        a=source.plain(p,op,nonce);b=source.plain(n,op,nonce)
        vp,wa=terminal_competitive(a,base,delta,0.)
        vn,wb=terminal_competitive(b,base,delta,0.)
        store(baseline,row,vp,vn,wa,wb)
        for mode,alpha in names:
            cpu=time.process_time_ns()
            value,work=handoff.score(a,base,delta,mode,alpha)
            negative,neg_work=handoff.score(b,base,delta,mode,alpha)
            store(candidates[(mode,alpha)],row,value,negative,
                  work,neg_work,cpu=time.process_time_ns()-cpu,
                  extra_ops=work.get("extra_handoff_ops",0)+
                            neg_work.get("extra_handoff_ops",0))
            need(all(w["max_packed_bits_per_state"]==12 and
                     w["max_states_per_node"]==1 and w["max_active"]<=64
                     for w in (work,neg_work)),
                 "ORIGINAL_ONE_12BIT_PACKET")
    baseline_long=set(baseline["accepted_long_case_ids"])
    options=[{"config":{"mode":k[0],"alpha":k[1]},"results":v,
              "eligible":v["FP"]<baseline["FP"] and
                 v["paired"]>=baseline["paired"] and
                 baseline_long.issubset(v["accepted_long_case_ids"])}
             for k,v in candidates.items()]
    need(len(options)==len(configs) and
         baseline["pairs"]==24 and
         all(x["results"]["pairs"]==24 for x in options),
         "COMPLETE_WING_DENOMINATORS")
    return {"original_gamma0":baseline,"candidate_grid":options,
            "source_normalization_evaluator_only":True,
            "retained_bits_per_node":12,"retained_packets_per_node":1}

def choose_ygg(data):
    control=max((data["original_controls"][x]["paired"]
                 for x in ("AS_24","AO_24")
                 if data["original_controls"][x]["FP"]==0),default=0)
    eligible=[x for x in data["candidates"]
              if x["results"]["FP"]==0 and
                 x["results"]["paired"]>control and
                 x["results"]["paired"]>=1]
    return min(eligible,key=lambda x:(-x["results"]["paired"],
                x["results"]["FN"],x["results"]["cpu_ns"],
                x["config"]["query_condition"],x["config"]["fit_bit_budget"],
                x["config"]["min_CHECK_correct"]))["config"] if eligible else None
def choose_wing(data):
    eligible=[x for x in data["candidate_grid"] if x["eligible"]]
    return min(eligible,key=lambda x:(-x["results"]["paired"],
                x["results"]["FP"],x["results"]["extra_ops"],
                x["config"]["mode"],x["config"]["alpha"]))["config"] if eligible else None

def run(o,t,an,ao_raw,ap,aq,ar,as_train,as_dev,at,au):
    parent_receipt(au)
    base,delta=parent.lineage(o,t,an,ao_raw,ap,aq,ar,
                              as_train,as_dev,at)
    y_options=[(cond,budget,check)
         for cond in ("balanced_basis48","random48")
         for budget in model.BUDGETS for check in model.CHECK_LIMITS]
    w_options=[(mode,alpha)
         for mode in ("weak_handoff_gap","rival_overconfidence")
         for alpha in (0.04,0.10,0.20)]
    y_fit=ygg_evaluate(rows("Yggdrasil","FIT"),
                       base["Yggdrasil"],delta["Yggdrasil"],y_options)
    w_fit=wing_evaluate(rows("Wingless","FIT"),
                        base["Wingless"],delta["Wingless"],w_options)
    y_choice=choose_ygg(y_fit)
    w_choice=choose_wing(w_fit)
    # FIT-only selection fixed before either SCREEN source instantiated.
    y_screen=ygg_evaluate(rows("Yggdrasil","SCREEN"),
                          base["Yggdrasil"],delta["Yggdrasil"],
                          [(y_choice["query_condition"],y_choice["fit_bit_budget"],
                            y_choice["min_CHECK_correct"])] if y_choice else [])
    w_screen=wing_evaluate(rows("Wingless","SCREEN"),
                           base["Wingless"],delta["Wingless"],
                           [(w_choice["mode"],w_choice["alpha"])] if w_choice else [])
    y_control=max((y_screen["original_controls"][k]["paired"]
                   for k in ("AS_24","AO_24")
                   if y_screen["original_controls"][k]["FP"]==0),default=0)
    y_candidate=y_screen["candidates"][0]["results"] if y_choice else None
    y_admit=(y_candidate is not None and y_candidate["FP"]==0 and
             y_candidate["paired"]>y_control and y_candidate["paired"]>=1)
    control=w_screen["original_gamma0"]
    candidate=w_screen["candidate_grid"][0]["results"] if w_choice else None
    w_admit=(candidate is not None and candidate["FP"]<control["FP"]
             and candidate["paired"]>=control["paired"] and
             set(control["accepted_long_case_ids"]).issubset(
                 candidate["accepted_long_case_ids"]))
    return {"schema":SCHEMA,"preimplementation_freeze_blob":source.FREEZE_BLOB,
            "original_parent_head":"c5cdb9ba55772b4b69a2534dd48cfc8b7abe20b2",
            "Yggdrasil":{"TRAIN_FIT":y_fit,"FIT_selection":y_choice,
                         "TRAIN_SCREEN":y_screen,"SCREEN_eligible":y_admit,
                         "strongest_SCREEN_public_control":y_control},
            "Wingless":{"TRAIN_FIT":w_fit,"FIT_selection":w_choice,
                        "TRAIN_SCREEN":w_screen,"SCREEN_eligible":w_admit},
            "FIT_cases_per_lane":24,"SCREEN_cases_per_lane":24,
            "SCREEN_never_used_to_select_or_tune":True,
            "both_new_DEV_generated":0,"both_new_DEV_consumed":False,
            "scientific_acceptance":False,"optimizer_promotion":False,
            "production_activation":False}

def main():
    p=argparse.ArgumentParser()
    for key in ("o","t","an","ao","ap","aq","ar","as_train","as_dev","at","au","output"):
        p.add_argument("--"+key,required=True)
    x=p.parse_args();dest=Path(x.output)
    need(dest.parent.is_dir() and not dest.exists(),"IMMUTABLE_NEW_REPORT")
    d=run(x.o,x.t,x.an,x.ao,x.ap,x.aq,x.ar,x.as_train,x.as_dev,x.at,x.au)
    raw=json.dumps(d,sort_keys=True,indent=2).encode()+b"\n"
    with dest.open("xb") as out:out.write(raw)
    print("F124AV_FIT_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in ("Yggdrasil","Wingless"):
        r=d[lane]
        print("F124AV_"+lane+"_FIT_SELECTED="+json.dumps(r["FIT_selection"]))
    print("F124AV_NEW_DEV_CONSUMED=false")
if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as error:
        print("F124AV_FAIL_CLOSED:"+str(error),file=sys.stderr);sys.exit(1)
