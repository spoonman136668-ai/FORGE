"""F124-CC genuinely trained alternative objective in the SAME two-link class.

Frozen pre-code prior to writing. The original CB learner is never called;
only pure CB algebra and bit packing are reused, with a newly trained
exact-symbol residual objective (CB used FIT bit Hamming). All 40 public
FIT available; CHECK is confidence veto only. Zero protected source use.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE/"f124cb_dual_link_learner.py"

def algebra():
    spec=importlib.util.spec_from_file_location("CC_frozen_CB_algebra_only",BASE)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def train(fit,check):
    m=algebra()
    rows=m._validate(fit,check)
    m.need(m.PARAM_BITS==32 and m.FITS==40 and m.CHECKS==8
           and len(m.PERMS)==24 and m.RESIDUAL_COUNT==6560
           and m.FIT_SCORING_COUNT==6560,
           "ORIGINAL_EQUAL_CAPACITY_AND_PUBLIC_INFORMATION")
    locals_by_slot={}
    scanned=0
    scored=0
    for slot in range(4):
        gates=(0,1) if slot in (0,2) else (0,)
        gains=m.ODDS if slot<3 else (1,)
        for src_idx in range(4):
            for link in gates:
                xy=[(x[src_idx],y[slot]^(y[slot+1] if link else 0))
                    for x,y in rows]
                best=None
                tie=0
                for gain in gains:
                    hist=[0]*16
                    for src,dst in xy:
                        hist[(dst-gain*src)&15]+=1
                        scanned+=1
                    bias=min(range(16),key=lambda k:(-hist[k],k))
                    mismatch=sum(((gain*src+bias)&15)!=dst for src,dst in xy)
                    scored+=len(xy)
                    if best is None or mismatch<best[0]:
                        best=(mismatch,gain,bias)
                        tie=0
                    elif mismatch==best[0] and (gain,bias)!=best[1:]:
                        tie+=1
                locals_by_slot[slot,src_idx,link]={
                    "loss":best[0],"gain":best[1],"bias":best[2],
                    "ambiguous":tie>0}
    m.need(scanned==scored==6560,
           "FROZEN_EXACT_SAME_6560_LOCAL_RESIDUAL_AND_SCORE_WORK")
    winner=None
    global_ties=0
    layouts=0
    for perm in m.PERMS:
        for flag0 in (0,1):
            for flag2 in (0,1):
                links=(flag0,flag2)
                slots=[locals_by_slot[j,perm[j],
                       links[0] if j==0 else links[1] if j==2 else 0]
                       for j in range(4)]
                mismatch=sum(s["loss"] for s in slots)
                gains=tuple(s["gain"] for s in slots)
                biases=tuple(s["bias"] for s in slots)
                word=m.pack(perm,gains,biases,links)
                ambiguous=any(s["ambiguous"] for s in slots)
                layouts+=1
                if winner is None or mismatch<winner["mismatch"]:
                    winner={"mismatch":mismatch,"word":word,
                            "ambiguous":ambiguous}
                    global_ties=0
                elif mismatch==winner["mismatch"]:
                    global_ties+=1
    m.need(layouts==96,"ORIGINAL_96_LAYOUT_SEARCH_REQUIRED")
    fit_error=sum((m.forward(x,winner["word"])^y).bit_count()
                  for x,y in fit)
    check_error=sum((m.forward(x,winner["word"])^y).bit_count()
                    for x,y in check)
    admitted=(fit_error<=6 and check_error<=2
              and global_ties==0 and not winner["ambiguous"])
    return (winner["word"] if admitted else None),{
       "schema":"mass.f124cc.fully-trained-two-link-symbol-objective.v1",
       "original_CB_model_learn_invoked":False,
       "fit_only_full_training":True,
       "CHECK_veto_only":True,
       "same_32bit_persistent_state":True,
       "original_public_FIT_sha256":hashlib.sha256(
           json.dumps(fit,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
       "symbol_mismatches":winner["mismatch"],
       "FIT_bit_errors":fit_error,"CHECK_bit_errors":check_error,
       "train_residuals":scanned,"train_score_samples":scored,
       "global_layouts_fully_trained":layouts,
       "tie_count":global_ties,"local_ambiguous":winner["ambiguous"],
       "learned_flags":m.unpack(winner["word"])[-1],
       "no_source_or_graph_truth_access":True,
       "science_accepted":False,"protected_used":False,
       "confidence":admitted}

def forward(x,state):
    return algebra().forward(x,state)

def inverse(y,state):
    return algebra().inverse(y,state)

if __name__=="__main__":
    raise SystemExit("CC_MODEL_NO_INDEPENDENT_SCIENTIFIC_FIRSTUSE")
