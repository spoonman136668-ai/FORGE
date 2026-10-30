"""MP-AI26: novel development questions from 4 distinct accepted memory lessons.

Original Windows source-pinned 3.8B GGUF, actual independent local model inference.
Protocol frozen before any of these specific task questions are run through model.
THIS IS NOT an independently blinded/externally witnessed first-use holdout:
questions come from exposed accepted lessons; no scientific generalization claim.
No production writes, no new controller, no paid APIs, no silent model promotion.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import sys
import time
import urllib.request

SOURCE_SHA="84ad556910c869afa2f171673d5a5b4041a4a9b4"
RECORDS_SHA="3a377f825ad6da28d2c85534337ce831441295ee662e7f4b869f6c565d9e4f83"
MODEL_SHA="e4165e3a71af97f1b4820da61079826d8752a2088e313af0c7d346796c38eff5"
MODEL_BYTES=2393232672
MODEL_REV="b1693692c4758ac83f0d0e65aff9b4f945f29941"
MODEL_NAME="Phi-3.5-mini-instruct-Q4_K_M.gguf"
MODEL_URL=("https://huggingface.co/bartowski/Phi-3.5-mini-instruct-GGUF/resolve/"
           +MODEL_REV+"/"+MODEL_NAME+"?download=true")
LESSONS=(
 "lesson/mpai05-p16-p17-memory-retriever-model-accuracy-no-gain-20261029",
 "lesson/mpai05-uq37-original-scheduled-inspection-repaired-but-idle-20261029",
 "lesson/mpai-hindsight-h2-development-context-efficiency-20261028",
 "decision/mp-ai-00-universal-agentic-improvement",
)
# New task questions NOT used in P23/P24/P25; two per original source family.
# Family-level holdout is impossible from these already public-to-this-agent
# records: annotate as development-only cross-source near transfer.
QUESTIONS=(
 ("p16-promotion",0,"Can the reported IDF-diverse approach be promoted as a proven answer-accuracy improvement over lexical retrieval?", "NO"),
 ("p16-lexical-score",0,"On the 1.7B P16 model, did lexical retrieval achieve more correct answers than IDF-diverse retrieval?", "YES"),
 ("uq37-learning",1,"Does a repaired UQ37 scheduled check with no queued source prove experience was durably learned?", "NO"),
 ("uq37-guard",1,"If the private tool-tree pin unexpectedly changes, should the source boundary fail closed until authenticated repair?", "YES"),
 ("h2-token-economy",2,"Did tiered context retrieval use fewer measured input tokens than legacy retrieval in the reported eight-question comparison?", "YES"),
 ("h2-accuracy",2,"Does that bounded context-efficiency result independently demonstrate improved factual accuracy?", "NO"),
 ("charter-criteria",3,"Does the MP-AI00 north star call for reproducing task improvement on unfamiliar tasks or efficiency versus matched baselines?", "YES"),
 ("charter-authority",3,"Does the MP-AI00 charter by itself authorize new execution, ingestion, scientific acceptance or promotion?", "NO"),
)
ARMS=("none","source_matched_placebo","accepted_memory")
MAX_OUTPUT=12
SEED=137
STAGE="INITIAL"
def need(v,code):
    if not v: raise RuntimeError("MPAI26_"+code)
def digest(data):return hashlib.sha256(data).hexdigest()
def protocol_sha():
    return digest(json.dumps({
        "accepted":SOURCE_SHA,"records":RECORDS_SHA,
        "model_sha":MODEL_SHA,"questions":QUESTIONS,
        "arm_order":ARMS,"model_seed":SEED,
        "generation_tokens":MAX_OUTPUT,"prompt":"mpai26-yes-no-unknown-v1",
        "token_match":"within_3_token_full_prompt_bound",
        "validation":"exact_yes_no_unknown",
    },sort_keys=True,separators=(",",":")).encode())
def provenance(source):
    sys.path.insert(0,str(source/"tools"))
    from mindpalace_readonly import MemorySnapshot
    snap=MemorySnapshot(source,SOURCE_SHA,["Mind-Palace"])
    need(snap.records_sha256==RECORDS_SHA,"SNAPSHOT_DIGEST")
    records={}
    for key in LESSONS:
        found=snap.get_record(SOURCE_SHA,key,["Mind-Palace"])
        need(found.get("found"),"RECORD_MISSING")
        rec=found["record"]
        need(rec["id"]==key and rec["status"]=="observed" and
             len(rec.get("source_refs",[]))>=2, "RECORD_SOURCE_PROVENANCE")
        records[key]=rec["statement"]
    other=snap.get_record(SOURCE_SHA,"lesson/mind-palace-one-command-real-ingestion-20260927",["Mind-Palace"])
    need(other.get("found"),"PLACEBO_SOURCE")
    return records, other["record"]["statement"]
def assert_protocol():
    need(len(QUESTIONS)==8 and len(LESSONS)==4 and len(ARMS)==3,"PROTOCOL_COUNTS")
    need(len({x[0] for x in QUESTIONS})==8,"QUESTION_UNIQUENESS")
    need(Counter(x[1] for x in QUESTIONS)=={0:2,1:2,2:2,3:2},"SOURCE_FAMILIES")
    need(Counter(x[3] for x in QUESTIONS)=={"YES":4,"NO":4},"LABEL_BALANCE")
    need(set(x[1] for x in QUESTIONS)==set(range(4)),"SOURCE_COHORT")
    print("MPAI26_PROTOCOL_SHA256="+protocol_sha(),flush=True)
    print("MPAI26_SOURCE_FAMILIES=4",flush=True)
    print("MPAI26_NEW_DEVELOPMENT_TASKS=8",flush=True)
    print("MPAI26_LABEL_BALANCE=4_YES_4_NO",flush=True)
    print("MPAI26_FIRST_USE_INDEPENDENT_CUSTODY=FALSE",flush=True)
def download(path):
    need(not path.exists(),"MODEL_COLLISION")
    t=time.monotonic()
    req=urllib.request.Request(MODEL_URL,
        headers={"User-Agent":"MPAI26-original-public-model-development/1"})
    h=hashlib.sha256();size=0
    with urllib.request.urlopen(req,timeout=55) as src,path.open("xb") as out:
        while True:
            data=src.read(4*1024*1024)
            if not data:break
            size+=len(data)
            need(size<=MODEL_BYTES and time.monotonic()-t<650,"MODEL_BYTES_OR_TIME_CAP")
            h.update(data);out.write(data)
    need(size==MODEL_BYTES and h.hexdigest()==MODEL_SHA,"MODEL_SHA256")
    with path.open("rb") as src:need(src.read(4)==b"GGUF","MODEL_GGUF_HEADER")
def parse(x):
    return x.strip().upper() if re.fullmatch(r"\s*(YES|NO|UNKNOWN)\s*",x,re.I) else None
def msgs(ctx,question):
    return [
      {"role":"system","content":"Answer with exactly YES, NO or UNKNOWN, nothing else. "
       "Use only provided evidence; if it does not establish an answer, choose UNKNOWN."},
      {"role":"user","content":"Evidence:\n"+ctx+"\n\nQuestion: "+question}
    ]
def placebo(model,target,unrelated,question):
    # Match actual chat prompt-token length, not character count.
    # Select a prefix only of an unrelated authentic record with content
    # repeated as needed; no authored fake events or target-fact hints.
    seed="Unrelated archived project history: "+unrelated+"\n"
    target_tokens=len(model.tokenize(
        ("Evidence:\n"+target+"\n\nQuestion: "+question).encode("utf-8"),add_bos=False))
    def build(n):
        x=(seed*(1+n//len(seed)))[:n]
        return x
    def tok(n):
        return len(model.tokenize(
            ("Evidence:\n"+build(n)+"\n\nQuestion: "+question).encode("utf-8"),add_bos=False))
    low=0;high=min(16000,max(len(target)*5,160))
    while low<high:
        mid=(low+high)//2
        if tok(mid)<target_tokens:low=mid+1
        else:high=mid
    window=range(max(0,low-55),min(16000,low+56))
    n=min(window,key=lambda c:(abs(tok(c)-target_tokens),c))
    result=build(n)
    need(abs(tok(n)-target_tokens)<=2,"PLACEBO_TOKEN_BUDGET_NOT_MATCHED")
    need(result and target and result!=target,"PLACEBO_VALUE_IDENTITY")
    return result
def peak_working_set():
    import ctypes
    from ctypes import wintypes
    class M(ctypes.Structure):
        _fields_=[("cb",wintypes.DWORD),("PageFaultCount",wintypes.DWORD),
           ("PeakWorkingSetSize",ctypes.c_size_t),("WorkingSetSize",ctypes.c_size_t),
           ("QuotaPeakPagedPoolUsage",ctypes.c_size_t),("QuotaPagedPoolUsage",ctypes.c_size_t),
           ("QuotaPeakNonPagedPoolUsage",ctypes.c_size_t),
           ("QuotaNonPagedPoolUsage",ctypes.c_size_t),
           ("PagefileUsage",ctypes.c_size_t),("PeakPagefileUsage",ctypes.c_size_t)]
    x=M();x.cb=ctypes.sizeof(x)
    k=ctypes.WinDLL("kernel32",use_last_error=True)
    p=ctypes.WinDLL("psapi",use_last_error=True)
    k.GetCurrentProcess.restype=wintypes.HANDLE
    p.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(M),wintypes.DWORD]
    p.GetProcessMemoryInfo.restype=wintypes.BOOL
    need(p.GetProcessMemoryInfo(k.GetCurrentProcess(),ctypes.byref(x),x.cb),"MEMORY_COUNTER")
    return int(x.PeakWorkingSetSize)
def main():
    global STAGE
    need(os.name=="nt" and os.getenv("RUNNER_NAME")=="FORGE-CODEX-REMOTE"
      and os.getenv("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE",
      "ORIGINAL_WINDOWS_RUNNER")
    need(not os.getenv("OPENAI_API_KEY"),"PAID_API_DENIED")
    scratch=Path(os.environ["MPAI26_PRIVATE_SCRATCH"])
    source=Path(os.environ["MPAI26_PRIVATE_SOURCE"])
    need(not scratch.exists() and source.is_dir(),"SCRATCH_OR_SOURCE")
    need(shutil.disk_usage(scratch.parent).free>=3500000000,"DISK_BUDGET")
    assert_protocol()
    STAGE="ACCEPTED_MEMORY"
    records,unrelated=provenance(source)
    scratch.mkdir()
    print("MPAI26_SOURCE_AND_FOUR_LESSONS_VERIFIED=PASS",flush=True)
    STAGE="MODEL_DOWNLOAD"
    model_path=scratch/MODEL_NAME
    download(model_path)
    print("MPAI26_MODEL_FULL_SHA256=PASS",flush=True)
    os.environ["HF_HUB_OFFLINE"]="1"
    socket.socket=lambda *a,**kw: (_ for _ in ()).throw(RuntimeError("MPAI26_NETWORK_DISABLED"))
    from llama_cpp import Llama,LlamaGrammar
    g=LlamaGrammar.from_string('root ::= ("YES" | "NO" | "UNKNOWN")',verbose=False)
    t0=time.perf_counter()
    model=Llama(model_path=str(model_path),n_ctx=3072,n_threads=4,
                n_gpu_layers=0,n_batch=128,seed=SEED,verbose=False)
    load_ms=int(1000*(time.perf_counter()-t0))
    need(load_ms<120000,"MODEL_LOAD_BUDGET")
    STAGE="PROMPT_FREEZE"
    contexts=[]
    for cid,family,question,gold in QUESTIONS:
        original=records[LESSONS[family]]
        control=placebo(model,original,unrelated,question)
        contexts.append((cid,question,gold,{"none":"","source_matched_placebo":control,
                    "accepted_memory":original}))
    print("MPAI26_REAL_TOKEN_PARITY_PREINFERENCE=PASS",flush=True)
    STAGE="INFERENCE"
    trials=[]
    for i,(cid,question,gold,arms) in enumerate(contexts):
        order=ARMS[i%3:]+ARMS[:i%3]
        for arm in order:
            ctx=arms[arm]
            start=time.perf_counter()
            response=model.create_chat_completion(messages=msgs(ctx,question),temperature=0,
                           top_p=1,max_tokens=MAX_OUTPUT,grammar=g)
            elapsed=max(1,int(1000*(time.perf_counter()-start)))
            choices=response.get("choices",[]);usage=response.get("usage",{})
            need(len(choices)==1 and isinstance(usage,dict),"INFERENCE_SCHEMA")
            answer=choices[0].get("message",{}).get("content","")
            pt=int(usage.get("prompt_tokens",0));ct=int(usage.get("completion_tokens",0))
            need(type(answer) is str and 0<pt<=3000 and 0<ct<=MAX_OUTPUT,"INFERENCE_TOKENS")
            result=parse(answer)
            trials.append({"case":cid,"family":i//2,"arm":arm,
              "decision":result,"correct":result==gold,"abstained":result=="UNKNOWN",
              "unparseable":result is None,"prompt_tokens":pt,"completion_tokens":ct,
              "latency_ms":elapsed,"context_chars":len(ctx),
              "context_sha256":digest(ctx.encode()),"response_sha256":digest(answer.encode())})
    need(len(trials)==24,"TRIAL_COUNT")
    # The model is not passed GOLD; score comparisons only after generation.
    for cid,_,_,a in contexts:
        z={x["arm"]:x for x in trials if x["case"]==cid}
        need(len(z)==3,"PAIR_COVERAGE")
        delta=abs(z["source_matched_placebo"]["prompt_tokens"]-
                  z["accepted_memory"]["prompt_tokens"])
        need(delta<=3,"ACTUAL_PROMPT_TOKEN_PARITY")
    print("MPAI26_ACTUAL_FULL_PROMPT_TOKEN_PARITY=PASS",flush=True)
    (scratch/"private_trial.json").write_text(json.dumps(
        {"study":"development_only_nonindependent","protocol_sha":protocol_sha(),
         "source_sha":SOURCE_SHA,"model_sha":MODEL_SHA,"trials":trials},
        sort_keys=True),encoding="utf-8")
    for arm in ARMS:
        subset=[x for x in trials if x["arm"]==arm]
        need(len(subset)==8,"ARM_COVERAGE")
        agg={"calls":len(subset),"correct":sum(x["correct"] for x in subset),
          "abstentions":sum(x["abstained"] for x in subset),
          "unparseable":sum(x["unparseable"] for x in subset),
          "tokens":sum(x["prompt_tokens"]+x["completion_tokens"] for x in subset),
          "wall_ms":sum(x["latency_ms"] for x in subset)}
        print("MPAI26_ARM_"+arm.upper()+"="+json.dumps(agg,sort_keys=True,separators=(",",":")),flush=True)
    for fam in range(4):
        matched=[x for x in trials if x["arm"]=="accepted_memory" and x["family"]==fam]
        print("MPAI26_SOURCE_FAMILY_"+str(fam+1)+"_ACCURACY="+str(sum(x["correct"] for x in matched))+"_OF_2",flush=True)
    mem=peak_working_set()
    need(0<mem<=6000000000,"PEAK_WORKING_SET_CAP")
    print("MPAI26_ORIGINAL_WINDOWS_PEAK_WORKING_SET="+str(mem),flush=True)
    print("MPAI26_MODEL_LOAD_MS="+str(load_ms),flush=True)
    print("MPAI26_REAL_LOCAL_MODEL_CALLS=24",flush=True)
    print("MPAI26_DISTINCT_LESSON_SOURCE_FAMILIES=4",flush=True)
    print("MPAI26_INDEPENDENT_BLIND_HOLDOUT=FALSE",flush=True)
    print("MPAI26_NOVEL_ENVIRONMENT_TRANSFER=NOT_PROVEN",flush=True)
    print("MPAI26_SCIENTIFIC_ACCEPTANCE=FALSE",flush=True)
    print("MPAI26_AUTONOMOUS_AGENT_LEARNING=NOT_PROVEN",flush=True)
    print("MPAI26_PRODUCTION_MEMORY_WRITES=0",flush=True)
if __name__=="__main__":
    try:main()
    except Exception as exc:
        v=str(exc)
        code=v if re.fullmatch(r"MPAI26_[A-Z0-9_]{3,100}",v) else "MPAI26_PRIVATE_EXCEPTION"
        print("MPAI26_SAFE_FAILURE="+code,flush=True)
        print("MPAI26_SAFE_STAGE="+STAGE,flush=True)
        print("MPAI26_SAFE_ERROR_TYPE="+type(exc).__name__,flush=True)
        sys.exit(2)
