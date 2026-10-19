"""F124-DA independent fully trained same-vocabulary strong peer.

Written separately from candidate: exhaustive three-wiring enumeration
over exactly same twenty public causal bits. Each wiring yields an
unspecified four-value Boolean table fitted from FIT ONLY. No source,
candidate, or private oracle imports. Independent search is exhaustive
on the same 7,600 raw input triples per output and never undertrained.
"""
from __future__ import annotations

NAMES=("alpha","beta","gamma")

def check(x):
    if (type(x) is not dict or set(x)!={"initial","events"}
        or type(x["initial"]) is not dict or set(x["initial"])!=set(NAMES)
        or len(x["events"])!=8):raise ValueError("F124DA_PEER_INPUT")
    for k in NAMES:
        row=x["initial"][k]
        if type(row) is not list or len(row)!=2 or not all(
              type(v) is int and 0<=v<16 for v in row):
            raise ValueError("F124DA_PEER_INITIAL")
    for e in x["events"]:
        if (type(e) is not dict or set(e)!={"target","source","event","observed"}
            or e["target"] not in NAMES or e["source"] not in NAMES
            or e["target"]==e["source"] or not all(type(e[q]) is int and
              0<=e[q]<16 for q in ("event","observed"))):
            raise ValueError("F124DA_PEER_EVENT")

def input_bits(memory,event):
    own=memory[event["target"]];foreign=memory[event["source"]]
    return (own[0]|own[1]<<4|foreign[0]<<8|foreign[1]<<12|
            event["event"]<<16)

def fit_records(episodes):
    if type(episodes) is not list or len(episodes)!=24:
        raise ValueError("F124DA_PEER_FIT_N")
    observations=[]
    for ep in episodes:
        check(ep)
        state={role:list(v) for role,v in ep["initial"].items()}
        for event in ep["events"]:
            observations.append((input_bits(state,event),event["observed"]))
            older=state[event["target"]][0]
            state[event["target"]]=[event["observed"],older]
    return observations

def search(bit,examples):
    # Search independently using 20-bit bitvectors to identify consistent
    # truth-table constraints. Same vocabulary and complete evaluation
    # work as candidate, different algorithmic layout.
    xs=[x for x,_ in examples]
    target=[(y>>bit)&1 for _,y in examples]
    bitcolumns=[[x>>col&1 for x in xs] for col in range(20)]
    for z in range(20):
        residual=[yy^zz for yy,zz in zip(target,bitcolumns[z])]
        for a in range(20):
            column_a=bitcolumns[a]
            for b in range(20):
                if a==b:continue
                table=[None,None,None,None]
                valid=True
                for row,(aa,bb) in enumerate(zip(column_a,bitcolumns[b])):
                    where=aa+(2*bb);required=residual[row]
                    if table[where] is None:table[where]=required
                    elif table[where]!=required:
                        valid=False;break
                if valid:
                    return (a,b,z,sum((v or 0)<<i for i,v in enumerate(table)))
    return None

def train(fit):
    data=fit_records(fit)
    learned=[]
    for bit in range(4):
        result=search(bit,data)
        if result is None:return None,{"natural_FIT":False,"rows":192,
                                      "full_operator_search":True}
        learned.append(result)
    err=sum((evaluate(x,learned)^y).bit_count() for x,y in data)
    if err:raise RuntimeError("F124DA_PEER_TRAINED_OPERATOR_NOT_FIT")
    return {"operators":learned},{"natural_FIT":True,"rows":192,
        "FIT_bit_errors":0,"fully_trained_4_truth_tables":True,
        "same_full_7600_wirings_each_bit":True,
        "independent_implementation":True,"CHECK_never_used_to_fit":True}

def evaluate(value,models):
    bits=0
    for output,(a,b,z,table) in enumerate(models):
        position=((value>>a)&1)|(((value>>b)&1)<<1)
        bits|=((((table>>position)&1)^((value>>z)&1))<<output)
    return bits

def predict(model,episode):
    check(episode)
    if model is None:raise ValueError("F124DA_PEER_ABSTAIN")
    memory={k:list(v) for k,v in episode["initial"].items()}
    answers=[]
    for row in episode["events"]:
        ans=evaluate(input_bits(memory,row),model["operators"])
        answers.append(ans)
        prev=memory[row["target"]][0]
        memory[row["target"]]=[ans,prev]
    return answers

def score(model,episode):
    answers=predict(model,episode)
    gold=[row["observed"] for row in episode["events"]]
    return {"exact":answers==gold,
       "bit_errors":sum((a^b).bit_count() for a,b in zip(answers,gold)),
       "native_events":len(answers)}
