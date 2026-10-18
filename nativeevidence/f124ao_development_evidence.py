"""F124-AO authentic twenty-one-receipt independent TRAIN/DEV experiment.

New 40-example redundant in-context learning and true-source-conditioned
sequential single-packed-state agreement. No protected first use; all
result failures retained. Evaluator-only source restoration is explicitly
separate from both model inference and actual scientific acceptance.
"""
from __future__ import annotations
import argparse,copy,gc,hashlib,json,os,platform,random,statistics,sys,time,tracemalloc
from pathlib import Path
import f124ao_frozen_source as source
import f124ao_redundant_affine_and_packed as model
import f124an_development_evidence as ancestor
import f124an_calibrated_affine as an
import f124ak_one_packed_contrast as ak
import f124al_packed_confidence as al_wing
import f124ae_scoring_transfer as w_old
import f124ag_transition_models as y_old
import f124aa_development_evidence as fixed_source
import f124q_independent_binding as q

SCHEMA="forge.research.f124ao.authentic-forty-demo-and-sequential-single-packet.v1"
AN_RAW="7226e267ac02090069690ebb40e92696a2cba1bd56a567d838fc6e48880cff9c"
LONG=("rotate4_dense_13_15","xor16_extended_13_15")
Y_ARMS=("redundant40_new","prior_AN_24","unparsed_AG",
        "oracle_normalized_AG","strong_fixed_supported")
W_ARMS=("sequential_frozen","original_AK_beta05",
        "AL_frozen_cap02","AA_single","AB_three","strong_fixed_supported")
def need(ok,tag):source.need(ok,"RECEIPT_"+tag)

def ancestry(paths):
    base,delta=ancestor.ancestry(paths[:-1])
    original=Path(paths[-1]).read_bytes()
    need(hashlib.sha256(original).hexdigest()==AN_RAW,
         "ORIGINAL_AN_SCIENCE_EXACT_RAW_SHA")
    doc=json.loads(original)
    need(doc["schema"]==
        "forge.research.f124an.authentic-robust-uncertainty-and-one-packed-isolation.v1"
        and doc["freeze_blob"]=="d3ad91612d2aefc4be13f94515badb6d2b4347cb"
        and doc["protected_first_use"] is False
        and doc["independent_science_acceptance"] is False
        and doc["optimizer_promotion"] is False
        and doc["lanes"][0]["DEV"]["models"]["new_calibrated_affine"]["paired"]==10
        and doc["lanes"][1]["DEV"]["models"]["terminal_gamma_selected"]["paired"]==31,
        "ORIGINAL_AN_NEGATIVE_PRESERVED")
    return base,delta

def mrecord():
    return {"pairs":0,"unsupported":0,"paired":0,"FP":0,"FN":0,
        "by_family":{f:{"pairs":0,"unsupported":0,"paired":0,"FP":0,"FN":0,
                        "long_positives_accepted":0}
                     for f in source.FAMILIES},
        "max_active":0,"max_retained":0,"max_states_per_node":0,
        "max_packed_bits_per_state":0,
        "long_ids":[],"case_digests":[],"abstaining_graphs":0,
        "model_edge_ops":0,"sequential_passes":0}

def add(row,family,depth,seed,vector,arm,phase,a,b):
    f=row["by_family"][family]
    if a is None:
        need(b is None and arm=="strong_fixed_supported" and depth>9,
             "FIXED_SUPPORTED_DEPTH_ONLY")
        row["unsupported"]+=1;f["unsupported"]+=1;return
    correct=int(a and not b)
    for rec in (row,f):
        rec["pairs"]+=1;rec["paired"]+=correct
        rec["FP"]+=int(b);rec["FN"]+=int(not a)
    if depth>=13:
        f["long_positives_accepted"]+=int(a)
        if a:row["long_ids"].append(q.digest({
            "seed":seed,"v":vector,"family":family}))
    row["case_digests"].append(q.digest({
        "seed":seed,"vector":vector,"arm":arm,"phase":phase,
        "positive":a,"negative":b}))

def work(row,w,meta=None):
    if w is not None:
        row["max_active"]=max(row["max_active"],w.get("max_active",0))
        row["max_retained"]=max(row["max_retained"],w.get("max_retained",0))
        row["max_states_per_node"]=max(row["max_states_per_node"],
                                        w.get("max_states_per_node",0))
        row["max_packed_bits_per_state"]=max(row["max_packed_bits_per_state"],
                                             w.get("max_packed_bits_per_state",0))
        row["model_edge_ops"]+=w.get("edge_inspections",0)
        row["sequential_passes"]+=w.get("sequential_full_passes",1)
    if meta is not None:
        d=meta.get("learner",{})
        row["abstaining_graphs"]+=int(d.get("abstained",not d.get("accepted",True)))

def ypredict(arm,g,base,delta,choice):
    if arm=="redundant40_new":
        return model.ygg(g,base,delta,choice["trials"],choice["margin"])
    if arm=="prior_AN_24":
        copy24=dict(g,demos=g["demos"][:24])
        return an.ygg(copy24,base,delta,3,1)
    orig={k:g[k] for k in ("start","target","roles","edges")}
    score,raw,prob,w=y_old.ygg_transition(orig,base,delta,.1)
    return score,w,None

def wpredict(arm,g,base,delta,chosen):
    if arm=="sequential_frozen":
        return model.sequential_wing(g,base,delta,tuple(chosen["checksum"]))
    if arm=="original_AK_beta05":
        return ak.wing_competitive(g,base,delta,.5)
    if arm=="AL_frozen_cap02":
        return al_wing.competitive_capped(g,base,delta,.2)
    return (w_old.frozen_packed(g,base,delta)
            if arm=="AA_single" else w_old.frozen_three(g,base,delta))

def stage(lane,phase,base,delta,ychoice,wchoice,fixed):
    arms=Y_ARMS if lane=="Yggdrasil" else W_ARMS
    models={a:mrecord() for a in arms}
    obs={"true_positive_source":0,"true_negative_source":0,
         "original_raw_equality_shortcuts":0,
         "affine_cases":0,"feistel_cases":0,
         "40_public_demonstrations":0,"original_three_corrupted":0,
         "exact_affine_matches":0,"confident_incorrect_maps":0,
         "abstained_maps":0,
         "original_hypothesis_class_restricted":True,
         "oracle_only_evaluator":True,
         "Wingless_true_normalization_conditional":lane=="Wingless"}
    oracle=source.prior.am.old.prior.parent.original.parent.prior.parent.routes15
    for seed,vec,fam,op,nonce,p,n in source.pairs(lane,phase):
        # IMPORTANT: source truth is used to condition ONLY the Wingless
        # scorer isolation, consistently for every comparison including
        # its original control; Yggdrasil receives opaque roles/demo only.
        if lane=="Wingless":
            graphs=(source.plain(p,op,nonce),source.plain(n,op,nonce))
        else:graphs=(p,n)
        for arm in arms:
            if arm in ("oracle_normalized_AG","strong_fixed_supported"):
                continue
            if arm=="strong_fixed_supported":continue
            decisions=[]
            for g in graphs:
                if lane=="Yggdrasil":
                    score,w,meta=ypredict(arm,g,base,delta,ychoice)
                else:
                    score,w=wpredict(arm,g,base,delta,wchoice)
                    meta=None
                decisions.append(score>=0)
                work(models[arm],w,meta)
            add(models[arm],fam,len(p["roles"]),seed,vec,arm,phase,*decisions)
        # SOURCE ONLY after all Ygg model decisions and source-only Wing
        # conditioning: oracle-normalized Ygg ceiling, fixed supported.
        plain_p=source.plain(p,op,nonce)
        plain_n=source.plain(n,op,nonce)
        if lane=="Yggdrasil":
            mapped,meta=model.normalize(p,ychoice["trials"],ychoice["margin"])
            if mapped is None:obs["abstained_maps"]+=1
            elif mapped==plain_p:obs["exact_affine_matches"]+=1
            else:obs["confident_incorrect_maps"]+=1
            predicted=[]
            for g in (plain_p,plain_n):
                value,raw,prob,w=y_old.ygg_transition(g,base,delta,.1)
                predicted.append(value>=0)
                work(models["oracle_normalized_AG"],w)
            add(models["oracle_normalized_AG"],fam,len(p["roles"]),seed,vec,
                "oracle_normalized_AG",phase,*predicted)
        relaxed=fam=="rotate4_tolerant"
        obs["true_positive_source"]+=int(oracle(plain_p,relaxed=relaxed)==1)
        obs["true_negative_source"]+=int(oracle(plain_n,relaxed=relaxed)==0)
        rawp={k:p[k] for k in ("start","target","roles","edges")}
        obs["original_raw_equality_shortcuts"]+=int(oracle(rawp,relaxed=True)>0)
        obs["affine_cases" if op.startswith("affine_") else "feistel_cases"]+=1
        obs["40_public_demonstrations"]+=int(len(p["demos"])==40)
        obs["original_three_corrupted"]+=int(sum(
            source.relation(d["input_bits"],op)!=d["output_bits"]
            for d in p["demos"])==3)
        if len(p["roles"])>9:
            models["strong_fixed_supported"]["unsupported"]+=1
            models["strong_fixed_supported"]["by_family"][fam]["unsupported"]+=1
        else:
            scored=[]
            for g in (plain_p,plain_n):
                yes,w=fixed(g);scored.append(bool(yes))
                work(models["strong_fixed_supported"],w)
            add(models["strong_fixed_supported"],fam,len(p["roles"]),seed,vec,
                "strong_fixed_supported",phase,*scored)
    need(obs["true_positive_source"]==48
         and obs["true_negative_source"]==48
         and obs["original_raw_equality_shortcuts"]==0
         and obs["affine_cases"]==24 and obs["feistel_cases"]==24
         and obs["40_public_demonstrations"]==48
         and obs["original_three_corrupted"]==48,
         "NEW_SOURCE_COHORT_IDENTITIES_AND_LABELS")
    if lane=="Yggdrasil":
        need(obs["exact_affine_matches"]+
             obs["confident_incorrect_maps"]+obs["abstained_maps"]==48,
             "COMPLETE_ERROR_CORRECTION_CLASSIFICATION")
    for arm,row in models.items():
        n=24 if arm=="strong_fixed_supported" else 48
        need(row["pairs"]==n and row["unsupported"]==48-n
             and len(row["case_digests"])==n
             and all(v["pairs"]+v["unsupported"]==12
                     for v in row["by_family"].values())
             and row["max_retained"]<=9
             and (row["max_active"]<=7 if lane=="Yggdrasil"
                  else row["max_active"]<=192),
             "CORRECT_FOUR_FAMILY_HARD_CAPACITY")
        if arm in ("sequential_frozen","original_AK_beta05",
                   "AL_frozen_cap02","AA_single"):
            need(row["max_states_per_node"]==1
                 and row["max_packed_bits_per_state"]==12
                 and row["max_active"]<=64,
                 "HISTORICAL_ONE_PACKED_STATE")
    return {"phase":phase,"pairs":48,"arms":models,"diagnostics":obs}

def resource(base,delta,chosen):
    samples={f:[] for f in source.FAMILIES}
    for seed,v,f,op,nonce,p,n in source.pairs("Wingless","DEV"):
        if len(samples[f])<6:
            samples[f].extend((source.plain(p,op,nonce),
                               source.plain(n,op,nonce)))
    need(all(len(v)==6 for v in samples.values()),"SAME_24_TRUE_NORMALIZED_GRAPHS")
    funcs={
        "selected_sequential":lambda g:model.sequential_wing(
            g,base,delta,tuple(chosen["checksum"])),
        "original_single_projection":lambda g:model.sequential_wing(
            g,base,delta,model.CHECKSUMS[0]),
        "AL_cap02":lambda g:al_wing.competitive_capped(g,base,delta,.2)}
    results={k:{"elapsed":[],"allocated":[],"graphs":0} for k in funcs}
    for fam in source.FAMILIES:
        for index,g in enumerate(samples[fam]):
            order=list(funcs)
            random.Random("F124AO/measured_source/"+fam+"/"+str(index)).shuffle(order)
            for name in order:
                fn=funcs[name];fn(g)
                for i in range(3):
                    start=time.perf_counter_ns();fn(g)
                    results[name]["elapsed"].append(time.perf_counter_ns()-start)
                gc.collect();tracemalloc.start()
                fn(g);_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
                results[name]["allocated"].append(peak)
                results[name]["graphs"]+=1
    rows={}
    for name,r in results.items():
        need(r["graphs"]==24 and len(r["elapsed"])==72
             and len(r["allocated"])==24,
             "MATCHED_SOURCE_RUNTIME")
        rows[name]={"graphs":24,"repetitions":72,
           "p50_ns":int(statistics.median(r["elapsed"])),
           "p50_python_peak_bytes":int(statistics.median(r["allocated"])),
           "case_sha256":q.digest(r)}
    return {"runner":os.environ.get("RUNNER_NAME","unknown"),
            "platform":platform.platform(),"python":platform.python_version(),
            "true_source_conditioning_outside_model":True,
            "no_end_to_end_runtime_superiority_claim":True,
            "models":rows}

def run(paths):
    source.frozen()
    base,delta=ancestry(paths)
    ychoice,ygrid=model.choose_y(
        source.pairs("Yggdrasil","TRAIN"),
        base["Yggdrasil"],delta["Yggdrasil"])
    wrows=[]
    for seed,v,fam,op,nonce,p,n in source.pairs("Wingless","TRAIN"):
        wrows.append((seed,v,fam,op,nonce,source.plain(p,op,nonce),
                      source.plain(n,op,nonce)))
    wchoice,wgrid=model.choose_w(wrows,base["Wingless"],delta["Wingless"])
    fixed=fixed_source.original_fixed()
    r={"schema":SCHEMA,"freeze_blob":source.FREEZE_BLOB,
       "original_AN_raw_sha256":AN_RAW,
       "source_40_public_examples":True,
       "unchanged_three_corrupted_inputs":True,
       "training_only_choices_before_DEV":True,
       "no_DEV_retuning":True,
       "source_oracle_never_used_to_infer_Ygg_operator":True,
       "Wingless_evaluator_only_true_normalized":True,
       "Wingless_max_one_12bit_state_per_node":True,
       "protected_first_use":False,
       "independent_science_acceptance":False,
       "optimizer_promotion":False,"production":False,
       "accepted_ref_mutations":0,
       "matched_resource_superiority":False,
       "selection":{"Yggdrasil":ychoice,"Wingless":wchoice},
       "TRAIN_Ygg_grid":ygrid,"TRAIN_Wing_grid":wgrid,"lanes":[]}
    for lane in ("Yggdrasil","Wingless"):
        out={"lane":lane,
          "TRAIN":stage(lane,"TRAIN",base[lane],delta[lane],
                        ychoice,wchoice,fixed),
          "DEV":stage(lane,"DEV",base[lane],delta[lane],
                      ychoice,wchoice,fixed),
          "frozen_base_digest":q.digest(base[lane])}
        if lane=="Wingless":
            out["resources"]=resource(base[lane],delta[lane],wchoice)
            first=out["DEV"]["arms"]["sequential_frozen"]
            old=out["DEV"]["arms"]["original_AK_beta05"]
            out["strict_long_preserved"]=set(old["long_ids"]).issubset(
                set(first["long_ids"]))
            out["strict_FP_reduced"]=first["FP"]<old["FP"]
            out["strict_win"]=out["strict_long_preserved"] and out["strict_FP_reduced"]
        r["lanes"].append(out)
    return r

def main():
    ap=argparse.ArgumentParser()
    for key in ("o","t","u","w","x","y","z","aa","ab","ac","ad",
                "ae","af","ag","ah","ai","aj","ak","al","am","an",
                "output"):
        ap.add_argument("--"+key,required=True)
    args=ap.parse_args();dest=Path(args.output)
    need(dest.parent.is_dir() and not dest.exists(),
         "APPEND_ONLY_SOURCE_BIRTH_RECORD")
    report=run([getattr(args,k) for k in
         ("o","t","u","w","x","y","z","aa","ab","ac","ad",
          "ae","af","ag","ah","ai","aj","ak","al","am","an")])
    raw=json.dumps(report,sort_keys=True,indent=2).encode()+b"\n"
    with dest.open("xb") as f:f.write(raw)
    print("F124AO_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in report["lanes"]:
        d=lane["DEV"]["arms"]
        if lane["lane"]=="Yggdrasil":
            print("F124AO_YGG_DEV=new:"+
                 str(d["redundant40_new"]["paired"])+"/48;AN24:"+
                 str(d["prior_AN_24"]["paired"])+"/48;oracle:"+
                 str(d["oracle_normalized_AG"]["paired"])+"/48;trials:"+
                 str(report["selection"]["Yggdrasil"]["trials"]))
        else:
            print("F124AO_WING_DEV=new:"+
                 str(d["sequential_frozen"]["paired"])+"/48;original:"+
                 str(d["original_AK_beta05"]["paired"])+"/48;strict:"+
                 str(lane["strict_win"])+";checksum:"+
                 str(report["selection"]["Wingless"]["checksum"]))

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as e:
        print("F124AO_FAIL_CLOSED:"+str(e),file=sys.stderr)
        sys.exit(1)
