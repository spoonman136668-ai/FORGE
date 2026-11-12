"""O10 prospective, source-only encoding versus readout fault isolation.

Public training and selection occur before DEV exposure. Recurrent weights
are frozen before auxiliary readout fitting and never modified in DEV.
Diagnostic labels cue and reset parity are calculated from PUBLIC history,
not simulator hidden state and never passed into the recurrent network.
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
from public_source import (
    FAMILIES,ROLES,COUNTS,STEPS,all_public,digest,query_info,
)
from frozen_o9_memory import TrainedMemory
from diagnostic_probes import (
    RECURRENT_KIND,selected_model,FrozenStateProbe,PublicHistoryCounts,
    query_score,nll,
)

ARMS=("EXTERNAL2_NATIVE","EXTERNAL2_ERASED","EXTERNAL2_FROZEN_TARGET",
      "EXTERNAL2_RANDOM_TARGET","EXTERNAL2_FROZEN_CUE",
      "EXTERNAL2_RANDOM_CUE","EXTERNAL2_FROZEN_PARITY",
      "EXTERNAL2_RANDOM_PARITY",
      "GRU2_NATIVE","GRU2_ERASED","GRU2_FROZEN_TARGET",
      "GRU2_RANDOM_TARGET","GRU2_FROZEN_CUE","GRU2_RANDOM_CUE",
      "GRU2_FROZEN_PARITY","GRU2_RANDOM_PARITY",
      "CURRENT_QUERY_COUNTS","EXPLICIT_PUBLIC_MEMORY_COUNTS","UNIFORM_05")
PROTOCOL=HERE/"O10_FROZEN_PROTOCOL.json"


def check_protocol():
    p=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert p["schema"]=="forge.optimizer.o10.state-versus-readout.public-development.v1"
    assert p["frozen_status"]=="FROZEN_BEFORE_SOURCE_MODEL_AND_TEST_IMPLEMENTATION"
    assert tuple(p["roles"])==ROLES and p["episodes_per_family"]==COUNTS
    assert p["episode_length"]==STEPS
    assert tuple(p["frozen_fit"]["selected_starts"])==(17,31)
    assert p["frozen_fit"]["original_training_epochs"]==12
    assert p["frozen_fit"]["linear_probe_epochs"]==120
    assert p["frozen_fit"]["linear_probe_learning_rate"]==0.2
    assert p["frozen_fit"]["linear_probe_l2"]==0.002
    assert len(ARMS)==19
    return p


def rss_bytes():
    if os.name=="posix":
        import resource
        value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(value if sys.platform=="darwin" else value*1024)
    if os.name=="nt":
        import ctypes
        from ctypes import wintypes
        class PM(ctypes.Structure):
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
        c=PM()
        c.cb=ctypes.sizeof(c)
        try:
            ok=ctypes.windll.psapi.GetProcessMemoryInfo(
                ctypes.windll.kernel32.GetCurrentProcess(),
                ctypes.byref(c),c.cb)
            return int(c.PeakWorkingSetSize) if ok else None
        except (OSError,AttributeError):
            return None
    return None


def receipt(nllvalue,fit_cpu,infer_cpu,checkpoint,params=None,**meta):
    if not math.isfinite(nllvalue):
        raise ValueError("O10_INVALID_NLL")
    return {"public_dev_nll":nllvalue,
            "fit_and_select_cpu_seconds":fit_cpu,
            "dev_eval_cpu_seconds":infer_cpu,
            "checkpoint_bytes":len(checkpoint),
            "checkpoint_sha256":hashlib.sha256(checkpoint).hexdigest(),
            "parameters":params,**meta}


def run():
    check_protocol()
    started=time.process_time()
    tracemalloc.start()
    families={}
    for family in FAMILIES:
        t=time.process_time()
        batches={role:all_public(role,family) for role in ROLES}
        hashes={role:digest(batch) for role,batch in batches.items()}
        if len(set(hashes.values()))!=3:
            raise ValueError("O10_ROLE_IDENTITIES_NOT_DISJOINT")
        source_cpu=time.process_time()-t
        train,select,dev=(batches[r] for r in ROLES)
        results={}
        for architecture,prefix in (
            ("LEARNED_EXTERNAL_WRITE_READ_2","EXTERNAL2"),
            ("GRU_2","GRU2"),
        ):
            t=time.process_time()
            trained,meta=selected_model(architecture,train,select)
            fit_cpu=time.process_time()-t
            original=trained.checkpoint()
            t=time.process_time()
            native=query_score(trained,dev)
            native_cpu=time.process_time()-t
            assert original==trained.checkpoint(),"O10_NATIVE_MODEL_DEV_MUTATION"
            results[prefix+"_NATIVE"]=receipt(
                native,fit_cpu,native_cpu,original,
                params=trained.parameter_count(),
                trained_recurrent_cells=trained.dim,
                recurrent_updates=trained.updates,**meta)
            t=time.process_time()
            erased=query_score(trained,dev,erased=True)
            erased_cpu=time.process_time()-t
            results[prefix+"_ERASED"]=receipt(
                erased,0.0,erased_cpu,original,
                params=trained.parameter_count(),
                checkpoint_shared_with=prefix+"_NATIVE",
                memory_cells_at_query=0)
            randomized=TrainedMemory(architecture,meta["selected_start"])
            random_before=randomized.checkpoint()
            for task in ("target","cue","parity"):
                for state,name in ((trained,"FROZEN"),
                                   (randomized,"RANDOM")):
                    t=time.process_time()
                    probe=FrozenStateProbe(task)
                    probe.fit(state,train)
                    fitting=time.process_time()-t
                    cp=probe.checkpoint()
                    t=time.process_time()
                    loss=probe.score(state,dev)
                    cpu=time.process_time()-t
                    assert cp==probe.checkpoint()
                    assert trained.checkpoint()==original
                    assert randomized.checkpoint()==random_before
                    results[f"{prefix}_{name}_{task.upper()}"]=receipt(
                        loss,fitting,cpu,cp,params=len(probe.w),
                        trained_state=(name=="FROZEN"),
                        separate_supervision=task,
                        recurrent_model_checkpoint_sha256=hashlib.sha256(
                            state.checkpoint()).hexdigest(),
                        recurrent_state_cells=state.dim)
        for kind,label in (
            ("CURRENT","CURRENT_QUERY_COUNTS"),
            ("EXPLICIT_RESET_PARITY","EXPLICIT_PUBLIC_MEMORY_COUNTS"),
        ):
            t=time.process_time()
            counts=PublicHistoryCounts(kind)
            counts.fit(train)
            fit_cpu=time.process_time()-t
            cp=counts.checkpoint()
            t=time.process_time()
            val=counts.score(dev)
            cpu=time.process_time()-t
            assert counts.checkpoint()==cp
            results[label]=receipt(val,fit_cpu,cpu,cp,
                                    public_history_hand_engineered=(
                                        kind=="EXPLICIT_RESET_PARITY"))
        results["UNIFORM_05"]=receipt(nll(0,0.5),0.0,0.0,b"")
        if set(results)!=set(ARMS):
            raise ValueError("O10_PROSPECTIVE_ARM_INVENTORY_DRIFT")
        families[family]={
            "roles_sha256":hashes,
            "role_episode_counts":{role:len(batch) for role,batch in batches.items()},
            "source_cpu_seconds":source_cpu,
            "external2_state_erasure_nll_gain":(
                results["EXTERNAL2_ERASED"]["public_dev_nll"]
                -results["EXTERNAL2_NATIVE"]["public_dev_nll"]),
            "external2_trained_state_target_probe_gain_vs_original_head":(
                results["EXTERNAL2_NATIVE"]["public_dev_nll"]
                -results["EXTERNAL2_FROZEN_TARGET"]["public_dev_nll"]),
            "external2_trained_vs_untrained_target_probe_gain":(
                results["EXTERNAL2_RANDOM_TARGET"]["public_dev_nll"]
                -results["EXTERNAL2_FROZEN_TARGET"]["public_dev_nll"]),
            "gru2_trained_vs_untrained_target_probe_gain":(
                results["GRU2_RANDOM_TARGET"]["public_dev_nll"]
                -results["GRU2_FROZEN_TARGET"]["public_dev_nll"]),
            "arms":results,
        }
    _,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "schema":"forge.optimizer.o10.public-encoding-readout-receipt.v1",
        "status":"PUBLIC_DEV_ONLY_NOT_FIRST_USE",
        "scientific_fsa_admission":"NONE",
        "protected_role_consumption":0,
        "native_integration":"NONE",
        "candidate_promotion":"NONE",
        "extra_public_supervision_used_only_for_probes":True,
        "full_process_cpu_seconds":time.process_time()-started,
        "peak_python_allocation_bytes":peak,
        "peak_rss_bytes":rss_bytes(),
        "operating_system":platform.platform(),
        "python":sys.version.split()[0],
        "families":families,
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True,allow_nan=False))
