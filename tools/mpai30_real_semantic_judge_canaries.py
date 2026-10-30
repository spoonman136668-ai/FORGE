"""MP-AI30: bounded real local semantic-judge falsification.

30 preregistered authored *synthetic* cases cover synonyms, contradictions,
unsupported claims, and quoted/disclaimed reference facts. No original public
benchmark question/gold is shown to model, no reported independent human grades.
Qualify or reject a candidate judge; do NOT relabel official benchmark score.
No paid APIs, production writer, controller or scientific promotion.
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

MODEL_SHA="e4165e3a71af97f1b4820da61079826d8752a2088e313af0c7d346796c38eff5"
MODEL_BYTES=2393232672
MODEL_REV="b1693692c4758ac83f0d0e65aff9b4f945f29941"
MODEL_NAME="Phi-3.5-mini-instruct-Q4_K_M.gguf"
MODEL_URL=("https://huggingface.co/bartowski/Phi-3.5-mini-instruct-GGUF/resolve/"+
           MODEL_REV+"/"+MODEL_NAME+"?download=true")
OLD_SELECTION_SHA="6ddf3d30019f102f2d2f820be69c1b0478a71f8e7cd1ea6733c5ee07ab29bb85"
# Authored declarative case labeling; NOT independently adjudicated or first use.
TOPICS=(
 ("relocation","Maya moved to Boston in 2022.",
  "In 2022 Maya relocated to Boston.",
  "Maya remained in Denver in 2022 and never moved to Boston.",
  "The company bought new computers in 2022."),
 ("approval","The committee approved the launch on April 14.",
  "On April 14 the launch received approval from the committee.",
  "The committee rejected the launch on April 14.",
  "The accountant filed taxes on April 14."),
 ("weight","The parcel weighed twelve kilograms.",
  "The package had a weight of 12 kg.",
  "The parcel weighed twenty-one kilograms instead of twelve.",
  "The parcel was shipped on a Friday."),
 ("borrowed","Jonah lent Ava the blue notebook.",
  "Ava borrowed Jonah's blue notebook.",
  "Ava lent Jonah the blue notebook, not the other way around.",
  "Jonah purchased a red binder."),
 ("recovery","Restarting the service restored the system.",
  "The system recovered following a service restart.",
  "Even after restarting the service the system remained down.",
  "A firmware update was scheduled for next Tuesday."),
 ("schedule","The meeting moved from Monday to Wednesday.",
  "They rescheduled the meeting from Monday over to Wednesday.",
  "The meeting was moved from Wednesday to Monday instead.",
  "The meeting was hosted over a video call."),
)
# Expected labels are never in judge model inputs. For unsupported claims,
# UNKNOWN or NO both safe (do not award credit); score abstention separately.
KINDS=("exact","paraphrase","contradiction","unrelated","quoted_disclaimer")
SEED=137
MAX_OUT=8
STAGE="INIT"

def must(v,reason):
    if not v:raise RuntimeError("MPAI30_"+reason)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def protocol():
    return sha(json.dumps({"model":MODEL_SHA,"model_rev":MODEL_REV,
             "preexisting_external_task_selection":OLD_SELECTION_SHA,
             "topics":TOPICS,"kinds":KINDS,"seed":SEED,"max_tokens":MAX_OUT,
             "judge":"single_candidate_semantic_relevance-v1",
             "negative_acceptance_threshold":0,
             "human_independent_grade":False},
             sort_keys=True,separators=(",",":")).encode())

def cases():
    out=[]
    for i,(name,ref,para,contra,unrelated) in enumerate(TOPICS):
        suite=(
            ("exact",ref,"YES"),
            ("paraphrase",para,"YES"),
            ("contradiction",contra,"NO"),
            ("unrelated",unrelated,"UNKNOWN"),
            ("quoted_disclaimer","This is not the answer: "+ref,"NO"),
        )
        for kind,candidate,label in suite:
            out.append((i,name,kind,ref,candidate,label))
    return tuple(out)

def prereg():
    c=cases()
    must(len(c)==30 and len(set(x[1] for x in c))==6,"FROZEN_FAMILIES")
    must(Counter(x[2] for x in c)=={k:6 for k in KINDS},"FROZEN_KINDS")
    must(Counter(x[5] for x in c)=={"YES":12,"NO":12,"UNKNOWN":6},"LABEL_COUNTS")
    # Fail closed if a candidate is an exact negative duplicated from target.
    must(all(x[3]!=x[4] for x in c if x[2]!="exact"),"NO_NEGATIVE_DUPLICATES")
    print("MPAI30_FROZEN_CANARY_PROTOCOL_SHA256="+protocol(),flush=True)
    print("MPAI30_DECLARATIVE_SYNTHETIC_CASES=30",flush=True)
    print("MPAI30_PARAPHRASE_CASES=6",flush=True)
    print("MPAI30_HARD_NEGATIVE_CASES=12",flush=True)
    print("MPAI30_UNKNOWN_CASES=6",flush=True)
    print("MPAI30_ORIGINAL_EXTERNAL_SELECTION_UNCHANGED="+OLD_SELECTION_SHA,flush=True)
    print("MPAI30_INDEPENDENT_HUMAN_ANNOTATION=FALSE",flush=True)
    print("MPAI30_MODEL_PRETRAINING_LEAKAGE_UNKNOWN=TRUE",flush=True)

def download_model(path):
    must(not path.exists(),"MODEL_EXISTS")
    count=0;t0=time.monotonic();h=hashlib.sha256()
    req=urllib.request.Request(MODEL_URL,
           headers={"User-Agent":"MPAI30-source-authenticated-judge-development/1"})
    with urllib.request.urlopen(req,timeout=55) as response,path.open("xb") as file:
        for buf in iter(lambda:response.read(4*1024*1024),b""):
            count+=len(buf)
            must(count<=MODEL_BYTES and time.monotonic()-t0<650,"DOWNLOAD_BOUNDED")
            h.update(buf);file.write(buf)
    must(count==MODEL_BYTES and h.hexdigest()==MODEL_SHA,"MODEL_IDENTITY")
    with path.open("rb") as f:must(f.read(4)==b"GGUF","MODEL_FILE_FORMAT")

def messages(reference,candidate):
    return [
     {"role":"system","content":
       "Evaluate whether a proposed answer is supported by a reference claim. "
       "Reply with exactly one token: YES, NO, or UNKNOWN. "
       "YES only if the proposed answer asserts the same facts as the reference, "
       "with no additions or contradictions. "
       "NO if the proposed answer contradicts or disclaims the reference. "
       "UNKNOWN if the proposed answer is unrelated or cannot be verified "
       "from reference. Beware quoted/disclaimed facts."},
     {"role":"user","content":"Reference: "+reference+
                            "\nProposed answer: "+candidate}
    ]

def parse(x):
    value=x.strip().upper()
    return value if value in ("YES","NO","UNKNOWN") else None

def peak_working_set():
    import ctypes
    from ctypes import wintypes
    class PMC(ctypes.Structure):
        _fields_=[("cb",wintypes.DWORD),("PageFaultCount",wintypes.DWORD),
          ("PeakWorkingSetSize",ctypes.c_size_t),("WorkingSetSize",ctypes.c_size_t),
          ("QuotaPeakPagedPoolUsage",ctypes.c_size_t),("QuotaPagedPoolUsage",ctypes.c_size_t),
          ("QuotaPeakNonPagedPoolUsage",ctypes.c_size_t),
          ("QuotaNonPagedPoolUsage",ctypes.c_size_t),("PagefileUsage",ctypes.c_size_t),
          ("PeakPagefileUsage",ctypes.c_size_t)]
    x=PMC();x.cb=ctypes.sizeof(x)
    k=ctypes.WinDLL("kernel32",use_last_error=True)
    p=ctypes.WinDLL("psapi",use_last_error=True)
    k.GetCurrentProcess.restype=wintypes.HANDLE
    p.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(PMC),wintypes.DWORD]
    p.GetProcessMemoryInfo.restype=wintypes.BOOL
    must(bool(p.GetProcessMemoryInfo(k.GetCurrentProcess(),ctypes.byref(x),x.cb)),
         "WIN32_MEMORY_COUNTER")
    return int(x.PeakWorkingSetSize)

def evaluate(scratch):
    global STAGE
    must(os.name=="nt" and os.getenv("RUNNER_NAME")=="FORGE-CODEX-REMOTE"
         and os.getenv("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE",
         "ORIGINAL_WINDOWS_RUNNER")
    must(not os.getenv("OPENAI_API_KEY"),"PAID_API_DENIED")
    must(not scratch.exists(),"PRIVATE_SCRATCH_COLLISION")
    must(shutil.disk_usage(scratch.parent).free>3500000000,"DISK_BUDGET")
    scratch.mkdir()
    STAGE="MODEL_DOWNLOAD"
    path=scratch/MODEL_NAME
    download_model(path)
    print("MPAI30_ORIGINAL_MODEL_FULL_SHA256=PASS",flush=True)
    os.environ["HF_HUB_OFFLINE"]="1"
    socket.socket=lambda *a,**kw: (_ for _ in ()).throw(
      RuntimeError("MPAI30_OFFLINE_INFERENCE_REQUIRED"))
    from llama_cpp import Llama,LlamaGrammar
    grammar=LlamaGrammar.from_string('root ::= ("YES" | "NO" | "UNKNOWN")',verbose=False)
    t0=time.perf_counter()
    llm=Llama(model_path=str(path),n_ctx=2048,n_threads=4,
             n_gpu_layers=0,n_batch=128,seed=SEED,verbose=False)
    load_ms=max(1,int(1000*(time.perf_counter()-t0)))
    must(load_ms<=120000,"MODEL_LOAD_BUDGET")
    STAGE="ACTUAL_INFERENCE"
    rows=[]
    for idx,(family,name,kind,reference,candidate,expected) in enumerate(cases()):
        start=time.perf_counter()
        response=llm.create_chat_completion(messages=messages(reference,candidate),
                        temperature=0,top_p=1,max_tokens=MAX_OUT,grammar=grammar)
        elapsed=max(1,int((time.perf_counter()-start)*1000))
        choices=response.get("choices",[])
        must(len(choices)==1,"OUTPUT_SCHEMA")
        txt=choices[0].get("message",{}).get("content","")
        usage=response.get("usage",{})
        pt=int(usage.get("prompt_tokens",0));ct=int(usage.get("completion_tokens",0))
        must(isinstance(txt,str) and 0<pt<=1800 and 0<ct<=MAX_OUT,
             "TOKEN_BUDGET")
        result=parse(txt)
        rows.append({"family":family,"case":idx,"kind":kind,"expected":expected,
            "actual":result,"correct":result==expected,
            "hard_false_positive":expected!="YES" and result=="YES",
            "unsupported_credit":expected=="UNKNOWN" and result=="YES",
            "paraphrase_credit":kind=="paraphrase" and result=="YES",
            "denied_valid":expected=="YES" and result!="YES",
            "unparseable":result is None,"prompt_tokens":pt,
            "completion_tokens":ct,"latency_ms":elapsed,
            "response_sha256":sha(txt.encode())})
    must(len(rows)==30,"TRIAL_DENOMINATOR")
    (scratch/"private-development-trials.json").write_text(
      json.dumps({"model_sha256":MODEL_SHA,"protocol_sha":protocol(),
                 "first_use_independent":False,"author_generated":True,
                 "trials":rows},sort_keys=True),encoding="utf-8")
    for kind in KINDS:
        z=[x for x in rows if x["kind"]==kind]
        must(len(z)==6,"KIND_DENOMINATOR")
        receipt={"cases":len(z),
           "exact_expected_label":z[0]["expected"],
           "exact_label_correct":sum(x["correct"] for x in z),
           "accepted_yes":sum(x["actual"]=="YES" for x in z),
           "hard_false_positives":sum(x["hard_false_positive"] for x in z),
           "unparseable":sum(x["unparseable"] for x in z),
           "total_tokens":sum(x["prompt_tokens"]+x["completion_tokens"] for x in z),
           "wall_ms":sum(x["latency_ms"] for x in z)}
        print("MPAI30_KIND_"+kind.upper()+"="+json.dumps(
              receipt,sort_keys=True,separators=(",",":")),flush=True)
    fp=sum(x["hard_false_positive"] for x in rows)
    accepted=sum(x["actual"]=="YES" for x in rows if x["expected"]=="YES")
    print("MPAI30_REAL_JUDGE_MODEL_CALLS=30",flush=True)
    print("MPAI30_TOTAL_HARD_FALSE_POSITIVES="+str(fp),flush=True)
    print("MPAI30_CORRECT_POSITIVE_ACCEPTED="+str(accepted)+"_OF_12",flush=True)
    print("MPAI30_ALL_EXACT_LABELS_CORRECT="+str(sum(x["correct"] for x in rows))+
          "_OF_30",flush=True)
    print("MPAI30_ORIGINAL_WINDOWS_PEAK_BYTES="+str(peak_working_set()),flush=True)
    print("MPAI30_MODEL_LOAD_MS="+str(load_ms),flush=True)
    # Passing the hard-negative zero-FP control alone is insufficient:
    # true semantic grading also needs paraphrase/unsupported coverage,
    # trusted independent human scores and hidden original benchmark cases.
    if fp:
        print("MPAI30_ZERO_HARD_FALSE_POSITIVES=FAIL",flush=True)
    else:
        print("MPAI30_ZERO_HARD_FALSE_POSITIVES=PASS",flush=True)
    print("MPAI30_AUTHOR_GENERATED_DEVELOPMENT_ONLY=TRUE",flush=True)
    print("MPAI30_INDEPENDENT_HUMAN_REFERENCE=NOT_PRESENT",flush=True)
    print("MPAI30_EXTERNAL_BENCHMARK_GOLD_MODEL_EXPOSURE=0",flush=True)
    print("MPAI30_PRODUCTION_MEMORY_WRITES=0",flush=True)
    print("MPAI30_SCIENTIFIC_SEMANTIC_SCORER=NOT_QUALIFIED",flush=True)
    print("MPAI30_UNFAMILIAR_EVALUATION_RELEASE=BLOCKED",flush=True)

def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--phase",choices=("preregister","evaluate"),required=True)
    args=ap.parse_args()
    prereg()
    if args.phase=="preregister":
        print("MPAI30_PREMODEL_PROTOCOL_FROZEN=PASS",flush=True)
        print("MPAI30_ORIGINAL_EXTERNAL_GOLD_READ=FALSE",flush=True)
    else:
        evaluate(Path(os.environ["MPAI30_PRIVATE_SCRATCH"]))

if __name__=="__main__":
    try:main()
    except Exception as err:
        msg=str(err)
        why=msg if re.fullmatch(r"MPAI30_[A-Z0-9_]{3,100}",msg) else "MPAI30_PRIVATE_EXCEPTION"
        print("MPAI30_SAFE_FAILURE="+why,flush=True)
        print("MPAI30_FAILURE_STAGE="+STAGE,flush=True)
        print("MPAI30_FAILURE_TYPE="+type(err).__name__,flush=True)
        sys.exit(2)
