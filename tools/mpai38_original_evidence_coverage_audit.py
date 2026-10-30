"""MP-AI38 authentic LoCoMo source evidence coverage, no new model calls.

Precommits exactly the 25 question IDs selected in MP-AI37. The audit job
then verifies independent human citation IDs against original conversation
dia_id entries, reproduces byte-for-byte the original MP-AI37 unsupervised
retrieved source text, and scores ID-level evidence coverage/recall@12.
Questions, answers, original turn text and evidence IDs are NEVER published.
This is diagnostic evidence *availability*, not proof of correct reasoning,
not new scientific first use, and not deployed Mind-Palace retrieval.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path

import mpai37_external_memory_effect as p37

P37_FROZEN="123411ed33446deded98c45dd3c5e54a98620b8565a8612b7bea1c594131c5b8"
P37_BLOB="f1305323279cf56c1fdda068a5d14933dfbe6ca7"
SCHEMA_BLOB="ca4fb37467f8aa886ef442b0e387fa06d82709c2"
STAGE="INIT"
CATEGORY_COUNTS={"1":10,"2":10,"5":5}

def need(v,code):
    if not v:raise RuntimeError("MPAI38_"+code)
def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=True)
def sha(x):
    return hashlib.sha256(x.encode()).hexdigest()
def selected(data):
    task,commit=p37.freeze(data)
    need(commit==P37_FROZEN,"ORIGINAL_P37_FROZEN_IDENTITY_CHANGED")
    need(len(task)==25 and Counter(x["category"] for x in task)==CATEGORY_COUNTS,
         "ORIGINAL_25_CATEGORIES_CHANGED")
    return task
def protocol(selected):
    return sha(canonical({
        "schema":"mpai38-authentic-original-evidence-annotation-coverage-v1",
        "source_git_blob":p37.source.LOCOMO_BLOB,
        "p37_original_source_blob":P37_BLOB,
        "p37_original_task_sha256":P37_FROZEN,
        "p37_schema_probe_blob":SCHEMA_BLOB,
        "original_tasks":selected,
        "measure":"human-annotated LoCoMo qa.evidence dia_id versus source-selected top12",
        "retrieval":"unchanged original p37 IDF, 6500 chars, top12, restore chronology",
        "comparison":"full-original-readable-turn oracle, not model answer",
        "category5":"adversarial citation only, NOT valid positive-answer evidence",
        "full_answer_scoring":False,
        "model_calls":0,"production_memory_writes":0,"scientific_acceptance":False,
    }))
def reconstructed(sample):
    conv=sample["conversation"]
    turns=[];ids=[];sizes=[]
    pairs=sorted((int(k[8:]),k) for k,v in conv.items()
                 if re.fullmatch(r"session_\d+",k) and isinstance(v,list))
    need(len(pairs)>0,"EMPTY_SESSIONS")
    for num,key in pairs:
        day=conv.get(key+"_date_time","")
        day=day[:45] if isinstance(day,str) else ""
        for turn in conv[key]:
            if not isinstance(turn,dict) or not isinstance(turn.get("text"),str):
                continue
            txt=turn["text"].strip()
            if not txt:continue
            dia=turn.get("dia_id")
            need(isinstance(dia,str) and dia.strip(),"MISSING_SOURCE_DIA_ID")
            full=f"Session {num} {day} | "+str(turn.get("speaker",""))[:70]+": "+txt
            turns.append(full[:700])
            ids.append(dia.strip())
            sizes.append(len(full))
    need(turns==p37.source_turns(sample),"TURN_TEXT_OR_ORDER_DRIFT")
    # Ensure an original evidence ID cannot reference two different turns
    # and be accidentally over-credited as supporting the answer.
    need(len(ids)==len(set(ids)),"SOURCE_DIA_ID_DUPLICATION")
    return turns,ids,sizes
def selected_indexes(turns,q):
    query=p37.terms(q)
    need(bool(query),"ORIGINAL_QUESTION_NO_SEARCH_TERMS")
    docs=[p37.terms(t) for t in turns]
    counts=Counter(x for doc in docs for x in doc)
    n=len(docs)
    ranked=[]
    for i,doc in enumerate(docs):
        weight=sum(math.log(1+(n-counts[token]+.5)/(counts[token]+.5))
                   for token in query&doc)
        ranked.append((-weight,i))
    indices=[];size=0
    for _,i in sorted(ranked):
        if size+len(turns[i])>6500:continue
        indices.append(i);size+=len(turns[i])+1
        if len(indices)==12:break
    need(len(indices)>=4,"ORIGINAL_RETRIEVER_SMALL")
    original="\n".join(turns[i] for i in sorted(indices))
    # EXACT verification against original P37 retriever, not a new retriever.
    need(original==p37.retrieve(turns,q),"P37_RETRIEVED_TEXT_MISMATCH")
    return indices,original
def summary(records,category):
    a=[x for x in records if x["category"]==category]
    expected=CATEGORY_COUNTS[category]
    need(len(a)==expected,"CATEGORY_AUDIT_DENOMINATOR")
    citations=sum(x["evidence_count"] for x in a)
    source_citations=sum(x["source_found_count"] for x in a)
    hits=sum(x["retrieved_count"] for x in a)
    source_available=sum(x["all_source_found"] for x in a)
    any_hit=sum(x["any_retrieved"] for x in a)
    full_hit=sum(x["all_retrieved"] for x in a)
    zero_hit=sum(x["retrieved_count"]==0 for x in a)
    # Oracle denominator counts all evidence IDs mentioned by original
    # human annotations, including IDs missing from readable text.
    return {"cases":len(a),"human_evidence_ids":citations,
      "ids_present_in_original_dialogue":source_citations,
      "ids_selected_by_original_retriever":hits,
      "micro_original_source_evidence_recall":round(source_citations/citations,4),
      "micro_retrieved_evidence_recall":round(hits/citations,4),
      "cases_all_citations_exist_in_source":source_available,
      "cases_any_citation_retrieved":any_hit,
      "cases_all_citations_retrieved":full_hit,
      "cases_zero_citations_retrieved":zero_hit,
      "selected_source_turns":sum(x["selected_turns"] for x in a),
      "selected_original_support_turns_with_text_truncated":
           sum(x["retrieved_truncated"] for x in a)}
def main():
    global STAGE
    ap=argparse.ArgumentParser()
    ap.add_argument("--phase",choices=("freeze","audit"),required=True)
    ap.add_argument("--expected-protocol",default="")
    args=ap.parse_args()
    need(os.getenv("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE",
         "OWNER_REPOSITORY")
    need(os.getenv("GITHUB_RUN_ATTEMPT")=="1","FIRST_ATTEMPT")
    need(not os.getenv("OPENAI_API_KEY"),"PAID_API_FORBIDDEN")
    if args.phase=="audit":
        need(re.fullmatch("[0-9a-f]{64}",args.expected_protocol or ""),
             "FROZEN_PROTOCOL_NOT_PRESENT")
    STAGE="IMMUTABLE_ORIGINAL_SOURCE"
    with tempfile.TemporaryDirectory(prefix="mpai38-source-evidence-") as scratch:
        data=p37.get_data(Path(scratch))
        chosen=selected(data)
        commitment=protocol(chosen)
        print("MPAI38_ORIGINAL_P37_SELECTION_SHA256="+P37_FROZEN,flush=True)
        print("MPAI38_PREREGISTERED_PROTOCOL_SHA256="+commitment,flush=True)
        print("MPAI38_ORIGINAL_25_CASES=25",flush=True)
        print("MPAI38_SOURCE_AUTHENTIC_GIT_BLOB=PASS",flush=True)
        if args.phase=="freeze":
            print("MPAI38_NO_GOLD_OR_SOURCE_EVIDENCE_READ_BY_FREEZE=TRUE",flush=True)
            print("MPAI38_NO_MODEL_CALLS_IN_FIRST_JOB=TRUE",flush=True)
            print("MPAI38_FIRST_JOB_FREEZE=PASS",flush=True)
            return
        need(commitment==args.expected_protocol,"FIRST_JOB_PROTOCOL_MISMATCH")
        print("MPAI38_SEPARATE_JOB_SOURCE_AND_SELECTION_RECOMPUTED=PASS",flush=True)
        STAGE="SOURCE_EVIDENCE_IDENTITY_VS_ORIGINAL_RETRIEVAL"
        cache={}
        for s in chosen:
            i=s["sample"]
            if i not in cache:
                cache[i]=reconstructed(data[i])
        records=[]
        for s in chosen:
            turns,ids,orig_lengths=cache[s["sample"]]
            q=data[s["sample"]]["qa"][s["index"]]
            question=q.get("question")
            need(isinstance(question,str) and question.strip(),"QUESTION_SCHEMA")
            evidence=q.get("evidence")
            need(isinstance(evidence,list) and len(evidence)>0 and
                 all(isinstance(z,str) and z.strip() for z in evidence),
                 "SOURCE_HUMAN_EVIDENCE_SCHEMA")
            citations=set(z.strip() for z in evidence)
            need(len(citations)==len(evidence),"DUPLICATE_HUMAN_EVIDENCE_IDS")
            selected_indices,_=selected_indexes(turns,question)
            readable=set(ids)
            picked={ids[j] for j in selected_indices}
            actual=citations&picked
            matching={j for j in selected_indices if ids[j] in citations}
            records.append({"category":s["category"],
                "evidence_count":len(citations),
                "source_found_count":len(citations&readable),
                "retrieved_count":len(actual),
                "any_retrieved":bool(actual),
                "all_retrieved":citations.issubset(picked),
                "all_source_found":citations.issubset(readable),
                "selected_turns":len(selected_indices),
                "retrieved_truncated":sum(orig_lengths[j]>700 for j in matching)})
        need(len(records)==25,"FULL_25_ORIGINAL_TASK_AUDIT")
        report={c:summary(records,c) for c in ("1","2","5")}
        for c,v in report.items():
            print("MPAI38_CATEGORY_"+c+"="+canonical(v),flush=True)
        answerable=[r for r in records if r["category"]!="5"]
        need(len(answerable)==20,"ANSWERABLE_DENOMINATOR")
        total=summary(records,"1")
        vals=summary(records,"2")
        es=total["human_evidence_ids"]+vals["human_evidence_ids"]
        hs=total["ids_selected_by_original_retriever"]+vals["ids_selected_by_original_retriever"]
        found=total["ids_present_in_original_dialogue"]+vals["ids_present_in_original_dialogue"]
        print("MPAI38_ANSWERABLE_GOLD_EVIDENCE_IDS="+str(es),flush=True)
        print("MPAI38_ANSWERABLE_SOURCE_PRESENT_EVIDENCE_IDS="+str(found),flush=True)
        print("MPAI38_ANSWERABLE_RETRIEVED_EVIDENCE_IDS="+str(hs),flush=True)
        print("MPAI38_ANSWERABLE_EVIDENCE_RECALL_AT_12="+str(round(hs/es,4)),flush=True)
        print("MPAI38_ANSWERABLE_TASKS_WITH_ANY_HUMAN_EVIDENCE="+
              str(sum(x["any_retrieved"] for x in answerable))+"_OF_20",flush=True)
        print("MPAI38_ANSWERABLE_TASKS_WITH_ALL_HUMAN_EVIDENCE="+
              str(sum(x["all_retrieved"] for x in answerable))+"_OF_20",flush=True)
        print("MPAI38_ANSWERABLE_TASKS_WITH_NO_HUMAN_EVIDENCE="+
              str(sum(not x["any_retrieved"] for x in answerable))+"_OF_20",flush=True)
        print("MPAI38_ALL_25_ORIGINAL_RETRIEVED_PASSAGES_BYTE_FOR_BYTE_VERIFIED=PASS",flush=True)
        print("MPAI38_CATEGORY5_REFERENCES_NOT_INTERPRETED_AS_POSITIVE_GOLD=TRUE",flush=True)
        print("MPAI38_ALL_SOURCE_DIALOGUE_ANSWER_QUALITY=NOT_EVALUATED",flush=True)
        print("MPAI38_ACTUAL_MINDPALACE_RETRIEVAL_EFFECT=NOT_TESTED",flush=True)
        print("MPAI38_MODEL_INFERENCE_CALLS=0",flush=True)
        print("MPAI38_PRIVATE_SOURCE_AND_GOLD_LOGGED=FALSE",flush=True)
        print("MPAI38_INDEPENDENT_FIRST_USE=NOT_ATTESTED",flush=True)
        print("MPAI38_SCIENTIFIC_ACCEPTANCE=FALSE",flush=True)
        print("MPAI38_PRODUCTION_MEMORY_WRITES=0",flush=True)
    print("MPAI38_PRIVATE_SOURCE_CLEAN=PASS",flush=True)
if __name__=="__main__":
    try:main()
    except Exception as err:
        s=str(err)
        code=s if re.fullmatch(r"MPAI38_[A-Z0-9_]{3,110}",s) else "MPAI38_PRIVATE_EXCEPTION"
        print("MPAI38_SAFE_FAILURE="+code,flush=True)
        print("MPAI38_SAFE_STAGE="+STAGE,flush=True)
        print("MPAI38_SAFE_EXCEPTION_TYPE="+type(err).__name__,flush=True)
        sys.exit(2)
