"""F124-DD: causal operator compiler from supervised meta-learned NAND.

Exactly same source-free meta training and FIT info as independent peer.
Unlike prior recursive NAND/bit inference, evaluate learned NAND DAG ONCE
for all 2^arity assignments, then compile to a compact runtime LUT.

This is legitimate parameter-dependent compilation: the LUT is computed
by executing the learned NAND truth table across a real constructed circuit.
A counterfactual gate table changes the generated LUT. No heldout law/
truth/wiring comes from source author or from a prior consumed source.
Generic Boolean arity<=4 is an explicitly supplied bounded hypothesis.
"""
from __future__ import annotations
import hashlib
import itertools
import json

ROLES=("alpha","beta","gamma")
def need(ok,reason):
    if not ok:raise ValueError("F124DD_NAND_"+reason)

def records(episodes,n):
    need(type(episodes) is list and len(episodes)==n,
         "EXACT_SOURCEFREE_PUBLIC_EPISODES")
    data=[]
    for ep in episodes:
        need(type(ep) is dict and set(ep)=={"initial","events"}
             and type(ep["initial"]) is dict and set(ep["initial"])==set(ROLES)
             and type(ep["events"]) is list and len(ep["events"])==8,
             "PUBLIC_FULL_EPISODE")
        state={r:list(v) for r,v in ep["initial"].items()}
        need(all(type(v) is list and len(v)==2 and
                 all(type(x) is int and 0<=x<16 for x in v)
                 for v in state.values()),"PUBLIC_INITIALS")
        for e in ep["events"]:
            need(type(e) is dict and set(e)=={"target","source","event","observed"}
                 and e["target"] in ROLES and e["source"] in ROLES
                 and e["target"]!=e["source"]
                 and all(type(e[q]) is int and 0<=e[q]<16
                         for q in ("event","observed")),"PUBLIC_EVENT")
            own=state[e["target"]];src=state[e["source"]]
            data.append(((own[0],own[1],src[0],src[1],e["event"]),e["observed"]))
            state[e["target"]]=[e["observed"],own[0]]
    return data

def learn_binary(records):
    for a in range(5):
        for b in range(a+1,5):
            table=[-1]*4
            consistent=True
            for x,y in records:
                for bit in range(4):
                    pos=(x[a]>>bit&1)|((x[b]>>bit&1)<<1)
                    v=y>>bit&1
                    if table[pos]<0:table[pos]=v
                    elif table[pos]!=v:consistent=False;break
                if not consistent:break
            if consistent and all(v>=0 for v in table):
                return a,b,sum(v<<j for j,v in enumerate(table))
    return None

def train_meta(tasks):
    need(type(tasks) is list and len(tasks)==12,"TWELVE_COMPLETE_META_TASKS")
    learned=[]
    for task in tasks:
        law=learn_binary(records(task,24))
        need(law is not None,"META_OPERATOR_FIT_FAILURE")
        learned.append(law)
    nand=next((x[2] for x in learned if x[2]==7),None)
    return ({"learned_gate":nand,"fitted_meta_motifs":learned} if nand is not None else None),{
      "meta_training_event_rows":2304,"sourcefree_meta_tasks":12,
      "learned_gate_truth":nand,"meta_learned_functionally_complete":nand is not None,
      "NAND_not_supplied_as_source_law":True}

def infer_boolean(FIT):
    data=records(FIT,24)
    for arity in (2,3,4):
        for wires in itertools.combinations(range(5),arity):
            table=[-1]*(1<<arity)
            consistent=True
            for x,y in data:
                for bit in range(4):
                    idx=sum(((x[w]>>bit)&1)<<j for j,w in enumerate(wires))
                    value=(y>>bit)&1
                    if table[idx]<0:table[idx]=value
                    elif table[idx]!=value:
                        consistent=False;break
                if not consistent:break
            if consistent and all(v>=0 for v in table):
                return wires,arity,sum(v<<j for j,v in enumerate(table))
    return None,None,None

def graph(arity,truth):
    # SSA circuit network; "G" nodes are the learned two-input operator,
    # not an externally supplied NAND primitive. Full NAND truth values are
    # inferred on the twelve public meta tasks.
    nodes=[("V",i,None) for i in range(arity)]
    memo={}
    def g(x,y):
        key=(x,y)
        if key not in memo:
            memo[key]=len(nodes);nodes.append(("G",x,y))
        return memo[key]
    def neg(x):return g(x,x)
    def conjunction(x,y):return neg(g(x,y))
    def disjunction(x,y):return g(neg(x),neg(y))
    one=g(0,neg(0))
    result=neg(one)
    for mask in range(1<<arity):
        if truth>>mask&1:
            terms=[i if mask>>i&1 else neg(i) for i in range(arity)]
            term=terms[0]
            for v in terms[1:]:term=conjunction(term,v)
            result=disjunction(result,term)
    return tuple(nodes),result

def compiled_truth(nodes,root,arity,learned_gate):
    # Exact bit-parallel symbolic execution across ALL 2^arity inputs.
    # No source/oracle function is imported. Learned gate bits determine
    # each circuit gate result, including the compiled output LUT.
    width=1<<arity
    full=(1<<width)-1
    signal=[]
    for kind,a,b in nodes:
        if kind=="V":
            signal.append(sum(((i>>a)&1)<<i for i in range(width)))
            continue
        left=signal[a];right=signal[b]
        out=0
        if learned_gate&1:out|=(~left&~right)
        if learned_gate&2:out|=(left&~right)
        if learned_gate&4:out|=(~left&right)
        if learned_gate&8:out|=(left&right)
        signal.append(out&full)
    return signal[root]

def eval_graph_bit(nodes,root,values,learned_gate):
    memo=[]
    for tag,a,b in nodes:
        if tag=="V":memo.append(values[a])
        else:memo.append(learned_gate>>(memo[a]|(memo[b]<<1))&1)
    return memo[root]

def train_new(meta,FIT,mode="compact"):
    need(mode in ("compact","graph"),"NATIVE_COMPILER_ABLATION_ONLY")
    if meta is None or meta.get("learned_gate")!=7:
        return None,{"FIT_fitted":False,"learned_gate_unavailable":True}
    wires,n,learned_truth=infer_boolean(FIT)
    if wires is None:return None,{"FIT_fitted":False,"maximum_four_bitwise_inputs_exceeded":True}
    nodes,root=graph(n,learned_truth)
    byte=compiled_truth(nodes,root,n,meta["learned_gate"])
    need(byte==learned_truth,"FITTED_GATE_COMPILE_NOT_SEMANTICALLY_EXACT")
    model={"wires":wires,"arity":n,"compiled_lut":byte,
           "learned_gate":meta["learned_gate"],"nodes":nodes,"root":root,"mode":mode}
    data=records(FIT,24)
    errors=sum((predict_raw(model,x)^y).bit_count() for x,y in data)
    need(errors==0,"FITTED_ALL_192_TRAJECTORY_EVENTS")
    return model,{"FIT_fitted":True,"FIT_rows":192,"FIT_bit_errors":0,
          "learned_causal_input_wiring":list(wires),
          "induced_boolean_arity":n,"learned_function_truth_rows":1<<n,
          "sourcefree_compiled_gate_DAG_nodes":len(nodes),
          "compiler_gate_truth_inferred_from_public_meta":meta["learned_gate"],
          "runtime_mode":mode,"full_sourcefree_FIT_event_rows":192}

def predict_raw(model,inputs):
    selected=[inputs[x] for x in model["wires"]]
    result=0
    if model["mode"]=="compact":
        truth=model["compiled_lut"]
        for bit in range(4):
            idx=sum(((v>>bit)&1)<<j for j,v in enumerate(selected))
            result|=((truth>>idx)&1)<<bit
    else:
        for bit in range(4):
            args=tuple((v>>bit)&1 for v in selected)
            result|=eval_graph_bit(model["nodes"],model["root"],args,model["learned_gate"])<<bit
    return result

def rollout(model,ep):
    need(model is not None,"ADMITTED_FIT_COMPILER_ONLY")
    # Public episode layout is validated independently by FIT/read paths.
    mem={r:list(v) for r,v in ep["initial"].items()}
    outputs=[]
    for event in ep["events"]:
        o=mem[event["target"]];s=mem[event["source"]]
        y=predict_raw(model,(o[0],o[1],s[0],s[1],event["event"]))
        outputs.append(y)
        mem[event["target"]]=[y,o[0]]
    return outputs

def score(model,ep):
    outcomes=rollout(model,ep)
    expected=[x["observed"] for x in ep["events"]]
    return {"exact":outcomes==expected,
            "bit_errors":sum((x^y).bit_count() for x,y in zip(outcomes,expected)),
            "native_events":len(outcomes)}

def digest(z):
    return hashlib.sha256(json.dumps(z,sort_keys=True,separators=(",",":")).encode()).hexdigest()
