"""O10 prospectively frozen encoding-versus-readout public development.

Native model is an EXACT source copy of O9 (no modification to internals),
trained and selected on new O10 roles. Decoder probes are fitted only to
publicly available, already-observed TRAIN labels with frozen model states.
DEV episodes never fit or select models or heads. Record negative results.
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
from public_source import (FAMILIES,ROLES,COUNTS,STEPS,public_episodes,
                           source_digest,query_info)
from o9_exact_trainable_memory import TrainedMemory
from probes import (PublicProbe,PublicEpisodicCounts,probe_examples,
                    evaluate_probe,nll)

PROTOCOL=HERE/"O10_FROZEN_PROTOCOL.json"
MODELS={"EXTERNAL2_O9":"LEARNED_EXTERNAL_WRITE_READ_2",
        "GRU2_O9":"GRU_2"}
PROBES=(("hidden","cue"),("current","cue"),
        ("hidden","parity"),("current","parity"),
        ("hidden","target"),("current","target"),
        ("quadratic_hidden","target"))


def verify_protocol():
    p=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert p["schema"]=="forge.optimizer.o10.encoding-vs-readout.public-dev.v1"
    assert p["status"]=="FROZEN_BEFORE_ANY_O10_DATA_OR_MODEL_SOURCE"
    assert p["predecessor_custody"]["O9_original_memory_blob"]==(
        "007f22006211439e625c1c317d32254acf902d74")
    assert tuple(p["public_source"]["roles"])==ROLES
    assert p["public_source"]["role_episodes"]==COUNTS
    assert p["public_source"]["transitions_per_episode"]==STEPS
    assert set(p["frozen_fit"]["models"])==set(MODELS)
    assert p["frozen_fit"]["seeds"]==[17,31]
    assert p["frozen_fit"]["probe_architecture"].startswith("Full-batch logistic")
    return p


def query_nll(model,eps,erased=False):
    return sum(nll(query_info(ep)["target"],
                   model.predict(ep,erased_query=erased)) for ep in eps)/len(eps)


def select_model(kind,train,select):
    options=[]
    for seed in (17,31):
        m=TrainedMemory(MODELS[kind],seed)
        m.fit(train)
        options.append((query_nll(m,select),seed,m))
    options.sort(key=lambda z:(z[0],z[1]))
    return options[0][2], {
        "selected_start":options[0][1],
        "public_select_nll":options[0][0],
        "public_select_by_seed":{str(s):v for v,s,_ in options},
    }


def rss_bytes():
    if os.name=="posix":
        import resource
        x=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(x if sys.platform=="darwin" else x*1024)
    if os.name=="nt":
        import ctypes
        from ctypes import wintypes
        class PM(ctypes.Structure):
            _fields_=[("cb",wintypes.DWORD),("PageFaultCount",wintypes.DWORD),
                      ("PeakWorkingSetSize",ctypes.c_size_t),
                      ("WorkingSetSize",ctypes.c_size_t),
                      ("QuotaPeakPagedPoolUsage",ctypes.c_size_t),
                      ("QuotaPagedPoolUsage",ctypes.c_size_t),
                      ("QuotaPeakNonPagedPoolUsage",ctypes.c_size_t),
                      ("PagefileUsage",ctypes.c_size_t),
                      ("PeakPagefileUsage",ctypes.c_size_t)]
        obj=PM()
        obj.cb=ctypes.sizeof(obj)
        try:
            ok=ctypes.windll.psapi.GetProcessMemoryInfo(
                ctypes.windll.kernel32.GetCurrentProcess(),
                ctypes.byref(obj),obj.cb)
            return int(obj.PeakWorkingSetSize) if ok else None
        except (AttributeError,OSError):
            return None
    return None


def run():
    verify_protocol()
    start=time.process_time()
    tracemalloc.start()
    results={}
    for family in FAMILIES:
        t=time.process_time()
        data={role:public_episodes(role,family) for role in ROLES}
        source_cpu=time.process_time()-t
        hashes={role:source_digest(eps) for role,eps in data.items()}
        if len(set(hashes.values()))!=len(ROLES):
            raise ValueError("O10_ROLE_COLLISION")
        train,select,dev=(data[role] for role in ROLES)
        records={}
        trained={}
        for name in MODELS:
            t=time.process_time()
            model,meta=select_model(name,train,select)
            fit_cpu=time.process_time()-t
            checkpoint=model.checkpoint()
            t=time.process_time()
            original=query_nll(model,dev)
            erased=query_nll(model,dev,erased=True)
            eval_cpu=time.process_time()-t
            if checkpoint!=model.checkpoint():
                raise ValueError("O10_DEV_MODEL_CHANGED")
            records[name]={
                "original_query_nll":original,
                "erased_query_nll":erased,
                "retention_nll_gain":erased-original,
                "training_selection_cpu_s":fit_cpu,
                "dev_model_inference_cpu_s":eval_cpu,
                "checkpoint_sha256":hashlib.sha256(checkpoint).hexdigest(),
                "checkpoint_bytes":len(checkpoint),
                "model_parameter_count":model.parameter_count(),
                **meta,
                "probe_results":{},
            }
            trained[name]=model
        # Each probe learns only from new TRAIN roles. All original recurrent
        # weights stay frozen and no DEV-based optimization is permitted.
        for name,model in trained.items():
            checkpoint=model.checkpoint()
            for feature,target in PROBES:
                label=f"{feature}_TO_{target}"
                t=time.process_time()
                fitted=PublicProbe(label)
                train_examples=probe_examples(train,model,feature,target)
                fitted.fit(train_examples)
                fit_cpu=time.process_time()-t
                receipt=fitted.checkpoint()
                t=time.process_time()
                dev_examples=probe_examples(dev,model,feature,target)
                loss=evaluate_probe(fitted,dev_examples)
                infer_cpu=time.process_time()-t
                if receipt!=fitted.checkpoint() or checkpoint!=model.checkpoint():
                    raise ValueError("O10_PROBE_DEV_ADAPTATION")
                records[name]["probe_results"][label]={
                    "dev_nll":loss,"probe_fit_cpu_s":fit_cpu,
                    "probe_dev_inference_cpu_s":infer_cpu,
                    "probe_bytes":len(receipt),
                    "probe_sha256":hashlib.sha256(receipt).hexdigest(),
                    "train_updates":fitted.updates,
                }
        # Strong conventional public-history witness; memory features are
        # engineered, not learned, and the comparison is not capacity-matched.
        t=time.process_time()
        table=PublicEpisodicCounts()
        table.fit(train)
        table_cpu=time.process_time()-t
        table_cp=table.checkpoint()
        table_loss=sum(nll(query_info(ep)["target"],table.predict(ep))
                       for ep in dev)/len(dev)
        if table_cp!=table.checkpoint():
            raise ValueError("O10_EPISODIC_DEV_ADAPTATION")
        t=time.process_time()
        engineered=PublicProbe("PUBLIC_ENGINEERED_LOGISTIC")
        train_ex=probe_examples(train,trained["GRU2_O9"],"engineered","target")
        engineered.fit(train_ex)
        engineered_cpu=time.process_time()-t
        engineered_cp=engineered.checkpoint()
        engineered_dev=evaluate_probe(
            engineered,probe_examples(dev,trained["GRU2_O9"],
                                      "engineered","target"))
        if engineered_cp!=engineered.checkpoint():
            raise ValueError("O10_PUBLIC_ENGINEERED_DEV_ADAPTATION")
        control={"episodic_count_query_nll":table_loss,
                 "episodic_count_fit_cpu_s":table_cpu,
                 "episodic_count_checkpoint_bytes":len(table_cp),
                 "episodic_count_sha256":hashlib.sha256(table_cp).hexdigest(),
                 "engineered_logistic_query_nll":engineered_dev,
                 "engineered_logistic_fit_cpu_s":engineered_cpu,
                 "engineered_logistic_checkpoint_bytes":len(engineered_cp),
                 "engineered_logistic_sha256":hashlib.sha256(engineered_cp).hexdigest(),
                 "uniform_query_nll":math.log(2)}
        def effect(model,feature,label):
            return records[model]["probe_results"][f"{feature}_TO_{label}"]["dev_nll"]
        results[family]={
            "source_role_sha256":hashes,
            "source_generation_cpu_s":source_cpu,
            "role_episode_counts":{r:len(data[r]) for r in ROLES},
            "models":records,
            "conventional_controls":control,
            "diagnostics":{
                name:{
                    "cue_state_vs_current_nll_gain":effect(name,"current","cue")-
                                                      effect(name,"hidden","cue"),
                    "parity_state_vs_current_nll_gain":effect(name,"current","parity")-
                                                         effect(name,"hidden","parity"),
                    "linear_readout_vs_original_query_nll_gain":(
                        records[name]["original_query_nll"]-
                        effect(name,"hidden","target")),
                    "quadratic_vs_original_query_nll_gain":(
                        records[name]["original_query_nll"]-
                        effect(name,"quadratic_hidden","target")),
                    "quadratic_vs_linear_query_nll_gain":(
                        effect(name,"hidden","target")-
                        effect(name,"quadratic_hidden","target")),
                } for name in MODELS
            },
        }
    _,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "schema":"forge.optimizer.o10.encoding-readout.public-development-receipt.v1",
        "scientific_authorization":"PUBLIC_ONLY_NO_PROTECTED_FIRST_USE",
        "qualified_scientific_positive":"NOT_EVALUATED",
        "wingless_yggdrasil_integration":"NONE",
        "fsa_science_admission":"NONE",
        "source_reuse_from_o9_dev":False,
        "full_process_cpu_seconds":time.process_time()-start,
        "peak_python_allocation_bytes":peak,
        "peak_process_rss_bytes":rss_bytes(),
        "platform":platform.platform(),
        "python":sys.version.split()[0],
        "families":results,
    }


if __name__=="__main__":
    print(json.dumps(run(),sort_keys=True,indent=2,allow_nan=False))
