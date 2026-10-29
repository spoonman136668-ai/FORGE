"""One-shot original-Windows development experiment, never science or memory admission.

Public source-pinned SmolLM2 weights are downloaded before MCP reads. No paid
API, no hosted inference, no production memory writer, no unattended scheduler.
All private records/answers and complete receipts remain in disposable scratch.
"""
from __future__ import annotations

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

SOURCE = "fd9d1d5cec917063a0a9d2d263affe7f0cce3f12"
P4 = "eac1c9098d2784388797a5f6a5c68dd297c66d82"
RECORDS = "fecf51aa59bd24bfac0c852d53f88c88e6d7c9c1de6848e6c1bab5f45a3c9742"
MODEL_SHA = "2fa3f013dcdd7b99f9b237717fa0b12d75bbb89984cc1274be1471a465bac9c2"
MODEL_SIZE = 270590880
MODEL_URL = ("https://huggingface.co/bartowski/SmolLM2-360M-Instruct-GGUF/resolve/"
    "ab928a97ee49f3a015f35194879f68211291d6ca/SmolLM2-360M-Instruct-Q4_K_M.gguf?download=true")
LESSON_ID = "lesson/mpai-hindsight-h2-development-context-efficiency-20261028"
SOURCE_REF = "https://github.com/spoonman136668-ai/FORGE/actions/runs/40802018105"
RUNNER = "FORGE-CODEX-REMOTE/llama_cpp/SmolLM2-360M-Instruct-Q4_K_M"
CASES = (
    ("input_pct", "What percentage reduction in input tokens was measured?", ("52.6",)),
    ("input_counts", "How many input tokens did legacy and tiered retrieval use respectively?", ("3513", "1665")),
    ("context_pct", "What percentage reduction in context bytes was measured?", ("56.1",)),
    ("latency_pct", "What percentage reduction in measured generation time was reported?", ("22.7",)),
    ("model_calls", "How many genuine local CPU GGUF model calls were made?", ("16",)),
    ("case_count", "How many development questions were compared?", ("8",)),
    ("output_cap", "What output-token limit did both arms reach in every case?", ("96",)),
    ("accuracy_limit", "Was a factual accuracy improvement independently graded and proven?", ("NEGATIVE_ACCURACY",)),
)
INSTRUCTIONS = {
 "no_memory": "Use only provided context. Answer briefly; when no evidence exists, say insufficient evidence.",
 "memory_only": "Use only the given evidence; answer accurately, briefly, and abstain when not supported.",
 "memory_reflection": "Apply the reflected output-cap mitigation hypothesis: cite only the exact requested figure or a direct negative answer, in one concise sentence; never invent proof of accuracy.",
 "size_matched_placebo": "Use only the supplied information; if it does not answer the question, state that evidence is insufficient.",
}
ARMS = ("no_memory", "memory_only", "memory_reflection", "size_matched_placebo")

def require(ok: bool, code: str):
    if not ok: raise RuntimeError(code)

def run(argv, cwd=None, input_text=None, timeout=90):
    p=subprocess.run(argv,cwd=cwd,input=input_text,text=True,encoding="utf-8",
       stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    require(p.returncode==0,"MPAI05_P6_SUBPROCESS_FAILED")
    return p.stdout

def get(repo, *args):
    return run(["git","-C",str(repo),*args]).strip()

def rpc(i,name,args):
    return {"jsonrpc":"2.0","id":i,"method":"tools/call",
        "params":{"name":name,"arguments":args}}

def mcp_read(src):
    events=[]
    for index, task in enumerate(("input_pct","latency_pct")):
        events.append({"event_id":"original-feedback-"+str(index),
          "agent_class":"independent-agent", "task_id":task,
          "failure_code":"output_cap_hit",
          "source_ref":SOURCE_REF+"#"+task,
          "source_sha":SOURCE,"result":"failure"})
    experience={"schema":"mind-palace.mpai01-observations.v1",
                "source_sha":SOURCE,"observations":events}
    requests=[
        {"jsonrpc":"2.0","id":1,"method":"initialize",
         "params":{"protocolVersion":"2025-06-18","capabilities":{},
           "clientInfo":{"name":"nonqwen-mpai05-p6-dev","version":"1"}}},
        rpc(2,"mindpalace_bootstrap",{"source_sha":SOURCE}),
        rpc(3,"mindpalace_get_record",
             {"source_sha":SOURCE,"record_id":LESSON_ID,"projects":["Mind-Palace"]}),
        rpc(4,"mindpalace_improvement_cycle",
             {"source_sha":SOURCE,"project":"Mind-Palace",
              "task":"source-linked output cap mitigation with no scientific claim",
              "experience":experience})
    ]
    payload="".join(json.dumps(x,separators=(",",":"))+"\n" for x in requests)
    # Preserve MCP JSON-RPC stdout in private, disposable scratch rather
    # than relying on a shell/Windows pipe-decoding return value.
    mcp_out=src.parent/"private-mcp-response.jsonl"
    with mcp_out.open("wb") as stream:
        proc=subprocess.run(
           [sys.executable,"-B",str(src/"tools/mindpalace_mcp.py"),
            "--root",str(src),"--source",SOURCE,"--project","Mind-Palace","--transport","stdio"],
           cwd=src,input=payload.encode("utf-8"),
           stdout=stream,stderr=subprocess.PIPE,timeout=100,
           env={**os.environ,"PYTHONIOENCODING":"utf-8"})
    require(proc.returncode==0,"MPAI05_P6_MCP_SUBPROCESS")
    replies=mcp_out.read_text(encoding="utf-8")
    require(isinstance(replies,str) and bool(replies.strip()),"MPAI05_P6_MCP_EMPTY")
    responses=[json.loads(x) for x in replies.splitlines()]
    require([r.get("id") for r in responses]==[1,2,3,4],"MPAI05_P6_MCP_ENVELOPE")
    def get_result(index):
        obj=responses[index].get("result")
        require(isinstance(obj,dict) and obj.get("isError") is False,"MPAI05_P6_MCP_ERROR")
        parts=obj.get("content",[])
        require(len(parts)==1 and parts[0].get("type")=="text","MPAI05_P6_MCP_CONTENT")
        return json.loads(parts[0]["text"])
    boot=get_result(1);read=get_result(2);cycle=get_result(3)
    require(boot.get("source_sha")==SOURCE and
        boot.get("records_sha256")==RECORDS and
        boot.get("read_only") is True and
        boot.get("permitted_projects")==["Mind-Palace"],"MPAI05_P6_MCP_SOURCE_DRIFT")
    require(read.get("found") is True and read.get("source_sha")==SOURCE and
        read.get("advisory") is True,"MPAI05_P6_LESSON_ABSENT")
    lesson=read["record"]; statement=lesson.get("statement","")
    refs=lesson.get("source_refs",[])
    require(lesson.get("id")==LESSON_ID and
        lesson.get("project")=="Mind-Palace" and
        len(refs)>0 and isinstance(statement,str) and
        all(x in statement for x in ("52.6%","56.1%","22.7%","3,513","1,665","96-token")),
        "MPAI05_P6_LESSON_CONTENT_DRIFT")
    require(cycle.get("source_sha")==SOURCE and
        cycle.get("records_sha256")==RECORDS and
        cycle.get("phase")=="PROPOSE_ONLY" and
        cycle.get("production_writes")==0 and
        cycle.get("model_calls")==0 and
        cycle.get("deployment_authorized") is False and
        cycle.get("feedback",{}).get("durable_memory_write") is False and
        len(cycle.get("reflection",{}).get("proposals",[]))>=1 and
        cycle["reflection"]["proposals"][0]["failure_code"]=="output_cap_hit",
        "MPAI05_P6_REFLECTION_NOT_GROUNDED")
    return statement,cycle["reflection"]["proposals"][0]["proposal_id"]

def get_model(root):
    model=root/"SmolLM2-360M-Instruct-Q4_K_M.gguf"
    require(shutil.disk_usage(str(root)).free>850000000,"MPAI05_P6_NO_DISK")
    n=0;h=hashlib.sha256();begin=time.monotonic()
    req=urllib.request.Request(MODEL_URL,headers={"User-Agent":"MindPalace-P6-public-model/1"})
    with urllib.request.urlopen(req,timeout=50) as inp,model.open("xb") as out:
        while True:
            b=inp.read(4*1024*1024)
            if not b:break
            n+=len(b)
            require(n<=MODEL_SIZE and time.monotonic()-begin<600,"MPAI05_P6_DOWNLOAD_BOUND")
            h.update(b);out.write(b)
    require(n==MODEL_SIZE and h.hexdigest()==MODEL_SHA,"MPAI05_P6_MODEL_DRIFT")
    with model.open("rb") as f:require(f.read(4)==b"GGUF","MPAI05_P6_MODEL_FORMAT")
    return model

def grade(answer, gold):
    low=answer.casefold();flat=re.sub(r"[, ._]","",low)
    if gold==("NEGATIVE_ACCURACY",):
        return bool(re.search(r"\b(no|not|never|unproven|unknown|cannot|can't|without|lack|insufficient|wasn't|isn't|didn't)\b",low)) and bool(re.search(r"accur|grad|prov|verif|improv|scientif",low))
    return all(value.replace(".","") in flat for value in gold)

def hard_claim(answer):
    low=answer.casefold()
    return 0 if re.search(r"\b(no|not|never|unproven|cannot|can't|without|insufficient|wasn't|isn't)\b",low) else int(bool(re.search(r"(scientifically proven|accuracy (?:was |is )?(?:proven|verified|confirmed|improved)|factual accuracy improved|verified better answers)",low)))

def evaluate(root, statement, proposal_id, model, audit):
    from llama_cpp import Llama
    inference=Llama(model_path=str(model),n_ctx=2048,n_threads=4,n_gpu_layers=0,
      n_batch=128,seed=137,verbose=False)
    placebo=("Unrelated neutral material with no metrics or experimental outcomes. " *
             (len(statement)//48+3))[:len(statement)]
    evidence={
      "no_memory":"",
      "memory_only":statement,
      "memory_reflection":statement,
      "size_matched_placebo":placebo,
    }
    require(len(placebo)==len(statement),"MPAI05_P6_PLACEBO_BYTES")
    harness={a:hashlib.sha256(INSTRUCTIONS[a].encode()).hexdigest() for a in ARMS}
    manifest={
       "schema":audit.SCHEMA,"project":"Mind-Palace",
       "mind_palace_source_sha":SOURCE,"records_sha256":RECORDS,
       "task_origin":{"kind":"repeatable_development","first_use_holdout":False,"development_only":True},
       "task_ids":[x[0] for x in CASES],
       "model":{"name":"SmolLM2-360M-Instruct-Q4_K_M","sha256":MODEL_SHA,
          "runtime_id":RUNNER,"local_execution":True,"paid_api":False,
          "model_calls_authorized":True},
       "budgets":{"max_output_tokens_per_call":192,"evidence_bytes_per_call":2048,
          "sampling_seed":137,"temperature":0,"top_p":1,
          "max_input_tokens_per_call":2048,"allow_network_during_trial":False},
       "harness_sha256":harness,
       "privacy":{"private_context_in_public_logs":False,"private_answers_in_public_logs":False,
                  "accepted_ice_writes":0},
       "scientific_claim":False
    }
    mhash=audit.validate_manifest(manifest)
    receipt={"schema":audit.RECEIPT_SCHEMA,"manifest_sha256":mhash,
       "synthetic":False,"trials":[]}
    responses=[]
    for t,(task_id,question,gold) in enumerate(CASES):
        order=ARMS[t%4:]+ARMS[:t%4]
        for arm in order:
            prompt=([{"role":"system","content":INSTRUCTIONS[arm]},
                     {"role":"user","content":("Evidence:\n"+evidence[arm]+"\n\n" if evidence[arm] else "")+"Question: "+question}])
            start=time.monotonic()
            result=inference.create_chat_completion(messages=prompt,
                   max_tokens=192,temperature=0,top_p=1)
            latency=max(1,int((time.monotonic()-start)*1000))
            choices=result.get("choices",[])
            answer=choices[0].get("message",{}).get("content","") if choices else ""
            usage=result.get("usage",{})
            require(isinstance(answer,str) and isinstance(usage,dict),"MPAI05_P6_ANSWER_INVALID")
            inputs=int(usage.get("prompt_tokens",0))
            output=int(usage.get("completion_tokens",0))
            require(0<inputs<=2048 and 0<output<=192,"MPAI05_P6_TOKEN_BUDGET_OR_EOS")
            receipt["trials"].append({
              "task_id":task_id,"arm":arm,"source_sha":SOURCE,
              "records_sha256":RECORDS,
              "model_sha256":MODEL_SHA,"runtime_id":RUNNER,
              "harness_sha256":harness[arm],
              "input_tokens":inputs,"output_tokens":output,
              "latency_ms":latency,"hit_output_cap":output==192,
              "correct":bool(grade(answer,gold)),
              "hard_false_claims":hard_claim(answer),
              "output_sha256":hashlib.sha256(answer.encode("utf-8")).hexdigest()})
            responses.append({"task_id":task_id,"arm":arm,"answer":answer,
                "input_tokens":inputs,"output_tokens":output})
    require(len(receipt["trials"])==32,"MPAI05_P6_CALL_COUNT")
    outcome=audit.validate_receipts(manifest,receipt)
    require(outcome.get("scientific_accepted") is False and
            outcome.get("development_candidate_budget_eligible") is False and
            outcome.get("model_runtime_authenticated") is False and
            outcome.get("accepted_ice_writes")==0,"MPAI05_P6_UNAUTHORIZED_QUALIFICATION")
    private={"manifest":manifest,"receipt":receipt,"raw_answers":responses,
             "audit":outcome,"reflection_proposal_id":proposal_id}
    (root/"private-development-receipts.json").write_text(
       json.dumps(private,sort_keys=True),encoding="utf-8")
    print("MPAI05_P6_LOCAL_MODEL_CALLS=32",flush=True)
    print("MPAI05_P6_PRIVATE_MCP=PASS",flush=True)
    print("MPAI05_P6_REFLECTION=PROPOSE_ONLY",flush=True)
    for arm in ARMS:
        m=outcome["arms"][arm]
        label=arm.upper()
        for key in ("correct","hard_false_claims","cap_hits","tokens","latency_ms"):
            print("MPAI05_P6_"+label+"_"+key.upper()+"="+str(m[key]),flush=True)
    print("MPAI05_P6_DEVELOPMENT_CANDIDATE_METRICS_PASS_UNVERIFIED="+
       str(outcome["development_candidate_metrics_pass_unverified"]).upper(),flush=True)
    print("MPAI05_P6_DEVELOPMENT_CANDIDATE_BUDGET_ELIGIBLE=FALSE",flush=True)
    print("MPAI05_P6_HOLDOUT_FIRST_USE_VERIFIED=FALSE",flush=True)
    print("MPAI05_P6_INDEPENDENT_GRADING=FALSE",flush=True)
    print("MPAI05_P6_SCIENTIFIC_ACCEPTANCE=FALSE",flush=True)
    print("MPAI05_P6_PRODUCTION_WRITES=0",flush=True)

PHASE = "INITIAL"

def main():
    global PHASE
    root=pathlib.Path(os.environ["MPAI05_P6_SCRATCH"])
    src=root/"mind-palace";evaldir=root/"evaluation"
    PHASE="SCRATCH"
    root.mkdir(parents=True,exist_ok=False)
    require(shutil.disk_usage(str(root)).free>900000000,"MPAI05_P6_SCRATCH_CAPACITY")
    # The proposal checkout hosts P4 audit code, while accepted memory is
    # read only from the exact previously merged main ancestor.
    PHASE="CLONE"
    run(["git","clone","--quiet","--single-branch","--branch",
         "proposal/mpai05-p4-fourarm-source-20261029",
         "https://github.com/spoonman136668-ai/Mind-Palace.git",str(src)],timeout=75)
    PHASE="SOURCE_IDENTITY"
    require(get(src,"rev-parse","HEAD")==P4,"MPAI05_P6_P4_HEAD_DRIFT")
    evaldir.mkdir()
    for fn in ("mpai05_dev_ablation_gate.py","mpai05_local_model_preflight.py"):
        prefix=pathlib.Path("experiments/mpai05_p4")
        target=evaldir/fn
        shutil.copyfile(src/prefix/fn,target)
    PHASE="ACCEPTED_CHECKOUT"
    run(["git","-C",str(src),"checkout","-q","--detach",SOURCE],timeout=75)
    require(get(src,"rev-parse","HEAD")==SOURCE,"MPAI05_P6_ACCEPTED_SOURCE_DRIFT")
    require(not get(src,"status","--porcelain","--untracked-files=all"),"MPAI05_P6_SOURCE_DIRTY")
    PHASE="WEIGHTS"
    model=get_model(root)
    # Public model bytes are verified BEFORE any private lesson is accessed.
    os.environ["HF_HUB_OFFLINE"]="1"
    def net_off(*a,**k): raise RuntimeError("MPAI05_P6_NETWORK_DENIED")
    socket.socket=net_off
    sys.path.insert(0,str(evaldir))
    import mpai05_dev_ablation_gate as audit
    import mpai05_local_model_preflight as weights
    PHASE="WEIGHT_PREFLIGHT"
    try:
        receipt=weights.preflight(model,MODEL_SHA)
    except weights.PreflightError as exc:
        if str(exc)=="MODEL_CHANGED_DURING_PREFLIGHT":
            # Do not weaken P4's identity check. Determine whether a just-
            # closed Windows download has settled, then retry exact verifier
            # only once. A persistent identity discrepancy remains a failure.
            with model.open("rb") as f:
                before=os.fstat(f.fileno())
                time.sleep(0.35)
                after=os.fstat(f.fileno())
                current=model.stat()
            names=("st_dev","st_ino","st_size","st_mtime_ns","st_ctime_ns")
            changed=[name.upper().replace("ST_","") for name in names
                if not (getattr(before,name)==getattr(after,name)==getattr(current,name))]
            if changed:
                raise RuntimeError("MPAI05_P6_GGUF_CHANGED_"+changed[0]) from None
            try:
                receipt=weights.preflight(model,MODEL_SHA)
                print("MPAI05_P6_WEIGHT_PREFLIGHT_SINGLE_RETRY=1",flush=True)
            except weights.PreflightError as newer:
                raise RuntimeError("MPAI05_P6_GGUF_RETRY_"+str(newer)) from None
        else:
            raise
        allowed={"NOT_GGUF","UNSUPPORTED_GGUF_VERSION","OVERSIZE_KV_COUNT",
                 "TRUNCATED_METADATA","DUPLICATE_METADATA_KEY",
                 "NESTED_METADATA_ARRAY","UNKNOWN_METADATA_ARRAY_TYPE",
                 "UNKNOWN_METADATA_TYPE","MISSING_OR_BAD_MODEL_IDENTITY",
                 "ARCHITECTURE_MISSING","QWEN_NOT_ALLOWED",
                 "EXPECTED_SHA256_REQUIRED","ABSOLUTE_GGUF_PATH_REQUIRED",
                 "MODEL_FILE_NOT_FOUND_OR_UNSAFE","MODEL_TOO_SMALL",
                 "MODEL_CHANGED_DURING_PREFLIGHT","CHECKPOINT_SHA256_MISMATCH",
                 "OVERSIZE_STRING","INVALID_STRING","OVERSIZE_ARRAY"}
        reason=str(exc)
        require(reason in allowed,"MPAI05_P6_GGUF_UNKNOWN")
        raise RuntimeError("MPAI05_P6_GGUF_"+reason) from None
    require(receipt.get("status")=="MODEL_FILE_BYTES_PINNED_RUNTIME_NOT_AUTHENTICATED" and
            receipt.get("gguf",{}).get("architecture")!="qwen2",
            "MPAI05_P6_CHECKPOINT_PREFLIGHT")
    PHASE="MCP"
    statement,proposal=mcp_read(src)
    PHASE="INFERENCE"
    evaluate(root,statement,proposal,model,audit)
    PHASE="FINAL_SOURCE_CUSTODY"
    require(not get(src,"status","--porcelain","--untracked-files=all"),"MPAI05_P6_SOURCE_MUTATED")

if __name__=="__main__":
    try:main()
    except Exception as e:
        # Model/user/retrieval contents never appear in public job logs.
        msg=str(e)
        code=(msg if msg.startswith("MPAI05_P6_") and re.fullmatch(r"MPAI05_P6_[A-Z0-9_]{3,80}",msg)
              else "MPAI05_P6_PRIVATE_RUN_FAILED")
        print("MPAI05_P6_SAFE_FAILURE="+code,flush=True)
        print("MPAI05_P6_SAFE_PHASE="+PHASE,flush=True)
        print("MPAI05_P6_SAFE_EXCEPTION="+type(e).__name__,flush=True)
        tb=e.__traceback__
        while tb is not None and tb.tb_next is not None: tb=tb.tb_next
        if tb is not None and tb.tb_frame.f_code.co_name in (
            "main","mcp_read","get_result","evaluate","get_model","run","get",
            "validate_manifest","validate_receipts"):
            print("MPAI05_P6_SAFE_FUNCTION="+tb.tb_frame.f_code.co_name,flush=True)
            print("MPAI05_P6_SAFE_LINE="+str(tb.tb_lineno),flush=True)
        sys.exit(2)
