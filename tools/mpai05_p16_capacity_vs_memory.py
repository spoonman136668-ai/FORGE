"""P16: 360M versus 1.7B on P15's disjoint public development cohort.

Matched original P10 lexical and P12 IDF-diverse retrieval and no-memory
control. Official deterministic grader only; no paid API, Qwen, science or
accepted-memory changes. Complete private outputs destroyed with scratch.
"""
from __future__ import annotations
import gc, hashlib, json, os, re, shutil, socket, sys, time
from pathlib import Path
import mpai05_p9_dataset_freeze as p9
import mpai05_p10_public_development as p10
import mpai05_p12_evidence_selection as p12
import mpai05_p15_model_qualification as p15

COHORT="81be63f61ee45231985c9341419a3abb1f42f40930a95be8337d16375ba1b696"
MODELS=("smollm2_360m","smollm2_1p7b")
ARMS=("no_memory","lexical_memory","idf_diverse_memory")
WEIGHTS={
  "smollm2_360m":(p10.MODEL_URL,p10.MODEL_SIZE if hasattr(p10,"MODEL_SIZE") else p10.BYTES_MODEL,
                 "2fa3f013dcdd7b99f9b237717fa0b12d75bbb89984cc1274be1471a465bac9c2",
                 "SmolLM2-360M-Instruct-Q4_K_M.gguf"),
  "smollm2_1p7b":(p15.MODEL_URL,p15.MODEL_EXACT_BYTES,p15.MODEL_SHA256,p15.MODEL_FILE)}
STAGE="INITIAL"

def require(ok,reason):
    if not ok:raise RuntimeError("MPAI05_P16_"+reason)
def digest(s):return hashlib.sha256(s.encode("utf-8")).hexdigest()

def make_context(question,ids,memory):
    require(len(ids)==100 and all(t in memory for t in ids),"CASE_HISTORY_ID_DRIFT")
    start=time.process_time_ns()
    lexical=p10.retrieve(question,ids,memory)
    lex_ns=max(1,time.process_time_ns()-start)
    start=time.process_time_ns()
    index,df=p12.build_index({t:memory[t] for t in ids})
    idf=p12.pack(p12.diverse(question,p12.score_anchors(question,index,df)))
    idf_ns=max(1,time.process_time_ns()-start)
    require(len(lexical)<=p10.CONTEXT_CHARS+8 and len(idf)<=p10.CONTEXT_CHARS,
            "CONTEXT_BUDGET")
    return {"no_memory":"","lexical_memory":lexical,"idf_diverse_memory":idf},{
            "no_memory":0,"lexical_memory":lex_ns,"idf_diverse_memory":idf_ns}

def prepare(rows,cohort,small,memory):
    index={row["id"]:row for row in rows}
    result=[]
    for selected in cohort:
        row=index[selected["id"]]
        require(type(row["question"]) is str and
                type(row["answer"]) is str and
                type(row["eval_function"]) is str,"QUESTION_OR_SCORER_SCHEMA")
        contexts,cpu=make_context(row["question"],small[selected["id"]],memory)
        result.append({"id":selected["id"],"question":row["question"],
                       "answer":row["answer"],"spec":row["eval_function"],
                       "contexts":contexts,"cpu":cpu})
    require(len(result)==16,"CASE_COUNT")
    return result

def evaluate(model_id,model_path,cases,scorer):
    from llama_cpp import Llama
    start=time.perf_counter()
    agent=Llama(model_path=str(model_path),n_ctx=p10.N_CTX,n_threads=4,
          n_gpu_layers=0,n_batch=128,seed=p10.SEED,verbose=False)
    load_ms=max(1,int(1000*(time.perf_counter()-start)))
    require(load_ms<120000,"MODEL_LOAD_TIME")
    trials=[]
    for i,case in enumerate(cases):
        rotated=ARMS[i%3:]+ARMS[:i%3]
        for arm in rotated:
            context=case["contexts"][arm]
            prompt=p10.SYSTEM["no_memory"] if arm=="no_memory" else p10.SYSTEM["memory_only"]
            start=time.perf_counter()
            output=agent.create_chat_completion(
              messages=[{"role":"system","content":prompt},
                        {"role":"user","content":"Context:\n"+context+
                                                 "\n\nQuestion:\n"+case["question"]}],
              temperature=0,top_p=1,max_tokens=p10.MAX_OUTPUT_TOKENS)
            latency_ms=max(1,int(1000*(time.perf_counter()-start)))
            choices=output.get("choices",[])
            require(len(choices)==1,"RESPONSE_CHOICES")
            answer=choices[0].get("message",{}).get("content","")
            usage=output.get("usage")
            require(type(answer) is str and type(usage) is dict,
                    "INFERENCE_RESPONSE_SCHEMA")
            inp=int(usage.get("prompt_tokens",0));out=int(usage.get("completion_tokens",0))
            require(0<inp<=p10.MAX_INPUT_TOKENS and 0<out<=p10.MAX_OUTPUT_TOKENS,
                    "INFERENCE_TOKEN_CAP")
            parsed=scorer.extract_boxed_answer(answer)
            grade,reason=p10.official_grade(scorer,case["spec"],parsed,case["answer"])
            require((grade is None and reason!="OFFICIAL_PURE_SCORER") or
                    (type(grade) is bool and reason=="OFFICIAL_PURE_SCORER"),
                    "GRADE_SCHEMA")
            trials.append({"case_sha256":digest(case["id"]),"arm":arm,
                "context_sha256":digest(context),"response_sha256":digest(answer),
                "official_grade":grade,"grading_reason":reason,
                "input_tokens":inp,"output_tokens":out,"inference_ms":latency_ms,
                "retrieval_cpu_ns":case["cpu"][arm],"context_chars":len(context),
                "output_cap_hit":out==p10.MAX_OUTPUT_TOKENS,
                "private_response":answer})
    peak=p15.windows_peak_working_set()
    require(peak<=p15.MAX_PEAK_WORKING_SET_BYTES,"PROCESS_MEMORY_CAP")
    del agent
    gc.collect()
    return trials,load_ms,peak

def aggregate(trials):
    require(len(trials)==48,"MODEL_CALL_COUNT")
    result={}
    refs=[]
    for arm in ARMS:
        rows=[t for t in trials if t["arm"]==arm]
        require(len(rows)==16 and len({r["case_sha256"] for r in rows})==16,
                "PER_ARM_DENOMINATOR")
        scored=[x for x in rows if x["official_grade"] is not None]
        refs.append({r["case_sha256"] for r in scored})
        result[arm]={"calls":16,"graded":len(scored),
          "unscorable":16-len(scored),
          "correct":sum(int(r["official_grade"]) for r in scored),
          "tokens":sum(r["input_tokens"]+r["output_tokens"] for r in rows),
          "inference_ms":sum(r["inference_ms"] for r in rows),
          "retrieval_cpu_ns":sum(r["retrieval_cpu_ns"] for r in rows),
          "output_cap_hits":sum(int(r["output_cap_hit"]) for r in rows),
          "context_chars":sum(r["context_chars"] for r in rows)}
    require(refs[0]==refs[1]==refs[2] and len(refs[0])>=1,
            "SCORABLE_SET_INCONSISTENT")
    return result,refs[0]

def main():
    global STAGE
    require(os.name=="nt" and os.getenv("RUNNER_NAME")=="FORGE-CODEX-REMOTE"
           and os.getenv("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE",
           "ORIGINAL_WINDOWS_HOST")
    require(not os.getenv("OPENAI_API_KEY"),"PAID_API_FORBIDDEN")
    root=Path(os.environ["MPAI05_P16_SCRATCH"])
    require(not root.exists() and
       shutil.disk_usage(root.parent).free>3500000000,"SCRATCH_CAPACITY_OR_COLLISION")
    root.mkdir()
    STAGE="OFFICIAL_SOURCE"
    scorer,checkout=p10.official_scorer(root)
    STAGE="COHORT"
    raw={k:p9.download(k) for k in ("checksums.sha256","SCHEMA.md",
            "questions.jsonl","haystacks/lme_v2_small.json")}
    p9.freeze(raw["questions.jsonl"],raw["haystacks/lme_v2_small.json"],
              raw["SCHEMA.md"],raw["checksums.sha256"])
    rows=[json.loads(z) for z in raw["questions.jsonl"].decode("utf-8").splitlines() if z.strip()]
    small=json.loads(raw["haystacks/lme_v2_small.json"])
    cohort=p15.new_cohort(rows,small)
    require(cohort["digest"]==COHORT and cohort["overlap"]==0,
            "NEW_COHORT_HASH_OR_OVERLAP")
    wanted={}
    for item in cohort["selected"]:
        for tid in small[item["id"]]:
            if tid in wanted:require(wanted[tid]==item["domain"],"CROSS_DOMAIN")
            wanted[tid]=item["domain"]
    STAGE="TRAJECTORIES"
    full=root/"trajectories.jsonl"
    p10.download(f"https://huggingface.co/datasets/{p9.REPO}/resolve/"
                 f"{p9.REVISION}/trajectories.jsonl?download=true",
                 full,p10.SHA_TRAJECTORIES,p10.BYTES_TRAJECTORIES)
    history=p10.get_text_trajectories(full,wanted)
    require(len(history)==len(wanted)==200,"TRAJECTORY_COUNT")
    cases=prepare(rows,cohort["selected"],small,history)
    del history
    STAGE="MODEL_CHECKSUMS"
    files={}
    for name in MODELS:
        url,count,hashvalue,filename=WEIGHTS[name]
        path=root/filename
        p10.download(url,path,hashvalue,count)
        files[name]=path
    STAGE="OFFLINE_INFERENCE"
    os.environ["HF_HUB_OFFLINE"]="1"
    def no_network(*a,**kw):raise RuntimeError("MPAI05_P16_NETWORK_DISABLED")
    socket.socket=no_network
    results={};summaries={};scorable=[]
    for name in MODELS:
        trials,load_ms,peak=evaluate(name,files[name],cases,scorer)
        stats,ids=aggregate(trials)
        scorable.append(ids)
        summaries[name]={"load_ms":load_ms,"peak_bytes":peak,"arms":stats}
        results[name]=trials
        print("MPAI05_P16_FINISHED_"+name.upper()+"=PASS",flush=True)
    require(scorable[0]==scorable[1],"SCORABLE_CASES_MODEL_DRIFT")
    require(sum(len(a) for a in results.values())==96,"TOTAL_MODEL_CALLS")
    require(not p10.run(["git","status","--porcelain","--untracked-files=all"],checkout),
            "OFFICIAL_SOURCE_CHANGED")
    (root/"private-results.json").write_text(json.dumps(
       {"cohort":COHORT,"model_results":results,"summary":summaries,
        "scientific_acceptance":False},sort_keys=True),encoding="utf-8")
    for name in MODELS:
        print("MPAI05_P16_"+name.upper()+"_LOAD_MS="+str(summaries[name]["load_ms"]))
        print("MPAI05_P16_"+name.upper()+"_PEAK_BYTES="+str(summaries[name]["peak_bytes"]))
        for arm in ARMS:
            print("MPAI05_P16_ARM_"+name.upper()+"_"+arm.upper()+"="+
                  json.dumps(summaries[name]["arms"][arm],sort_keys=True,
                             separators=(",",":")))
    print("MPAI05_P16_ACTUAL_LOCAL_MODEL_CALLS=96")
    print("MPAI05_P16_FROZEN_COHORT_SHA256="+COHORT)
    print("MPAI05_P16_OFFICIAL_PUBLISHED_DATA=PASS")
    print("MPAI05_P16_OFFICIAL_SCORER=PASS")
    print("MPAI05_P16_VERIFIED_MODEL_SHA256=2_PASS")
    print("MPAI05_P16_PREVIOUS_PUBLIC_CASES_EXCLUDED=TRUE")
    print("MPAI05_P16_PUBLIC_DEVELOPMENT_ONLY=TRUE")
    print("MPAI05_P16_INDEPENDENT_FIRST_USE=FALSE")
    print("MPAI05_P16_INDEPENDENT_SEMANTIC_GRADING=FALSE")
    print("MPAI05_P16_SCIENTIFIC_ACCEPTANCE=FALSE")
    print("MPAI05_P16_PRODUCTION_WRITES=0")
if __name__=="__main__":
    try:main()
    except Exception as exc:
        text=str(exc)
        code=text if re.fullmatch(r"MPAI05_P16_[A-Z0-9_]{3,80}",text) else "PRIVATE_EXCEPTION"
        print("MPAI05_P16_SAFE_FAILURE="+code,flush=True)
        print("MPAI05_P16_SAFE_STAGE="+STAGE,flush=True)
        print("MPAI05_P16_SAFE_ERROR_TYPE="+type(exc).__name__,flush=True)
        sys.exit(2)
