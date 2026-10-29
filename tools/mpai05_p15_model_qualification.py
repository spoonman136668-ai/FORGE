"""MP-AI05 P15 — stronger non-Qwen local model custody + fresh public dev cohort.

Source-only official P9 data selection excludes the *entire* already exposed
P9/P10-P14 sixteen-case cohort. No gold/answer/question is read to select.
Verifies 1.7B Apache-2.0 public GGUF exact commit, bytes and full SHA-256,
then runs ONE PUBLIC ARITHMETIC SMOKE off-network. Original Windows only.
No model benchmark accuracy, held-out science, autonomous writer or scheduler.
"""
from __future__ import annotations

from collections import Counter
import ctypes
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

import mpai05_p9_dataset_freeze as p9

PUBLIC_MODEL_REPO="bartowski/SmolLM2-1.7B-Instruct-GGUF"
MODEL_REVISION="72da00985aa7cb57cd436a6172be99c3bd906d9c"
MODEL_FILE="SmolLM2-1.7B-Instruct-Q4_K_M.gguf"
MODEL_SHA256="77665ea4815999596525c636fbeb56ba8b080b46ae85efef4f0d986a139834d7"
MODEL_EXACT_BYTES=1055609824
MODEL_LICENSE="apache-2.0"
MODEL_URL=(f"https://huggingface.co/{PUBLIC_MODEL_REPO}/resolve/{MODEL_REVISION}/"
           f"{MODEL_FILE}?download=true")
PRIOR_COHORT_SHA="103dbf87dda69f03b32f4c6a3a987b5ab5b7a8d3c3ceeb11f223ad5cf358ae52"
NEW_COHORT_SEED="MPAI05-P15-NEW-PUBLIC-DEVELOPMENT-COHORT-v1"
COUNT_BY_DOMAIN={"web":8,"enterprise":8}
MAX_CPU_INFERENCE_SECONDS=120
MAX_PEAK_WORKING_SET_BYTES=5000000000
STATE="INITIAL"

def require(ok:bool,code:str):
    if not ok: raise RuntimeError("MPAI05_P15_"+code)

def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def new_cohort(rows:list[dict],small:dict)->dict:
    # P9 independently authenticates 451 public question records, all source
    # identities and the list of 100 per-question trajectory IDs.
    previous=p9.choose(rows,small)
    require(previous["cohort_sha256"]==PRIOR_COHORT_SHA,"PRIOR_COHORT_DRIFT")
    old={r["id"] for r in previous["cohort"]}
    selections=[]
    for domain,count in COUNT_BY_DOMAIN.items():
        candidates=[]
        for row in rows:
            if (row["domain"]!=domain or row.get("image") is not None or
                row["id"] in old):
                continue
            # No gold, answer, question text, evaluation function or actual
            # trajectory text is read for cohort selection.
            key=sha((NEW_COHORT_SEED+"|"+row["id"]).encode("utf-8"))
            candidates.append((key,row["id"],row["question_type"]))
        candidates.sort()
        require(len(candidates)>=count,"INSUFFICIENT_NEW_CASES")
        for _,qid,kind in candidates[:count]:
            trajectories=small[qid]
            require(type(trajectories) is list and len(trajectories)==100
                and len(set(trajectories))==100,"SMALL_HAYSTACK_DRIFT")
            selections.append({"id":qid,"domain":domain,"kind":kind,
                 "haystack_ids_sha256":sha(json.dumps(trajectories,
                     separators=(",",":"),ensure_ascii=True).encode("utf-8"))})
    selections.sort(key=lambda r:(r["domain"],r["id"]))
    require(len(selections)==16 and
            len({r["id"] for r in selections})==16 and
            not ({r["id"] for r in selections}&old),"P15_P9_COHORT_OVERLAP")
    families={p9.FAMILIES[r["kind"]] for r in selections}
    require(len(families)>=3,"INSUFFICIENT_FAMILY_COVERAGE")
    raw=json.dumps(selections,sort_keys=True,separators=(",",":")).encode("utf-8")
    return {"digest":sha(raw),"selected":selections,
            "domain_counts":dict(sorted(Counter(r["domain"] for r in selections).items())),
            "family_counts":dict(sorted(Counter(p9.FAMILIES[r["kind"]] for r in selections).items())),
            "prior_excluded":len(old),"overlap":0}

def download_model(path:Path):
    require(not path.exists(),"MODEL_DESTINATION_COLLISION")
    start=time.monotonic()
    h=hashlib.sha256()
    n=0
    req=urllib.request.Request(MODEL_URL,
        headers={"User-Agent":"MindPalace-P15-frozen-public-check/1"})
    with urllib.request.urlopen(req,timeout=50) as source,path.open("xb") as out:
        # Allow only an EXACT declared model size; bound the duration and
        # number of bytes. Nothing fetched from public moving "main".
        while True:
            chunk=source.read(4*1024*1024)
            if not chunk: break
            n+=len(chunk)
            require(n<=MODEL_EXACT_BYTES and time.monotonic()-start<650,
                    "MODEL_DOWNLOAD_BOUND")
            h.update(chunk)
            out.write(chunk)
    require(n==MODEL_EXACT_BYTES and h.hexdigest()==MODEL_SHA256,
            "MODEL_BYTES_OR_FULL_SHA256_DRIFT")
    with path.open("rb") as f:
        require(f.read(4)==b"GGUF","NOT_GGUF")

def windows_peak_working_set()->int:
    # Native process memory accounting includes C/C++ GGUF allocations,
    # unlike Python tracemalloc. Original runner must be Windows.
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_=[("cb",wintypes.DWORD),("PageFaultCount",wintypes.DWORD),
          ("PeakWorkingSetSize",ctypes.c_size_t),("WorkingSetSize",ctypes.c_size_t),
          ("QuotaPeakPagedPoolUsage",ctypes.c_size_t),
          ("QuotaPagedPoolUsage",ctypes.c_size_t),
          ("QuotaPeakNonPagedPoolUsage",ctypes.c_size_t),
          ("QuotaNonPagedPoolUsage",ctypes.c_size_t),
          ("PagefileUsage",ctypes.c_size_t),
          ("PeakPagefileUsage",ctypes.c_size_t)]
    measure=Counters()
    measure.cb=ctypes.sizeof(measure)
    kernel=ctypes.WinDLL("kernel32",use_last_error=True)
    psapi=ctypes.WinDLL("psapi",use_last_error=True)
    kernel.GetCurrentProcess.restype=wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),
                                         wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype=wintypes.BOOL
    ok=psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),
                                  ctypes.byref(measure),measure.cb)
    require(ok,"WINDOWS_MEMORY_READ_FAILED")
    return int(measure.PeakWorkingSetSize)

def smoke(path:Path):
    from llama_cpp import Llama
    started=time.perf_counter()
    model=Llama(model_path=str(path),n_ctx=2048,n_threads=4,n_gpu_layers=0,
                n_batch=128,seed=137,verbose=False)
    loaded_ms=max(1,int((time.perf_counter()-started)*1000))
    require(loaded_ms<=120000,"MODEL_LOAD_TIME_LIMIT")
    started=time.perf_counter()
    result=model.create_chat_completion(
        messages=[{"role":"system","content":"Give a short numeric answer."},
                  {"role":"user","content":"What is seven plus five?"}],
        temperature=0,top_p=1,max_tokens=24)
    inference_ms=max(1,int((time.perf_counter()-started)*1000))
    usage=result.get("usage",{})
    answer=result.get("choices",[{}])[0].get("message",{}).get("content","")
    require(type(answer) is str and answer.strip() and
            type(usage) is dict and
            0<int(usage.get("completion_tokens",0))<=24 and
            0<int(usage.get("prompt_tokens",0))<=1024,
            "PUBLIC_SMOKE_RECEIPT_INVALID")
    peak=windows_peak_working_set()
    require(inference_ms<=MAX_CPU_INFERENCE_SECONDS*1000,"SMOKE_CPU_TIME_LIMIT")
    require(0<peak<=MAX_PEAK_WORKING_SET_BYTES,"PEAK_MEMORY_LIMIT")
    print("MPAI05_P15_PUBLIC_SMOKE_CALLS=1")
    print("MPAI05_P15_LOCAL_RUNTIME=PASS")
    print("MPAI05_P15_LOAD_MS="+str(loaded_ms))
    print("MPAI05_P15_INFERENCE_MS="+str(inference_ms))
    print("MPAI05_P15_PROMPT_TOKENS="+str(usage["prompt_tokens"]))
    print("MPAI05_P15_COMPLETION_TOKENS="+str(usage["completion_tokens"]))
    print("MPAI05_P15_PEAK_WORKING_SET_BYTES="+str(peak))
    # Intentionally never publishes the answer text or hidden/task data.
    print("MPAI05_P15_PUBLIC_ANSWER_NONEMPTY=PASS")

def main():
    global STATE
    require(os.environ.get("RUNNER_NAME")=="FORGE-CODEX-REMOTE" and
            os.environ.get("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE",
            "WRONG_ORIGINAL_RUNNER")
    require(os.name=="nt","WINDOWS_REQUIRED")
    require(not os.environ.get("OPENAI_API_KEY"),"PAID_API_KEY_PROHIBITED")
    root=Path(os.environ["MPAI05_P15_SCRATCH"])
    require(not root.exists(),"SCRATCH_COLLISION")
    require(shutil.disk_usage(root.parent).free>=2400000000,"DISK_CAPACITY")
    root.mkdir()
    STATE="FROZEN_PUBLIC_COHORT"
    raw={name:p9.download(name) for name in (
        "checksums.sha256","SCHEMA.md","questions.jsonl",
        "haystacks/lme_v2_small.json")}
    previous=p9.freeze(raw["questions.jsonl"],
        raw["haystacks/lme_v2_small.json"],
        raw["SCHEMA.md"],raw["checksums.sha256"])
    require(previous["cohort_sha256"]==PRIOR_COHORT_SHA,"PRIOR_SOURCE_DRIFT")
    rows=[json.loads(z) for z in raw["questions.jsonl"].decode("utf-8").splitlines() if z.strip()]
    small=json.loads(raw["haystacks/lme_v2_small.json"])
    selected=new_cohort(rows,small)
    print("MPAI05_P15_PUBLIC_DATA_SHA256=PASS")
    print("MPAI05_P15_PRIOR_COHORT_EXCLUDED=16")
    print("MPAI05_P15_NEW_COHORT_SHA256="+selected["digest"])
    print("MPAI05_P15_NEW_COHORT_CASES=16")
    print("MPAI05_P15_WEB="+str(selected["domain_counts"]["web"]))
    print("MPAI05_P15_ENTERPRISE="+str(selected["domain_counts"]["enterprise"]))
    print("MPAI05_P15_COHORT_OVERLAP=0")
    print("MPAI05_P15_NEW_FAMILIES="+str(len(selected["family_counts"])))
    STATE="MODEL_HASH"
    path=root/MODEL_FILE
    download_model(path)
    print("MPAI05_P15_MODEL_FULL_SHA256=PASS")
    print("MPAI05_P15_MODEL_BYTES="+str(MODEL_EXACT_BYTES))
    print("MPAI05_P15_MODEL_ORIGINAL_COMMIT="+MODEL_REVISION)
    STATE="LOCAL_OFFLINE_SMOKE"
    os.environ["HF_HUB_OFFLINE"]="1"
    def network_denied(*args,**kwargs):
        raise RuntimeError("MPAI05_P15_NETWORK_AFTER_MODEL_DOWNLOAD_DENIED")
    socket.socket=network_denied
    smoke(path)
    print("MPAI05_P15_PUBLIC_DEVELOPMENT_ONLY=TRUE")
    print("MPAI05_P15_FIRST_USE_HOLDOUT=FALSE")
    print("MPAI05_P15_SCIENTIFIC_ACCEPTANCE=FALSE")
    print("MPAI05_P15_PRODUCTION_MEMORY_WRITES=0")
    print("MPAI05_P15_MODEL_PROMOTION=FALSE")

if __name__=="__main__":
    try:main()
    except Exception as exc:
        msg=str(exc)
        reason=msg if re.fullmatch(r"MPAI05_P15_[A-Z0-9_]{3,100}",msg) else "PRIVATE_EXCEPTION"
        print("MPAI05_P15_SAFE_FAILURE="+reason,flush=True)
        print("MPAI05_P15_SAFE_STAGE="+STATE,flush=True)
        print("MPAI05_P15_SAFE_EXCEPTION="+type(exc).__name__,flush=True)
        sys.exit(2)
