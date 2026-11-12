"""L2 original-code independent, PUBLIC synthetic phrase-dependence evaluation.

All fit/selection uses L2_TRAIN / L2_SELECT only. DEV_COMPOSE and the
corrupted NULL are encountered only AFTER all models, feature subsets and
repair thresholds are frozen. No Q21/FSA/protected scientific first-use.
This evaluates six aligned synthetic language controls, NOT real coding,
reasoning, multilingual language or actual parallel processor throughput.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import time
import tracemalloc

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from public_source import (ROLES,COUNTS,FIELD_SIZES,SLOTS,
                           dataset,digest,canonical,source_tokens)
from learners import (PublicChunkLearner,FittedTupleLookup,
                      FittedSelectiveRepair)

PROTO=HERE/"L2_FROZEN_PROTOCOL.json"
ARMS=("PARALLEL_3","PARALLEL_4","SEQUENTIAL_3",
      "SELECTIVE_REPAIR","UNCONDITIONAL_CONTROL","FULL_TUPLE_LOOKUP")


def guard():
    p=json.loads(PROTO.read_text(encoding="utf-8"))
    assert p["schema"]=="forge.optimizer.language.l2.frozen-dependency-stress-v1"
    assert p["stage"]=="PROTOCOL_ONLY_COMMIT_PRECEDES_GENERATOR_MODELS_AND_DEV_FIRST_USE"
    assert p["namespace"]=="l2-20261023-conditional-phrase-dependence-v1"
    assert tuple(p["roles"])==ROLES and p["role_counts"]==COUNTS
    assert tuple(p["models"])==ARMS
    assert p["training"]["smoothing"]==.5
    assert p["training"]["repair_thresholds"]==[.05,.15,.30]
    assert p["governance"]["mode"]=="ADDITIVE_DEVELOPMENT_ONLY"
    return p


def peak_rss_bytes():
    if os.name=="posix":
        import resource
        x=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(x if sys.platform=="darwin" else x*1024)
    if os.name=="nt":
        import ctypes
        from ctypes import wintypes
        class MEM(ctypes.Structure):
            _fields_=[
                ("cb",wintypes.DWORD),("PageFaultCount",wintypes.DWORD),
                ("PeakWorkingSetSize",ctypes.c_size_t),
                ("WorkingSetSize",ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage",ctypes.c_size_t),
                ("QuotaPagedPoolUsage",ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage",ctypes.c_size_t),
                ("PagefileUsage",ctypes.c_size_t),
                ("PeakPagefileUsage",ctypes.c_size_t),
            ]
        buf=MEM()
        buf.cb=ctypes.sizeof(buf)
        if ctypes.windll.psapi.GetProcessMemoryInfo(
                ctypes.windll.kernel32.GetCurrentProcess(),
                ctypes.byref(buf),buf.cb):
            return int(buf.PeakWorkingSetSize)
    return None


def evaluate(model,batch,role):
    exact=0
    slots_correct=0
    subject_correct=0
    verb_correct=0
    compliant=0
    corrupted_target_matches=0
    operations=0
    repairs=0
    cpu0=time.process_time()
    wall0=time.perf_counter()
    for row in batch:
        value=model.generate(row["meaning"])
        if len(value)==3:
            generated,ops,repaired=value
            repairs+=repaired
        else:
            generated,ops=value
        generated=tuple(generated)
        if len(generated)!=8:
            raise ValueError("L2_INVALID_GENERATED_CHUNK_LENGTH")
        target=tuple(row["slots"])
        # The SOURCE truth for corruption is withheld from predictors.
        honest=source_tokens(tuple(row["meaning"]))
        oracle=(honest if role=="L2_NULL_CORRUPTION" else target)
        if generated==oracle:
            exact+=1
        slots_correct+=sum(x==y for x,y in zip(generated,oracle))
        subject_correct+=(generated[1]==oracle[1])
        verb_correct+=(generated[2]==oracle[2])
        compliant+=(generated[0]=="the" and generated[3]=="the"
                    and generated[6]=="." and generated[7]=="<eos>")
        if role=="L2_NULL_CORRUPTION":
            corrupted_target_matches+=(generated==target)
        operations+=ops
    wall=time.perf_counter()-wall0
    cpu=time.process_time()-cpu0
    return {
        "records":len(batch),
        "meaning_fidelity_exact":exact/len(batch),
        "mean_correct_chunk_fraction":slots_correct/(8*len(batch)),
        "subject_code_accuracy":subject_correct/len(batch),
        "dependent_verb_accuracy":verb_correct/len(batch),
        "synthetic_surface_grammar_accuracy":compliant/len(batch),
        "corrupted_gold_exact_false_positive_rate":(
            corrupted_target_matches/len(batch)
            if role=="L2_NULL_CORRUPTION" else None),
        "trained_verifier_repairs_applied":repairs,
        "categorical_lookup_scoring_operations_NOT_FLOPS":operations,
        "serial_python_inference_process_cpu_s":cpu,
        "serial_python_wall_us_per_utterance":wall/len(batch)*1e6,
    }


def run():
    guard()
    tracemalloc.start()
    start=time.process_time()
    source_t=time.process_time()
    data={role:dataset(role) for role in ROLES}
    source_cpu=time.process_time()-source_t
    hashes={role:digest(role) for role in ROLES}
    sets={role:{tuple(row["meaning"]) for row in batch}
          for role,batch in data.items()}
    for i,role in enumerate(ROLES):
        if len(sets[role])!=COUNTS[role]:
            raise ValueError("L2_SOURCE_DUPLICATE_TUPLE")
        for previous in ROLES[:i]:
            if sets[previous]&sets[role]:
                raise ValueError("L2_TRAIN_SELECT_DEV_TUPLE_LEAKAGE")
    train=data["L2_TRAIN"]
    select=data["L2_SELECT"]
    models={}
    resources={}
    specs=(
        ("PARALLEL_3",3,False),
        ("PARALLEL_4",4,False),
        ("SEQUENTIAL_3",3,True),
        ("UNCONDITIONAL_CONTROL",0,False),
    )
    for name,max_features,ar in specs:
        t=time.process_time()
        model=PublicChunkLearner(max_features,ar).fit(train,select)
        elapsed=time.process_time()-t
        models[name]=model
        resources[name]={
            "fit_and_SELECT_cpu_s":elapsed,
            "shared_train_records":len(train),
            "shared_SELECT_records":len(select),
            "learned_table_contexts":model.context_entries(),
            "frozen_selected_field_subsets":[list(x) for x in model.subsets],
            "conceptual_serial_dependency_stages":8 if ar else 1,
            "execution_is_actually_parallel":False,
        }
    t=time.process_time()
    models["SELECTIVE_REPAIR"]=FittedSelectiveRepair(
        models["PARALLEL_3"],models["SEQUENTIAL_3"]).select(select)
    repair_cost=time.process_time()-t
    resources["SELECTIVE_REPAIR"]={
        "fit_and_SELECT_cpu_s":(
            resources["PARALLEL_3"]["fit_and_SELECT_cpu_s"]+
            resources["SEQUENTIAL_3"]["fit_and_SELECT_cpu_s"]+repair_cost),
        "shared_train_records":len(train),
        "shared_SELECT_records":len(select),
        "repair_SELECT_cpu_s":repair_cost,
        "frozen_threshold":models["SELECTIVE_REPAIR"].threshold,
        "conceptual_serial_dependency_stages":9,
        "execution_is_actually_parallel":False,
        "inherits_both_fitted_checkpoints":True,
    }
    t=time.process_time()
    models["FULL_TUPLE_LOOKUP"]=FittedTupleLookup(
        train,models["UNCONDITIONAL_CONTROL"])
    lookup_cost=time.process_time()-t
    resources["FULL_TUPLE_LOOKUP"]={
        "fit_and_SELECT_cpu_s":(
            resources["UNCONDITIONAL_CONTROL"]["fit_and_SELECT_cpu_s"]+
            lookup_cost),
        "shared_train_records":len(train),
        "shared_SELECT_records":len(select),
        "exact_fitted_tuples":len(models["FULL_TUPLE_LOOKUP"].table),
        "conceptual_serial_dependency_stages":1,
        "execution_is_actually_parallel":False,
    }
    for name,model in models.items():
        checkpoint=model.checkpoint()
        resources[name].update({
            "checkpoint_bytes":len(checkpoint),
            "checkpoint_sha256":hashlib.sha256(checkpoint).hexdigest(),
        })
    frozen_checks={name:res["checkpoint_sha256"]
                   for name,res in resources.items()}
    evaluations={}
    for role,batch in data.items():
        evaluations[role]={}
        for arm in ARMS:
            evaluations[role][arm]=evaluate(models[arm],batch,role)
            new_sha=hashlib.sha256(models[arm].checkpoint()).hexdigest()
            if new_sha!=frozen_checks[arm]:
                raise ValueError("L2_TRAINED_CHECKPOINT_MODIFIED_ON_EVAL")
    _,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "schema":"forge.optimizer.language.l2.public-dependence-receipt.v1",
        "previous_l1_l2_protected_dev_reuse":0,
        "Q21_FSA_protected_scientific_first_use":False,
        "existing_research_priority_unchanged":True,
        "externally_independent_natural_language":False,
        "reasoning_coding_math_multilingual_evaluated":False,
        "language_model_replacement_claim":False,
        "trained_state_space_recurrent_transformer_controls":"NOT_YET",
        "energy_joules":"NOT_MEASURED",
        "measured_flops":"NOT_MEASURED",
        "actual_parallel_hardware_inference":False,
        "source_role_sha256":hashes,
        "source_role_sizes":COUNTS,
        "train_corpus_bytes":len(canonical(train)),
        "select_corpus_bytes":len(canonical(select)),
        "source_generation_cpu_s":source_cpu,
        "resources":resources,
        "evaluations":evaluations,
        "total_process_cpu_s":time.process_time()-start,
        "peak_tracemalloc_bytes":peak,
        "peak_process_rss_bytes":peak_rss_bytes(),
        "platform":platform.platform(),"python":sys.version.split()[0],
    }


if __name__=="__main__":
    print(json.dumps(run(),sort_keys=True,indent=2,allow_nan=False))
