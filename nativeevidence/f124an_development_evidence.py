"""F124-AN complete prospective TRAIN and DEV source-backed evidence.

Yggdrasil infers public operators from three-bit-corrupted demonstration
pairs. Wingless independently receives source-certified true-normalized
graphs to isolate packed false-positive discrimination; NEVER count that
source knowledge as model-learned capability. No DEV fitting.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,math,os,platform,random,statistics,sys,time,tracemalloc
from pathlib import Path
import f124an_frozen_source as s
import f124an_calibrated_affine as model
import f124am_development_evidence as previous
import f124am_example_affine_learner as am_model
import f124al_noisy_operator_learner as al_model
import f124am_terminal_competition as wing_model
import f124al_packed_confidence as cap_model
import f124ae_scoring_transfer as wing_previous
import f124ag_transition_models as ygg_previous
import f124aa_development_evidence as fixed_previous
import f124q_independent_binding as q

SCHEMA="forge.research.f124an.authentic-robust-uncertainty-and-one-packed-isolation.v1"
PARENT_RAW="fcb5bb9825a4b95860461c55abd3953c518adaf0cfa7052a9d200397ee87a88f"
Y_ARMS=("new_calibrated_affine","AM_original_affine","AL_old_nonlinear",
        "original_unparsed","evaluator_only_exact_inverse_AG",
        "strong_fixed_supported")
W_ARMS=("terminal_gamma_selected","original_gamma_zero",
        "AL_positive_cap_0_2","AA_one_packed","AB_three_packed",
        "strong_fixed_supported")
LONG=("rotate4_dense_13_15","xor16_extended_13_15")
def need(ok,label):s.need(ok,"RECEIPT_"+label)

def ancestry(paths):
    base,delta=previous.ancestry(paths[:-1])
    raw=Path(paths[-1]).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==PARENT_RAW,
         "AM_QUALIFIED_ORIGINAL_RAW_IDENTITY")
    doc=json.loads(raw)
    need(doc["schema"]==
         "forge.research.f124am.authentic-affine-feistel-noisy-and-one-packed-margin.v1"
         and doc["freeze_git_blob"]=="64481a7c1077e8ae8aafee723ca63d3f33f298a1"
         and doc["no_protected_first_use"]
         and not doc["independent_science_acceptance"]
         and not doc["optimizer_promotion"]
         and doc["lanes"][0]["DEV"]["models"]["learned_affine"]["paired"]==13
         and doc["lanes"][1]["DEV"]["models"]["gamma_selected"]["paired"]==7,
         "ORIGINAL_AM_NEGATIVES_RETAINED")
    return base,delta

def score_y(arm,graph,base,delta,threshold,margin):
    if arm=="new_calibrated_affine":
        return model.ygg(graph,base,delta,threshold,margin)
    if arm=="AM_original_affine":
        return am_model.ygg(graph,base,delta,24)
    if arm=="AL_old_nonlinear":
        return al_model.ygg(graph,base,delta,24)
    g={k:graph[k] for k in ("start","target","roles","edges")}
    v,raw,prob,work=ygg_previous.ygg_transition(g,base,delta,.1)
    return v,work,None

def score_w(arm,graph,base,delta,gamma):
    if arm=="terminal_gamma_selected":
        return wing_model.terminal_competitive(graph,base,delta,gamma)
    if arm=="original_gamma_zero":
        return wing_model.terminal_competitive(graph,base,delta,0.)
    if arm=="AL_positive_cap_0_2":
        return cap_model.competitive_capped(graph,base,delta,.2)
    if arm=="AA_one_packed":
        return wing_previous.frozen_packed(graph,base,delta)
    return wing_previous.frozen_three(graph,base,delta)

def empty():
    return {"pairs":0,"unsupported":0,"paired":0,"FP":0,"FN":0,
       "by_family":{f:{"pairs":0,"unsupported":0,"paired":0,"FP":0,"FN":0,
                       "accepted_long_positive":0,"long_positive_total":0}
                    for f in s.FAMILIES},
       "max_active":0,"max_retained":0,"max_states_per_node":0,
       "max_packed_bits_per_state":0,
       "source_blind_uncertain_graphs":0,
       "extra_competitor_ops":0,
       "case_sha256":[],"long_positive_ids":[]}

def record(row,fam,depth,seed,vector,arm,yes,no):
    sub=row["by_family"][fam]
    if yes is None:
        need(no is None and arm=="strong_fixed_supported" and depth>9,
             "FIXED_SHALLOW_ONLY")
        row["unsupported"]+=1;sub["unsupported"]+=1
        return
    ok=int(yes and not no)
    for dst in (row,sub):
        dst["pairs"]+=1;dst["paired"]+=ok
        dst["FP"]+=int(no);dst["FN"]+=int(not yes)
    if depth>=13:
        sub["accepted_long_positive"]+=int(yes)
        sub["long_positive_total"]+=1
        if yes:row["long_positive_ids"].append(q.digest({
            "seed":seed,"vector":vector,"family":fam}))
    row["case_sha256"].append(q.digest({
        "seed":seed,"vector":vector,"arm":arm,"family":fam,
        "positive":yes,"negative":no}))

def add_work(row,w,meta):
    if w is not None:
        row["max_active"]=max(row["max_active"],w.get("max_active",0))
        row["max_retained"]=max(row["max_retained"],w.get("max_retained",0))
        row["max_states_per_node"]=max(
             row["max_states_per_node"],w.get("max_states_per_node",0))
        row["max_packed_bits_per_state"]=max(
             row["max_packed_bits_per_state"],w.get("max_packed_bits_per_state",0))
        row["extra_competitor_ops"]+=w.get(
             "extra_competitor_packed_evaluations",0)
    if meta is not None:
        d=meta.get("learner",{})
        row["source_blind_uncertain_graphs"]+=int(
            d.get("abstained",not d.get("unique",True)))

def stage(lane,phase,base,delta,threshold,margin,gamma,fixed):
    arms=Y_ARMS if lane=="Yggdrasil" else W_ARMS
    table={arm:empty() for arm in arms}
    o={"valid_positives":0,"valid_negatives":0,
       "old_literal_shortcut_positives":0,"three_corrupt_demos":0,
       "affine_cases":0,"feistel_cases":0,
       "correct_model_affine_mapping":0,
       "confident_wrong_mapping":0,
       "honest_abstention":0,
       "truth_operator_only_in_evaluator":True,
       "wing_source_only_oracle_normalized":lane=="Wingless"}
    for seed,vector,fam,op,nonce,p,n in s.pairs(lane,phase):
        # If Wingless, source-only normalized inputs are an explicit
        # experiment conditioning, equally available to all controls.
        # Yggdrasil never sees a source-restored graph until AFTER scoring.
        if lane=="Wingless":
            plain_p=s.plain(p,op,nonce)
            plain_n=s.plain(n,op,nonce)
            graphs=(plain_p,plain_n)
        else:
            plain_p=plain_n=None
            graphs=(p,n)
        for arm in arms:
            if arm in ("evaluator_only_exact_inverse_AG",
                       "strong_fixed_supported"):
                continue
            if lane=="Wingless" and arm=="strong_fixed_supported":continue
            decisions=[]
            for g in graphs:
                if lane=="Yggdrasil":
                    val,work,meta=score_y(arm,g,base,delta,threshold,margin)
                else:
                    val,work=score_w(arm,g,base,delta,gamma)
                    meta=None
                decisions.append(val>=0)
                add_work(table[arm],work,meta)
            record(table[arm],fam,len(p["roles"]),seed,vector,arm,*decisions)
        # New-source truth and comparator ceiling read ONLY after
        # actual Yggdrasil predictions.
        if lane=="Yggdrasil":
            plain_p=s.plain(p,op,nonce)
            plain_n=s.plain(n,op,nonce)
            inferred,diag=model.normalize(p,threshold,margin)
            if inferred is None:o["honest_abstention"]+=1
            elif inferred==plain_p:o["correct_model_affine_mapping"]+=1
            else:o["confident_wrong_mapping"]+=1
            ceiling=[]
            for g in (plain_p,plain_n):
                score,raw,prob,w=ygg_previous.ygg_transition(
                    g,base,delta,.1)
                ceiling.append(score>=0)
                add_work(table["evaluator_only_exact_inverse_AG"],w,None)
            record(table["evaluator_only_exact_inverse_AG"],fam,
                   len(p["roles"]),seed,vector,
                   "evaluator_only_exact_inverse_AG",*ceiling)
        truth=s.am.old.prior.parent.original.parent.prior.parent.routes15
        relaxed=fam=="rotate4_tolerant"
        o["valid_positives"]+=int(truth(plain_p,relaxed=relaxed)==1)
        o["valid_negatives"]+=int(truth(plain_n,relaxed=relaxed)==0)
        o["old_literal_shortcut_positives"]+=int(truth(
            {k:p[k] for k in ("start","target","roles","edges")},
            relaxed=True)>0)
        o["three_corrupt_demos"]+=int(sum(
            s.relation(d["input_bits"],op)!=d["output_bits"]
            for d in p["demos"])==3)
        o["affine_cases" if op.startswith("affine_")
          else "feistel_cases"]+=1
        if len(plain_p["roles"])>9:
            row=table["strong_fixed_supported"]
            row["unsupported"]+=1
            row["by_family"][fam]["unsupported"]+=1
        else:
            control=[]
            for g in (plain_p,plain_n):
                yes,w=fixed(g);control.append(bool(yes))
                add_work(table["strong_fixed_supported"],w,None)
            record(table["strong_fixed_supported"],fam,len(p["roles"]),
                   seed,vector,"strong_fixed_supported",*control)
    need(o["valid_positives"]==48 and o["valid_negatives"]==48
         and o["old_literal_shortcut_positives"]==0
         and o["three_corrupt_demos"]==48
         and o["affine_cases"]==24 and o["feistel_cases"]==24,
         "FROZEN_TRUE_SOURCE_AND_STRONG_CORRUPTION")
    if lane=="Yggdrasil":
        need(o["correct_model_affine_mapping"]+
             o["confident_wrong_mapping"]+o["honest_abstention"]==48,
             "MODEL_CONFIDENCE_AND_WRONG_MAP_ACCOUNTING")
    for arm,row in table.items():
        expected=24 if arm=="strong_fixed_supported" else 48
        need(row["pairs"]==expected and row["unsupported"]==48-expected
             and len(row["case_sha256"])==expected
             and all(f["pairs"]+f["unsupported"]==12
                     for f in row["by_family"].values())
             and row["max_retained"]<=9
             and (row["max_active"]<=7 if lane=="Yggdrasil"
                  else row["max_active"]<=192),
             "FROZEN_COEFFICIENTS_AND_SOURCE_DENOMINATOR")
        if arm in ("terminal_gamma_selected","original_gamma_zero",
                   "AL_positive_cap_0_2","AA_one_packed"):
            need(row["max_states_per_node"]==1
                 and row["max_packed_bits_per_state"]==12
                 and row["max_active"]<=64,
                 "NO_ONE_PACKED_STATE_GROWTH")
    return {"phase":phase,"pairs":48,"models":table,"diagnostic":o}

def choose_calibration(base,delta,cases):
    selected,grid=model.select(cases,base,delta)
    # Frozen tiebreak: when multiple choices give exact same paired count,
    # count confident incorrect maps using SOURCE-ONLY TRAIN reference AFTER
    # model scoring. Never inject this identity into learner/inference.
    candidates=[r for r in grid if r["paired"]==selected["paired"]]
    if len(candidates)>1:
        checked=[]
        for r in candidates:
            wrong=0
            for seed,v,fam,op,nonce,p,n in cases:
                got,meta=model.normalize(p,r["threshold"],r["margin"])
                if got is not None and got!=s.plain(p,op,nonce):wrong+=1
            checked.append(dict(r,TRAIN_wrong_maps=wrong))
        selected=sorted(checked,key=lambda r:(
            -r["paired"],r["TRAIN_wrong_maps"],r["FP"],
             r["threshold"],-r["margin"]))[0]
    return selected,grid

def select_wing_gamma(cases,base,delta):
    need(len(cases)==48,"SOURCE_NORMALIZED_TRAIN_ONLY")
    source=[]
    baseLong=set()
    for seed,v,fam,op,nonce,p,n in cases:
        a=s.plain(p,op,nonce);b=s.plain(n,op,nonce)
        score,w=wing_model.terminal_competitive(a,base,delta,0.)
        ident=(seed,tuple(v),fam)
        if fam in LONG and score>=0:baseLong.add(ident)
        source.append((ident,a,b))
    results=[]
    for gamma in (0.,.1,.25,.5,1.):
        paired=fp=0;longs=set()
        for ident,a,b in source:
            yes=wing_model.terminal_competitive(a,base,delta,gamma)[0]>=0
            no=wing_model.terminal_competitive(b,base,delta,gamma)[0]>=0
            paired+=int(yes and not no);fp+=int(no)
            if ident[2] in LONG and yes:longs.add(ident)
        results.append({"gamma":gamma,"paired":paired,"FP":fp,
                        "long_positive":len(longs),
                        "baseline_long_positive":len(baseLong),
                        "strict_TRAIN_preservation":baseLong.issubset(longs)})
    eligible=[r for r in results if r["strict_TRAIN_preservation"]]
    need(any(r["gamma"]==0. for r in eligible),
         "FROZEN_BASELINE_GAMMA0_INELIGIBLE")
    return sorted(eligible,key=lambda r:(-r["paired"],r["FP"],r["gamma"]))[0],results

def resources(base,delta,gamma):
    samples={f:[] for f in s.FAMILIES}
    for seed,v,fam,op,nonce,p,n in s.pairs("Wingless","DEV"):
        if len(samples[fam])<6:
            samples[fam].extend((s.plain(p,op,nonce),s.plain(n,op,nonce)))
    need(all(len(row)==6 for row in samples.values()),
         "STRATIFIED_FRESH_24_RESOURCE_GRAPHS")
    funcs={
        "selected_gamma":lambda g:wing_model.terminal_competitive(g,base,delta,gamma),
        "original_gamma0":lambda g:wing_model.terminal_competitive(g,base,delta,0.),
        "AL_cap02":lambda g:cap_model.competitive_capped(g,base,delta,.2),
        "AA_one_state":lambda g:wing_previous.frozen_packed(g,base,delta)}
    out={name:{"times":[],"peaks":[],"graphs":0} for name in funcs}
    for fam in s.FAMILIES:
        for i,g in enumerate(samples[fam]):
            order=list(funcs)
            random.Random("F124AN/wing/resource/"+fam+"/"+str(i)).shuffle(order)
            for name in order:
                call=funcs[name]
                call(g)
                for _ in range(3):
                    t=time.perf_counter_ns();call(g)
                    out[name]["times"].append(time.perf_counter_ns()-t)
                gc.collect();tracemalloc.start()
                call(g)
                _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
                out[name]["peaks"].append(peak)
                out[name]["graphs"]+=1
    summary={}
    for name,recorded in out.items():
        need(recorded["graphs"]==24 and len(recorded["times"])==72
             and len(recorded["peaks"])==24,
             "SOURCE_MATCHED_SAME_HOST_COST_SAMPLES")
        summary[name]={"graphs":24,"timed_calls":72,
            "p50_ns":int(statistics.median(recorded["times"])),
            "p50_python_peak_bytes":int(statistics.median(recorded["peaks"])),
            "samples_digest":q.digest(recorded)}
    return {"host":os.environ.get("RUNNER_NAME","unknown"),
         "os":platform.platform(),"python":platform.python_version(),
         "model_only_excludes_evaluator_source_inversion":True,
         "comparable_true_normalized_24_public_graphs":True,
         "hardware_equalized_superiority_claim":False,"arms":summary}

def run(paths):
    s.frozen()
    base,delta=ancestry(paths)
    fit,fitgrid=choose_calibration(
         base["Yggdrasil"],delta["Yggdrasil"],
         s.pairs("Yggdrasil","TRAIN"))
    wing,winggrid=select_wing_gamma(
         s.pairs("Wingless","TRAIN"),
         base["Wingless"],delta["Wingless"])
    fixed=fixed_previous.original_fixed()
    result={"schema":SCHEMA,"freeze_blob":s.FREEZE_BLOB,
        "parent_AM_raw_sha256":PARENT_RAW,
        "authentic_TRAIN_before_first_DEV":True,
        "no_DEV_selection_or_tuning":True,
        "Ygg_from_noisy_public_support_only":True,
        "Wing_true_source_normalized_evaluator_only":True,
        "true_oracle_never_used_as_model_weight":True,
        "protected_first_use":False,
        "independent_science_acceptance":False,"optimizer_promotion":False,
        "production_activation":False,"accepted_ref_mutations":0,
        "Wing_extra_retained_state":False,
        "matched_hardware_superiority":False,
        "selected":{"Yggdrasil":fit,"Wingless":wing},
        "TRAIN_Ygg_grid":fitgrid,"TRAIN_Wing_grid":winggrid,"lanes":[]}
    for lane in ("Yggdrasil","Wingless"):
        row={"lane":lane,
             "TRAIN":stage(lane,"TRAIN",base[lane],delta[lane],
                         fit["threshold"],fit["margin"],wing["gamma"],fixed),
             "DEV":stage(lane,"DEV",base[lane],delta[lane],
                         fit["threshold"],fit["margin"],wing["gamma"],fixed),
             "original_weights_digest":q.digest(base[lane])}
        if lane=="Wingless":
            row["resources"]=resources(base[lane],delta[lane],wing["gamma"])
            a=set(row["DEV"]["models"]["terminal_gamma_selected"]["long_positive_ids"])
            b=set(row["DEV"]["models"]["original_gamma_zero"]["long_positive_ids"])
            row["strict_long_positive_preserved"]=b.issubset(a)
            row["strict_FP_reduced"]=(
                row["DEV"]["models"]["terminal_gamma_selected"]["FP"]<
                row["DEV"]["models"]["original_gamma_zero"]["FP"])
            row["strict_candidate_win"]=(
                row["strict_long_positive_preserved"] and row["strict_FP_reduced"])
        result["lanes"].append(row)
    return result

def main():
    parser=argparse.ArgumentParser()
    for item in ("o","t","u","w","x","y","z","aa","ab","ac","ad",
                 "ae","af","ag","ah","ai","aj","ak","al","am","output"):
        parser.add_argument("--"+item,required=True)
    args=parser.parse_args()
    path=Path(args.output)
    need(path.parent.is_dir() and not path.exists(),
         "APPEND_ONLY_FIRST_USE_RECEIPT")
    report_obj=run([getattr(args,k) for k in
        ("o","t","u","w","x","y","z","aa","ab","ac","ad",
         "ae","af","ag","ah","ai","aj","ak","al","am")])
    raw=json.dumps(report_obj,sort_keys=True,indent=2).encode()+b"\n"
    with path.open("xb") as f:f.write(raw)
    print("F124AN_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in report_obj["lanes"]:
        models=lane["DEV"]["models"]
        if lane["lane"]=="Yggdrasil":
            print("F124AN_YGG_DEV=new:"+
                  str(models["new_calibrated_affine"]["paired"])+
                  "/48;AM:"+
                  str(models["AM_original_affine"]["paired"])+
                  "/48;oracle:"+
                  str(models["evaluator_only_exact_inverse_AG"]["paired"])+
                  "/48;threshold:"+str(report_obj["selected"]["Yggdrasil"]["threshold"])+
                  ";margin:"+str(report_obj["selected"]["Yggdrasil"]["margin"]))
        else:
            print("F124AN_WING_DEV=new:"+
                  str(models["terminal_gamma_selected"]["paired"])+
                  "/48;gamma0:"+
                  str(models["original_gamma_zero"]["paired"])+
                  "/48;strict:"+str(lane["strict_candidate_win"])+
                  ";gamma:"+str(report_obj["selected"]["Wingless"]["gamma"]))
if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as error:
        print("F124AN_FAIL_CLOSED:"+str(error),file=sys.stderr)
        sys.exit(1)
