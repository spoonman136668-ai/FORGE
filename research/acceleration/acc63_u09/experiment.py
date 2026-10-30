#!/usr/bin/env python3
"""ACC-63 U09 source-free hierarchical seed surrogate, NOT pretrained model acceleration."""
from __future__ import annotations
import argparse
import functools
import hashlib
import json
import struct
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
REGISTRY=ROOT/"research/ac07_sourcefree/ac08_portfolio.py"
PREREG=ROOT/"docs/research/ACC-63-U09-PREEXEC-20261030.md"
REGISTRY_BLOB="5126c860771fb024ccfc14c3f7ee8925edf29787"
PREREG_COMMIT="6e4e4cb2c6b25e29997e583d5954912eb8cde529"
SIDES=(32,64)
IN_SEEDS=(3,11,23)
OUT_SEEDS=(37,41,43)
CONTROL_IDS=(101,103,107)
DICTIONARY=tuple(range(32))
LEVELS=(4,8,16)
BLOCK_LABEL=b"forge-acc63-u09-v1:block:"
ARRAY_LABEL=b"forge-acc63-u09-v1:array:"
SPLIT_LABEL=b"forge-acc63-u09-v1:split:"
VECTOR_LABEL=b"forge-acc63-u09-v1:matvec:"

def git_blob(payload:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(payload)).encode()+b"\0"+payload).hexdigest()

def source_identity()->dict:
    if not REGISTRY.is_file() or git_blob(REGISTRY.read_bytes().replace(b"\r\n",b"\n"))!=REGISTRY_BLOB:
        raise RuntimeError("ACC63_ORIGINAL_REGISTRY_DRIFT")
    if '"fractal-seed arbitrary weight replacement"' not in REGISTRY.read_text(encoding="utf-8"):
        raise RuntimeError("ACC63_ORIGINAL_CLAIM_MISSING")
    if not PREREG.is_file() or "U09" not in PREREG.read_text(encoding="utf-8"):
        raise RuntimeError("ACC63_FROZEN_PREREG_MISSING")
    return {"original_registry_git_blob":REGISTRY_BLOB,"prereg_commit":PREREG_COMMIT,
            "claim_id":"U09","model_claim_scope":"SYNTHETIC_HIERARCHICAL_SURROGATE_NOT_AUTHENTIC_FRACTAL_MODEL"}

def h(*values: int, prefix:bytes)->bytes:
    return hashlib.sha256(prefix+b"".join(struct.pack(">I",x) for x in values)).digest()

@functools.lru_cache(maxsize=None)
def block_coeff(seed:int, side:int, level:int, br:int, bc:int)->int:
    if seed<0 or side not in SIDES or level not in LEVELS or br<0 or bc<0:
        raise ValueError("invalid hierarchical block")
    return h(seed,side,level,br,bc,prefix=BLOCK_LABEL)[0]%7-3

def weight(seed:int,side:int,row:int,col:int)->int:
    if side not in SIDES or not 0<=row<side or not 0<=col<side:
        raise ValueError("invalid position")
    raw=sum(block_coeff(seed,side,level,row//(side//level),col//(side//level))
            for level in LEVELS)
    return max(-8,min(7,raw))

def matrix(seed:int, side:int)->tuple[int,...]:
    if side not in SIDES:raise ValueError("unfrozen side")
    return tuple(weight(seed,side,i//side,i%side) for i in range(side*side))

def control_matrix(key:int,side:int)->tuple[int,...]:
    if key not in CONTROL_IDS or side not in SIDES:raise ValueError("unfrozen control")
    return tuple(h(key,side,i,prefix=ARRAY_LABEL)[0]%16-8 for i in range(side*side))

def check_index(side:int)->tuple[int,...]:
    if side not in SIDES:raise ValueError("unfrozen side")
    return tuple(i for i in range(side*side)
        if h(side,i//side,i%side,prefix=SPLIT_LABEL)[0]%5==0)

def fit_index(side:int)->tuple[int,...]:
    checks=set(check_index(side))
    return tuple(i for i in range(side*side) if i not in checks)

def mae(pred:tuple[int,...],actual:tuple[int,...],indices:tuple[int,...])->float:
    if not indices or len(pred)!=len(actual):raise ValueError("empty comparison or shape drift")
    return sum(abs(pred[i]-actual[i]) for i in indices)/len(indices)

def choose_seed(actual:tuple[int,...],side:int)->tuple[int,float]:
    fit=fit_index(side)
    if len(actual)!=side*side:raise ValueError("shape drift")
    ranked=[(sum(abs(weight(s,side,i//side,i%side)-actual[i]) for i in fit),s)
            for s in DICTIONARY]
    best=min(ranked)
    return best[1],best[0]/len(fit)

def means(actual:tuple[int,...],side:int)->dict[str,tuple[int,...]]:
    if len(actual)!=side*side:raise ValueError("shape drift")
    fit=fit_index(side)
    def rounded(vals:list[int])->int:
        if not vals:raise RuntimeError("missing fitted row/column")
        return max(-8,min(7,round(sum(vals)/len(vals))))
    overall=rounded([actual[i] for i in fit])
    rows=[rounded([actual[i] for i in fit if i//side==r]) for r in range(side)]
    cols=[rounded([actual[i] for i in fit if i%side==c]) for c in range(side)]
    return {"global_mean":(overall,)*(side*side),
        "row_mean":tuple(rows[i//side] for i in range(side*side)),
        "column_mean":tuple(cols[i%side] for i in range(side*side))}

def matvec(weights:tuple[int,...],side:int,key:int)->tuple[int,...]:
    if len(weights)!=side*side or key not in (0,1,2):raise ValueError("invalid matvec")
    inp=[h(side,key,c,prefix=VECTOR_LABEL)[0]%7-3 for c in range(side)]
    return tuple(sum(weights[r*side+c]*inp[c] for c in range(side))
                 for r in range(side))

def digest_int8(weights:tuple[int,...])->str:
    if any(not -128<=x<128 for x in weights):raise ValueError("out of int8")
    return hashlib.sha256(bytes(x&255 for x in weights)).hexdigest()

def case_report(side:int,family:str,source:int)->dict:
    if family=="in_dict":
        if source not in IN_SEEDS:raise ValueError("bad in-dict source")
        target=matrix(source,side)
    elif family=="out_dict":
        if source not in OUT_SEEDS:raise ValueError("bad out-dict source")
        target=matrix(source,side)
    elif family=="hash_control":
        target=control_matrix(source,side)
    else:raise ValueError("unknown source family")
    chosen,fit_mae=choose_seed(target,side)
    predicted=matrix(chosen,side)
    check=check_index(side)
    controls=means(target,side)
    expected=[matvec(target,side,k) for k in (0,1,2)]
    actual=[matvec(predicted,side,k) for k in (0,1,2)]
    is_exact=target==predicted
    return {"side":side,"family":family,"source":source,
        "selected_seed":chosen,"source_seed_known_only_for_posthoc_check":source if family!="hash_control" else None,
        "fit_entries":len(fit_index(side)),"check_entries":len(check),"fit_mae":fit_mae,
        "check_mae":mae(predicted,target,check),
        "check_exact_share":sum(predicted[i]==target[i] for i in check)/len(check),
        "comparator_check_mae":{name:mae(x,target,check) for name,x in controls.items()},
        "full_tensor_exact":is_exact,"tensor_sha256":digest_int8(target),
        "predicted_sha256":digest_int8(predicted),
        "matvec_3_of_3_exact":sum(a==b for a,b in zip(expected,actual)),
        "matvec_max_absolute_error":max(abs(x-y) for a,b in zip(expected,actual)
                                        for x,y in zip(a,b)),
        "candidate_seed_payload_bytes":1,
        "search_candidate_evaluations":len(DICTIONARY)*len(fit_index(side))}

def report()->dict:
    custody=source_identity()
    records=[case_report(side,family,seed) for side in SIDES
             for family,seeds in (("in_dict",IN_SEEDS),("out_dict",OUT_SEEDS),
                                  ("hash_control",CONTROL_IDS)) for seed in seeds]
    in_rows=[x for x in records if x["family"]=="in_dict"]
    other=[x for x in records if x["family"]!="in_dict"]
    restricted=(len(in_rows)==6 and all(x["full_tensor_exact"] and
        x["selected_seed"]==x["source"] and x["matvec_3_of_3_exact"]==3
        and x["check_mae"]==0 for x in in_rows))
    neg=(len(other)==12 and all(not x["full_tensor_exact"] for x in other))
    if any(not(.15<=x["check_entries"]/(x["side"]**2)<=.25) for x in records):
        raise RuntimeError("FIT_CHECK_SPLIT_OUTSIDE_FROZEN_RANGE")
    return {"schema":"forge.acc63.u09.synthetic-hierarchical-seed.v1",
        "identity":custody,"sides":list(SIDES),"dictionary":[0,31],
        "candidate_generator_levels":list(LEVELS),
        "fit_check_rule":"sha256 fixed split; 1/5, no check used to select",
        "rounding":"Python round nearest, ties-to-even, clamp [-8,7]",
        "candidate_decoder_source_bytes":Path(__file__).stat().st_size,
        "completeness":{"source_matrices":18,"in_dict":6,"outside":12,
                        "independent_matvec_inputs_each":3},
        "cases":records,
        "classification":{
            "in_dictionary_exact":"U09_PASS_RESTRICTED_ONLY" if restricted else "U09_NO_GO_IN_DICT",
            "out_of_dictionary_general":"U09_NO_GO_OUT_DICT" if neg else "U09_UNEXPECTED_CONTROL_MATCH_REVIEW",
            "original_pretrained_llm_speed_memory_accuracy":"UNVERIFIED",
            "scientific_first_use":"NOT_ESTABLISHED",
            "production_admission":"NOT_GRANTED"},
        "limitations":"Hierarchical synthetic surrogate, no actual fractal-model source, pretrained tensor, "
            "training, original hardware benchmark or model-level outcome. Hash controls are "
            "deterministic and not truly incompressible; one byte seed excludes decoder code "
            "and cannot be quoted as whole-model footprint."}

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--json",required=True,type=Path)
    args=p.parse_args()
    result=report()
    args.json.parent.mkdir(parents=True,exist_ok=True)
    args.json.write_bytes((json.dumps(result,sort_keys=True,indent=2)+"\n").encode("utf-8"))
    print("ACC63_U09_SOURCE_BOUND=PASS")
    print("ACC63_U09_IN_DICT="+result["classification"]["in_dictionary_exact"])
    print("ACC63_U09_OUT_DICT="+result["classification"]["out_of_dictionary_general"])
    print("ACC63_U09_REAL_MODEL=UNVERIFIED")

if __name__=="__main__":main()
