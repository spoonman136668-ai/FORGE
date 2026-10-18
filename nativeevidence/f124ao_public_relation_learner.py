"""F124-AO bounded example-learned inverse relation families, with abstention.

All fitting uses 22 PUBLIC examples and only two reserved PUBLIC examples for
calibration. No operator names, source module, labels or evaluator truth are
accessible to this module. These are small supervised models, NOT a claim
of general neural cognition.
"""
from __future__ import annotations
import f124aj_example_operator_learner as public
import f124ag_transition_models as ag
import f124q_fresh_source as q

ARCHITECTURES=("stump","depth2","neighbor1","neighbor3")
BAD_BITS=(2,4,6)
MARGINS=(1,2)
FIT_DEMOS=22

def need(ok,key): q.need(ok,"F124AO_PUBLIC_LEARNER_"+key)

def build(demos,architecture):
    need(architecture in ARCHITECTURES and len(demos)==24,
         "PUBLIC_FROZEN_CANDIDATES")
    train=demos[:FIT_DEMOS]
    out=[]
    count=0
    if architecture.startswith("neighbor"):
        k=1 if architecture=="neighbor1" else 3
        memory=tuple((tuple(x["output_bits"]),tuple(x["input_bits"]))
                     for x in train)
        return ("neighbor",memory,k),{"fit_operations":0,"public_fit":22}
    for target in range(16):
        options=[]
        if architecture=="stump":
            for j in range(16):
                for flip in (0,1):
                    error=sum((x["output_bits"][j]^flip)!=x["input_bits"][target]
                              for x in train)
                    count+=len(train)
                    options.append((error,j,flip))
            options.sort()
            out.append(("stump",options[0][1],options[0][2],
                        options[1][0]-options[0][0]))
        else:
            for a in range(16):
                for b in range(a+1,16):
                    grouped=[[] for _ in range(4)]
                    for x in train:
                        grouped[2*x["output_bits"][a]+x["output_bits"][b]].append(
                            x["input_bits"][target])
                        count+=1
                    majority=[]
                    error=0
                    for bits in grouped:
                        ones=sum(bits)
                        zeroes=len(bits)-ones
                        guess=int(ones>zeroes)
                        majority.append(guess)
                        error+=min(ones,zeroes)
                    options.append((error,a,b,tuple(majority)))
            options.sort()
            out.append(("depth2",options[0][1],options[0][2],
                        options[0][3],options[1][0]-options[0][0]))
    return ("rules",tuple(out)),{"fit_operations":count,"public_fit":22}

def predict(fitted,encoded):
    need(len(encoded)==16 and all(x in (0,1) for x in encoded),
         "SIXTEEN_PUBLIC_BITS")
    if fitted[0]=="neighbor":
        memory,k=fitted[1:]
        chosen=sorted(((sum(a!=b for a,b in zip(encoded,e)),i,raw)
                       for i,(e,raw) in enumerate(memory)))[:k]
        result=[]
        margins=[]
        for bit in range(16):
            votes=sum(row[2][bit] for row in chosen)
            result.append(int(votes>k/2))
            margins.append(abs(2*votes-k))
        return result,min(margins),len(memory)*16+16*k
    result=[]
    confidences=[]
    for rule in fitted[1]:
        if rule[0]=="stump":
            result.append(encoded[rule[1]]^rule[2])
            confidences.append(rule[3])
        else:
            result.append(rule[3][2*encoded[rule[1]]+encoded[rule[2]]])
            confidences.append(rule[4])
    return result,min(confidences),len(fitted[1])*2

def normalize(graph,architecture,max_bad_bits,min_margin):
    need(max_bad_bits in BAD_BITS and min_margin in MARGINS,
         "FROZEN_CALIBRATION_GRID")
    raw,demos,task=public.public_task(graph)
    fitted,fit=build(demos,architecture)
    calibration=[]
    margins=[]
    operations=fit["fit_operations"]
    for demo in demos[FIT_DEMOS:]:
        guess,confidence,steps=predict(fitted,demo["output_bits"])
        operations+=steps
        calibration.extend(int(a!=b) for a,b in zip(guess,demo["input_bits"]))
        margins.append(confidence)
    bad=sum(calibration)
    confidence=min(margins)
    accepted=bad<=max_bad_bits and confidence>=min_margin
    obs={"learner_family":architecture,"public_fit":22,"public_check":2,
         "reserved_public_bad_bits":bad,"public_margin":confidence,
         "calibration_bad_limit":max_bad_bits,
         "calibration_min_margin":min_margin,
         "abstained":not accepted,"operator_identity_supplied":False,
         "oracle_used":False,"extra_retained_cells":0,
         "model_bit_operations":operations}
    if not accepted:
        return None,obs
    for edge in raw["edges"]:
        edge["src_bits"],margin,steps=predict(fitted,edge["src_bits"])
        operations+=steps
    obs["model_bit_operations"]=operations
    ag.frozen.prior.parent.validate_15(raw)
    return raw,obs

def ygg(graph,base,delta,architecture,max_bad_bits,min_margin):
    norm,obs=normalize(graph,architecture,max_bad_bits,min_margin)
    if norm is None:return -1.e9,None,obs
    score,raw,prob,work=ag.ygg_transition(norm,list(base),list(delta),.1)
    need(work["max_active"]<=7 and work["max_retained"]<=9,
         "ORIGINAL_SEVEN_PLUS_NINE")
    return score,work,obs

def select(cases,base,delta):
    """TRAIN-only, no source-oracle diagnostic or hidden operator knowledge."""
    need(len(cases)==48,"ONLY_FROZEN_NEW_TRAIN")
    results=[]
    for arm in ARCHITECTURES:
        for bad in BAD_BITS:
            for margin in MARGINS:
                paired=fp=fn=abstentions=work=0
                for seed,vec,family,operator,nonce,pos,neg in cases:
                    a,wa,da=ygg(pos,base,delta,arm,bad,margin)
                    b,wb,db=ygg(neg,base,delta,arm,bad,margin)
                    paired+=int(a>=0 and b<0)
                    fp+=int(b>=0)
                    fn+=int(a<0)
                    abstentions+=int(da["abstained"])+int(db["abstained"])
                    work+=da["model_bit_operations"]+db["model_bit_operations"]
                results.append({"architecture":arm,"bad_bits":bad,"margin":margin,
                                "paired":paired,"FP":fp,"FN":fn,
                                "abstained_graphs":abstentions,
                                "model_bit_operations":work})
    valid=[r for r in results if r["FP"]==0]
    eligible=valid if valid else results
    chosen=sorted(eligible,key=lambda r:(-r["paired"],r["FP"],
              r["model_bit_operations"],r["architecture"],r["bad_bits"],
              r["margin"]))[0]
    return chosen,results
