"""MP-AI32: exact original P30 canary replay, evaluated under unchanged P31 veto.

This is deliberately exposed DEVELOPMENT regression: no task modification,
new model or tuned guard. P30 original baseline expected 5 hard FP /30,
21 exact labels /30; the replay validates reproduction and applies the
*previously precommitted* P31 guard to the same authentic 30 completions.
The original model prompt/seed/grammar, model GGUF and case iteration are
imported directly from immutable P30 source. No scientifically blind holdout,
no independent human adjudication, no production memory writes.
"""
from __future__ import annotations
from collections import Counter
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import sys
import time

import mpai30_real_semantic_judge_canaries as p30
import mpai31_conservative_semantic_veto_development as p31

P30_BLOB="0fa02bc09fae04f72c49f555fa7063e31f546f6c"
P31_BLOB="97510664d981e3bf70dbcc2f1002fd40945150d4"
P30_ORIGINAL_PROTOCOL="325cd39377bd3dd6e736ac6ccf5c8dc3205420bad92df60c1ba5d4ea03ab0477"
P31_ORIGINAL_PROTOCOL="192c5c7c7678ebc89e4b35ff1ebe7e2b82dbc60b782b8dcc4cbdfd538b3a06bc"
P30_ORIGINAL_RESULTS={
 "exact":{"correct":6,"accepted_yes":6,"hard_false_positives":0},
 "paraphrase":{"correct":6,"accepted_yes":6,"hard_false_positives":0},
 "contradiction":{"correct":6,"accepted_yes":0,"hard_false_positives":0},
 "unrelated":{"correct":2,"accepted_yes":0,"hard_false_positives":0},
 "quoted_disclaimer":{"correct":1,"accepted_yes":5,"hard_false_positives":5},
}
STAGE="INIT"

def check(cond,code):
    if not cond:raise RuntimeError("MPAI32_"+code)
def sha(data):
    return hashlib.sha256(data).hexdigest()
def orig_case_sha():
    return sha(json.dumps(p30.cases(),sort_keys=True,separators=(",",":")).encode())
def prereg_sha():
    return sha(json.dumps({
      "protocol":"MPAI32-original-P30-failure-unchanged-P31-veto-exposed-development-v1",
      "model_sha":p30.MODEL_SHA,
      "p30_original_script_blob":P30_BLOB,
      "p31_original_script_blob":P31_BLOB,
      "p30_original_protocol":P30_ORIGINAL_PROTOCOL,
      "p31_original_protocol":P31_ORIGINAL_PROTOCOL,
      "frozen_original_P30_case_content_sha":orig_case_sha(),
      "original_P30_aggregate_receipts":P30_ORIGINAL_RESULTS,
      "inference": "exact P30 source unchanged",
      "guard": "exact P31 conservative_guard unchanged",
      "same_model_output_comparator":True,
      "max_new_model_completions":30,
      "raw_benchmark_golds_to_model":0,
      "independent_first_use":False,
    },sort_keys=True,separators=(",",":")).encode())
def prereg():
    check(p30.protocol()==P30_ORIGINAL_PROTOCOL,"P30_PROTOCOL_DRIFT")
    check(p31.prereg_digest()==P31_ORIGINAL_PROTOCOL,"P31_PROTOCOL_DRIFT")
    check(len(p30.cases())==30,"P30_CASES_COUNT")
    check(Counter(c[2] for c in p30.cases())=={k:6 for k in p30.KINDS},
          "P30_FROZEN_KIND_COUNTS")
    check(p30.MODEL_SHA==p31.MODEL_SHA and
          p30.MODEL_REV==p31.MODEL_REV and p30.MODEL_BYTES==p31.MODEL_BYTES,
          "MODEL_PIN_DISAGREEMENT")
    # Previously fixed P31 guard, reused without modifications:
    expected=[x for x in p30.cases() if x[2]=="quoted_disclaimer"]
    check(len(expected)==6 and all(p31.veto(x[4]) for x in expected),
          "P31_GUARD_EXPECTED_QUOTE_COVERAGE")
    check(all(not p31.veto(x[4]) for x in p30.cases() if x[5]=="YES"),
          "P31_GUARD_UNEXPECTED_POSITIVE_VETO")
    print("MPAI32_FROZEN_PROTOCOL_SHA256="+prereg_sha(),flush=True)
    print("MPAI32_ORIGINAL_P30_PROTOCOL_VERIFIED=PASS",flush=True)
    print("MPAI32_ORIGINAL_P31_PROTOCOL_VERIFIED=PASS",flush=True)
    print("MPAI32_ORIGINAL_P30_CASES_SHA256="+orig_case_sha(),flush=True)
    print("MPAI32_REPLAY_EXPOSED_DEVELOPMENT_ONLY=TRUE",flush=True)
    print("MPAI32_REPLAY_CANDIDATES=30",flush=True)
    print("MPAI32_SAME_MODEL_OUTPUT_FOR_ALL_COMPARATORS=TRUE",flush=True)
    print("MPAI32_P31_FROZEN_VETO_COVERS_6_EXPOSED_DISCLAIMERS=PASS",flush=True)
    print("MPAI32_P30_ORIGINAL_5_HARD_FP_RECORDED=TRUE",flush=True)
def evaluate(scratch):
    global STAGE
    check(os.name=="nt" and os.getenv("RUNNER_NAME")=="FORGE-CODEX-REMOTE"
          and os.getenv("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE",
          "ORIGINAL_WINDOWS_AUTHORITY")
    check(not os.getenv("OPENAI_API_KEY"),"PAID_API_DENIED")
    check(not scratch.exists() and shutil.disk_usage(scratch.parent).free>3500000000,
          "PRIVATE_SCRATCH_OR_DISK")
    scratch.mkdir()
    STAGE="MODEL_AUTHENTICATE"
    model_path=scratch/p30.MODEL_NAME
    p30.download_model(model_path)
    print("MPAI32_FULL_MODEL_SHA256_VERIFIED=PASS",flush=True)
    os.environ["HF_HUB_OFFLINE"]="1"
    socket.socket=lambda *a,**kw: (_ for _ in ()).throw(
       RuntimeError("MPAI32_INFERENCE_OFFLINE"))
    from llama_cpp import Llama,LlamaGrammar
    # Exactly the parameters of P30; no new prompt or generation budget.
    grammar=LlamaGrammar.from_string('root ::= ("YES" | "NO" | "UNKNOWN")',
                                     verbose=False)
    t=time.perf_counter()
    model=Llama(model_path=str(model_path),n_ctx=2048,n_threads=4,
                n_gpu_layers=0,n_batch=128,seed=p30.SEED,verbose=False)
    load_ms=max(1,int(1000*(time.perf_counter()-t)))
    check(load_ms<=120000,"LOAD_BUDGET")
    STAGE="P30_EXACT_INFERENCE"
    trials=[]
    for i,(_,name,kind,reference,candidate,gold) in enumerate(p30.cases()):
        started=time.perf_counter()
        response=model.create_chat_completion(
             messages=p30.messages(reference,candidate),
             temperature=0,top_p=1,max_tokens=p30.MAX_OUT,grammar=grammar)
        elapsed=max(1,int((time.perf_counter()-started)*1000))
        choices=response.get("choices",[])
        check(len(choices)==1,"MODEL_RESPONSE_SCHEMA")
        raw=choices[0].get("message",{}).get("content","")
        usage=response.get("usage",{})
        pt=int(usage.get("prompt_tokens",0))
        ct=int(usage.get("completion_tokens",0))
        check(isinstance(raw,str) and 0<pt<=1800 and
              0<ct<=p30.MAX_OUT,"MODEL_TOKEN_BOUNDS")
        base=p30.parse(raw)
        guarded=p31.conservative_guard(base,candidate)
        strict=p31.strict_comparator(reference,candidate)
        trials.append({
          "id":i,"kind":kind,"family":name,"gold":gold,
          "baseline":base,"guarded":guarded,"strict":strict,
          "guard_vetoed":bool(base=="YES" and p31.veto(candidate)),
          "tokens":pt+ct,"latency_ms":elapsed,
          "raw_sha256":sha(raw.encode()),
        })
    check(len(trials)==30,"EXACT_MODEL_CALL_DENOMINATOR")
    (scratch/"private_original_canary_replay.json").write_text(
      json.dumps({"protocol":prereg_sha(),"model_sha":p30.MODEL_SHA,
        "is_blinded":False,"is_scientific_win":False,
        "rows":trials},sort_keys=True),encoding="utf-8")
    original_reproduced=True
    for kind in p30.KINDS:
        z=[x for x in trials if x["kind"]==kind]
        check(len(z)==6,"SIX_PER_ORIGINAL_KIND")
        observed={
          "correct":sum(x["baseline"]==x["gold"] for x in z),
          "accepted_yes":sum(x["baseline"]=="YES" for x in z),
          "hard_false_positives":sum(x["baseline"]=="YES" and x["gold"]!="YES" for x in z)}
        reproduced=observed==P30_ORIGINAL_RESULTS[kind]
        original_reproduced &= reproduced
        rec={
          "cases":len(z),
          "original_baseline_correct":observed["correct"],
          "original_baseline_hard_false_positives":observed["hard_false_positives"],
          "guard_correct":sum(x["guarded"]==x["gold"] for x in z),
          "guard_hard_false_positives":sum(x["guarded"]=="YES" and x["gold"]!="YES" for x in z),
          "guard_changed_judgment":sum(x["guarded"]!=x["baseline"] for x in z),
          "strict_correct":sum(x["strict"]==x["gold"] for x in z),
          "reproduced_p30_receipt":reproduced,
          "total_tokens":sum(x["tokens"] for x in z),
          "latency_ms":sum(x["latency_ms"] for x in z),
        }
        print("MPAI32_KIND_"+kind.upper()+"="+json.dumps(
            rec,sort_keys=True,separators=(",",":")),flush=True)
    for key in ("baseline","guarded","strict"):
        fp=sum(x[key]=="YES" and x["gold"]!="YES" for x in trials)
        correct=sum(x[key]==x["gold"] for x in trials)
        supported=sum(x[key]=="YES" and x["gold"]=="YES" for x in trials)
        print("MPAI32_"+key.upper()+"_FALSE_POSITIVES="+str(fp),flush=True)
        print("MPAI32_"+key.upper()+"_CORRECT="+str(correct)+"_OF_30",flush=True)
        print("MPAI32_"+key.upper()+"_SUPPORTED="+str(supported)+"_OF_12",flush=True)
    changes=sum(x["guarded"]!=x["baseline"] for x in trials)
    print("MPAI32_GUARD_CHANGED_DECISIONS="+str(changes),flush=True)
    print("MPAI32_ORIGINAL_P30_RECEIPTS_REPRODUCED="+
          ("PASS" if original_reproduced else "FAIL"),flush=True)
    rawfp=sum(x["baseline"]=="YES" and x["gold"]!="YES" for x in trials)
    guardfp=sum(x["guarded"]=="YES" and x["gold"]!="YES" for x in trials)
    print("MPAI32_GUARD_ZERO_HARD_FALSE_POSITIVES="+(
       "PASS" if guardfp==0 else "FAIL"),flush=True)
    print("MPAI32_GUARD_INCREMENTAL_FALSE_POSITIVES_PREVENTED="+
          str(rawfp-guardfp),flush=True)
    print("MPAI32_REAL_P30_REPLAY_MODEL_CALLS=30",flush=True)
    print("MPAI32_MODEL_LOAD_MS="+str(load_ms),flush=True)
    peak=p30.peak_working_set()
    check(0<peak<6000000000,"PEAK_MEMORY_CAP")
    print("MPAI32_PEAK_WINDOWS_PROCESS_BYTES="+str(peak),flush=True)
    print("MPAI32_HUMAN_INDEPENDENT_ADJUDICATION=FALSE",flush=True)
    print("MPAI32_BENCHMARK_GOLD_MODEL_EXPOSURE=0",flush=True)
    print("MPAI32_PRODUCTION_MEMORY_WRITES=0",flush=True)
    print("MPAI32_EXTERNAL_SCIENTIFIC_FIRST_USE=FALSE",flush=True)
    print("MPAI32_SEMANTIC_JUDGE_SCIENTIFIC_ADMISSION=BLOCKED",flush=True)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--phase",choices=("preregister","evaluate"),required=True)
    args=p.parse_args()
    prereg()
    if args.phase=="preregister":
        print("MPAI32_LINUX_SOURCE_FREEZE=PASS",flush=True)
        print("MPAI32_LINUX_MODEL_CALLS=0",flush=True)
    else:
        evaluate(Path(os.environ["MPAI32_PRIVATE_SCRATCH"]))
if __name__=="__main__":
    try:main()
    except Exception as error:
        code=str(error)
        safe=code if re.fullmatch(r"MPAI32_[A-Z0-9_]{3,100}",code) else "MPAI32_PRIVATE_EXCEPTION"
        print("MPAI32_SAFE_FAILURE="+safe,flush=True)
        print("MPAI32_SAFE_STAGE="+STAGE,flush=True)
        print("MPAI32_SAFE_TYPE="+type(error).__name__,flush=True)
        sys.exit(2)
