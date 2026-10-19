"""F124-DA data-driven induction of causal operator truth tables and wiring.

No hidden source grammar imported. For each of four outputs, search all
20x19x20 raw-bit wiring triples (A,B,Z). The learned Boolean operator is
an arbitrary four-entry truth table; infer all observed entries entirely
from supervised FIT trajectories, with deterministic zero defaults for
unseen entries. The operator is applied across ALL entity role pairs.

This is bounded program/operator induction: the generic 2-input LUT XOR
one raw bit skeleton is supplied, but neither concrete operator truth
tables nor source/target/event wiring are supplied. Claim no unrestricted
discovery beyond the skeleton.
"""
from __future__ import annotations
import hashlib
import json

ROLES=("alpha","beta","gamma")
BITS=20
WIRES=BITS*(BITS-1)*BITS

def need(ok,why):
    if not ok:raise ValueError("F124DA_LEARNER_"+why)

def validate(ep):
    need(type(ep) is dict and set(ep)=={"initial","events"} and
         type(ep["initial"]) is dict and set(ep["initial"])==set(ROLES),
         "EXACT_PUBLIC_EPISODE")
    need(all(type(x) is list and len(x)==2 and
        all(type(v) is int and 0<=v<16 for v in x)
        for x in ep["initial"].values()),"BOUNDED_PUBLIC_INITIAL")
    need(type(ep["events"]) is list and len(ep["events"])==8 and all(
        type(e) is dict and set(e)=={"target","source","event","observed"} and
        e["target"] in ROLES and e["source"] in ROLES and e["target"]!=e["source"]
        and type(e["event"]) is int and 0<=e["event"]<16 and
        type(e["observed"]) is int and 0<=e["observed"]<16
        for e in ep["events"]),"EIGHT_PUBLIC_CAUSAL_EVENTS")

def raw(mem,e):
    own=mem[e["target"]];src=mem[e["source"]]
    return own[0]|(own[1]<<4)|(src[0]<<8)|(src[1]<<12)|(e["event"]<<16)

def fit_rows(episodes):
    need(type(episodes) is list and len(episodes)==24,
         "COMPLETE_24_FIT_ONLY")
    records=[]
    for ep in episodes:
        validate(ep)
        mem={k:list(x) for k,x in ep["initial"].items()}
        for row in ep["events"]:
            records.append((raw(mem,row),row["observed"]))
            previous=mem[row["target"]][0]
            # Only FIT may use teacher-supervised state updates.
            mem[row["target"]]=[row["observed"],previous]
    need(len(records)==192,"192_FULL_FIT_EVENT_ROWS")
    return records

def infer_bit(records,output_bit):
    # Indexed by triple (a,b,z) and four unknown Boolean truth values.
    # Exhaustively fit 7,600 possible wirings per output, in canonical
    # order. Reject inconsistencies; CHECK labels play no role.
    y=[(answer>>output_bit)&1 for _,answer in records]
    for z in range(20):
        for a in range(20):
            for b in range(20):
                if a==b:continue
                seen=0;table=0;consistent=True
                for (value,_),target in zip(records,y):
                    slot=((value>>a)&1)|(((value>>b)&1)<<1)
                    required=target^((value>>z)&1)
                    seen_bit=1<<slot
                    if seen&seen_bit:
                        if ((table>>slot)&1)!=required:
                            consistent=False;break
                    else:
                        seen|=seen_bit
                        if required:table|=seen_bit
                if consistent:return (a,b,z,table),{"observed_table_entries":seen.bit_count(),
                      "fit_consistent":True}
    return None,{"fit_consistent":False}

def train(fit):
    rows=fit_rows(fit)
    operators=[];op_receipts=[]
    for bit in range(4):
        operator,receipt=infer_bit(rows,bit)
        if operator is None:
            return None,{"natural_FIT":False,
              "operators_learned":len(operators),
              "FIT_rows":192,"bounded_search_wirings_each_bit":WIRES}
        operators.append(operator);op_receipts.append(receipt)
    mistakes=sum((evaluate_raw(value,operators)^answer).bit_count()
                  for value,answer in rows)
    need(mistakes==0,"FITTED_OPERATOR_CONSISTENCY")
    return {"learned_operators":operators},{
        "natural_FIT":True,"FIT_rows":192,"FIT_bit_errors":0,
        "operators_learned":len(operators),"all_Boolean_truth_tables_FIT_inferred":True,
        "all_raw_input_wiring_FIT_searched":True,"per_bit_search_budget":WIRES,
        "learned_table_entries":[x["observed_table_entries"] for x in op_receipts],
        "source_generator_not_used":True}

def evaluate_raw(value,ops):
    output=0
    for bit,(a,b,z,truth) in enumerate(ops):
        slot=((value>>a)&1)|(((value>>b)&1)<<1)
        output|=((((truth>>slot)&1)^((value>>z)&1))<<bit)
    return output

def rollout(model,ep):
    validate(ep)
    need(model is not None and set(model)=={"learned_operators"},
         "LEARNED_FIT_OPERATOR_REQUIRED")
    mem={k:list(v) for k,v in ep["initial"].items()}
    prediction=[]
    for event in ep["events"]:
        result=evaluate_raw(raw(mem,event),model["learned_operators"])
        prediction.append(result)
        before=mem[event["target"]][0]
        mem[event["target"]]=[result,before]
    return prediction

def score(model,ep):
    pred=rollout(model,ep)
    truth=[row["observed"] for row in ep["events"]]
    return {"exact":pred==truth,"bit_errors":sum((x^y).bit_count() for x,y in zip(pred,truth)),
            "native_events":len(pred)}

def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()
