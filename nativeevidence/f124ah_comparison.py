"""F124-AH blind new source comparison: historical learned O/U vs learned
scalar fingerprint, its untrained ablation, and semantic fixed controls.
No original weights are changed, no training is performed on DEV.
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
from types import FunctionType,SimpleNamespace
import f124ah_source as S
import f124ah_learned_fingerprint as L
import f124ag_noisy_controls as AG
import f124af_fixed_controls as AF
import f124ad_intermediate_credit as AD
import f124h_train_receipt as H
import f124v_yggdrasil_causal_trace as V

SCHEMA="forge.research.f124ah.authentic-learned-vs-fixed-noise.v1"
ARMS=("O_original","O_combined","U_original","U_combined",
      "untrained_fp","trained_fp","fixed_consistency16",
      "fixed_exact16","fixed_tolerant15","historical_H12")

def bind(fn,changes):
    env=dict(fn.__globals__)
    env.update(changes)
    cloned=FunctionType(fn.__code__,env,fn.__name__,
                        fn.__defaults__,fn.__closure__)
    S.need(cloned.__code__ is fn.__code__,"EXISTING_MODEL_BYTECODE_DRIFT")
    return cloned

def historical():
    return bind(AD.forward,{"source":S})

def fixed_result(name,g):
    if name=="fixed_consistency16":
        return bind(AG.bounded_public_control,{"source":S})(g,"consistency16")
    if name=="fixed_tolerant15":
        return bind(AG.bounded_public_control,{"source":S})(g,"tolerant15")
    if name=="fixed_exact16":
        return bind(AF.bounded_exact16,{"source":S})(g)
    if name=="historical_H12":
        fn=bind(H.fixed_comparator,{
             "graph":SimpleNamespace(validate=S.validate_public)})
        return AG.AF.H12(g,fn)
    raise ValueError("UNREGISTERED_CONTROL")

def predict(arm,g,weights,trained,threshold):
    if arm=="untrained_fp":
        return L.inference(g,trained["initial"],L.GRID[0])
    if arm=="trained_fp":
        return L.inference(g,trained["codebook"],threshold)
    if arm.startswith("fixed_") or arm=="historical_H12":
        return fixed_result(arm,g)
    model,variant=arm.split("_",1)
    kw={} if variant=="original" else dict(gamma=.1,penalty=1.)
    return historical()(model,g,weights,**kw)

def cohort(phase):
    return {family:[(seed,list(v),*S.build(family,seed,v,phase))
                   for v in S.VECTORS for seed in S.COHORTS[family][phase]]
            for family in S.FAMILIES}

def score(phase,weights,trained,threshold):
    result={}
    for family,items in cohort(phase).items():
        allarms={a:{"pairs":0,"correct":0,"FP":0,"FN":0,"blocked":0,
          "by_depth":{str(d):{"pairs":0,"correct":0,"FP":0,"FN":0}
                      for d in (10,11,12)},"cases":[]} for a in ARMS}
        for seed,v,pos,neg in items:
            # Blind inference for all arms precedes independent semantic
            # verification. The previous source builder checks admission.
            predictions={arm:(predict(arm,pos,weights,trained,threshold),
                              predict(arm,neg,weights,trained,threshold))
                         for arm in ARMS}
            for arm,(p,n) in predictions.items():
                target=allarms[arm]
                blocked=bool(p.get("blocked",False) or n.get("blocked",False))
                correct=bool(p["prediction"] and not n["prediction"]) if not blocked else False
                fp=bool(n["prediction"]) if not blocked else False
                fn=bool(not p["prediction"]) if not blocked else False
                target["pairs"]+=1
                target["blocked"]+=int(blocked)
                target["correct"]+=int(correct)
                target["FP"]+=int(fp);target["FN"]+=int(fn)
                depth=str(len(pos["roles"]))
                d=target["by_depth"][depth];d["pairs"]+=1
                d["correct"]+=int(correct);d["FP"]+=int(fp);d["FN"]+=int(fn)
                if "final_active" in p:
                    S.need(p["final_active"]<=7 and p["final_retained"]<=9,
                           "HISTORICAL_CELL_CAP")
                if "actual_cell_peak" in p:
                    S.need(p["actual_cell_peak"]<=16,"NEW_STATE_CAP")
                target["cases"].append({
                  "seed":seed,"vector":v,"depth":int(depth),
                  "correct":correct,"positive_prediction":p["prediction"],
                  "negative_prediction":n["prediction"],
                  "blocked":blocked,
                  "positive_logit_hex":p.get("logit_hex"),
                  "negative_logit_hex":n.get("logit_hex"),
                  "positive_cell_peak":p.get("actual_cell_peak"),
                  "negative_cell_peak":n.get("actual_cell_peak"),
                  "positive_scans":p.get("edge_scans"),
                  "negative_scans":n.get("edge_scans")})
            S.need(S.routes(pos,"consistency")==1 and
                   S.routes(neg,"consistency")==0,
                   "ORACLE_AFTER_BLIND_INFERENCE")
        for arm,z in allarms.items():
            S.need(z["pairs"]==48 and len(z["cases"])==48
             and all(d["pairs"]==16 for d in z["by_depth"].values()),
             "ALL_FAMILY_CASE_DENOMINATORS")
        result[family]={"arms":allarms,
          "trained_development_superior_to_fixed":(
            allarms["trained_fp"]["correct"]>
            allarms["fixed_consistency16"]["correct"] and
            allarms["trained_fp"]["FP"]==0),
          "trained_improves_untrained":(
            allarms["trained_fp"]["correct"]>
            allarms["untrained_fp"]["correct"] and
            allarms["trained_fp"]["FP"]==0),
          "trained_improves_historical":(
            allarms["trained_fp"]["correct"]>
            max(allarms["O_combined"]["correct"],
                allarms["U_combined"]["correct"]) and
            allarms["trained_fp"]["FP"]==0)}
    return result

def main():
    ap=argparse.ArgumentParser()
    for name in ("o","r","s","u"):ap.add_argument("--original-"+name,required=True)
    ap.add_argument("--trained-receipt",required=True)
    ap.add_argument("--output",required=True)
    a=ap.parse_args()
    S.frozen()
    evidence=Path(a.trained_receipt).read_bytes()
    trained_receipt=json.loads(evidence)
    S.need(trained_receipt["schema"]==L.SCHEMA
     and trained_receipt["freeze_blob"]==S.PROTOCOL_BLOB
     and trained_receipt["fully_FIT_trained"]
     and trained_receipt["no_DEV_parameter_selection"],
     "TRAINED_FIT_RECEIPT_NOT_VERIFIED")
    trained=trained_receipt["trained"]
    threshold=trained_receipt["selected_threshold"]
    weights=V.original_weights(a.original_o,a.original_r,a.original_s,a.original_u)
    fit=score("FIT",weights,trained,threshold)
    dev=score("DEV",weights,trained,threshold)
    out={"schema":SCHEMA,"freeze_blob":S.PROTOCOL_BLOB,
      "learned_receipt_sha256":hashlib.sha256(evidence).hexdigest(),
      "parameters_fit_only":True,"historical_O_U_unchanged":True,
      "frozen_old_gamma":.1,"frozen_old_penalty":1.,
      "codebook_trainable_parameter_count":L.PARAMETER_COUNT,
      "original_max_persistent_cells":16,
      "FIT":fit,"DEV":dev,"protected_first_use":False,
      "independent_science_accepted":False,"optimizer_promoted":False}
    dest=Path(a.output)
    S.need(dest.parent.is_dir() and not dest.exists(),"IMMUTABLE")
    raw=(json.dumps(out,sort_keys=True,indent=2)+"\n").encode()
    with dest.open("xb") as f:f.write(raw)
    print("F124AH_COMPARISON_SHA256="+hashlib.sha256(raw).hexdigest(),flush=True)
    for family,z in dev.items():
        for arm,row in z["arms"].items():
            print("F124AH_DEV_"+family+"_"+arm+
               ":correct="+str(row["correct"])+"/48:FP="+str(row["FP"])+
               ":FN="+str(row["FN"])+":blocked="+str(row["blocked"]),flush=True)
        print("F124AH_VERDICT_"+family+":improves_untrained="+str(
             z["trained_improves_untrained"])+":beats_historical="+str(
             z["trained_improves_historical"])+":beats_fixed="+str(
             z["trained_development_superior_to_fixed"]),flush=True)

if __name__=="__main__":
    try:main()
    except (ValueError,OSError,TypeError,KeyError,ArithmeticError) as e:
        print("F124AH_COMPARISON_QUARANTINE="+str(e),file=sys.stderr)
        sys.exit(1)
