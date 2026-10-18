"""F124-AL frozen AK transfer and four independent baseline/evaluation arms.

The F124AK FIT-trained model is READ-ONLY. AK.infer's original code object is
unchanged; the only rebinding is the newly frozen public graph validator.
Includes the original historical fixed controls and a separately frozen
deterministic generalized mask controller (no family or semantic-oracle input).
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
from types import FunctionType
import f124al_transfer_source as S
import f124ak_learned as AK
import f124ag_noisy_controls as AG
import f124ai_calibration as AI
import f124o_native_learners as O
SCHEMA="forge.research.f124al.locked-AK-transfer-controls.v1"
TRAIN_SHA="892155207d036b57ae62a29d77b51248fb4ec09bbe87621a88d0ceaeb1d4914a"
ARMS=("ak_original_frozen","fixed_consistency16",
      "fixed_collisionfree","fixed_generalized_mask")
CAP=16

def clone(fn,key,source):
    globals_=dict(fn.__globals__);globals_[key]=source
    bound=FunctionType(fn.__code__,globals_,fn.__name__,
                       fn.__defaults__,fn.__closure__)
    S.need(bound.__code__ is fn.__code__,"FROZEN_ORIGINAL_MODEL_CODE_CHANGED")
    return bound
def ak_original():
    return clone(AK.infer,"S",S)
def old_fixed_consistency(g):
    return clone(AG.bounded_public_control,"source",S)(g,"consistency16")
def old_fixed_collisionfree(g):
    return clone(AI.fingerprint_infer,"S",S)(g,"fixed",{
        "slope":0.,"bias":0.},.5)

def generalized(g):
    """New source-independent fixed policy: require 2 or 3 same 1/2-bit
    nonzero change masks, retaining ONLY original node/raw16/score triples.
    Uses original 7 active/9 retained cells and unchanged public sort logic.
    """
    S.validate_public(g)
    edges=O.sorted_edges(g)
    active=[(g["start"],None,0)]
    retained=[]
    scans=comparisons=0;peak=1
    for role in g["roles"]:
        candidates=[]
        for node,carried,score in active+retained:
            for e in edges:
                scans+=1
                if e["from"]!=node or e["role"]!=role:continue
                mask=S.mask_of(carried,e["src_bits"])
                if carried is not None:comparisons+=16
                if mask.bit_count()>2:continue
                if mask:
                    if score==0:
                        next_score=(1<<16)|mask
                    else:
                        seen_mask=score&65535
                        count=score>>16
                        if mask!=seen_mask or count>=3:continue
                        next_score=((count+1)<<16)|seen_mask
                else:next_score=score
                candidates.append((e["to"],tuple(e["dst_bits"]),next_score))
        candidates.sort(key=lambda x:(
            0 if x[2]>>16>=2 else 1,x[0],x[1],x[2]))
        selected=[];nodes=set()
        for cell in candidates:
            if cell[0] in nodes:continue
            nodes.add(cell[0]);selected.append(cell)
            if len(selected)==7:break
        selected_ids={id(x) for x in selected}
        for cell in candidates:
            if len(selected)==7:break
            if id(cell) not in selected_ids:selected.append(cell)
        selected_ids={id(x) for x in selected}
        active=selected[:7]
        retained=[c for c in candidates if id(c) not in selected_ids][:9]
        peak=max(peak,len(active)+len(retained))
        S.need(len(active)<=7 and len(retained)<=9 and peak<=16,
               "GENERALIZED_FIXED_OVER_16_CELLS")
    return {"prediction":any(
        n==g["target"] and (score>>16)>=2 for n,_,score in active+retained),
        "blocked":False,"actual_cell_peak":peak,"edge_scans":scans,
        "bit_comparisons":comparisons,"score_packed_mask_event_count":True}

def predict(name,g,trained,threshold):
    if name=="ak_original_frozen":
        return ak_original()(g,trained,threshold)
    if name=="fixed_consistency16":
        return old_fixed_consistency(g)
    if name=="fixed_collisionfree":
        return old_fixed_collisionfree(g)
    if name=="fixed_generalized_mask":
        return generalized(g)
    raise ValueError("UNREGISTERED_ARM")

def load_receipt(path):
    raw=Path(path).read_bytes()
    S.need(hashlib.sha256(raw).hexdigest()==TRAIN_SHA,
           "AUTHENTIC_ORIGINAL_AK_TRAINED_FIT_RECEIPT_HASH")
    data=json.loads(raw)
    S.need(data["schema"]=="forge.research.f124ak.FIT-trained-intermediate-and-binder.v1" and
        data["freeze_blob"]=="53c7cd76e2a8fc44be05e186b989ef8b1a3ad86f" and
        data["qualified_zero_FP_and_minimum_positive_sensitivity"] and
        data["selected_threshold"]==.1 and
        data["trained"]["parameter_count"]==39,
        "AUTHENTIC_ORIGINAL_AK_FIT_MODEL_CONTRACT")
    return data

def cases(phase,family):
    return [(seed,list(v),*S.build(family,seed,v,phase))
           for v in S.VECTORS for seed in S.COHORTS[family][phase]]

def evaluate(phase,trained,threshold):
    families={}
    for family in S.FAMILIES:
        arms={name:{"pairs":0,"correct":0,"FP":0,"FN":0,"blocked":0,
            "by_depth":{str(i):{"pairs":0,"correct":0,"FP":0,"FN":0}
                        for i in (10,11,12)},"cases":[]}
              for name in ARMS}
        for seed,v,pos,neg in cases(phase,family):
            # Run ALL inference before accessing source-only semantic truth.
            decisions={name:(predict(name,pos,trained,threshold),
                             predict(name,neg,trained,threshold))
                       for name in ARMS}
            S.need(S.semantic_routes(pos)==1 and S.semantic_routes(neg)==0,
                   "POST_INFERENCE_SOURCE_ADMISSION")
            for name,(p,n) in decisions.items():
                z=arms[name]
                blocked=bool(p.get("blocked",False) or n.get("blocked",False))
                S.need(not blocked,"STRONG_FIXED_OR_MODEL_BLOCKED")
                good=bool(p["prediction"] and not n["prediction"])
                z["pairs"]+=1;z["correct"]+=int(good)
                z["FP"]+=int(n["prediction"]);z["FN"]+=int(not p["prediction"])
                depth=str(len(pos["roles"]))
                d=z["by_depth"][depth]
                d["pairs"]+=1;d["correct"]+=int(good)
                d["FP"]+=int(n["prediction"]);d["FN"]+=int(not p["prediction"])
                for result in (p,n):
                    S.need(result.get("actual_cell_peak",0)<=16,
                           "PERSISTENT_CELL_BUDGET_VIOLATED")
                z["cases"].append({"seed":seed,"vector":v,
                    "depth":int(depth),"positive":p["prediction"],
                    "negative":n["prediction"],"correct":good,
                    "positive_cell_peak":p.get("actual_cell_peak"),
                    "negative_cell_peak":n.get("actual_cell_peak"),
                    "positive_scans":p.get("edge_scans"),
                    "negative_scans":n.get("edge_scans")})
        for name,z in arms.items():
            S.need(z["pairs"]==48 and len(z["cases"])==48 and
                 all(d["pairs"]==16 for d in z["by_depth"].values()),
                 "FROZEN_DENOMINATOR")
        families[family]={"arms":arms,
           "AK_beats_strongest_fixed":(
              arms["ak_original_frozen"]["correct"]>
              max(arms["fixed_consistency16"]["correct"],
                  arms["fixed_collisionfree"]["correct"],
                  arms["fixed_generalized_mask"]["correct"]) and
              arms["ak_original_frozen"]["FP"]==0),
           "AK_qualified_sensitivity":(
              arms["ak_original_frozen"]["FP"]==0 and
              arms["ak_original_frozen"]["FN"]<48)}
    return families

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--original-ak-receipt",required=True)
    parser.add_argument("--output",required=True)
    a=parser.parse_args()
    S.frozen()
    original=load_receipt(a.original_ak_receipt)
    model=original["trained"]["model"]
    threshold=original["selected_threshold"]
    fit=evaluate("FIT",model,threshold)
    dev=evaluate("DEV",model,threshold)
    report={"schema":SCHEMA,"freeze_blob":S.PROTOCOL_BLOB,
      "original_AK_receipt_SHA256":TRAIN_SHA,
      "original_AK_fitted_weights_unchanged":True,
      "original_AK_python_bytecode_unchanged":True,
      "no_new_FIT_or_DEV_model_training_or_selection":True,
      "AK_global_params":39,"original_cells":16,
      "new_generalized_fixed_no_labels_in_inference":True,
      "silent_slot_is_absent_event_NOT_missing_bit_mask":True,
      "FIT":fit,"DEV":dev,"protected_first_use":False,
      "independent_science_accepted":False,"optimizer_promoted":False}
    out=Path(a.output)
    S.need(out.parent.is_dir() and not out.exists(),"EVIDENCE_ALREADY_EXISTS")
    b=(json.dumps(report,sort_keys=True,indent=2)+"\n").encode()
    with out.open("xb") as f:f.write(b)
    print("F124AL_TRANSFER_SHA256="+hashlib.sha256(b).hexdigest(),flush=True)
    for fam,z in dev.items():
        for name,x in z["arms"].items():
            print("F124AL_DEV_"+fam+"_"+name+":paired="+str(x["correct"])+
                  "/48:FP="+str(x["FP"])+":FN="+str(x["FN"])+
                  ":blocked="+str(x["blocked"]),flush=True)
        print("F124AL_VERDICT_"+fam+":beats_fixed="+str(
              z["AK_beats_strongest_fixed"])+
              ":AK_has_positive_sensitivity="+str(
              z["AK_qualified_sensitivity"]),flush=True)
if __name__=="__main__":
    try:main()
    except (ValueError,OSError,KeyError,TypeError,ArithmeticError) as e:
        print("F124AL_QUARANTINED="+str(e),file=sys.stderr);sys.exit(1)
