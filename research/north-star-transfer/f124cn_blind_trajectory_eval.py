"""F124-CN blinded online multi-role trajectory evaluator (not a source birth).

The evaluator imports ONLY the frozen candidate and independent trained
control, never the source generator, private family, hidden key or oracle.
Natural abstentions are retained; a missing model never gets fake native work.
Native input identities represent the same observed public trajectories; model
predictions may and should differ. Equal work is not a scientific success.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ARMS=("CANDIDATE","TRAINED_CONTROL","PERSISTENCE_REFERENCE")
REAL_ROSTER=set(range(932000,932012)) | set(range(933000,933012))

def need(ok,msg):
    if not ok:raise ValueError("F124CN_EVAL_"+msg)

def canonical(v):
    return json.dumps(v,sort_keys=True,separators=(",",":")).encode()

def sha(v):
    return hashlib.sha256(canonical(v)).hexdigest()

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,HERE/path)
    need(spec is not None and spec.loader is not None,"FROZEN_MODEL_SOURCE_MISSING")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def validate_task(task,synthetic=False):
    need(type(task) is dict and set(task)==
         {"case_id","FIT","CHECK","positive","hard_negative"},
         "ONLY_PUBLIC_INFORMATION")
    need((task["case_id"]==-1 if synthetic else task["case_id"] in REAL_ROSTER),
         "NEW_SOURCE_IDENTITIES_ONLY")
    fit,check=task["FIT"],task["CHECK"]
    need(type(fit) is list and len(fit)==40 and
         type(check) is list and len(check)==8,"FROZEN_INFORMATION")
    pairs=fit+check
    need(all(type(row) in (tuple,list) and len(row)==4 and
             all(type(v) is int and 0<=v<16 for v in row) for row in pairs),
         "PUBLIC_TRANSITIONS_ONLY")
    need(len({tuple(row[:3]) for row in pairs})==48,"DISTINCT_PUBLIC_OBSERVATIONS")
    for label in ("positive","hard_negative"):
        g=task[label]
        need(type(g) is dict and set(g)=={"initial","events"},
             "ONLY_PUBLIC_GRAPH")
        need(type(g["initial"]) is dict and set(g["initial"])=={"A","B"}
             and all(type(v) is list and len(v)==2
                     and all(type(x) is int and 0<=x<16 for x in v)
                     for v in g["initial"].values()),"PUBLIC_TWO_ENTITY_STATES")
        events=g["events"]
        need(type(events) is list and len(events) in (8,10),"BOUNDED_CHAIN")
        need(all(type(e) is dict and set(e)=={"role","event","observed"}
                 and e["role"] in ("A","B")
                 and all(type(e[k]) is int and 0<=e[k]<16 for k in ("event","observed"))
                 for e in events),"OPAQUE_ROLE_BOUND_EVENTS")
        need([e["role"] for e in events]==["A","B"]*(len(events)//2),
             "TWO_ENTITY_ROLE_SEQUENCE")
    p,n=task["positive"],task["hard_negative"]
    need(p["initial"]==n["initial"] and len(p["events"])==len(n["events"])
         and [(e["role"],e["event"]) for e in p["events"]]==
             [(e["role"],e["event"]) for e in n["events"]],
         "MATCHED_TOPOLOGY_INTERVENTIONS")
    need(sorted(e["observed"] for e in p["events"])==
         sorted(e["observed"] for e in n["events"])
         and [e["observed"] for e in p["events"]]!=
             [e["observed"] for e in n["events"]],
         "MATCHED_DISTINCT_TOKEN_INVENTORY")
    return True

def score_public_graph(graph,step,model,state_type):
    """One single source-neutral scorer shared by both learned arms."""
    states={k:state_type(*v) for k,v in graph["initial"].items()}
    all_matched=True
    calls=0
    for row in graph["events"]:
        role=row["role"]
        nxt=step(model,row["event"],states[role])
        need(type(nxt.current) is int and 0<=nxt.current<16
             and type(nxt.lagged) is int and 0<=nxt.lagged<16,
             "FINITE_BOUNDED_ROLLOUT")
        all_matched=bool(all_matched and nxt.current==row["observed"])
        states[role]=nxt
        calls+=1
    return all_matched,calls

def evaluate(task,arm,synthetic=False):
    validate_task(task,synthetic)
    need(arm in ARMS,"REGISTERED_ARM_ONLY")
    if arm=="CANDIDATE":
        mod=load("f124cm_learned_online_state.py","CM_frozen_candidate")
        model,training=mod.fit(task["FIT"],task["CHECK"])
        step,state_type=mod.predict,mod.OnlineState
    elif arm=="TRAINED_CONTROL":
        mod=load("f124cm_trained_relational_control.py","CM_independent_control")
        model,training=mod.train(task["FIT"],task["CHECK"])
        step,state_type=mod.step,mod.State
    else:
        from collections import namedtuple
        state_type=namedtuple("PersistenceState",("current","lagged"))
        step=lambda unused,event,state:state_type(state.current,state.current)
        model=object()
        training={"trained":False,"frozen_reference_only":True}
    admitted=model is not None
    outcomes=[]
    native_calls=0
    if admitted:
        for label in ("positive","hard_negative"):
            decision,calls=score_public_graph(task[label],step,model,state_type)
            outcomes.append(decision);native_calls+=calls
    else:
        outcomes=[False,False]
    graph_hashes={label:sha(task[label]) for label in ("positive","hard_negative")}
    return {
       "schema":"mass.f124cn.public-source-blind-original-scorer.v1",
       "arm":arm,"case_id":task["case_id"],"synthetic_engineering_only":synthetic,
       "public_task_sha256":sha(task),"graph_sha256":graph_hashes,
       "natural_admission":admitted,
       "native_graph_score_calls":2 if admitted else 0,
       "native_event_transition_calls":native_calls,
       "expected_event_transition_calls_if_admitted":sum(
           len(task[x]["events"]) for x in ("positive","hard_negative")),
       "positive_accepted":bool(outcomes[0]),
       "hard_false_positive":bool(outcomes[1]),
       "correct_pair":bool(outcomes[0] and not outcomes[1]),
       "full_path_scored_no_early_exit":True,
       "training":training,
       "private_oracle_or_source_imported":False,
       "science_accepted":False,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--public-file",required=True,type=Path)
    p.add_argument("--arm",required=True,choices=ARMS)
    p.add_argument("--synthetic-engineering",action="store_true")
    args=p.parse_args()
    task=json.loads(args.public_file.read_text())
    print(json.dumps(evaluate(task,args.arm,synthetic=args.synthetic_engineering),sort_keys=True))

if __name__=="__main__":main()
