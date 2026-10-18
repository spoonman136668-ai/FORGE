"""F124-AN true three-outcome inference: POS / NEG / ABSTAIN.

NOTE: Deterministic candidate-completion support is ENGINEERED and disclosed;
FIT-trained head learns calibrated abstention on that representation. It does
NOT learn bit-mask logic or discover causal structure without supplied
one-bit, two-event role assumptions. Existing node/raw16/score only, <=7+9.
"""
from __future__ import annotations
import argparse,hashlib,json,math,random,sys
from pathlib import Path
import f124an_observable_source as S
SCHEMA="forge.research.f124an.FIT-observable-abstention.v1"
LABELS=("NEG","POS","ABSTAIN")
THRESHOLDS=(.4,.5,.6,.7,.8,.9,.95)
EPOCHS=160;LR=.05;L2=.0001
FIRST=1<<18;COMPLETE=1<<19
GLOBAL_PARAMS=16

def public_edges(g):
    return sorted(g["edges"],key=lambda e:(
        e["from"],e["to"],e["role"],
        tuple(-1 if v is None else v for v in e["src_bits"]),
        tuple(e["dst_bits"])))
def observe(g):
    """Single packed first-mask and second-completion status per original cell.

    New public NULLs can have multiple possible latent completions. We do
    not branch into extra persistent cells, instead OR possible second
    statuses into the original scalar score.
    """
    S.validate_public(g)
    active=[(g["start"],None,0)]
    retained=[];peak=1;scans=0;bitops=0;scorebits=0
    edges=public_edges(g)
    for role in g["roles"]:
        candidates=[]
        for node,carried,score in active+retained:
            for e in edges:
                scans+=1
                if node!=e["from"] or role!=e["role"]:continue
                if carried is not None:bitops+=16
                opts=S.public_bit_options(carried,e["src_bits"])
                if not opts:continue
                if score & COMPLETE:
                    # The public relation is complete; another nonzero
                    # mismatch would exceed the PRECOMMITTED two events.
                    if any(bit is not None for bit in opts):continue
                    new=score
                elif score & FIRST:
                    anchor=(score&65535).bit_length()-1
                    flags=0
                    for bit in opts:
                        if bit is None:continue
                        flags|=1 if bit==anchor else 2
                    if flags:
                        new=COMPLETE|flags
                    else:new=score
                else:
                    flipbits=[bit for bit in opts if bit is not None]
                    # One public first error; multiple uncertain initial
                    # anchor bits are not in this frozen new source. All
                    # novel ambiguity is the second event.
                    if len(flipbits)>1:continue
                    new=FIRST|(1<<flipbits[0]) if flipbits else 0
                scorebits=max(scorebits,new.bit_length())
                candidates.append((e["to"],tuple(e["dst_bits"]),new))
        candidates.sort(key=lambda v:(
          0 if v[2]&COMPLETE else 1,v[0],v[1],v[2]))
        selected=[];nodes=set()
        for item in candidates:
            if item[0] in nodes:continue
            nodes.add(item[0]);selected.append(item)
            if len(selected)==7:break
        seen_ids={id(x) for x in selected}
        active=selected[:7]
        retained=[x for x in candidates if id(x) not in seen_ids][:9]
        peak=max(peak,len(active)+len(retained))
        S.need(len(active)<=7 and len(retained)<=9 and peak<=16,
               "ORIGINAL_7_PLUS_9_CELL_LIMIT")
    flags=0
    for node,_,score in active+retained:
        if node==g["target"] and score&COMPLETE:
            flags|=score&3
    missing=sum(v is None for e in g["edges"] for v in e["src_bits"])
    feature=(float(bool(flags&1)),float(bool(flags&2)),
             min(missing,4)/4.,1.)
    return {"feature":feature,"flags":flags,
            "deterministic":"ABSTAIN" if flags==3 else
                   ("POS" if flags&1 else "NEG"),
            "cell_peak":peak,"edge_scans":scans,
            "raw_bit_ops":bitops,"packed_score_bits":scorebits}

def seeded():
    rng=random.Random(int.from_bytes(hashlib.sha256(
        b"forge/F124AN/abstain-head/init/v1").digest()[:12],"big"))
    return {"weights":[[(rng.random()-.5)*.15 for j in range(4)]
                       for k in range(3)],
            "bias":[(rng.random()-.5)*.02 for _ in range(3)]}
def num_weights(model):
    return sum(len(row) for row in model["weights"])+len(model["bias"])
def softmax(model,feat):
    z=[model["bias"][k]+sum(w*x for w,x in
       zip(model["weights"][k],feat)) for k in range(3)]
    m=max(z);v=[math.exp(max(-700.,x-m)) for x in z]
    denom=sum(v)
    return [x/denom for x in v]
def decide(observation,model=None,threshold=.5,mode="trained"):
    if mode=="fixed":
        return observation["deterministic"],None
    S.need(num_weights(model)==15,"TRAINED_HEAD_PARAMETER_COUNT")
    prob=softmax(model,observation["feature"])
    idx=max(range(3),key=lambda x:prob[x])
    return (LABELS[idx] if prob[idx]>=threshold else "ABSTAIN"),prob

def new_cases(phase):
    for family in S.FAMILIES:
        for vector in S.VECTORS:
            for seed in S.COHORTS[family][phase]:
                graphs=S.build(family,seed,vector,phase)
                yield family,seed,list(vector),graphs

def training_data():
    records=[]
    for family,seed,vec,graphs in new_cases("FIT"):
        for role,label in (("positive","POS"),("negative","NEG"),
                           ("ambiguous_public","ABSTAIN")):
            graph=graphs[role]
            features=observe(graph)["feature"]
            records.append((features,LABELS.index(label)))
    S.need(len(records)==432 and all(sum(y==k for _,y in records)==144
               for k in range(3)),"FIT_SOURCE_BALANCE")
    return records
def train():
    original=seeded()
    model=json.loads(json.dumps(original))
    S.need(num_weights(model)==15,"MODEL_15_WEIGHT_CONTRACT")
    data=training_data();first=last=None
    for epoch in range(EPOCHS):
        loss=0.
        for feature,y in data:
            p=softmax(model,feature)
            loss-=math.log(max(1e-12,p[y]))
            for k in range(3):
                delta=p[k]-float(k==y)
                for j,x in enumerate(feature):
                    grad=delta*x+L2*model["weights"][k][j]
                    model["weights"][k][j]-=LR*max(-2.,min(2.,grad))
                model["bias"][k]-=LR*max(-2.,min(2.,delta))
        av=loss/len(data)
        if epoch==0:first=av
        last=av
    before=sum(original["weights"],[])+original["bias"]
    after=sum(model["weights"],[])+model["bias"]
    displacement=math.sqrt(sum((a-b)**2 for a,b in zip(before,after)))
    S.need(displacement>0 and math.isfinite(displacement)
           and math.isfinite(last),"NO_GENUINE_FIT_LEARNING")
    return {"model":model,"initial":original,"FIT_samples":len(data),
            "epochs":EPOCHS,"lr":LR,"l2":L2,
            "trainable_weights":15,"global_weights_plus_threshold":16,
            "first_loss":first,"last_loss":last,
            "weight_displacement_L2":displacement,
            "MASK_LOGIC_IS_ENGINEERED_NOT_LEARNED":True}

def evaluate(phase,model,threshold,mode,retain_cases):
    family_data={}
    for family in S.FAMILIES:
        fam={"resolved_POS":0,"resolved_NEG":0,"ambiguous":0,
             "wrong_positive":0,"wrong_negative":0,
             "ambiguous_forced":0,"resolved_abstain":0,
             "by_depth":{str(i):{"triplets":0,"pos_covered":0,
                   "neg_covered":0,"amb_abstained":0}
                         for i in (10,11,12)},"cases":[]}
        for fam_name,seed,vector,graphs in new_cases(phase):
            if fam_name!=family:continue
            reports={}
            for role in ("positive","negative","ambiguous_public","ambiguous_twin"):
                obs=observe(graphs[role])
                pred,prob=decide(obs,model,threshold,mode)
                reports[role]={"prediction":pred,"features":obs["feature"],
                    "public_support_flags":obs["flags"],
                    "state_cell_peak":obs["cell_peak"],
                    "max_score_bits":obs["packed_score_bits"],
                    "probabilities_hex":[x.hex() for x in prob] if prob else None}
            S.need(reports["ambiguous_public"]["prediction"]==
                   reports["ambiguous_twin"]["prediction"] and
                   json.dumps(graphs["ambiguous_public"],sort_keys=True)==
                   json.dumps(graphs["ambiguous_twin"],sort_keys=True),
                   "LATENT_TWIN_PUBLIC_INFERENCE_DIVERGENCE")
            pos=reports["positive"]["prediction"]
            neg=reports["negative"]["prediction"]
            amb=reports["ambiguous_public"]["prediction"]
            fam["resolved_POS"]+=int(pos=="POS")
            fam["resolved_NEG"]+=int(neg=="NEG")
            fam["ambiguous"]+=int(amb=="ABSTAIN")
            fam["wrong_positive"]+=int(neg=="POS")
            fam["wrong_negative"]+=int(pos=="NEG")
            fam["ambiguous_forced"]+=int(amb!="ABSTAIN")
            fam["resolved_abstain"]+=int(pos=="ABSTAIN")+int(neg=="ABSTAIN")
            d=fam["by_depth"][str(len(graphs["positive"]["roles"]))]
            d["triplets"]+=1;d["pos_covered"]+=int(pos=="POS")
            d["neg_covered"]+=int(neg=="NEG")
            d["amb_abstained"]+=int(amb=="ABSTAIN")
            if retain_cases:
                fam["cases"].append({"seed":seed,"vector":vector,
                  "depth":len(graphs["positive"]["roles"]),"decisions":reports,
                  "opposite_latent_worlds_public_identical":True})
        S.need(all(d["triplets"]==16 for d in fam["by_depth"].values()),
               "SOURCE_48_TRIPLETS_AND_DEPTH")
        if retain_cases:S.need(len(fam["cases"])==48,"MISSING_CASES")
        family_data[family]=fam
    return family_data

def choose_threshold(fit):
    curve=[]
    for threshold in THRESHOLDS:
        report=evaluate("FIT",fit["model"],threshold,"trained",False)
        summed={k:sum(r[k] for r in report.values()) for k in
                ("resolved_POS","resolved_NEG","ambiguous","wrong_positive",
                 "wrong_negative","ambiguous_forced","resolved_abstain")}
        curve.append({"threshold":threshold,**summed})
    candidates=[x for x in curve if
        x["wrong_positive"]==0 and x["wrong_negative"]==0 and
        x["ambiguous_forced"]==0 and x["resolved_POS"]>=72 and
        x["resolved_NEG"]>=72]
    best=min(candidates,key=lambda x:(
        -(x["resolved_POS"]+x["resolved_NEG"]),x["threshold"])) if candidates else None
    return best,curve

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--output",required=True)
    opt=ap.parse_args();S.frozen()
    training=train()
    chosen,curve=choose_threshold(training)
    threshold=chosen["threshold"] if chosen else .95
    # DEV is first constructed only AFTER the FIT-only selection.
    fresh=evaluate("DEV",training["model"],threshold,"trained",True)
    original=evaluate("DEV",training["initial"],.5,"untrained",True)
    fixed=evaluate("DEV",None,0.,"fixed",True)
    report={"schema":SCHEMA,"freeze_blob":S.PROTOCOL_BLOB,
       "FIT_only_training":True,"no_DEV_training_or_threshold_selection":True,
       "training":training,"FIT_curve":curve,
       "FIT_selected":chosen,"FIT_qualified":chosen is not None,
       "selected_threshold":threshold,"DEV_learned":fresh,
       "DEV_untrained":original,"DEV_fixed":fixed,
       "original_7_active_9_retained":True,
       "global_model_params":GLOBAL_PARAMS,
       "trained_only_on_engineered_public_support_features":True,
       "independent_accepted_science":False,
       "protected_first_use":False,"optimizer_promoted":False}
    out=Path(opt.output)
    S.need(out.parent.is_dir() and not out.exists(),"CUSTODY_OUTPUT_EXCLUSIVE")
    raw=(json.dumps(report,sort_keys=True,indent=2)+"\n").encode()
    with out.open("xb") as handle:handle.write(raw)
    print("F124AN_TRAIN_SHA256="+hashlib.sha256(raw).hexdigest(),flush=True)
    print("F124AN_TRAIN_L2="+str(training["weight_displacement_L2"]),flush=True)
    print("F124AN_TRAIN_LOSS="+str(training["first_loss"])+
          ":final="+str(training["last_loss"]),flush=True)
    print("F124AN_FIT_SELECTION="+json.dumps(chosen),flush=True)
    for family in S.FAMILIES:
        for name,group in (("trained",fresh),("untrained",original),("fixed",fixed)):
            d=group[family]
            print("F124AN_DEV_"+family+"_"+name+
              ":POS="+str(d["resolved_POS"])+"/48:NEG="+str(d["resolved_NEG"])+
              "/48:ABSTAIN="+str(d["ambiguous"])+
              "/48:FP="+str(d["wrong_positive"])+
              ":FN="+str(d["wrong_negative"])+
              ":AMB_FORCED="+str(d["ambiguous_forced"]),flush=True)
if __name__=="__main__":
    try:main()
    except (ValueError,OSError,KeyError,TypeError,ArithmeticError) as e:
        print("F124AN_QUARANTINE="+str(e),file=sys.stderr)
        sys.exit(1)
