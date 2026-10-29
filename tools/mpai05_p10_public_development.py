"""P10 original-Windows PUBLIC-DEVELOPMENT 16-case benchmark comparison.

Source-reproducible study of the frozen P9 cohort; no scientific first-use,
production memory, hosted model API, Qwen weights, hidden first-use or writes.
Unscorable official LLM-judge cases remain in the denominator, not guessed.
"""
from __future__ import annotations
import collections
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

import mpai05_p9_dataset_freeze as p9

SHA_TRAJECTORIES = "363cec9a8e87aa8d9101ce4e600aadbf7031d674056ebe4f969e8424abc5f3c6"
BYTES_TRAJECTORIES = 1195604539
SHA_MODEL = "2fa3f013dcdd7b99f9b237717fa0b12d75bbb89984cc1274be1471a465bac9c2"
BYTES_MODEL = 270590880
MODEL_URL=("https://huggingface.co/bartowski/SmolLM2-360M-Instruct-GGUF/resolve/"
           "ab928a97ee49f3a015f35194879f68211291d6ca/"
           "SmolLM2-360M-Instruct-Q4_K_M.gguf?download=true")
MODEL_ORIGINAL_PUBLIC_SMOKE="https://github.com/spoonman136668-ai/FORGE/actions/runs/40844959248"
UPSTREAM_REPO="https://github.com/xiaowu0162/LongMemEval-V2.git"
OFFICIAL_COMMIT="2cc8c540bdb87fe6761629b585e727e1c4704520"
OFFICIAL_SCORER_BLOB="6197efa64d1d47bff73c2523f4728c41ec78fd74"
PIN_COHORT="103dbf87dda69f03b32f4c6a3a987b5ab5b7a8d3c3ceeb11f223ad5cf358ae52"
ARMS=("no_memory","memory_only","memory_reflection","char_matched_placebo")
SYSTEM={
  "no_memory":"Answer only from supplied context. If not known, respond exactly \\boxed{UNKNOWN}. Give final answer as \\boxed{answer}.",
  "memory_only":"Answer only from relevant history, without guessing. If unknown respond \\boxed{UNKNOWN}. Give \\boxed{answer}.",
  "memory_reflection":"Check stale or contradictory UI history. Use only supported evidence, abstain if unsure. Give \\boxed{answer}.",
  "char_matched_placebo":"Use only context. If not known, respond \\boxed{UNKNOWN}. Give \\boxed{answer}.",
}
MAX_OUTPUT_TOKENS=96
MAX_INPUT_TOKENS=2048
CONTEXT_CHARS=2300
N_CTX=3072
SEED=137
MAX_REQUEST_SECONDS=650
SCORER_ALLOWED=frozenset({
    "norm_phrase_set_match","norm_phrase_set_match_ordered",
    "mc_choice_match","mc_choice_set_match",
})
JUDGE_REQUIRED=frozenset({"llm_abstention_checker","llm_gotchas_checker"})
SAFE_PHASE="INITIAL"

def require(condition: bool,code:str):
    if not condition: raise RuntimeError("MPAI05_P10_"+code)

def digest(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()

def download(url:str, dest:pathlib.Path, expected_hash:str, exact_bytes:int,
             timeout:int=650):
    require(not dest.exists(),"DESTINATION_ALREADY_EXISTS")
    started=time.monotonic(); n=0; h=hashlib.sha256()
    req=urllib.request.Request(url,headers={"User-Agent":"MindPalace-P10-public-development/1"})
    with urllib.request.urlopen(req,timeout=45) as inp,dest.open("xb") as out:
        while True:
            b=inp.read(4*1024*1024)
            if not b:break
            n+=len(b)
            require(n<=exact_bytes and time.monotonic()-started<timeout,"DOWNLOAD_BOUND")
            h.update(b);out.write(b)
    require(n==exact_bytes and h.hexdigest()==expected_hash,"SOURCE_FILE_SHA_OR_SIZE_DRIFT")

def run(cmd:list[str], cwd:pathlib.Path,timeout:int=80)->str:
    p=subprocess.run(cmd,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                     timeout=timeout,encoding="utf-8",errors="replace")
    require(p.returncode==0,"PINNED_SOURCE_SUBPROCESS_FAILED")
    return p.stdout.strip()

def official_scorer(root:pathlib.Path):
    checkout=root/"official"
    run(["git","clone","-q","--depth","20","--single-branch","--branch","main",
         UPSTREAM_REPO,str(checkout)],root)
    require(run(["git","rev-parse","HEAD"],checkout)==OFFICIAL_COMMIT,"OFFICIAL_SOURCE_SHA_DRIFT")
    blob=run(["git","rev-parse","HEAD:evaluation/qa_eval_metrics.py"],checkout)
    require(blob==OFFICIAL_SCORER_BLOB,"OFFICIAL_SCORER_BLOB_DRIFT")
    require(not run(["git","status","--porcelain","--untracked-files=all"],checkout),
            "OFFICIAL_SOURCE_DIRTY")
    spec=importlib.util.spec_from_file_location("lme_v2_p10_official_scorer",
                 checkout/"evaluation"/"qa_eval_metrics.py")
    require(spec is not None and spec.loader is not None,"OFFICIAL_SCORER_IMPORT")
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod,checkout

def get_text_trajectories(path:pathlib.Path,wanted:dict[str,str]):
    """Read complete SHA-verified official JSONL but retain text for selected IDs only."""
    selected={}
    seen=set()
    with path.open("r",encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():continue
            row=json.loads(line)
            ident=row.get("id")
            require(type(ident) is str and len(ident)<256,"TRAJECTORY_ID_MALFORMED")
            if ident not in wanted:continue
            require(ident not in seen,"TRAJECTORY_DUPLICATE")
            seen.add(ident)
            require(row.get("domain")==wanted[ident],"TRAJECTORY_DOMAIN_MISMATCH")
            states=row.get("states")
            require(type(states) is list,"TRAJECTORY_STATES_INVALID")
            chunks=[]
            goal=str(row.get("goal",""))[:600]
            if goal:chunks.append("Goal: "+goal)
            for st in states[:150]:
                if type(st) is not dict:continue
                for name,limit in (("action",260),("accessibility_tree",1100),("thought",160)):
                    val=st.get(name)
                    if type(val) is str and val.strip():
                        chunks.append(name+": "+val[:limit].replace("\r"," ").replace("\n"," ") )
            # Text-only interface: screenshot fields ignored and never opened.
            selected[ident]=chunks[:520]
    require(seen==set(wanted),"TRAJECTORY_SELECTION_INCOMPLETE")
    return selected

def tokenize(text:str)->set[str]:
    return {x for x in re.findall(r"[a-z0-9]{3,}",text.casefold()) if x not in {
        "the","and","for","with","that","this","from","your","what","where",
        "when","how","are","will","would","which","into","have","does","using"}}

def retrieve(question:str, ids:list[str],trajectories:dict[str,list[str]])->str:
    q=tokenize(question)
    rank=[]
    for ident in ids:
        for idx,segment in enumerate(trajectories[ident]):
            subset=segment[:1150]
            overlap=len(q & tokenize(subset))
            if overlap:
                # Fixed tie-breakers; no gold-answer lookup.
                rank.append((-overlap,ident,idx,subset))
    rank.sort()
    out=[]
    for neg,ident,idx,value in rank:
        line="Evidence ["+ident[:8]+":"+str(idx)+"]: "+value
        if sum(len(x) for x in out)+len(line)>CONTEXT_CHARS:continue
        out.append(line)
        if len(out)>=8:break
    return "\n".join(out)

def official_grade(scorer,spec:str,prediction:str,answer:str)->tuple[bool|None,str]:
    require(type(spec) is str,"SCORER_SPEC_TYPE")
    name=scorer.eval_name(spec)
    if name in JUDGE_REQUIRED:
        return None,"OFFICIAL_LLM_JUDGE_NOT_AUTHORIZED"
    if name not in SCORER_ALLOWED:
        return None,"OFFICIAL_UNRECOGNIZED_OR_UNSUPPORTED_SCORER"
    # No calls to scorer when LLM judge or unknown function name.
    res=scorer.eval_from_spec(spec,prediction,answer)
    return bool(scorer.score_to_bool(res)),"OFFICIAL_PURE_SCORER"

def run_model(modelpath:pathlib.Path,questions:list[dict],cohort:list[dict],
              haystacks:dict[str,list[str]],memories:dict[str,list[str]],
              scorer,root:pathlib.Path):
    from llama_cpp import Llama
    agent=Llama(model_path=str(modelpath),n_ctx=N_CTX,
         n_threads=4,n_gpu_layers=0,n_batch=128,seed=SEED,verbose=False)
    by_id={x["id"]:x for x in questions}
    trial=[]
    for idx,item in enumerate(cohort):
        row=by_id[item["id"]]
        question=row["question"]
        answer=row["answer"]
        scorer_spec=row["eval_function"]
        require(type(question) is str and len(question)<5000 and type(answer) is str,
                "QUESTION_TEXT_OR_GOLD_FORMAT")
        ids=haystacks[item["id"]]
        evidence=retrieve(question,ids,memories)
        placebo=("Neutral unrelated interface notes and generic status information. " *
                (len(evidence)//65+2))[:len(evidence)]
        require(len(evidence)==len(placebo),"PLACEBO_NOT_EQUAL_CHARS")
        # The same frozen response task, model and assessor; only context policy varies.
        contexts={"no_memory":"","memory_only":evidence,
            "memory_reflection":evidence,"char_matched_placebo":placebo}
        order=ARMS[idx%4:]+ARMS[:idx%4]
        for arm in order:
            system=SYSTEM[arm]
            user="Context:\n"+contexts[arm]+"\n\nQuestion:\n"+question
            started=time.perf_counter()
            result=agent.create_chat_completion(
                messages=[{"role":"system","content":system},
                          {"role":"user","content":user}],
                temperature=0,top_p=1,max_tokens=MAX_OUTPUT_TOKENS)
            dt=max(1,int((time.perf_counter()-started)*1000))
            choice=result["choices"][0]
            raw=choice.get("message",{}).get("content","") or ""
            usage=result.get("usage",{})
            inputs=int(usage.get("prompt_tokens",0))
            outputs=int(usage.get("completion_tokens",0))
            require(0<inputs<=MAX_INPUT_TOKENS and 0<outputs<=MAX_OUTPUT_TOKENS,
                    "INFERENCE_TOKEN_CAP")
            parsed=scorer.extract_boxed_answer(raw)
            score,reason=official_grade(scorer,scorer_spec,parsed,answer)
            trial.append({
              "id":item["id"],"domain":item["domain"],"family":item["kind"],
              "arm":arm,"response_sha256":digest(raw.encode("utf-8")),
              "input_tokens":inputs,"output_tokens":outputs,
              "latency_ms":dt,"output_cap":outputs==MAX_OUTPUT_TOKENS,
              "official_score":score,"score_status":reason,
              # Raw answers in disposable private scratch, never public stdout.
              "private_response":raw,
            })
    require(len(trial)==16*len(ARMS),"TRIAL_COUNT_INVALID")
    require(len({(x["id"],x["arm"]) for x in trial})==len(trial),
            "DUPLICATE_ARM_CASE")
    (root/"private-evaluation-receipts.json").write_text(
        json.dumps(trial,sort_keys=True),encoding="utf-8")
    for arm in ARMS:
        group=[t for t in trial if t["arm"]==arm]
        graded=[x for x in group if x["official_score"] is not None]
        stats={
         "calls":len(group),"official_graded":len(graded),
         "official_correct":sum(int(x["official_score"]) for x in graded),
         "unscorable":len(group)-len(graded),
         "total_tokens":sum(x["input_tokens"]+x["output_tokens"] for x in group),
         "total_ms":sum(x["latency_ms"] for x in group),
         "cap_hits":sum(x["output_cap"] for x in group)}
        print("MPAI05_P10_ARM_"+arm.upper()+"="+json.dumps(stats,sort_keys=True,separators=(",",":")))
    print("MPAI05_P10_ACTUAL_MODEL_CALLS=64")
    print("MPAI05_P10_DATASET_CASES=16")
    print("MPAI05_P10_OFFICIAL_BLIND_GRADING=FALSE")
    print("MPAI05_P10_PRIVATE_HOLDOUT_FIRST_USE=FALSE")
    print("MPAI05_P10_SCIENTIFIC_ADMISSION=FALSE")
    print("MPAI05_P10_PRODUCTION_WRITES=0")

def main():
    global SAFE_PHASE
    require(os.environ.get("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE" and
            os.environ.get("RUNNER_NAME")=="FORGE-CODEX-REMOTE",
            "UNAUTHORIZED_ORIGINAL_RUNNER")
    require("OPENAI_API_KEY" not in os.environ,"PAID_API_CREDENTIAL_DENIED")
    root=pathlib.Path(os.environ["MPAI05_P10_SCRATCH"])
    require(not root.exists(),"SCRATCH_ALREADY_EXISTS")
    require(shutil.disk_usage(root.parent).free>=3_300_000_000,
            "ORIGINAL_HOST_DISK_TOO_SMALL")
    root.mkdir()
    SAFE_PHASE="SOURCE"
    scorer,official=official_scorer(root)
    SAFE_PHASE="P9_COHORT"
    raw={name:p9.download(name) for name in
         ("checksums.sha256","SCHEMA.md","questions.jsonl","haystacks/lme_v2_small.json")}
    freeze=p9.freeze(raw["questions.jsonl"],raw["haystacks/lme_v2_small.json"],
        raw["SCHEMA.md"],raw["checksums.sha256"])
    require(freeze["cohort_sha256"]==PIN_COHORT and freeze["development_case_count"]==16,
            "COHORT_SHA_OR_SIZE_CHANGED")
    rows=[json.loads(x) for x in raw["questions.jsonl"].decode("utf-8").splitlines() if x.strip()]
    small=json.loads(raw["haystacks/lme_v2_small.json"])
    selected=p9.choose(rows,small)["cohort"]
    require(len(selected)==16,"COHORT_CASE_COUNT")
    # All selected ids and their gold answers remain private scratch, not logs.
    required={}
    for item in selected:
        for tid in small[item["id"]]:
            if tid in required:require(required[tid]==item["domain"],"CROSS_DOMAIN_REUSE")
            required[tid]=item["domain"]
    SAFE_PHASE="TRAJECTORY_BYTES"
    file=root/"trajectories.jsonl"
    download(f"https://huggingface.co/datasets/{p9.REPO}/resolve/{p9.REVISION}/trajectories.jsonl?download=true",
             file,SHA_TRAJECTORIES,BYTES_TRAJECTORIES)
    SAFE_PHASE="TRAJECTORY_PARSE"
    mem=get_text_trajectories(file,required)
    require(len(mem)==len(required),"TEXT_MEMORY_INCOMPLETE")
    SAFE_PHASE="MODEL_BYTES"
    modelpath=root/"SmolLM2-360M-Instruct-Q4_K_M.gguf"
    download(MODEL_URL,modelpath,SHA_MODEL,BYTES_MODEL)
    SAFE_PHASE="INFERENCE"
    os.environ["HF_HUB_OFFLINE"]="1"
    def net_denied(*args,**kwargs):raise RuntimeError("MPAI05_P10_NETWORK_DISABLED_DURING_TRIAL")
    socket.socket=net_denied
    run_model(modelpath,rows,selected,small,mem,scorer,root)
    require(not run(["git","status","--porcelain","--untracked-files=all"],official),
            "OFFICIAL_SOURCE_DIRTY_AFTER")
    print("MPAI05_P10_ORIGINAL_OFFICIAL_SCORER_BLOB=PASS")
    print("MPAI05_P10_PUBLIC_DATA_SHA256=PASS")
    print("MPAI05_P10_MODEL_SHA256=PASS")
    print("MPAI05_P10_DATA_COHORT_SHA256="+PIN_COHORT)

if __name__=="__main__":
    try:main()
    except Exception as error:
        reason=str(error)
        if re.fullmatch(r"MPAI05_P10_[A-Z0-9_]+",reason):
            print("MPAI05_P10_SAFE_FAILURE="+reason,flush=True)
        else:
            print("MPAI05_P10_SAFE_FAILURE=PRIVATE_EXCEPTION",flush=True)
        print("MPAI05_P10_SAFE_PHASE="+SAFE_PHASE,flush=True)
        print("MPAI05_P10_SAFE_TYPE="+type(error).__name__,flush=True)
        sys.exit(2)
