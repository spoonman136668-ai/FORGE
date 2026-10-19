"""F124-DB independently trained meta-synthesis peer.

Same primitive DSL, same 12 public meta-training tasks, same full
24-episode novel FIT budget and exhaustive library-pair/top-operation
composition. Independently implemented; no import of candidate or source
generator. No missing training privileges or deliberately weak baseline.
"""
from __future__ import annotations

R=("alpha","beta","gamma")
OPS=("xor","add","and")

def check(ep):
    if type(ep) is not dict or set(ep)!={"initial","events"} or set(ep["initial"])!=set(R) or len(ep["events"])!=8:
        raise ValueError("F124DB_CONTROL_EP")
    if not all(type(v) is list and len(v)==2 and all(type(n) is int and 0<=n<16 for n in v)
               for v in ep["initial"].values()):raise ValueError("F124DB_CONTROL_INIT")
    if not all(type(x) is dict and set(x)=={"target","source","event","observed"} and
               x["target"] in R and x["source"] in R and x["target"]!=x["source"] and
               all(type(x[k]) is int and 0<=x[k]<16 for k in ("event","observed"))
               for x in ep["events"]):raise ValueError("F124DB_CONTROL_EVENT")

def read_training(examples,n):
    if type(examples) is not list or len(examples)!=n:raise ValueError("F124DB_CONTROL_FIT_N")
    data=[]
    for ep in examples:
        check(ep)
        memory={r:list(v) for r,v in ep["initial"].items()}
        for x in ep["events"]:
            t=x["target"];source=x["source"]
            a=memory[t];b=memory[source]
            data.append((a[0],a[1],b[0],b[1],x["event"],x["observed"]))
            memory[t]=[x["observed"],a[0]]
    return data

def calc(operator,a,b):
    if operator=="xor":return a^b
    if operator=="add":return (a+b)%16
    if operator=="and":return a&b
    raise ValueError("F124DB_CONTROL_OPERATOR")

def extract(task):
    records=read_training(task,24)
    for op in OPS:
        for i in range(5):
            for j in range(5):
                if i==j:continue
                if all(calc(op,row[i],row[j])==row[5] for row in records):
                    return (op,i,j)
    return None

def train_meta(tasks):
    if type(tasks) is not list or len(tasks)!=12:raise ValueError("F124DB_CONTROL_ALL_META_TASKS")
    learned=[]
    for task in tasks:
        program=extract(task)
        if program is None:raise ValueError("F124DB_CONTROL_META_NOT_LEARNED")
        if program not in learned:learned.append(program)
    if len(learned)<2 or len(learned)>12:raise ValueError("F124DB_CONTROL_LIBRARY_NOT_REUSABLE")
    return {"macros":learned},{"meta_trained_tasks":12,"meta_training_event_rows":2304,
           "distinct_learned_primitive_motifs":len(learned),
           "same_meta_fit_data_and_full_primitive_vocabulary":True}

def synth(model,fit):
    samples=read_training(fit,24)
    library=model["macros"]
    checked=0
    for op in OPS:
        for A in library:
            for B in library:
                checked+=1
                oa,ia,ja=A;ob,ib,jb=B
                if all(calc(op,calc(oa,row[ia],row[ja]),
                         calc(ob,row[ib],row[jb]))==row[5] for row in samples):
                    return {"chosen":(op,A,B)},{
                       "natural_FIT":True,"FIT_rows":192,"FIT_bit_errors":0,
                       "programs_checked":checked,"complete_search_size":len(library)**2*len(OPS),
                       "learned_meta_motifs_used_in_program":2,
                       "no_CHECK_based_selection":True}
    return None,{"natural_FIT":False,"FIT_rows":192,"programs_checked":checked}

def predict(model,ep):
    check(ep)
    if model is None:raise ValueError("F124DB_CONTROL_ABSTAIN")
    state={k:list(v) for k,v in ep["initial"].items()}
    result=[]
    top,A,B=model["chosen"]
    for event in ep["events"]:
        own=state[event["target"]];src=state[event["source"]]
        row=(own[0],own[1],src[0],src[1],event["event"])
        n=calc(top,calc(A[0],row[A[1]],row[A[2]]),
               calc(B[0],row[B[1]],row[B[2]]))
        result.append(n)
        state[event["target"]]=[n,own[0]]
    return result

def score(model,ep):
    pred=predict(model,ep)
    true=[x["observed"] for x in ep["events"]]
    return {"exact":pred==true,"bit_errors":sum((x^y).bit_count() for x,y in zip(pred,true)),
            "native_events":len(pred)}
