"""F124-AQ authenticated source-new TRAIN selection, no DEV first-use.

Historical O/T/AN/AO foundations and negative F124-AP raw TRAIN bytes are
authenticated by immutable identity before original new TRAIN construction.
No graph truth, source operator, inverse, or partner labels enter model code.
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
import f124aq_train_source as source
import f124aq_sparse_composition as y
import f124aq_local_contrast as w
import f124ap_train_selection as previous
import f124ap_dual_kernel_learner as old_ap
import f124ao_public_relation_learner as old_ao
import f124q_independent_binding as q

SCHEMA="forge.research.f124aq.authentic-new-train-compositional-v1"
AP_RAW="56bb2b97a2d0ae5babc0884e55841252ecefd6a11748f33425753e6309ef1417"

def need(ok,name):source.need(ok,"TRAIN_"+name)

def ancestry(o,t,an,ao,ap):
    base,delta,previous_ao=previous.foundation(o,t,an,ao)
    raw=Path(ap).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==AP_RAW,"AP_ORIGINAL_TRAIN_RAW")
    packet=json.loads(raw)
    need(packet["schema"]=="forge.research.f124ap.authentic-train-only-kernel-and-hop-selection.v1"
         and packet["frozen_source_blob"]=="4ceb1d410001cfb56d0be5e4b6eb8b17cf4cade9"
         and packet["dev_cases_generated"]==0
         and packet["dev_source_touched"] is False
         and packet["selected"]["Yggdrasil"]["paired"]==0
         and packet["selected"]["Wingless"]["mode"]=="original_gamma0"
         and packet["selected"]["Wingless"]["paired"]==39
         and packet["protected_first_use"] is False
         and packet["optimizer_promotion"] is False,
         "AP_PREVIOUS_SCIENTIFIC_NEGATIVE_RETAINED")
    for lane in ("Yggdrasil","Wingless"):
        need(packet["original_model_identity"][lane]["base_sha256"]==
             q.digest(base[lane]) and
             packet["original_model_identity"][lane]["delta_sha256"]==
             q.digest(delta[lane]),"HISTORICAL_MODEL_IDENTITIES")
    return base,delta

def check_cases(rows):
    truth=source.parent.parent.parent.am.old.prior.parent.original.parent.prior.parent.routes15
    pos=neg=corrupted=literal=0
    family={f:0 for f in source.FAMILIES}
    for seed,vec,fam,op,nonce,p,n in rows:
        restored_p=source.plain(p,op,nonce)
        restored_n=source.plain(n,op,nonce)
        relaxed=fam=="rotate4_tolerant"
        pos+=int(truth(restored_p,relaxed=relaxed)==1)
        neg+=int(truth(restored_n,relaxed=relaxed)==0)
        corrupted+=int(sum(source.relation(d["input_bits"],op)!=d["output_bits"]
                           for d in p["demos"])==3)
        literal+=int(truth({k:p[k] for k in ("start","target","roles","edges")},
                           relaxed=True)>0)
        family[fam]+=1
        need(p["demos"]==n["demos"],"EXACT_PAIRED_DEMOS")
    need(len(rows)==48 and pos==48 and neg==48 and corrupted==48 and
         literal==0 and all(n==12 for n in family.values()),
         "FROZEN_SOURCE_TRUTH_FOUR_FAMILIES")
    return {"pairs":48,"correct_positive_truths":pos,"correct_negative_truths":neg,
            "three_corrupted_examples":corrupted,
            "old_literal_shortcut_positive":literal,"families":family}

def comparator_y(rows,base,delta,model):
    correct=fp=fn=0
    for seed,vec,fam,op,nonce,p,n in rows:
        if model=="AO":
            f=lambda g:old_ao.ygg(g,base,delta,"neighbor1",2,1)
        else:
            f=lambda g:old_ap.ygg(g,base,delta,
                "dual_linear_kernel_ridge",1.,4,0.)
        a=f(p)[0]>=0
        b=f(n)[0]>=0
        correct+=int(a and not b)
        fp+=int(b)
        fn+=int(not a)
    return {"paired":correct,"FP":fp,"FN":fn,"pairs":48,
            "model":model,"same_fresh_TRAIN_sources":True}

def run(o,t,an,ao,ap):
    source.frozen()
    base,delta=ancestry(o,t,an,ao,ap)
    ys=source.pairs("Yggdrasil","TRAIN")
    ws=source.pairs("Wingless","TRAIN")
    ydiag=check_cases(ys)
    wdiag=check_cases(ws)
    ybest,ygrid=y.select(ys,base["Yggdrasil"],delta["Yggdrasil"])
    certified=[(q.digest([seed,list(vec),fam]),fam,
                source.plain(p,op,nonce),source.plain(n,op,nonce))
               for seed,vec,fam,op,nonce,p,n in ws]
    wbest,wgrid=w.select(certified,base["Wingless"],delta["Wingless"])
    need(len(ygrid)==18 and len(wgrid)==7 and
         wbest["strict_train_preservation"] and
         ybest in ygrid and wbest in wgrid,
         "ALL_TRAIN_FROZEN_CANDIDATES")
    comparators={name:comparator_y(ys,base["Yggdrasil"],
                                  delta["Yggdrasil"],name)
                 for name in ("AO","AP")}
    y_eligible=(ybest["FP"]==0 and ybest["paired"]>0 and
                ybest["paired"]>max(v["paired"] for v in comparators.values()))
    wcontrol=next(x for x in wgrid if x["mode"]=="original_gamma0")
    w_eligible=(wbest["mode"]!="original_gamma0" and
                wbest["strict_train_preservation"] and
                wbest["FP"]<wcontrol["FP"])
    return {"schema":SCHEMA,
            "freeze_blob":source.FREEZE_BLOB,
            "original_AP_RAW_SHA256":AP_RAW,
            "candidate_provenance":"public_example_supervision_only",
            "source_diagnostic":{"Yggdrasil":ydiag,"Wingless":wdiag},
            "selected":{"Yggdrasil":ybest,"Wingless":wbest},
            "TRAIN_grids":{"Yggdrasil":ygrid,"Wingless":wgrid},
            "same_source_comparators":comparators,
            "TRAIN_eligible_to_consider_DEV":{"Yggdrasil":y_eligible,
                                              "Wingless":w_eligible},
            "original_model_identity":{
                lane:{"base_sha256":q.digest(base[lane]),
                      "delta_sha256":q.digest(delta[lane])}
                for lane in ("Yggdrasil","Wingless")},
            "only_frozen_new_TRAIN":True,
            "source_oracle_never_model_input":True,
            "wing_source_evaluator_normalized_only":True,
            "Ygg_original_seven_plus_nine_retained":True,
            "Wing_original_one_12bit_state":True,
            "extra_model_memory_disclosed":True,
            "DEV_cases_generated":0,"DEV_consumed":False,
            "protected_first_use":False,"science_accepted":False,
            "optimizer_promotion":False,"production_activation":False}

def main():
    ap=argparse.ArgumentParser()
    for key in ("o","t","an","ao","ap","output"):
        ap.add_argument("--"+key,required=True)
    a=ap.parse_args()
    path=Path(a.output)
    need(path.parent.is_dir() and not path.exists(),"APPEND_ONLY_RAW_TRAIN")
    data=run(a.o,a.t,a.an,a.ao,a.ap)
    payload=json.dumps(data,indent=2,sort_keys=True).encode()+b"\n"
    with path.open("xb") as f:f.write(payload)
    print("F124AQ_TRAIN_RAW_SHA256="+hashlib.sha256(payload).hexdigest())
    for lane in ("Yggdrasil","Wingless"):
        print("F124AQ_TRAIN_"+lane+"="+json.dumps(data["selected"][lane],sort_keys=True))
        print("F124AQ_TRAIN_DEV_ELIGIBLE_"+lane+"="+str(data["TRAIN_eligible_to_consider_DEV"][lane]))
    print("F124AQ_DEV_CONSUMED=FALSE")
if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as error:
        print("F124AQ_FAIL_CLOSED:"+str(error),file=sys.stderr)
        sys.exit(1)
