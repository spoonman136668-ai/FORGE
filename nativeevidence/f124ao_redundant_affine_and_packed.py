"""F124-AO robust redundant affine learner and sequential single-state packed consensus.

Inference only sees opaque roles and independent 40 demonstration pairs.
No access to source relation/label/oracle/DEV. Strong inductive bias:
16x16 affine GF2; nonlinear Feistel intentionally remains out-of-class.
"""
from __future__ import annotations
import random,types
import f124am_example_affine_learner as prior
import f124ag_transition_models as ygg_original
import f124ak_one_packed_contrast as packed_original
import f124q_fresh_source as q

TRIALS=(64,256,1024)
MARGINS=(1,3)
CHECKSUMS=((1,3,4,2),(2,4,1,3),(4,2,3,1),(3,4,2,1))
def need(x,label):q.need(x,"F124AO_LEARN_"+label)
def integer(a):return sum(x<<i for i,x in enumerate(a))

def public(graph):
    need(type(graph) is dict and
         set(graph)=={"start","target","roles","edges","demos"},
         "NO_HIDDEN_SOURCE_FIELDS")
    roles=graph["roles"]
    need(type(roles) is list and 7<=len(roles)<=15
         and all(type(x) is str and x.startswith("rel_task_")
                 for x in roles),
         "PUBLIC_OPAQUE_ROLES")
    tag=roles[0].split(":",1)[0]+":"
    need(all(role.startswith(tag) for role in roles)
         and all(e["role"].startswith(tag) for e in graph["edges"]),
         "ONE_OPAQUE_TASK_NO_SEMANTIC_NAMES")
    demos=graph["demos"]
    need(type(demos) is list and len(demos)==40
         and all(type(d) is dict and
                 set(d)=={"input_bits","output_bits"} and
                 all(type(d[k]) is list and len(d[k])==16 and
                     all(type(v) is int and v in (0,1) for v in d[k])
                     for k in ("input_bits","output_bits"))
                 for d in demos),
         "FORTY_PUBLIC_INPUT_OUTPUT_DEMONSTRATIONS")
    result={"start":graph["start"],"target":graph["target"],
            "roles":[r[len(tag):] for r in roles],
            "edges":[dict(e,role=e["role"][len(tag):],
                          src_bits=list(e["src_bits"]),
                          dst_bits=list(e["dst_bits"]))
                     for e in graph["edges"]]}
    return result,demos,tag

def learn(demos,task,trials,margin):
    need(len(demos)==40 and trials in TRIALS and margin in MARGINS,
         "PREDECLARED_FIT_GRID")
    randomizer=random.Random("F124AO/new_ransac/"+task)
    discovered={}
    for attempt in range(trials):
        ids=tuple(sorted(randomizer.sample(range(40),17)))
        coeff=prior.solve_17([demos[i] for i in ids])
        if coeff is None or coeff in discovered:continue
        if prior.inverse_output(0,coeff) is None:continue
        residual=sum(prior.popcount(
            prior.forward(integer(row["input_bits"]),coeff)^
            integer(row["output_bits"])) for row in demos)
        discovered[coeff]=residual
    ranked=sorted((cost,coef) for coef,cost in discovered.items())
    best=ranked[0][0] if ranked else None
    nearest=[p for cost,p in ranked if cost==best] if ranked else []
    nextcost=next((cost for cost,p in ranked if cost>best),None)
    gap=(nextcost-best) if nextcost is not None else None
    accepted=(best is not None and best<=3 and
              len(nearest)==1 and (gap is None or gap>=margin))
    return nearest[0] if accepted else None,{
        "trials":trials,"margin":margin,"support":40,
        "candidate_count":len(discovered),
        "lowest_public_bit_mismatches":best,
        "same_best_models":len(nearest),
        "runner_up_gap":gap,
        "accepted":accepted,"abstained":not accepted,
        "operator_label_seen":False,
        "hypothesis_class":"affine_GF2_only"}

def normalize(graph,trials,margin):
    g,demos,tag=public(graph)
    coeff,diag=learn(demos,tag,trials,margin)
    if coeff is None:return None,{"learner":diag,"edge_bit_ops":0,
                                  "added_retained_states":0}
    ops=0
    for e in g["edges"]:
        key=prior.inverse_output(integer(e["src_bits"]),coeff)
        if key is None:return None,{"learner":dict(diag,abstained=True,
                                                 accepted=False),
                                   "edge_bit_ops":ops,
                                   "added_retained_states":0}
        e["src_bits"]=[(key>>i)&1 for i in range(16)]
        ops+=256
    ygg_original.frozen.prior.parent.validate_15(g)
    return g,{"learner":diag,"edge_bit_ops":ops,
              "added_retained_states":0}

def ygg(graph,base,delta,trials,margin):
    normalized,meta=normalize(graph,trials,margin)
    if normalized is None:return -1.e9,None,meta
    score,raw,prob,work=ygg_original.ygg_transition(normalized,base,delta,.1)
    need(work["max_active"]<=7 and work["max_retained"]<=9,
         "ORIGINAL_YGG_SEVEN_NINE")
    return score,work,meta

def sequential_wing(graph,base,delta,checksum):
    """Run ONE original 12-bit packed model at a time, never co-retain states."""
    need(checksum in CHECKSUMS,"FROZEN_SECOND_INDEPENDENT_PROJECTION")
    original,wa=packed_original.wing_competitive(
        graph,list(base),list(delta),.5)
    if checksum==CHECKSUMS[0]:
        return original,wa
    env=dict(packed_original.wing_competitive.__globals__,
             CHECKSUM=tuple(checksum))
    forward=types.FunctionType(
        packed_original.wing_competitive.__code__,env,
        packed_original.wing_competitive.__name__,
        packed_original.wing_competitive.__defaults__)
    alternative,wb=forward(graph,list(base),list(delta),.5)
    need(wa["max_states_per_node"]==1 and
         wb["max_states_per_node"]==1 and
         wa["max_packed_bits_per_state"]==12 and
         wb["max_packed_bits_per_state"]==12 and
         wa["max_active"]<=64 and wb["max_active"]<=64,
         "NEVER_MORE_THAN_ONE_STATE_PER_NODE_PER_PASS")
    report=dict(wa)
    report["max_active"]=max(wa["max_active"],wb["max_active"])
    report["edge_inspections"]+=wb["edge_inspections"]
    report["raw_bit_reads"]+=wb["raw_bit_reads"]
    report["affinity_ops"]+=wb["affinity_ops"]
    report["max_packed_bits_per_state"]=12
    report["max_states_per_node"]=1
    report["sequential_full_passes"]=2
    report["projection_original_score"]=original
    report["projection_alternate_score"]=alternative
    report["sequential_alternative_checksum"]=list(checksum)
    return min(original,alternative),report

def choose_y(cases,base,delta):
    need(len(cases)==48,"TRAIN_ONLY")
    options=[]
    for trial in TRIALS:
        for margin in MARGINS:
            paired=fp=0
            for seed,v,fam,op,tag,p,n in cases:
                a,_,_=ygg(p,base,delta,trial,margin)
                b,_,_=ygg(n,base,delta,trial,margin)
                paired+=int(a>=0 and b<0);fp+=int(b>=0)
            options.append({"trials":trial,"margin":margin,
                            "paired":paired,"FP":fp})
    return sorted(options,key=lambda r:(-r["paired"],r["FP"],
                                        r["trials"],-r["margin"]))[0],options

def choose_w(cases,base,delta):
    need(len(cases)==48,"WING_ONLY_TRAIN_48")
    source=[];original_long=set()
    for seed,v,fam,op,tag,p,n in cases:
        # Source normalizer is evaluation-only; never passed to Yggdrasil.
        source.append((seed,tuple(v),fam,p,n))
    results=[]
    for checksum in CHECKSUMS:
        paired=fp=0
        positives=set()
        for seed,v,fam,p,n in source:
            a=sequential_wing(p,base,delta,checksum)[0]>=0
            b=sequential_wing(n,base,delta,checksum)[0]>=0
            paired+=int(a and not b);fp+=int(b)
            if fam in ("rotate4_dense_13_15","xor16_extended_13_15") and a:
                positives.add((seed,v,fam))
        if checksum==CHECKSUMS[0]:original_long=positives
        results.append({"checksum":list(checksum),
                        "paired":paired,"FP":fp,
                        "long_positive":len(positives),
                        "all_original_long_preserved":original_long.issubset(positives)})
    candidates=[r for r in results if r["all_original_long_preserved"]]
    need(candidates and
         any(tuple(r["checksum"])==CHECKSUMS[0] for r in candidates),
         "SOURCE_BLIND_SINGLE_STATE_BASELINE_REQUIRED")
    chosen=sorted(candidates,key=lambda x:(x["FP"],-x["paired"],
                                            0 if tuple(x["checksum"])==CHECKSUMS[0] else 1))[0]
    return chosen,results
