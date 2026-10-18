"""F124-AK independent source-backed original O/U and fixed baselines versus
raw intermediate-supervised neural learner and ablations on fresh DEV cases.
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
from types import FunctionType
import f124ak_source as S
import f124ak_learned as L
import f124ad_intermediate_credit as AD
import f124ag_noisy_controls as AG
import f124ai_calibration as AI
import f124v_yggdrasil_causal_trace as V

SCHEMA="forge.research.f124ak.original-vs-intermediate-supervised.v1"
ARMS=("historical_O_combined","historical_U_combined",
      "fixed_consistency16","fixed_collisionfree",
      "untrained_hop_relation","intermediate_trained_untrained_binder",
      "trained_hop_relation")

def bind(old,name,source):
    globals_=dict(old.__globals__);globals_[name]=source
    new=FunctionType(old.__code__,globals_,old.__name__,
                     old.__defaults__,old.__closure__)
    S.need(new.__code__ is old.__code__,"HISTORICAL_CONTROL_BYTECODE")
    return new
def old_original():
    return bind(AD.forward,"source",S)
def fixed_consistency(g):
    return bind(AG.bounded_public_control,"source",S)(g,"consistency16")
def fixed_collisionfree(g):
    return bind(AI.fingerprint_infer,"S",S)(
        g,"fixed",{"slope":0.,"bias":0.},.5)
def predict(arm,g,trained,threshold,weights,old):
    if arm=="fixed_consistency16":return fixed_consistency(g)
    if arm=="fixed_collisionfree":return fixed_collisionfree(g)
    if arm=="trained_hop_relation":
        return L.infer(g,trained["model"],threshold)
    if arm=="untrained_hop_relation":
        return L.infer(g,trained["initial"],.5)
    if arm=="intermediate_trained_untrained_binder":
        m=json.loads(json.dumps(trained["model"]))
        m["head"]={"w":[0.,0.,0.,0.],"b":0.}
        return L.infer(g,m,.5)
    who=arm.split("_")[1]
    return old(who,g,weights,gamma=.1,penalty=1.)

def evaluation(phase,trained,threshold,weights):
    old=old_original()
    data={}
    for family in S.FAMILIES:
        arms={arm:{"pairs":0,"correct":0,"FP":0,"FN":0,
               "by_depth":{str(d):{"pairs":0,"correct":0,"FP":0,"FN":0}
                           for d in (10,11,12)},"cases":[]}
               for arm in ARMS}
        for vector in S.VECTORS:
            for seed in S.COHORTS[family][phase]:
                pos,neg=S.build(family,seed,vector,phase)
                # Run every arm blind before source-only semantic adjudication.
                obs={arm:(predict(arm,pos,trained,threshold,weights,old),
                          predict(arm,neg,trained,threshold,weights,old))
                     for arm in ARMS}
                S.need(S.semantic_routes(pos)==1 and
                       S.semantic_routes(neg)==0,
                       "POST_PREDICTION_SOURCE_TRUTH")
                for arm,(p,n) in obs.items():
                    S.need(not p.get("blocked",False) and
                           not n.get("blocked",False),"INAPPLICABLE_STRONG_CONTROL")
                    true=bool(p["prediction"] and not n["prediction"])
                    result=arms[arm]
                    result["pairs"]+=1;result["correct"]+=int(true)
                    result["FP"]+=int(n["prediction"])
                    result["FN"]+=int(not p["prediction"])
                    d=result["by_depth"][str(len(pos["roles"]))]
                    d["pairs"]+=1;d["correct"]+=int(true)
                    d["FP"]+=int(n["prediction"])
                    d["FN"]+=int(not p["prediction"])
                    pc=p.get("actual_cell_peak",
                        p.get("final_active",0)+p.get("final_retained",0))
                    nc=n.get("actual_cell_peak",
                        n.get("final_active",0)+n.get("final_retained",0))
                    S.need(pc<=16 and nc<=16,"ORIGINAL_16_PERSISTENT_CELLS")
                    result["cases"].append({
                        "seed":seed,"vector":list(vector),
                        "depth":len(pos["roles"]),"paired_correct":true,
                        "positive_prediction":p["prediction"],
                        "negative_prediction":n["prediction"],
                        "positive_cell_peak":pc,"negative_cell_peak":nc,
                        "original_positive_logit_hex":p.get("logit_hex"),
                        "original_negative_logit_hex":n.get("logit_hex"),
                        "positive_public_edge_scans":p.get("edge_scans"),
                        "negative_public_edge_scans":n.get("edge_scans")})
        for arm,result in arms.items():
            S.need(result["pairs"]==48 and len(result["cases"])==48 and
               all(q["pairs"]==16 for q in result["by_depth"].values()),
               "MISSING_PAIRS_OR_DEPTH")
        data[family]={"arms":arms,
              "learned_meets_zero_FP":arms["trained_hop_relation"]["FP"]==0,
              "learned_beats_both_fixed":(
                  arms["trained_hop_relation"]["FP"]==0 and
                  arms["trained_hop_relation"]["correct"]>
                    max(arms["fixed_consistency16"]["correct"],
                        arms["fixed_collisionfree"]["correct"])),
              "learned_improves_untrained_head":(
                  arms["trained_hop_relation"]["correct"]>
                  arms["intermediate_trained_untrained_binder"]["correct"])}
    return data

def main():
    ap=argparse.ArgumentParser()
    for key in ("o","r","s","u"):ap.add_argument("--original-"+key,required=True)
    ap.add_argument("--trained-receipt",required=True)
    ap.add_argument("--output",required=True)
    a=ap.parse_args()
    S.frozen()
    training=Path(a.trained_receipt).read_bytes()
    receipt=json.loads(training)
    S.need(receipt["schema"]==L.SCHEMA and
        receipt["freeze_blob"]==S.PROTOCOL_BLOB and
        receipt["no_DEV_training_or_selection"] and
        receipt["additional_global_params"]==39,
        "FIT_PRETRAINED_CUSTODY_MISMATCH")
    historical=V.original_weights(a.original_o,a.original_r,
                                 a.original_s,a.original_u)
    fit=evaluation("FIT",receipt["trained"],
                   receipt["selected_threshold"],historical)
    dev=evaluation("DEV",receipt["trained"],
                   receipt["selected_threshold"],historical)
    report={"schema":SCHEMA,"freeze_blob":S.PROTOCOL_BLOB,
      "trained_receipt_sha256":hashlib.sha256(training).hexdigest(),
      "original_O_U_authentic_FIT_weights_unchanged":True,
      "FIT_choice_qualified":receipt["qualified_zero_FP_and_minimum_positive_sensitivity"],
      "DEV_is_untrained_and_no_model_selection":True,
      "raw_operator_learned_parameter_count":39,
      "original_16_cell_cap":16,
      "FIT":fit,"DEV":dev,"protected_first_use":False,
      "independent_science_accepted":False,
      "optimizer_promoted":False}
    out=Path(a.output)
    S.need(out.parent.is_dir() and not out.exists(),"EXCLUSIVE_RESULT")
    raw=(json.dumps(report,sort_keys=True,indent=2)+"\n").encode()
    with out.open("xb") as f:f.write(raw)
    print("F124AK_COMPARISON_SHA256="+hashlib.sha256(raw).hexdigest(),flush=True)
    for family,item in dev.items():
        for arm,row in item["arms"].items():
            print("F124AK_DEV_"+family+"_"+arm+
               ":correct="+str(row["correct"])+"/48:FP="+str(row["FP"])+
               ":FN="+str(row["FN"]),flush=True)
        print("F124AK_VERDICT_"+family+":superior_to_both_fixed="+
              str(item["learned_beats_both_fixed"])+":improves_head="+
              str(item["learned_improves_untrained_head"]),flush=True)

if __name__=="__main__":
    try:main()
    except (ValueError,OSError,KeyError,TypeError,ArithmeticError) as e:
        print("F124AK_COMPARISON_QUARANTINE="+str(e),file=sys.stderr)
        sys.exit(1)
