"""MP-AI33: truly externally authored and human-labeled adversarial NLI data.

Gold labels are from original pinned facebookresearch/ANLI hard-dev analysis
(license CC BY-NC 4.0). Dataset and classifications publicly released;
therefore NOT a blinded, contamination-proven scientific first-use holdout.
Pre-model Linux preregistration selects 36 distinct source UIDs by metadata
only without accessing question, premise or gold values. Windows independently
checks the exact source, frozen selection and then runs 36 genuine Phi-3.5
local model comparisons with P31 frozen lexical veto and strict exact check.
No human labels are changed or printed; no paid API, production memory writes,
FORGE controller, model promotion or hidden holdout claim.
"""
from __future__ import annotations
from collections import Counter
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import socket
import sys
import tempfile
import time
import urllib.request

import mpai30_real_semantic_judge_canaries as p30
import mpai31_conservative_semantic_veto_development as p31

ANLI_COMMIT="b5ce27af54a53bd495af7260fdc485000eed15f8"
ANLI_BLOB="c8c1e7a8ea43ae08efec608a5dae7203810fda08"
ANLI_PATH="anlizinganli/anli_annot_v0.2/ANLI_analysis_hard_dev.csv"
ANLI_BYTES=119033
ANLI_URL="https://raw.githubusercontent.com/facebookresearch/anli/"+ANLI_COMMIT+"/"+ANLI_PATH
P30_BLOB="0fa02bc09fae04f72c49f555fa7063e31f546f6c"
P31_BLOB="97510664d981e3bf70dbcc2f1002fd40945150d4"
P30_PROTO="325cd39377bd3dd6e736ac6ccf5c8dc3205420bad92df60c1ba5d4ea03ab0477"
P31_PROTO="192c5c7c7678ebc89e4b35ff1ebe7e2b82dbc60b782b8dcc4cbdfd538b3a06bc"
SOURCE_FAMILIES=(
  "Basic-Negation",
  "Tricky-Syntactic",
  "Tricky-Pragmatic",
  "Reference-Coreference",
  "Basic-Lexical-Similar",
  "Reasoning-Facts",
)
PER_FAMILY=6
STAGE="INIT"

def must(value,code):
    if not value:raise RuntimeError("MPAI33_"+code)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(o):
    return json.dumps(o,sort_keys=True,separators=(",",":"),ensure_ascii=True)

def source_download(private):
    path=private/"anli-original-private.csv"
    must(not path.exists(),"SOURCE_OVERWRITE")
    request=urllib.request.Request(ANLI_URL,headers={
        "User-Agent":"MPAI33-source-verified-anli-noncommercial-research/1"})
    h=hashlib.sha1();count=0
    with urllib.request.urlopen(request,timeout=45) as inp,path.open("xb") as out:
        while True:
            data=inp.read(128*1024)
            if not data:break
            count+=len(data)
            must(count<=ANLI_BYTES,"SOURCE_SIZE")
            out.write(data)
    must(count==ANLI_BYTES,"ANLI_ORIGINAL_BYTES_CHANGED")
    data=path.read_bytes()
    h.update(b"blob "+str(len(data)).encode()+b"\0"+data)
    must(h.hexdigest()==ANLI_BLOB,"ANLI_ORIGINAL_GIT_BLOB")
    print("MPAI33_ANLI_ORIGINAL_SOURCE_GIT_BLOB=PASS",flush=True)
    print("MPAI33_ANLI_ORIGINAL_SOURCE_BYTES="+str(count),flush=True)
    return path

def source_rows(path):
    # The pre-model selector accesses UID and original author error-code
    # categories exclusively. Gold, premise, hypothesis, reviewer notes and
    # wrong upstream model outputs are not read by the selector.
    with path.open("r",encoding="utf-8-sig",newline="") as file:
        rdr=csv.DictReader(file)
        must(set(("uid","context","statement","gold_label","A1Code")).issubset(
             set(rdr.fieldnames or ()),"ANLI_FIELDS")
        rows=list(rdr)
    must(len(rows)==177,"ANLI_ORIGINAL_ROW_COUNT")
    must(len({r["uid"] for r in rows})==len(rows),"ANLI_UID_DUPLICATION")
    return rows

def select(rows):
    chosen=[];seen=set()
    # Sorted UUIDs, no content or labels used. Error taxonomy provided by
    # independent ANLI annotators, fixed before inspecting model outputs.
    for group in SOURCE_FAMILIES:
        candidates=sorted((r for r in rows if group in
          {x.strip() for x in r["A1Code"].split(",")} and
          r["uid"] not in seen),key=lambda r:r["uid"])
        must(len(candidates)>=PER_FAMILY,"ANLI_CATEGORY_SIZE")
        for row in candidates[:PER_FAMILY]:
            chosen.append({"uid":row["uid"],"category":group})
            seen.add(row["uid"])
    must(len(chosen)==36 and len(seen)==36,"SELECTED_36_UIDS")
    must(Counter(x["category"] for x in chosen)==
         {x:PER_FAMILY for x in SOURCE_FAMILIES},"SELECTED_BALANCE")
    must(all(re.fullmatch(r"[a-zA-Z0-9-]{8,100}",x["uid"]) for x in chosen),
         "PUBLIC_UID_SHAPE")
    manifest={"schema":"mpai33-anli-independent-author-source-metadata-only-v1",
      "upstream_author":"facebookresearch/anli",
      "source_commit":ANLI_COMMIT,"source_git_blob":ANLI_BLOB,
      "prior_p30_blob":P30_BLOB,"prior_p31_blob":P31_BLOB,
      "prior_p30_protocol":P30_PROTO,"prior_p31_protocol":P31_PROTO,
      "model_sha256":p30.MODEL_SHA,
      "source_license":"CC-BY-NC-4.0","original_human_annotation":True,
      "first_use_independently_blinded":False,
      "source_hypothesis_or_gold_in_commitment":False,
      "selection":chosen,
      "labels":{"e":"YES","c":"NO","n":"UNKNOWN"},
      "protocol":"P30 original judge, P31 frozen guard, exact strict comparator",
      "purpose":"advisory offline noncommercial research; no benchmark tuning"}
    return chosen,sha(canonical(manifest).encode())

def prereg_digest(chosen,manifest_sha):
    return sha(canonical({"manifest_sha":manifest_sha,
      "source_commit":ANLI_COMMIT,"source_blob":ANLI_BLOB,
      "model_sha":p30.MODEL_SHA,"model_prompt":P30_PROTO,
      "guard_source":P31_BLOB,"36_human_labeled_tasks":len(chosen),
      "independent_source_yes":"not independent first use",
      "no_scorer_promotion":True}).encode())

def check_previous():
    must(p30.protocol()==P30_PROTO and p31.prereg_digest()==P31_PROTO,
         "PREEXISTING_PROTOCOL_CHANGED")
    must(p30.MODEL_SHA==p31.MODEL_SHA and p30.MODEL_BYTES==p31.MODEL_BYTES
         and p30.MODEL_REV==p31.MODEL_REV,"MODEL_IDENTITY_MISMATCH")

def peak():
    return p30.peak_working_set()

def main():
    global STAGE
    p=argparse.ArgumentParser()
    p.add_argument("--phase",choices=("freeze","evaluate"),required=True)
    p.add_argument("--expected-manifest-sha",default="")
    p.add_argument("--expected-protocol-sha",default="")
    args=p.parse_args()
    must(os.getenv("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE",
         "REPO_ID")
    must(os.getenv("GITHUB_RUN_ATTEMPT")=="1","FIRST_RUN_ATTEMPT")
    must(not os.getenv("OPENAI_API_KEY"),"PAID_API_DISABLED")
    check_previous()
    if args.phase=="evaluate":
        must(os.name=="nt" and os.getenv("RUNNER_NAME")=="FORGE-CODEX-REMOTE",
            "ORIGINAL_WINDOWS")
        must(re.fullmatch(r"[a-f0-9]{64}",args.expected_manifest_sha or ""),
            "EXPECTED_MANIFEST_NOT_PINNED")
        must(re.fullmatch(r"[a-f0-9]{64}",args.expected_protocol_sha or ""),
            "EXPECTED_PROTOCOL_NOT_PINNED")
        scratch=Path(os.environ["MPAI33_PRIVATE_SCRATCH"])
        must(not scratch.exists() and shutil.disk_usage(scratch.parent).free>3500000000,
             "PRIVATE_SCRATCH_OR_DISK")
        scratch.mkdir()
        private=scratch
    else:
        scratch=None
        private=Path(tempfile.mkdtemp(prefix="mpai33-original-source-"))
    try:
        STAGE="AUTHENTIC_UPSTREAM"
        source=source_download(private)
        rows=source_rows(source)
        STAGE="METADATA_SELECTION"
        chosen,manifest=select(rows)
        protocol=prereg_digest(chosen,manifest)
        print("MPAI33_FROZEN_SELECTION_SHA256="+manifest,flush=True)
        print("MPAI33_FROZEN_PROTOCOL_SHA256="+protocol,flush=True)
        print("MPAI33_PRESELECTED_UPSTREAM_ROWS=36",flush=True)
        print("MPAI33_INDEPENDENT_ANNOTATED_ERROR_CATEGORIES=6",flush=True)
        print("MPAI33_METADATA_ONLY_SELECTION=PASS",flush=True)
        if args.phase=="freeze":
            print("MPAI33_ORIGINAL_GOLD_NOT_READ_AT_FREEZE=TRUE",flush=True)
            print("MPAI33_PREMODEL_SELECTION_FROZEN=PASS",flush=True)
            print("MPAI33_MODEL_CALLS=0",flush=True)
            return
        must(manifest==args.expected_manifest_sha and
             protocol==args.expected_protocol_sha,
             "LINUX_COMMITMENT_MISMATCH")
        print("MPAI33_FROZEN_SELECTION_RECOMPUTED=PASS",flush=True)
        # Source gold text is consumed only *after* frozen selection, for
        # scores. Source hypothesis and premise are exposed to model, but
        # source answers/annotations and reasons are never model inputs.
        uid_map={r["uid"]:r for r in rows}
        tasks=[]
        for one in chosen:
            original=uid_map[one["uid"]]
            g=original["gold_label"].strip().lower()
            must(g in {"e","c","n"},"ORIGINAL_HUMAN_LABEL")
            premise=original["context"]
            hypothesis=original["statement"]
            must(premise.strip() and hypothesis.strip(),"EMPTY_SOURCE_QUESTION")
            must(len(premise)<8500 and len(hypothesis)<900,
                 "CONTEXT_CHARACTER_BUDGET")
            tasks.append((one["uid"],one["category"],premise,hypothesis,
                          {"e":"YES","c":"NO","n":"UNKNOWN"}[g]))
        print("MPAI33_ALL_36_EXTERNAL_ORIGINAL_GOLD_LABELS_VERIFIED=PASS",flush=True)
        STAGE="MODEL_DOWNLOAD"
        model_path=private/p30.MODEL_NAME
        p30.download_model(model_path)
        print("MPAI33_PINNED_MODEL_FULL_SHA256=PASS",flush=True)
        os.environ["HF_HUB_OFFLINE"]="1"
        socket.socket=lambda *a,**kw: (_ for _ in ()).throw(
           RuntimeError("MPAI33_NO_NETWORK_AFTER_MODEL_FREEZE"))
        from llama_cpp import Llama,LlamaGrammar
        grammar=LlamaGrammar.from_string('root ::= ("YES" | "NO" | "UNKNOWN")',
                                         verbose=False)
        t0=time.perf_counter()
        model=Llama(model_path=str(model_path),n_ctx=3072,n_threads=4,
                    n_gpu_layers=0,n_batch=128,seed=p30.SEED,verbose=False)
        load_ms=max(1,int((time.perf_counter()-t0)*1000))
        must(load_ms<120000,"MODEL_LOAD_TIME")
        STAGE="INFERENCE"
        trials=[]
        for uid,category,premise,hypothesis,gold in tasks:
            started=time.perf_counter()
            output=model.create_chat_completion(
                 messages=p30.messages(premise,hypothesis),
                 temperature=0,top_p=1,max_tokens=p30.MAX_OUT,grammar=grammar)
            choices=output.get("choices",[])
            must(len(choices)==1,"ONE_COMPLETION")
            raw=choices[0].get("message",{}).get("content","")
            info=output.get("usage",{})
            tokens=int(info.get("prompt_tokens",0))
            completion=int(info.get("completion_tokens",0))
            must(isinstance(raw,str) and 0<tokens<=3000 and
                 0<completion<=p30.MAX_OUT,"TOKEN_BUDGET")
            base=p30.parse(raw)
            guard=p31.conservative_guard(base,hypothesis)
            strict=p31.strict_comparator(premise,hypothesis)
            trials.append({"uid_sha256":sha(uid.encode()),"category":category,
              "gold":gold,"baseline":base,"guard":guard,"strict":strict,
              "veto":bool(base=="YES" and p31.veto(hypothesis)),
              "tokens":tokens+completion,
              "latency_ms":max(1,int((time.perf_counter()-started)*1000))})
        must(len(trials)==36,"MODEL_CALL_COUNT")
        (private/"private_adversarial_trials.json").write_text(
            json.dumps({"manifest":manifest,"model":p30.MODEL_SHA,
              "is_blind_holdout":False,"independent_original_human_labels":True,
              "trials":trials},sort_keys=True),encoding="utf-8")
        for family in SOURCE_FAMILIES:
            zz=[x for x in trials if x["category"]==family]
            must(len(zz)==6,"FAMILY_DENOMINATOR")
            counts=Counter(x["gold"] for x in zz)
            print("MPAI33_FAMILY_"+family.upper().replace("-","_")+"="+
                 json.dumps({"cases":6,
                   "original_gold_labels":dict(counts),
                   "baseline_correct":sum(x["baseline"]==x["gold"] for x in zz),
                   "guard_correct":sum(x["guard"]==x["gold"] for x in zz),
                   "veto_changed":sum(x["guard"]!=x["baseline"] for x in zz),
                   "baseline_hard_fp":sum(x["baseline"]=="YES" and x["gold"]!="YES" for x in zz),
                   "guard_hard_fp":sum(x["guard"]=="YES" and x["gold"]!="YES" for x in zz)},
                   sort_keys=True,separators=(",",":")),flush=True)
        for arm in ("baseline","guard","strict"):
            fp=sum(t[arm]=="YES" and t["gold"]!="YES" for t in trials)
            exact=sum(t[arm]==t["gold"] for t in trials)
            yes=sum(t[arm]=="YES" and t["gold"]=="YES" for t in trials)
            support=sum(t["gold"]=="YES" for t in trials)
            print("MPAI33_"+arm.upper()+"_CORRECT="+str(exact)+"_OF_36",flush=True)
            print("MPAI33_"+arm.upper()+"_HARD_FALSE_POSITIVES="+str(fp),flush=True)
            print("MPAI33_"+arm.upper()+"_SUPPORTED_ENTAILMENTS="+
                  str(yes)+"_OF_"+str(support),flush=True)
        total_veto=sum(t["guard"]!=t["baseline"] for t in trials)
        guardfp=sum(t["guard"]=="YES" and t["gold"]!="YES" for t in trials)
        print("MPAI33_GUARD_CHANGED_DECISIONS="+str(total_veto),flush=True)
        print("MPAI33_GUARD_ZERO_HARD_FP="+("PASS" if guardfp==0 else "FAIL"),flush=True)
        print("MPAI33_REAL_LOCAL_MODEL_CALLS=36",flush=True)
        print("MPAI33_ORIGINAL_WINDOWS_PROCESS_PEAK_BYTES="+str(peak()),flush=True)
        print("MPAI33_MODEL_LOAD_MS="+str(load_ms),flush=True)
        print("MPAI33_EXTERNAL_SOURCE_PUBLIC_CONTAMINATION_UNEXCLUDED=TRUE",flush=True)
        print("MPAI33_LLM_JUDGE_SCIENTIFIC_ADMISSION=BLOCKED",flush=True)
        print("MPAI33_PRODUCTION_MEMORY_WRITES=0",flush=True)
    finally:
        shutil.rmtree(private)
        print("MPAI33_PRIVATE_SCRATCH_CLEAN=PASS",flush=True)

if __name__=="__main__":
    try:main()
    except Exception as err:
        msg=str(err)
        label=msg if re.fullmatch(r"MPAI33_[A-Z0-9_]{3,100}",msg) else "MPAI33_PRIVATE_EXCEPTION"
        print("MPAI33_SAFE_FAILURE="+label,flush=True)
        print("MPAI33_SAFE_PHASE="+STAGE,flush=True)
        print("MPAI33_SAFE_ERROR_TYPE="+type(err).__name__,flush=True)
        sys.exit(2)
