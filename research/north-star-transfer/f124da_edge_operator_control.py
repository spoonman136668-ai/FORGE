"""F124-DA role-edge-conditioned full search control, equal vocabulary.

Trains SIX distinct source-target operator lexicons from corresponding
parts of the SAME 24 FIT episodes. Every edge gets complete search of
20×19×20 wirings per output, no intentionally weak control. Sharing across
role assignments is its only structural disadvantage.
"""
import f124da_independent_operator_peer as peer

ROLES=("alpha","beta","gamma")
EDGES=tuple((a,b) for a in ROLES for b in ROLES if a!=b)

def train(fit):
    if type(fit) is not list or len(fit)!=24:
        raise ValueError("F124DA_EDGE_FIT_PROTOCOL")
    samples={edge:[] for edge in EDGES}
    for ep in fit:
        peer.check(ep)
        state={name:list(value) for name,value in ep["initial"].items()}
        for event in ep["events"]:
            k=(event["target"],event["source"])
            samples[k].append((peer.input_bits(state,event),event["observed"]))
            prior=state[event["target"]][0]
            state[event["target"]]=[event["observed"],prior]
    learned={}
    for relation,records in samples.items():
        ops=[]
        for bit in range(4):
            op=peer.search(bit,records)
            if op is None:
                return None,{"natural_FIT":False,"underconstrained_relation":relation,
                       "observed_FIT_events":sum(len(x) for x in samples.values())}
            ops.append(op)
        learned[relation]=ops
    errors=sum((peer.evaluate(raw,learned[rel])^out).bit_count()
               for rel,rows in samples.items() for raw,out in rows)
    if errors:raise RuntimeError("F124DA_EDGE_FIT_ERRORS")
    return {"per_edge_operators":learned},{"natural_FIT":True,
        "FIT_rows":192,"FIT_bit_errors":0,
        "trained_complete_directed_role_pairs":len(learned),
        "same_20_raw_bit_feature_vocabulary":True,
        "same_7600_wiring_search_budget_per_output_edge":True,
        "distinct_role_binding_models":True}

def score(model,ep):
    peer.check(ep)
    if model is None:raise ValueError("F124DA_EDGE_NO_FITTED_MODEL")
    state={k:list(v) for k,v in ep["initial"].items()}
    outputs=[]
    for e in ep["events"]:
        k=(e["target"],e["source"])
        value=peer.evaluate(peer.input_bits(state,e),model["per_edge_operators"][k])
        outputs.append(value)
        earlier=state[e["target"]][0]
        state[e["target"]]=[value,earlier]
    gold=[e["observed"] for e in ep["events"]]
    return {"exact":outputs==gold,"bit_errors":sum((x^y).bit_count()
           for x,y in zip(outputs,gold)),"native_events":8}
