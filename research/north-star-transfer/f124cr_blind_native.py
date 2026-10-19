"""F124-CR source-blind original public trajectory/native work evaluator.

Never imports F124-CR source generator or hidden oracle. Both trained arms
use one identical full public graph evaluation route with model-specific next
step, natural abstentions, no early exit. Source IDs 934/935 only.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROSTER=tuple(range(934000,934012))+tuple(range(935000,935012))
ARMS=("CANDIDATE","TRAINED_CONTROL","PERSISTENCE_REFERENCE")

def need(ok,reason):
    if not ok:raise ValueError("F124CR_EVAL_"+reason)

def sha(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,HERE/path)
    need(spec is not None and spec.loader is not None,"FROZEN_MODEL_NOT_PRESENT")
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod

def task_check(t,synthetic=False):
    need(type(t) is dict and set(t)==
         {"case_id","FIT","CHECK","positive","hard_negative"},
         "NO_PRIVATE_ORACLE_OR_SEED_IN_CHILD")
    need((t["case_id"]==-1 if synthetic else t["case_id"] in ROSTER),
         "NO_CONSUMED_GH_OR_OLD_EF_CASE_ID")
    fit,check=t["FIT"],t["CHECK"]
    need(type(fit) is list and len(fit)==40 and type(check) is list and len(check)==8,
         "PUBLIC_40_PLUS_8")
    rows=fit+check
    need(all(type(x) is list and len(x)==4 and
         all(type(z) is int and 0<=z<16 for z in x) for x in rows)
         and len({tuple(x[:3]) for x in rows})==48,
         "PUBLIC_TRANSITIONS_ONLY")
    for k in ("positive","hard_negative"):
        g=t[k]
        need(type(g) is dict and set(g)=={"initial","events"}
             and type(g["initial"]) is dict
             and set(g["initial"])=={"north","south"}
             and all(type(v) is list and len(v)==2 and
             all(type(x) is int and 0<=x<16 for x in v) for v in g["initial"].values()),
             "PUBLIC_ROLES_AND_INITIAL_STATE")
        events=g["events"]
        need(type(events) is list and len(events) in (8,10)
             and all(type(e) is dict and set(e)=={"role","event","observed"}
             and e["role"] in ("north","south")
             and type(e["event"]) is int and 0<=e["event"]<16
             and type(e["observed"]) is int and 0<=e["observed"]<16 for e in events),
             "PUBLIC_ROLE_EVENT_GRAPH_ONLY")
    pos,neg=t["positive"],t["hard_negative"]
    need(pos["initial"]==neg["initial"] and
         [(r["role"],r["event"]) for r in pos["events"]]==
         [(r["role"],r["event"]) for r in neg["events"]] and
         sorted(x["observed"] for x in pos["events"])==
         sorted(x["observed"] for x in neg["events"]) and
         [x["observed"] for x in pos["events"]]!=
         [x["observed"] for x in neg["events"]],
         "MATCHED_COUNTERFACTUAL_INVENTORY")
    return True

def native_full_graph_score(graph,step,constructor,model):
    # One and the same public/native scoring implementation for all arms.
    states={role:constructor(*v) for role,v in graph["initial"].items()}
    correct=True;calls=0
    for event in graph["events"]:
        prior=states[event["role"]]
        nxt=step(model,event["event"],prior)
        need(type(nxt.current) is int and 0<=nxt.current<16 and
             type(nxt.lagged) is int and 0<=nxt.lagged<16,"BOUND_NATIVE_OUTPUT")
        correct=bool(correct and nxt.current==event["observed"])
        states[event["role"]]=nxt
        calls+=1
    return correct,calls

def evaluate(task,arm,synthetic=False):
    task_check(task,synthetic)
    need(arm in ARMS,"REGISTERED_MODEL_ARM")
    if arm=="CANDIDATE":
        m=load("F124CR_FROZEN_TREE_CANDIDATE","f124cq_learned_relational_tree.py")
        model,fit=m.train(task["FIT"],task["CHECK"])
        step,constructor=m.predict,m.OnlineState
    elif arm=="TRAINED_CONTROL":
        m=load("F124CR_FROZEN_INDEPENDENT_CONTROL","f124cq_trained_tree_control.py")
        model,fit=m.fit(task["FIT"],task["CHECK"])
        step,constructor=m.next_state,m.State
    else:
        from collections import namedtuple
        constructor=namedtuple("FrozenPersistenceState",("current","lagged"))
        step=lambda _model,_event,state:constructor(state.current,state.current)
        model=object();fit={"frozen_untrained_safety_reference":True}
    admitted=model is not None
    decisions=[]
    calls=0
    if admitted:
        for name in ("positive","hard_negative"):
            yes,native_calls=native_full_graph_score(task[name],step,constructor,model)
            decisions.append(yes);calls+=native_calls
    else:
        decisions=[False,False]
    return {
      "schema":"mass.f124cr.original-source-blind-native-route.v1",
      "case_id":task["case_id"],"arm":arm,
      "synthetic_engineering_only":synthetic,
      "public_task_sha256":sha(task),
      "native_public_input_sha256":{k:sha(task[k]) for k in ("positive","hard_negative")},
      "natural_model_admission":admitted,
      "native_graph_calls":2 if admitted else 0,
      "native_event_transition_calls":calls,
      "expected_complete_transition_calls":sum(len(task[k]["events"])
                  for k in ("positive","hard_negative")),
      "positive_accepted":bool(decisions[0]),
      "hard_false_positive":bool(decisions[1]),
      "correct_paired_causal_task":bool(decisions[0] and not decisions[1]),
      "all_events_visited_no_early_exit":True,
      "trained_model_receipt":fit,
      "source_oracle_or_hidden_seed_imported":False,
      "prior_G_H_reused":False,"protected_opened":False,
      "science_accepted":False
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--public-case",required=True,type=Path)
    p.add_argument("--arm",required=True,choices=ARMS)
    p.add_argument("--synthetic-engineering",action="store_true")
    x=p.parse_args()
    print(json.dumps(evaluate(json.loads(x.public_case.read_text()),x.arm,
                    synthetic=x.synthetic_engineering),sort_keys=True))

if __name__=="__main__":main()
