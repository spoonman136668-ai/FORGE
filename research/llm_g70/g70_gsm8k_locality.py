#!/usr/bin/env python3
"""G70 disjoint held-out GSM8K locality-dose GPT-2 localhost HTTP screen.

This benchmark is not a production serving system or science acceptance.
"""
import collections
import concurrent.futures
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import statistics
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL_REV="607a30d783dfa663caf39e06633721c8d4cfcd7e"
WEIGHTS_SHA="248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
DATA_REPO="openai/grade-school-math"
DATA_REV="3101c7d5072418e28b9008a6636bde82a006892c"
DATA_FILE="grade_school_math/data/test.jsonl"
DATA_SHA="3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14"
PREREG="672447c13730c5e841956f4e017b0722517b90d3"
SEED=b"G68-GPT2-HELDOUT-20261030:"
ARMS=("baseline_incremental","hf_generate","shared_prefix")
SHARED_COUNT={"reuse_0":0,"reuse_25":3,"reuse_50":6,"reuse_75":9}
COHORTS=tuple(SHARED_COUNT)
CASES=12
SELECT_OFFSET=12
TOKENS=8
CPU_BUDGET=3
REPEATS=2
CACHE_ENTRIES=2
CACHE_BYTES=42_000_000
THRESHOLDS={"reuse_0":0.98,"reuse_25":0.98,"reuse_50":1.10,"reuse_75":1.30,"reuse_75_p95_ratio":1.20}

def load_module(name,relative):
    p=Path(__file__).resolve().parents[1]/relative
    s=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

def sha256_file(filename):
    h=hashlib.sha256()
    with open(filename,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def select_heldout(records):
    """Sort independent natural instructions by frozen key, with no model scores."""
    eligible=[]
    for row,record in enumerate(records):
        if not isinstance(record,dict):
            continue
        instruction=record.get("instruction","")
        category=record.get("category","")
        if isinstance(instruction,str) and instruction.strip() and isinstance(category,str) and category.strip():
            key=hashlib.sha256(SEED+instruction.encode("utf-8")).hexdigest()
            eligible.append((key,row,instruction,category))
    eligible.sort(key=lambda z:(z[0],z[1]))
    selected=[]
    seen=set()
    for digest,row,instruction,category in eligible:
        if instruction in seen:
            continue
        seen.add(instruction)
        selected.append({"source_row":row,"instruction":instruction,
                         "category":category,"instruction_sha256":hashlib.sha256(instruction.encode()).hexdigest(),
                         "rank_sha256":digest})
        if len(selected)==CASES+SELECT_OFFSET:
            break
    if len(selected)!=CASES+SELECT_OFFSET:
        raise RuntimeError("INSUFFICIENT_DISTINCT_HUMAN_INSTRUCTIONS")
    return selected[SELECT_OFFSET:]

def observe_cache(history,key):
    """First sighting never admits; any later sighting can admit."""
    admit=key in history
    history.add(key)
    return admit

def p95(values):
    return sorted(values)[max(0,math.ceil(len(values)*.95)-1)]

def contract():
    assert len(ARMS)==3 and len(COHORTS)==4 and CASES==12 and SELECT_OFFSET==12
    assert SHARED_COUNT=={"reuse_0":0,"reuse_25":3,"reuse_50":6,"reuse_75":9}
    assert REPEATS==2 and TOKENS==8 and CPU_BUDGET==3
    assert (CACHE_ENTRIES,CACHE_BYTES)==(2,42_000_000)
    assert THRESHOLDS=={"reuse_0":0.98,"reuse_25":0.98,"reuse_50":1.10,"reuse_75":1.30,"reuse_75_p95_ratio":1.20}
    assert not observe_cache(set(),(1,2))
    seen=set()
    assert not observe_cache(seen,(1,2))
    assert observe_cache(seen,(1,2))
    assert p95(list(range(12)))==11

class PrefixStore:
    """Shared future makes a single authentic prefill for each admitted prefix."""
    def __init__(self,torch,model,capacity_bytes,capacity_entries):
        self.torch=torch
        self.model=model
        self.cap_bytes=capacity_bytes
        self.cap_entries=capacity_entries
        self.lock=threading.Lock()
        self.history=set()
        self.data=collections.OrderedDict()
        self.stats={"hits":0,"misses":0,"admissions":0,"evictions":0,"skips":0,
                    "producer_waits":0,"max_retained_bytes":0,"max_retained_entries":0}
    def _nbytes(self,past):
        return sum(t.numel()*t.element_size() for layer in past for t in layer)
    def get(self,key,pref_tensor):
        with self.lock:
            if key in self.data:
                self.stats["hits"]+=1
                self.data.move_to_end(key)
                future,nbytes=self.data[key]
                if not future.done():
                    self.stats["producer_waits"]+=1
                return future
            self.stats["misses"]+=1
            if not observe_cache(self.history,key):
                self.stats["skips"]+=1
                return None
            # Original GPT-2 float32 cached tensor size (12 layers, 768 hidden).
            planned=2*self.model.config.n_layer*self.model.config.n_embd*len(key)*4
            if planned>self.cap_bytes:
                self.stats["skips"]+=1
                return None
            while self.data and (len(self.data)>=self.cap_entries or
                                 sum(item[1] for item in self.data.values())+planned>self.cap_bytes):
                _,(old_future,_) = self.data.popitem(last=False)
                self.stats["evictions"]+=1
                # A removed future remains owned by the requesting decoder.
            future=concurrent.futures.Future()
            self.data[key]=(future,planned)
            self.stats["admissions"]+=1
            self.stats["max_retained_bytes"]=max(self.stats["max_retained_bytes"],
                                       sum(v[1] for v in self.data.values()))
            self.stats["max_retained_entries"]=max(self.stats["max_retained_entries"],len(self.data))
        # Perform expensive prefill OUTSIDE lock; all consumers wait for this producer.
        try:
            with self.torch.inference_mode():
                cached=self.model(input_ids=pref_tensor,use_cache=True).past_key_values
            if self._nbytes(cached)!=planned:
                raise RuntimeError("CACHE_PREFIX_TENSOR_BYTE_MISMATCH")
            future.set_result(cached)
        except BaseException as exc:
            future.set_exception(exc)
            raise
        return future
    def snapshot(self):
        with self.lock:
            if self.stats["max_retained_entries"]>self.cap_entries or self.stats["max_retained_bytes"]>self.cap_bytes:
                raise RuntimeError("CACHE_LIMIT_EXCEEDED")
            return dict(self.stats)

def main():
    import copy
    import psutil
    import torch
    import transformers
    from transformers import AutoTokenizer,AutoModelForCausalLM
    contract()
    g55=load_module("g55_g67","llm_g55/g55_gpt2_controls.py")
    g60=load_module("g60_g68","llm_g60/g60_concurrent.py")
    if (g55.REV,g55.WEIGHT_SHA)!=(MODEL_REV,WEIGHTS_SHA):
        raise RuntimeError("FROZEN_G55_AUTHENTIC_MODEL_MISMATCH")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    receipt={"gate":"G70","source_sha":os.getenv("GITHUB_SHA","UNSET"),
             "preregistration_sha":PREREG,"classification":"HELDOUT_LOCALHOST_HTTP_LIBRARY_CONTROL_ONLY",
             "model_revision":MODEL_REV,"model_safetensors_sha256":WEIGHTS_SHA,
             "dataset_repo":DATA_REPO,"dataset_revision":DATA_REV,
             "dataset_file_sha256":DATA_SHA,"dataset_license":"MIT",
             "dataset_attribution":"GSM8K, Cobbe et al. 2021; original OpenAI grade-school-math repository",
             "torch":torch.__version__,"transformers":transformers.__version__,
             "platform":platform.platform(),"cohorts":COHORTS,
             "arms":ARMS,"repeats":REPEATS,"cpu_budget":CPU_BUDGET,
             "generated_tokens_per_request":TOKENS,
             "correctness":"UNVERIFIED","engineering":"UNVERIFIED",
             "screen":"UNVERIFIED","scientific_acceptance":"NOT_GRANTED",
             "promotion_allowed":False,"optimized_serving_engine_control":"NOT_INCLUDED",
             "limitations":[
                 "12 new disjoint original human-written GSM8K questions under four artificial system-prefix locality mixes",
                 "HTTP bound to localhost; process startup, model load, tokenization excluded from timed streams",
                 "HF generate is a reference library baseline, NOT an independent optimized production serving engine",
                 "Only 3 concurrent clients and 2 paired repeats; no continuous/dynamic batching",
                 "Single CPU Linux host with sampled RSS, not exact peak; no energy, GPU, external heldout host",
                 "No native Wingless/Yggdrasil/FORGE model integration"
             ]}
    try:
        # Exact original archived GitHub file, NOT Hugging Face CDN/LFS.
        # The complete raw file identity is frozen before first use.
        import urllib.request
        url="https://raw.githubusercontent.com/"+DATA_REPO+"/"+DATA_REV+"/"+DATA_FILE
        target=Path("g70_heldout_gsm8k_pinned.jsonl")
        request=urllib.request.Request(url,headers={"User-Agent":"FORGE-G70-GSM8K-Authentic-Research/1"})
        with urllib.request.urlopen(request,timeout=45) as response, target.open("xb") as out:
            total=0
            while True:
                chunk=response.read(1024*1024)
                if not chunk:break
                total+=len(chunk)
                if total>800000:raise RuntimeError("GSM8K_FILE_SIZE_CAP_EXCEEDED")
                out.write(chunk)
        if target.stat().st_size!=749738:
            raise RuntimeError("GSM8K_FROZEN_FILE_SIZE_MISMATCH")
        if sha256_file(target)!=DATA_SHA:
            raise RuntimeError("GSM8K_FROZEN_RAW_SHA256_MISMATCH")
        raw_path=target
        receipt["dataset_transport"]="PINNED_ARCHIVED_GITHUB_RAW_SHA256_PASS"
        with raw_path.open("r",encoding="utf-8") as f:
            rows=[{"instruction":item["question"],"category":"math_word_problem"}
                  for item in (json.loads(line) for line in f if line.strip())]
        heldout=select_heldout(rows)
        g68_original=load_module("g68_frozen_original","llm_g68/g68_gsm8k_http.py")
        previously_used=g68_original.select_heldout(rows)
        if len(previously_used)!=CASES or set(r["source_row"] for r in heldout) & set(r["source_row"] for r in previously_used):
            raise RuntimeError("G70_HELDOUT_DISJOINTNESS_FAILURE")
        receipt["prior_g68_source_rows"]=[r["source_row"] for r in previously_used]
        receipt["selection_rank_interval"]=[SELECT_OFFSET,SELECT_OFFSET+CASES-1]
        receipt["eligible_dataset_rows"]=len(rows)
        root,files=g55.stage()
        receipt["model_files"]=files
        receipt["model_manifest_sha256"]=sha256_file(root/"manifest.json")
        tokenizer=AutoTokenizer.from_pretrained(str(root),trust_remote_code=False,local_files_only=True)
        model=AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,
                            trust_remote_code=False,use_safetensors=True).eval()
        if model.config.model_type!="gpt2" or next(model.parameters()).dtype!=torch.float32:
            raise RuntimeError("MODEL_ARCH_OR_DTYPE_MISMATCH")
        def ids(s):
            return tokenizer(s,return_tensors="pt",add_special_tokens=False)["input_ids"]
        selected_tokens=[]
        for record in heldout:
            token_ids=ids(record["instruction"])[:,:64]
            if token_ids.shape[1]==0:
                raise RuntimeError("EMPTY_SELECTED_TOKENIZED_INSTRUCTION")
            selected_tokens.append(token_ids)
        prefix_shared=ids(g55.PREFIX)
        input_records={}
        for cohort in COHORTS:
            batch=[]
            for i,instruction in enumerate(selected_tokens):
                pre=prefix_shared if i<SHARED_COUNT[cohort] else ids(g55.PREFIX+f" Account {i:02d}. ")
                whole=torch.cat((pre,instruction),dim=1)
                if whole.shape[1]+TOKENS>model.config.n_positions:
                    raise RuntimeError("CONTEXT_LIMIT_EXCEEDED")
                batch.append({"prefix":pre,"suffix":instruction,"full":whole,
                              "key":tuple(pre.flatten().tolist()),"source_index":heldout[i]["source_row"],
                              "category":heldout[i]["category"],
                              "instruction_sha256":heldout[i]["instruction_sha256"],
                              "prefix_sha256":hashlib.sha256(pre.numpy().tobytes()).hexdigest(),
                              "input_sha256":hashlib.sha256(whole.numpy().tobytes()).hexdigest()})
            input_records[cohort]=batch
        receipt["heldout_selection"]=[{
          "source_row":v["source_row"],"category":v["category"],
          "instruction_sha256":v["instruction_sha256"],
          "rank_sha256":v["rank_sha256"],
          "input_tokens":int(selected_tokens[i].shape[1])}
          for i,v in enumerate(heldout)]
        receipt["cohort_input_hashes"]={n:[v["input_sha256"] for v in items] for n,items in input_records.items()}
        if len(set(x["input_sha256"] for x in input_records["reuse_75"]))!=CASES:
            raise RuntimeError("HELDOUT_DUPLICATE_PROMPTS")
        if len(set(x["key"] for x in input_records["reuse_0"]))!=CASES:
            raise RuntimeError("UNIQUE_PREFIX_NOT_DISTINCT")
        proc=psutil.Process()
        if not hasattr(proc,"cpu_affinity"):
            raise RuntimeError("CPU_AFFINITY_UNAVAILABLE")
        initial_affinity=proc.cpu_affinity()
        if len(initial_affinity)<CPU_BUDGET:
            raise RuntimeError("INSUFFICIENT_LOGICAL_CPUS")
        receipt["allowed_cpu_affinity_before"]=initial_affinity

        def manual(first,future=None,prefix_len=0):
            kw={"input_ids":first,"use_cache":True}
            consumed=int(first.shape[1])+prefix_len
            if future is not None:
                cached=future.result(timeout=60)
                kw["past_key_values"]=copy.deepcopy(cached)
                kw["attention_mask"]=torch.ones((1,consumed),dtype=torch.long)
            with torch.inference_mode():
                out=model(**kw)
                past,logits=out.past_key_values,out.logits[:,-1,:]
                generated=[]
                for n in range(TOKENS):
                    token=logits.argmax(dim=-1,keepdim=True)
                    generated.append(token)
                    if n+1<TOKENS:
                        out=model(input_ids=token,past_key_values=past,use_cache=True,
                          attention_mask=torch.ones((1,consumed+n+1),dtype=torch.long))
                        past,logits=out.past_key_values,out.logits[:,-1,:]
                return torch.cat(generated,dim=1).flatten().tolist()

        def hf_decode(full):
            with torch.inference_mode():
                generated=model.generate(input_ids=full,do_sample=False,num_beams=1,
                  max_new_tokens=TOKENS,min_new_tokens=TOKENS,
                  use_cache=True,pad_token_id=tokenizer.eos_token_id,eos_token_id=None)
            return generated[:,full.shape[1]:].flatten().tolist()

        def run_http(cohort,arm):
            batch=input_records[cohort]
            cache=PrefixStore(torch,model,CACHE_BYTES,CACHE_ENTRIES)
            guard=threading.Semaphore(CPU_BUDGET)
            statuses=[]
            statuses_lock=threading.Lock()
            class Handler(BaseHTTPRequestHandler):
                def log_message(self,*_):pass
                def do_POST(self):
                    with guard:
                        t0=time.perf_counter()
                        try:
                            if self.path!="/generate" or int(self.headers.get("Content-Length","-1"))>128:
                                raise RuntimeError("INVALID_LOCAL_GENERATION_REQUEST")
                            length=int(self.headers.get("Content-Length","-1"))
                            if length<=0:raise RuntimeError("INVALID_BODY_LENGTH")
                            body=self.rfile.read(length)
                            obj=json.loads(body.decode("utf-8"))
                            if set(obj)!={"index"} or type(obj["index"]) is not int:
                                raise RuntimeError("INVALID_REQUEST_INDEX")
                            index=obj["index"]
                            if not 0<=index<CASES:
                                raise RuntimeError("REQUEST_OUT_OF_BOUNDS")
                            inp=batch[index]
                            if arm=="hf_generate":
                                result=hf_decode(inp["full"])
                            elif arm=="baseline_incremental":
                                result=manual(inp["full"])
                            else:
                                retained=cache.get(inp["key"],inp["prefix"])
                                result=(manual(inp["full"]) if retained is None else
                                        manual(inp["suffix"],retained,int(inp["prefix"].shape[1])))
                            if len(result)!=TOKENS:raise RuntimeError("OUTPUT_LENGTH_INVALID")
                            data=json.dumps({"index":index,"ids":result},sort_keys=True).encode("utf-8")
                            self.send_response(200)
                            self.send_header("Content-Type","application/json")
                            self.send_header("Content-Length",str(len(data)))
                            self.end_headers()
                            self.wfile.write(data)
                            with statuses_lock:statuses.append({"index":index,"server_request_s":time.perf_counter()-t0})
                        except BaseException as exc:
                            with statuses_lock:statuses.append({"error":str(exc),"exception":type(exc).__name__})
                            payload=json.dumps({"error":"AUTHENTIC_MODEL_EVALUATION_FAILURE"}).encode()
                            self.send_response(500);self.send_header("Content-Length",str(len(payload)))
                            self.end_headers();self.wfile.write(payload)
            class LocalServer(ThreadingHTTPServer):
                daemon_threads=True
            server=LocalServer(("127.0.0.1",0),Handler)
            server_thread=threading.Thread(target=server.serve_forever,daemon=True)
            server_thread.start()
            if not server_thread.is_alive():raise RuntimeError("LOCAL_HTTP_SERVER_DID_NOT_START")
            endpoint=f"http://127.0.0.1:{server.server_address[1]}/generate"
            def request(i):
                data=json.dumps({"index":i}).encode()
                req=urllib.request.Request(endpoint,data=data,headers={"Content-Type":"application/json"},method="POST")
                started=time.perf_counter()
                with urllib.request.urlopen(req,timeout=90) as response:
                    if response.status!=200:raise RuntimeError("HTTP_STATUS_FAILURE")
                    decoded=json.loads(response.read(2048))
                if decoded["index"]!=i or len(decoded["ids"])!=TOKENS:
                    raise RuntimeError("HTTP_RESPONSE_IDENTITY_MISMATCH")
                return decoded["ids"],time.perf_counter()-started
            wall_start=time.perf_counter()
            cpu_start=time.process_time()
            monitor=g60.RSSMonitor(proc)
            replies=[None]*CASES
            latencies=[None]*CASES
            try:
                with monitor, concurrent.futures.ThreadPoolExecutor(max_workers=CPU_BUDGET) as clients:
                    for at in range(0,CASES,CPU_BUDGET):
                        futures=[clients.submit(request,i) for i in range(at,at+CPU_BUDGET)]
                        for j,task in enumerate(futures):
                            ids_out,elapsed=task.result(timeout=120)
                            replies[at+j]=ids_out;latencies[at+j]=elapsed
                wall=time.perf_counter()-wall_start
                cpu=time.process_time()-cpu_start
            finally:
                server.shutdown()
                server.server_close()
                server_thread.join(timeout=3)
            if any(x is None for x in replies):raise RuntimeError("INCOMPLETE_HTTP_RESULTS")
            if len(statuses)!=CASES or any("error" in x for x in statuses):
                raise RuntimeError("HTTP_SERVER_GENERATION_ERROR")
            cs=cache.snapshot()
            if arm!="shared_prefix" and (cs["admissions"] or cs["hits"]):
                raise RuntimeError("BASELINE_CROSS_REQUEST_CACHE_CONTAMINATION")
            if cohort=="reuse_0" and arm=="shared_prefix" and (
                  cs["admissions"] or cs["hits"] or cs["max_retained_bytes"]):
                raise RuntimeError("UNIQUE_SOURCE_UNEXPECTED_CACHING")
            return replies,{
                "wall_s":wall,"process_cpu_s":cpu,
                "tokens_per_s":CASES*TOKENS/wall,
                "latencies_s":latencies,
                "p50_client_latency_s":statistics.median(latencies),
                "p95_sample_client_latency_s":p95(latencies),
                "max_client_latency_s":max(latencies),
                "sampled_rss_max_bytes":max(monitor.samples),
                "sampled_rss_count":len(monitor.samples),
                "http_completed_requests":len(statuses),
                "prefix_cache":cs,"http_bind":"127.0.0.1"
            }
        def check_tokens(a,b,label):
            if a!=b:raise RuntimeError("HELDOUT_GENERATION_PARITY_FAILURE_"+label)
        try:
            proc.cpu_affinity(initial_affinity[:CPU_BUDGET])
            # Warm-up uses only original public G55 prompt, NOT held-out instructions.
            with torch.inference_mode():
                model(input_ids=ids("This is a public warmup phrase."),use_cache=True)
            for cohort in COHORTS:
                reference,_=run_http(cohort,"baseline_incremental")
                for arm in ARMS:
                    out,_=run_http(cohort,arm)
                    check_tokens(reference,out,cohort+"_"+arm+"_admission")
                trials=[]
                for trial in range(REPEATS):
                    order=list(ARMS[trial:]+ARMS[:trial])
                    if trial%2:order.reverse()
                    rows={}
                    for arm in order:
                        out,info=run_http(cohort,arm)
                        check_tokens(reference,out,cohort+"_"+arm+"_trial"+str(trial))
                        rows[arm]=info
                    baseline_arm=min(("baseline_incremental","hf_generate"),
                              key=lambda name:rows[name]["wall_s"])
                    trials.append({"trial":trial+1,"order":order,"arms":rows,
                           "fastest_reference_arm":baseline_arm,
                           "shared_vs_fastest":rows[baseline_arm]["wall_s"]/rows["shared_prefix"]["wall_s"]})
                receipt.setdefault("results",{})[cohort]={
                    "reference_token_sha256":[hashlib.sha256(
                       json.dumps(x,separators=(",",":")).encode()).hexdigest() for x in reference],
                    "trials":trials,
                    "median_shared_vs_fastest":statistics.median(t["shared_vs_fastest"] for t in trials)
                }
            high=receipt["results"]["reuse_75"]
            unique=receipt["results"]["reuse_0"]
            # Compare medians of per-trial sample p95 (12 requests => largest observation).
            high_lats=[(t["arms"]["shared_prefix"]["p95_sample_client_latency_s"],
                         t["arms"][t["fastest_reference_arm"]]["p95_sample_client_latency_s"])
                       for t in high["trials"]]
            high_ratio=statistics.median(a/b for a,b in high_lats)
            receipt["reuse_75_sample_p95_ratio"]=high_ratio
            receipt["engineering"]="PASS"
            receipt["correctness"]="PASS"
            receipt["screen"]="PASS" if (
                all(receipt["results"][cohort]["median_shared_vs_fastest"] >= THRESHOLDS[cohort] for cohort in COHORTS) and
                high_ratio<=THRESHOLDS["reuse_75_p95_ratio"]
            ) else "FAIL"
        finally:
            proc.cpu_affinity(initial_affinity)
    except BaseException as exc:
        receipt["error"]=type(exc).__name__+": "+str(exc)
        raise
    finally:
        Path("g70_result.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
        print(json.dumps({k:receipt.get(k) for k in
             ("gate","correctness","engineering","screen","error","reuse_75_sample_p95_ratio")},sort_keys=True))
        for name,result in receipt.get("results",{}).items():
            print(json.dumps({"cohort":name,
                 "median_shared_vs_fastest":result["median_shared_vs_fastest"],
                 "trials":[{"shared_vs_fastest":t["shared_vs_fastest"],
                            "fastest_reference_arm":t["fastest_reference_arm"],
                            "wall_s":{n:d["wall_s"] for n,d in t["arms"].items()}}
                           for t in result["trials"]]},sort_keys=True))

if __name__=="__main__":
    main()
