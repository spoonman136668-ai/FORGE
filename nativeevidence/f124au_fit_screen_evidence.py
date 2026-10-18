"""F124-AU authenticated prospective TRAIN-FIT -> held TRAIN-SCREEN.

The models have zero source truth access. Operator and evaluator truth are
only consulted after predictions are fixed. Candidate selection uses 24
TRAIN-FIT paired cases; the other 24 TRAIN-SCREEN cases are sealed until the
single best eligible candidate has been chosen. No DEV constructor is imported.
"""
from __future__ import annotations
import argparse,hashlib,json,time,sys,math
from pathlib import Path
import f124au_train_source as source
import f124au_parity_inverse as inverse
import f124au_onepacked_policy as packed
import f124at_train_evidence as previous
import f124at_packed_collision_controls as control
import f124as_noisy_inverse as as_model
import f124ao_public_relation_learner as ao
import f124ag_transition_models as ag
import f124q_independent_binding as q

SCHEMA="forge.research.f124au.authentic-noisy-parity-and-conditional-packed-train-screen.v1"
AT_SHA="8050c9f4bae5821c4bc2d222d1c4985a41e3c86cb4af1c3cedf1a70c1a94422d"
def need(ok,tag):source.need(ok,"FIT_SCREEN_"+tag)

def lineage(o,t,an,ao_raw,ap,aq,ar,as_train,as_dev,at):
    source.frozen()
    data=Path(at).read_bytes()
    need(hashlib.sha256(data).hexdigest()==AT_SHA,
         "ORIGINAL_AT_DIAGNOSTIC_RAW_IMMUTABLE")
    prior=json.loads(data)
    need(prior["schema"]==previous.SCHEMA
         and prior["Yggdrasil"]["models"]["AS_frozen"]["paired"]==0
         and prior["Yggdrasil"]["models"]["AG_true_inverse_ORACLE_ONLY"]["paired"]==48
         and prior["Wingless"]["models"]["original_gamma0_checksum_1342"]["FP"]==12
         and prior["new_DEV_generated"]==0
         and not prior["new_DEV_consumed"]
         and not prior["optimizer_promotion"],
         "PARENT_NEGATIVE_RETAINED_AND_UNUSED_DEV")
    return previous.evidence_ancestry(
        o,t,an,ao_raw,ap,aq,ar,as_train,as_dev)

def subset(rows,lane,split):
    lo=source.COHORTS[lane]["TRAIN"].start
    yes=lambda seed: (seed-lo<12 if split=="FIT" else seed-lo>=12)
    result=[r for r in rows if yes(r[0])]
    need(len(result)==24 and
         all(source.COHORTS[lane]["TRAIN"].start<=r[0]<
             source.COHORTS[lane]["TRAIN"].stop for r in result)
         and len(set((r[0],r[1]) for r in result))==24,
         "DISJOINT_TRAIN_SUBCOHORT_IDENTITY")
    return result

def blank():
    return {"pairs":0,"paired":0,"FP":0,"FN":0,
            "long_accepted_cases":[],"model_CPU_ns":0,
            "model_wall_ns":0,"max_active":0,"max_retained":0,
            "max_states_per_node":0,"max_packet_bits_per_node":0,
            "abstained_graphs":0,"public_check_total":0,
            "additional_task_coefficient_bits":0}
def add(t,case,fam,depth,a,b,works=(),diagnostics=(),fitinfo=None,cpu=0,wall=0):
    t["pairs"]+=1;t["paired"]+=int(a>=0 and b<0)
    t["FP"]+=int(b>=0);t["FN"]+=int(a<0)
    if depth>=13 and a>=0:t["long_accepted_cases"].append(case)
    t["model_CPU_ns"]+=cpu;t["model_wall_ns"]+=wall
    for w in works:
        if not w:continue
        t["max_active"]=max(t["max_active"],w.get("max_active",0))
        t["max_retained"]=max(t["max_retained"],w.get("max_retained",0))
        t["max_states_per_node"]=max(t["max_states_per_node"],
                                      w.get("max_states_per_node",0))
        t["max_packet_bits_per_node"]=max(t["max_packet_bits_per_node"],
                                           w.get("max_packed_bits_per_state",0))
    for d in diagnostics:
        if not d:continue
        t["abstained_graphs"]+=int(d.get("abstained",False))
        t["public_check_total"]+=d.get("public_check_correct_bits",0)
    if fitinfo:
        t["additional_task_coefficient_bits"]=max(
            t["additional_task_coefficient_bits"],
            fitinfo["model_coefficients_bits_lower"])

def timed(fn,p,n):
    cpu=time.process_time_ns();wall=time.perf_counter_ns()
    va=fn(p);vb=fn(n)
    return va,vb,time.process_time_ns()-cpu,time.perf_counter_ns()-wall

def ygg_arm(rows,base,delta,config=None,include_original=True):
    names=(["parity_selected"] if config else [])
    if include_original:names+=["AS_original","AO_sourceblind","AG_oracle_ONLY"]
    stats={x:blank() for x in names}
    source_diagnostic={"correct_source_pairs":0,"public_pairs_shared":0,
                       "source_oracle_given_to_model":False}
    for seed,vec,fam,op,nonce,p,n in rows:
        identity=q.digest([seed,list(vec),fam])
        need(p["demos"]==n["demos"] and len(p["demos"])==24,
             "SAME_PUBLIC_DEMONSTRATION_SUPPORTS")
        source_diagnostic["public_pairs_shared"]+=1
        if config:
            degree,minimum=config
            raw,demos,_=inverse.public.public_task(p)
            coeff,meta=inverse.learn(demos,degree)
            (a,wa,da),(b,wb,db),cpu,wall=timed(
                lambda g:inverse.score(g,base,delta,coeff,minimum),p,n)
            add(stats["parity_selected"],identity,fam,len(p["roles"]),
                a,b,(wa,wb),(da,db),meta,cpu,wall)
        if include_original:
            (a,wa,da),(b,wb,db),cpu,wall=timed(
                lambda g:as_model.ygg(g,base,delta,*(
                  lambda x:(x[0],x[1],3,56))(
                    as_model.public_fit(g,"robust_affine_syndrome")[:2])),p,n)
            add(stats["AS_original"],identity,fam,len(p["roles"]),
                a,b,(wa,wb),cpu=cpu,wall=wall)
            (a,wa,da),(b,wb,db),cpu,wall=timed(
                lambda g:ao.ygg(g,base,delta,"neighbor1",2,1),p,n)
            add(stats["AO_sourceblind"],identity,fam,len(p["roles"]),
                a,b,(wa,wb),cpu=cpu,wall=wall)
        # Source oracle AFTER all public model decisions above.
        g=source.plain(p,op,nonce);h=source.plain(n,op,nonce)
        if include_original:
            def eval_model(x):
                value,_,_,work=ag.ygg_transition(
                    x,list(base),list(delta),.1)
                return value,work,None
            (a,wa,da),(b,wb,db),cpu,wall=timed(eval_model,g,h)
            add(stats["AG_oracle_ONLY"],identity,fam,len(p["roles"]),
                a,b,(wa,wb),cpu=cpu,wall=wall)
        source_diagnostic["correct_source_pairs"]+=1
    need(all(x["pairs"]==len(rows) for x in stats.values())
         and source_diagnostic["public_pairs_shared"]==len(rows),
         "COMPLETE_YGG_FIT_SCREEN_DENOMINATORS")
    return {"models":stats,"source_diagnostic":source_diagnostic,
            "diagnostic_oracle_is_not_candidate":True}

def ygg_fit(rows,base,delta):
    configs=[(a,b) for a in inverse.DEGREES for b in inverse.CHECK_LIMITS]
    grid=[]
    originals=ygg_arm(rows,base,delta,None,True)
    strongest=max((originals["models"][k]["paired"]
                   for k in ("AS_original","AO_sourceblind")
                   if originals["models"][k]["FP"]==0),default=0)
    for config in configs:
        result=ygg_arm(rows,base,delta,config,False)["models"]["parity_selected"]
        grid.append({"config":{"degree":config[0],"minimum_check":config[1]},
                     "summary":result})
    need(len(grid)==4,"FROZEN_FOUR_PARITY_CONFIGURATIONS")
    allowed=[r for r in grid if r["summary"]["FP"]==0
             and r["summary"]["paired"]>strongest
             and r["summary"]["paired"]>=1]
    selected=min(allowed,key=lambda x:(-x["summary"]["paired"],
                 x["summary"]["FN"],
                 x["summary"]["model_CPU_ns"],x["config"]["degree"],
                 x["config"]["minimum_check"])) if allowed else None
    return {"source_pairs":24,"fit_grid":grid,"controls":originals,
            "best_eligible_sourceblind_control":strongest,
            "FIT_selected":selected["config"] if selected else None,
            "SCREEN_selection_frozen_before_evaluation":True}

def wing_arm(rows,base,delta,policy=None,controls=True):
    names=(["conditional_policy"] if policy else [])+(
        ["original_gamma0"] if controls else [])
    stats={name:blank() for name in names}
    for seed,vec,fam,op,nonce,p,n in rows:
        case=q.digest([seed,list(vec),fam])
        # Both scorer arms receive identical evaluator-corrected source only;
        # no operator or paired truth is passed to policy.
        g=source.plain(p,op,nonce);h=source.plain(n,op,nonce)
        for name in names:
            if name=="conditional_policy":
                fn=lambda x:packed.score(x,base,delta,policy)
            else:
                fn=lambda x:control.score12(
                    x,base,delta,"original_gamma0_checksum_1342")
            (a,wa),(b,wb),cpu,wall=timed(fn,g,h)
            need(all(w["max_states_per_node"]==1 and
                     w["max_packed_bits_per_state"]==12 and
                     w["max_active"]<=64 for w in (wa,wb)),
                 "PACKED_CAPACITY_INTEGRITY")
            add(stats[name],case,fam,len(g["roles"]),a,b,(wa,wb),cpu=cpu,wall=wall)
    need(all(v["pairs"]==len(rows) for v in stats.values()),
         "ORIGINAL_PAIRED_WING_DENOMINATOR")
    return stats

def wing_fit(rows,base,delta):
    baseline=wing_arm(rows,base,delta,None,True)["original_gamma0"]
    grid=[]
    for policy in packed.GRID:
        score=wing_arm(rows,base,delta,policy,False)["conditional_policy"]
        eligible=(score["paired"]>=baseline["paired"] and
                  score["FP"]<baseline["FP"] and
                  set(baseline["long_accepted_cases"]).issubset(
                      score["long_accepted_cases"]))
        grid.append({"policy":{"checksum":policy[0],"threshold":policy[1]},
                     "summary":score,"eligible_on_FIT":eligible})
    need(len(grid)==6,"FROZEN_SIX_SINGLE_PACKED_CONFIGS")
    eligible=[x for x in grid if x["eligible_on_FIT"]]
    selected=min(eligible,key=lambda x:(-x["summary"]["paired"],
                 x["summary"]["FP"],x["summary"]["model_CPU_ns"],
                 x["policy"]["checksum"],x["policy"]["threshold"])) if eligible else None
    return {"source_pairs":24,"controls":{"original_gamma0":baseline},
            "FIT_grid":grid,
            "FIT_selected":selected["policy"] if selected else None,
            "SCREEN_selection_frozen_before_evaluation":True}

def run(o,t,an,ao_raw,ap,aq,ar,as_train,as_dev,at):
    base,delta=lineage(o,t,an,ao_raw,ap,aq,ar,as_train,as_dev,at)
    y_all=source.pairs("Yggdrasil","TRAIN")
    w_all=source.pairs("Wingless","TRAIN")
    y_f=subset(y_all,"Yggdrasil","FIT")
    w_f=subset(w_all,"Wingless","FIT")
    y_sel=ygg_fit(y_f,base["Yggdrasil"],delta["Yggdrasil"])
    w_sel=wing_fit(w_f,base["Wingless"],delta["Wingless"])
    # Neither SCREEN cohort is instantiated until both FIT selections fixed.
    y_s=subset(y_all,"Yggdrasil","SCREEN")
    w_s=subset(w_all,"Wingless","SCREEN")
    y_cfg=(y_sel["FIT_selected"]["degree"],
           y_sel["FIT_selected"]["minimum_check"]) if y_sel["FIT_selected"] else None
    w_cfg=(w_sel["FIT_selected"]["checksum"],
           w_sel["FIT_selected"]["threshold"]) if w_sel["FIT_selected"] else None
    y_screen=ygg_arm(y_s,base["Yggdrasil"],delta["Yggdrasil"],y_cfg,True)
    w_screen=wing_arm(w_s,base["Wingless"],delta["Wingless"],w_cfg,True)
    control_w=w_screen["original_gamma0"]
    if w_cfg:
        chosen=w_screen["conditional_policy"]
        preserve=set(control_w["long_accepted_cases"]).issubset(
            chosen["long_accepted_cases"])
        w_admit=(chosen["FP"]<control_w["FP"] and
                 chosen["paired"]>=control_w["paired"] and preserve)
    else:
        preserve=None;w_admit=False
    if y_cfg:
        scored=y_screen["models"]["parity_selected"]
        other=max((y_screen["models"][k]["paired"]
                   for k in ("AS_original","AO_sourceblind")
                   if y_screen["models"][k]["FP"]==0),default=0)
        y_admit=(scored["FP"]==0 and scored["paired"]>other
                 and scored["paired"]>=1)
    else:y_admit=False;other=None
    return {"schema":SCHEMA,"source_frozen_blob":source.FREEZE_BLOB,
            "source_original_parent":"b5bb419f9d406bf3d35b868431310cd82e68b7c4",
            "Yggdrasil":{"TRAIN_FIT":y_sel,"TRAIN_SCREEN":y_screen,
                         "SCREEN_best_sourceblind_control":other,
                         "admissible_for_separate_future_DEV_gate":y_admit},
            "Wingless":{"TRAIN_FIT":w_sel,"TRAIN_SCREEN":w_screen,
                        "SCREEN_original_long_positive_preserved":preserve,
                        "admissible_for_separate_future_DEV_gate":w_admit},
            "FIT_pairs_per_lane":24,"SCREEN_pairs_per_lane":24,
            "SCREEN_never_used_for_parameter_selection":True,
            "new_DEV_cases_generated":0,"new_DEV_consumed":False,
            "independent_scientific_acceptance":False,
            "optimizer_promotion":False,"production_activation":False}
def main():
    p=argparse.ArgumentParser()
    for name in ("o","t","an","ao","ap","aq","ar","as_train","as_dev","at","output"):
        p.add_argument("--"+name,required=True)
    a=p.parse_args();dest=Path(a.output)
    need(dest.parent.is_dir() and not dest.exists(),"APPEND_ONLY_EVIDENCE")
    data=run(a.o,a.t,a.an,a.ao,a.ap,a.aq,a.ar,a.as_train,a.as_dev,a.at)
    raw=json.dumps(data,indent=2,sort_keys=True).encode()+b"\n"
    with dest.open("xb") as stream:stream.write(raw)
    print("F124AU_ORIGINAL_FIT_SCREEN_SHA256="+hashlib.sha256(raw).hexdigest())
    for name in ("Yggdrasil","Wingless"):
        r=data[name]
        print("F124AU_"+name+"="+json.dumps({"FIT_selected":r["TRAIN_FIT"]["FIT_selected"],
              "SCREEN":r["TRAIN_SCREEN"],
              "admissible":r["admissible_for_separate_future_DEV_gate"]},sort_keys=True))
    print("F124AU_NEW_DEV_CONSUMED=false")
if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as e:
        print("F124AU_FAIL_CLOSED:"+str(e),file=sys.stderr)
        sys.exit(1)
