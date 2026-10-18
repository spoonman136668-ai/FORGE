"""F124-AM mask-aware recursive state: newly FIT-trained readout vs fixed.

Known and UNKNOWN public bits are treated differently. The raw public
possible-mask set is ENGINEERED, so this is learned calibration of a
recurrence, NOT learned discovery of bitwise set intersection. Both use the
same 7 active +9 retained original node/raw16/score cell fields, with a
larger packed Python integer in score. No oracle or label enters inference.
"""
from __future__ import annotations
import argparse,hashlib,json,math,random,sys
from pathlib import Path
import f124am_masked_source as S
SCHEMA="forge.research.f124am.FIT-recurrent-readout.v1"
ARMS=("fixed_maskset","untrained_masked","learned_masked")
THRESHOLDS=(.1,.2,.3,.4,.5,.6,.7,.8,.9)
EPOCHS=220;LR=.13;L2=.0001;WEIGHTS=6;TOTAL_GLOBALS=7
N=len(S.MASKS)
LOW_MASK=(1<<N)-1
EVENT_SHIFT=N
CONFLICT_SHIFT=N+4
MATCH_SHIFT=N+8
PARTIAL_SHIFT=N+12
LIMIT_SHIFT=N+16
def pack(anchor,events,conflicts,matches,partials):
    S.need(anchor>0 and anchor<=LOW_MASK and
           0<=events<=4 and 0<=conflicts<=4 and
           0<=matches<=4 and 0<=partials<=4,"PACK_SCORE_SHAPE")
    return (anchor|(events<<EVENT_SHIFT)|(conflicts<<CONFLICT_SHIFT)|
            (matches<<MATCH_SHIFT)|(partials<<PARTIAL_SHIFT))
def unpack(score):
    return (score&LOW_MASK,
      (score>>EVENT_SHIFT)&15,(score>>CONFLICT_SHIFT)&15,
      (score>>MATCH_SHIFT)&15,(score>>PARTIAL_SHIFT)&15)
def sigmoid(z):
    if z>=0:return 1./(1.+math.exp(-min(700.,z)))
    p=math.exp(max(-700.,z));return p/(1.+p)
def features(score):
    mask,events,conflicts,matches,partials=unpack(score)
    return (float(conflicts),float(matches),float(mask.bit_count()/10.),
            float(events),float(partials),1.)
def score_prob(model,feature):
    return sigmoid(sum(w*x for w,x in zip(model,feature)))
def candidate(carried,src):
    """Public raw candidate bitmasks; NEVER source semantic label/oracle."""
    if carried is None:return 0
    # More than two DEFINITE mismatches is outside both frozen hypotheses.
    definite=sum(a!=b for a,b in zip(carried,src) if b is not None)
    if definite>2:return -1
    return S.allowed_masks(carried,src)
def next_state(score,cand,partial,fixed=False):
    if cand==0:return score
    if cand<0:return None
    if score==0:return pack(cand,1,0,0,int(partial))
    anchor,events,conflicts,matches,partials=unpack(score)
    if events>=4:return None
    intersection=anchor&cand
    if fixed and not intersection:return None
    return pack(intersection if fixed else anchor,events+1,
        conflicts+int(not intersection),
        matches+int(bool(intersection)),partials+int(partial))
def ordered_edges(graph):
    return sorted(graph["edges"],key=lambda e:(
        e["from"],e["to"],e["role"],
        tuple(-1 if v is None else v for v in e["src_bits"]),
        tuple(e["dst_bits"])))
def inference(graph,model=None,threshold=.5,mode="learned"):
    S.validate_public(graph)
    S.need(mode in ("fixed","learned","untrained"),"INFERENCE_MODE")
    if mode!="fixed":S.need(len(model)==6,"READOUT_COEFFICIENTS")
    active=[(graph["start"],None,0)]
    retained=[];peak=1;scans=0;bit_ops=0;largest_score=0
    edges=ordered_edges(graph)
    for role in graph["roles"]:
        states=[]
        for node,carried,score in active+retained:
            for e in edges:
                scans+=1
                if e["from"]!=node or e["role"]!=role:continue
                if carried is not None:bit_ops+=16
                cand=candidate(carried,e["src_bits"])
                updated=next_state(score,cand,
                    any(v is None for v in e["src_bits"]),mode=="fixed")
                if updated is None:continue
                if updated:largest_score=max(largest_score,updated.bit_length())
                states.append((e["to"],tuple(e["dst_bits"]),updated))
        # Deterministic public-only destination diversity. Ranking uses
        # observed event count, never the source label or family.
        states.sort(key=lambda v:(
            -(unpack(v[2])[1] if v[2] else 0),v[0],v[1],v[2]))
        selected=[];seen=set()
        for item in states:
            if item[0] in seen:continue
            seen.add(item[0]);selected.append(item)
            if len(selected)==7:break
        chosen={id(x) for x in selected}
        active=selected[:7]
        retained=[v for v in states if id(v) not in chosen][:9]
        peak=max(peak,len(active)+len(retained))
        S.need(len(active)<=7 and len(retained)<=9 and peak<=16,
               "PERSISTENT_ORIGINAL_CAP")
    answers=[]
    for node,_,score in active+retained:
        if node!=graph["target"] or not score:continue
        anchor,events,conflicts,matches,partials=unpack(score)
        if not 2<=events<=4:continue
        if mode=="fixed":
            accept=anchor!=0
        else:
            accept=score_prob(model,features(score))>=threshold
        answers.append(bool(accept))
    return {"prediction":any(answers),"blocked":False,
      "actual_cell_peak":peak,"edge_scans":scans,
      "public_bit_comparisons":bit_ops,
      "maximum_packed_score_bit_length":largest_score,
      "global_model_parameters":7 if mode!="fixed" else 0}
def FIT_teacher(graph):
    """FIT-only extract PUBLIC route events, never source semantic oracle."""
    S.validate_public(graph)
    states=[(graph["start"],None,0)]
    for role in graph["roles"]:
        nxt=[]
        for node,carried,score in states:
            for e in graph["edges"]:
                if node!=e["from"] or role!=e["role"]:continue
                q=candidate(carried,e["src_bits"])
                s=next_state(score,q,
                    any(x is None for x in e["src_bits"]),False)
                if s is None:continue
                nxt.append((e["to"],e["dst_bits"],s))
                S.need(len(nxt)<=128,"TRAIN_PUBLIC_ROUTE_BUDGET")
        states=nxt
    endings=[score for node,_,score in states
             if node==graph["target"] and score and
             2<=unpack(score)[1]<=4]
    S.need(len(endings)==1,"FIT_UNIQUE_PUBLIC_CANDIDATE_ROUTE")
    return features(endings[0])
def FIT_cases():
    data=[]
    for fam in S.FAMILIES:
        for v in S.VECTORS:
            for seed in S.COHORTS[fam]["FIT"]:
                pos,neg=S.build(fam,seed,v,"FIT")
                data.extend(((FIT_teacher(pos),1),(FIT_teacher(neg),0)))
    S.need(len(data)==288 and sum(y for _,y in data)==144,
           "FIT_LABELLED_EXAMPLE_COUNT")
    return data
def train():
    data=FIT_cases()
    rng=random.Random(int.from_bytes(hashlib.sha256(
           b"forge/F124AM/recurrent-weight-init/v1").digest()[:12],"big"))
    initial=[(rng.random()-.5)*.1 for _ in range(6)]
    weights=list(initial);first=last=None
    for epoch in range(EPOCHS):
        loss=0.
        for feature,label in data:
            p=score_prob(weights,feature)
            loss-=label*math.log(max(p,1e-12)) + (
                   1-label)*math.log(max(1-p,1e-12))
            for i,x in enumerate(feature):
                g=(p-label)*x+L2*weights[i]
                weights[i]-=LR*max(-2.,min(2.,g))
        avg=loss/len(data)
        if epoch==0:first=avg
        last=avg
    delta=math.sqrt(sum((a-b)**2 for a,b in zip(weights,initial)))
    S.need(delta>0 and math.isfinite(delta) and
           all(math.isfinite(x) for x in weights),"NO_TRUE_FIT_LEARNING")
    return {"model":weights,"initial":initial,"parameter_count":6,
       "additional_global_parameter_count":7,
       "epochs":EPOCHS,"lr":LR,"l2":L2,"FIT_samples":len(data),
       "loss_first":first,"loss_last":last,"learned_L2":delta,
       "engineered_error_mask_and_anchor_features":True}
def phase(when,mode,model,threshold):
    results={}
    for family in S.FAMILIES:
        cases=[];depths={str(n):{"pairs":0,"correct":0,"FP":0,"FN":0}
                          for n in (10,11,12)}
        for vector in S.VECTORS:
            for seed in S.COHORTS[family][when]:
                pos,neg=S.build(family,seed,vector,when)
                p=inference(pos,model,threshold,mode)
                n=inference(neg,model,threshold,mode)
                correct=p["prediction"] and not n["prediction"]
                k=str(len(pos["roles"]))
                d=depths[k];d["pairs"]+=1
                d["correct"]+=int(correct)
                d["FP"]+=int(n["prediction"])
                d["FN"]+=int(not p["prediction"])
                cases.append({"seed":seed,"vector":list(vector),"depth":int(k),
                   "paired_correct":correct,"positive":p["prediction"],
                   "negative":n["prediction"],"positive_cells":p["actual_cell_peak"],
                   "negative_cells":n["actual_cell_peak"],
                   "positive_score_bits":p["maximum_packed_score_bit_length"],
                   "negative_score_bits":n["maximum_packed_score_bit_length"]})
        S.need(len(cases)==48 and all(v["pairs"]==16 for v in depths.values()),
               "DEPTH_OR_FAMILY_DENOMINATOR")
        results[family]={"pairs":48,"correct":sum(x["paired_correct"] for x in cases),
             "FP":sum(x["negative"] for x in cases),
             "FN":sum(not x["positive"] for x in cases),
             "by_depth":depths,"cases":cases}
    return results
def select_FIT(fitted):
    curve=[]
    for t in THRESHOLDS:
        results=phase("FIT","learned",fitted["model"],t)
        correct=sum(z["correct"] for z in results.values())
        FP=sum(z["FP"] for z in results.values())
        FN=sum(z["FN"] for z in results.values())
        curve.append({"threshold":t,"correct":correct,"FP":FP,
                      "FN":FN,"positive_recall":144-FN})
    eligible=[x for x in curve if x["FP"]==0 and x["positive_recall"]>=72]
    chosen=min(eligible,key=lambda x:(-x["correct"],x["threshold"])) if eligible else None
    return chosen,curve
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",required=True)
    a=ap.parse_args()
    S.frozen()
    learned=train()
    chosen,curve=select_FIT(learned)
    threshold=chosen["threshold"] if chosen is not None else THRESHOLDS[0]
    # No DEV constructed before the original frozen FIT threshold decision.
    dev=phase("DEV","learned",learned["model"],threshold)
    ablation=phase("DEV","untrained",learned["initial"],.5)
    fixed=phase("DEV","fixed",None,0.)
    result={"schema":SCHEMA,"freeze_blob":S.PROTOCOL_BLOB,
      "train_only_FIT":True,"no_DEV_training_or_selection":True,
      "learned":learned,"FIT_curve":curve,"FIT_choice":chosen,
      "FIT_qualified_both_FP_and_positive_recall":chosen is not None,
      "selected_threshold":threshold,"DEV":dev,"untrained_DEV":ablation,
      "fixed_DEV":fixed,"original_16_cells":True,
      "new_score_fields":0,"additional_model_global_parameters":7,
      "protected_first_use":False,"independent_science_accepted":False,
      "optimizer_promoted":False}
    path=Path(a.output)
    S.need(path.parent.is_dir() and not path.exists(),"REPEATED_EVIDENCE")
    data=(json.dumps(result,sort_keys=True,indent=2)+"\n").encode()
    with path.open("xb") as f:f.write(data)
    print("F124AM_TRAIN_SHA256="+hashlib.sha256(data).hexdigest(),flush=True)
    print("F124AM_TRAIN_DELTA="+str(learned["learned_L2"]),flush=True)
    print("F124AM_TRAIN_LOSS="+str(learned["loss_first"])+
          ":final="+str(learned["loss_last"]),flush=True)
    print("F124AM_FIT_SELECTION="+json.dumps(chosen),flush=True)
    for fam in S.FAMILIES:
        for key,group in (("learned",dev),("untrained",ablation),("fixed",fixed)):
            r=group[fam]
            print("F124AM_DEV_"+fam+"_"+key+":correct="+str(r["correct"])+
                  "/48:FP="+str(r["FP"])+":FN="+str(r["FN"]),flush=True)
if __name__=="__main__":
    try:main()
    except (ValueError,OSError,TypeError,KeyError,ArithmeticError) as e:
        print("F124AM_FIT_QUARANTINE="+str(e),file=sys.stderr)
        sys.exit(1)
