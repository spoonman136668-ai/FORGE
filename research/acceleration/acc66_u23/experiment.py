#!/usr/bin/env python3
"""ACC-66 U23: limited learned character prediction with four-point spectral power.

Authentic previously exposed Austen text; not a pretrained model or real LLM first-use.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import time
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[3]
REGISTRY=ROOT/"research/ac07_sourcefree/ac08_portfolio.py"
PREREG=ROOT/"docs/research/ACC-66-U23-PREREG-20261030.md"
ORIGINAL_REGISTRY_BLOB="5126c860771fb024ccfc14c3f7ee8925edf29787"
PREEXEC_COMMIT="87509a9551d0a572b3f910ea5e3826fa629efad2"
AUSTEN_COMMIT="81db45c9c48c592f0b77f01fc59e677ad0a5634e"
AUSTEN_GIT_BLOB="0a7d439c2f34b0dfacb88b7116429a9575b5735c"
AUSTEN_SHA256="441e778a4297bfc944dc254810e8ded3134cfb0e36d73eef6bb312b4ffd74d6a"
AUSTEN_BYTES=717602
AUSTEN_URL=("https://raw.githubusercontent.com/GITenberg/Pride-and-Prejudice_1342/"
            +AUSTEN_COMMIT+"/1342.txt")
ALPHABET="abcdefghijklmnopqrstuvwxyz "
ALPHA_IDX={c:i for i,c in enumerate(ALPHABET)}
STARTS=(24576,98304,196608)
MODELS=("ngram1","ngram2","ngram4","spectral_power_4")
OFFSETS={"fit":(0,14000),"gap1":(14000,16000),"dev":(16000,20000),
         "gap2":(20000,22000),"check":(22000,28000)}
CONTEXT_SIZE=4
V=len(ALPHABET)

def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def git_blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def source_identity()->dict:
    if not REGISTRY.is_file() or git_blob(REGISTRY.read_bytes().replace(b"\r\n",b"\n"))!=ORIGINAL_REGISTRY_BLOB:
        raise RuntimeError("ACC66_ORIGINAL_REGISTRY_DRIFT")
    if '"spectral one-pass language"' not in REGISTRY.read_text(encoding="utf-8"):
        raise RuntimeError("ACC66_U23_CLAIM_MISSING")
    if not PREREG.is_file() or "ACC-66 / U23" not in PREREG.read_text(encoding="utf-8"):
        raise RuntimeError("ACC66_PREEXEC_DRIFT")
    return {"claim":"U23","registry_git_blob":ORIGINAL_REGISTRY_BLOB,
            "prereg_commit":PREEXEC_COMMIT,"source_exposure":"AUSTEN_EXPOSED_IN_PRIOR_G74",
            "source_training_heldout_verified":False}

def fetch_source()->tuple[str,dict]:
    request=Request(AUSTEN_URL,headers={"User-Agent":"FORGE-ACC66-U23-source-pinned/1.0"})
    with urlopen(request,timeout=40) as response:
        raw=response.read(AUSTEN_BYTES+1)
    if (len(raw)!=AUSTEN_BYTES or sha(raw)!=AUSTEN_SHA256 or
            git_blob(raw)!=AUSTEN_GIT_BLOB):
        raise RuntimeError("ACC66_AUTHENTIC_PUBLIC_DOMAIN_AUSTEN_SOURCE_MISMATCH")
    # Exactly one output character per original decoded character.
    decoded=raw.decode("utf-8").lower()
    normalized="".join(c if c in ALPHA_IDX else " " for c in decoded)
    if len(normalized)<max(STARTS)+28000:raise RuntimeError("ACC66_CORPUS_TOO_SHORT")
    return normalized,{"repo":"GITenberg/Pride-and-Prejudice_1342",
        "source_commit":AUSTEN_COMMIT,"git_blob":AUSTEN_GIT_BLOB,
        "raw_sha256":AUSTEN_SHA256,"raw_bytes":len(raw),
        "normalized_chars":len(normalized),"normalized_sha256":sha(normalized.encode("ascii")),
        "exposed_original_prior":"ACC-G74"}

def slices(corpus:str,start:int)->dict[str,str]:
    if start not in STARTS or len(corpus)<start+28000:raise ValueError("unfrozen corpus fold")
    window=corpus[start:start+28000]
    result={name:window[a:b] for name,(a,b) in OFFSETS.items()}
    if [len(result[n]) for n in OFFSETS] != [14000,2000,4000,2000,6000]:
        raise RuntimeError("SPLIT_SIZE_CHANGED")
    return result

def examples(seq:str):
    if len(seq)<5:raise ValueError("source too short")
    for i in range(CONTEXT_SIZE,len(seq)):
        yield seq[i-CONTEXT_SIZE:i],seq[i]

def spectrum_power(context:str)->tuple[int,...]:
    if len(context)!=4 or any(c not in ALPHA_IDX for c in context):
        raise ValueError("bad spectral context")
    result=[]
    for symbol in ALPHABET:
        v=[int(c==symbol) for c in context]
        dc=v[0]+v[1]+v[2]+v[3]
        re=v[0]-v[2]
        im=v[3]-v[1]
        nyquist=v[0]-v[1]+v[2]-v[3]
        result.extend((dc,re*re+im*im,nyquist*nyquist))
    return tuple(result)

def phase_preserved(context:str)->tuple[int,...]:
    if len(context)!=4 or any(c not in ALPHA_IDX for c in context):
        raise ValueError("bad phase context")
    result=[]
    for symbol in ALPHABET:
        v=[int(c==symbol) for c in context]
        result.extend((sum(v),v[0]-v[2],v[3]-v[1],v[0]-v[1]+v[2]-v[3]))
    return tuple(result)

def inverse_phase(features:tuple[int,...])->str:
    if len(features)!=V*4:raise ValueError("bad feature shape")
    positions=[[""]*V for _ in range(4)]
    for s in range(V):
        f0,re,im,f2=features[s*4:s*4+4]
        four=(f0+f2+2*re,f0-f2-2*im,f0+f2-2*re,f0-f2+2*im)
        if any(v%4 for v in four):raise ValueError("nonintegral phase inverse")
        for i,v in enumerate(four):
            positions[i][s]=v//4
    if any(sum(row)!=1 or any(v not in (0,1) for v in row) for row in positions):
        raise ValueError("invalid phase inverse")
    return "".join(ALPHABET[row.index(1)] for row in positions)

def key(mode:str,context:str):
    if mode=="spectral_power_4":return spectrum_power(context)
    if mode in ("ngram1","ngram2","ngram4"):
        return context[-int(mode[-1]):]
    raise ValueError("unknown model")

def train(mode:str,fit:str)->dict:
    counts={}
    global_counts=[0]*V
    seen=0
    for context,target in examples(fit):
        if target not in ALPHA_IDX:raise ValueError("bad symbol")
        signature=key(mode,context)
        row=counts.setdefault(signature,[0]*V)
        row[ALPHA_IDX[target]]+=1
        global_counts[ALPHA_IDX[target]]+=1
        seen+=1
    if seen!=13996 or sum(global_counts)!=seen:raise RuntimeError("INCOMPLETE_FIT")
    return {"mode":mode,"table":counts,"global":global_counts,"fit_examples":seen}

def byte_size(model:dict)->int:
    # Deterministic logical JSON table encoding; NOT measured machine RSS.
    entries=[(list(k) if isinstance(k,tuple) else k,v) for k,v in model["table"].items()]
    entries.sort(key=lambda x:json.dumps(x[0],separators=(",",":")))
    return len(json.dumps({"table":entries,"global":model["global"]},
                          separators=(",",":"),ensure_ascii=True).encode("utf-8"))

def eval_model(model:dict,corpus_slice:str)->dict:
    correct=0
    unseen=0
    negative_loglikelihood=0.0
    predictions=[]
    count=0
    for context,target in examples(corpus_slice):
        v=model["table"].get(key(model["mode"],context))
        if v is None:
            unseen+=1
            v=model["global"]
        # Equal counts resolve alphabetically, independent of insertion order.
        max_count=max(v)
        index=next(i for i,c in enumerate(v) if c==max_count)
        prediction=ALPHABET[index]
        correct+=int(prediction==target)
        predictions.append(prediction)
        negative_loglikelihood-=math.log((v[ALPHA_IDX[target]]+1)/(sum(v)+V))
        count+=1
    return {"examples":count,"exact":correct,"accuracy":correct/count,
            "nll":negative_loglikelihood/count,
            "unseen":unseen,"prediction_sha256":sha("".join(predictions).encode("ascii"))}

def select_control(dev_rows:dict,model_bytes:dict)->str:
    # Never reads CHECK metrics.
    candidates=("ngram1","ngram2","ngram4")
    return min(candidates,key=lambda m:(-dev_rows[m]["exact"],
            model_bytes[m],int(m[-1])))

def evaluate_fold(corpus:str,start:int)->dict:
    w=slices(corpus,start)
    windows={name:{"characters":len(v),"sha256":sha(v.encode("ascii"))}
             for name,v in w.items()}
    rows={}
    dev={}
    bytes_by_model={}
    for mode in MODELS:
        # Prewarm only feature computation, without fitting any data.
        key(mode,"a bc")
        t0=time.perf_counter_ns()
        learned=train(mode,w["fit"])
        fit_ns=time.perf_counter_ns()-t0
        stored_bytes=byte_size(learned)
        dev_row=eval_model(learned,w["dev"])
        t0=time.perf_counter_ns()
        check_row=eval_model(learned,w["check"])
        check_ns=time.perf_counter_ns()-t0
        if dev_row["examples"]!=3996 or check_row["examples"]!=5996:
            raise RuntimeError("INCOMPLETE_DEVELOPMENT_OR_CHECK")
        rows[mode]={"fit_examples":learned["fit_examples"],
            "dev":dev_row,"check":check_row,"logical_json_table_bytes":stored_bytes,
            "learned_context_keys":len(learned["table"]),
            "fit_wall_ns":fit_ns,"check_wall_ns":check_ns,
            "fit_plus_check_wall_ns":fit_ns+check_ns}
        dev[mode]=dev_row
        bytes_by_model[mode]=stored_bytes
    selected=select_control(dev,bytes_by_model)
    best=rows[selected]
    spectral=rows["spectral_power_4"]
    delta=spectral["check"]["accuracy"]-best["check"]["accuracy"]
    nll_delta=spectral["check"]["nll"]-best["check"]["nll"]
    speed=best["fit_plus_check_wall_ns"]/spectral["fit_plus_check_wall_ns"]
    table_ratio=spectral["logical_json_table_bytes"]/best["logical_json_table_bytes"]
    return {"start":start,"windows":windows,"selected_baseline":selected,
        "rows":rows,"candidate_minus_best_check_accuracy":delta,
        "candidate_minus_best_check_nll":nll_delta,
        "candidate_speedup_over_best_fit_plus_check":speed,
        "candidate_table_over_best_table_bytes":table_ratio,
        "candidate_pass":delta>=.02 and nll_delta<=0 and speed>=1.15 and table_ratio<=1.10}

def report()->dict:
    identity=source_identity()
    corpus,original=fetch_source()
    folds=[evaluate_fold(corpus,start) for start in STARTS]
    if len(folds)!=3:raise RuntimeError("FROZEN_FOLD_MATRIX_MISSING")
    # Explicit phase-loss counterexample with different order/last positions.
    x,y="abcd","bcda"
    if spectrum_power(x)!=spectrum_power(y) or inverse_phase(phase_preserved(x))!=x or inverse_phase(phase_preserved(y))!=y:
        raise RuntimeError("SPECTRAL_PHASE_FALSIFIER_MISSING")
    permitted=all(f["candidate_pass"] for f in folds)
    return {"schema":"forge.acc66.u23.public-prose-bounded-spectrum-predictor.v1",
        "identity":identity,"original_source":original,
        "preregistered":{"character_starts":list(STARTS),"split":OFFSETS,
            "models":list(MODELS),"token_alphabet":ALPHABET,
            "training_count_per_fold":13996,"check_count_per_fold":5996,
            "source_first_use":"EXPOSED_IN_PRIOR_ACC_G74"},
        "phase_loss_counterexample":{"context_a":x,"context_b":y,
            "spectral_power_equal":True,"phase_inverse_a":x,"phase_inverse_b":y,
            "not_universal_semantic_falsification":True},
        "folds":folds,
        "classification":{
            "exact_phase_preserving_reconstruction":"PASS_REPRESENTATION_ONLY",
            "spectral_power_phase_collision":"PASS_RESTRICTED_NEGATIVE",
            "source_checked":"PASS",
            "spectral_power_predictor_vs_dev_selected_ngram":"U23_RESTRICTED_PUBLIC_PROSE_PREDICTION_RESOURCE_POSITIVE_ONLY" if permitted else "U23_NO_VERIFIED_RESTRICTED_PREDICTION_RESOURCE_WIN",
            "unfamiliar_domain_and_firstuse":"UNVERIFIED",
            "pretrained_llm_speed":"UNVERIFIED",
            "general_language_semantics":"UNVERIFIED",
            "complete_host_cpu_rss":"UNVERIFIED",
            "scientific_admission":"NOT_GRANTED",
            "production_acceptance":"NOT_GRANTED"},
        "caveat":"One-pass learned Fourier-POWER conditional table is phase-blind; does not test full-spectrum learned model. "
            "Already exposed Austen development text, char-level metrics, 3 non-overlapping folds and "
            "Python function computation, NOT pretrained model speed or independent scientific first use."}

def main()->None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--json",required=True,type=Path)
    args=ap.parse_args()
    result=report()
    args.json.parent.mkdir(parents=True,exist_ok=True)
    args.json.write_bytes((json.dumps(result,indent=2,sort_keys=True)+"\n").encode("utf-8"))
    print("ACC66_U23_SOURCE=PASS")
    print("ACC66_U23_FOLDS="+str(len(result["folds"])))
    print("ACC66_U23_PREDICTIVE="+result["classification"]["spectral_power_predictor_vs_dev_selected_ngram"])
    print("ACC66_U23_SCIENTIFIC=NOT_GRANTED")

if __name__=="__main__":main()
