"""F124-DA fully trained directed-edge PROGRAM search control.

Same complete 3456-program grammar and 24 FIT sequences as pooled arms.
Six separately learned source/target edge programs; no reduced primitive
set or limited search. Exposes the cost of fragmented causal evidence.
"""
import f124da_independent_program_control as peer

ROLES=peer.ROLES
EDGES=tuple((t,s) for t in ROLES for s in ROLES if t!=s)

def train(fit):
    if type(fit) is not list or len(fit)!=24:
        raise ValueError("DA_EDGE_FROZEN_FIT")
    rows={k:[] for k in EDGES}
    for episode in fit:
        peer.verify(episode)
        memory={name:list(v) for name,v in episode["initial"].items()}
        for e in episode["events"]:
            pair=e["target"],e["source"]
            rows[pair].append((peer.vector(memory,e),e["observed"]))
            old=memory[e["target"]][0]
            memory[e["target"]]=[e["observed"],old]
    models={};possible={}
    for pair,samples in rows.items():
        learned,count=peer.learn_from_rows(samples)
        if learned is None:
            return None,{"all_edges_fitted":False,"failed_edge":list(pair)}
        models[pair]=learned
        possible["/".join(pair)]=count
    return {"edge_programs":models},{"all_edges_fitted":True,
        "full_FIT_rows":192,"edge_programs":6,
        "complete_3456_grammar_per_edge":True,
        "all_edges_fit_consistent_counts":possible,
        "no_CHECK_or_HELDOUT_fit":True}

def score(model,ep):
    peer.verify(ep)
    if model is None:raise ValueError("DA_EDGE_NO_MODEL")
    memory={name:list(v) for name,v in ep["initial"].items()}
    result=[]
    for e in ep["events"]:
        value=peer.compute(model["edge_programs"][e["target"],e["source"]],
                           peer.vector(memory,e))
        old=memory[e["target"]][0]
        memory[e["target"]]=[value,old]
        result.append(value)
    target=[e["observed"] for e in ep["events"]]
    return {"correct":result==target,
      "bit_errors":sum((a^b).bit_count() for a,b in zip(result,target)),
      "native_event_calls":8}
