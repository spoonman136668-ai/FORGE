"""F124-AS independently authenticated fresh TRAIN screen; NEVER DEV.

Original prior O/T/AN/AO/AP/AQ/AR receipts must match SHA-256 before source
generation. Learned models receive PUBLIC demonstration objects only; operator
and partner graph truth is restricted to source evaluator and TRAIN outcome
bookkeeping. No result or configuration is promoted by this script.
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
import f124as_train_source as src
import f124as_noisy_inverse as y
import f124as_packed_fork_causality as w
import f124aq_train_selection as old
import f124ao_public_relation_learner as ao
import f124ap_dual_kernel_learner as ap
import f124aq_sparse_composition as aq
import f124am_terminal_competition as wing0
import f124q_independent_binding as provenance

SCHEMA="forge.research.f124as.original-source-authenticated-train-selection.v1"
AQ_RAW="d3a3935cc58d0fe69f46a496ae130a434360bee4169dc22bdad72385af3aa5b0"
AR_RAW="8e8a062ed46af068cf490044f9f5f548d78cc31655ca7fe2061f4ad8ddfd0446"

def need(ok,tag):src.need(ok,"EVIDENCE_"+tag)

def original(o,t,an,ao_raw,ap_raw,aq_raw,ar_raw):
    base,delta=old.ancestry(o,t,an,ao_raw,ap_raw)
    a=Path(aq_raw).read_bytes()
    r=Path(ar_raw).read_bytes()
    need(hashlib.sha256(a).hexdigest()==AQ_RAW and
         hashlib.sha256(r).hexdigest()==AR_RAW,"UNCHANGED_PRIOR_RAW")
    aqinfo=json.loads(a);arinfo=json.loads(r)
    need(aqinfo["schema"]==old.SCHEMA and
         aqinfo["DEV_cases_generated"]==0 and
         not aqinfo["DEV_consumed"] and
         arinfo["schema"]=="forge.research.f124ar.first-original-train-meta-relations.v1"
         and arinfo["DEV_cases_generated"]==0 and
         arinfo["DEV_consumed"] is False and
         not arinfo["optimizer_promotion"],
         "HISTORICAL_NEGATIVE_NO_DEV_ADMISSION")
    return base,delta,arinfo

def check_source(rows):
    oracle=src.prior.parent.parent.parent.parent.am.old.prior.parent.original.parent.prior.parent.routes15
    positive=negative=corrupt=raw_literal=0
    fam={f:0 for f in src.FAMILIES}
    for seed,vec,f,op,nonce,p,n in rows:
        a=src.plain(p,op,nonce);b=src.plain(n,op,nonce)
        positive+=int(oracle(a,relaxed=f=="rotate4_tolerant")==1)
        negative+=int(oracle(b,relaxed=f=="rotate4_tolerant")==0)
        corrupt+=int(sum(src.relation(d["input_bits"],op)!=d["output_bits"]
                          for d in p["demos"])==3)
        raw_literal+=int(oracle({k:p[k] for k in
                ("start","target","roles","edges")},relaxed=True)>0)
        fam[f]+=1
    need(len(rows)==48 and positive==negative==corrupt==48
         and raw_literal==0 and all(v==12 for v in fam.values()),
         "AUTHENTIC_FOUR_FAMILY_SOURCE")
    return {"pairs":48,"correct_positive_truths":positive,
            "correct_negative_truths":negative,"three_corrupted":corrupt,
            "original_literal_positive":raw_literal,"families":fam}

def ygg(rows,base,delta):
    selected,grid=y.select(rows,base,delta)
    control={}
    for name,func in (
        ("AO_nearest",lambda g:ao.ygg(g,base,delta,"neighbor1",2,1)),
        ("AP_kernel",lambda g:ap.ygg(g,base,delta,"dual_linear_kernel_ridge",1.,4,0.)),
        ("AQ_sparse",lambda g:aq.ygg(g,base,delta,"sparse_xor_basis",2,12))):
        paired=FP=FN=0
        for seed,v,f,op,nonce,p,n in rows:
            va,_,_=func(p);vb,_,_=func(n)
            paired+=int(va>=0 and vb<0)
            FP+=int(vb>=0);FN+=int(va<0)
        control[name]={"paired":paired,"FP":FP,"FN":FN,"pairs":48}
    threshold=max((x["paired"] for x in control.values()
                   if x["FP"]==0),default=0)
    admitted=(selected["paired"]>0 and selected["FP"]==0 and
              selected["paired"]>threshold)
    return {"candidate_grid":grid,"selected":selected,
            "candidate_count":8,"same_source_learned_controls":control,
            "strict_original_TRAIN_DEV_admissibility":admitted,
            "original_cognitive_cells":{"active":7,"retained":9},
            "additional_task_memory_disclosed":True,
            "source_oracle_used_by_model":False}

def wing(rows,base,delta):
    normalized=[]
    for seed,v,f,op,nonce,p,n in rows:
        normalized.append((provenance.digest([seed,list(v),f]),f,
                           src.plain(p,op,nonce),src.plain(n,op,nonce)))
    baseline_long=set()
    for identity,f,p,n in normalized:
        score,work=w.score(p,base,delta,"original_gamma0",0.)
        if len(p["roles"])>=13 and score>=0:
            baseline_long.add(identity)
    results=[]
    for mode,alpha in [("original_gamma0",0.)]+[
            (m,a) for m in w.MODES[1:] for a in w.ALPHAS[1:]]:
        FP=FN=paired=ops=0
        accepted=set()
        for identity,f,p,n in normalized:
            vp,wp=w.score(p,base,delta,mode,alpha)
            vn,wn=w.score(n,base,delta,mode,alpha)
            paired+=int(vp>=0 and vn<0);FP+=int(vn>=0);FN+=int(vp<0)
            ops+=wp.get("extra_hop_evidence_ops",0)+wn.get("extra_hop_evidence_ops",0)
            if len(p["roles"])>=13 and vp>=0:accepted.add(identity)
            for work in (wp,wn):
                need(work["max_states_per_node"]==1 and
                     work["max_packed_bits_per_state"]==12 and
                     work["max_active"]<=64 and
                     work["extra_retained_states"]==0,
                     "ONE_PACKED_STATE_ORIGINAL_BOUND")
        results.append({"mode":mode,"alpha":alpha,"paired":paired,
            "FP":FP,"FN":FN,"extra_hop_ops":ops,
            "original_long_accepted":len(baseline_long),
            "candidate_long_accepted":len(accepted),
            "strict_original_long_preserved":baseline_long.issubset(accepted)})
    need(len(results)==7,"FROZEN_SEVEN_WING_CONFIGS")
    original=results[0]
    eligible=[x for x in results[1:]
              if x["strict_original_long_preserved"] and
                 x["FP"]<original["FP"] and
                 x["paired"]>=original["paired"]]
    best=min(eligible,key=lambda x:(-x["paired"],x["FP"],
              x["extra_hop_ops"],x["mode"],x["alpha"])) if eligible else original
    return {"candidate_grid":results,"selected":best,"candidate_count":7,
            "original_baseline":original,
            "strict_original_TRAIN_DEV_admissibility":bool(eligible),
            "same_source_evaluator_normalization_only":True,
            "original_12_bit_one_state_per_node":True}

def train(o,t,an,ao,ap,aq,ar):
    src.frozen()
    base,delta,original_ar=original(o,t,an,ao,ap,aq,ar)
    yr=src.pairs("Yggdrasil","TRAIN")
    wr=src.pairs("Wingless","TRAIN")
    a=ygg(yr,base["Yggdrasil"],delta["Yggdrasil"])
    b=wing(wr,base["Wingless"],delta["Wingless"])
    return {"schema":SCHEMA,"preimplementation_freeze_blob":src.FREEZE_BLOB,
            "original_AR_RAW_SHA256":AR_RAW,
            "new_sources":{"Yggdrasil":check_source(yr),
                           "Wingless":check_source(wr)},
            "TRAIN":{"Yggdrasil":a,"Wingless":b},
            "only_fresh_TRAIN_generated":True,
            "DEV_cases_generated":0,"DEV_consumed":False,
            "historical_DEV_used_for_selection":False,
            "source_oracle_used_for_learned_inference":False,
            "original_7_plus_9_cells_kept":True,
            "original_one_12bit_wing_state_kept":True,
            "protected_scientific_first_use":False,
            "independent_science_acceptance":False,
            "optimizer_promotion":False,"production_activation":False}

def main():
    parser=argparse.ArgumentParser()
    for key in ("o","t","an","ao","ap","aq","ar","output"):
        parser.add_argument("--"+key,required=True)
    z=parser.parse_args();out=Path(z.output)
    need(out.parent.is_dir() and not out.exists(),"WRITE_NEW_RECEIPT_ONLY")
    result=train(z.o,z.t,z.an,z.ao,z.ap,z.aq,z.ar)
    raw=json.dumps(result,sort_keys=True,indent=2).encode()+b"\n"
    with out.open("xb") as f:f.write(raw)
    print("F124AS_TRAIN_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in ("Yggdrasil","Wingless"):
        print("F124AS_TRAIN_"+lane+"="+json.dumps({
            "selected":result["TRAIN"][lane]["selected"],
            "eligible":result["TRAIN"][lane]["strict_original_TRAIN_DEV_admissibility"]
        },sort_keys=True))
    print("F124AS_DEV_CONSUMED=false")
if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as ex:
        print("F124AS_TRAIN_FAIL_CLOSED:"+str(ex),file=sys.stderr)
        sys.exit(1)
