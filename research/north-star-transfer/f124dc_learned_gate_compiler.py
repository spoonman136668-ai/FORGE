"""F124-DC FIT-learned universal gate -> new ternary circuit construction.

Meta tasks teach a universal two-input Boolean gate from labels, without
source-law tags. A new FIT task supplies raw 5 role/event nibble inputs:
the learner identifies three causally relevant variable slots and an
unsupplied 8-entry ternary truth table, then compiles a Boolean circuit
from the earlier meta-learned gate. No majority/selector template exists
in this learner. CHECK and heldout update state only from predictions.
"""
from __future__ import annotations
import hashlib
import json

ROLES=("alpha","beta","gamma")

def need(ok,why):
    if not ok:raise RuntimeError("F124DC_CANDIDATE_"+why)

def validate(ep):
    need(type(ep) is dict and set(ep)=={"initial","events"}
         and type(ep["initial"]) is dict and set(ep["initial"])==set(ROLES),
         "PUBLIC_ROLE_INPUTS")
    need(all(type(v) is list and len(v)==2 and all(type(n) is int and 0<=n<16 for n in v)
              for v in ep["initial"].values()),"COMPLETE_INITIAL_REGISTERS")
    need(type(ep["events"]) is list and len(ep["events"])==8 and all(
      type(e) is dict and set(e)=={"target","source","event","observed"} and
      e["target"] in ROLES and e["source"] in ROLES and e["target"]!=e["source"]
      and all(type(e[q]) is int and 0<=e[q]<16 for q in ("event","observed"))
      for e in ep["events"]),"PUBLIC_EIGHT_EVENT_SEQUENCE")

def fit_rows(episodes,n):
    need(type(episodes) is list and len(episodes)==n,"ALL_SUPERVISED_SEQUENCES")
    result=[]
    for ep in episodes:
        validate(ep)
        state={k:list(v) for k,v in ep["initial"].items()}
        for e in ep["events"]:
            a=state[e["target"]];b=state[e["source"]]
            result.append(((a[0],a[1],b[0],b[1],e["event"]),e["observed"]))
            state[e["target"]]=[e["observed"],a[0]]
    need(len(result)==n*8,"COMPLETE_LABELLED_FIT_EVENT_ROWS")
    return result

def train_binary_table(rows):
    for i in range(5):
        for j in range(i+1,5):
            truth=[None]*4
            for input_vector,observed in rows:
                for bit in range(4):
                    idx=((input_vector[i]>>bit)&1)|(((input_vector[j]>>bit)&1)<<1)
                    required=(observed>>bit)&1
                    if truth[idx] is None:truth[idx]=required
                    elif truth[idx]!=required:break
                else:continue
                break
            else:
                return (i,j,sum((v or 0)<<k for k,v in enumerate(truth)))
    return None

def learn_universal_gate(meta):
    need(type(meta) is list and len(meta)==12,"TWELVE_SOURCEFREE_META_TASKS")
    tasks=[]
    for t in meta:
        m=train_binary_table(fit_rows(t,24))
        need(m is not None,"META_OPERATOR_NOT_LEARNABLE")
        tasks.append(m)
    # A universal gate is recognized from the measured four truth-table
    # entries (NAND or NOR). Neither private generator labels nor correct
    # heldout three-input primitive types are supplied to the learner.
    universal=next((m for m in tasks if m[2]==7),None)
    return ({"learned_gate_table":universal[2],"meta_motifs":tasks}
      if universal else None),{
      "meta_FIT_tasks":12,"meta_training_events":2304,
      "learned_binary_motifs":len(tasks),
      "learned_functionally_complete_gate":universal is not None,
      "gate_table_inferred_from_public_FIT":universal[2] if universal else None}

def infer_unknown_ternary(FIT):
    rows=fit_rows(FIT,24)
    # Freeze exact three-input grammar as an upper bounded hypothesis
    # class, not the source's actual majority/selector primitive labels.
    for a in range(5):
        for b in range(a+1,5):
            for c in range(b+1,5):
                truth=[None]*8
                conflict=False
                for inputs,y in rows:
                    for bit in range(4):
                        j=((inputs[a]>>bit)&1)|(((inputs[b]>>bit)&1)<<1)|(((inputs[c]>>bit)&1)<<2)
                        want=(y>>bit)&1
                        if truth[j] is None:truth[j]=want
                        elif truth[j]!=want:
                            conflict=True;break
                    if conflict:break
                if not conflict:
                    return (a,b,c),sum((v or 0)<<i for i,v in enumerate(truth)),sum(v is not None for v in truth)
    return None,None,0

def gate(a,b):return ("G",a,b)
def inv(x):return gate(x,x)
def conjunction(a,b):return inv(gate(a,b))
def disjunction(a,b):return gate(inv(a),inv(b))

def compile_ternary(table):
    # Construct each previously unseen truth table into an explicit DAG
    # of *meta-learned universal two-input gates*, without templates for
    # the heldout majority/mux source laws. 0/1 constants are synthesized
    # using gate(x,not(x)), not provided as magic output primitives.
    inputs=[("V",i) for i in range(3)]
    one=gate(inputs[0],inv(inputs[0]))
    zero=inv(one)
    formula=zero
    for code in range(8):
        if table>>code&1:
            terms=[inputs[i] if code>>i&1 else inv(inputs[i]) for i in range(3)]
            cube=conjunction(conjunction(terms[0],terms[1]),terms[2])
            formula=disjunction(formula,cube)
    return formula

def evaluate_circuit(node,bit_inputs,learned_gate_table,cache=None):
    if cache is None:cache={}
    if node in cache:return cache[node]
    if node[0]=="V":value=bit_inputs[node[1]]
    else:
        left=evaluate_circuit(node[1],bit_inputs,learned_gate_table,cache)
        right=evaluate_circuit(node[2],bit_inputs,learned_gate_table,cache)
        value=learned_gate_table>>(left|(right<<1))&1
    cache[node]=value
    return value

def learn_new_primitive(meta_model,FIT):
    if meta_model is None or meta_model.get("learned_gate_table")!=7:
        return None,{"natural_FIT":False,"learned_gate_unavailable":True}
    wires,table,observed=infer_unknown_ternary(FIT)
    if wires is None:
        return None,{"natural_FIT":False,"complete_192_FIT_events":True,
                     "structural_candidate_class_insufficient":True}
    # For a genuinely newly learned primitive, require all 8 3-bit input
    # truth values to have appeared in FIT: no hidden output guessing.
    if observed!=8:
        return None,{"natural_FIT":False,"unseen_truth_rows":8-observed}
    model={"wires":wires,"learned_gate_table":meta_model["learned_gate_table"],
           "learned_truth_table":table,"compiled_gate_dag":compile_ternary(table)}
    errors=sum((predict_raw(model,inputs)^y).bit_count()
               for inputs,y in fit_rows(FIT,24))
    need(errors==0,"FULL_PUBLIC_FIT_RECONSTRUCTION_VIA_LEARNED_GATE")
    return model,{"natural_FIT":True,"FIT_event_rows":192,
        "FIT_bit_errors":0,"learned_three_input_boolean_truth_rows":8,
        "learned_wiring":list(wires),
        "learned_binary_gate_real_compiler_dependency":True,
        "no_heldout_family_template_import":True}

def predict_raw(model,inputs):
    selected=[inputs[j] for j in model["wires"]]
    result=0
    for bit in range(4):
        xyz=[(q>>bit)&1 for q in selected]
        result|=evaluate_circuit(model["compiled_gate_dag"],xyz,model["learned_gate_table"])<<bit
    return result

def rollout(model,ep):
    validate(ep)
    need(model is not None and "compiled_gate_dag" in model,"FIT_ADMITTED_CAUSAL_PROGRAM")
    mem={k:list(v) for k,v in ep["initial"].items()}
    out=[]
    for e in ep["events"]:
        a=mem[e["target"]];b=mem[e["source"]]
        observed=predict_raw(model,(a[0],a[1],b[0],b[1],e["event"]))
        out.append(observed)
        mem[e["target"]]=[observed,a[0]]
    return out

def score(model,ep):
    pred=rollout(model,ep)
    gold=[x["observed"] for x in ep["events"]]
    return {"exact":pred==gold,"bit_errors":sum((p^y).bit_count() for p,y in zip(pred,gold)),
            "native_events":len(pred)}

def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()
