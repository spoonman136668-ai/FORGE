"""F124-CA independent fully trained same-information BZ binding control.

Frozen BEFORE engineering sources: same reversible 31-bit + reserved-zero
state family, 40 FIT / 8 CHECK, 24 layout permutations, 2 relation modes,
48k residual samples and 48k symbol evaluations. Training objective is
EXACT NIBBLE mismatch rather than candidate BZ bit-error loss. All training
is performed independently: NEVER delegate to BZ.learn. This is a strong
fully trained learned control, not an untrained identity/solver.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ORIGINAL=HERE/"f124bz_binding_candidate.py"


def load():
    s=importlib.util.spec_from_file_location("CA_frozen_BZ_algebra",ORIGINAL)
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def train(fit,check):
    model=load()
    rows=model._validate(fit,check)
    model.need(model.FIT==40 and model.CHECK==8
               and model.BITS==32 and len(model.PERMS)==24,
               "CA_FROZEN_EQUAL_INFORMATION")
    best=None
    ties=0
    residuals=0
    evaluations=0
    total=0
    for gate in (0,1):
        for pi,perm in enumerate(model.PERMS):
            gains=[]; biases=[]; mismatch=0; ambiguous=False
            for slot in range(4):
                pool=model.ODD if slot<3 else (1,)
                chosen=None; slot_ties=0
                for gain in pool:
                    histogram=[0]*16
                    vals=[]
                    for x,y in rows:
                        target=y[slot] ^ (y[1] if gate and slot==0 else 0)
                        val=x[perm[slot]]
                        bias=(target-gain*val)&15
                        histogram[bias]+=1
                        vals.append((val,target))
                        residuals+=1
                    # exact output-symbol correctness, not bit Hamming.
                    bias=min(range(16),key=lambda b:(-histogram[b],b))
                    errors=sum(((gain*x+bias)&15)!=target
                               for x,target in vals)
                    evaluations+=len(vals)
                    contender=(errors,gain,bias)
                    if chosen is None or errors<chosen[0]:
                        chosen=contender; slot_ties=0
                    elif errors==chosen[0] and (gain,bias)!=chosen[1:]:
                        slot_ties+=1
                gains.append(chosen[1])
                biases.append(chosen[2])
                mismatch+=chosen[0]
                ambiguous|=bool(slot_ties)
            word=model.pack(perm,tuple(gains),tuple(biases),gate)
            total+=1
            if best is None or mismatch<best["mismatches"]:
                best={"mismatches":mismatch,"word":word,"ambiguous":ambiguous,
                      "permutation":pi,"gate":gate}
                ties=0
            elif mismatch==best["mismatches"]:
                ties+=1
    model.need(residuals==model.TRAIN_RESIDUALS==48000
               and evaluations==48000 and total==48,
               "CA_MATCHED_FULL_TRAINING_COUNTS")
    # Frozen BZ safety ceilings remain identical even though search loss
    # differs; CHECK has no influence on the learned layout.
    fit_error=sum((model.forward(x,best["word"])^y).bit_count()
                  for x,y in fit)
    check_error=sum((model.forward(x,best["word"])^y).bit_count()
                    for x,y in check)
    confidence=(not best["ambiguous"] and ties==0
                and fit_error<=model.FIT_BIT_ERROR_MAX
                and check_error<=model.CHECK_BIT_ERROR_MAX)
    return (best["word"] if confidence else None),{
        "schema":"mass.f124ca.independently-trained-exact-symbol-binding.v1",
        "full_train_residuals":residuals,
        "full_train_symbol_score_evaluations":evaluations,
        "FIT_bit_errors":fit_error,"CHECK_bit_errors":check_error,
        "FIT_mismatched_symbols":best["mismatches"],
        "sourceblind_FIT_only":True,"CHECK_veto_only":True,
        "original_candidate_learn_called":False,
        "fully_trained_40_public_FIT":True,
        "same_31bit_state_plus_reserved_zero":True,
        "permutation_index":best["permutation"],
        "relation_gate":best["gate"],
        "ambiguous_equal_loss_layouts":ties,
        "ambiguous_gains":best["ambiguous"],
        "public_FIT_hash":hashlib.sha256(json.dumps(
            fit,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
        "science_firstuse":False,"protected_opened":False,
        "accepted":confidence
    }


def forward(x,state):
    return load().forward(x,state)


def inverse(y,state):
    return load().inverse(y,state)


if __name__=="__main__":
    raise SystemExit("F124CA_ONLY_FROZEN_PUBLIC_TEST_AND_ORIGINAL_NATIVE")
