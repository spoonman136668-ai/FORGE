#!/usr/bin/env python3
"""ACC-67: finite eight-bit nonlinear state predictor vs matched trained controls.

No infinite cognition, no native model, no independent scientific first use.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import time
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[3]
REGISTRY=ROOT/"research/ac07_sourcefree/ac08_portfolio.py"
PREREG=ROOT/"docs/research/ACC-67-U21-PREREG-20261030.md"
REGISTRY_GIT_BLOB="5126c860771fb024ccfc14c3f7ee8925edf29787"
PREREG_COMMIT="1c961a1793e8f453bc210a1fa33b12a83f780af5"
AUSTEN_COMMIT="81db45c9c48c592f0b77f01fc59e677ad0a5634e"
AUSTEN_GIT_BLOB="0a7d439c2f34b0dfacb88b7116429a9575b5735c"
AUSTEN_SHA256="441e778a4297bfc944dc254810e8ded3134cfb0e36d73eef6bb312b4ffd74d6a"
AUSTEN_BYTES=717602
SOURCE_URL=("https://raw.githubusercontent.com/GITenberg/Pride-and-Prejudice_1342/"
            +AUSTEN_COMMIT+"/1342.txt")
ALPHABET="abcdefghijklmnopqrstuvwxyz "
AIDX={c:i for i,c in enumerate(ALPHABET)}
V=27
STARTS=(24576,98304,196608)
OFFSETS={"fit":(0,14000),"gap1":(14000,16000),"dev":(16000,20000),
         "gap2":(20000,22000),"check":(22000,28000)}
MODELS=("ngram2","ngram4","linear_state","hash_state","chaos_state")
CONTROLS=("ngram2","ngram4","linear_state","hash_state")
SEED=17
H_DOMAIN=b"forge-acc67-u21-v1"

def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def git_blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def source_custody()->dict:
    if not REGISTRY.is_file() or git_blob(REGISTRY.read_bytes().replace(b"\r\n",b"\n"))!=REGISTRY_GIT_BLOB:
        raise RuntimeError("ACC67_U21_ORIGINAL_REGISTRY_DRIFT")
    if '"chaos-seed infinite cognition"' not in REGISTRY.read_text(encoding="utf-8"):
        raise RuntimeError("ACC67_U21_CLAIM_MISSING")
    if not PREREG.is_file() or "ACC-67 / U21" not in PREREG.read_text(encoding="utf-8"):
        raise RuntimeError("ACC67_U21_PREREG_MISSING")
    return {"claim_id":"U21","original_git_blob":REGISTRY_GIT_BLOB,
            "prereg_commit":PREREG_COMMIT,"source_previous_exposure":"G74_AND_U23",
            "scientific_new_first_use":False}

def load_prose()->tuple[str,dict]:
    with urlopen(Request(SOURCE_URL,headers={"User-Agent":"FORGE-ACC67-U21/1.0"}),timeout=45) as response:
        raw=response.read(AUSTEN_BYTES+1)
    if len(raw)!=AUSTEN_BYTES or sha(raw)!=AUSTEN_SHA256 or git_blob(raw)!=AUSTEN_GIT_BLOB:
        raise RuntimeError("AUSTEN_SOURCE_IDENTITY_MISMATCH")
    original=raw.decode("utf-8")
    prose="".join(lower if len(lower)==1 and lower in AIDX else " "
                  for c in original for lower in (c.lower(),))
    if len(prose)<max(STARTS)+28000:raise RuntimeError("AUSTEN_SOURCE_TOO_SHORT")
    return prose,{"repo":"GITenberg/Pride-and-Prejudice_1342",
                  "commit":AUSTEN_COMMIT,"git_blob":AUSTEN_GIT_BLOB,
                  "source_sha256":AUSTEN_SHA256,"raw_bytes":AUSTEN_BYTES,
                  "normalized_sha256":sha(prose.encode("ascii")),
                  "previous_exposure":"G74_AND_U23"}

def windows(prose:str,start:int)->dict[str,str]:
    if start not in STARTS or len(prose)<start+28000:raise ValueError("invalid frozen fold")
    source=prose[start:start+28000]
    pieces={name:source[a:b] for name,(a,b) in OFFSETS.items()}
    if list(map(len,pieces.values()))!=[14000,2000,4000,2000,6000]:
        raise RuntimeError("UNFROZEN_WINDOW")
    return pieces

def original_ac06_autonomous(x:int)->int:
    if not 0<=x<256:raise ValueError("state not uint8")
    return (3*x*(255-x)//255)%256

def advance(model:str,s:int,char:str)->int:
    if not 0<=s<256 or char not in AIDX:raise ValueError("invalid state or character")
    c=AIDX[char]
    if model=="chaos_state":
        return (original_ac06_autonomous(s)+17*(c+1))%256
    if model=="linear_state":
        return (37*s+c+1)%256
    if model=="hash_state":
        return hashlib.sha256(H_DOMAIN+bytes((s,c))).digest()[0]
    raise ValueError("unknown state transition")

def finite_witness()->dict:
    orbits=[]
    for seed in range(256):
        seen={}
        state=seed
        while state not in seen:
            seen[state]=len(seen)
            state=original_ac06_autonomous(state)
            if len(seen)>256:raise RuntimeError("FINITE_ORBIT_BROKEN")
        orbits.append({"seed":seed,"prefix":seen[state],
                       "cycle":len(seen)-seen[state],"states_seen":len(seen)})
    states={}
    for i in ALPHABET:
        for j in ALPHABET:
            state=advance("chaos_state",advance("chaos_state",SEED,i),j)
            states.setdefault(state,[]).append(i+j)
    collision_histories=sum(len(xs)-1 for xs in states.values())
    if sum(map(len,states.values()))!=729 or collision_histories<473:
        raise RuntimeError("FINITE_MEMORY_INJECTIVITY_LIMIT_LOST")
    pair=next((xs[0],xs[1],k) for k,xs in sorted(states.items())
              if len(xs)>=2)
    if not all(x["cycle"]>=1 and x["prefix"]+x["cycle"]<=256 for x in orbits):
        raise RuntimeError("ORBIT_CLASSIFICATION_INVALID")
    return {"total_autonomous_seeds":256,
            "max_distinct_states_per_autonomous_orbit":max(x["states_seen"] for x in orbits),
            "max_prefix":max(x["prefix"] for x in orbits),
            "max_cycle":max(x["cycle"] for x in orbits),
            "two_character_histories":729,
            "distinct_eight_bit_states":len(states),
            "collision_histories":collision_histories,
            "collision_example":{"history_a":pair[0],"history_b":pair[1],"state":pair[2]},
            "unbounded_external_memory_ruled_out":False}

def iter_examples(seq:str,mode:str):
    if len(seq)<5:raise ValueError("segment shorter than context")
    state=SEED
    if mode.endswith("_state"):
        for char in seq[:4]:
            state=advance(mode,state,char)
    for i in range(4,len(seq)):
        key=state if mode.endswith("_state") else seq[i-(2 if mode=="ngram2" else 4):i]
        yield key,seq[i]
        if mode.endswith("_state"):
            state=advance(mode,state,seq[i])

def train(mode:str,fit:str)->dict:
    if mode not in MODELS:raise ValueError("unfrozen model")
    table={}
    global_counts=[0]*V
    n=0
    for key,target in iter_examples(fit,mode):
        counts=table.setdefault(key,[0]*V)
        counts[AIDX[target]]+=1
        global_counts[AIDX[target]]+=1
        n+=1
    if n!=13996 or sum(global_counts)!=n:raise RuntimeError("INCOMPLETE_FIT")
    return {"mode":mode,"table":table,"global":global_counts,"fit_count":n}

def table_bytes(model:dict)->int:
    items=sorted(model["table"].items(),key=lambda pair:str(pair[0]))
    return len(json.dumps({"table":items,"global":model["global"]},
                          separators=(",",":"),ensure_ascii=True).encode())

def evaluate(model:dict,seq:str)->dict:
    seen=0;correct=0;unknown=0;nll=0.0;predictions=[]
    for key,actual in iter_examples(seq,model["mode"]):
        counts=model["table"].get(key)
        if counts is None:
            counts=model["global"]
            unknown+=1
        prediction=ALPHABET[next(i for i,v in enumerate(counts) if v==max(counts))]
        predictions.append(prediction)
        correct+=int(prediction==actual)
        nll-=math.log((counts[AIDX[actual]]+1)/(sum(counts)+V))
        seen+=1
    return {"examples":seen,"correct":correct,"accuracy":correct/seen,
            "nll":nll/seen,"unseen":unknown,
            "prediction_sha256":sha("".join(predictions).encode("ascii"))}

def choose_control(dev:dict,sizes:dict)->str:
    # Receives DEV evidence exclusively, not CHECK metrics.
    return min(CONTROLS,key=lambda k:(-dev[k]["correct"],sizes[k],CONTROLS.index(k)))

def evaluate_fold(prose:str,start:int)->dict:
    w=windows(prose,start)
    named={name:{"characters":len(txt),"sha256":sha(txt.encode("ascii"))}
           for name,txt in w.items()}
    trained={}
    results={}
    development={}
    sizes={}
    for mode in MODELS:
        if mode.endswith("_state"):advance(mode,SEED,"a")  # No training during warmup.
        t0=time.perf_counter_ns()
        model=train(mode,w["fit"])
        fit_ns=time.perf_counter_ns()-t0
        size=table_bytes(model)
        dev=evaluate(model,w["dev"])
        t0=time.perf_counter_ns()
        check=evaluate(model,w["check"])
        check_ns=time.perf_counter_ns()-t0
        if dev["examples"]!=3996 or check["examples"]!=5996:
            raise RuntimeError("INCOMPLETE_HELDOUT_EVAL")
        trained[mode]=model
        development[mode]=dev
        sizes[mode]=size
        results[mode]={"fit_examples":model["fit_count"],
            "learned_keys":len(model["table"]),"table_bytes":size,
            "dev":dev,"check":check,
            "fit_ns":fit_ns,"check_ns":check_ns,"fit_check_ns":fit_ns+check_ns}
    selected=choose_control(development,sizes)
    challenger=results["chaos_state"]
    baseline=results[selected]
    d_acc=challenger["check"]["accuracy"]-baseline["check"]["accuracy"]
    d_nll=challenger["check"]["nll"]-baseline["check"]["nll"]
    ratio=baseline["fit_check_ns"]/challenger["fit_check_ns"]
    size_ratio=challenger["table_bytes"]/baseline["table_bytes"]
    passed=d_acc>=.02 and d_nll<=0 and ratio>=1.15 and size_ratio<=1.10
    return {"start":start,"window_hashes":named,"selected_control":selected,
            "models":results,"chaos_minus_control_check_accuracy":d_acc,
            "chaos_minus_control_check_nll":d_nll,
            "control_over_chaos_fit_check_speed":ratio,
            "chaos_over_control_table_bytes":size_ratio,"candidate_pass":passed}

def report()->dict:
    custody=source_custody()
    theory=finite_witness()
    prose,source=load_prose()
    folds=[evaluate_fold(prose,start) for start in STARTS]
    if len(folds)!=3:raise RuntimeError("FROZEN_FOLD_COUNT_DRIFT")
    all_pass=all(x["candidate_pass"] for x in folds)
    return {"schema":"forge.acc67.u21.eightbit-chaos-state-public-prose.v1",
        "identity":custody,"source":source,
        "protocol":{"starts":list(STARTS),"splits":OFFSETS,
            "modes":list(MODELS),"candidate":"chaos_state",
            "controls":list(CONTROLS),"state_bits":8,
            "state_seed":SEED,"fit_examples":13996,"dev_examples":3996,"check_examples":5996,
            "one_pass_training":True,"full_model_cpu_rss":False},
        "finite_state_witness":theory,
        "folds":folds,
        "classification":{"fixed_eight_bit_infinite_state":"U21_FIXED_8BIT_INFINITE_STATE_NO_GO",
            "chaos_state_predictive_speed_resource":"U21_RESTRICTED_CHAOS_NEXTCHAR_POSITIVE_ONLY" if all_pass else "U21_NO_VERIFIED_RESTRICTED_CHAOS_PREDICTION_WIN",
            "pretrained_LLM_inference_speed":"UNVERIFIED",
            "unfamiliar_source_generalization":"UNVERIFIED",
            "native_persistent_autonomous_cognition":"UNVERIFIED",
            "model_training_firstuse":"NOT_ESTABLISHED",
            "scientific_admission":"NOT_GRANTED",
            "production_acceptance":"NOT_GRANTED"},
        "limits":"A fitted conditional count readout on 8-bit chaos-like state is not "
                 "general infinite cognition; reused publicly exposed Austen source, "
                 "not independent heldout science. Timings are only Python FIT+CHECK "
                 "compute; no original LLM, physical memory, CPU accounting or GPU."}

def main()->None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--json",type=Path,required=True)
    args=ap.parse_args()
    out=report()
    args.json.parent.mkdir(parents=True,exist_ok=True)
    args.json.write_bytes((json.dumps(out,indent=2,sort_keys=True)+"\n").encode("utf-8"))
    print("ACC67_U21_CORPUS_SOURCE_PIN=PASS")
    print("ACC67_U21_FOLDS="+str(len(out["folds"])))
    print("ACC67_U21_STATE="+out["classification"]["fixed_eight_bit_infinite_state"])
    print("ACC67_U21_PREDICTION="+out["classification"]["chaos_state_predictive_speed_resource"])
    print("ACC67_U21_SCIENTIFIC_ADMISSION=NOT_GRANTED")

if __name__=="__main__":main()
