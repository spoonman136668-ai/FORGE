"""F124-AJ shared neural operator on raw paired transition bits.

Critically NO bit-position extraction, XOR-signature lookup, or equality
operator in the learned scoring function. The shared MLP receives aligned
raw quadruples (prior carried, src) at two noisy events, aggregated across
all 16 anonymous bit lanes. Engineered: public-role traversal, count of
one-bit error EVENTS, packed 33-bit raw-pair scalar in original cell.score.
This is not end-to-end unsupervised learning and the 33-bit Python int
can consume more memory than the predecessor float score.
"""
from __future__ import annotations
import argparse,hashlib,json,math,random,sys
from pathlib import Path
import f124aj_source as S
import f124o_native_learners as O

SCHEMA="forge.research.f124aj.raw-shared-operator-FIT.v1"
H=8
EPOCHS=140
LR=.025
WEIGHT_DECAY=.0001
THRESHOLDS=(.05,.1,.2,.3,.4,.5,.6,.7,.8,.9,.95)
PARAMS=49
PACK_FLAG=1<<32
MASK16=(1<<16)-1

def bitint(bits):
    x=0
    for i,v in enumerate(bits):x|=(v<<i)
    return x
def bits16(x):
    return [(x>>i)&1 for i in range(16)]
def pack(first,second):
    return PACK_FLAG | (bitint(first)<<16) | bitint(second)
def unpack(score):
    return bits16((score>>16)&MASK16),bits16(score&MASK16)
def raw_patterns(a,b,c,d):
    """Raw bit tuples, NOT mismatched bit indices or exact-equality codes."""
    counts=[0]*16
    for i in range(16):
        key=(a[i]<<3)|(b[i]<<2)|(c[i]<<1)|d[i]
        counts[key]+=1
    S.need(sum(counts)==16,"RAW_BIT_DENOMINATOR")
    return counts
def pattern_bits(p):
    return ((p>>3)&1,(p>>2)&1,(p>>1)&1,p&1)
PATT=tuple(pattern_bits(i) for i in range(16))

def seeded():
    rng=random.Random(int.from_bytes(hashlib.sha256(
        b"forge/F124AJ/operator-init/v1").digest()[:16],"big"))
    return {"w":[[(rng.random()-.5)*.4 for _ in range(4)] for j in range(H)],
            "hidden_bias":[(rng.random()-.5)*.04 for j in range(H)],
            "output":[(rng.random()-.5)*.4 for j in range(H)],
            "output_bias":0.}

def count_params(model):
    return sum(len(v) for v in model["w"])+len(model["hidden_bias"])+len(model["output"])+1
def sigmoid(z):
    if z>=0:return 1./(1.+math.exp(-min(z,700.)))
    q=math.exp(max(z,-700.));return q/(1.+q)

def network(model,hist,for_training=False):
    hidden=[]
    pooled=[0.]*H
    for j in range(H):
        terms=[]
        for k,count in enumerate(hist):
            if not count:continue
            bits=PATT[k]
            x=model["hidden_bias"][j]+sum(model["w"][j][i]*bits[i] for i in range(4))
            y=math.tanh(x)
            pooled[j]+=count*y/16.
            if for_training:terms.append((count,bits,y))
        hidden.append(terms)
    z=model["output_bias"]+sum(model["output"][j]*pooled[j] for j in range(H))
    return sigmoid(z),pooled,hidden

def _fit_only_path(graph):
    """Read FIT labelled public graph via role topology and <=1 error EVENT.

    This function does NOT extract which bit differs. Never called at DEV
    or inside neural network inference.
    """
    S.validate_public(graph)
    states=[(graph["start"],None,())]
    for role in graph["roles"]:
        nxt=[]
        for node,carried,events in states:
            for e in graph["edges"]:
                if e["from"]!=node or e["role"]!=role:continue
                if carried is None:
                    misses=0
                else:misses=sum(x!=y for x,y in zip(carried,e["src_bits"]))
                if misses>1:continue
                items=events
                if misses==1:
                    items=events+((tuple(carried),tuple(e["src_bits"])),)
                if len(items)>2:continue
                nxt.append((e["to"],e["dst_bits"],items))
                S.need(len(nxt)<=128,"FIT_PUBLIC_PATH_BUDGET")
        states=nxt
    paths=[t for n,_,t in states if n==graph["target"] and len(t)==2]
    S.need(len(paths)==1,"FIT_LABELLED_PUBLIC_PATH_NOT_UNIQUE")
    (a,b),(c,d)=paths[0]
    return raw_patterns(a,b,c,d)

def training_samples():
    rows=[]
    for family in S.FAMILIES:
        for v in S.VECTORS:
            for seed in S.COHORTS[family]["FIT"]:
                pos,neg=S.build(family,seed,v,"FIT")
                rows.append((_fit_only_path(pos),1))
                rows.append((_fit_only_path(neg),0))
    S.need(len(rows)==288 and
          sum(y for _,y in rows)==144,"FIT_LABEL_COUNT")
    return rows

def train():
    S.frozen()
    rows=training_samples()
    initial=seeded()
    model=json.loads(json.dumps(initial))
    S.need(count_params(model)==PARAMS,"EXPECTED_49_TRAINED_PARAMS")
    first=last=None
    for epoch in range(EPOCHS):
        total_loss=0.
        for hist,y in rows:
            p,pooled,hidden=network(model,hist,True)
            total_loss-=y*math.log(max(p,1e-12))+(1-y)*math.log(max(1-p,1e-12))
            delta=p-y
            oldout=list(model["output"])
            gw=[[0.]*4 for _ in range(H)];gb=[0.]*H
            for j in range(H):
                for count,bits,t in hidden[j]:
                    d=delta*oldout[j]*count*(1-t*t)/16.
                    gb[j]+=d
                    for i in range(4):gw[j][i]+=d*bits[i]
            for j in range(H):
                g=delta*pooled[j]+WEIGHT_DECAY*oldout[j]
                model["output"][j]-=LR*max(-1.,min(1.,g))
                g=gb[j]+WEIGHT_DECAY*model["hidden_bias"][j]
                model["hidden_bias"][j]-=LR*max(-1.,min(1.,g))
                for i in range(4):
                    g=gw[j][i]+WEIGHT_DECAY*model["w"][j][i]
                    model["w"][j][i]-=LR*max(-1.,min(1.,g))
            model["output_bias"]-=LR*max(-1.,min(1.,delta))
        loss=total_loss/len(rows)
        if epoch==0:first=loss
        last=loss
    before=initial["output"]+initial["hidden_bias"]+sum(initial["w"],[])+[initial["output_bias"]]
    after=model["output"]+model["hidden_bias"]+sum(model["w"],[])+[model["output_bias"]]
    delta=math.sqrt(sum((a-b)**2 for a,b in zip(before,after)))
    S.need(delta>0 and math.isfinite(delta) and math.isfinite(last),"NO_VALID_TRAINING")
    return {"model":model,"initial":initial,"params":PARAMS,
        "epochs":EPOCHS,"LR":LR,"weight_decay":WEIGHT_DECAY,
        "FIT_samples":len(rows),"loss_initial":first,"loss_final":last,
        "weight_change_L2":delta,"training_contains_raw_inputs_not_bit_index":True}

def infer(graph,model,threshold):
    S.validate_public(graph)
    S.need(count_params(model)==PARAMS and threshold>=0.,
           "RAW_NETWORK_MODEL_PARAMS")
    edges=O.sorted_edges(graph)
    active=[(graph["start"],None,0)]
    retained=[]
    scans=compares=0
    max_cells=1
    for role in graph["roles"]:
        candidates=[]
        for node,carried,score in active+retained:
            for e in edges:
                scans+=1
                if e["from"]!=node or e["role"]!=role:continue
                if carried is None:noise=0
                else:
                    compares+=16
                    noise=sum(a!=b for a,b in zip(carried,e["src_bits"]))
                if noise>1:continue
                if noise==1:
                    if score==0:
                        next_score=pack(carried,e["src_bits"])
                    elif isinstance(score,int) and score>=PACK_FLAG:
                        a,b=unpack(score)
                        h=raw_patterns(a,b,carried,e["src_bits"])
                        prediction,_,_=network(model,h)
                        if prediction<threshold:continue
                        next_score=-1
                    else:continue
                else:next_score=score
                candidates.append((e["to"],tuple(e["dst_bits"]),next_score))
        # Exactly the same public position-based ordering and destination
        # diversity across trained, untrained and deterministic comparator.
        candidates.sort(key=lambda x:(
            0 if x[2]==-1 else 1,x[0],x[1],x[2]))
        chosen=[];seen=set()
        for c in candidates:
            if c[0] in seen:continue
            seen.add(c[0]);chosen.append(c)
            if len(chosen)==7:break
        selected={id(x) for x in chosen}
        for c in candidates:
            if len(chosen)==7:break
            if id(c) not in selected:chosen.append(c)
        selected={id(x) for x in chosen}
        active=chosen[:7]
        retained=[c for c in candidates if id(c) not in selected][:9]
        max_cells=max(max_cells,len(active)+len(retained))
        S.need(len(active)<=7 and len(retained)<=9 and max_cells<=16,
               "ORIGINAL_CELL_LIMIT")
    return {"prediction":any(n==graph["target"] and score==-1
                 for n,_,score in active+retained),
            "actual_cell_peak":max_cells,"blocked":False,
            "edge_scans":scans,"raw_bit_comparisons":compares,
            "packed_33bit_cell_payload":True}

def phase_eval(phase,model,threshold):
    data={}
    for family in S.FAMILIES:
        rows=[];by_depth={str(d):{"pairs":0,"correct":0,"FP":0,"FN":0}
                               for d in (10,11,12)}
        for v in S.VECTORS:
            for seed in S.COHORTS[family][phase]:
                pos,neg=S.build(family,seed,v,phase)
                p=infer(pos,model,threshold)
                n=infer(neg,model,threshold)
                good=p["prediction"] and not n["prediction"]
                depth=str(len(pos["roles"]))
                d=by_depth[depth];d["pairs"]+=1;d["correct"]+=int(good)
                d["FP"]+=int(n["prediction"]);d["FN"]+=int(not p["prediction"])
                rows.append({"seed":seed,"vector":list(v),"depth":int(depth),
                  "positive_prediction":p["prediction"],
                  "negative_prediction":n["prediction"],"correct":good,
                  "positive_max_cells":p["actual_cell_peak"],
                  "negative_max_cells":n["actual_cell_peak"],
                  "positive_edge_scans":p["edge_scans"],
                  "negative_edge_scans":n["edge_scans"]})
        S.need(len(rows)==48 and all(z["pairs"]==16 for z in by_depth.values()),
               "PHASE_DENOMINATORS")
        data[family]={"pairs":48,"correct":sum(z["correct"] for z in rows),
           "FP":sum(z["negative_prediction"] for z in rows),
           "FN":sum(not z["positive_prediction"] for z in rows),
           "by_depth":by_depth,"cases":rows}
    return data

def choose_fit(fitted):
    rows=[]
    for threshold in THRESHOLDS:
        result=phase_eval("FIT",fitted["model"],threshold)
        correct=sum(r["correct"] for r in result.values())
        FP=sum(r["FP"] for r in result.values())
        FN=sum(r["FN"] for r in result.values())
        rows.append({"threshold":threshold,"pairs_correct":correct,
                     "FP":FP,"FN":FN,"positives_recalled":144-FN})
    valid=[x for x in rows if x["FP"]==0 and x["positives_recalled"]>=72]
    choice=min(valid,key=lambda x:(-x["pairs_correct"],x["threshold"])) if valid else None
    return choice,rows

def save(output,doc,prefix):
    path=Path(output)
    S.need(path.parent.is_dir() and not path.exists(),"EXCLUSIVE_OUTPUT")
    b=(json.dumps(doc,sort_keys=True,indent=2)+"\n").encode()
    with path.open("xb") as f:f.write(b)
    print(prefix+"="+hashlib.sha256(b).hexdigest(),flush=True)

def main():
    a=argparse.ArgumentParser();a.add_argument("--output",required=True)
    opt=a.parse_args()
    S.frozen()
    fit=train()
    choice,curve=choose_fit(fit)
    threshold=choice["threshold"] if choice is not None else THRESHOLDS[0]
    # Only NOW is DEV constructed and evaluated.
    DEV=phase_eval("DEV",fit["model"],threshold)
    untrained=phase_eval("DEV",fit["initial"],.5)
    data={"schema":SCHEMA,"freeze_blob":S.PROTOCOL_BLOB,
      "FIT_trained":True,"training_samples":288,"learned_parameters":PARAMS,
      "selected_threshold_parameter":1,"trained":fit,
      "FIT_curve":curve,"FIT_choice":choice,
      "qualified_FIT_zero_FP_with_positive_sensitivity":choice is not None,
      "selected_threshold":threshold,"DEV":DEV,"untrained_DEV":untrained,
      "no_DEV_training_or_selection":True,
      "no_added_persistent_state_fields":True,
      "first_noisy_edge_as_packed_raw_pair_in_original_scalar":True,
      "protected_first_use":False,"science_accepted":False,
      "optimizer_promoted":False}
    save(opt.output,data,"F124AJ_TRAIN_SHA256")
    print("F124AJ_TRAIN_L2="+str(fit["weight_change_L2"]),flush=True)
    print("F124AJ_TRAIN_LOSS="+str(fit["loss_initial"])+
          ":final="+str(fit["loss_final"]),flush=True)
    print("F124AJ_FIT_CHOICE="+json.dumps(choice),flush=True)
    for family in S.FAMILIES:
        for name,record in (("trained",DEV[family]),
                            ("untrained",untrained[family])):
            print("F124AJ_DEV_"+family+"_"+name+
              ":correct="+str(record["correct"])+"/48:FP="+str(record["FP"])+
              ":FN="+str(record["FN"]),flush=True)

if __name__=="__main__":
    try:main()
    except (ValueError,OSError,TypeError,KeyError,ArithmeticError) as e:
        print("F124AJ_TRAIN_QUARANTINE="+str(e),file=sys.stderr);sys.exit(1)
