"""O12 original native O10 vs deterministic Decimal arithmetic; fresh TRAIN-only.

No SELECT/DEV, O10/O11 old role imports, scientific heldout or native
candidate promotion. TRAIN_DIAGNOSTIC is a fixed report-only probe and
does not influence fitting or restart selection.
"""
import hashlib
import json
import math
from pathlib import Path
import platform
import sys
import time
from decimal import Decimal as D, localcontext

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from public_source import FAMILIES,ROLES,COUNTS,STEPS,role_batch,query_info,digest
from o10_frozen_phase import PublicPhaseComposer
from decimal_phase import (DecimalPhase,VARIANTS as DEC_VARIANTS,
                           CTX,SEEDS,nll as decimal_nll,fixed_sin_cos)

PROTOCOL=ROOT/"O12_FROZEN_PROTOCOL.json"
ARMS=("NATIVE_O10_FLOAT",)+DEC_VARIANTS
TRACE=(0,1,2,3,16,96,192,384,768,1536,1920)


def guard():
    p=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert p["schema"]=="forge.optimizer.o12.deterministic-phase-trainonly-v1"
    assert p["stage"]=="PREREGISTERED_BEFORE_ANY_SOURCE_OR_MODEL_IMPLEMENTATION"
    assert p["original_o10_model_blob"]=="56203c6aa60b29c4a5e8fb4bcd250bc212582209"
    assert tuple(p["roles"])==ROLES and tuple(p["families"])==FAMILIES
    assert p["role_counts"]==COUNTS and p["episode_steps"]==STEPS
    assert tuple(p["models"])==ARMS
    assert p["frozen_training"]["epochs"]==40
    assert p["frozen_training"]["updates_per_run"]==1920
    assert tuple(p["frozen_training"]["trace_after_updates"])==TRACE
    assert p["frozen_training"]["seeds"]==list(SEEDS)
    return p


def model_for(arm,seed):
    if arm=="NATIVE_O10_FLOAT":
        return PublicPhaseComposer("TRAINED_PHASE_MEMORY",seed)
    if arm in DEC_VARIANTS:
        return DecimalPhase(arm,seed)
    raise ValueError("O12_UNREGISTERED_ARM")


def query_loss(model,batch,decimal):
    if decimal:
        with localcontext(CTX):
            return +(sum((decimal_nll(query_info(ep)["target"],
                                       model.predict(ep)) for ep in batch),
                         D(0))/D(len(batch)))
    return sum(-math.log(
        model.predict(ep) if query_info(ep)["target"] else
        1-model.predict(ep)) for ep in batch)/len(batch)


def snapshot(model,arm,diagnostic,fixed_train):
    is_decimal=arm in DEC_VARIANTS
    val=query_loss(model,diagnostic,is_decimal)
    _,gradient=model.loss_gradient(fixed_train)
    details=query_info(fixed_train)
    if is_decimal:
        with localcontext(CTX):
            phase=D(details["n0"])*model.w[0]+D(details["n1"])*model.w[1]
            sine,cosine=fixed_sin_cos(phase)
            encode=str
    else:
        phase=details["n0"]*model.w[0]+details["n1"]*model.w[1]
        sine,cosine=math.sin(phase),math.cos(phase)
        encode=float.hex
    return {
        "step":model.updates,
        "w":[encode(x) for x in model.w],
        "adam_m":[encode(x) for x in model.m],
        "adam_v":[encode(x) for x in model.v],
        "train_gradient":[encode(x) for x in gradient],
        "train_diagnostic_query_loss":encode(val),
        "phase":encode(phase),
        "phase_sin":encode(sine),
        "phase_cos":encode(cosine),
    }


def run():
    guard()
    source_hashes={}
    models=[]
    start=time.process_time()
    for family in FAMILIES:
        roles={role:role_batch(role,family) for role in ROLES}
        for role,episodes in roles.items():
            source_hashes[f"{family}:{role}"]=digest(episodes)
        train=roles["O12_TRAIN"]
        diagnostic=roles["O12_TRAIN_DIAGNOSTIC"]
        assert len(train)==48 and len(diagnostic)==8
        for seed in SEEDS:
            for arm in ARMS:
                model=model_for(arm,seed)
                trace=[snapshot(model,arm,diagnostic,train[0])]
                begin=time.process_time()
                for ix in range(40*len(train)):
                    model.step(train[ix%len(train)])
                    if model.updates in TRACE[1:]:
                        trace.append(snapshot(model,arm,diagnostic,train[0]))
                fit_cpu=time.process_time()-begin
                if tuple(p["step"] for p in trace)!=TRACE:
                    raise ValueError("O12_TRACE_COVERAGE_OR_SAMPLE_ORDER")
                checkpoint=model.checkpoint()
                models.append({
                    "family":family,"seed":seed,"arm":arm,
                    "training_update_count":model.updates,
                    "training_cpu_s":fit_cpu,
                    "checkpoint_bytes":len(checkpoint),
                    "checkpoint_sha256":hashlib.sha256(checkpoint).hexdigest(),
                    "numeric_representation":"Decimal34" if arm in DEC_VARIANTS else "native_float",
                    "public_retained_state_scalars":5,
                    "public_stored_full_history_events":0,
                    "trace":trace,
                })
    assert len(models)==4*2*3
    return {
        "schema":"forge.optimizer.o12.new-train-only-numeric-receipt.v1",
        "no_old_o10_o11_dev_or_select_role_consumption":True,
        "protected_scientific_first_use":False,
        "scientific_candidate_admitted":False,
        "original_o10_model_code_blob":"56203c6aa60b29c4a5e8fb4bcd250bc212582209",
        "sources_sha256":source_hashes,
        "models":models,
        "platform":platform.platform(),
        "python_version":sys.version.split()[0],
        "whole_process_cpu_s":time.process_time()-start,
    }


def main():
    if len(sys.argv)!=2:
        raise SystemExit("usage: train_only.py /path/o12.json")
    t=run()
    dest=Path(sys.argv[1])
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(t,sort_keys=True,allow_nan=False,
                               separators=(",",":"))+"\n",encoding="utf-8")
    print("O12_TRAIN_ONLY_SOURCE_DIGESTS="+str(len(t["sources_sha256"])))
    print("O12_MODEL_TRACES="+str(len(t["models"])))
    print("O12_TRACE_POINTS_PER_ARM="+str(len(TRACE)))
    print("O12_NO_OLD_DEV_OR_PROTECTED_USE=PASS")
    print("O12_NATIVE_DIAGNOSTIC_JSON="+str(dest))
    print("O12_TOTAL_PROCESS_CPU_SECONDS="+str(t["whole_process_cpu_s"]))


if __name__=="__main__":
    main()
