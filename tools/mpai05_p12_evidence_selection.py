"""MP-AI05 P12: frozen, gold-blind evidence-selection diagnostics.

Compares unchanged P10 lexical retrieval against two prespecified selection
mechanisms on identical P9 public development questions, P10-extracted states,
and 2,300-character context cap. Official gold is inspected ONLY after all
contexts are frozen; literal gold inclusion is a weak post-hoc probe, not an
accuracy grade or promotion criterion. No local/hosted model inference.
"""
from __future__ import annotations

from collections import Counter,defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import time

import mpai05_p9_dataset_freeze as p9
import mpai05_p10_public_development as p10
import mpai05_p11_diagnose as p11

EXPECTED_COHORT="103dbf87dda69f03b32f4c6a3a987b5ab5b7a8d3c3ceeb11f223ad5cf358ae52"
SOURCE_PIN_P10="7bd698e3265cc41ee4d286461980d7586a25ac99"
SOURCE_PIN_P11="5beb813560d0e4f816a0dabefd1aa5fcc89321a9"
METHODS=("p10_lexical","idf_diverse","idf_neighbor")
MAX_CONTEXT=p10.CONTEXT_CHARS
MAX_SEGMENTS=8
TOP_ANCHORS=120
STAGE="INIT"

def require(ok,code):
    if not ok: raise RuntimeError("MPAI05_P12_"+code)

def fingerprint(raw:str)->str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def build_index(memory:dict[str,list[str]]):
    index=[]
    df=Counter()
    for ident in sorted(memory):
        for idx,original in enumerate(memory[ident]):
            text=original[:1150]
            terms=frozenset(p10.tokenize(text))
            if not terms:continue
            index.append((ident,idx,text,terms))
            df.update(terms)
    require(len(index)>0,"EMPTY_INDEX")
    return index,df

def score_anchors(question:str,index,df):
    terms=p10.tokenize(question)
    if not terms:return []
    n=len(index)
    rarity={q:math.log1p((n-df.get(q,0)+0.5)/(df.get(q,0)+0.5))
            for q in terms}
    result=[]
    for ident,idx,text,doc in index:
        common=terms & doc
        if not common:continue
        relevance=sum(rarity[q] for q in common)
        # Fixed length normalization, no reference/gold/answer input.
        relevance*=1.0/(1.0+len(doc)/80.0)
        result.append((relevance,ident,idx,text,doc))
    result.sort(key=lambda x:(-x[0],x[1],x[2]))
    return result[:TOP_ANCHORS]

def pack(candidates:list[tuple[str,int,str]],max_chars:int=MAX_CONTEXT,
         max_lines:int=MAX_SEGMENTS)->str:
    pieces=[]
    used=set()
    total=0
    for ident,idx,text in candidates:
        key=(ident,idx)
        if key in used:continue
        line="Evidence ["+ident[:8]+":"+str(idx)+"]: "+text
        extra=len(line)+(1 if pieces else 0)
        if total+extra>max_chars:continue
        pieces.append(line)
        used.add(key)
        total+=extra
        if len(pieces)>=max_lines:break
    result="\n".join(pieces)
    require(len(result)<=max_chars,"CONTEXT_BUDGET")
    return result

def diverse(question,anchors):
    # Fixed query-coverage reward and redundancy penalty, at most two
    # selected segments per source trajectory; all weights predeclared.
    terms=p10.tokenize(question)
    pool=list(anchors)
    chosen=[]
    seen=set()
    per_trajectory=Counter()
    while pool and len(chosen)<MAX_SEGMENTS:
        eligible=[]
        for row in pool:
            rel,ident,idx,text,doc=row
            if per_trajectory[ident]>=2:continue
            qbonus=0.55*len((doc & terms)-seen)
            redundant=0.08*len(doc & seen)
            score=rel+qbonus-redundant
            eligible.append((-score,ident,idx,row))
        if not eligible:break
        _,_,_,best=min(eligible,key=lambda x:(x[0],x[1],x[2]))
        pool.remove(best)
        rel,ident,idx,text,doc=best
        chosen.append((ident,idx,text))
        seen.update(doc)
        per_trajectory[ident]+=1
    return chosen

def adjacent(anchors,memory):
    # Anchors selected only from question similarity. Include closest
    # preceding/following sequence elements when within the same source.
    # No gold-answer access, no reranking on the diagnostic outcome.
    out=[]
    used=set()
    for rel,ident,idx,text,doc in anchors[:32]:
        for near in (idx,idx+1,idx-1):
            if near<0 or near>=len(memory[ident]):continue
            key=(ident,near)
            if key in used:continue
            used.add(key)
            out.append((ident,near,memory[ident][near][:1150]))
    return out

def generate(question,index,df,memory):
    """All methods are question+source only; never given gold or scorer."""
    original=p10.retrieve(question,list(memory.keys()),memory)
    anchors=score_anchors(question,index,df)
    result={
      "p10_lexical":original,
      "idf_diverse":pack(diverse(question,anchors)),
      "idf_neighbor":pack(adjacent(anchors,memory)),
    }
    require(set(result)==set(METHODS),"METHOD_MISSING")
    require(all(type(v) is str for v in result.values()),"CONTEXT_TYPE")
    require(all(len(v)<=MAX_CONTEXT+10 for v in result.values()),
            "CONTEXT_BOUND_EXCEEDED")
    return result

def compare(questions,selected,haystacks,memory):
    by_id={q["id"]:q for q in questions}
    index,df=build_index(memory)
    metrics={m:Counter() for m in METHODS}
    examples=[]
    for case in selected:
        qid=case["id"]
        row=by_id[qid]
        question=row["question"]
        require(type(question) is str,"QUESTION_TYPE")
        # Freeze actual retrieval contexts and their hashes BEFORE looking at gold.
        timings={}
        contexts={}
        for method in METHODS:
            before=time.process_time_ns()
            if method=="p10_lexical":
                text=p10.retrieve(question,haystacks[qid],memory)
            else:
                anchors=score_anchors(question,index,df)
                if method=="idf_diverse":
                    text=pack(diverse(question,anchors))
                else:
                    text=pack(adjacent(anchors,memory))
            timings[method]=max(1,time.process_time_ns()-before)
            contexts[method]=text
        require(all(len(t)<=MAX_CONTEXT+10 for t in contexts.values()),
                "CONTEXT_LENGTH_OVER")
        hashes={m:fingerprint(contexts[m]) for m in METHODS}
        require(len(hashes)==3,"CONTEXT_SHA_MISSING")
        # The held-out *public development* reference is used only for the
        # following post-freeze literal probe, not for candidate generation.
        gold=row.get("answer")
        require(type(gold) is str,"REFERENCE_TYPE")
        ids=haystacks[qid]
        full="\n".join(segment for tid in ids for segment in memory[tid])
        full_literal=p11.has_literal(gold,full)
        baseline_literal=p11.has_literal(gold,contexts["p10_lexical"])
        for method in METHODS:
            text=contexts[method]
            stats=metrics[method]
            stats["cases"]+=1
            stats["total_context_chars"]+=len(text)
            stats["total_cpu_ns"]+=timings[method]
            stats["empty_context_cases"]+=int(not bool(text))
            stats["near_cap_cases"]+=int(len(text)>=MAX_CONTEXT*0.9)
            stats["literal_reference_present"]+=int(p11.has_literal(gold,text))
            stats["literal_eligible_cases"]+=int(full_literal)
            stats["literal_gained_vs_p10"]+=int(
                not baseline_literal and p11.has_literal(gold,text))
            stats["literal_lost_vs_p10"]+=int(
                baseline_literal and not p11.has_literal(gold,text))
            stats["question_term_coverage_milli"]+=round(
                1000*len(p10.tokenize(question)&p10.tokenize(text))/
                max(1,len(p10.tokenize(question))))
        examples.append({"case_digest":fingerprint(qid)[:12],
                         "context_sha256":hashes})
    require(all(x["cases"]==16 and x["literal_eligible_cases"]==7
                for x in metrics.values()),"COHORT_DIAGNOSIS_DRIFT")
    require(metrics["p10_lexical"]["literal_reference_present"]==2,
            "P11_LITERAL_BASELINE_DRIFT")
    # Published aggregate only. No example IDs, golds, prompts or contexts.
    return metrics

def main():
    global STAGE
    require(os.getenv("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE" and
            os.getenv("RUNNER_NAME")=="FORGE-CODEX-REMOTE",
            "WRONG_RUNNER")
    require(not os.getenv("OPENAI_API_KEY"),"PAID_API_DENIED")
    root=Path(os.environ["MPAI05_P12_SCRATCH"])
    require(not root.exists(),"SCRATCH_EXISTS")
    require(shutil.disk_usage(root.parent).free>=2_000_000_000,"DISK_CAPACITY")
    root.mkdir()
    STAGE="SOURCE"
    official,checkout=p10.official_scorer(root)
    STAGE="COHORT"
    raw={name:p9.download(name) for name in (
         "checksums.sha256","SCHEMA.md","questions.jsonl","haystacks/lme_v2_small.json")}
    frozen=p9.freeze(raw["questions.jsonl"],raw["haystacks/lme_v2_small.json"],
                     raw["SCHEMA.md"],raw["checksums.sha256"])
    require(frozen["cohort_sha256"]==EXPECTED_COHORT,"COHORT_SHA_DRIFT")
    questions=[json.loads(z) for z in raw["questions.jsonl"].decode("utf-8").splitlines()
               if z.strip()]
    small=json.loads(raw["haystacks/lme_v2_small.json"])
    selected=p9.choose(questions,small)["cohort"]
    required={}
    for item in selected:
        for ident in small[item["id"]]:
            if ident in required:require(required[ident]==item["domain"],"CROSS_DOMAIN")
            required[ident]=item["domain"]
    STAGE="TRAJECTORIES"
    path=root/"trajectories.jsonl"
    p10.download(
       f"https://huggingface.co/datasets/{p9.REPO}/resolve/{p9.REVISION}/"
       "trajectories.jsonl?download=true",
       path,p10.SHA_TRAJECTORIES,p10.BYTES_TRAJECTORIES)
    STAGE="COMPARE"
    mem=p10.get_text_trajectories(path,required)
    require(len(mem)==len(required)==200,"MEMORY_TRAJECTORY_COUNT")
    stats=compare(questions,selected,small,mem)
    require(not p10.run(["git","status","--porcelain","--untracked-files=all"],checkout),
            "OFFICIAL_SOURCE_DIRTY")
    print("MPAI05_P12_ORIGINAL_SOURCE=PASS")
    print("MPAI05_P12_OFFICIAL_DATA_SHA256=PASS")
    print("MPAI05_P12_FROZEN_COHORT_SHA256="+EXPECTED_COHORT)
    print("MPAI05_P12_FROZEN_METHODS=3")
    for method in METHODS:
        x=stats[method]
        for key in ("cases","total_context_chars","total_cpu_ns",
                    "empty_context_cases","near_cap_cases",
                    "literal_reference_present","literal_eligible_cases",
                    "literal_gained_vs_p10","literal_lost_vs_p10",
                    "question_term_coverage_milli"):
            print("MPAI05_P12_"+method.upper()+"_"+key.upper()+"="+str(x[key]))
    print("MPAI05_P12_GOLD_USED_FOR_RANKING=FALSE")
    print("MPAI05_P12_LITERAL_PROXY_NOT_SEMANTIC_GRADE=TRUE")
    print("MPAI05_P12_PUBLIC_DEVELOPMENT_ONLY=TRUE")
    print("MPAI05_P12_FIRST_USE=FALSE")
    print("MPAI05_P12_MODEL_CALLS=0")
    print("MPAI05_P12_SCIENTIFIC_ACCEPTANCE=FALSE")
    print("MPAI05_P12_PRODUCTION_WRITES=0")

if __name__=="__main__":
    try:main()
    except Exception as exc:
        msg=str(exc)
        safe=msg if re.fullmatch(r"MPAI05_P12_[A-Z0-9_]+",msg) else "PRIVATE_EXCEPTION"
        print("MPAI05_P12_FAILURE_CLASS="+safe,flush=True)
        print("MPAI05_P12_FAILURE_STAGE="+STAGE,flush=True)
        print("MPAI05_P12_FAILURE_TYPE="+type(exc).__name__,flush=True)
        sys.exit(2)
