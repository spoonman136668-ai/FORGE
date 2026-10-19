"""F124-CU source-blind full BPTT and natural native trajectory evaluator.

Only public 24 FIT and 8 CHECK sequential episodes and original two
eight-event public graphs may enter. No hidden seed/oracle/source import.
Natural trained abstention is not replaced by fake comparable native work.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ARMS=("CANDIDATE","TRAINED_CONTROL","PERSISTENCE_REFERENCE")
CASES=tuple(range(936000,936012))+tuple(range(937000,937012))
ROLES=("alpha","beta","gamma")

def need(ok,reason):
    if not ok:raise ValueError("F124CU_EVAL_"+reason)

def sha(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,HERE/path)
    need(spec is not None and spec.loader is not None,"FROZEN_MODEL_NOT_FOUND")
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def validate(task,synthetic=False):
    need(type(task) is dict and set(task)==
         {"case_id","FIT","CHECK","positive","hard_negative"},
         "SOURCE_PRIVATE_SEED_OR_ORACLE_DENIED")
    need((task["case_id"]==-1 if synthetic else task["case_id"] in CASES),
         "NO_CONSUMED_SCIENTIFIC_SOURCE")
    p=module("f124ct_sequence_protocol.py","F124CU_public_protocol")
    p.validate(task["FIT"],24);p.validate(task["CHECK"],8)
    for part in ("positive","hard_negative"):
        p.validate([task[part]]*24,24)
    a,b=task["positive"],task["hard_negative"]
    need(a["initial"]==b["initial"]
         and [(e["target"],e["source"],e["event"]) for e in a["events"]]==
             [(e["target"],e["source"],e["event"]) for e in b["events"]]
         and sorted(x["observed"] for x in a["events"])==
             sorted(x["observed"] for x in b["events"])
         and [x["observed"] for x in a["events"]]!=
             [x["observed"] for x in b["events"]],
         "MATCHED_COUNTERFACTUAL_PUBLIC_TRAJECTORIES")
    return True

def persistence(ep):
    states={k:list(v) for k,v in ep["initial"].items()}
    outputs=[]
    for row in ep["events"]:
        observed=states[row["target"]][0]
        outputs.append(observed)
        previous=states[row["target"]][0]
        states[row["target"]]=[observed,previous]
    return outputs

def evaluate(task,arm,synthetic=False):
    validate(task,synthetic)
    need(arm in ARMS,"UNKNOWN_FROZEN_COMPARATOR")
    if arm=="CANDIDATE":
        m=module("f124ct_attentive_causal_memory.py","F124CU_frozen_associative")
        fitted,trained=m.train(task["FIT"],task["CHECK"])
    elif arm=="TRAINED_CONTROL":
        m=module("f124ct_gated_sequence_control.py","F124CU_frozen_gated")
        fitted,trained=m.train(task["FIT"],task["CHECK"])
    else:
        m=None;fitted=object()
        trained={"frozen_untrained_reference":True,"same_public_graphs":True}
    admitted=fitted is not None
    accepts=[];native_calls=0
    if admitted:
        for label in ("positive","hard_negative"):
            graph=task[label]
            predicted=persistence(graph) if m is None else m.predict_sequence(fitted,graph)
            need(len(predicted)==8 and all(type(x) is int and 0<=x<16 for x in predicted),
                 "ACTUAL_NATIVE_EIGHT_TRANSITIONS")
            accepts.append(all(y==e["observed"] for y,e in
                               zip(predicted,graph["events"])))
            native_calls+=len(predicted)
    else:accepts=[False,False]
    return {
      "schema":"mass.f124cu.source-blind-original-BPTT-native.v1",
      "case_id":task["case_id"],"arm":arm,
      "synthetic_engineering_only":synthetic,
      "public_case_sha256":sha(task),
      "identical_native_public_graph_hashes":{k:sha(task[k]) for k in
                       ("positive","hard_negative")},
      "identical_train_FIT_sha256":sha(task["FIT"]),
      "identical_veto_CHECK_sha256":sha(task["CHECK"]),
      "natural_trained_admission":admitted,
      "native_complete_graph_calls":2 if admitted else 0,
      "native_event_count":native_calls,"expected_event_count_if_admitted":16,
      "positive_accepted":bool(accepts[0]),
      "hard_false_positive":bool(accepts[1]),
      "correct_positive_and_hard_negative":bool(accepts[0] and not accepts[1]),
      "all_eight_events_evaluated_without_early_exit":True,
      "full_training_and_CHECK_receipt":trained,
      "private_oracle_or_seed_imported":False,
      "previous_924_935_original_sources_used":False,
      "science_accepted":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--public-case",required=True,type=Path)
    p.add_argument("--arm",required=True,choices=ARMS)
    p.add_argument("--synthetic-engineering",action="store_true")
    x=p.parse_args()
    task=json.loads(x.public_case.read_text())
    print(json.dumps(evaluate(task,x.arm,synthetic=x.synthetic_engineering),
                     sort_keys=True))

if __name__=="__main__":main()
