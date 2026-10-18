"""F124-AH genuine FIT-supervised scalar mismatch-fingerprint codebook.

Sixteen trainable bit-position embeddings, fit by deterministic contrastive
logistic SGD on fresh FIT-labelled public graphs only; a zero-FP FIT-only
threshold chooses completed two-error equality. During inference a single
learned scalar signature lives in the original cell.score field; original
(node,raw16,score) and 7 active + 9 retained slots remain exactly bounded.
No path oracle or label call inside inference. This is explicitly supervised
learning atop a hand-engineered mismatch extractor, NOT discovery of the
underlying bit-identity representation from first principles.
"""
from __future__ import annotations
import argparse,hashlib,json,math,sys
from pathlib import Path
import f124ah_source as source
import f124ag_noisy_controls as prior
import f124o_native_learners as O

SCHEMA="forge.research.f124ah.fit-supervised-scalar-fingerprint.v1"
FAMILIES=source.FAMILIES
GRID=(0.0001,0.001,0.01,0.04,0.09,0.16,0.25,0.49)
MARGIN_SQ=.09
LR=.075
L2=.0001
EPOCHS=100
PARAMETER_COUNT=17
MODELS=("untrained_fp","trained_fp")

def _training_path(graph):
    """FIT-only public near-tolerance path to the declared public target.

    Only called by fit(). Uses public role/edge data and FIT labels.
    Training supervision is not imported into inference().
    """
    source.validate_public(graph)
    paths=[(graph["start"],None,())]
    for role in graph["roles"]:
        nxt=[]
        for node,carried,errs in paths:
            for e in graph["edges"]:
                if node!=e["from"] or e["role"]!=role:continue
                mismatch=source.diff_bits(carried,e["src_bits"])
                if len(mismatch)>1:continue
                nxt.append((e["to"],e["dst_bits"],errs+mismatch))
                source.need(len(nxt)<=128,"FIT_SOURCE_ROUTE_CAP")
        paths=nxt
    endings=[err for node,_,err in paths
             if node==graph["target"] and len(err)==2]
    source.need(len(endings)==1,"FIT_PUBLIC_TARGET_UNIQUE")
    return endings[0]

def training_examples():
    examples=[]
    for family in FAMILIES:
        for v in source.VECTORS:
            for seed in source.COHORTS[family]["FIT"]:
                positive,negative=source.build(family,seed,v,"FIT")
                a=_training_path(positive);b=_training_path(negative)
                source.need(a[0]==a[1] and b[0]!=b[1],
                            "FIT_ONLY_LABELLED_RELATION_CONTRACT")
                examples.extend(((a[0],a[1],1),(b[0],b[1],0)))
    source.need(len(examples)==288,"EXACT_TRAINING_CASES")
    return examples

def init_codebook():
    return [((int.from_bytes(hashlib.sha256(
               ("forge/F124AH/SGD-deterministic/v1/"+str(bit)).encode()
             ).digest()[:8],"big")/float(2**64))-.5)*.03
            for bit in range(16)]

def _sigmoid(z):
    if z>=0:
        return 1./(1.+math.exp(-z))
    e=math.exp(z);return e/(1.+e)

def fit():
    source.frozen()
    samples=training_examples()
    initial=init_codebook()
    codes=list(initial)
    first_loss=last_loss=None
    for epoch in range(EPOCHS):
        loss=0.
        for first,second,y in samples:
            d=codes[first]-codes[second]
            z=(MARGIN_SQ-d*d) if y==0 else (d*d-MARGIN_SQ)
            loss+=math.log1p(math.exp(max(-50.,min(50.,z))))
            if y==0:
                # Different bit indices should separate in learned code
                # space. The gradient is derived from logistic negative loss.
                grad=2.*d*_sigmoid(z)
                move=LR*max(-1.,min(1.,grad))
                codes[first]+=move
                codes[second]-=move
            # Small L2 regularizer prevents unchecked scalar growth.
            codes[first]-=LR*L2*codes[first]
            if second!=first:codes[second]-=LR*L2*codes[second]
            codes[first]=max(-2.,min(2.,codes[first]))
            codes[second]=max(-2.,min(2.,codes[second]))
        avg=loss/len(samples)
        if epoch==0:first_loss=avg
        last_loss=avg
    delta=math.sqrt(sum((a-b)**2 for a,b in zip(initial,codes)))
    source.need(math.isfinite(delta) and delta>0. and
        all(math.isfinite(x) and abs(x)<=2. for x in codes),
        "NO_GENUINE_LEARNING_OR_FINITE_WEIGHTS")
    return {"codebook":codes,"initial":initial,"weight_delta_l2":delta,
        "loss_first":first_loss,"loss_last":last_loss,
        "epochs":EPOCHS,"lr":LR,"margin_sq":MARGIN_SQ,
        "parameter_count":PARAMETER_COUNT,
        "FIT_samples":len(samples)}

def inference(graph,codes,threshold):
    """Score from PUBLIC graph only; fingerprint uses existing score scalar.

    score=0 first error unknown; score=10+trained_code[bit] after first
    one-bit mismatch; score=-1 on valid learned second-bit similarity.
    Third noisy transition rejected. No new per-cell field introduced.
    """
    source.validate_public(graph)
    source.need(len(codes)==16 and threshold>=0.,"WEIGHT_SHAPE")
    edges=O.sorted_edges(graph)
    active=[(graph["start"],None,0.)]
    retained=[]
    scans=raw_bits=0
    max_cells=1
    for role in graph["roles"]:
        candidates=[]
        for node,carried,score in active+retained:
            for e in edges:
                scans+=1
                if e["from"]!=node or e["role"]!=role:continue
                mismatch=source.diff_bits(carried,e["src_bits"])
                if carried is not None:raw_bits+=16
                if len(mismatch)>1:continue
                if mismatch:
                    bit=mismatch[0]
                    if score==0.:
                        next_score=10.+codes[bit]
                    elif score>0.:
                        d=(score-10.)-codes[bit]
                        if d*d>threshold:continue
                        next_score=-1.
                    else:continue
                else:next_score=score
                candidates.append((e["to"],tuple(e["dst_bits"]),next_score))
        # Fixed ranked structure identical to the source-independent fixed
        # consistency comparator; codebook and threshold are the only
        # trained properties. No labels / oracle / family context.
        candidates.sort(key=lambda row:(
            0 if row[2]==-1. else 1,row[0],row[1],row[2]))
        winners=[];seen=set()
        for cell in candidates:
            if cell[0] in seen:continue
            seen.add(cell[0]);winners.append(cell)
            if len(winners)==7:break
        selected={id(x) for x in winners}
        for cell in candidates:
            if len(winners)==7:break
            if id(cell) not in selected:winners.append(cell)
        selected={id(x) for x in winners}
        active=winners[:7]
        retained=[x for x in candidates if id(x) not in selected][:9]
        max_cells=max(max_cells,len(active)+len(retained))
        source.need(len(active)<=7 and len(retained)<=9
          and max_cells<=16,"EXCEEDED_ORIGINAL_16_CELLS")
    pred=any(node==graph["target"] and score==-1.
             for node,_,score in active+retained)
    return {"prediction":pred,"actual_cell_peak":max_cells,
            "edge_scans":scans,"raw_bit_comparisons":raw_bits,
            "blocked":False}

def fit_threshold(trained):
    """FIT-only selection with zero false positives and frozen tie breaks."""
    fit_groups={}
    for family in FAMILIES:
        fit_groups[family]=[(source.build(family,seed,v,"FIT"))
            for v in source.VECTORS for seed in source.COHORTS[family]["FIT"]]
    curve=[]
    for threshold in GRID:
        correct=FP=FN=0
        for graphs in fit_groups.values():
            for positive,negative in graphs:
                pp=inference(positive,trained["codebook"],threshold)["prediction"]
                nn=inference(negative,trained["codebook"],threshold)["prediction"]
                correct+=int(pp and not nn);FP+=int(nn);FN+=int(not pp)
        curve.append({"threshold":threshold,"correct":correct,"FP":FP,"FN":FN})
    valid=[x for x in curve if x["FP"]==0]
    choice=sorted(valid,key=lambda x:(-x["correct"],x["threshold"]))[0] if valid else None
    return choice,curve

def evaluate(phase,codes,threshold):
    out={}
    for family in FAMILIES:
        rows=[];depths={str(d):{"pairs":0,"correct":0,"FP":0,"FN":0}
                           for d in (10,11,12)}
        for v in source.VECTORS:
            for seed in source.COHORTS[family][phase]:
                pp,nn=source.build(family,seed,v,phase)
                p=inference(pp,codes,threshold)
                n=inference(nn,codes,threshold)
                good=p["prediction"] and not n["prediction"]
                depth=str(len(pp["roles"]))
                d=depths[depth];d["pairs"]+=1;d["correct"]+=int(good)
                d["FP"]+=int(n["prediction"]);d["FN"]+=int(not p["prediction"])
                rows.append({"seed":seed,"vector":list(v),"depth":int(depth),
                   "positive_prediction":p["prediction"],
                   "negative_prediction":n["prediction"],
                   "paired_correct":good,
                   "positive_peak_cells":p["actual_cell_peak"],
                   "negative_peak_cells":n["actual_cell_peak"],
                   "positive_scans":p["edge_scans"],
                   "negative_scans":n["edge_scans"],
                   "positive_bit_comparisons":p["raw_bit_comparisons"],
                   "negative_bit_comparisons":n["raw_bit_comparisons"]})
        source.need(len(rows)==48 and
             all(x["pairs"]==16 for x in depths.values()),
             "EXACT_48_AND_DEPTH_BALANCE")
        out[family]={"pairs":48,"correct":sum(x["paired_correct"] for x in rows),
          "FP":sum(x["negative_prediction"] for x in rows),
          "FN":sum(not x["positive_prediction"] for x in rows),
          "by_depth":depths,"cases":rows}
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    trained=fit()
    threshold,fit_curve=fit_threshold(trained)
    # If frozen FIT zero-false-positive admission fails, report a negative
    # using the smallest frozen threshold, no DEV search or alteration.
    selected=threshold["threshold"] if threshold is not None else GRID[0]
    fit_training=evaluate("FIT",trained["codebook"],selected)
    DEV=evaluate("DEV",trained["codebook"],selected)
    untrained=evaluate("DEV",trained["initial"],GRID[0])
    report={"schema":SCHEMA,"freeze_blob":source.PROTOCOL_BLOB,
       "fully_FIT_trained":True,"no_DEV_parameter_selection":True,
       "first_mismatch_encoded_in_original_cell_scalar":True,
       "additional_persistent_fields":0,
       "original_active_limit":7,"original_retained_limit":9,
       "trained":trained,"FIT_threshold_curve":fit_curve,
       "FIT_choice":threshold,"selected_threshold":selected,
       "FIT":fit_training,"DEV":DEV,
       "untrained_DEV":untrained,
       "protected_first_use":False,"science_accepted":False,
       "optimizer_promoted":False}
    dest=Path(args.output)
    source.need(dest.parent.is_dir() and not dest.exists(),"IMMUTABLE_OUTPUT")
    b=(json.dumps(report,sort_keys=True,indent=2)+"\n").encode()
    with dest.open("xb") as f:f.write(b)
    print("F124AH_TRAIN_SHA256="+hashlib.sha256(b).hexdigest(),flush=True)
    print("F124AH_TRAIN_L2="+str(trained["weight_delta_l2"]),flush=True)
    print("F124AH_TRAIN_LOSS="+str(trained["loss_first"])+
          ":final="+str(trained["loss_last"]),flush=True)
    print("F124AH_FIT_SELECTED_THRESHOLD="+str(selected)+
          ":qualified="+str(threshold is not None),flush=True)
    for family in FAMILIES:
        for name,z in (("trained",DEV[family]),("untrained",untrained[family])):
            print("F124AH_DEV_"+family+"_"+name+
             ":correct="+str(z["correct"])+"/48:FP="+str(z["FP"])+
             ":FN="+str(z["FN"]),flush=True)

if __name__=="__main__":
    try:main()
    except (ValueError,OSError,TypeError,KeyError,ArithmeticError) as exc:
        print("F124AH_TRAIN_QUARANTINE="+str(exc),file=sys.stderr)
        sys.exit(1)
