"""L6 real-text hierarchical morphology vs fitted count and BPTT RNN controls.

All six models have EXACTLY the same public 900 labeled TRAIN instances.
RNN seeds chosen solely by 200 public SELECT target-char NLL. No L6 DEV
data is used for training, hyperparameters, model choice or backoff.
This is PUBLIC natural text prefix completion, NOT learned general cognition.
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

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from source import ROLES,COUNTS,GIT_BLOB,load,digest,canonical
from hierarchy import HierarchicalStemAffix
from l5_original_models import FittedPrefixLexicon,FittedSuffixReuse,FittedCharGram
from neural import SEEDS,TrainedCharRNN

ARMS=("CLOSED_PREFIX","FLAT_SUFFIX","CHAR_TRIGRAM_BEAM",
      "HIERARCHICAL_STEM_AFFIX","HIERARCHICAL_NO_AFFIX_ABLATION",
      "RNN_CHAR_H20")


def prereg():
    p=json.loads((ROOT/"L6_FROZEN_PROTOCOL.json").read_text(encoding="utf-8"))
    assert p["schema"]=="forge.optimizer.language.l6.hierarchical-public-realtext.v1"
    assert p["stage"]=="PREREG_PROTOCOL_ONLY_FIRST_COMMIT_BEFORE_SOURCE_MODEL_OR_DEV"
    assert p["source"]["git_blob_sha1"]==GIT_BLOB
    assert p["source"]["roles"]==COUNTS
    assert tuple(p["arms"])==ARMS
    assert p["governance"]["mode"]=="ADDITIVE_BOUNDED_PUBLIC_LANGUAGE_EXPLORATION_ONLY"
    return p


def edit(a,b):
    prev=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        cur=[i]
        for j,y in enumerate(b,1):
            cur.append(min(cur[-1]+1,prev[j]+1,prev[j-1]+int(x!=y)))
        prev=cur
    return prev[-1]


def eval_one(model,rows,train_vocabulary):
    exact=unseen_n=unseen_hit=0
    new_outputs=abstain=prefix_bad=0
    edits=characters_correct=all_chars=ops=0
    outputs=hashlib.sha256()
    cpu0=time.process_time()
    wall0=time.perf_counter()
    for row in rows:
        # Include no gold or source ordinal in learner inputs.
        inp={k:row[k] for k in ("prefix","left","right")}
        out,work=model.predict(inp)
        if not isinstance(out,str) or not isinstance(work,int) or work<0:
            raise ValueError("L6_MODEL_OUTPUT_CONTRACT_BROKEN")
        truth=row["gold"]
        exact+=int(out==truth)
        if truth not in train_vocabulary:
            unseen_n+=1
            unseen_hit+=int(out==truth)
        new_outputs+=int(out not in train_vocabulary)
        abstain+=int(out==row["prefix"])
        prefix_bad+=int(not out.startswith(row["prefix"]))
        edits+=edit(out,truth)/max(len(out),len(truth))
        characters_correct+=sum(a==b for a,b in zip(out,truth))
        all_chars+=len(truth)
        ops+=work
        outputs.update(out.encode("ascii")+b"\n")
    cpu=time.process_time()-cpu0
    wall=time.perf_counter()-wall0
    count=len(rows)
    return {
        "examples":count,
        "full_word_exact":exact/count,
        "unseen_gold_count":unseen_n,
        "unseen_gold_hits":unseen_hit,
        "unseen_gold_exact":unseen_hit/unseen_n if unseen_n else None,
        "normalized_edit_distance":edits/count,
        "position_character_accuracy":characters_correct/all_chars,
        "novel_predicted_form_fraction":new_outputs/count,
        "prefix_violation":prefix_bad/count,
        "prefix_only_abstention":abstain/count,
        "predicted_words_sha256":outputs.hexdigest(),
        "analytical_lookup_or_MAC_proxy_NOT_FLOPs":ops,
        "serial_inference_cpu_seconds":cpu,
        "serial_wall_us_per_word":wall/count*1e6,
    }


def fit_all(train,selection):
    models={}
    resources={}
    constructors={
        "CLOSED_PREFIX":lambda:FittedPrefixLexicon().fit(train),
        "FLAT_SUFFIX":lambda:FittedSuffixReuse().fit(train),
        "CHAR_TRIGRAM_BEAM":lambda:FittedCharGram(3).fit(train),
        "HIERARCHICAL_STEM_AFFIX":lambda:HierarchicalStemAffix(True).fit(train),
        "HIERARCHICAL_NO_AFFIX_ABLATION":lambda:HierarchicalStemAffix(False).fit(train),
    }
    for arm,maker in constructors.items():
        t=time.process_time()
        model=maker()
        duration=time.process_time()-t
        models[arm]=model
        resources[arm]={
            "all_fit_select_cpu_seconds":duration,
            "training_examples":len(train),
            "select_examples_not_used_for_fit":len(selection),
            "parameter_count":None,
            "actual_parallel_hardware":False,
            "feature_category":"learned_count_hierarchy_or_ngrams",
        }
    t=time.process_time()
    from neural import TrainedCharRNN
    candidates=[]
    for seed in SEEDS:
        model=TrainedCharRNN(seed).fit(train)
        valid=model.select_nll(selection)
        candidates.append((valid,seed,model))
    candidates.sort(key=lambda x:(x[0],x[1]))
    nll,chosen,selected=candidates[0]
    models["RNN_CHAR_H20"]=selected
    resources["RNN_CHAR_H20"]={
        "all_fit_select_cpu_seconds":time.process_time()-t,
        "training_examples":len(train),
        "select_examples":len(selection),
        "seeds":[int(s) for _,s,_ in candidates],
        "SELECT_char_NLL_by_seed":{str(seed):value for value,seed,_ in candidates},
        "selected_seed":chosen,
        "selected_seed_SELECT_char_NLL":nll,
        "optimizer_updates_selected":selected.updates,
        "parameter_count":selected.params_count(),
        "actual_parallel_hardware":False,
        "feature_category":"trained_character_recurrent_neural",
    }
    for arm,model in models.items():
        cp=model.checkpoint()
        resources[arm]["checkpoint_bytes_including_optimizer_if_any"]=len(cp)
        resources[arm]["checkpoint_sha256"]=hashlib.sha256(cp).hexdigest()
        resources[arm]["conceptual_serial_steps"]=(
            18 if arm=="RNN_CHAR_H20" else
            18 if arm=="CHAR_TRIGRAM_BEAM" else 2 if arm.startswith("HIERARCHICAL") else 1
        )
    return models,resources


def rss_bytes():
    if os.name=="posix":
        import resource
        z=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(z if sys.platform=="darwin" else z*1024)
    if os.name=="nt":
        import ctypes
        from ctypes import wintypes
        class MEM(ctypes.Structure):
            _fields_=[("cb",wintypes.DWORD),("PageFaultCount",wintypes.DWORD),
                ("PeakWorkingSetSize",ctypes.c_size_t),
                ("WorkingSetSize",ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage",ctypes.c_size_t),
                ("QuotaPagedPoolUsage",ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage",ctypes.c_size_t),
                ("PagefileUsage",ctypes.c_size_t),
                ("PeakPagefileUsage",ctypes.c_size_t)]
        m=MEM();m.cb=ctypes.sizeof(m)
        if ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(),ctypes.byref(m),m.cb):
            return int(m.PeakWorkingSetSize)
    return None


def run(raw_file):
    prereg()
    import numpy as np
    if np.__version__!="2.1.3":
        raise ValueError("L6_UNPINNED_TRAINING_NUMPY_VERSION")
    tracemalloc.start()
    clock=time.process_time()
    loadtime=time.process_time()
    sha,cohorts=load(raw_file)
    source_cpu=time.process_time()-loadtime
    source_hash={k:digest(v) for k,v in cohorts.items()}
    identified=[]
    for role in ROLES:
        rows=cohorts[role]
        if len(rows)!=COUNTS[role]:
            raise ValueError("L6_SOURCE_CARDINALITY_DRIFT")
        fingerprints={canonical((r["left"],r["gold"],r["right"])) for r in rows}
        if len(fingerprints)!=COUNTS[role]:
            raise ValueError("L6_DUPLICATE_WORD_CONTEXT_EXPOSURE")
        for prior in identified:
            if prior&fingerprints:
                raise ValueError("L6_CROSS_ROLE_WORD_WINDOW_LEAKAGE")
        identified.append(fingerprints)
    train,select=cohorts["L6_TRAIN"],cohorts["L6_SELECT"]
    train_vocab={r["gold"] for r in train}
    trained,resources=fit_all(train,select)
    frozen={a:r["checkpoint_sha256"] for a,r in resources.items()}
    result={}
    for role in ROLES:
        result[role]={}
        for name in ARMS:
            result[role][name]=eval_one(trained[name],cohorts[role],train_vocab)
            current=hashlib.sha256(trained[name].checkpoint()).hexdigest()
            if current!=frozen[name]:
                raise ValueError("L6_SOURCE_OR_FITTED_CHECKPOINT_MUTATED_ON_DEV")
    _,py_peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "schema":"forge.optimizer.language.l6.public-hierarchy-rnn-receipt.v1",
        "source_git_blob_sha1":GIT_BLOB,
        "source_raw_sha256":sha,
        "source_roles_sha256":source_hash,
        "role_count":COUNTS,
        "old_L1_L5_dev_consumed":0,
        "Q21_FSA_HELD_scientific_first_use":False,
        "all_active_research_unchanged":True,
        "no_scientific_promotion":True,
        "external_blinded_science":False,
        "fully_computation_matched_controls":False,
        "human_natural_language_comprehension":"NOT_EVALUATED",
        "coding_reasoning_math_multilingual":"NOT_EVALUATED",
        "energy_joules":"NOT_MEASURED",
        "measured_flops":"NOT_MEASURED",
        "actual_hardware_parallel_generation":False,
        "numpy_version":np.__version__,
        "training_example_public_bytes":len(canonical(train)),
        "select_example_public_bytes":len(canonical(select)),
        "train_distinct_word_count":len(train_vocab),
        "source_gen_cpu_seconds":source_cpu,
        "model_resources":resources,
        "evaluations":result,
        "experiment_total_CPU_seconds":time.process_time()-clock,
        "peak_process_rss_bytes":rss_bytes(),
        "peak_python_tracemalloc_bytes":py_peak,
        "platform":platform.platform(),
    }


if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: runner.py /verified/external/source.txt")
    print(json.dumps(run(sys.argv[1]),sort_keys=True,indent=2,allow_nan=False))
