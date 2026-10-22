"""Q17C frozen read-only RNN mathematical pretraining audit.

Never fit, update, checkpoint, evaluate DEV, instantiate held, run original
source, or dispatch any science. Uses only the first 32 already exposed FIT
samples to reproduce mathematical operands before optimizer step one.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import platform
import random
import sys
from decimal import Decimal, localcontext
from pathlib import Path

BASE=Path(__file__).resolve().parent
Q17B=BASE.parent/"q17b_twoedge"
sys.path.insert(0,str(Q17B))
import experiment as q17b  # noqa: E402

FROZEN_AUDIT_BLOB="02cd82ed887023a15d7e351e9be437a8ead83330"
BLOBS={
    "FROZEN_PROTOCOL.json":"7b09596afb9a3e2859f2de20e470c91416d94578",
    "experiment.py":"ba447295eaedd094907e56faef67fad2bfc283c3",
    "test_experiment.py":"b3c0051234312280c0fc286e016320e6156b17df"
}
KIND="TRAINED_TWO_STATE_TANH_RNN"


def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()


def git_blob(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def ensure(ok,code):
    if not ok:
        raise RuntimeError("Q17C_"+code)


def hexlist(xs):
    return [float(z).hex() for z in xs]


def digest_obj(v):
    return sha(json.dumps(v,sort_keys=True,separators=(",",":"),
                          ensure_ascii=True).encode())


def pure_decimal_tanh(x):
    with localcontext() as ctx:
        ctx.prec=90
        d=Decimal.from_float(float(x))
        v=(2*d).exp()
        return float((v-1)/(v+1))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=("math-audit",),required=True)
    parser.parse_args()
    audit=(BASE/"FROZEN_AUDIT.json").read_bytes()
    ensure(git_blob(audit)==FROZEN_AUDIT_BLOB,"AUDIT_PREEXECUTION_IDENTITY_DRIFT")
    policy=json.loads(audit)
    ensure(policy["source_preimage"]=="a4fe005a18de77a17b4404dc042720da4c640a63",
           "ORIGINAL_SOURCE_PREIMAGE_DRIFT")
    for name,blob in BLOBS.items():
        ensure(git_blob((Q17B/name).read_bytes())==blob,
               "Q17B_ORIGINAL_SCIENTIFIC_SOURCE_CHANGED_"+name)
    doc=q17b.frozen()
    ensure(doc["training"]["epochs"]==24
           and doc["training"]["restarts"]==[0,1],
           "PREV_TRAINING_POLICY_CHANGED")
    # Guard cannot cause training: calls to mutable optimization functions
    # terminate instead of yielding a potentially unreported model update.
    def forbid(*unused,**kw):
        raise RuntimeError("Q17C_MODEL_TRAINING_OR_PARAMETER_UPDATE_FORBIDDEN")
    q17b.train_gradient=forbid
    q17b.train_symbolic=forbid
    fit=q17b.episodes("fit",doc)
    ensure(len(fit)==256,"FROZEN_FIT_CARDINALITY")
    seed=q17b.seeded("q17b-init",KIND,0)
    rng=random.Random(seed)
    params=[rng.uniform(-.4,.4) for _ in range(9)]
    order=list(range(len(fit)))
    rng.shuffle(order)
    indices=order[:doc["training"]["batch_episodes"]]
    batch=[fit[i] for i in indices]
    ensure(len(batch)==32 and len(params)==9,"INITIAL_BATCH_DRIFT")
    # Exact first forward trajectory at unchanged initial params.
    events,label=fit[indices[0]]
    state=[0.0,0.0]
    trace=[]
    for edge,action,outcome in events:
        match=2*int(action==outcome)-1
        pre=params[0]*state[edge]+params[1+edge]*match+params[3+edge]
        post=math.tanh(pre)
        state[edge]=post
        if len(trace)<12:
            trace.append({"edge":edge,"match":match,
                          "pre":pre.hex(),"post":post.hex(),
                          "dec90":pure_decimal_tanh(pre).hex()})
    logit=params[5]*state[0]+params[6]*state[1]+(
        params[7]*state[0]*state[1])+params[8]
    fixed_probs=q17b.probability(KIND,params,events)
    batchloss=q17b.average_loss(KIND,params,batch)
    finite_grad=[]
    step=doc["training"]["finite_difference_epsilon"]
    for index in range(9):
        plus=params.copy();minus=params.copy()
        plus[index]+=step
        minus[index]-=step
        hi=q17b.average_loss(KIND,plus,batch)
        lo=q17b.average_loss(KIND,minus,batch)
        finite_grad.append({"index":index,"loss_up":hi.hex(),
                            "loss_down":lo.hex(),
                            "gradient":((hi-lo)/(2*step)).hex()})
    probes=[-20.,-10.,-2.,-1.,-.3,0.,.3,1.,2.,10.,20.]
    funcs=[{"input":float(v).hex(),"tanh":math.tanh(v).hex(),
            "decimal90_tanh":pure_decimal_tanh(v).hex()} for v in probes]
    report={
        "schema":"forge.nci04.q17c.readonly_rnn_math_result.v1",
        "q17b_source_git_sha":"a4fe005a18de77a17b4404dc042720da4c640a63",
        "q17c_protocol_blob":FROZEN_AUDIT_BLOB,
        "platform":platform.platform(),
        "python_version":sys.version.split()[0],
        "implementation":platform.python_implementation(),
        "float_mantissa_digits":sys.float_info.mant_dig,
        "training_or_model_update_performed":False,
        "dev_or_held_generated":False,
        "original_source_episodes":0,
        "fit_cohort_digest":q17b.cohort_sha(fit),
        "initial_restart_0_seed":seed,
        "initial_parameters_hex":hexlist(params),
        "first_batch_indices_sha256":digest_obj(indices),
        "first_batch_indices_prefix":indices[:12],
        "first_fit_event_label":label,
        "first_fit_event_digest":digest_obj(events),
        "first_12_hidden_transition_hex":trace,
        "fixed_forward_logit_hex":logit.hex(),
        "fixed_forward_probability_hex":fixed_probs.hex(),
        "fixed_batch_loss_hex":batchloss.hex(),
        "fixed_batch_gradient_hex":finite_grad,
        "math_tanh_probe":funcs,
        "conclusion_scope":"INITIAL_FIT_OPERANDS_NO_TRAINING_NO_DEVELOPMENT",
    }
    ensure(report["fit_cohort_digest"]==
           "7f970f4690da9278d337c1fa2b2ad3c81bc73cda14517746904a9ae07b77e931",
           "PREVIOUS_FIT_EVIDENCE_NOT_REPRODUCED")
    print("Q17C_RESULT_JSON="+json.dumps(report,sort_keys=True,
                                    separators=(",",":")),flush=True)
    print("Q17C_INITIAL_FIT_MATH_FORENSICS=PASS",flush=True)
    print("Q17C_NO_RETRAIN_NO_DEV_NO_HELD=PASS",flush=True)


if __name__=="__main__":
    main()
