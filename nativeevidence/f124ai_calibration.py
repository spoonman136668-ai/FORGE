"""F124-AI collision-free fixed identity vs two-parameter FIT-learned calibration.

Scientific attribution:
 * The 16 bit indices are represented by 16 exactly representable unique
   scalar codes 10 + bit_index/8. This is HAND-ENGINEERED identity, not learned.
 * The first mismatched index is carried only in original cell.score.
 * Training changes TWO global logistic parameters (slope and bias) to
   calibrate squared scalar distance, not the encoding or mismatch extractor.
 * A third global scalar is the FIT-only selected decision probability.
 * DEV is evaluated only after FIT threshold is sealed in a receipt.
"""
from __future__ import annotations
import argparse,hashlib,json,math,sys
from pathlib import Path
from types import FunctionType,SimpleNamespace
import f124ai_source as S
import f124o_native_learners as O
import f124ad_intermediate_credit as AD
import f124ag_noisy_controls as AG
import f124v_yggdrasil_causal_trace as V

SCHEMA_TRAIN="forge.research.f124ai.FIT-calibration-receipt.v1"
SCHEMA_DEV="forge.research.f124ai.fixed-vs-learned-independent-DEV.v1"
CODES=tuple(10.+i/8. for i in range(16))
THRESHOLDS=(.01,.05,.1,.2,.3,.4,.5,.6,.7,.8,.9,.95,.99)
FAMILIES=S.FAMILIES
ARMS=("historical_O_original","historical_O_combined",
      "historical_U_original","historical_U_combined",
      "fixed_exact16","fixed_tolerant15","fixed_consistency16",
      "fixed_collisionfree_index","untrained_collisionfree_calibrator",
      "trained_collisionfree_calibrator")
EPOCHS=100
LR=.05
L2=.0001

def logistic(z):
    if z>=0:
        return 1./(1.+math.exp(-min(700.,z)))
    e=math.exp(max(-700.,z))
    return e/(1.+e)

def code(bit):
    S.need(0<=bit<=15 and isinstance(bit,int),"BIT_INDEX")
    return CODES[bit]

def original_learner():
    fn=AD.forward
    ns=dict(fn.__globals__);ns["source"]=S
    out=FunctionType(fn.__code__,ns,fn.__name__,fn.__defaults__,fn.__closure__)
    S.need(out.__code__ is fn.__code__,"ORIGINAL_BYTECODE_CHANGED")
    return out

def fixed_consistency(graph):
    fn=AG.bounded_public_control
    ns=dict(fn.__globals__);ns["source"]=S
    rep=FunctionType(fn.__code__,ns,fn.__name__,fn.__defaults__,fn.__closure__)
    return rep(graph,"consistency16")

def fixed_tolerance(graph):
    fn=AG.bounded_public_control
    ns=dict(fn.__globals__);ns["source"]=S
    rep=FunctionType(fn.__code__,ns,fn.__name__,fn.__defaults__,fn.__closure__)
    return rep(graph,"tolerant15")

def fixed_exact(graph):
    import f124af_fixed_controls as AF
    fn=AF.bounded_exact16
    ns=dict(fn.__globals__);ns["source"]=S
    rep=FunctionType(fn.__code__,ns,fn.__name__,fn.__defaults__,fn.__closure__)
    return rep(graph)

def decode_public_pair(graph):
    """FIT-ONLY labelled public pathway extraction. Not called by inference."""
    S.validate_public(graph)
    states=[(graph["start"],None,())]
    for role in graph["roles"]:
        later=[]
        for node,carried,hops in states:
            for edge in graph["edges"]:
                if edge["from"]!=node or edge["role"]!=role:continue
                mismatches=S.diff_bits(carried,edge["src_bits"])
                if len(mismatches)>1:continue
                later.append((edge["to"],edge["dst_bits"],hops+mismatches))
                S.need(len(later)<=128,"FIT_ROUTE_BUDGET")
        states=later
    ending=[hops for node,_,hops in states
            if node==graph["target"] and len(hops)==2]
    S.need(len(ending)==1,"FIT_ONE_TARGET_PATH")
    return ending[0]

def training_samples():
    source=[]
    for family in FAMILIES:
        for vector in S.VECTORS:
            for seed in S.COHORTS[family]["FIT"]:
                pos,neg=S.build(family,seed,vector,"FIT")
                a,b=decode_public_pair(pos),decode_public_pair(neg)
                S.need(a[0]==a[1] and b[0]!=b[1],"FIT_LABELS")
                source.append(((code(a[0])-code(a[1]))**2,1))
                source.append(((code(b[0])-code(b[1]))**2,0))
    S.need(len(source)==288,"FIT_SOURCE_COUNT")
    return source

def fit_two_weights():
    samples=training_samples()
    slope=bias=0.
    first_loss=last_loss=None
    for epoch in range(EPOCHS):
        loss=0.
        for d2,label in samples:
            p=logistic(bias-slope*d2)
            loss-=label*math.log(max(1.e-12,p))+(
                  1-label)*math.log(max(1.e-12,1-p))
            g=p-label
            gb=max(-2.,min(2.,g+L2*bias))
            gs=max(-2.,min(2.,-g*d2+L2*slope))
            bias-=LR*gb
            slope-=LR*gs
        loss/=len(samples)
        if epoch==0:first_loss=loss
        last_loss=loss
    S.need(all(math.isfinite(x) for x in (slope,bias))
           and slope>0,"TRAINED_SLOPE_NOT_POSITIVE")
    return {"slope":slope,"bias":bias,"init_slope":0.,"init_bias":0.,
            "epochs":EPOCHS,"lr":LR,"l2":L2,
            "training_samples":len(samples),
            "initial_loss":first_loss,"final_loss":last_loss,
            "weight_update_l2":math.hypot(slope,bias)}

def fingerprint_infer(graph,mode,cal,threshold):
    """Only ORIGINAL three cell fields persist; no per-node extra signature."""
    S.validate_public(graph)
    S.need(mode in ("fixed","untrained","trained"),"MODE")
    edges=O.sorted_edges(graph)
    active=[(graph["start"],None,0.)];retained=[]
    scans=compares=0;cell_peak=1
    terminal_probs=[]
    for role in graph["roles"]:
        candidates=[]
        for node,carried,scalar in active+retained:
            for e in edges:
                scans+=1
                if e["from"]!=node or e["role"]!=role:continue
                errors=S.diff_bits(carried,e["src_bits"])
                if carried is not None:compares+=16
                if len(errors)>1:continue
                if errors:
                    match_code=code(errors[0])
                    if scalar==0.:
                        next_score=match_code
                    elif scalar>=10.:
                        d2=(scalar-match_code)**2
                        if mode=="fixed":
                            accepted=d2==0.
                        else:
                            accepted=logistic(
                                cal["bias"]-cal["slope"]*d2)>=threshold
                        if not accepted:continue
                        terminal_probs.append(logistic(
                            cal["bias"]-cal["slope"]*d2))
                        next_score=-1.
                    else:continue
                else:next_score=scalar
                candidates.append((e["to"],tuple(e["dst_bits"]),next_score))
        # Exactly same fixed public ranking as original deterministic
        # consistency comparator. Not adjusted on FIT/DEV.
        candidates.sort(key=lambda q:(
            0 if q[2]==-1. else 1,q[0],q[1],q[2]))
        selected=[];nodes=set()
        for item in candidates:
            if item[0] in nodes:continue
            nodes.add(item[0]);selected.append(item)
            if len(selected)==7:break
        taken={id(x) for x in selected}
        for item in candidates:
            if len(selected)==7:break
            if id(item) not in taken:selected.append(item)
        taken={id(x) for x in selected}
        active=selected[:7]
        retained=[x for x in candidates if id(x) not in taken][:9]
        cell_peak=max(cell_peak,len(active)+len(retained))
        S.need(len(active)<=7 and len(retained)<=9 and cell_peak<=16,
               "EXTRA_CELL_ALLOCATION")
    prediction=any(n==graph["target"] and score==-1.
                   for n,_,score in active+retained)
    return {"prediction":prediction,"blocked":False,
            "actual_cell_peak":cell_peak,
            "edge_scans":scans,"raw_bit_comparisons":compares,
            "candidate_second_hop_probabilities_hex":[x.hex() for x in terminal_probs]}

def pairs(phase):
    return {family:[(seed,list(v),*S.build(family,seed,v,phase))
                   for v in S.VECTORS
                   for seed in S.COHORTS[family][phase]]
            for family in FAMILIES}

def FIT_threshold_calibration(cal):
    """Zero-FP selection is strictly FIT-only; no DEV is even constructed."""
    cohort=pairs("FIT")
    curve=[]
    for t in THRESHOLDS:
        score=FP=FN=0
        for cases in cohort.values():
            for _,_,positive,negative in cases:
                p=fingerprint_infer(positive,"trained",cal,t)["prediction"]
                n=fingerprint_infer(negative,"trained",cal,t)["prediction"]
                score+=int(p and not n);FP+=int(n);FN+=int(not p)
        curve.append({"probability_threshold":t,"paired":score,
                      "FP":FP,"FN":FN})
    valid=[x for x in curve if x["FP"]==0]
    choice=sorted(valid,key=lambda x:(-x["paired"],
                                      x["probability_threshold"]))[0] if valid else None
    return choice,curve

def training_main(output):
    S.frozen()
    S.need(tuple(json.loads(S.PROTOCOL.read_text())["hypotheses"]["threshold_grid"])
           ==THRESHOLDS,"THRESHOLD_PREREGISTRATION_DRIFT")
    fit=fit_two_weights()
    selected,curve=FIT_threshold_calibration(fit)
    threshold=selected["probability_threshold"] if selected else THRESHOLDS[0]
    report={"schema":SCHEMA_TRAIN,"freeze_blob":S.PROTOCOL_BLOB,
       "collision_free_encoding_is_hand_designed":True,
       "identity_code_hex":[v.hex() for v in CODES],
       "bit_identity_collisions":16-len(set(CODES)),
       "learned_parameters":["slope","bias"],
       "global_calibrated_param_count":3,
       "original_persistent_cell_fields":["node","raw16","score"],
       "no_DEV_used_for_training":True,"fitted":fit,
       "FIT_curve":curve,"FIT_selected":selected,
       "qualified_FIT_zero_FP":selected is not None,
       "diagnostic_threshold":threshold,
       "protected_first_use":False,
       "independent_science_accepted":False,"optimizer_promoted":False}
    save(output,report,"F124AI_FIT_TRAIN_SHA256")
    print("F124AI_FIT_L2="+str(fit["weight_update_l2"]),flush=True)
    print("F124AI_FIT_LOSS="+str(fit["initial_loss"])+
          ":final="+str(fit["final_loss"]),flush=True)
    print("F124AI_FIT_SELECTION="+json.dumps(selected),flush=True)

def make_prediction(arm,graph,trained,threshold,oldweights,oldmodel):
    if arm=="fixed_collisionfree_index":
        return fingerprint_infer(graph,"fixed",trained,threshold)
    if arm=="untrained_collisionfree_calibrator":
        return fingerprint_infer(graph,"untrained",
               {"slope":0.,"bias":0.},.5)
    if arm=="trained_collisionfree_calibrator":
        return fingerprint_infer(graph,"trained",trained,threshold)
    if arm=="fixed_consistency16":return fixed_consistency(graph)
    if arm=="fixed_tolerant15":return fixed_tolerance(graph)
    if arm=="fixed_exact16":return fixed_exact(graph)
    split=arm.split("_")
    who=split[1];combined=(split[2]=="combined")
    return oldmodel(who,graph,oldweights,
             **({"gamma":.1,"penalty":1.} if combined else {}))

def evaluate_phase(phase,trained,threshold,oldweights):
    oldmodel=original_learner()
    out={}
    for family,cohort in pairs(phase).items():
        arms={name:{"paired":0,"FP":0,"FN":0,"blocked":0,
             "by_depth":{str(d):{"pairs":0,"paired":0,"FP":0,"FN":0}
                         for d in (10,11,12)},"cases":[]} for name in ARMS}
        for seed,vec,pos,neg in cohort:
            allresults={arm:(make_prediction(arm,pos,trained,threshold,
                                            oldweights,oldmodel),
                             make_prediction(arm,neg,trained,threshold,
                                             oldweights,oldmodel))
                        for arm in ARMS}
            S.need(S.routes(pos,"consistency")==1 and
                   S.routes(neg,"consistency")==0,
                   "INDEPENDENT_POST_INFERENCE_SOURCE_TRUTH")
            for arm,(p,n) in allresults.items():
                z=arms[arm]
                block=bool(p.get("blocked",False) or n.get("blocked",False))
                accepted_pos=bool(p["prediction"]) if not block else False
                accepted_neg=bool(n["prediction"]) if not block else False
                right=accepted_pos and not accepted_neg
                z["paired"]+=int(right);z["FP"]+=int(accepted_neg)
                z["FN"]+=int(not accepted_pos);z["blocked"]+=int(block)
                d=z["by_depth"][str(len(pos["roles"]))]
                d["pairs"]+=1;d["paired"]+=int(right)
                d["FP"]+=int(accepted_neg);d["FN"]+=int(not accepted_pos)
                cell_p=p.get("actual_cell_peak",
                            p.get("final_active",0)+p.get("final_retained",0))
                cell_n=n.get("actual_cell_peak",
                            n.get("final_active",0)+n.get("final_retained",0))
                S.need(cell_p<=16 and cell_n<=16,"STATE_16")
                z["cases"].append({"seed":seed,"vector":vec,
                   "depth":len(pos["roles"]),"paired_correct":right,
                   "positive_prediction":p["prediction"],
                   "negative_prediction":n["prediction"],"blocked":block,
                   "positive_state_cells":cell_p,"negative_state_cells":cell_n,
                   "positive_logit_hex":p.get("logit_hex"),
                   "negative_logit_hex":n.get("logit_hex"),
                   "positive_second_bit_proba_hex":
                      p.get("candidate_second_hop_probabilities_hex"),
                   "negative_second_bit_proba_hex":
                      n.get("candidate_second_hop_probabilities_hex")})
        for row in arms.values():
            S.need(len(row["cases"])==48 and
                all(depth["pairs"]==16 for depth in row["by_depth"].values()),
                "FAMILY_DEPTH_SOURCE_COMPLETENESS")
        out[family]={"arms":arms,
           "learned_gain_over_fixed_identity":(
               arms["trained_collisionfree_calibrator"]["paired"]>
               arms["fixed_collisionfree_index"]["paired"] and
               arms["trained_collisionfree_calibrator"]["FP"]==0),
           "learned_gain_over_untrained":(
               arms["trained_collisionfree_calibrator"]["paired"]>
               arms["untrained_collisionfree_calibrator"]["paired"] and
               arms["trained_collisionfree_calibrator"]["FP"]==0),
           "superiority_to_fixed_consistency":(
               arms["trained_collisionfree_calibrator"]["paired"]>
               arms["fixed_consistency16"]["paired"] and
               arms["trained_collisionfree_calibrator"]["FP"]==0)}
    return out

def evaluate_main(a):
    S.frozen()
    receipt_bytes=Path(a.trained_receipt).read_bytes()
    receipt=json.loads(receipt_bytes)
    S.need(receipt["schema"]==SCHEMA_TRAIN and
           receipt["freeze_blob"]==S.PROTOCOL_BLOB and
           receipt["no_DEV_used_for_training"] and
           receipt["bit_identity_collisions"]==0,
           "FROZEN_TRAINING_RECEIPT_NOT_AUTHENTIC")
    oldweights=V.original_weights(a.original_o,a.original_r,
                                  a.original_s,a.original_u)
    fit=evaluate_phase("FIT",receipt["fitted"],
                       receipt["diagnostic_threshold"],oldweights)
    dev=evaluate_phase("DEV",receipt["fitted"],
                       receipt["diagnostic_threshold"],oldweights)
    record={"schema":SCHEMA_DEV,"freeze_blob":S.PROTOCOL_BLOB,
       "training_receipt_sha256":hashlib.sha256(receipt_bytes).hexdigest(),
       "FIT_selection_qualified":receipt["qualified_FIT_zero_FP"],
       "trained_codebook_is_not_learned":True,
       "global_trained_parameters":3,
       "fixed_identity_exact_no_collision":True,
       "old_original_O_U_weights_unchanged":True,
       "original_7_plus_9_cells":True,
       "DEV_no_fit_selection":True,"FIT":fit,"DEV":dev,
       "protected_first_use":False,
       "independent_science_accepted":False,"optimizer_promoted":False}
    save(a.output,record,"F124AI_DEV_EVIDENCE_SHA256")
    for family,z in dev.items():
        for arm,row in z["arms"].items():
            print("F124AI_DEV_"+family+"_"+arm+
              ":paired="+str(row["paired"])+"/48:FP="+str(row["FP"])+
              ":FN="+str(row["FN"])+":blocked="+str(row["blocked"]),flush=True)
        print("F124AI_VERDICT_"+family+":gain_fixed_identity="+str(
          z["learned_gain_over_fixed_identity"])+
          ":gain_untrained="+str(z["learned_gain_over_untrained"])+
          ":beats_fixed_consistency="+str(
          z["superiority_to_fixed_consistency"]),flush=True)

def save(path,obj,prefix):
    file=Path(path)
    S.need(file.parent.is_dir() and not file.exists(),"IMMUTABLE_OUTPUT")
    data=(json.dumps(obj,sort_keys=True,indent=2)+"\n").encode()
    with file.open("xb") as handle:handle.write(data)
    print(prefix+"="+hashlib.sha256(data).hexdigest(),flush=True)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--train",action="store_true")
    ap.add_argument("--evaluate",action="store_true")
    for name in ("o","r","s","u"):
        ap.add_argument("--original-"+name)
    ap.add_argument("--trained-receipt")
    ap.add_argument("--output",required=True)
    a=ap.parse_args()
    try:
        S.need(a.train!=a.evaluate,"CHOOSE_TRAIN_OR_EVALUATE")
        if a.train:training_main(a.output)
        else:
            S.need(all(getattr(a,"original_"+x) for x in ("o","r","s","u"))
                   and a.trained_receipt,"MISSING_AUTHENTIC_REFS")
            evaluate_main(a)
    except (ValueError,OSError,KeyError,TypeError,ArithmeticError) as e:
        print("F124AI_QUARANTINED="+str(e),file=sys.stderr);sys.exit(1)
