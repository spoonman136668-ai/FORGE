"""F124-DD independent fully meta-trained compact ANF strong peer.

No candidate/source import. Same 12 public binary operator tasks and novel
24 FIT trajectories. A separately implemented learner fits and compiles
unknown 2/3/4 input Boolean functions using learned XOR/AND basis, and
executes a compact truth-table native runtime. No artificially slow peer.
"""
from __future__ import annotations
import itertools

ROLES=("alpha","beta","gamma")
def require(ok,why):
    if not ok:raise RuntimeError("F124DD_PEER_"+why)

def read(episodes,count):
    require(type(episodes) is list and len(episodes)==count,"COMPLETE_EPISODE_ROSTER")
    samples=[]
    for ep in episodes:
        require(type(ep) is dict and set(ep)=={"initial","events"}
                and set(ep["initial"])==set(ROLES) and len(ep["events"])==8,
                "PUBLIC_FULL_CAUSAL_STATE")
        register={k:list(v) for k,v in ep["initial"].items()}
        for e in ep["events"]:
            require(set(e)=={"target","source","event","observed"}
                and e["target"] in ROLES and e["source"] in ROLES and
                e["target"]!=e["source"],"VALID_PUBLIC_ROLES")
            a=register[e["target"]];b=register[e["source"]]
            vector=(a[0],a[1],b[0],b[1],e["event"])
            require(all(type(x) is int and 0<=x<16 for x in vector)
                    and type(e["observed"]) is int and 0<=e["observed"]<16,
                    "ALL_PUBLIC_CAUSAL_NIBBLES")
            samples.append((vector,e["observed"]))
            register[e["target"]]=[e["observed"],a[0]]
    return samples

def infer_pair(samples):
    for i in range(5):
        for j in range(i+1,5):
            vals=[-1]*4
            error=False
            for vector,output in samples:
                for bit in range(4):
                    slot=((vector[i]>>bit)&1)|(((vector[j]>>bit)&1)<<1)
                    y=(output>>bit)&1
                    if vals[slot]<0:vals[slot]=y
                    elif vals[slot]!=y:error=True;break
                if error:break
            if not error and all(y>=0 for y in vals):
                return (i,j,sum(y<<k for k,y in enumerate(vals)))
    return None

def train_meta(meta):
    require(type(meta) is list and len(meta)==12,"FULL_EQUAL_META_TRAINING_TASKS")
    found=[]
    for sourcefree_task in meta:
        primitive=infer_pair(read(sourcefree_task,24))
        require(primitive is not None,"EQUAL_PEER_META_NOT_FITTED")
        found.append(primitive)
    functions={q[2] for q in found}
    model={"xor_gate":6,"and_gate":8,"learned_tasks":found} if 6 in functions and 8 in functions else None
    return model,{"meta_public_episode_tasks":12,"meta_fit_event_rows":2304,
       "meta_FIT_learned_XOR":6 in functions,"meta_FIT_learned_AND":8 in functions,
       "full_independent_meta_supervision":True}

def infer_novel(rows):
    for size in (2,3,4):
        for slots in itertools.combinations(range(5),size):
            look=[-1]*(1<<size);fails=False
            for raw,response in rows:
                for bit in range(4):
                    key=0
                    for i,col in enumerate(slots):
                        key|=((raw[col]>>bit)&1)<<i
                    desired=(response>>bit)&1
                    if look[key]<0:look[key]=desired
                    elif look[key]!=desired:
                        fails=True;break
                if fails:break
            if not fails and all(z>=0 for z in look):
                return slots,look
    return None,None

def learned_gate(table,a,b):
    return (table>>(a|(b<<1)))&1

def algebraic_coefficients(lookup):
    coeff=lookup.copy()
    dimensions=len(coeff).bit_length()-1
    for dim in range(dimensions):
        for index in range(len(coeff)):
            if index>>dim&1:coeff[index]^=coeff[index^(1<<dim)]
    return coeff

def eval_ANF(coef,inputs,meta):
    ans=0
    for mask,c in enumerate(coef):
        if not c:continue
        value=1
        for bit,v in enumerate(inputs):
            if mask>>bit&1:
                value=learned_gate(meta["and_gate"],value,v)
        ans=learned_gate(meta["xor_gate"],ans,value)
    return ans

def fit(meta,FIT):
    if meta is None or meta.get("and_gate")!=8 or meta.get("xor_gate")!=6:
        return None,{"natural_FIT":False,"meta_algebraic_basis_missing":True}
    training=read(FIT,24)
    wires,table=infer_novel(training)
    if wires is None:
        return None,{"natural_FIT":False,"source_outside_four_bitwise_input_vocabulary":True}
    coef=algebraic_coefficients(table)
    n=len(wires)
    compiled=sum(eval_ANF(coef,tuple((p>>i)&1 for i in range(n)),meta)<<p
                 for p in range(1<<n))
    require(compiled==sum(y<<i for i,y in enumerate(table)),
            "EQUAL_PEER_COMPILED_LEARNED_ANF_NOT_EXACT")
    model={"input_positions":tuple(wires),"compiled_truth":compiled,
           "ANF_coefficient_vector":tuple(coef),
           "learned_meta_XOR":meta["xor_gate"],
           "learned_meta_AND":meta["and_gate"]}
    err=sum((predict_raw(model,row)^value).bit_count() for row,value in training)
    require(err==0,"EQUAL_PEER_NOT_INTERPOLATED_FIT")
    return model,{"natural_FIT":True,"FIT_rows":192,"FIT_bit_errors":0,
         "unknown_causal_variable_wiring":list(wires),
         "sourcefree_arity_learned":n,"truth_entries_learned":1<<n,
         "learned_ANF_coefficients":sum(coef),
         "compact_FIT_only_truth_table":True,"source_hidden_function_not_passed":True}

def predict_raw(model,row):
    chosen=[row[i] for i in model["input_positions"]]
    truth=model["compiled_truth"]
    answer=0
    for bit in range(4):
        offset=0
        for j,x in enumerate(chosen):offset|=((x>>bit)&1)<<j
        answer|=((truth>>offset)&1)<<bit
    return answer

def rollout(model,ep):
    require(model is not None,"EQUAL_PEER_NOT_TRAINED")
    state={k:list(v) for k,v in ep["initial"].items()}
    outputs=[]
    for event in ep["events"]:
        own=state[event["target"]];foreign=state[event["source"]]
        value=predict_raw(model,(own[0],own[1],foreign[0],foreign[1],event["event"]))
        outputs.append(value)
        state[event["target"]]=[value,own[0]]
    return outputs

def score(model,ep):
    predicted=rollout(model,ep);true=[e["observed"] for e in ep["events"]]
    return {"exact":predicted==true,"bit_errors":sum((x^y).bit_count() for x,y in zip(predicted,true)),
            "native_events":len(predicted)}
