#!/usr/bin/env python3
"""CPU G93: exact shared-prefix KV reuse versus full-prompt original GPT-2."""
from __future__ import annotations
import copy,hashlib,importlib.util,json,math,os,platform,statistics,time,traceback,urllib.request
from pathlib import Path

PREREG="047ec14a2e27eedc0bb1e47e050fd4a071b94a6f"
MODEL_REV="607a30d783dfa663caf39e06633721c8d4cfcd7e"
WEIGHTS_SHA="248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
DATA_REV="3101c7d5072418e28b9008a6636bde82a006892c"
DATA_SHA="3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14"
DATA_BYTES=749738
SEED=b"G68-GPT2-HELDOUT-20261030:"
OFFSET,CASES,REPEATS,TOKENS,CPU_BUDGET=240,12,4,8,3
ARMS=("full_prompt_prefill2","shared_prefix_kv_reuse2")
THRESHOLDS={"cohort_speedup_min":1.15,"min_paired":0.90,"p95_amortized_max":1.10,
            "cpu_max":1.10,"rss_max":1.10}

def contract():
    assert (OFFSET,CASES,REPEATS,TOKENS,CPU_BUDGET)==(240,12,4,8,3)
    assert ARMS==("full_prompt_prefill2","shared_prefix_kv_reuse2")
    assert THRESHOLDS=={"cohort_speedup_min":1.15,"min_paired":0.90,
      "p95_amortized_max":1.10,"cpu_max":1.10,"rss_max":1.10}

def sha_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()

def module(name,rel):
    p=Path(__file__).resolve().parents[1]/rel
    spec=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def rank_original(records,n):
    pool=[]
    for row,item in enumerate(records):
        q=item.get("instruction","");cat=item.get("category","")
        if isinstance(q,str) and q.strip() and isinstance(cat,str) and cat.strip():
            pool.append((hashlib.sha256(SEED+q.encode()).hexdigest(),row,q,cat))
    pool.sort(key=lambda x:(x[0],x[1]));out=[];seen=set()
    for digest,row,q,cat in pool:
        if q in seen:continue
        seen.add(q);out.append({"source_row":row,"instruction":q,"category":cat,
          "instruction_sha256":hashlib.sha256(q.encode()).hexdigest(),"rank_sha256":digest})
        if len(out)==n:break
    if len(out)!=n:raise RuntimeError("G93_INSUFFICIENT_ORIGINAL_HELDOUT")
    return out

def p95(xs):
    if not xs:raise RuntimeError("G93_EMPTY_LATENCY_SAMPLE")
    return sorted(xs)[max(0,math.ceil(.95*len(xs))-1)]

def decide(trials):
    if len(trials)!=REPEATS:raise RuntimeError("G93_INCOMPLETE_COHORT_REPETITIONS")
    baseline_rows=[];candidate_rows=[]
    base_wall=[];cand_wall=[];base_cpu=[];cand_cpu=[];base_rss=[];cand_rss=[]
    for trial in trials:
        if set(trial["arms"])!=set(ARMS):raise RuntimeError("G93_MISSING_ARM")
        b=trial["arms"][ARMS[0]];c=trial["arms"][ARMS[1]]
        if b["responses"]!=CASES or c["responses"]!=CASES:
            raise RuntimeError("G93_INCOMPLETE_REQUEST_COHORT")
        if b["generated_tokens"]!=CASES*TOKENS or c["generated_tokens"]!=CASES*TOKENS:
            raise RuntimeError("G93_INCOMPLETE_TOKEN_COHORT")
        if set(b["output_hashes"])!=set(c["output_hashes"]):
            raise RuntimeError("G93_REQUEST_SET_MISMATCH")
        for row in b["output_hashes"]:
            if b["output_hashes"][row]!=c["output_hashes"][row]:
                raise RuntimeError("G93_ORIGINAL_TOKEN_PARITY_ERROR_"+row)
        base_wall.append(b["cohort_wall_ns"]);cand_wall.append(c["cohort_wall_ns"])
        base_cpu.append(b["cohort_cpu_ns"]);cand_cpu.append(c["cohort_cpu_ns"])
        base_rss.append(b["max_sampled_rss_bytes"]);cand_rss.append(c["max_sampled_rss_bytes"])
        baseline_rows.extend(b["request_rows"])
        candidate_rows.extend(c["request_rows"])
    base_speed=statistics.median([CASES*TOKENS/(x/1e9) for x in base_wall])
    cand_speed=statistics.median([CASES*TOKENS/(x/1e9) for x in cand_wall])
    by_b={x["source_row"]:[] for x in baseline_rows}
    by_c={x["source_row"]:[] for x in candidate_rows}
    for x in baseline_rows:by_b[x["source_row"]].append(x["request_wall_ns"])
    for x in candidate_rows:by_c[x["source_row"]].append(x["request_wall_ns"]+x["prefix_setup_share_ns"])
    paired=[]
    for row in sorted(by_b):
        bmed=statistics.median(by_b[row]);cmed=statistics.median(by_c[row])
        paired.append({"source_row":row,"baseline_median_ns":bmed,
          "candidate_amortized_median_ns":cmed,"speedup":bmed/cmed})
    metrics={
      "median_cohort_throughput_speedup":cand_speed/base_speed,
      "minimum_paired_request_speedup_after_prefix_cost_allocation":min(x["speedup"] for x in paired),
      "p95_amortized_candidate_over_baseline_request_latency":p95([x["request_wall_ns"]+x["prefix_setup_share_ns"] for x in candidate_rows])/p95([x["request_wall_ns"] for x in baseline_rows]),
      "total_cpu_candidate_over_baseline":sum(cand_cpu)/sum(base_cpu),
      "sampled_rss_candidate_over_baseline":max(cand_rss)/max(base_rss),
      "median_candidate_prefix_setup_ns":statistics.median([x["prefix_setup_ns"] for x in trials for x in [x["arms"][ARMS[1]]]]),
      "median_baseline_cohort_wall_ns":statistics.median(base_wall),
      "median_candidate_cohort_wall_ns":statistics.median(cand_wall),
      "timed_authentic_responses":REPEATS*2*CASES,
      "timed_authentic_generated_tokens":REPEATS*2*CASES*TOKENS,
      "paired_request_speedups":paired}
    ok=(metrics["median_cohort_throughput_speedup"]>=THRESHOLDS["cohort_speedup_min"]
      and metrics["minimum_paired_request_speedup_after_prefix_cost_allocation"]>=THRESHOLDS["min_paired"]
      and metrics["p95_amortized_candidate_over_baseline_request_latency"]<=THRESHOLDS["p95_amortized_max"]
      and metrics["total_cpu_candidate_over_baseline"]<=THRESHOLDS["cpu_max"]
      and metrics["sampled_rss_candidate_over_baseline"]<=THRESHOLDS["rss_max"])
    return metrics,"SHARED_PREFIX_KV_PASS" if ok else "SHARED_PREFIX_KV_NO_GO"

def decode_one(model,full_ids,suffix_ids,prefix_cache,prefix_len,torch,proc):
    start=time.perf_counter_ns();cpu0=time.process_time_ns()
    if prefix_cache is None:
        out=model(input_ids=full_ids,use_cache=True)
        context_len=int(full_ids.shape[1])
        prefill_ns=time.perf_counter_ns()-start
        cache_copy_ns=0
    else:
        tc=time.perf_counter_ns()
        past=copy.deepcopy(prefix_cache)
        cache_copy_ns=time.perf_counter_ns()-tc
        suffix_len=int(suffix_ids.shape[1]);context_len=prefix_len+suffix_len
        mask=torch.ones((1,context_len),dtype=torch.long)
        positions=torch.arange(prefix_len,context_len,dtype=torch.long).unsqueeze(0)
        tp=time.perf_counter_ns()
        out=model(input_ids=suffix_ids,past_key_values=past,attention_mask=mask,
                  position_ids=positions,use_cache=True)
        prefill_ns=time.perf_counter_ns()-tp
    state,logits=out.past_key_values,out.logits[:,-1,:]
    generated=[];decode_start=time.perf_counter_ns()
    for step in range(TOKENS):
        token=logits.argmax(dim=-1,keepdim=True);generated.append(token)
        if step+1<TOKENS:
            mask=torch.ones((1,context_len+step+1),dtype=torch.long)
            positions=torch.tensor([[context_len+step]],dtype=torch.long)
            out=model(input_ids=token,past_key_values=state,attention_mask=mask,
                      position_ids=positions,use_cache=True)
            state,logits=out.past_key_values,out.logits[:,-1,:]
    decode_ns=time.perf_counter_ns()-decode_start
    wall=time.perf_counter_ns()-start;cpu=time.process_time_ns()-cpu0
    tokens=torch.cat(generated,dim=1).flatten().tolist()
    return tokens,{"request_wall_ns":wall,"prefill_ns":prefill_ns,"decode_ns":decode_ns,
      "cache_copy_ns":cache_copy_ns,"cpu_ns":cpu,"rss_bytes":proc.memory_info().rss,
      "output_sha256":hashlib.sha256(json.dumps(tokens,separators=(",",":")).encode()).hexdigest()}

def run_full_cohort(model,inputs,torch,proc):
    cohort_start=time.perf_counter_ns();cpu0=time.process_time_ns()
    rows=[];outputs={}
    for source_row,full,suffix in inputs:
        ids,timing=decode_one(model,full,suffix,None,0,torch,proc)
        outputs[source_row]=ids
        rows.append({"source_row":source_row,**timing,"prefix_setup_share_ns":0})
    return outputs,{"cohort_wall_ns":time.perf_counter_ns()-cohort_start,
      "cohort_cpu_ns":time.process_time_ns()-cpu0,"prefix_setup_ns":0,
      "request_rows":rows,"output_hashes":{str(k):hashlib.sha256(json.dumps(v,separators=(",",":")).encode()).hexdigest() for k,v in outputs.items()},
      "responses":len(outputs),"generated_tokens":sum(len(x) for x in outputs.values()),
      "max_sampled_rss_bytes":max(x["rss_bytes"] for x in rows)}

def run_shared_cohort(model,inputs,prefix,torch,proc):
    cohort_start=time.perf_counter_ns();cpu0=time.process_time_ns()
    tp=time.perf_counter_ns()
    with torch.inference_mode():
        shared=model(input_ids=prefix,use_cache=True).past_key_values
    prefix_setup_ns=time.perf_counter_ns()-tp
    rows=[];outputs={};rss=[proc.memory_info().rss]
    prefix_len=int(prefix.shape[1])
    for source_row,full,suffix in inputs:
        ids,timing=decode_one(model,full,suffix,shared,prefix_len,torch,proc)
        outputs[source_row]=ids
        rows.append({"source_row":source_row,**timing,
          "prefix_setup_share_ns":prefix_setup_ns//CASES})
        rss.append(timing["rss_bytes"])
    wall=time.perf_counter_ns()-cohort_start;cpu=time.process_time_ns()-cpu0
    return outputs,{"cohort_wall_ns":wall,"cohort_cpu_ns":cpu,"prefix_setup_ns":prefix_setup_ns,
      "request_rows":rows,"output_hashes":{str(k):hashlib.sha256(json.dumps(v,separators=(",",":")).encode()).hexdigest() for k,v in outputs.items()},
      "responses":len(outputs),"generated_tokens":sum(len(x) for x in outputs.values()),
      "max_sampled_rss_bytes":max(rss)}

def main():
    import torch,transformers,psutil
    from transformers import AutoTokenizer,AutoModelForCausalLM
    contract()
    if os.name!="posix" or platform.system()!="Linux" or platform.machine().lower() not in ("x86_64","amd64"):
        raise RuntimeError("G93_NOT_NATIVE_X86_64_LINUX")
    if torch.version.cuda is not None:raise RuntimeError("G93_NON_CPU_PYTORCH")
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    proc=psutil.Process();old_aff=None
    receipt={"schema":"forge.cpu-llm-g93.authentic-shared-prefix-kv.v1","gate":"CPU_G93",
      "preregistration_commit":PREREG,"source_sha":os.getenv("GITHUB_SHA","UNSET"),
      "model_revision":MODEL_REV,"model_weights_sha256":WEIGHTS_SHA,
      "dataset_revision":DATA_REV,"dataset_sha256":DATA_SHA,
      "engineering":"UNVERIFIED","correctness":"UNVERIFIED","decision":"UNVERIFIED",
      "scientific_acceptance":"NOT_GRANTED","promotion_allowed":False,
      "runtime":{"torch":torch.__version__,"torch_cuda":torch.version.cuda,
        "transformers":transformers.__version__,"python":platform.python_version(),
        "machine":platform.machine(),"processor":platform.processor(),"logical_cpus":os.cpu_count(),
        "platform":platform.platform()},
      "limitations":["Shared identical prefix across a fixed cohort of 12 requests only",
        "Original GPT2 FP32 and eight-token greedy output only",
        "GSM8K ranks disjoint but not proven unseen in GPT2 pretraining",
        "One Linux x86_64 virtualized host, fixed three-core affinity, sampled RSS, no energy metric",
        "No model weights changed, production or intelligence claims, scientific acceptance or promotion"]}
    try:
        raw=Path("cpu_g93_original_gsm8k.jsonl")
        req=urllib.request.Request("https://raw.githubusercontent.com/openai/grade-school-math/"+DATA_REV+"/grade_school_math/data/test.jsonl",
          headers={"User-Agent":"FORGE-CPU-G93-SHARED-PREFIX-KV/1"})
        with urllib.request.urlopen(req,timeout=45) as inp,raw.open("xb") as out:
            count=0
            while True:
                b=inp.read(1<<20)
                if not b:break
                count+=len(b)
                if count>800000:raise RuntimeError("G93_DATA_SIZE_CAP")
                out.write(b)
        if raw.stat().st_size!=DATA_BYTES or sha_file(raw)!=DATA_SHA:
            raise RuntimeError("G93_DATA_IDENTITY_DRIFT")
        with raw.open(encoding="utf-8") as f:
            records=[{"instruction":x["question"],"category":"math_word_problem"} for x in (json.loads(line) for line in f if line.strip())]
        ranked=rank_original(records,OFFSET+CASES)
        g68=module("g93_g68","llm_g68/g68_gsm8k_http.py")
        g70=module("g93_g70","llm_g70/g70_gsm8k_locality.py")
        if ranked[:12]!=g68.select_heldout(records) or ranked[12:24]!=g70.select_heldout(records):
            raise RuntimeError("G93_RANK_CONTRACT_DRIFT")
        if len({x["source_row"] for x in ranked})!=OFFSET+CASES:
            raise RuntimeError("G93_DUPLICATE_HELDOUT_RANK")
        selected=ranked[OFFSET:OFFSET+CASES]
        receipt["selected"]=[{k:v for k,v in x.items() if k!="instruction"} for x in selected]
        receipt["selected_ranks"]=[OFFSET,OFFSET+CASES-1]
        g55=module("g93_g55","llm_g55/g55_gpt2_controls.py")
        if (g55.REV,g55.WEIGHT_SHA)!=(MODEL_REV,WEIGHTS_SHA):
            raise RuntimeError("G93_G55_MODEL_IDENTITY_DRIFT")
        if not isinstance(g55.PREFIX,str) or not g55.PREFIX:
            raise RuntimeError("G93_EMPTY_SHARED_PREFIX")
        root,manifest=g55.stage()
        receipt["model_files"]=manifest
        receipt["model_manifest_sha256"]=sha_file(root/"manifest.json")
        tokenizer=AutoTokenizer.from_pretrained(str(root),local_files_only=True,trust_remote_code=False)
        model=AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,
          use_safetensors=True,trust_remote_code=False).eval()
        if model.config.model_type!="gpt2" or next(model.parameters()).dtype!=torch.float32:
            raise RuntimeError("G93_ORIGINAL_FP32_GPT2_REQUIRED")
        if not hasattr(proc,"cpu_affinity"):raise RuntimeError("G93_AFFINITY_UNAVAILABLE")
        old_aff=proc.cpu_affinity()
        if len(old_aff)<CPU_BUDGET:raise RuntimeError("G93_THREE_CPU_AFFINITY_UNAVAILABLE")
        proc.cpu_affinity(old_aff[:CPU_BUDGET])
        receipt["fixed_affinity"]=proc.cpu_affinity()
        receipt["fixed_torch_interop"]=torch.get_num_interop_threads()
        def encode(s):return tokenizer(s,return_tensors="pt",add_special_tokens=False)["input_ids"]
        prefix=encode(g55.PREFIX)
        inputs=[]
        for item in selected:
            suffix=encode(item["instruction"])
            full=torch.cat((prefix,suffix),dim=1)
            if full.shape[1]+TOKENS>model.config.n_positions:raise RuntimeError("G93_CONTEXT_OVERFLOW")
            inputs.append((item["source_row"],full,suffix))
        receipt["prefix_tokens"]=int(prefix.shape[1])
        receipt["prefix_token_ids_sha256"]=hashlib.sha256(prefix.numpy().tobytes()).hexdigest()
        receipt["suffixes"]=[{"source_row":row,"suffix_tokens":int(s.shape[1]),
          "suffix_token_ids_sha256":hashlib.sha256(s.numpy().tobytes()).hexdigest(),
          "full_prompt_tokens":int(full.shape[1])} for row,full,s in inputs]
        # Validate next-token logits and first greedy token before any timed work.
        logit_checks=[]
        with torch.inference_mode():
            prefix_cache=model(input_ids=prefix,use_cache=True).past_key_values
            for row,full,suffix in inputs:
                ordinary=model(input_ids=full,use_cache=True).logits[:,-1,:]
                mask=torch.ones((1,int(full.shape[1])),dtype=torch.long)
                positions=torch.arange(int(prefix.shape[1]),int(full.shape[1]),dtype=torch.long).unsqueeze(0)
                reused=model(input_ids=suffix,past_key_values=copy.deepcopy(prefix_cache),
                  attention_mask=mask,position_ids=positions,use_cache=True).logits[:,-1,:]
                diff=(ordinary-reused).abs()
                if int(ordinary.argmax(-1).item())!=int(reused.argmax(-1).item()):
                    raise RuntimeError("G93_FIRST_GREEDY_TOKEN_MISMATCH_"+str(row))
                logit_checks.append({"source_row":row,"max_absolute_logit_difference":float(diff.max().item())})
        receipt["first_token_logit_checks"]=logit_checks
        # Equal untimed warmups, exact full output parity.
        with torch.inference_mode():
            warm_base,_=run_full_cohort(model,inputs,torch,proc)
            warm_shared,_=run_shared_cohort(model,inputs,prefix,torch,proc)
        for row in warm_base:
            if warm_base[row]!=warm_shared[row]:
                raise RuntimeError("G93_WARMUP_TOKEN_PARITY_FAILURE_"+str(row))
        trials=[]
        for rep in range(REPEATS):
            order=ARMS if rep%2==0 else tuple(reversed(ARMS))
            arms={}
            with torch.inference_mode():
                for arm in order:
                    if arm==ARMS[0]:out,measurement=run_full_cohort(model,inputs,torch,proc)
                    else:out,measurement=run_shared_cohort(model,inputs,prefix,torch,proc)
                    if set(out)!=set(warm_base):raise RuntimeError("G93_REQUEST_SET_DRIFT")
                    for row in warm_base:
                        if out[row]!=warm_base[row]:
                            raise RuntimeError("G93_EXACT_TOKEN_MISMATCH_"+arm+"_"+str(row))
                    arms[arm]=measurement
            trials.append({"rep":rep+1,"order":order,"arms":arms})
        metrics,decision=decide(trials)
        receipt["paired_cohort_trials"]=trials
        receipt["metrics"]=metrics
        receipt["engineering"]="PASS";receipt["correctness"]="PASS";receipt["decision"]=decision
    except BaseException as exc:
        receipt["error"]=type(exc).__name__+": "+str(exc)
        receipt["traceback_tail"]=traceback.format_exc()[-3000:]
        raise
    finally:
        if old_aff is not None:
            receipt["cpu_affinity_at_end"]=proc.cpu_affinity();proc.cpu_affinity(old_aff)
        Path("cpu_g93_original_result.json").write_text(json.dumps(receipt,sort_keys=True,indent=2,default=str)+"\n",encoding="utf-8")
        print(json.dumps({k:receipt.get(k) for k in
          ("gate","engineering","correctness","decision","metrics","error")},sort_keys=True),flush=True)

if __name__=="__main__":main()
