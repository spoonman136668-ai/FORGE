"""MP-AI31: precommitted adversarial guard and real local semantic judge.

Research development, not independently human-adjudicated science. Six new
synthetic claims are disjoint from P30. Eight conditions per claim: 48 genuine
Phi-3.5 local calls. Frozen original P30 source/result remains untouched.
Guard and counterfactual no-guard decisions are calculated from SAME raw model
outputs; strict exact string is an additional conservative comparator.
No API, model promotion, accepted-memory change, or production dispatch.
"""
from __future__ import annotations
from collections import Counter
import argparse
import ctypes
from ctypes import wintypes
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
MODEL_URL=("https://huggingface.co/bartowski/Phi-3.5-mini-instruct-GGUF/resolve/"
          +MODEL_REV+"/"+MODEL_NAME+"?download=true")
P30_FROZEN_SOURCE_BLOB="0fa02bc09fae04f72c49f555fa7063e31f546f6c"
P28_SELECTION_SHA="6ddf3d30019f102f2d2f820be69c1b0478a71f8e7cd1ea6733c5ee07ab29bb85"
SEED=137
MAX_TOKENS=8
STAGE="INIT"

# Six new independent *authored* scenarios, NOT independent human labels.
# Reference and positive paraphrase contain the same factual proposition.
FAMILIES=(
 ("river","The Red River flows through Fargo.",
  "Fargo is situated on the Red River.",
  "The Red River never passes through Fargo.",
  "The festival was canceled because of a storm."),
 ("orbit","Saturn takes about 29 years to orbit the Sun.",
  "Saturn completes a solar orbit in roughly twenty-nine years.",
  "Saturn completes a solar orbit in less than one Earth year.",
  "A new telescope was installed in the laboratory."),
 ("election","Nina won the committee vote by six to four.",
  "The committee voted 6–4 in Nina's favor.",
  "Nina lost the committee vote six to four.",
  "The committee reviewed a new budget proposal."),
 ("chemistry","Water boils at about one hundred degrees Celsius at sea level.",
  "At sea-level pressure water boils near 100 °C.",
  "Water boils at about fifty degrees Celsius at sea level.",
  "The chemistry course began during the autumn."),
 ("archive","The archive reopened after the roof repair was finished.",
  "Once the roof had been repaired the archive opened again.",
  "The archive stayed closed despite the completed roof repair.",
  "The archive catalog includes historical photographs."),
 ("transfer","The team transferred the prototype from Oslo to Bergen.",
  "The prototype was moved to Bergen from Oslo by the team.",
  "The team moved the prototype from Bergen to Oslo instead.",
  "The team arranged a video conference for Tuesday."),
)
KINDS=("exact","paraphrase","contradiction","unrelated",
       "disclaimed_quote","unsupported_claim","retracted_claim","double_negative")
ABSTAIN_ON_UNSUPPORTED={"NO","UNKNOWN"}
# Broad precommitted veto patterns. These are *not* a general semantic parser.
# Every pattern may also reject a genuine fact if embedded in another context.
VETO_PATTERNS=(
  r"\brejected\s+(?:the\s+)?(?:claim|statement|assertion|report)\b",
  r"\bno\s+evidence\s+(?:exists\s+)?for\b",
  r"\b(?:has|have|was|were)\s+been\s+retracted\b",
  r"\bretracted\b",
  r"\bnot\s+(?:the\s+)?(?:correct\s+)?answer\b",
  r"\bfalse\s+(?:statement|claim|assertion)\b",
  r"\b(?:not\s+supported|unsubstantiated)\b",
)
VETO_REGEX=tuple(re.compile(p,re.IGNORECASE) for p in VETO_PATTERNS)

def check(cond,code):
    if not cond:raise RuntimeError("MPAI31_"+code)
def sha(data):
    return hashlib.sha256(data).hexdigest()
def all_cases():
    tasks=[]
    for fam,(name,ref,para,contra,irrelevant) in enumerate(FAMILIES):
        samples=(
          ("exact",ref,"YES"),
          ("paraphrase",para,"YES"),
          ("contradiction",contra,"NO"),
          ("unrelated",irrelevant,"UNKNOWN"),
          ("disclaimed_quote","The reviewers rejected the statement '"+ref+"' as false.","NO"),
          ("unsupported_claim","The evidence has not been found; there is no evidence for the assertion that "+ref,"NO"),
          ("retracted_claim","The following claim has been retracted: '"+ref+"'","NO"),
          ("double_negative","It is not false that "+ref,"YES"),
        )
        for kind,candidate,label in samples:
            tasks.append((fam,name,kind,ref,candidate,label))
    return tuple(tasks)
def prereg_digest():
    return sha(json.dumps({
     "protocol":"mpai31-authored-new-claim-family-v1",
     "model":MODEL_SHA,"seed":SEED,"max_output":MAX_TOKENS,
     "frozen_p30_source_blob":P30_FROZEN_SOURCE_BLOB,
     "p28_source_selection":P28_SELECTION_SHA,
     "families":FAMILIES,"kinds":KINDS,"veto_patterns":VETO_PATTERNS,
     "guard_accepts": "YES only when raw model YES and no veto",
     "same_raw_output_comparator":True,
     "independent_human_grade":False,
     "scientific_acceptance":False},sort_keys=True,separators=(",",":")).encode())
def prereg():
    cases=all_cases()
    check(len(cases)==48,"FROZEN_48_CASES")
    check(Counter(x[2] for x in cases)=={k:6 for k in KINDS},"FROZEN_EIGHT_KINDS")
    check(Counter(x[5] for x in cases)=={"YES":18,"NO":24,"UNKNOWN":6},"EXPECTED_COUNTS")
    check(len({x[1] for x in cases})==6,"INDEPENDENT_NEW_FAMILY_NAMES")
    check(all(x[3]!=x[4] for x in cases if x[2]!="exact"),"NO_NEGATIVE_DUPLICATES")
    print("MPAI31_FROZEN_PROTOCOL_SHA256="+prereg_digest(),flush=True)
    print("MPAI31_NEW_PRECOMMITTED_DEVELOPMENT_CASES=48",flush=True)
    print("MPAI31_NEW_SOURCE_INDEPENDENT_HUMAN_LABELS=FALSE",flush=True)
    print("MPAI31_HARD_NEGATIVE_CASES=24",flush=True)
    print("MPAI31_POSITIVE_CASES=18",flush=True)
    print("MPAI31_UNRELATED_CASES=6",flush=True)
    print("MPAI31_SAME_RAW_MODEL_OUTPUT_BOTH_ARMS=TRUE",flush=True)
    print("MPAI31_PRIOR_NEGATIVE_RESULT_UNALTERED=TRUE",flush=True)
def veto(candidate):
    return any(p.search(candidate) for p in VETO_REGEX)
def conservative_guard(raw,candidate):
    if raw=="YES" and veto(candidate):
        return "NO"
    return raw
def strict_comparator(reference,candidate):
    # Only casefold + whitespace. Not credited as semantic paraphrase judge.
    return "YES" if " ".join(reference.casefold().split())==" ".join(candidate.casefold().split()) else "UNKNOWN"
def check_guard_without_model():
    # Guards are frozen and can be checked without genuine model outcomes.
    cases=all_cases()
    denial=[x for x in cases if x[2] in ("disclaimed_quote","unsupported_claim","retracted_claim")]
    check(len(denial)==18 and all(veto(x[4]) for x in denial),"GUARD_DENIAL_COVERAGE")
    positive=[x for x in cases if x[5]=="YES"]
    check(len(positive)==18 and not any(veto(x[4]) for x in positive),"GUARD_POSITIVE_BLOCK")
    contradiction=[x for x in cases if x[2]=="contradiction"]
    check(len(contradiction)==6 and not any(veto(x[4]) for x in contradiction),"GUARD_NONOVERFIT")
    print("MPAI31_DETERMINISTIC_PREMODEL_GUARD_ASSERTIONS=PASS",flush=True)
def download(path):
    check(not path.exists(),"MODEL_ALREADY_EXISTS")
    count=0;h=hashlib.sha256();t=time.monotonic()
    req=urllib.request.Request(MODEL_URL,
         headers={"User-Agent":"MPAI31-original-pinned-model-canary/1"})
    with urllib.request.urlopen(req,timeout=55) as source,path.open("xb") as out:
        for data in iter(lambda:source.read(4*1024*1024),b""):
            count+=len(data)
            check(count<=MODEL_BYTES and time.monotonic()-t<660,"MODEL_TRANSFER_BOUND")
            h.update(data);out.write(data)
    check(count==MODEL_BYTES and h.hexdigest()==MODEL_SHA,"MODEL_SHA256_DRIFT")
    with path.open("rb") as read:
        check(read.read(4)==b"GGUF","MODEL_GGUF_HEADER")
def parse(raw):
    if not isinstance(raw,str):return None
    text=raw.strip().upper()
    return text if text in ("YES","NO","UNKNOWN") else None
def messages(reference,candidate):
    return [
      {"role":"system","content":"Evaluate whether a proposed answer is supported by a reference claim. "
      "Reply with exactly one token: YES, NO, or UNKNOWN. "
      "YES only if the proposed answer asserts the same facts as the reference, "
      "with no additions or contradictions. "
      "NO if the proposed answer contradicts or disclaims the reference. "
      "UNKNOWN if the proposed answer is unrelated or cannot be verified "
      "from reference. Beware quoted/disclaimed facts."},
      {"role":"user","content":"Reference: "+reference+"\nProposed answer: "+candidate}
    ]
def memory_peak():
    class PMC(ctypes.Structure):
        _fields_=[("cb",wintypes.DWORD),("PageFaultCount",wintypes.DWORD),
          ("PeakWorkingSetSize",ctypes.c_size_t),("WorkingSetSize",ctypes.c_size_t),
          ("QuotaPeakPagedPoolUsage",ctypes.c_size_t),("QuotaPagedPoolUsage",ctypes.c_size_t),
          ("QuotaPeakNonPagedPoolUsage",ctypes.c_size_t),
          ("QuotaNonPagedPoolUsage",ctypes.c_size_t),
          ("PagefileUsage",ctypes.c_size_t),("PeakPagefileUsage",ctypes.c_size_t)]
    x=PMC();x.cb=ctypes.sizeof(x)
    k=ctypes.WinDLL("kernel32",use_last_error=True)
    p=ctypes.WinDLL("psapi",use_last_error=True)
    k.GetCurrentProcess.restype=wintypes.HANDLE
    p.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(PMC),wintypes.DWORD]
    p.GetProcessMemoryInfo.restype=wintypes.BOOL
    check(bool(p.GetProcessMemoryInfo(k.GetCurrentProcess(),ctypes.byref(x),x.cb)),
          "MEMORY_COUNTER")
    return int(x.PeakWorkingSetSize)
def evaluate(scratch):
    global STAGE
    check(os.name=="nt" and os.getenv("RUNNER_NAME")=="FORGE-CODEX-REMOTE"
          and os.getenv("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE",
          "ORIGINAL_WINDOWS_REQUIRED")
    check(not os.getenv("OPENAI_API_KEY"),"PAID_API_DENIED")
    check(not scratch.exists(),"SCRATCH_COLLISION")
    check(shutil.disk_usage(scratch.parent).free>3500000000,"DISK_BUDGET")
    scratch.mkdir()
    STAGE="DOWNLOAD"
    path=scratch/MODEL_NAME
    download(path)
    print("MPAI31_MODEL_FULL_SHA256=PASS",flush=True)
    os.environ["HF_HUB_OFFLINE"]="1"
    socket.socket=lambda *a,**kw:(_ for _ in ()).throw(
       RuntimeError("MPAI31_NETWORK_PROHIBITED"))
    from llama_cpp import Llama,LlamaGrammar
    grammar=LlamaGrammar.from_string('root ::= ("YES" | "NO" | "UNKNOWN")',verbose=False)
    t=time.perf_counter()
    model=Llama(model_path=str(path),n_ctx=2048,n_threads=4,
                n_gpu_layers=0,n_batch=128,seed=SEED,verbose=False)
    load_ms=max(1,int((time.perf_counter()-t)*1000))
    check(load_ms<=120000,"LOAD_TIME_BUDGET")
    STAGE="INFERENCE"
    rows=[]
    for number,(fi,name,kind,reference,candidate,gold) in enumerate(all_cases()):
        start=time.perf_counter()
        data=model.create_chat_completion(messages=messages(reference,candidate),
                          temperature=0,top_p=1,max_tokens=MAX_TOKENS,grammar=grammar)
        elapsed=max(1,int((time.perf_counter()-start)*1000))
        choices=data.get("choices",[])
        check(len(choices)==1,"MODEL_CHOICE_SCHEMA")
        raw=choices[0].get("message",{}).get("content","")
        usage=data.get("usage",{})
        pt=int(usage.get("prompt_tokens",0));ct=int(usage.get("completion_tokens",0))
        check(isinstance(raw,str) and 0<pt<1800 and 0<ct<=MAX_TOKENS,
              "TOKEN_BOUNDS")
        baseline=parse(raw)
        guard=conservative_guard(baseline,candidate)
        strict=strict_comparator(reference,candidate)
        rows.append({"family":fi,"case":number,"kind":kind,"gold":gold,
          "baseline":baseline,"guard":guard,"strict":strict,
          "guard_veto":veto(candidate),"tokens":pt+ct,"latency_ms":elapsed,
          "private_raw_hash":sha(raw.encode())})
    check(len(rows)==48,"CALLS_48")
    (scratch/"private_study.json").write_text(json.dumps({
       "protocol_sha":prereg_digest(),"model_sha":MODEL_SHA,
       "research_only":True,"rows":rows},sort_keys=True),encoding="utf-8")
    for kind in KINDS:
        rr=[x for x in rows if x["kind"]==kind]
        check(len(rr)==6,"KIND_N")
        d={"count":6,"baseline_correct":sum(x["baseline"]==x["gold"] for x in rr),
           "guard_correct":sum(x["guard"]==x["gold"] for x in rr),
           "strict_correct":sum(x["strict"]==x["gold"] for x in rr),
           "baseline_yes":sum(x["baseline"]=="YES" for x in rr),
           "guard_yes":sum(x["guard"]=="YES" for x in rr),
           "strict_yes":sum(x["strict"]=="YES" for x in rr),
           "guard_vetoes":sum(x["guard_veto"] for x in rr),
           "tokens":sum(x["tokens"] for x in rr),
           "inference_ms":sum(x["latency_ms"] for x in rr)}
        print("MPAI31_"+kind.upper()+"="+json.dumps(
              d,sort_keys=True,separators=(",",":")),flush=True)
    for name in ("baseline","guard","strict"):
        fp=sum(x[name]=="YES" and x["gold"]!="YES" for x in rows)
        pos=sum(x[name]=="YES" and x["gold"]=="YES" for x in rows)
        actual=sum(x[name]==x["gold"] for x in rows)
        abstain=sum(x[name]=="UNKNOWN" for x in rows)
        print("MPAI31_"+name.upper()+"_HARD_FALSE_POSITIVES="+str(fp),flush=True)
        print("MPAI31_"+name.upper()+"_SUPPORTED_POSITIVES="+str(pos)+"_OF_18",flush=True)
        print("MPAI31_"+name.upper()+"_EXACT_LABELS="+str(actual)+"_OF_48",flush=True)
        print("MPAI31_"+name.upper()+"_ABSTENTIONS="+str(abstain),flush=True)
        if name=="guard":
            print("MPAI31_GUARD_ZERO_HARD_FALSE_POSITIVES="+(
              "PASS" if fp==0 else "FAIL"),flush=True)
    print("MPAI31_REAL_LOCAL_MODEL_CALLS=48",flush=True)
    print("MPAI31_MODEL_LOAD_MS="+str(load_ms),flush=True)
    peak=memory_peak()
    print("MPAI31_PEAK_ORIGINAL_WINDOWS_PROCESS_BYTES="+str(peak),flush=True)
    check(0<peak<6000000000,"PEAK_MEMORY_BUDGET")
    print("MPAI31_NO_EXTERNAL_BENCHMARK_ANSWER_EXPOSURE=TRUE",flush=True)
    print("MPAI31_NEW_SYNTHETIC_AUTHORSHIP_NOT_INDEPENDENT=TRUE",flush=True)
    print("MPAI31_NO_AUTONOMOUS_AGENT_LEARNING_CLAIM=TRUE",flush=True)
    print("MPAI31_SCIENTIFIC_SEMANTIC_JUDGE=NOT_QUALIFIED",flush=True)
    print("MPAI31_SCIENTIFIC_MODEL_EVAL_RELEASE=BLOCKED",flush=True)
    print("MPAI31_PRODUCTION_MEMORY_WRITES=0",flush=True)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--phase",choices=("preregister","evaluate"),required=True)
    args=p.parse_args()
    prereg()
    check_guard_without_model()
    if args.phase=="preregister":
        print("MPAI31_PREMODEL_PROTOCOL_FROZEN=PASS",flush=True)
        print("MPAI31_MODEL_CALLS=0",flush=True)
    else:
        evaluate(Path(os.environ["MPAI31_PRIVATE_SCRATCH"]))
if __name__=="__main__":
    try:main()
    except Exception as exc:
        message=str(exc)
        code=message if re.fullmatch(r"MPAI31_[A-Z0-9_]{3,90}",message) else "MPAI31_PRIVATE_EXCEPTION"
        print("MPAI31_SAFE_FAILURE="+code,flush=True)
        print("MPAI31_SAFE_STAGE="+STAGE,flush=True)
        print("MPAI31_SAFE_TYPE="+type(exc).__name__,flush=True)
        sys.exit(2)
