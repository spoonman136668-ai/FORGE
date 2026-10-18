"""F124-AT frozen fresh TRAIN-only causal failure attribution.

Learned models see only 24 public demonstrations and graph data. Original
source operators, labels and true inverse are evaluator-only, consulted
AFTER all source-blind predictions are complete. No parameter selection or
DEV source creation. Original prior raw evidence authenticated by SHA256.
"""
from __future__ import annotations
import argparse,hashlib,json,math,sys,time
from collections import Counter
from pathlib import Path
import f124at_train_source as source
import f124at_packed_collision_controls as pack
import f124as_noisy_inverse as as_model
import f124as_train_selection as historical
import f124am_example_affine_learner as am
import f124aq_sparse_composition as aq
import f124ao_public_relation_learner as ao
import f124ag_transition_models as ag
import f124q_independent_binding as q

SCHEMA="forge.research.f124at.original-fresh-train-identifiability-collision.v1"
AS_DEV_SHA="d6d6c184ec4a06df0c33de1a0490d8fb67d1d9897ec78529d51e85547b0d48f7"
AS_TRAIN_SHA="f012c3c34ee7f859932b5d4274e53d675f683568b2cda74cbeeee6407c785b7b"

def need(ok,name):source.need(ok,"AT_DIAG_"+name)
def rank17(demos):
    basis={}
    for d in demos[:20]:
        word=am.integer(d["input_bits"])|(1<<16)
        while word:
            pivot=word.bit_length()-1
            if pivot in basis:word^=basis[pivot]
            else:
                basis[pivot]=word
                break
    return len(basis)

def evidence_ancestry(o,t,an,ao_raw,ap_raw,aq_raw,ar_raw,as_train,as_dev):
    base,delta,ar=historical.original(o,t,an,ao_raw,ap_raw,aq_raw,ar_raw)
    a=Path(as_train).read_bytes()
    d=Path(as_dev).read_bytes()
    need(hashlib.sha256(a).hexdigest()==AS_TRAIN_SHA and
         hashlib.sha256(d).hexdigest()==AS_DEV_SHA,
         "ORIGINAL_AS_TRAIN_DEV_RAW_INTACT")
    train=json.loads(a);dev=json.loads(d)
    need(train["schema"]==historical.SCHEMA
         and train["DEV_cases_generated"]==0
         and not train["DEV_consumed"]
         and train["TRAIN"]["Yggdrasil"]["selected"]["paired"]==2
         and not train["TRAIN"]["Wingless"]["strict_original_TRAIN_DEV_admissibility"]
         and dev["schema"]=="forge.research.f124as.original-first-ygg-dev-outcome.v1"
         and dev["mode"]=="dev"
         and dev["Yggdrasil"]["models"]["AS_selected"]["paired"]==0
         and dev["Yggdrasil"]["models"]["AS_selected"]["FP"]==0
         and not dev["Yggdrasil"]["strict_scientific_candidate_improvement"]
         and not dev["Wingless"]["DEV_consumed"]
         and not dev["optimizer_promotion"],
         "RETAIN_AUTHENTIC_AS_NEGATIVE")
    return base,delta

def call_original(g,base,delta):
    val,raw,ratio,work=ag.ygg_transition(g,list(base),list(delta),.1)
    need(work["max_active"]<=7 and work["max_retained"]<=9 and
         math.isfinite(val),"ORIGINAL_SEVEN_PLUS_NINE")
    return val

def model_result(p,n,fn):
    a=fn(p);b=fn(n)
    return a>=0,b>=0

def ygg(rows,base,delta):
    need(len(rows)==48,"YGG_FRESH_48")
    names=("AS_frozen","AS_forced_DIAGNOSTIC","AM_public_affine",
           "AQ_sparse_public","AO_nearest_public","AG_unparsed",
           "AG_true_inverse_ORACLE_ONLY")
    stats={name:{"pairs":0,"paired":0,"FP":0,"FN":0,
                  "by_operator":{"affine":{"paired":0,"FP":0,"FN":0},
                                 "feistel":{"paired":0,"FP":0,"FN":0}}}
           for name in names}
    attr={"tasks":0,"rank17_hist":Counter(),"fit_mismatch_hist":Counter(),
          "check_correct_hist":Counter(),"public_abstentions":0,
          "forced_decoder_available":0,
          "forced_mapping_wrong_edge_bit_hist":Counter(),
          "exact_mapping_task_count":0,
          "correct_oracle_positive_force_negative":0,
          "total_fit_trials":0,
          "additional_task_model_memory":True,
          "max_transient_coefficients_bits":0,
          "source_operator_seen_by_model":False}
    for seed,vector,family,operator,nonce,p,n in rows:
        # Public fit and ALL source-blind predictions happen before oracle.
        fitted,info,demos=as_model.public_fit(p,"robust_affine_syndrome")
        attr["tasks"]+=1
        attr["rank17_hist"][str(rank17(demos))]+=1
        attr["fit_mismatch_hist"][str(info["best_FIT_wrong_bits"])]+=1
        attr["total_fit_trials"]+=info["matrix_trials"]
        attr["max_transient_coefficients_bits"]=max(
            attr["max_transient_coefficients_bits"],
            info["transient_coefficients"])
        normal={}
        normal["AS_frozen"]=model_result(p,n,lambda g:as_model.ygg(
            g,base,delta,fitted,info,3,56)[0])
        check=0
        if fitted is not None:
            attr["forced_decoder_available"]+=1
            for d in demos[20:]:
                pred,_=as_model.infer(fitted,d["output_bits"])
                check+=sum(a==b for a,b in zip(pred,d["input_bits"]))
        attr["check_correct_hist"][str(check)]+=1
        if info["best_FIT_wrong_bits"] is None or (
            info["best_FIT_wrong_bits"]>3 or check<56):
            attr["public_abstentions"]+=1
        def forced(g):
            if fitted is None:return -1e9
            raw,ds,non=as_model.public.public_task(g)
            for e in raw["edges"]:
                e["src_bits"],_=as_model.infer(fitted,e["src_bits"])
            return call_original(raw,base,delta)
        normal["AS_forced_DIAGNOSTIC"]=model_result(p,n,forced)
        normal["AM_public_affine"]=model_result(p,n,lambda g:
            am.ygg(g,base,delta,20)[0])
        normal["AQ_sparse_public"]=model_result(p,n,lambda g:
            aq.ygg(g,base,delta,"sparse_xor_basis",2,12)[0])
        normal["AO_nearest_public"]=model_result(p,n,lambda g:
            ao.ygg(g,base,delta,"neighbor1",2,1)[0])
        normal["AG_unparsed"]=model_result(p,n,lambda g:
            call_original({k:g[k] for k in ("start","target","roles","edges")},
                          base,delta))
        # Source-only true inverse and source truth: NEVER model input.
        oracle_p=source.plain(p,operator,nonce)
        oracle_n=source.plain(n,operator,nonce)
        normal["AG_true_inverse_ORACLE_ONLY"]=(
            call_original(oracle_p,base,delta)>=0,
            call_original(oracle_n,base,delta)>=0)
        if fitted is not None:
            raw,_,_=as_model.public.public_task(p)
            mismatch=0
            for e,truth in zip(raw["edges"],oracle_p["edges"]):
                predicted,_=as_model.infer(fitted,e["src_bits"])
                mismatch+=sum(x!=y for x,y in zip(predicted,truth["src_bits"]))
            attr["forced_mapping_wrong_edge_bit_hist"][str(mismatch)]+=1
            attr["exact_mapping_task_count"]+=int(mismatch==0)
        else:
            attr["forced_mapping_wrong_edge_bit_hist"]["no_inverse"]+=1
        attr["correct_oracle_positive_force_negative"]+=int(
            normal["AG_true_inverse_ORACLE_ONLY"][0] and
            not normal["AS_forced_DIAGNOSTIC"][0])
        fam="affine" if operator.startswith("affine_") else "feistel"
        for name,(pos,neg) in normal.items():
            for target in (stats[name],stats[name]["by_operator"][fam]):
                if target is stats[name]:target["pairs"]+=1
                target["paired"]+=int(pos and not neg)
                target["FP"]+=int(neg)
                target["FN"]+=int(not pos)
    need(attr["tasks"]==48 and
         sum(attr["rank17_hist"].values())==48 and
         sum(attr["forced_mapping_wrong_edge_bit_hist"].values())==48 and
         all(x["pairs"]==48 for x in stats.values()),
         "COMPLETE_YGG_DIAGNOSTIC_COHORT")
    attr["rank17_hist"]=dict(sorted(attr["rank17_hist"].items()))
    attr["fit_mismatch_hist"]=dict(sorted(attr["fit_mismatch_hist"].items()))
    attr["check_correct_hist"]=dict(sorted(attr["check_correct_hist"].items()))
    attr["forced_mapping_wrong_edge_bit_hist"]=dict(sorted(
        attr["forced_mapping_wrong_edge_bit_hist"].items()))
    return {"cohort":48,"models":stats,"identifiability":attr,
            "original_cognitive_limit":{"active":7,"retained":9},
            "oracle_control_admissible":False,"forced_decode_admissible":False,
            "selection_performed":False}

def wing(rows,base,delta):
    need(len(rows)==48,"WING_FRESH_48")
    names=list(pack.CHECKSUMS)+["source_only_full16_OVERBUDGET"]
    summary={name:{"paired":0,"FP":0,"FN":0,
                   "long_positive_hashes":[],
                   "collision_pairs":0,"colliding_raw_vectors":0,
                   "max_active":0,"max_packet_bits":0,
                   "by_family":{f:{"paired":0,"FP":0,"FN":0} for f in source.FAMILIES},
                   "by_depth":{}}
             for name in names}
    cases=[]
    for seed,vec,fam,operator,nonce,p,n in rows:
        g=source.plain(p,operator,nonce)
        h=source.plain(n,operator,nonce)
        case=q.digest([seed,list(vec),fam])
        depth=len(g["roles"])
        entry={"case":case,"family":fam,"depth":depth,"results":{}}
        for name in names:
            fn=(lambda z:pack.full16_diagnostic(z,base,delta)
                if name=="source_only_full16_OVERBUDGET" else
                pack.score12(z,base,delta,name))
            score_p,work=fn(g)
            score_n,neg_work=fn(h)
            pos=score_p>=0;negative=score_n>=0
            record=summary[name]
            record["paired"]+=int(pos and not negative)
            record["FP"]+=int(negative);record["FN"]+=int(not pos)
            record["by_family"][fam]["paired"]+=int(pos and not negative)
            record["by_family"][fam]["FP"]+=int(negative)
            record["by_family"][fam]["FN"]+=int(not pos)
            bydepth=record["by_depth"].setdefault(str(depth),
                           {"paired":0,"FP":0,"FN":0})
            bydepth["paired"]+=int(pos and not negative)
            bydepth["FP"]+=int(negative);bydepth["FN"]+=int(not pos)
            if depth>=13 and pos:record["long_positive_hashes"].append(case)
            record["max_active"]=max(record["max_active"],
                                      work["max_active"],neg_work["max_active"])
            record["max_packet_bits"]=max(record["max_packet_bits"],
                                      work["max_packed_bits_per_state"],
                                      neg_work["max_packed_bits_per_state"])
            if name in pack.CHECKSUMS:
                for graph in (g,h):
                    collision=pack.collisions(graph,pack.CHECKSUMS[name])
                    record["collision_pairs"]+=collision["collision_pairs"]
                    record["colliding_raw_vectors"]+=collision["colliding_raw_vectors"]
            entry["results"][name]={"positive":pos,"negative":negative,
                                     "score_positive":score_p,"score_negative":score_n}
        cases.append(entry)
    baseline=summary["original_gamma0_checksum_1342"]
    saved=set(baseline["long_positive_hashes"])
    admitted=[]
    for name,r in summary.items():
        r["original_accepted_long_preserved"]=saved.issubset(r["long_positive_hashes"])
        r["new_candidate_eligible"]=(name in pack.CHECKSUMS
                  and name!="original_gamma0_checksum_1342"
                  and r["FP"]<baseline["FP"]
                  and r["paired"]>=baseline["paired"]
                  and r["original_accepted_long_preserved"]
                  and r["max_packet_bits"]==12 and r["max_active"]<=64)
        if r["new_candidate_eligible"]:admitted.append(name)
    need(len(cases)==48 and len(summary)==4 and
         all(r["max_active"]<=64 for r in summary.values()),
         "COMPLETE_PACKED_DIAGNOSTIC_COHORT")
    return {"cohort":48,"models":summary,
            "original_long_accepted":len(saved),
            "admissible_12bit_candidates":admitted,
            "16bit_overbudget_admissible":False,
            "source_only_normalization_for_all":True,
            "case_level":cases,
            "DEV_opened":False}

def run(o,t,an,ao,ap,aq,ar,as_train,as_dev):
    source.frozen()
    base,delta=evidence_ancestry(o,t,an,ao,ap,aq,ar,as_train,as_dev)
    yr=source.pairs("Yggdrasil","TRAIN")
    wr=source.pairs("Wingless","TRAIN")
    return {"schema":SCHEMA,"frozen_source_blob":source.FREEZE_BLOB,
            "qualified_parent_head":"449fc54cecccb6e30eaa13016f9d1828532714ac",
            "Yggdrasil":ygg(yr,base["Yggdrasil"],delta["Yggdrasil"]),
            "Wingless":wing(wr,base["Wingless"],delta["Wingless"]),
            "only_independent_fresh_TRAIN":True,
            "prior_consumed_DEV_read_for_identity_only":True,
            "new_DEV_generated":0,"new_DEV_consumed":False,
            "scientific_acceptance":False,"optimizer_promotion":False,
            "production_activation":False,"merge":False}

def main():
    parser=argparse.ArgumentParser()
    for n in ("o","t","an","ao","ap","aq","ar","as_train","as_dev","output"):
        parser.add_argument("--"+n,required=True)
    v=parser.parse_args()
    out=Path(v.output)
    need(out.parent.is_dir() and not out.exists(),"APPEND_ONLY_REPORT")
    data=run(v.o,v.t,v.an,v.ao,v.ap,v.aq,v.ar,v.as_train,v.as_dev)
    raw=json.dumps(data,sort_keys=True,indent=2).encode()+b"\n"
    with out.open("xb") as fd:fd.write(raw)
    print("F124AT_ORIGINAL_TRAIN_SHA256="+hashlib.sha256(raw).hexdigest())
    print("F124AT_YGG="+json.dumps({k:{a:m[a] for a in ("paired","FP","FN")}
        for k,m in data["Yggdrasil"]["models"].items()},sort_keys=True))
    print("F124AT_IDENTIFIABILITY="+json.dumps(
        data["Yggdrasil"]["identifiability"],sort_keys=True))
    print("F124AT_WING="+json.dumps({k:{a:m[a] for a in ("paired","FP","FN",
        "collision_pairs","original_accepted_long_preserved","new_candidate_eligible")}
        for k,m in data["Wingless"]["models"].items()},sort_keys=True))
    print("F124AT_NEW_DEV_CONSUMED=false")
if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as e:
        print("F124AT_DIAG_FAIL_CLOSED:"+str(e),file=sys.stderr)
        sys.exit(1)
