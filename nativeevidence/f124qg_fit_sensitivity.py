"""F124-QG source-pinned FIT-only audit of the failed frozen causal-key optimizer.

No re-training for selection, DEV generation, model changes, or alternative
optimizer. Replays the exact 72 frozen Q SPSA updates and preserves zero-gradient
outcomes. Q source/module raw blobs and F124-O original weights authenticated.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import sys

import f124o_native_learners as original
import f124q_independent_binding as model
import f124q_fresh_source as source
import f124q_training_evidence as parent

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f124qg-fit-gradient-freeze.json"
FREEZE_BLOB="495565b44b20a6a8e0b8b0ab9566612f61d2b0f6"
PARENT_RECEIPT_SHA="025c97abc8eb69079d7d7d0f59bfdb81235b9ad9ab83e230f32b542d2cfbdb5d"
SOURCE_BLOB="63a8657a948500d3d178aea2c6cdf14880faf431"
LEARNER_BLOB="ebad38ff22ef6b151fd5ff7f25da41a20d9fcf65"
SCHEMA="forge.research.f124qg.frozen-fit-spsa-zero-gradient-diagnostic.v1"


def need(ok,code):
    source.need(ok,"FIT_DIAG_"+code)


def git_blob(path):
    b=Path(path).read_bytes().replace(b"\r\n",b"\n")
    return source.git_blob(b)


def sha(v):
    b=(json.dumps(v,sort_keys=True,separators=(",",":"))+"\n").encode()
    return hashlib.sha256(b).hexdigest()


def admission():
    need(git_blob(FREEZE)==FREEZE_BLOB,"FROZEN_DIAGNOSTIC_IDENTITY")
    p=json.loads(FREEZE.read_text(encoding="utf-8"))
    need(p["schema"]=="forge.research.f124qg.frozen-fit-sensitivity-diagnostic.v1"
         and p["state"]=="PREIMPLEMENTATION_FROZEN"
         and p["source"]["failed_f124q_head"]==
             "a062296b3187eac3cc6892069be5d9a9de58125b"
         and p["source"]["original_f124o_receipt_sha256"]==PARENT_RECEIPT_SHA
         and p["source"]["source_code_blob"]==SOURCE_BLOB
         and p["source"]["learner_code_blob"]==LEARNER_BLOB
         and p["analysis"]["epochs"]==model.EPOCHS==12
         and p["analysis"]["batch"]==model.BATCH==8
         and p["analysis"]["spsa_steps"]==72
         and p["analysis"]["perturbation"]==model.PERTURB==0.08
         and p["analysis"]["rate"]==model.LR==0.04
         and p["analysis"]["no_DEV_evaluation"]
         and p["analysis"]["no_model_source_mutation"]
         and all(x is False for x in p["authority"].values())
         and git_blob(source.__file__)==SOURCE_BLOB
         and git_blob(model.__file__)==LEARNER_BLOB,
         "FROZEN_INPUT_OR_ALGORITHM_DRIFT")
    parent.validate_freeze()
    return p


def audit(lane,base):
    # Exact faithful replay of original F124-Q SPSA: never use DEV here.
    need(lane in ("Wingless","Yggdrasil") and len(base)==7,"ORIGINAL_LANE")
    pairs=model.fit_pairs(lane)
    need(len(pairs)==48,"FIT_PAIR_COUNT")
    d=list(model.WING_INIT if lane=="Wingless" else model.YGG_INIT)
    init=list(d)
    randomizer=random.Random(int.from_bytes(hashlib.sha256(
        ("F124Q/FIT/SPSA/v1/"+lane).encode()).digest()[:12],"big"))
    initial=model.loss(lane,pairs,base,d)
    zero=positive=nonzero=0
    maximum_difference=0.
    minimum_nonzero=None
    work_diffs=[]
    change_counts=[]
    for epoch in range(model.EPOCHS):
        order=list(range(48));randomizer.shuffle(order)
        for k in range(0,48,model.BATCH):
            subset=[pairs[i] for i in order[k:k+model.BATCH]]
            signs=[1 if randomizer.getrandbits(1) else -1 for _ in d]
            hi=[max(-3.,min(3.,v+model.PERTURB*s)) for v,s in zip(d,signs)]
            lo=[max(-3.,min(3.,v-model.PERTURB*s)) for v,s in zip(d,signs)]
            high=model.loss(lane,subset,base,hi)
            low=model.loss(lane,subset,base,lo)
            delta_loss=high-low
            require_finite=math.isfinite(delta_loss) and math.isfinite(high) and math.isfinite(low)
            need(require_finite,"NUMERIC_FINITE")
            grad=delta_loss/(2*model.PERTURB)
            if abs(delta_loss)<1e-12:zero+=1
            else:
                nonzero+=1
                if delta_loss>0:positive+=1
                minimum_nonzero=(abs(delta_loss) if minimum_nonzero is None else
                                 min(minimum_nonzero,abs(delta_loss)))
            maximum_difference=max(maximum_difference,abs(delta_loss))
            rate=model.LR/(1+.01*(epoch*6+k//model.BATCH))
            new=[max(-3.,min(3.,v-rate*grad*sgn))
                 for v,sgn in zip(d,signs)]
            change_counts.append(sum(abs(a-b) for a,b in zip(new,d)))
            d=new
            work_diffs.append(round(delta_loss,12))
    drift=math.sqrt(sum((a-b)**2 for a,b in zip(d,init)))
    final=model.loss(lane,pairs,base,d)
    need(zero+nonzero==72 and len(change_counts)==72 and
         math.isfinite(drift),"COMPLETE_FROZEN_TRAINING_STEPS")
    # This only instruments the original Q computations, never 'repairs' them.
    return {"lane":lane,"source_phase":"FIT_ONLY","pairs":48,
            "spsa_steps":72,"zero_loss_difference_steps":zero,
            "nonzero_loss_difference_steps":nonzero,
            "positive_loss_difference_steps":positive,
            "zero_weight_change_steps":sum(x<1e-12 for x in change_counts),
            "initial_fit_loss":round(initial,12),
            "final_fit_loss":round(final,12),
            "max_absolute_two_sided_difference":round(maximum_difference,12),
            "min_nonzero_two_sided_difference":(
                None if minimum_nonzero is None else round(minimum_nonzero,12)),
            "step_difference_sha256":sha(work_diffs),
            "delta_sha256":sha(d),
            "update_l2":round(drift,12),
            "trained_update_qualified":drift>1e-9,
            "outcome":("FIT_LEARNED_UPDATE_CONFIRMED" if drift>1e-9
                       else "FIT_NO_UPDATE_NEGATIVE_RETAINED"),
            "dev_examples_scored":0,"protected_examples_scored":0}


def produce(path):
    admission()
    bases=parent.original_weights(path)
    reports=[audit(lane,bases[lane]) for lane in ("Wingless","Yggdrasil")]
    return {"schema":SCHEMA,"source_protocol_sha":SOURCE_BLOB,
            "frozen_diagnostic_git_blob":FREEZE_BLOB,
            "frozen_original_weights_sha256":PARENT_RECEIPT_SHA,
            "original_train_failure_head":
                "a062296b3187eac3cc6892069be5d9a9de58125b",
            "lanes":reports,"original_Q_model_modified":False,
            "development_only":True,"dev_cases_generated":0,
            "scientific_acceptances":0,"accepted_ref_mutations":0,
            "optimizer_promotions":0,"first_use":False,
            "paid_model_calls":0,"codex_calls":0,
            "new_schedulers":0,"resource_matched_science":False}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--f124o-receipt",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    out=Path(args.output)
    need(out.parent.is_dir() and not out.exists(),"IMMUTABLE_OUTPUT")
    result=produce(args.f124o_receipt)
    b=json.dumps(result,indent=2,sort_keys=True).encode()+b"\n"
    with out.open("xb") as f:f.write(b)
    print("F124QG_RECEIPT_SHA256="+hashlib.sha256(b).hexdigest())
    for z in result["lanes"]:
        print("F124QG_FIT="+z["lane"]+":nonzero_loss_steps="+
              str(z["nonzero_loss_difference_steps"])+"/72:update_l2="+
              str(z["update_l2"])+":"+z["outcome"])


if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as exc:
        print("F124QG_SOURCE_QUARANTINED:"+str(exc),file=sys.stderr)
        sys.exit(1)
