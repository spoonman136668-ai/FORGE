"""F124-DB FIT-trained reusable causal-program library and constructor.

Learn primitive expression motifs from TWELVE independent source-free
meta-tasks (public whole causal trajectories). Freeze motifs; only then
construct new nested operator trees and fit each novel FIT episode.
No heldout structural template/source law imported; no source generator
import; no CHECK/HELDOUT tuning, no original first-use consumption.
"""
from __future__ import annotations
import hashlib
import json

ROLES=("alpha","beta","gamma")
OPERATORS=("xor","add","and")
NAMES=("own_current","own_lagged","source_current","source_lagged","event")

def need(ok,why):
    if not ok:raise ValueError("F124DB_PROGRAM_"+why)

def validate(ep):
    need(type(ep) is dict and set(ep)=={"initial","events"} and
         set(ep["initial"])==set(ROLES) and len(ep["events"])==8,
         "FULL_PUBLIC_SEQUENCE")
    need(all(type(x) is list and len(x)==2 and
         all(type(v) is int and 0<=v<16 for v in x)
         for x in ep["initial"].values()),"ALL_ENTITY_REGISTER_INITIALS")
    need(all(type(e) is dict and set(e)=={"target","source","event","observed"} and
         e["target"] in ROLES and e["source"] in ROLES and e["target"]!=e["source"] and
         all(type(e[k]) is int and 0<=e[k]<16 for k in ("event","observed"))
         for e in ep["events"]),"ALL_PUBLIC_INTERVENTIONS")

def rows(episodes,expected):
    need(type(episodes) is list and len(episodes)==expected,
         "FROZEN_COMPLETE_FIT_EPISODES")
    result=[]
    for ep in episodes:
        validate(ep)
        state={r:list(vals) for r,vals in ep["initial"].items()}
        for e in ep["events"]:
            own=state[e["target"]];src=state[e["source"]]
            result.append(((own[0],own[1],src[0],src[1],e["event"]),e["observed"]))
            previous=own[0]
            state[e["target"]]=[e["observed"],previous]  # FIT supervision only
    return result

def apply(op,left,right):
    if op=="xor":return left^right
    if op=="add":return (left+right)&15
    if op=="and":return left&right
    raise ValueError("UNKNOWN_PRIMITIVE")

def motif(m,raw):
    op,i,j=m
    return apply(op,raw[i],raw[j])

def construct(program,raw):
    top,left,right=program
    return apply(top,motif(left,raw),motif(right,raw))

def learn_library(training_tasks):
    need(type(training_tasks) is list and len(training_tasks)==12,
         "TWELVE_ORIGINAL_META_SUPERVISION_TASKS")
    motifs=[]
    receipts=[]
    for task in training_tasks:
        samples=rows(task,24)
        found=None
        for op in OPERATORS:
            if found is not None:break
            for a in range(5):
                if found is not None:break
                for b in range(5):
                    if a==b:continue
                    candidate=(op,a,b)
                    if all(motif(candidate,x)==y for x,y in samples):
                        found=candidate;break
        need(found is not None,"META_TASK_OUTSIDE_PUBLIC_PRIMITIVES")
        if found not in motifs:motifs.append(found)
        receipts.append({"rows":len(samples),"learned_motif":list(found)})
    need(2<=len(motifs)<=12,"NO_REUSABLE_LEARNED_LIBRARY")
    return {"learned_library":motifs},{
      "meta_tasks_trained":12,"FIT_episodes_per_meta_task":24,
      "meta_supervised_event_rows":2304,
      "unique_learned_macro_count":len(motifs),
      "all_metatrain_labels_fit":True,
      "learned_motifs_from_public_targets_only":True,
      "operator_library_influences_constructed_programs":True,
      "meta_receipts":receipts}

def fit_novel(meta_model,fit):
    samples=rows(fit,24)
    discovered=meta_model["learned_library"]
    attempted=0
    for op in OPERATORS:
        for left in discovered:
            for right in discovered:
                attempted+=1
                proposal=(op,left,right)
                if all(construct(proposal,x)==target for x,target in samples):
                    return {"program":proposal,"learned_library_sha256":digest(discovered)},{
                      "natural_FIT":True,"FIT_rows":192,"FIT_bit_errors":0,
                      "learned_meta_motifs_used_in_program":2,
                      "constructor_candidate_attempts":attempted,
                      "full_library_pair_search_budget":len(discovered)**2*len(OPERATORS),
                      "source_law_not_provided":True}
    return None,{"natural_FIT":False,"FIT_rows":192,
                  "constructor_candidate_attempts":attempted,
                  "full_library_pair_search_budget":len(discovered)**2*len(OPERATORS)}

def rollout(model,episode):
    validate(episode)
    need(model is not None and set(model)=={"program","learned_library_sha256"},
         "FIT_LEARNED_COMPOSITION_REQUIRED")
    state={r:list(s) for r,s in episode["initial"].items()}
    output=[]
    for e in episode["events"]:
        own=state[e["target"]];src=state[e["source"]]
        raw=(own[0],own[1],src[0],src[1],e["event"])
        y=construct(model["program"],raw)
        output.append(y)
        state[e["target"]]=[y,own[0]]  # never teacher force CHECK/HELDOUT
    return output

def score(model,ep):
    y=rollout(model,ep);true=[x["observed"] for x in ep["events"]]
    return {"exact":y==true,"bit_errors":sum((x^z).bit_count() for x,z in zip(y,true)),
            "native_events":8}

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()
