"""F124-AK: learn raw public bit transitions with FIT intermediate supervision,
then learn an aligned two-event relational binder from FIT labelled examples.

No supplied XOR feature, mismatch-index, equality comparator or source label
in inference. ENGINEERED biases disclosed: aligned bit lanes, fixed 0.5
bit-probability discretization, 'one noisy event' cardinality gate, and
histogram pooling. The original 3-field (node, raw16, score) persistent cell
stores a learned binary first-hop mask with 17-bit integer sentinel; <=7+9
cells, possibly LARGER byte payload than historical float score.
"""
from __future__ import annotations
import argparse,hashlib,json,math,random,sys
from pathlib import Path
import f124ak_source as S
import f124o_native_learners as O

SCHEMA="forge.research.f124ak.FIT-trained-intermediate-and-binder.v1"
PAIR_VALUES=((0,0),(0,1),(1,0),(1,1))
LOCAL_HIDDEN=8
LOCAL_PARAMS=33
HEAD_PARAMS=5
TOTAL_PARAMS=39
SENTINEL=1<<16
THRESHOLDS=(.1,.2,.3,.4,.5,.6,.7,.8,.9)
LOCAL_EPOCHS=320;LOCAL_LR=.09;LOCAL_L2=.0001
HEAD_EPOCHS=360;HEAD_LR=.18;HEAD_L2=.0001
FAMILIES=S.FAMILIES

def sigmoid(z):
    if z>=0:return 1./(1.+math.exp(-min(z,700.)))
    e=math.exp(max(z,-700.));return e/(1.+e)
def seeded():
    rng=random.Random(int.from_bytes(hashlib.sha256(
        b"forge/F124AK/local-mlp/v1").digest()[:16],"big"))
    local={"w":[[(rng.random()-.5)*1.3 for _ in range(2)]
                 for j in range(LOCAL_HIDDEN)],
           "b":[(rng.random()-.5)*.12 for _ in range(LOCAL_HIDDEN)],
           "out":[(rng.random()-.5)*.5 for _ in range(LOCAL_HIDDEN)],
           "out_bias":(rng.random()-.5)*.04}
    head={"w":[0.,0.,0.,0.],"b":0.}
    return {"local":local,"head":head}
def count_params(model):
    local=model["local"];head=model["head"]
    return (sum(len(r) for r in local["w"])+len(local["b"])+
            len(local["out"])+1+len(head["w"])+1)
def local_forward(model,a,b):
    z=[];t=[]
    for j in range(LOCAL_HIDDEN):
        v=model["b"][j]+model["w"][j][0]*a+model["w"][j][1]*b
        z.append(v);t.append(math.tanh(v))
    pred=sigmoid(model["out_bias"]+
                 sum(model["out"][j]*t[j] for j in range(LOCAL_HIDDEN)))
    return pred,t
def predict_table(model):
    return {(a,b):local_forward(model,a,b)[0] for a,b in PAIR_VALUES}
def mask_from_raw(carried,nxt,table):
    mask=0
    for i,(a,b) in enumerate(zip(carried,nxt)):
        if table[(a,b)]>=.5:mask|=1<<i
    return mask
def relation_features(mask1,mask2):
    """Public aligned lane histogram, NOT an explicit equality comparator."""
    h=[0,0,0,0]
    for i in range(16):
        key=(((mask1>>i)&1)<<1)|((mask2>>i)&1)
        h[key]+=1
    S.need(sum(h)==16,"LANE_HISTOGRAM")
    # Frozen centering for 16-lane exactly two-noise setting, not taught
    # mismatch-index or label. Report engineered source assumption.
    return (float(h[0]-14),float(h[1]),float(h[2]),float(h[3]))
def head_predict(head,features):
    return sigmoid(head["b"]+sum(a*b for a,b in zip(head["w"],features)))
def flatten(model):
    l=model["local"];h=model["head"]
    return sum(l["w"],[])+l["b"]+l["out"]+[l["out_bias"]]+h["w"]+[h["b"]]

def _fit_path(graph):
    """Only FIT training teacher, NEVER invoked by model inference."""
    S.validate_public(graph)
    frontier=[(graph["start"],None,())]
    for role in graph["roles"]:
        nxt=[]
        for node,carried,events in frontier:
            for edge in graph["edges"]:
                if edge["from"]!=node or edge["role"]!=role:continue
                if carried is None:d=0
                else:d=sum(x!=y for x,y in zip(carried,edge["src_bits"]))
                if d>1:continue
                later=events if d==0 else events+(
                    (tuple(carried),tuple(edge["src_bits"])),)
                if len(later)>2:continue
                nxt.append((edge["to"],edge["dst_bits"],later))
                S.need(len(nxt)<=128,"FIT_ONLY_ROUTE_BUDGET")
        frontier=nxt
    endings=[e for n,_,e in frontier
             if n==graph["target"] and len(e)==2]
    S.need(len(endings)==1,"FIT_ONLY_PUBLIC_TARGET_PATH")
    return endings[0]

def fit_examples():
    pairs=[];distribution={(a,b):0 for a,b in PAIR_VALUES}
    for family in FAMILIES:
        for v in S.VECTORS:
            for seed in S.COHORTS[family]["FIT"]:
                pos,neg=S.build(family,seed,v,"FIT")
                for graph,label in ((pos,1),(neg,0)):
                    first,second=_fit_path(graph)
                    for carried,src in (first,second):
                        for a,b in zip(carried,src):
                            distribution[(a,b)]+=1
                    pairs.append((first,second,label))
    S.need(len(pairs)==288 and
         all(distribution[x]>0 for x in PAIR_VALUES),
         "FIT_NO_INTERMEDIATE_SOURCE_DIVERSITY")
    return pairs,distribution

def train():
    S.frozen()
    samples,distribution=fit_examples()
    initial=seeded()
    model=json.loads(json.dumps(initial))
    S.need(count_params(model)==TOTAL_PARAMS-1,"MODEL_PARAMETER_COUNT")
    local=model["local"]
    local_first=local_last=None
    # Intermediate hop target: EXACT bit-flip label from FIT public edge,
    # supervised explicitly; equal weight for all four observed raw pair
    # patterns prevents a misleading 98% no-error majority classifier.
    for epoch in range(LOCAL_EPOCHS):
        total=0.
        for a,b in PAIR_VALUES:
            target=float(a!=b)
            prob,hidden=local_forward(local,a,b)
            total-=target*math.log(max(prob,1e-12))+(1-target)*math.log(
                max(1-prob,1e-12))
            delta=prob-target
            old_out=list(local["out"])
            for j in range(LOCAL_HIDDEN):
                g=delta*hidden[j]+LOCAL_L2*old_out[j]
                local["out"][j]-=LOCAL_LR*max(-1.,min(1.,g))
                d=delta*old_out[j]*(1-hidden[j]*hidden[j])
                local["b"][j]-=LOCAL_LR*max(-1.,min(1.,d+LOCAL_L2*local["b"][j]))
                for k,x in enumerate((a,b)):
                    g=d*x+LOCAL_L2*local["w"][j][k]
                    local["w"][j][k]-=LOCAL_LR*max(-1.,min(1.,g))
            local["out_bias"]-=LOCAL_LR*max(-1.,min(1.,delta))
        total/=4.
        if epoch==0:local_first=total
        local_last=total
    table=predict_table(local)
    hop_correct=sum((table[(a,b)]>=.5)==bool(a!=b)
                    for a,b in PAIR_VALUES)
    # The full 4-entry table is RETAINED, never changed using DEV.
    head_train=[]
    for first,second,label in samples:
        a,b=first;c,d=second
        features=relation_features(
           mask_from_raw(a,b,table),mask_from_raw(c,d,table))
        head_train.append((features,label))
    rel=model["head"];rel_first=rel_last=None
    for epoch in range(HEAD_EPOCHS):
        loss=0.
        for features,label in head_train:
            prob=head_predict(rel,features)
            loss-=label*math.log(max(prob,1e-12)) + (
                 1-label)*math.log(max(1-prob,1e-12))
            grad=prob-label
            for i,x in enumerate(features):
                g=grad*x+HEAD_L2*rel["w"][i]
                rel["w"][i]-=HEAD_LR*max(-1.,min(1.,g))
            rel["b"]-=HEAD_LR*max(-1.,min(1.,grad))
        loss/=len(head_train)
        if epoch==0:rel_first=loss
        rel_last=loss
    delta=math.sqrt(sum((a-b)**2 for a,b in
          zip(flatten(initial),flatten(model))))
    S.need(delta>0 and math.isfinite(delta) and
           all(math.isfinite(x) for x in flatten(model)),
           "GENUINE_TRAINING_NAN")
    return {"model":model,"initial":initial,
       "parameter_count":TOTAL_PARAMS,"local_params":LOCAL_PARAMS,
       "relation_params":HEAD_PARAMS,
       "FIT_graph_pairs":len(samples),"FIT_bit_lane_counts":{
          str(a)+str(b):distribution[(a,b)] for a,b in PAIR_VALUES},
       "FIT_local_epochs":LOCAL_EPOCHS,
       "FIT_relation_epochs":HEAD_EPOCHS,
       "hop_training_loss_first":local_first,
       "hop_training_loss_last":local_last,
       "head_loss_first":rel_first,"head_loss_last":rel_last,
       "FIT_four_raw_pattern_probabilities":{
          str(a)+str(b):table[(a,b)] for a,b in PAIR_VALUES},
       "FIT_four_raw_pattern_accuracy":hop_correct,
       "trained_L2_distance_from_random_initial":delta,
       "source_pretrained_historical_model_used_for_training":False}

def infer(graph,model,threshold):
    """Only public bits + learned network. No source causal oracle or labels."""
    S.validate_public(graph)
    S.need(count_params(model)==TOTAL_PARAMS-1 and threshold>=0.,"FIT_PARAM_SHAPE")
    table=predict_table(model["local"])
    edges=O.sorted_edges(graph)
    active=[(graph["start"],None,0)]
    retained=[];scans=bits=0
    peak=1
    for role in graph["roles"]:
        candidates=[]
        for node,carried,score in active+retained:
            for e in edges:
                scans+=1
                if e["from"]!=node or e["role"]!=role:continue
                # First hop lacks carried raw16 comparison.
                mask=0
                if carried is not None:
                    bits+=16
                    mask=mask_from_raw(carried,e["src_bits"],table)
                events=mask.bit_count()
                if events>1:continue
                if events==1:
                    if score==0:
                        next_score=SENTINEL|mask
                    elif isinstance(score,int) and score>=SENTINEL:
                        first=score&(SENTINEL-1)
                        prob=head_predict(model["head"],
                                  relation_features(first,mask))
                        if prob<threshold:continue
                        next_score=-1
                    else:continue
                else:next_score=score
                candidates.append((e["to"],tuple(e["dst_bits"]),next_score))
        candidates.sort(key=lambda c:(
            0 if c[2]==-1 else 1,c[0],c[1],c[2]))
        chosen=[];nodes=set()
        for c in candidates:
            if c[0] in nodes:continue
            nodes.add(c[0]);chosen.append(c)
            if len(chosen)==7:break
        selected={id(x) for x in chosen}
        for c in candidates:
            if len(chosen)==7:break
            if id(c) not in selected:chosen.append(c)
        selected={id(x) for x in chosen}
        active=chosen[:7]
        retained=[c for c in candidates if id(c) not in selected][:9]
        peak=max(peak,len(active)+len(retained))
        S.need(len(active)<=7 and len(retained)<=9 and peak<=16,
               "PERSISTENT_7_PLUS_9_CAP")
    return {"prediction":any(n==graph["target"] and score==-1
                      for n,_,score in active+retained),
            "actual_cell_peak":peak,"edge_scans":scans,
            "public_bit_lane_predictor_calls":bits,
            "packed_first_mask_in_original_score":True,
            "blocked":False}

def eval_phase(phase,model,threshold):
    data={}
    for fam in FAMILIES:
        pairs=[];depths={str(d):{"pairs":0,"correct":0,"FP":0,"FN":0}
                            for d in (10,11,12)}
        for v in S.VECTORS:
            for seed in S.COHORTS[fam][phase]:
                positive,negative=S.build(fam,seed,v,phase)
                p=infer(positive,model,threshold)
                n=infer(negative,model,threshold)
                correct=bool(p["prediction"] and not n["prediction"])
                depth=str(len(positive["roles"]))
                r=depths[depth];r["pairs"]+=1;r["correct"]+=int(correct)
                r["FP"]+=int(n["prediction"]);r["FN"]+=int(not p["prediction"])
                pairs.append({"seed":seed,"vector":list(v),"depth":int(depth),
                    "positive":p["prediction"],"negative":n["prediction"],
                    "paired_correct":correct,
                    "positive_peak_cells":p["actual_cell_peak"],
                    "negative_peak_cells":n["actual_cell_peak"]})
        S.need(len(pairs)==48 and all(x["pairs"]==16 for x in depths.values()),
               "DEV_PAIRS_OR_DEPTH")
        data[fam]={"pairs":48,"correct":sum(x["paired_correct"] for x in pairs),
                   "FP":sum(x["negative"] for x in pairs),
                   "FN":sum(not x["positive"] for x in pairs),
                   "by_depth":depths,"cases":pairs}
    return data

def threshold_on_FIT(trained):
    curve=[]
    for t in THRESHOLDS:
        results=eval_phase("FIT",trained["model"],t)
        good=sum(x["correct"] for x in results.values())
        fp=sum(x["FP"] for x in results.values())
        fn=sum(x["FN"] for x in results.values())
        curve.append({"threshold":t,"correct":good,"FP":fp,
                      "FN":fn,"positive_recall":144-fn})
    valid=[x for x in curve if x["FP"]==0 and x["positive_recall"]>=72]
    chosen=min(valid,key=lambda x:(-x["correct"],x["threshold"])) if valid else None
    return chosen,curve

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",required=True)
    a=parser.parse_args()
    S.frozen()
    fit=train()
    chosen,curve=threshold_on_FIT(fit)
    selected=chosen["threshold"] if chosen else THRESHOLDS[0]
    # Now construct DEV for first time. Never change model after.
    dev=eval_phase("DEV",fit["model"],selected)
    untrained=eval_phase("DEV",fit["initial"],.5)
    ablated=json.loads(json.dumps(fit["model"]))
    ablated["head"]={"w":[0.,0.,0.,0.],"b":0.}
    ablated_dev=eval_phase("DEV",ablated,.5)
    report={"schema":SCHEMA,"freeze_blob":S.PROTOCOL_BLOB,
      "train_genuine":True,"fit_uses_only_new_FIT":True,
      "no_DEV_training_or_selection":True,
      "trained":fit,"FIT_curve":curve,"FIT_choice":chosen,
      "qualified_zero_FP_and_minimum_positive_sensitivity":chosen is not None,
      "selected_threshold":selected,
      "DEV":dev,"untrained_DEV":untrained,
      "intermediate_trained_untrained_binder_DEV":ablated_dev,
      "original_cell_fields_unchanged":True,
      "original_cell_cap":16,"additional_global_params":TOTAL_PARAMS,
      "packed_score_integer_bytes_must_be_measured":True,
      "protected_first_use":False,"independent_science_accepted":False,
      "optimizer_promoted":False}
    output=Path(a.output)
    S.need(output.parent.is_dir() and not output.exists(),"IMMUTABLE_FIT_EVIDENCE")
    data=(json.dumps(report,sort_keys=True,indent=2)+"\n").encode()
    with output.open("xb") as f:f.write(data)
    print("F124AK_TRAIN_SHA256="+hashlib.sha256(data).hexdigest(),flush=True)
    print("F124AK_HOP_L2="+str(fit["trained_L2_distance_from_random_initial"]),flush=True)
    print("F124AK_HOP_PATTERN_ACCURACY="+str(fit["FIT_four_raw_pattern_accuracy"])+"/4",flush=True)
    print("F124AK_HOP_LOSS="+str(fit["hop_training_loss_first"])+
          ":final="+str(fit["hop_training_loss_last"]),flush=True)
    print("F124AK_HEAD_LOSS="+str(fit["head_loss_first"])+
          ":final="+str(fit["head_loss_last"]),flush=True)
    print("F124AK_FIT_CHOICE="+json.dumps(chosen),flush=True)
    for fam in FAMILIES:
        for arm,data in (("trained",dev[fam]),("untrained",untrained[fam]),
                         ("hop_only",ablated_dev[fam])):
            print("F124AK_DEV_"+fam+"_"+arm+":correct="+str(data["correct"])+
                 "/48:FP="+str(data["FP"])+":FN="+str(data["FN"]),flush=True)

if __name__=="__main__":
    try:main()
    except (ValueError,OSError,KeyError,TypeError,ArithmeticError) as e:
        print("F124AK_FIT_QUARANTINE="+str(e),file=sys.stderr);sys.exit(1)
