#!/usr/bin/env python3
"""CPU G91: length-aware grouping for original FP32 GPT-2 independent requests."""
from __future__ import annotations
import hashlib,importlib.util,json,math,os,platform,statistics,time,traceback,urllib.request
from pathlib import Path

PREREG="e04dfa901e36892ce6c2eea48bdb2e30ec26918a"
MODEL_REV="607a30d783dfa663caf39e06633721c8d4cfcd7e"
WEIGHTS_SHA="248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
DATA_REV="3101c7d5072418e28b9008a6636bde82a006892c"
DATA_SHA="3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14"
DATA_BYTES=749738
SEED=b"G68-GPT2-HELDOUT-20261030:"
OFFSET=216;CASES=12;REPEATS=4;TOKENS=8;CPU_BUDGET=3
ARM_SPECS=(("batch1",1,"random"),("batch2_random",2,"random"),
 ("batch2_length",2,"length"),("batch4_random",4,"random"),("batch4_length",4,"length"))
ARMS=tuple(x[0] for x in ARM_SPECS)
THRESHOLDS={"throughput_speedup_min":1.20,"p95_group_latency_ratio_max":2.00,
 "rss_ratio_max":1.50,"cpu_per_token_ratio_max":1.50}

def contract():
    assert (OFFSET,CASES,REPEATS,TOKENS,CPU_BUDGET)==(216,12,4,8,3)
    assert ARM_SPECS==(("batch1",1,"random"),("batch2_random",2,"random"),
      ("batch2_length",2,"length"),("batch4_random",4,"random"),("batch4_length",4,"length"))
    assert THRESHOLDS=={"throughput_speedup_min":1.20,
      "p95_group_latency_ratio_max":2.00,"rss_ratio_max":1.50,
      "cpu_per_token_ratio_max":1.50}

def sha_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()

def module(name,rel):
    p=Path(__file__).resolve().parents[1]/rel
    s=importlib.util.spec_from_file_location(name,p)
    x=importlib.util.module_from_spec(s);s.loader.exec_module(x);return x

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
    if len(out)!=n:raise RuntimeError("G91_INSUFFICIENT_ORIGINAL_HELDOUT")
    return out

def group_schedule(n,rep,lengths,strategy):
    indices=list(range(CASES))
    if strategy=="length":
        indices.sort(key=lambda i:(lengths[i],i))
    elif strategy=="random":
        shift=(rep*5+n)%CASES
        indices=indices[shift:]+indices[:shift]
        if rep%2:indices.reverse()
    else:raise RuntimeError("G91_UNKNOWN_GROUP_STRATEGY")
    return [indices[i:i+n] for i in range(0,CASES,n)]

def p95(xs):
    if not xs:raise RuntimeError("G91_EMPTY_LATENCY_SAMPLE")
    return sorted(xs)[max(0,math.ceil(.95*len(xs))-1)]

def decide(trials):
    if len(trials)!=REPEATS:raise RuntimeError("G91_INCOMPLETE_REPETITIONS")
    summaries={};all_outputs={}
    for arm in ARMS:
        runs=[t["arms"][arm] for t in trials]
        if any(x["responses"]!=CASES or x["generated_tokens"]!=CASES*TOKENS for x in runs):
            raise RuntimeError("G91_INCOMPLETE_REQUEST_COHORT_"+arm)
        for run in runs:
            for row,h in run["output_hashes"].items():all_outputs.setdefault(row,[]).append(h)
        walls=[x["wall_ns"] for x in runs]
        groups=[g["wall_ns"] for x in runs for g in x["groups"]]
        summaries[arm]={"median_full_cohort_wall_ns":statistics.median(walls),
          "p95_group_completion_wall_ns":p95(groups),
          "median_requests_per_second":statistics.median([CASES/(x["wall_ns"]/1e9) for x in runs]),
          "median_generated_tokens_per_second":statistics.median([CASES*TOKENS/(x["wall_ns"]/1e9) for x in runs]),
          "total_process_cpu_ns":sum(x["process_cpu_ns"] for x in runs),
          "cpu_ns_per_generated_token":sum(x["process_cpu_ns"] for x in runs)/(REPEATS*CASES*TOKENS),
          "max_sampled_rss_bytes":max(x["max_sampled_rss_bytes"] for x in runs),
          "max_group_size":max(len(g["indices"]) for x in runs for g in x["groups"]),
          "padding_tokens":sum(g["padding_tokens"] for x in runs for g in x["groups"])}
    base=summaries["batch1"];qualification=[]
    for arm,n,kind in ARM_SPECS[1:]:
        x=summaries[arm];random_arm=summaries[f"batch{n}_random"]
        metrics={"throughput_speedup":x["median_generated_tokens_per_second"]/base["median_generated_tokens_per_second"],
          "p95_group_latency_ratio":x["p95_group_completion_wall_ns"]/base["p95_group_completion_wall_ns"],
          "sampled_rss_ratio":x["max_sampled_rss_bytes"]/base["max_sampled_rss_bytes"],
          "cpu_per_token_ratio":x["cpu_ns_per_generated_token"]/base["cpu_ns_per_generated_token"],
          "throughput_vs_same_size_random":x["median_generated_tokens_per_second"]/random_arm["median_generated_tokens_per_second"]}
        ok=(kind=="length" and metrics["throughput_speedup"]>=THRESHOLDS["throughput_speedup_min"]
          and metrics["p95_group_latency_ratio"]<=THRESHOLDS["p95_group_latency_ratio_max"]
          and metrics["sampled_rss_ratio"]<=THRESHOLDS["rss_ratio_max"]
          and metrics["cpu_per_token_ratio"]<=THRESHOLDS["cpu_per_token_ratio_max"]
          and metrics["throughput_vs_same_size_random"]>1.0)
        qualification.append({"arm":arm,"batch_size":n,"grouping":kind,**metrics,"qualifies":ok})
    for row,hashes in all_outputs.items():
        if len(hashes)!=len(ARMS)*REPEATS or len(set(hashes))!=1:
            raise RuntimeError("G91_CROSS_ARM_OR_REPETITION_OUTPUT_MISMATCH_"+str(row))
    winners=[x for x in qualification if x["qualifies"]]
    winners.sort(key=lambda x:(-x["throughput_speedup"],x["batch_size"]))
    decision="LENGTH_BUCKET_PASS" if winners else "LENGTH_BUCKET_NO_GO"
    return {"arms":summaries,"candidate_qualification":qualification,
      "selected_arm":winners[0]["arm"] if winners else None,
      "timed_authentic_responses":len(ARMS)*REPEATS*CASES,
      "timed_authentic_generated_tokens":len(ARMS)*REPEATS*CASES*TOKENS},decision

def make_batch(items,pad_id,torch):
    lengths=[int(x.shape[1]) for _,x in items]
    maxlen=max(lengths);b=len(items)
    input_ids=torch.full((b,maxlen),int(pad_id),dtype=torch.long)
    mask=torch.zeros((b,maxlen),dtype=torch.long)
    for i,(_,x) in enumerate(items):
        length=int(x.shape[1])
        input_ids[i,maxlen-length:]=x[0]
        mask[i,maxlen-length:]=1
    positions=(mask.cumsum(dim=-1)-1).clamp(min=0)
    return input_ids,mask,positions

def decode_group(model,items,pad_id,torch,proc):
    # Collation and left-padding are intentionally charged to candidate batch time.
    t0=time.perf_counter_ns();cpu0=time.process_time_ns()
    input_ids,mask,positions=make_batch(items,pad_id,torch)
    batch_size=len(items)
    with torch.inference_mode():
        out=model(input_ids=input_ids,attention_mask=mask,position_ids=positions,use_cache=True)
        past,logits=out.past_key_values,out.logits[:,-1,:]
        generated=[]
        for step in range(TOKENS):
            token=logits.argmax(dim=-1,keepdim=True);generated.append(token)
            if step+1<TOKENS:
                next_positions=mask.sum(dim=-1,keepdim=True)
                mask=torch.cat((mask,torch.ones((batch_size,1),dtype=torch.long)),dim=1)
                out=model(input_ids=token,past_key_values=past,attention_mask=mask,
                          position_ids=next_positions,use_cache=True)
                past,logits=out.past_key_values,out.logits[:,-1,:]
    result=torch.cat(generated,dim=1).tolist()
    wall=time.perf_counter_ns()-t0;cpu=time.process_time_ns()-cpu0
    rss=proc.memory_info().rss
    return result,{"wall_ns":wall,"process_cpu_ns":cpu,"rss_sampled":rss}

def run_cohort(model,inputs,batch_size,strategy,pad_id,torch,proc,rep):
    lengths=[int(x.shape[1]) for _,x in inputs]
    wall0=time.perf_counter_ns();cpu0=time.process_time_ns()
    groups=group_schedule(batch_size,rep,lengths,strategy)
    results={};group_rows=[];maxrss=0
    for indices in groups:
        items=[inputs[i] for i in indices]
        outputs,timing=decode_group(model,items,pad_id,torch,proc)
        if len(outputs)!=len(indices):raise RuntimeError("G91_BATCH_RESPONSE_COUNT_MISMATCH")
        for index,ids in zip(indices,outputs):
            if len(ids)!=TOKENS:raise RuntimeError("G91_OUTPUT_TOKEN_COUNT_MISMATCH")
            results[index]=ids
        maxrss=max(maxrss,timing["rss_sampled"])
        group_rows.append({"indices":indices,"input_lengths":[lengths[i] for i in indices],
          "padding_tokens":len(indices)*max(lengths[i] for i in indices)-sum(lengths[i] for i in indices),
          "wall_ns":timing["wall_ns"],"process_cpu_ns":timing["process_cpu_ns"],
          "rss_sampled":timing["rss_sampled"]})
    wall=time.perf_counter_ns()-wall0;cpu=time.process_time_ns()-cpu0
    if sorted(results)!=list(range(CASES)):raise RuntimeError("G91_MISSING_OR_DUPLICATED_REQUESTS")
    hashes={str(inputs[i][0]):hashlib.sha256(json.dumps(results[i],separators=(",",":")).encode()).hexdigest()
      for i in range(CASES)}
    return results,{"wall_ns":wall,"process_cpu_ns":cpu,"max_sampled_rss_bytes":maxrss,
      "groups":group_rows,"output_hashes":hashes,"responses":len(results),
      "generated_tokens":sum(len(x) for x in results.values()),"strategy":strategy}

def main():
    import psutil,torch,transformers
    from transformers import AutoTokenizer,AutoModelForCausalLM
    contract()
    if os.name!="posix" or platform.system()!="Linux" or platform.machine().lower() not in ("x86_64","amd64"):
        raise RuntimeError("G91_NOT_NATIVE_X86_64_LINUX")
    if torch.version.cuda is not None:raise RuntimeError("G91_NON_CPU_PYTORCH_BUILD")
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    proc=psutil.Process();old_aff=None
    receipt={"schema":"forge.cpu-llm-g91.authentic-length-bucketing.v1","gate":"CPU_G91",
      "preregistration_commit":PREREG,"source_sha":os.getenv("GITHUB_SHA","UNSET"),
      "model_revision":MODEL_REV,"model_weights_sha256":WEIGHTS_SHA,
      "dataset_revision":DATA_REV,"dataset_sha256":DATA_SHA,
      "runtime":{"torch":torch.__version__,"torch_cuda":torch.version.cuda,
        "transformers":transformers.__version__,"python":platform.python_version(),
        "machine":platform.machine(),"processor":platform.processor(),"logical_cpu_count":os.cpu_count(),
        "platform":platform.platform()},
      "engineering":"UNVERIFIED","correctness":"UNVERIFIED","decision":"UNVERIFIED",
      "scientific_acceptance":"NOT_GRANTED","promotion_allowed":False,
      "limitations":["Original GPT2 FP32 and fixed eight-token greedy decoding only",
        "Aggregate throughput is not single-request latency",
        "Three logical CPUs, single pinned Linux x86_64 runner",
        "GSM8K evaluation prompts are not proven unseen during pretraining",
        "RSS sampled, no energy metric, no production-serving claim",
        "No model weights changed; no GPU, Wingless/Yggdrasil or promotion"]}
    try:
        raw=Path("cpu_g91_original_gsm8k.jsonl")
        req=urllib.request.Request("https://raw.githubusercontent.com/openai/grade-school-math/"+DATA_REV+"/grade_school_math/data/test.jsonl",
          headers={"User-Agent":"FORGE-CPU-G91-LENGTH-BUCKET/1"})
        with urllib.request.urlopen(req,timeout=45) as inp,raw.open("xb") as out:
            n=0
            while True:
                b=inp.read(1<<20)
                if not b:break
                n+=len(b)
                if n>800000:raise RuntimeError("G91_DATA_SIZE_CAP")
                out.write(b)
        if raw.stat().st_size!=DATA_BYTES or sha_file(raw)!=DATA_SHA:raise RuntimeError("G91_DATA_IDENTITY_DRIFT")
        with raw.open(encoding="utf-8") as f:
            records=[{"instruction":x["question"],"category":"math_word_problem"} for x in (json.loads(line) for line in f if line.strip())]
        ranked=rank_original(records,OFFSET+CASES)
        g68=module("g90_g68","llm_g68/g68_gsm8k_http.py")
        g70=module("g90_g70","llm_g70/g70_gsm8k_locality.py")
        if ranked[:12]!=g68.select_heldout(records) or ranked[12:24]!=g70.select_heldout(records):
            raise RuntimeError("G91_RANK_CONTRACT_DRIFT")
        if len({x["source_row"] for x in ranked})!=OFFSET+CASES:raise RuntimeError("G91_DUPLICATE_RANK")
        selected=ranked[OFFSET:OFFSET+CASES]
        receipt["selected"]=[{k:v for k,v in x.items() if k!="instruction"} for x in selected]
        receipt["selected_ranks"]=[OFFSET,OFFSET+CASES-1]
        g55=module("g90_g55","llm_g55/g55_gpt2_controls.py")
        if (g55.REV,g55.WEIGHT_SHA)!=(MODEL_REV,WEIGHTS_SHA):raise RuntimeError("G91_MODEL_IDENTITY_DRIFT")
        t0=time.perf_counter();root,manifest=g55.stage()
        receipt["model_manifest_sha256"]=sha_file(root/"manifest.json");receipt["model_files"]=manifest
        tok=AutoTokenizer.from_pretrained(str(root),local_files_only=True,trust_remote_code=False)
        model=AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,
          use_safetensors=True,trust_remote_code=False).eval()
        if model.config.model_type!="gpt2" or next(model.parameters()).dtype!=torch.float32:
            raise RuntimeError("G91_ORIGINAL_FP32_GPT2_REQUIRED")
        if not hasattr(proc,"cpu_affinity"):raise RuntimeError("G91_AFFINITY_UNAVAILABLE")
        old_aff=proc.cpu_affinity()
        if len(old_aff)<CPU_BUDGET:raise RuntimeError("G91_THREE_CPU_AFFINITY_UNAVAILABLE")
        proc.cpu_affinity(old_aff[:CPU_BUDGET]);receipt["fixed_affinity"]=proc.cpu_affinity()
        receipt["fixed_torch_interop"]=torch.get_num_interop_threads()
        inputs=[]
        for item in selected:
            ids=tok(g55.PREFIX,return_tensors="pt",add_special_tokens=False)["input_ids"]
            suffix=tok(item["instruction"],return_tensors="pt",add_special_tokens=False)["input_ids"][:,:64]
            full=torch.cat((ids,suffix),dim=1)
            if full.shape[1]+TOKENS>model.config.n_positions:raise RuntimeError("G91_CONTEXT_OVERFLOW")
            inputs.append((item["source_row"],full))
        pad_id=tok.eos_token_id
        receipt["input_lengths"]=[{"source_row":row,"tokens":int(t.shape[1])} for row,t in inputs]
        references={}
        for name,bs,strategy in ARM_SPECS:
            out,_=run_cohort(model,inputs,bs,strategy,pad_id,torch,proc,0)
            if name=="batch1":references=out
            elif any(out[i]!=references[i] for i in range(CASES)):
                raise RuntimeError("G91_WARMUP_CROSS_ARM_TOKEN_MISMATCH_"+name)
        measured=[]
        for rep in range(REPEATS):
            arms={}
            arm_order=ARM_SPECS[rep%len(ARM_SPECS):]+ARM_SPECS[:rep%len(ARM_SPECS)]
            if rep%2:arm_order=tuple(reversed(arm_order))
            for name,bs,strategy in arm_order:
                out,timing=run_cohort(model,inputs,bs,strategy,pad_id,torch,proc,rep)
                for i in range(CASES):
                    if out[i]!=references[i]:
                        raise RuntimeError("G91_EXACT_TOKEN_MISMATCH_"+name+"_REQUEST_"+str(i))
                arms[name]=timing
            measured.append({"rep":rep+1,"arms":arms})
        summary,decision=decide(measured)
        receipt["paired_cohort_trials"]=measured
        receipt["summary"]=summary
        receipt["engineering"]="PASS";receipt["correctness"]="PASS";receipt["decision"]=decision
    except BaseException as exc:
        receipt["error"]=type(exc).__name__+": "+str(exc)
        receipt["traceback_tail"]=traceback.format_exc()[-2500:]
        raise
    finally:
        if old_aff is not None:
            receipt["cpu_affinity_at_end"]=proc.cpu_affinity();proc.cpu_affinity(old_aff)
        Path("cpu_g91_original_result.json").write_text(
          json.dumps(receipt,sort_keys=True,indent=2,default=str)+"\n",encoding="utf-8")
        print(json.dumps({k:receipt.get(k) for k in
          ("gate","engineering","correctness","decision","summary","error")},sort_keys=True),flush=True)

if __name__=="__main__":main()
