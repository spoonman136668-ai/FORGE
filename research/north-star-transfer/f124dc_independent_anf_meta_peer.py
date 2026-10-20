"""F124-DC independent grammar-unaware full meta-trained ANF peer.

Independently infer Boolean-gate truth tables from identical 12 public
meta-task FIT sets; retain observed XOR/AND complete gates. In each heldout
task fit unknown three-input causal wiring and arbitrary eight-entry truth
table with a separate bit-column algorithm, compile it using algebraic
normal form (learned XOR/AND) without accessing source author or
candidate implementation. Same public examples, no CHECK-driven fit.
"""
from __future__ import annotations

ROLES=("alpha","beta","gamma")

def need(ok,msg):
    if not ok:raise RuntimeError("F124DC_PEER_"+msg)

def read_episodes(episodes,n):
    need(type(episodes) is list and len(episodes)==n,"PUBLIC_EPISODE_COUNT")
    rows=[]
    for ep in episodes:
        need(type(ep) is dict and set(ep)=={"initial","events"} and
             set(ep["initial"])==set(ROLES) and len(ep["events"])==8,"PUBLIC_EIGHT_EVENTS")
        need(all(type(v) is list and len(v)==2 and all(type(z) is int and 0<=z<16 for z in v)
                 for v in ep["initial"].values()),"PUBLIC_ROLE_INITIALS")
        state={k:list(v) for k,v in ep["initial"].items()}
        for row in ep["events"]:
            need(set(row)=={"target","source","event","observed"}
                 and row["target"] in ROLES and row["source"] in ROLES
                 and row["target"]!=row["source"] and all(
                     type(row[j]) is int and 0<=row[j]<16
                     for j in ("event","observed")),"PUBLIC_CAUSAL_EVENT")
            own=state[row["target"]];src=state[row["source"]]
            rows.append((own[0],own[1],src[0],src[1],row["event"],row["observed"]))
            state[row["target"]]=[row["observed"],own[0]]
    return rows

def discover_binary(records):
    for a in range(5):
        for b in range(a+1,5):
            values={}
            good=True
            for row in records:
                for bit in range(4):
                    slot=(row[a]>>bit&1)|((row[b]>>bit&1)<<1)
                    answer=row[5]>>bit&1
                    if slot in values and values[slot]!=answer:
                        good=False;break
                    values[slot]=answer
                if not good:break
            if good and len(values)==4:
                return a,b,sum(values[i]<<i for i in range(4))
    return None

def train_meta(tasks):
    need(type(tasks) is list and len(tasks)==12,"COMPLETE_12_META_TASKS")
    learned=[]
    for task in tasks:
        op=discover_binary(read_episodes(task,24))
        need(op is not None,"META_TRAINING_OPERATOR_UNKNOWN")
        learned.append(op)
    present={op[2] for op in learned}
    # The peer must have independently learned the two algebraic
    # primitives needed for normal-form compilation from public examples.
    return ({"learned_truth_functions":learned,"xor_truth":6,"and_truth":8}
            if 6 in present and 8 in present else None),{
          "trained_meta_tasks":12,"meta_event_rows":2304,
          "learned_binary_tasks":len(learned),
          "learned_full_ANF_gate_basis":6 in present and 8 in present}

def infer_ternary(records):
    for i in range(5):
        for j in range(i+1,5):
            for k in range(j+1,5):
                lookup=[-1]*8
                consistent=True
                for row in records:
                    for bit in range(4):
                        slot=(row[i]>>bit&1)|((row[j]>>bit&1)<<1)|((row[k]>>bit&1)<<2)
                        ans=row[5]>>bit&1
                        if lookup[slot]<0:lookup[slot]=ans
                        elif lookup[slot]!=ans:
                            consistent=False;break
                    if not consistent:break
                if consistent:
                    return (i,j,k),lookup
    return None,None

def to_anf(truth):
    coeff=truth[:]
    for index in range(3):
        for mask in range(8):
            if mask>>index&1:coeff[mask]^=coeff[mask^(1<<index)]
    return coeff

def train_novel(meta_model,FIT):
    if meta_model is None or meta_model.get("xor_truth")!=6 or meta_model.get("and_truth")!=8:
        return None,{"natural_FIT":False,"learned_algebraic_primitives_missing":True}
    records=read_episodes(FIT,24)
    wiring,lookup=infer_ternary(records)
    if wiring is None or any(x<0 for x in lookup):
        return None,{"natural_FIT":False,"source_outside_full_three_input_ANF":True}
    model={"input_positions":wiring,"ANF_coefficients":to_anf(lookup),
           "meta_learned_xor_table":meta_model["xor_truth"],
           "meta_learned_and_table":meta_model["and_truth"]}
    errors=sum((predict_raw(model,row)^row[5]).bit_count() for row in records)
    need(errors==0,"FIT_ANF_WHOLE_PROGRAM_ERROR")
    return model,{"natural_FIT":True,"FIT_rows":192,
                  "FIT_bit_errors":0,
                  "learned_boolean_truth_values":8,
                  "causal_raw_slots":list(wiring),
                  "ANF_coefficient_count":sum(model["ANF_coefficients"]),
                  "learned_public_meta_gates_used":True}

def learned_gate(table,x,y):
    return (table>>(x|(y<<1)))&1

def eval_one(coeff,a,b,c,and_gate,xor_gate):
    signal=(a,b,c)
    ans=0
    for mask in range(8):
        if coeff[mask]:
            term=1
            for i in range(3):
                if mask>>i&1:term=learned_gate(and_gate,term,signal[i])
            ans=learned_gate(xor_gate,ans,term)
    return ans

def predict_raw(model,row):
    raw=[row[i] for i in model["input_positions"]]
    answer=0
    for bit in range(4):
        q=[z>>bit&1 for z in raw]
        answer|=(eval_one(model["ANF_coefficients"],*q,
                   model["meta_learned_and_table"],model["meta_learned_xor_table"])<<bit)
    return answer

def rollout(model,episode):
    need(model is not None,"FIT_LEARNED_PEER_REQUIRED")
    state={role:list(v) for role,v in episode["initial"].items()}
    outs=[]
    for e in episode["events"]:
        a=state[e["target"]];b=state[e["source"]]
        answer=predict_raw(model,(a[0],a[1],b[0],b[1],e["event"]))
        outs.append(answer)
        state[e["target"]]=[answer,a[0]]
    return outs

def score(model,ep):
    result=rollout(model,ep);expected=[x["observed"] for x in ep["events"]]
    return {"exact":result==expected,"bit_errors":sum((x^y).bit_count()
       for x,y in zip(result,expected)),"native_events":len(result)}
