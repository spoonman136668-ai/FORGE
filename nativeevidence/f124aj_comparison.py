"""F124-AJ separate authentic pretrained O/U, source-independent fixed 16-cell
consistency and fixed injected-index references vs FIT-supervised raw operator.

Source evaluator never used in classification. The fixed controls are old
bytecode rebound only to new public graph admission.
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
from types import FunctionType
import f124aj_source as S
import f124aj_raw_neural as N
import f124ad_intermediate_credit as AD
import f124ag_noisy_controls as AG
import f124ai_calibration as AI
import f124v_yggdrasil_causal_trace as V

SCHEMA="forge.research.f124aj.original-vs-raw-learned.v1"
ARMS=("historical_O_combined","historical_U_combined",
      "fixed_consistency16","fixed_collisionfree",
      "untrained_raw_neural","trained_raw_neural")

def bind(fn,name,mod):
    ns=dict(fn.__globals__);ns[name]=mod
    out=FunctionType(fn.__code__,ns,fn.__name__,
                     fn.__defaults__,fn.__closure__)
    S.need(out.__code__ is fn.__code__,"ORIGINAL_BYTECODE_CHANGED")
    return out

def original():
    return bind(AD.forward,"source",S)

def fixed_consistency(g):
    return bind(AG.bounded_public_control,"source",S)(g,"consistency16")

def fixed_collisionfree(g):
    return bind(AI.fingerprint_infer,"S",S)(
      g,"fixed",{"slope":0.,"bias":0.},.5)

def predict(arm,g,trained,threshold,weights,old):
    if arm=="fixed_consistency16":return fixed_consistency(g)
    if arm=="fixed_collisionfree":return fixed_collisionfree(g)
    if arm=="untrained_raw_neural":
        return N.infer(g,trained["initial"],.5)
    if arm=="trained_raw_neural":
        return N.infer(g,trained["model"],threshold)
    who=arm.split("_")[1]
    return old(who,g,weights,gamma=.1,penalty=1.)

def cohort(phase):
    return {fam:[(seed,list(v),*S.build(fam,seed,v,phase))
                  for v in S.VECTORS for seed in S.COHORTS[fam][phase]]
             for fam in S.FAMILIES}

def evaluate(phase,trained,threshold,weights):
    old=original()
    results={}
    for family,cases in cohort(phase).items():
        arms={arm:{"pairs":0,"correct":0,"FP":0,"FN":0,
             "by_depth":{str(d):{"pairs":0,"correct":0,"FP":0,"FN":0}
                           for d in (10,11,12)},"cases":[]} for arm in ARMS}
        for seed,v,p,n in cases:
            answers={arm:(predict(arm,p,trained,threshold,weights,old),
                          predict(arm,n,trained,threshold,weights,old))
                     for arm in ARMS}
            # Strictly after blinded inference, independently admit source.
            S.need(S.semantic_routes(p)==1 and S.semantic_routes(n)==0,
                   "SEMANTIC_ORACLE_AFTER_BLIND_INFERENCE")
            for arm,(pos,neg) in answers.items():
                source=arms[arm]
                S.need(not pos.get("blocked",False) and
                       not neg.get("blocked",False),"COMPARATOR_BLOCKED")
                actual=bool(pos["prediction"] and not neg["prediction"])
                source["correct"]+=int(actual)
                source["FP"]+=int(neg["prediction"])
                source["FN"]+=int(not pos["prediction"])
                source["pairs"]+=1
                depth=str(len(p["roles"]))
                d=source["by_depth"][depth]
                d["pairs"]+=1;d["correct"]+=int(actual)
                d["FP"]+=int(neg["prediction"])
                d["FN"]+=int(not pos["prediction"])
                pc=pos.get("actual_cell_peak",
                       pos.get("final_active",0)+pos.get("final_retained",0))
                nc=neg.get("actual_cell_peak",
                       neg.get("final_active",0)+neg.get("final_retained",0))
                S.need(pc<=16 and nc<=16,"ORIGINAL_STATE_CAP")
                source["cases"].append({"seed":seed,"vector":v,
                    "depth":int(depth),"paired_correct":actual,
                    "positive":pos["prediction"],"negative":neg["prediction"],
                    "positive_cells":pc,"negative_cells":nc,
                    "positive_logit_hex":pos.get("logit_hex"),
                    "negative_logit_hex":neg.get("logit_hex"),
                    "positive_edge_scans":pos.get("edge_scans"),
                    "negative_edge_scans":neg.get("edge_scans"),
                    "raw_event_packed":pos.get("packed_33bit_cell_payload",False)})
        for r in arms.values():
            S.need(r["pairs"]==48 and len(r["cases"])==48 and
              all(x["pairs"]==16 for x in r["by_depth"].values()),
              "FROZEN_DENOMINATORS")
        results[family]={"arms":arms,"qualifies_superiority":(
           arms["trained_raw_neural"]["correct"]>
           max(arms["fixed_consistency16"]["correct"],
               arms["fixed_collisionfree"]["correct"]) and
           arms["trained_raw_neural"]["FP"]==0),
           "development_learning_gain":(
           arms["trained_raw_neural"]["correct"]>
           arms["untrained_raw_neural"]["correct"])}
    return results

def main():
    ap=argparse.ArgumentParser()
    for k in ("o","r","s","u"):ap.add_argument("--original-"+k,required=True)
    ap.add_argument("--trained-receipt",required=True)
    ap.add_argument("--output",required=True)
    a=ap.parse_args()
    S.frozen()
    blob=Path(a.trained_receipt).read_bytes()
    saved=json.loads(blob)
    S.need(saved["schema"]==N.SCHEMA and
           saved["freeze_blob"]==S.PROTOCOL_BLOB and
           saved["no_DEV_training_or_selection"] and
           saved["learned_parameters"]==49,"AUTHENTIC_FIT_RECEIPT")
    weights=V.original_weights(a.original_o,a.original_r,
                               a.original_s,a.original_u)
    fit=evaluate("FIT",saved["trained"],saved["selected_threshold"],weights)
    dev=evaluate("DEV",saved["trained"],saved["selected_threshold"],weights)
    report={"schema":SCHEMA,"freeze_blob":S.PROTOCOL_BLOB,
      "training_receipt_sha256":hashlib.sha256(blob).hexdigest(),
      "original_historical_fitted_weights_unchanged":True,
      "trained_network_49_global_params_and_threshold":50,
      "first_hop_packed_score_requires_real_byte_cost_measure":True,
      "original_state_cell_count_limit":16,
      "FIT_qualification":saved["qualified_FIT_zero_FP_with_positive_sensitivity"],
      "new_DEV_never_selected":True,"FIT":fit,"DEV":dev,
      "protected_first_use":False,"science_accepted":False,
      "optimizer_promoted":False}
    path=Path(a.output)
    S.need(path.parent.is_dir() and not path.exists(),"EXCLUSIVE_EVIDENCE")
    raw=(json.dumps(report,sort_keys=True,indent=2)+"\n").encode()
    with path.open("xb") as f:f.write(raw)
    print("F124AJ_COMPARISON_SHA256="+hashlib.sha256(raw).hexdigest(),flush=True)
    for family,row in dev.items():
        for arm,d in row["arms"].items():
            print("F124AJ_DEV_"+family+"_"+arm+
              ":correct="+str(d["correct"])+"/48:FP="+str(d["FP"])+
              ":FN="+str(d["FN"]),flush=True)
        print("F124AJ_VERDICT_"+family+":beats_fixed="+
              str(row["qualifies_superiority"])+":learning_gain="+
              str(row["development_learning_gain"]),flush=True)

if __name__=="__main__":
    try:main()
    except (ValueError,OSError,KeyError,TypeError,ArithmeticError) as e:
        print("F124AJ_COMPARISON_QUARANTINE="+str(e),file=sys.stderr)
        sys.exit(1)
