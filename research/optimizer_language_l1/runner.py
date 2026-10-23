"""L1 public-aligned language realization development receipts; no FSA first use.

Real trained 8-head factor parallel, teacher-forced conditional left-to-right,
and serial conditional repair all use identical TRAIN and SELECT sources.
No cognitive meaning is learned: the meaning record and sentence slot
boundaries are publicly supplied. Novel means a previously unseen *pair*
of familiar values; coding/reasoning/unaligned language are not evaluated.
"""
import hashlib
import json
import math
from pathlib import Path
import platform
import sys
import time
import tracemalloc

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from public_language import (ROLES,COUNTS,SLOTS,dataset,role_hash,
                             surface_slots,render,canonical)
from learners import (PublicCategoricalHeads,MemorizedFullMeaning,
                      SelectiveChunkRepair)

PROTOCOL=ROOT/"L1_FROZEN_PROTOCOL.json"
ARMS=("PARALLEL_FACTOR","AUTOREGRESSIVE_CHUNK",
      "PARALLEL_SELECTIVE_REPAIR","PARALLEL_UNCONDITIONAL",
      "FULL_MEANING_LOOKUP","SOURCE_KNOWN_TEMPLATE_DIAGNOSTIC")


def guard():
    p=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert p["schema"]=="forge.optimizer.language.l1.parallel-slot-realization-public.v1"
    assert p["status"]=="FROZEN_FIRST_BEFORE_ANY_L1_SOURCE_OR_LEARNER"
    assert p["role_namespace"]=="ol1-20261023-language-synthetic-v1"
    assert p["roles"]==COUNTS
    assert tuple(p["models"])==ARMS
    assert p["training"]["feature_subsets_max_size"]==3
    assert p["training"]["repair_thresholds"]==[.05,.15,.30]
    return p


def edit_distance(a,b):
    if a==b:
        return 0
    prior=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        curr=[i]
        for j,y in enumerate(b,1):
            curr.append(min(curr[-1]+1,prior[j]+1,
                            prior[j-1]+(0 if x==y else 1)))
        prior=curr
    return prior[-1]


def evaluate(arm,model,rows):
    hits=0
    n_correct_slots=0
    clause_semantic=0
    core_semantic=0
    edit=0.
    punctuation=0
    operations=0
    changes=0
    start_cpu=time.process_time()
    start_wall=time.perf_counter_ns()
    for row in rows:
        if arm=="SOURCE_KNOWN_TEMPLATE_DIAGNOSTIC":
            chunks=surface_slots(tuple(row["meaning"]))
            ops=0
        elif arm=="PARALLEL_SELECTIVE_REPAIR":
            chunks,ops,edits=model.generate(row["meaning"])
            changes+=edits
        else:
            chunks,ops=model.generate(row["meaning"])
        if len(chunks)!=8:
            raise ValueError("L1_UNREGISTERED_OUTPUT_SLOT_LENGTH")
        target=tuple(row["slots"])
        sentence=render(chunks)
        gold=render(target)
        operations+=ops
        hits+=int(sentence==gold)
        n_correct_slots+=sum(a==b for a,b in zip(chunks,target))
        core_semantic+=int(
            chunks[0]==target[0] and chunks[3]==target[3]
            and chunks[5]==target[5]
        )
        clause_semantic+=int(all(chunks[i]==target[i]
                                  for i in (0,1,2,3,5,6)))
        punctuation+=int(chunks[7]==".")
        edit+=edit_distance(sentence,gold)/max(1,len(gold))
    cpu=time.process_time()-start_cpu
    wall=time.perf_counter_ns()-start_wall
    n=len(rows)
    return {
        "exact_utterance_accuracy":hits/n,
        "mean_slot_accuracy":n_correct_slots/(n*8),
        "core_actor_verb_object_accuracy":core_semantic/n,
        "clause_semantic_slot_fidelity":clause_semantic/n,
        "normalized_character_edit_distance":edit/n,
        "punctuation_accuracy":punctuation/n,
        "inference_process_cpu_seconds":cpu,
        "measured_sequential_python_wall_microseconds_per_utterance":wall/n/1000,
        "categorical_lookup_and_candidate_scoring_operation_proxy":operations,
        "total_verified_repairs":changes,
        "n_examples":n,
    }


def run():
    guard()
    tracemalloc.start()
    start=time.process_time()
    source_start=time.process_time()
    data={role:dataset(role) for role in ROLES}
    hashes={role:role_hash(role) for role in ROLES}
    if len(set(hashes.values()))!=4:
        raise ValueError("L1_SOURCE_ROLE_IDENTITY_COLLISION")
    train,select=data["L1_TRAIN"],data["L1_SELECT"]
    familiar,novel=data["L1_INDOMAIN_DEV"],data["L1_NOVEL_COMPOSITION_DEV"]
    fitkeys={tuple(r["meaning"]) for r in train+select+familiar}
    novelkeys={tuple(r["meaning"]) for r in novel}
    if fitkeys & novelkeys or any(
        x[0]!="eli" or x[2]!="door" for x in novelkeys
    ):
        raise ValueError("L1_COMPOSITION_LEAK")
    if len(fitkeys)!=len(train)+len(select)+len(familiar):
        raise ValueError("L1_ROLE_DUPLICATE_MEANING")
    source_cpu=time.process_time()-source_start

    fitted={}
    fitcost={}
    for name,ar,uncond in (
        ("PARALLEL_FACTOR",False,False),
        ("AUTOREGRESSIVE_CHUNK",True,False),
        ("PARALLEL_UNCONDITIONAL",False,True),
    ):
        t=time.process_time()
        model=PublicCategoricalHeads(ar,uncond).fit(train,select)
        fitcost[name]=time.process_time()-t
        fitted[name]=model
    t=time.process_time()
    repair=SelectiveChunkRepair(
        fitted["PARALLEL_FACTOR"],fitted["AUTOREGRESSIVE_CHUNK"]
    ).select(select)
    repair_search_cpu=time.process_time()-t
    fitted["PARALLEL_SELECTIVE_REPAIR"]=repair
    lookup=MemorizedFullMeaning(train,fitted["PARALLEL_UNCONDITIONAL"])
    fitted["FULL_MEANING_LOOKUP"]=lookup

    model_evidence={}
    for name in ARMS:
        if name=="SOURCE_KNOWN_TEMPLATE_DIAGNOSTIC":
            cp=b""
        else:
            cp=fitted[name].checkpoint()
        model_evidence[name]={
            "checkpoint_bytes":len(cp),
            "checkpoint_sha256":hashlib.sha256(cp).hexdigest(),
            "training_and_selection_cpu_seconds":(
                fitcost["PARALLEL_FACTOR"]+fitcost["AUTOREGRESSIVE_CHUNK"]+
                repair_search_cpu if name=="PARALLEL_SELECTIVE_REPAIR"
                else fitcost.get(name,0)
            ),
            "learned_conditional_count_contexts":(
                fitted[name].entries() if name in (
                    "PARALLEL_FACTOR","AUTOREGRESSIVE_CHUNK",
                    "PARALLEL_UNCONDITIONAL") else None
            ),
            "training_utterances_consumed":(
                0 if name=="SOURCE_KNOWN_TEMPLATE_DIAGNOSTIC" else len(train)
            ),
            "select_utterances_available":(
                0 if name in ("SOURCE_KNOWN_TEMPLATE_DIAGNOSTIC",
                              "FULL_MEANING_LOOKUP")
                else len(select)
            ),
            "sequential_dependency_stages":(
                0 if name=="SOURCE_KNOWN_TEMPLATE_DIAGNOSTIC"
                else 1 if name in ("PARALLEL_FACTOR","PARALLEL_UNCONDITIONAL",
                                   "FULL_MEANING_LOOKUP")
                else 9 if name=="PARALLEL_SELECTIVE_REPAIR" else 8
            ),
        }
    model_evidence["PARALLEL_SELECTIVE_REPAIR"]["selected_threshold"]=repair.threshold
    # Checkpoints locked BEFORE touching either DEV role.
    before={name:hashlib.sha256(fitted[name].checkpoint()).hexdigest()
            for name in fitted}
    outputs={}
    for role,rows in (
        ("L1_INDOMAIN_DEV",familiar),
        ("L1_NOVEL_COMPOSITION_DEV",novel),
    ):
        outputs[role]={}
        for name in ARMS:
            outputs[role][name]=evaluate(name,fitted.get(name),rows)
    for name in fitted:
        if hashlib.sha256(fitted[name].checkpoint()).hexdigest()!=before[name]:
            raise ValueError("L1_DEV_MUTATED_TRAINED_MODEL")
    _,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "schema":"forge.optimizer.language.l1.public-parallel-realization-receipt.v1",
        "scientific_first_use":False,
        "externally_independent_language_source":False,
        "protected_Q21_FSA_cohorts_consumed":0,
        "native_Wingless_Yggdrasil_candidate":None,
        "reasoning_evaluation":"NOT_TESTED",
        "coding_evaluation":"NOT_TESTED",
        "unaligned_natural_language_evaluation":"NOT_TESTED",
        "matched_trained_recurrent_state_space_foundation_model":"NOT_YET_IN_L1",
        "energy_joules":"NOT_MEASURED",
        "exact_floating_point_flops":"NOT_MEASURED_COUNT_LOOKUPS_ARE_NOT_FLOPS",
        "source_role_sha256":hashes,
        "source_role_sizes":{r:len(data[r]) for r in ROLES},
        "all_public_train_meaning_pair_count":len(train),
        "train_corpus_serialized_bytes":len(canonical(train)),
        "select_corpus_serialized_bytes":len(canonical(select)),
        "source_generation_cpu_seconds":source_cpu,
        "fitted_model_evidence":model_evidence,
        "evaluations":outputs,
        "whole_process_cpu_seconds":time.process_time()-start,
        "peak_tracemalloc_bytes":peak,
        "platform":platform.platform(),
        "python":sys.version.split()[0],
    }


if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True,allow_nan=False))
