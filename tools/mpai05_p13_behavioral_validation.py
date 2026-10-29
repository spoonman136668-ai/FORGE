"""MP-AI05 P13. Real original-Windows model-level follow-up of P12.

Same published 16-case P9 development cohort, exact P10 official deterministic
grader, verified local non-Qwen GGUF and frozen input/output budgets. The only
experimental mechanism is the P12 gold-blind IDF-diverse evidence selection.
Results are *PUBLIC DEVELOPMENT* only; no agent/controller/memory deployment.
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

import mpai05_p9_dataset_freeze as p9
import mpai05_p10_public_development as p10
import mpai05_p12_evidence_selection as p12

COHORT_SHA="103dbf87dda69f03b32f4c6a3a987b5ab5b7a8d3c3ceeb11f223ad5cf358ae52"
MODEL_SHA="2fa3f013dcdd7b99f9b237717fa0b12d75bbb89984cc1274be1471a465bac9c2"
P10_SOURCE_BLOB="7bd698e3265cc41ee4d286461980d7586a25ac99"
P12_SOURCE_BLOB="de13820b5598e2cabf8432481b9a34abfd6e461b"
ARMS=("no_memory","lexical_memory","idf_diverse_memory",
      "idf_diverse_reflection","char_matched_placebo")
EXPECTED_GRADED_PER_ARM=11
EXPECTED_UNSCORABLE_PER_ARM=5
MAX_OUTPUT=p10.MAX_OUTPUT_TOKENS
MAX_INPUT=p10.MAX_INPUT_TOKENS
MAX_CONTEXT=p10.CONTEXT_CHARS
SEED=p10.SEED
STAGE="INITIAL"

def require(ok,code):
    if not ok:raise RuntimeError("MPAI05_P13_"+code)

def bytes_sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def prepare_contexts(question,ids,memory):
    """Exactly P10 case history; P12 reranker does not accept gold/scorer."""
    require(type(question) is str and type(ids) is list and len(ids)==100,
            "CASE_INPUT_FORMAT")
    require(all(ident in memory for ident in ids),"CASE_SOURCE_MISSING")
    before=time.process_time_ns()
    lexical=p10.retrieve(question,ids,memory)
    lex_cpu=max(1,time.process_time_ns()-before)
    before=time.process_time_ns()
    index,df=p12.build_index({ident:memory[ident] for ident in ids})
    anchors=p12.score_anchors(question,index,df)
    ranked=p12.pack(p12.diverse(question,anchors))
    idf_cpu=max(1,time.process_time_ns()-before)
    require(len(ranked)<=MAX_CONTEXT and len(lexical)<=MAX_CONTEXT+8,
            "RETRIEVAL_BUDGET")
    neutral=("Neutral unrelated interface notes and generic status information. "*
             (len(ranked)//65+2))[:len(ranked)]
    require(len(neutral)==len(ranked),"PLACEBO_BYTES")
    contexts={
        "no_memory":"",
        "lexical_memory":lexical,
        "idf_diverse_memory":ranked,
        "idf_diverse_reflection":ranked,
        "char_matched_placebo":neutral,
    }
    cpu={
        "no_memory":0,
        "lexical_memory":lex_cpu,
        "idf_diverse_memory":idf_cpu,
        "idf_diverse_reflection":idf_cpu,
        "char_matched_placebo":idf_cpu,
    }
    require(set(contexts)==set(ARMS),"ARM_CONTEXT_DRIFT")
    return contexts,cpu

def system_prompt(arm):
    return {
        "no_memory":p10.SYSTEM["no_memory"],
        "lexical_memory":p10.SYSTEM["memory_only"],
        "idf_diverse_memory":p10.SYSTEM["memory_only"],
        "idf_diverse_reflection":p10.SYSTEM["memory_reflection"],
        "char_matched_placebo":p10.SYSTEM["char_matched_placebo"],
    }[arm]

def summarize(trials,expected_arms=ARMS):
    require(len(trials)==16*len(expected_arms),"TRIAL_COUNT")
    groups={}
    for arm in expected_arms:
        rows=[r for r in trials if r["arm"]==arm]
        require(len(rows)==16,"ARM_TRIAL_COUNT")
        ids={r["case_digest"] for r in rows}
        require(len(ids)==16,"DUPLICATE_CASE_ARM")
        graded=[r for r in rows if r["official_score"] is not None]
        require(len(graded)==EXPECTED_GRADED_PER_ARM,
                "DETERMINISTIC_GRADING_DENOMINATOR")
        groups[arm]={
          "cases":len(rows),
          "official_graded":len(graded),
          "official_correct":sum(int(r["official_score"]) for r in graded),
          "official_unscorable":len(rows)-len(graded),
          "output_cap_hits":sum(int(r["hit_output_cap"]) for r in rows),
          "boxed_nonempty":sum(int(r["boxed_nonempty"]) for r in rows),
          "tokens":sum(r["input_tokens"]+r["output_tokens"] for r in rows),
          "inference_ms":sum(r["inference_ms"] for r in rows),
          "retrieval_cpu_ns":sum(r["retrieval_cpu_ns"] for r in rows),
          "context_chars":sum(r["context_chars"] for r in rows),
        }
        require(groups[arm]["official_unscorable"]==EXPECTED_UNSCORABLE_PER_ARM,
                "UNSCORABLE_DENOMINATOR")
    return groups

def actual_inference(model,questions,selected,haystacks,memory,scorer,root):
    from llama_cpp import Llama
    agent=Llama(model_path=str(model),n_ctx=p10.N_CTX,
        n_threads=4,n_gpu_layers=0,n_batch=128,seed=SEED,verbose=False)
    byid={r["id"]:r for r in questions}
    receipts=[]
    for i,case in enumerate(selected):
        q=byid[case["id"]]
        question=q["question"]
        require(type(question) is str and len(question)<5000,"QUESTION_FORMAT")
        contexts,context_cpu=prepare_contexts(question,haystacks[case["id"]],memory)
        # Context selection and its SHA are frozen before any access to gold.
        frozen={arm:bytes_sha(contexts[arm]) for arm in ARMS}
        require(len(frozen)==len(ARMS),"CONTEXT_HASH")
        scoring=q["eval_function"]
        answer=q["answer"]
        require(type(scoring) is str and type(answer) is str,"SCORER_AND_GOLD_FORMAT")
        # Official scoring is restricted inside p10.official_grade.
        # Unknown or judge-required scoring stays explicitly unscorable.
        rotated=ARMS[i%len(ARMS):]+ARMS[:i%len(ARMS)]
        for arm in rotated:
            messages=[
                {"role":"system","content":system_prompt(arm)},
                {"role":"user","content":
                  "Context:\n"+contexts[arm]+"\n\nQuestion:\n"+question},
            ]
            start=time.perf_counter()
            result=agent.create_chat_completion(messages=messages,temperature=0,
                 top_p=1,max_tokens=MAX_OUTPUT)
            elapsed=max(1,int((time.perf_counter()-start)*1000))
            choices=result.get("choices",[])
            require(len(choices)==1,"CHOICES_COUNT")
            response=choices[0].get("message",{}).get("content","")
            usage=result.get("usage")
            require(type(response) is str and type(usage) is dict,
                    "RESPONSE_USAGE_SCHEMA")
            inp=int(usage.get("prompt_tokens",0))
            out=int(usage.get("completion_tokens",0))
            require(0<inp<=MAX_INPUT and 0<out<=MAX_OUTPUT,
                    "TOKEN_BUDGET")
            extracted=scorer.extract_boxed_answer(response)
            score,reason=p10.official_grade(scorer,scoring,extracted,answer)
            require((score is None and reason!="OFFICIAL_PURE_SCORER") or
                    (type(score) is bool and reason=="OFFICIAL_PURE_SCORER"),
                    "GRADING_CLASSIFICATION")
            receipts.append({
              "case_digest":bytes_sha(case["id"]),
              "arm":arm,
              "context_sha256":frozen[arm],
              "response_sha256":bytes_sha(response),
              "official_score":score,"scorer_status":reason,
              "boxed_nonempty":bool(extracted and str(extracted).strip()),
              "input_tokens":inp,"output_tokens":out,
              "hit_output_cap":out==MAX_OUTPUT,
              "inference_ms":elapsed,
              "retrieval_cpu_ns":context_cpu[arm],
              "context_chars":len(contexts[arm]),
              # Genuine private output retained only in disposable local
              # scratch and never printed or uploaded to GitHub.
              "private_response":response,
            })
    stats=summarize(receipts)
    (root/"private-p13-development.json").write_text(
        json.dumps({"schema":"mpai05.p13.private-development.v1",
            "frozen_cohort_sha256":COHORT_SHA,
            "weights_sha256":MODEL_SHA,
            "source_p10_blob":P10_SOURCE_BLOB,
            "source_p12_blob":P12_SOURCE_BLOB,
            "unblinded_public_development":True,
            "scientific_acceptance":False,
            "trial_receipts":receipts,
            "statistics":stats},sort_keys=True),encoding="utf-8")
    for arm in ARMS:
        print("MPAI05_P13_ARM_"+arm.upper()+"="+
              json.dumps(stats[arm],sort_keys=True,separators=(",",":")))
    b=stats["lexical_memory"]
    c=stats["idf_diverse_memory"]
    strict_improvement=(c["official_correct"]>b["official_correct"] and
       c["tokens"]<=b["tokens"] and
       (c["inference_ms"]*1_000_000+c["retrieval_cpu_ns"])<=
       (b["inference_ms"]*1_000_000+b["retrieval_cpu_ns"]) and
       c["output_cap_hits"]<=b["output_cap_hits"])
    print("MPAI05_P13_COST_NEUTRAL_CANDIDATE_METRICS_PASS_UNVERIFIED="+
          str(strict_improvement).upper())
    print("MPAI05_P13_MODEL_CALLS="+str(len(receipts)))
    print("MPAI05_P13_DEVELOPMENT_CASES=16")
    print("MPAI05_P13_OFFICIAL_DETERMINISTIC_PER_ARM=11")
    print("MPAI05_P13_UNSCORABLE_PER_ARM=5")
    print("MPAI05_P13_PUBLIC_DEVELOPMENT_ONLY=TRUE")
    print("MPAI05_P13_BLINDED_FIRST_USE=FALSE")
    print("MPAI05_P13_INDEPENDENT_SEMANTIC_GRADER=FALSE")
    print("MPAI05_P13_SCIENTIFIC_ACCEPTANCE=FALSE")
    print("MPAI05_P13_PRODUCTION_WRITES=0")

def main():
    global STAGE
    require(os.getenv("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE" and
            os.getenv("RUNNER_NAME")=="FORGE-CODEX-REMOTE",
            "WRONG_ORIGINAL_RUNNER")
    require(not os.getenv("OPENAI_API_KEY"),"PAID_API_CREDENTIAL_PROHIBITED")
    root=Path(os.environ["MPAI05_P13_SCRATCH"])
    require(not root.exists(),"SCRATCH_COLLISION")
    require(shutil.disk_usage(root.parent).free>=3_300_000_000,
            "INSUFFICIENT_SCRATCH_DISK")
    root.mkdir()
    STAGE="OFFICIAL_SOURCE"
    scorer,official=p10.official_scorer(root)
    STAGE="COHORT"
    raw={name:p9.download(name) for name in (
       "checksums.sha256","SCHEMA.md","questions.jsonl",
       "haystacks/lme_v2_small.json")}
    receipt=p9.freeze(raw["questions.jsonl"],raw["haystacks/lme_v2_small.json"],
       raw["SCHEMA.md"],raw["checksums.sha256"])
    require(receipt["cohort_sha256"]==COHORT_SHA and
            receipt["development_case_count"]==16,"COHORT_DRIFT")
    questions=[json.loads(z) for z in raw["questions.jsonl"].decode("utf-8").splitlines()
               if z.strip()]
    haystacks=json.loads(raw["haystacks/lme_v2_small.json"])
    selected=p9.choose(questions,haystacks)["cohort"]
    require(len(selected)==16,"CASE_COUNT")
    required={}
    for case in selected:
        for tid in haystacks[case["id"]]:
            if tid in required:require(required[tid]==case["domain"],"DOMAIN_DRIFT")
            required[tid]=case["domain"]
    STAGE="TRAJECTORY_BYTES"
    trajectories=root/"trajectories.jsonl"
    p10.download(
        f"https://huggingface.co/datasets/{p9.REPO}/resolve/{p9.REVISION}/"
        "trajectories.jsonl?download=true",
        trajectories,p10.SHA_TRAJECTORIES,p10.BYTES_TRAJECTORIES)
    STAGE="TRAJECTORY_TEXT"
    memory=p10.get_text_trajectories(trajectories,required)
    require(len(memory)==len(required)==200,"TRAJECTORY_COUNT")
    STAGE="PUBLIC_MODEL_BYTES"
    model=root/"SmolLM2-360M-Instruct-Q4_K_M.gguf"
    p10.download(p10.MODEL_URL,model,MODEL_SHA,p10.BYTES_MODEL)
    STAGE="OFFLINE_INFERENCE"
    os.environ["HF_HUB_OFFLINE"]="1"
    def deny_network(*args,**kwargs):
        raise RuntimeError("MPAI05_P13_NETWORK_DISABLED_DURING_INFERENCE")
    socket.socket=deny_network
    actual_inference(model,questions,selected,haystacks,memory,scorer,root)
    require(not p10.run(["git","status","--porcelain","--untracked-files=all"],official),
            "OFFICIAL_SOURCE_CHANGED")
    print("MPAI05_P13_OFFICIAL_SCORER_SOURCE=PASS")
    print("MPAI05_P13_PUBLIC_DATA_AND_MODEL_SHA256=PASS")
    print("MPAI05_P13_FROZEN_COHORT_SHA256="+COHORT_SHA)

if __name__=="__main__":
    try:main()
    except Exception as e:
        code=str(e)
        safe=code if re.fullmatch(r"MPAI05_P13_[A-Z0-9_]{3,80}",code) else "PRIVATE_EXCEPTION"
        print("MPAI05_P13_SAFE_FAILURE="+safe,flush=True)
        print("MPAI05_P13_SAFE_PHASE="+STAGE,flush=True)
        print("MPAI05_P13_SAFE_EXCEPTION="+type(e).__name__,flush=True)
        sys.exit(2)
