"""F124-CZ separately fitted directed-edge nonlinear causal comparator.

All six ordered role-pair programs receive same complete causal public
states/event 211-bit degree-two basis as both pooled learners. Each edge
is trained exactly to consistency with its own FIT rows; no under-training,
CHECK tuning, source-law access, or candidate implementation import.
"""
from __future__ import annotations
import f124cz_independent_pooled_control as base

ROLES=("alpha","beta","gamma")
EDGES=tuple((a,b) for a in ROLES for b in ROLES if a!=b)

def fit(episodes):
    if type(episodes) is not list or len(episodes)!=24:
        raise ValueError("F124CZ_EDGE_24_FIT")
    rows={k:[] for k in EDGES}
    for ep in episodes:
        base.check_episode(ep)
        mem={k:list(v) for k,v in ep["initial"].items()}
        for row in ep["events"]:
            key=(row["target"],row["source"])
            rows[key].append((base.encode(mem,row),row["observed"]))
            old=mem[row["target"]][0]
            mem[row["target"]]=[row["observed"],old]
    weights={}
    ranks={}
    for key,samples in rows.items():
        masks=[]
        for bit in range(4):
            learned,rank=base.eliminate(samples,bit)
            if learned is None:
                return None,{"natural_model_fitted":False,
                     "edge_not_fit_consistent":list(key)}
            masks.append(learned)
            ranks["/".join(key)]=rank
        weights[key]=masks
    err=sum((base.infer(x,weights[key])^y).bit_count()
            for key,items in rows.items() for x,y in items)
    if err:raise RuntimeError("F124CZ_EDGE_FIT_ERROR")
    return {"directed":weights},{"natural_model_fitted":True,
          "FIT_bit_errors":0,"FIT_rows":192,
          "directed_source_target_programs":6,
          "basis":"same 211 terms as both pooled nonlinear controls",
          "edge_ranks":ranks,"source_unknown":True,
          "all_24_public_FIT_episodes_consumed":True}

def score(model,ep):
    base.check_episode(ep)
    if model is None:raise ValueError("F124CZ_EDGE_NOT_FITTED")
    mem={k:list(v) for k,v in ep["initial"].items()}
    outputs=[]
    for row in ep["events"]:
        k=(row["target"],row["source"])
        y=base.infer(base.encode(mem,row),model["directed"][k])
        before=mem[row["target"]][0]
        mem[row["target"]]=[y,before]
        outputs.append(y)
    gold=[v["observed"] for v in ep["events"]]
    return {"correct":outputs==gold,
           "bit_errors":sum((a^b).bit_count() for a,b in zip(outputs,gold)),
           "native_event_calls":len(outputs)}
