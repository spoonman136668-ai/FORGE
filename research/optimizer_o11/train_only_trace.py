"""O11 training-only numerical forensics with BYTE-IDENTICAL O10 original learner.

Traces initial/early/final gradients, moments and parameters; data source is
O11_DIAG_TRAIN alone. No O10 roles, no SELECT, DEV, HELD or scientific first use.
"""
import json
import math
import pathlib
import platform
import sys
import time

ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from public_source import FAMILIES,ROLES,COUNT,STEPS,public_train,digest,query_info
from o10_immutable_phase import PublicPhaseComposer

FROZEN=ROOT/"O11_FROZEN_PROTOCOL.json"
MODELS=("TRAINED_PHASE_MEMORY","FROZEN_PHASE_TRAINED_HEAD","LINEAR_COUNT_MEMORY")
SEEDS=(17,31)
TRACE=(0,1,2,3,8,16,32,96,192,384,768,1536,3072,3840)
MATH_PROBE_INPUTS=(0.0,0.1,0.7,1.1,3.0,7.0,15.0,21.0,-3.0)


def guard():
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    assert p["schema"]=="forge.optimizer.o11.train-only-numeric-forensics.v1"
    assert p["frozen_stage"]=="BEFORE_ANY_PROBE_SOURCE_AND_EXECUTION"
    assert p["role_namespace"]=="o11-determinism-training-probe-v1"
    assert tuple(p["roles"])==ROLES
    assert p["episodes_per_family"]==COUNT and p["steps"]==STEPS
    assert tuple(p["families"])==FAMILIES
    assert p["training"]["trace_after_updates"]==list(TRACE)
    assert p["training"]["starts"]==list(SEEDS)
    assert p["training"]["epochs"]==40
    return p


def native_math_probes():
    out={}
    for x in MATH_PROBE_INPUTS:
        out[repr(x)]={
            "sin_hex":math.sin(x).hex(),
            "cos_hex":math.cos(x).hex(),
            "exp_hex":math.exp(x).hex(),
        }
    return out


def snapshot(model,episode):
    d=query_info(episode)
    loss,grad=model.loss_gradient(episode)
    phase=d["n0"]*model.w[0]+d["n1"]*model.w[1]
    return {
        "step":model.updates,
        "weight_hex":[x.hex() for x in model.w],
        "moment1_hex":[x.hex() for x in model.m],
        "moment2_hex":[x.hex() for x in model.v],
        "train_probe_loss_hex":loss.hex(),
        "train_probe_gradient_hex":[g.hex() for g in grad],
        "phase_hex":phase.hex(),
        "sin_phase_hex":math.sin(phase).hex(),
        "cos_phase_hex":math.cos(phase).hex(),
    }


def trace_run(family,variant,seed,episodes):
    if variant not in MODELS or seed not in SEEDS:
        raise ValueError("O11_UNFROZEN_MODEL")
    model=PublicPhaseComposer(variant,seed)
    fixed_probe=episodes[0]
    trace=[]
    trace.append(snapshot(model,fixed_probe))
    total_steps=len(episodes)*40
    wanted=set(TRACE[1:])
    for index in range(total_steps):
        model.step(episodes[index%len(episodes)])
        if model.updates in wanted:
            trace.append(snapshot(model,fixed_probe))
    if tuple(t["step"] for t in trace)!=TRACE:
        raise ValueError("O11_TRACE_STEP_COVERAGE_FAIL")
    return {
        "family":family,"variant":variant,"seed":seed,
        "sample_role":ROLES[0],
        "n_training_updates":model.updates,
        "last_checkpoint_sha256":__import__("hashlib").sha256(
            model.checkpoint()).hexdigest(),
        "trace":trace,
    }


def run():
    guard()
    start=time.process_time()
    source_hash={}
    traces=[]
    for family in FAMILIES:
        batch=public_train(family)
        source_hash[family]=digest(batch)
        if len(batch)!=COUNT or any(query_info(ep)["query_t"] not in (10,18)
                                    for ep in batch):
            raise ValueError("O11_SOURCE_ROLE_COVERAGE")
        for seed in SEEDS:
            for variant in MODELS:
                traces.append(trace_run(family,variant,seed,batch))
    if len(traces)!=24 or len(source_hash)!=4:
        raise ValueError("O11_COMPARISON_INCOMPLETE")
    return {
        "schema":"forge.optimizer.o11.native-train-only-trace.v1",
        "code_identity":"O10_PHASE_BLOB_56203c6aa60b29c4a5e8fb4bcd250bc212582209",
        "O10_TRAIN_SELECT_DEV_CONSUMED":0,
        "PROTECTED_FIRST_USE":False,
        "python":sys.version,
        "platform":platform.platform(),
        "math_library_probes":native_math_probes(),
        "o11_new_source_sha256":source_hash,
        "traces":traces,
        "cpu_process_s":time.process_time()-start,
    }


def main():
    if len(sys.argv)!=2:
        raise SystemExit("usage: train_only_trace.py path-to-output-json")
    result=run()
    path=pathlib.Path(sys.argv[1])
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,allow_nan=False,sort_keys=True,
                               separators=(",",":"))+"\n",encoding="utf-8")
    print("O11_FRESH_TRAIN_FAMILY_DIGESTS="+str(len(result["o11_new_source_sha256"])))
    print("O11_ORIGINAL_O10_FROZEN_TRAINED_MODELS="+str(len(result["traces"])))
    print("O11_TRACE_POINTS_PER_MODEL="+str(len(TRACE)))
    print("O11_O10_ROLE_EPISODES_CONSUMED=ZERO")
    print("O11_PROTECTED_FIRST_USE=ZERO")
    print("O11_TRAIN_ONLY_TRACE_RECEIPT="+str(path))
    print("O11_TRAIN_DIAGNOSTIC_CPU_S="+str(result["cpu_process_s"]))


if __name__=="__main__":
    main()
