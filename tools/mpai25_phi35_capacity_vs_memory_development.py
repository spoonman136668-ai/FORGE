"""MP-AI25: real CPU local-model format vs evidence-use ablation.

The P23/P24 four questions were previously exposed: ONLY development. Phi-3.5 mini MIT 3.8B versus original 1.7B.
Paired three contexts by two fixed output encodings on exactly the same pinned
1.7B model. No performance winner claims, autonomous learning or production.
All private text and model weights remain in temporary scratch, removed by owner.
"""
from __future__ import annotations
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
MODEL_URL="https://huggingface.co/bartowski/Phi-3.5-mini-instruct-GGUF/resolve/"+MODEL_REV+"/"+MODEL_NAME+"?download=true"
LESSONS=(
 "lesson/mpai05-p16-p17-memory-retriever-model-accuracy-no-gain-20261029",
 "lesson/mpai05-uq37-original-scheduled-inspection-repaired-but-idle-20261029",
)
CASES=(
 ("memory-accuracy",LESSONS[0],
  "Did the shorter IDF retrieval context improve the 1.7B model's measured correct-answer count over lexical memory?", "NO"),
 ("retrieval-efficiency",LESSONS[0],
  "Was IDF retrieval more resource-efficient than lexical memory in the recorded experiment?", "YES"),
 ("empty-queue",LESSONS[1],
  "Did a successful scheduled inspection with no authorized queued sources prove that the system autonomously learned?", "NO"),
 ("inspection-recovery",LESSONS[1],
  "Did repairing the guarded poll's source-tree pin restore scheduled source inspection?", "YES"),
)
ARMS=("no_memory","placebo","accepted_memory")
MODES=("free","grammar")
GENERATION_CAP=12
STATUS="INIT"
def check(x,code):
    if not x:raise RuntimeError("MPAI25_"+code)
def sha(b):return hashlib.sha256(b).hexdigest()
def frozen():
    d={"mp":SOURCE_SHA,"records":RECORDS_SHA,"model":MODEL_SHA,
       "cases":CASES,"arms":ARMS,"modes":MODES,"max_output":GENERATION_CAP,
       "seed":137,"score":"exact-yes-no-unknown-v1"}
    return sha(json.dumps(d,sort_keys=True,separators=(",",":")).encode())
def download(out):
    check(not out.exists(),"MODEL_COLLISION")
    d=hashlib.sha256();n=0;t0=time.monotonic()
    req=urllib.request.Request(MODEL_URL,headers={"User-Agent":"MPAI25-original-source-diagnostic/1"})
    with urllib.request.urlopen(req,timeout=55) as src,out.open("xb") as f:
        for b in iter(lambda:src.read(4*1024*1024),b""):
            n+=len(b)
            check(n<=MODEL_BYTES and time.monotonic()-t0<=660,"DOWNLOAD_BOUND")
            d.update(b);f.write(b)
    check(n==MODEL_BYTES and d.hexdigest()==MODEL_SHA,"MODEL_SHA_DRIFT")
    with out.open("rb") as f:check(f.read(4)==b"GGUF","MODEL_HEADER")
def parse_answer(x):
    return x.strip().upper() if re.fullmatch(r"\s*(YES|NO|UNKNOWN)\s*",x,re.I) else None
def messages(question,context):
    return [
      {"role":"system","content":"Using only the evidence provided, answer the yes/no question. "
          "Reply with exactly YES, NO, or UNKNOWN. If the evidence does not establish "
          "an answer, answer UNKNOWN. Do not explain."},
      {"role":"user","content":"Evidence:\n"+context+"\n\nQuestion: "+question},
    ]
def placebo(n,statement):
    prefix="Unrelated source-backed prior event: "+statement+"\n"
    return (prefix*(1+n//len(prefix)))[:n]
def main():
    global STATUS
    check(os.name=="nt" and os.getenv("RUNNER_NAME")=="FORGE-CODEX-REMOTE"
      and os.getenv("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE",
      "ORIGINAL_RUNNER_REQUIRED")
    check(not os.getenv("OPENAI_API_KEY"),"PAID_API_DENIED")
    scratch=Path(os.environ["MPAI25_PRIVATE_SCRATCH"])
    source=Path(os.environ["MPAI25_PRIVATE_SOURCE"])
    check(not scratch.exists() and source.is_dir(),"SCRATCH_SOURCE")
    check(shutil.disk_usage(scratch.parent).free>3400000000,"DISK_BOUND")
    scratch.mkdir()
    STATUS="SOURCE"
    sys.path.insert(0,str(source/"tools"))
    from mindpalace_readonly import MemorySnapshot
    snap=MemorySnapshot(source,SOURCE_SHA,["Mind-Palace"])
    check(snap.records_sha256==RECORDS_SHA,"RECORDS_SHA")
    records={}
    for key in LESSONS:
        x=snap.get_record(SOURCE_SHA,key,["Mind-Palace"])
        check(x.get("found") and x["record"].get("status")=="observed"
              and len(x["record"].get("source_refs",[]))>=2,"SOURCE_PROVENANCE")
        records[key]=x["record"]["statement"]
    bad=snap.get_record(SOURCE_SHA,"lesson/mind-palace-one-command-real-ingestion-20260927",["Mind-Palace"])
    check(bad.get("found"),"PLACEBO_SOURCE")
    unrelated=bad["record"]["statement"]
    context=lambda arm,key: records[key] if arm=="accepted_memory" else (
        placebo(len(records[key]),unrelated) if arm=="placebo" else "")
    print("MPAI25_PINNED_SNAPSHOT_AND_2_RECORDS=PASS",flush=True)
    print("MPAI25_FROZEN_DEVELOPMENT_PROTOCOL_SHA256="+frozen(),flush=True)
    STATUS="MODEL"
    path=scratch/MODEL_NAME
    download(path)
    print("MPAI25_MODEL_FULL_SHA256=PASS",flush=True)
    os.environ["HF_HUB_OFFLINE"]="1"
    socket.socket=lambda *a,**kw: (_ for _ in ()).throw(RuntimeError("MPAI25_NETWORK_DISABLED"))
    from llama_cpp import Llama,LlamaGrammar
    grammar=LlamaGrammar.from_string('root ::= ("YES" | "NO" | "UNKNOWN")',verbose=False)
    t=time.perf_counter()
    llm=Llama(model_path=str(path),n_ctx=3072,n_threads=4,n_gpu_layers=0,n_batch=128,seed=137,verbose=False)
    load_ms=max(1,int((time.perf_counter()-t)*1000))
    check(load_ms<=120000,"MODEL_LOAD_BOUND")
    STATUS="INFERENCE"
    rows=[]
    for index,(task,key,question,gold) in enumerate(CASES):
        arms=ARMS[index%3:]+ARMS[:index%3]
        for arm in arms:
            ctxt=context(arm,key)
            for mode in MODES:
                started=time.perf_counter()
                res=llm.create_chat_completion(messages=messages(question,ctxt),
                      temperature=0,top_p=1,max_tokens=GENERATION_CAP,
                      grammar=grammar if mode=="grammar" else None)
                elapsed=max(1,int((time.perf_counter()-started)*1000))
                choices=res.get("choices",[])
                check(len(choices)==1,"COMPLETION_SCHEMA")
                answer=choices[0].get("message",{}).get("content","")
                usage=res.get("usage",{})
                inp=int(usage.get("prompt_tokens",0));out=int(usage.get("completion_tokens",0))
                check(isinstance(answer,str) and 0<inp<=2600 and 0<out<=GENERATION_CAP,
                     "TOKEN_BOUND")
                chosen=parse_answer(answer)
                rows.append({"task":task,"arm":arm,"mode":mode,
                     "correct":chosen==gold,"abstained":chosen=="UNKNOWN",
                     "format_valid":chosen is not None,
                     "unparseable":chosen is None,
                     "completion_tokens":out,"prompt_tokens":inp,
                     "latency_ms":elapsed,
                     "context_chars":len(ctxt),
                     "context_sha256":sha(ctxt.encode()),
                     "private_response_sha256":sha(answer.encode())})
    check(len(rows)==len(CASES)*len(ARMS)*len(MODES),"TRIAL_COUNT")
    (scratch/"private_trial.json").write_text(json.dumps(
       {"source_sha":SOURCE_SHA,"model_sha":MODEL_SHA,"protocol_sha":frozen(),
        "development_only":True,"all_trials":rows},sort_keys=True),encoding="utf-8")
    for mode in MODES:
        for arm in ARMS:
            z=[r for r in rows if r["mode"]==mode and r["arm"]==arm]
            check(len(z)==4,"ARM_DENOMINATOR")
            summary={"calls":len(z),"correct":sum(x["correct"] for x in z),
               "abstained":sum(x["abstained"] for x in z),
               "unparseable":sum(x["unparseable"] for x in z),
               "tokens":sum(x["prompt_tokens"]+x["completion_tokens"] for x in z),
               "inference_ms":sum(x["latency_ms"] for x in z),
               "context_chars":sum(x["context_chars"] for x in z)}
            print("MPAI25_"+mode.upper()+"_"+arm.upper()+"="+json.dumps(
               summary,sort_keys=True,separators=(",",":")),flush=True)
    # Resource bound to the existing original Windows workstation.
    import ctypes
    from ctypes import wintypes
    class PMC(ctypes.Structure):
        _fields_=[("cb",wintypes.DWORD),("PageFaultCount",wintypes.DWORD),
            ("PeakWorkingSetSize",ctypes.c_size_t),("WorkingSetSize",ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage",ctypes.c_size_t),("QuotaPagedPoolUsage",ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage",ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage",ctypes.c_size_t),
            ("PagefileUsage",ctypes.c_size_t),("PeakPagefileUsage",ctypes.c_size_t)]
    pmc=PMC()
    pmc.cb=ctypes.sizeof(pmc)
    k=ctypes.WinDLL("kernel32",use_last_error=True)
    p=ctypes.WinDLL("psapi",use_last_error=True)
    k.GetCurrentProcess.restype=wintypes.HANDLE
    p.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(PMC),wintypes.DWORD]
    p.GetProcessMemoryInfo.restype=wintypes.BOOL
    check(bool(p.GetProcessMemoryInfo(k.GetCurrentProcess(),ctypes.byref(pmc),pmc.cb)),"MEMORY_COUNTER")
    peak=int(pmc.PeakWorkingSetSize)
    check(0<peak<=6000000000,"PEAK_MEMORY_BUDGET")
    print("MPAI25_PEAK_WORKING_SET_BYTES="+str(peak),flush=True)
    print("MPAI25_MODEL_LOAD_MS="+str(load_ms),flush=True)
    print("MPAI25_REAL_LOCAL_MODEL_CALLS="+str(len(rows)),flush=True)
    print("MPAI25_OFFLINE_INFERENCE=PASS",flush=True)
    print("MPAI25_PUBLIC_DEVELOPMENT_ONLY=TRUE",flush=True)
    print("MPAI25_FIRST_USE_HOLDOUT=FALSE",flush=True)
    print("MPAI25_SCIENTIFIC_ACCEPTANCE=FALSE",flush=True)
    print("MPAI25_PRODUCTION_WRITES=0",flush=True)
if __name__=="__main__":
    try:main()
    except Exception as exc:
        v=str(exc)
        print("MPAI25_SAFE_FAILURE="+(v if re.fullmatch(r"MPAI25_[A-Z0-9_]{3,70}",v)
             else "MPAI25_PRIVATE_EXCEPTION"),flush=True)
        print("MPAI25_SAFE_STAGE="+STATUS,flush=True)
        print("MPAI25_SAFE_ERROR_TYPE="+type(exc).__name__,flush=True)
        sys.exit(2)
