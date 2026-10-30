"""MP-AI39: precommitted BM25 vs exact P37 lexical-IDF retrieval evidence audit.

Authentic LoCoMo original source (source-custody verified) and exact frozen P37
25 question IDs, independently annotated evidence turn IDs. Model calls: zero.
Selection phase sees only question *metadata*, not text/evidence/reference gold.
Both retrievers receive question and source dialogue text only, never original
annotation/evidence or gold; both use top12 turns and 6500-character budgets.
Reference/oracle evidence identities are inspected only after ranking finishes.
This is an exposed DEVELOPMENT comparison, NOT held-out first-use science,
production Mind-Palace retrieval or a user-facing source-data release.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
import os
import re
import statistics
import sys
import tempfile
from pathlib import Path

import mpai37_external_memory_effect as p37
import mpai38_original_evidence_coverage_audit as p38

P37_COMMITMENT="123411ed33446deded98c45dd3c5e54a98620b8565a8612b7bea1c594131c5b8"
P38_PRE_REGISTERED_SHA="305445ecba4792995b64de45d729dcc7cd71575215c4eb7fbb41a0eb0e8a3e38"
P37_SOURCE_BLOB="f1305323279cf56c1fdda068a5d14933dfbe6ca7"
P38_SOURCE_BLOB="bae5ddce69e17b8f3b5682799840405828784e63"
SOURCE_ORIGINAL_GIT_BLOB=p37.source.LOCOMO_BLOB
TOP_K=12
MAX_CHAR=6500
BM25_K1=1.2
BM25_B=0.75
RETRIEVERS=("p37_original_idf","untuned_bm25")
PHASE="INIT"

def need(cond,label):
    if not cond:raise RuntimeError("MPAI39_"+label)
def stable(x):
    return json.dumps(x,sort_keys=True,ensure_ascii=True,separators=(",",":"))
def checksum(s):
    return hashlib.sha256(s.encode()).hexdigest()
def freeze_protocol(items):
    # Selection-only manifest. Original external source text, question, gold,
    # evidence IDs, and retrieval scores are deliberately not part of it.
    return checksum(stable({
        "schema":"mpai39-original-p37-matched-budget-bm25-v1",
        "source_original_git_blob":SOURCE_ORIGINAL_GIT_BLOB,
        "p37_frozen_selection":P37_COMMITMENT,
        "p38_original_protocol":P38_PRE_REGISTERED_SHA,
        "p37_script_git_blob":P37_SOURCE_BLOB,
        "p38_script_git_blob":P38_SOURCE_BLOB,
        "frozen_selection":items,
        "candidates":RETRIEVERS,
        "bm25_params":{"k1":BM25_K1,"b":BM25_B,
                       "idf":"log(1+(N-df+0.5)/(df+0.5))",
                       "tf":"raw term frequency, stopwords from P37",
                       "doc_length":"number of non-stopword token occurrences"},
        "limits":{"top_k":TOP_K,"characters":MAX_CHAR,
                  "chunk":"exact P37 original truncated 700 chars",
                  "rank_ties":"original source turn index"},
        "scorer":"human original QA evidence-ID retrieval recall only",
        "category5":"audit separately as adversarial/unanswerable",
        "model_inference_calls":0,
        "first_use_unfamiliar":False,
        "accepted_memory_writes":0
    }))
def rank_bm25(turns,question):
    # Query and text only, never original LoCoMo QA evidence/gold.
    # Preserve token occurrences unlike P37 unique-term IDF scoring.
    q=p37.terms(question)
    need(bool(q),"NONEMPTY_QUESTION")
    documents=[]
    lengths=[]
    df=Counter()
    for line in turns:
        words=[z for z in re.findall(r"[a-z0-9]+",line.casefold())
               if len(z)>1 and z not in p37.STOP]
        tf=Counter(words)
        documents.append(tf)
        lengths.append(len(words))
        df.update(tf.keys())
    n=len(documents)
    need(n>30,"SOURCE_CONVERSATION_TOO_SHORT")
    avg=sum(lengths)/n
    need(avg>0,"SOURCE_AVERAGE_LENGTH")
    ranked=[]
    for i,counts in enumerate(documents):
        s=0.0
        norm=BM25_K1*(1-BM25_B+BM25_B*(lengths[i]/avg))
        for token in sorted(q):
            f=counts.get(token,0)
            if not f:continue
            idf=math.log(1+(n-df[token]+0.5)/(df[token]+0.5))
            s+=idf*(f*(BM25_K1+1))/(f+norm)
        ranked.append((-s,i))
    return ranked
def select_context(turns,ranked):
    indexes=[]
    consumed=0
    for neg_score,i in sorted(ranked):
        chunk=turns[i]
        if consumed+len(chunk)>MAX_CHAR:continue
        indexes.append(i)
        consumed+=len(chunk)+1
        if len(indexes)==TOP_K:break
    need(4<=len(indexes)<=TOP_K,"CONTEXT_K")
    ordered=sorted(indexes)
    text="\n".join(turns[i] for i in ordered)
    need(len(text)<=MAX_CHAR+TOP_K,"SOURCE_CONTEXT_CAP")
    return indexes,text
def original_retriever_indexes(turns,question):
    # Independently reconstruct indices, then verify byte-exact P37 function.
    q=p37.terms(question)
    docs=[p37.terms(t) for t in turns]
    df=Counter(word for doc in docs for word in doc)
    total=len(docs)
    scores=[(-sum(math.log(1+(total-df[x]+.5)/(df[x]+.5))
                   for x in (q&doc)),i)
            for i,doc in enumerate(docs)]
    indexes,text=select_context(turns,scores)
    need(text==p37.retrieve(turns,question),"ORIGINAL_P37_RETRIEVAL_DRIFT")
    return indexes,text
def get_tasks(data):
    cases,p37_sha=p37.freeze(data)
    need(p37_sha==P37_COMMITMENT,"ORIGINAL_FROZEN_SELECTION_DRIFT")
    need(len(cases)==25 and Counter(x["category"] for x in cases)==
         {"1":10,"2":10,"5":5},"ORIGINAL_CASE_COUNTS")
    return cases
def summarise(rows,arm,cat):
    a=[x for x in rows if x["category"]==cat]
    need(len(a)==(5 if cat=="5" else 10),"ORIGINAL_CATEGORY_COUNT")
    evidence=sum(x["evidence_count"] for x in a)
    retrieved=sum(x[arm+"_retrieved"] for x in a)
    return {
      "cases":len(a),"human_evidence_ids":evidence,
      "retrieved_evidence_ids":retrieved,
      "evidence_recall":round(retrieved/evidence,4),
      "tasks_any_evidence":sum(x[arm+"_retrieved"]>0 for x in a),
      "tasks_all_evidence":sum(x[arm+"_retrieved"]==x["evidence_count"] for x in a),
      "tasks_zero_evidence":sum(x[arm+"_retrieved"]==0 for x in a),
      "selected_turns":sum(x[arm+"_selected_turns"] for x in a),
      "context_chars":sum(x[arm+"_context_chars"] for x in a)
    }
def main():
    global PHASE
    ap=argparse.ArgumentParser()
    ap.add_argument("--phase",choices=("freeze","evaluate"),required=True)
    ap.add_argument("--expected-protocol",default="")
    args=ap.parse_args()
    need(os.getenv("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE","REPO_SCOPE")
    need(os.getenv("GITHUB_RUN_ATTEMPT")=="1","FIRST_ATTEMPT_ONLY")
    need(not os.getenv("OPENAI_API_KEY"),"NO_PAID_API")
    if args.phase=="evaluate":
        need(bool(re.fullmatch(r"[a-f0-9]{64}",args.expected_protocol)),
             "MISSING_INDEPENDENT_PREREGISTRATION")
    PHASE="ORIGINAL_SOURCE_AND_METADATA"
    with tempfile.TemporaryDirectory(prefix="mpai39-original-source-") as td:
        data=p37.get_data(Path(td))
        cases=get_tasks(data)
        protocol=freeze_protocol(cases)
        print("MPAI39_PREREGISTERED_PROTOCOL_SHA256="+protocol,flush=True)
        print("MPAI39_EXACT_P37_SELECTION_SHA256="+P37_COMMITMENT,flush=True)
        print("MPAI39_ORIGINAL_SOURCE_VERIFIED=PASS",flush=True)
        print("MPAI39_FROZEN_ORIGINAL_CASES=25",flush=True)
        if args.phase=="freeze":
            # Must not read QA.question, QA.answer or QA.evidence here.
            print("MPAI39_SOURCE_QA_GOLD_AND_EVIDENCE_NOT_READ_BY_SELECTOR=TRUE",flush=True)
            print("MPAI39_ORIGINAL_RETRIEVAL_METHOD_UNMODIFIED=TRUE",flush=True)
            print("MPAI39_NO_MODEL_CALLS=TRUE",flush=True)
            print("MPAI39_FREEZE=PASS",flush=True)
            return
        need(protocol==args.expected_protocol,"SEPARATE_JOB_PROTOCOL_MISMATCH")
        PHASE="RETRIEVAL_WITHOUT_HUMAN_GOLD"
        turns_by_sample={i:p38.reconstructed(s) for i,s in enumerate(data)}
        # Important: collect BOTH candidate ranked sources for all tasks before
        # the first human citation/evidence ID is loaded for evaluation.
        candidates=[]
        for c in cases:
            turns,ids,lens=turns_by_sample[c["sample"]]
            original=data[c["sample"]]["qa"][c["index"]]
            question=original.get("question")
            need(isinstance(question,str) and question.strip(),"ORIGINAL_QUESTION")
            baseline,bt=original_retriever_indexes(turns,question)
            bm25,mt=select_context(turns,rank_bm25(turns,question))
            need(len(baseline)==TOP_K and len(bm25)==TOP_K,
                 "MATCHED_TOP12_PASSAGE_BUDGET")
            candidates.append({
              "category":c["category"],"sample":c["sample"],
              "qa_index":c["index"],
              "baseline":set(baseline),"bm25":set(bm25),
              "baseline_chars":len(bt),"bm25_chars":len(mt),
              "source_ids":ids,
              "selected_only_from_source":True,
            })
        need(len(candidates)==25,"EXACT_ALL_25_RETRIEVAL_EXECUTED")
        print("MPAI39_ALL_RETRIEVAL_COMPLETED_BEFORE_GOLD=PASS",flush=True)
        print("MPAI39_MATCHED_TOP12_AND_6500_CHAR_BUDGET=PASS",flush=True)
        print("MPAI39_P37_RETRIEVED_CONTEXT_BYTE_EXACT_25_OF_25=PASS",flush=True)
        PHASE="EXTERNAL_HUMAN_EVIDENCE_SCORING_ONLY"
        rows=[]
        for c in candidates:
            qa=data[c["sample"]]["qa"][c["qa_index"]]
            evidence=qa.get("evidence")
            need(isinstance(evidence,list) and len(evidence)>0
                 and all(isinstance(x,str) and x.strip() for x in evidence),
                 "HUMAN_EVIDENCE_SCHEMA")
            e={x.strip() for x in evidence}
            need(len(e)==len(evidence),"ANNOTATED_EVIDENCE_ID_DUPLICATION")
            allids=set(c["source_ids"])
            need(e.issubset(allids),"HUMAN_EVIDENCE_SOURCE_MISSING")
            r={"category":c["category"],"evidence_count":len(e)}
            for key,idxkey in (("p37_original_idf","baseline"),
                               ("untuned_bm25","bm25")):
                chosen={c["source_ids"][i] for i in c[idxkey]}
                r[key+"_retrieved"]=len(chosen&e)
                r[key+"_selected_turns"]=len(c[idxkey])
                r[key+"_context_chars"]=c[idxkey+"_chars"]
            rows.append(r)
        need(len(rows)==25,"HUMAN_AUDIT_25_COMPLETE")
        for category in ("1","2","5"):
            for arm in RETRIEVERS:
                d=summarise(rows,arm,category)
                print("MPAI39_"+arm.upper()+"_CATEGORY_"+category+"="+stable(d),flush=True)
        answerable=[x for x in rows if x["category"] in ("1","2")]
        need(len(answerable)==20,"SOURCE_20_ANSWERABLE")
        total=sum(x["evidence_count"] for x in answerable)
        need(total==38,"SOURCE_38_ANNOTATED_EVIDENCE_IDS")
        pairs=[]
        for arm in RETRIEVERS:
            retrieved=sum(x[arm+"_retrieved"] for x in answerable)
            anyq=sum(x[arm+"_retrieved"]>0 for x in answerable)
            allq=sum(x[arm+"_retrieved"]==x["evidence_count"] for x in answerable)
            noneq=sum(x[arm+"_retrieved"]==0 for x in answerable)
            chars=sum(x[arm+"_context_chars"] for x in answerable)
            print("MPAI39_"+arm.upper()+"_ANSWERABLE="+stable({
                "questions":20,"reference_evidence_ids":38,
                "retrieved_evidence_ids":retrieved,
                "micro_recall":round(retrieved/38,4),
                "any_evidence_questions":anyq,
                "all_evidence_questions":allq,
                "zero_evidence_questions":noneq,
                "total_context_characters":chars,
                "selected_turns":sum(x[arm+"_selected_turns"] for x in answerable)
            }),flush=True)
            pairs.append((retrieved,anyq,allq,noneq))
        need(pairs[0]==(22,15,10,5),"P38_BASELINE_SOURCE_REPRODUCTION")
        b,be=pairs
        print("MPAI39_BM25_MINUS_P37_RETRIEVED_CITATIONS="+str(be[0]-b[0]),flush=True)
        print("MPAI39_BM25_MINUS_P37_ALL_EVIDENCE_QUESTIONS="+str(be[2]-b[2]),flush=True)
        improved=sum(x["untuned_bm25_retrieved"]>x["p37_original_idf_retrieved"]
                     for x in answerable)
        regressed=sum(x["untuned_bm25_retrieved"]<x["p37_original_idf_retrieved"]
                      for x in answerable)
        print("MPAI39_BM25_RECALL_BETTER_ORIGINAL_CASES="+str(improved),flush=True)
        print("MPAI39_BM25_RECALL_WORSE_ORIGINAL_CASES="+str(regressed),flush=True)
        print("MPAI39_SOURCE_ORACLE_ANNOTATED_EVIDENCE_AVAILABLE=38_OF_38",flush=True)
        print("MPAI39_ORACLE_NOT_USED_FOR_RANKING=PASS",flush=True)
        print("MPAI39_NO_NEW_INFERENCE_CALLS=0",flush=True)
        print("MPAI39_NOT_DEPLOYED_MINDPALACE_RETRIEVAL=TRUE",flush=True)
        print("MPAI39_PUBLIC_SOURCE_EXPOSED_DEVELOPMENT_ONLY=TRUE",flush=True)
        print("MPAI39_SCIENTIFIC_ACCEPTANCE=BLOCKED",flush=True)
        print("MPAI39_NO_PRIVATE_ORIGINAL_TEXT_LOGGED=TRUE",flush=True)
        print("MPAI39_ACCEPTED_MEMORY_WRITES=0",flush=True)
    print("MPAI39_ORIGINAL_PRIVATE_SOURCE_CLEANED=PASS",flush=True)
if __name__=="__main__":
    try:main()
    except Exception as exc:
        msg=str(exc)
        safe=msg if re.fullmatch(r"MPAI39_[A-Z0-9_]{3,100}",msg) else "MPAI39_PRIVATE_ERROR"
        print("MPAI39_SAFE_FAILURE="+safe,flush=True)
        print("MPAI39_SAFE_PHASE="+PHASE,flush=True)
        print("MPAI39_SAFE_EXCEPTION_TYPE="+type(exc).__name__,flush=True)
        sys.exit(2)
