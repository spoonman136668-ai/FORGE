#!/usr/bin/env python3
"""CPU G94: shared-prefix KV reuse scaling by independent cohort size."""
from __future__ import annotations
import copy,hashlib,importlib.util,json,math,os,platform,statistics,time,traceback,urllib.request
from pathlib import Path
PREREG="f2e8323f1909b70a8ae998e332e5c94754591077"
MODEL_REV="607a30d783dfa663caf39e06633721c8d4cfcd7e"
WEIGHTS_SHA="248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
DATA_REV="3101c7d5072418e28b9008a6636bde82a006892c"
DATA_SHA="3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14"
DATA_BYTES=749738
SEED=b"G68-GPT2-HELDOUT-20261030:"
OFFSET,CASES,REPEATS,TOKENS,CPU_BUDGET=252,12,4,8,3
COHORT_SIZES=(2,4,6,12)
ARMS=("full_prompt_all12",)+tuple("shared_prefix_cohort"+str(n) for n in COHORT_SIZES)
THRESHOLDS={"throughput_min":1.15,"min_paired":.90,"p95_max":1.10,"cpu_max":1.10,"rss_max":1.10}
def contract():
 assert (OFFSET,CASES,REPEATS,TOKENS,CPU_BUDGET)==(252,12,4,8,3)
 assert ARMS==("full_prompt_all12","shared_prefix_cohort2","shared_prefix_cohort4","shared_prefix_cohort6","shared_prefix_cohort12")
 assert THRESHOLDS=={"throughput_min":1.15,"min_paired":.90,"p95_max":1.10,"cpu_max":1.10,"rss_max":1.10}
def sha_file(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def module(name,rel):
 p=Path(__file__).resolve().parents[1]/rel
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def rank_original(records,n):
 pool=[]
 for row,item in enumerate(records):
  q=item.get("instruction","");cat=item.get("category","")
  if isinstance(q,str) and q.strip() and isinstance(cat,str) and cat.strip():
   pool.append((hashlib.sha256(SEED+q.encode()).hexdigest(),row,q,cat))
 pool.sort(key=lambda x:(x[0],x[1]));out=[];seen=set()
 for digest,row,q,cat in pool:
  if q in seen:continue
  seen.add(q);out.append({"source_row":row,"instruction":q,"category":cat,"instruction_sha256":hashlib.sha256(q.encode()).hexdigest(),"rank_sha256":digest})
  if len(out)==n:break
 if len(out)!=n:raise RuntimeError("G94_INSUFFICIENT_ORIGINAL_HELDOUT")
 return out
def p95(xs):
 if not xs:raise RuntimeError("G94_EMPTY_LATENCY_SAMPLE")
 return sorted(xs)[max(0,math.ceil(.95*len(xs))-1)]
def decode(model,full,suffix,shared_cache,prefix_len,tokens,torch,proc):
 t0=time.perf_counter_ns();c0=time.process_time_ns()
 if shared_cache is None:
  out=model(input_ids=full,use_cache=True);prefill=time.perf_counter_ns()-t0;clone=0
 else:
  tc=time.perf_counter_ns();past=copy.deepcopy(shared_cache);clone=time.perf_counter_ns()-tc
  plen=int(suffix.shape[1]);total=prefix_len+plen
  mask=torch.ones((1,total),dtype=torch.long)
  pos=torch.arange(prefix_len,total,dtype=torch.long).unsqueeze(0)
  ts=time.perf_counter_ns()
  out=model(input_ids=suffix,past_key_values=past,attention_mask=mask,position_ids=pos,use_cache=True)
  prefill=time.perf_counter_ns()-ts
 state,logits=out.past_key_values,out.logits[:,-1,:];generated=[];ds=time.perf_counter_ns()
 context=int(full.shape[1])
 for step in range(tokens):
  nxt=logits.argmax(-1,keepdim=True);generated.append(nxt)
  if step+1<tokens:
   mask=torch.ones((1,context+step+1),dtype=torch.long)
   pos=torch.tensor([[context+step]],dtype=torch.long)
   out=model(input_ids=nxt,past_key_values=state,attention_mask=mask,position_ids=pos,use_cache=True)
   state,logits=out.past_key_values,out.logits[:,-1,:]
 dec=time.perf_counter_ns()-ds;wall=time.perf_counter_ns()-t0;cpu=time.process_time_ns()-c0
 ids=torch.cat(generated,dim=1).flatten().tolist()
 return ids,{"request_wall_ns":wall,"prefill_ns":prefill,"decode_ns":dec,"cache_copy_ns":clone,"cpu_ns":cpu,
  "rss_bytes":proc.memory_info().rss,"output_sha256":hashlib.sha256(json.dumps(ids,separators=(",",":")).encode()).hexdigest()}
def run_baseline(model,inputs,tokens,torch,proc):
 start=time.perf_counter_ns();cpu=time.process_time_ns();rows=[];outputs={}
 for row,full,suffix in inputs:
  ids,m=decode(model,full,suffix,None,0,tokens,torch,proc);outputs[row]=ids;rows.append({"source_row":row,**m,"prefix_share_ns":0})
 return outputs,{"wall_ns":time.perf_counter_ns()-start,"cpu_ns":time.process_time_ns()-cpu,"prefix_setup_ns":0,
  "rows":rows,"responses":len(outputs),"generated_tokens":sum(map(len,outputs.values())),
  "max_rss":max(x["rss_bytes"] for x in rows),"hashes":{str(k):hashlib.sha256(json.dumps(v,separators=(",",":")).encode()).hexdigest() for k,v in outputs.items()}}
def run_candidate(model,inputs,prefix,n,tokens,torch,proc):
 start=time.perf_counter_ns();cpu=time.process_time_ns();rows=[];outputs={};setup_total=0;maxrss=proc.memory_info().rss;plen=int(prefix.shape[1])
 for gstart in range(0,CASES,n):
  group=inputs[gstart:gstart+n]
  ts=time.perf_counter_ns()
  with torch.inference_mode():cache=model(input_ids=prefix,use_cache=True).past_key_values
  setup=time.perf_counter_ns()-ts;setup_total+=setup;share=setup//len(group)
  for row,full,suffix in group:
   ids,m=decode(model,full,suffix,cache,plen,tokens,torch,proc);outputs[row]=ids
   rows.append({"source_row":row,**m,"prefix_share_ns":share})
   maxrss=max(maxrss,m["rss_bytes"])
 return outputs,{"wall_ns":time.perf_counter_ns()-start,"cpu_ns":time.process_time_ns()-cpu,
  "prefix_setup_ns":setup_total,"rows":rows,"responses":len(outputs),"generated_tokens":sum(map(len,outputs.values())),
  "max_rss":maxrss,"hashes":{str(k):hashlib.sha256(json.dumps(v,separators=(",",":")).encode()).hexdigest() for k,v in outputs.items()}}
def decide(trials):
 if len(trials)!=REPEATS:raise RuntimeError("G94_INCOMPLETE_REPETITIONS")
 summary={};allref=None
 for arm in ARMS:
  runs=[t["arms"][arm] for t in trials]
  if any(x["responses"]!=CASES or x["generated_tokens"]!=CASES*TOKENS for x in runs):raise RuntimeError("G94_INCOMPLETE_COHORT_"+arm)
  summary[arm]={"median_wall_ns":statistics.median(x["wall_ns"] for x in runs),
   "median_throughput_tokens_sec":statistics.median([CASES*TOKENS/(x["wall_ns"]/1e9) for x in runs]),
   "total_cpu_ns":sum(x["cpu_ns"] for x in runs),"max_sampled_rss_bytes":max(x["max_rss"] for x in runs),
   "total_prefix_setup_ns":sum(x["prefix_setup_ns"] for x in runs),
   "p95_amortized_request_ns":p95([r["request_wall_ns"]+r["prefix_share_ns"] for x in runs for r in x["rows"]])}
 base=summary["full_prompt_all12"];qual=[];baseline_rows=[r for t in trials for r in t["arms"]["full_prompt_all12"]["rows"]]
 base_by={}
 for row in baseline_rows:base_by.setdefault(row["source_row"],[]).append(row["request_wall_ns"])
 for n in COHORT_SIZES:
  arm="shared_prefix_cohort"+str(n);x=summary[arm]
  cand_rows=[r for t in trials for r in t["arms"][arm]["rows"]];cand_by={}
  for row in cand_rows:cand_by.setdefault(row["source_row"],[]).append(row["request_wall_ns"]+row["prefix_share_ns"])
  paired=[statistics.median(base_by[k])/statistics.median(cand_by[k]) for k in base_by]
  metrics={"cohort_size":n,"throughput_speedup":x["median_throughput_tokens_sec"]/base["median_throughput_tokens_sec"],
   "minimum_paired_request_speedup":min(paired),
   "p95_amortized_latency_ratio":x["p95_amortized_request_ns"]/base["p95_amortized_request_ns"],
   "cpu_ratio":x["total_cpu_ns"]/base["total_cpu_ns"],
   "rss_ratio":x["max_sampled_rss_bytes"]/base["max_sampled_rss_bytes"],
   "prefix_builds_per_repetition":CASES//n,"total_prefix_setup_ns":x["total_prefix_setup_ns"]}
  metrics["qualifies"]=(metrics["throughput_speedup"]>=1.15 and metrics["minimum_paired_request_speedup"]>=.90
   and metrics["p95_amortized_latency_ratio"]<=1.10 and metrics["cpu_ratio"]<=1.10 and metrics["rss_ratio"]<=1.10)
  qual.append(metrics)
 winners=sorted([x for x in qual if x["qualifies"]],key=lambda x:(-x["throughput_speedup"],x["cohort_size"]))
 return {"arms":summary,"cohort_qualification":qual,"selected_cohort_size":winners[0]["cohort_size"] if winners else None,
  "timed_authentic_responses":REPEATS*len(ARMS)*CASES,"timed_authentic_generated_tokens":REPEATS*len(ARMS)*CASES*TOKENS},("KV_COHORT_SCALE_PASS" if winners else "KV_COHORT_SCALE_NO_GO")
def main():
 import torch,transformers,psutil
 from transformers import AutoTokenizer,AutoModelForCausalLM
 contract()
 if platform.system()!="Linux" or platform.machine().lower() not in ("x86_64","amd64"):raise RuntimeError("G94_NOT_NATIVE_LINUX_X86_64")
 if torch.version.cuda is not None:raise RuntimeError("G94_NON_CPU_RUNTIME")
 torch.set_num_threads(1);torch.set_num_interop_threads(1);proc=psutil.Process();old=None
 receipt={"schema":"forge.cpu-llm-g94.kv-cohort-scaling.v1","gate":"CPU_G94","preregistration_commit":PREREG,
  "source_sha":os.getenv("GITHUB_SHA","UNSET"),"model_revision":MODEL_REV,"model_weights_sha256":WEIGHTS_SHA,
  "dataset_revision":DATA_REV,"dataset_sha256":DATA_SHA,"engineering":"UNVERIFIED","correctness":"UNVERIFIED",
  "decision":"UNVERIFIED","scientific_acceptance":"NOT_GRANTED","promotion_allowed":False,
  "runtime":{"torch":torch.__version__,"transformers":transformers.__version__,"python":platform.python_version(),
  "platform":platform.platform(),"machine":platform.machine(),"cpu":platform.processor(),"logical_cpus":os.cpu_count()},
  "limitations":["One GPT2 FP32 model, one Linux x86_64 runner, fixed 3 CPU cores",
   "Shared prefix exact G55 prefix; 12-request workload partitioned into cohort sizes 2/4/6/12",
   "GSM8K data ranks disjoint but not proven unseen in GPT2 pretraining","RSS sampled, no energy",
   "No production, unrelated-prefix traffic, other model, scientific acceptance or promotion claim"]}
 try:
  raw=Path("cpu_g94_original_gsm8k.jsonl")
  req=urllib.request.Request("https://raw.githubusercontent.com/openai/grade-school-math/"+DATA_REV+"/grade_school_math/data/test.jsonl",headers={"User-Agent":"FORGE-CPU-G94-KV-SCALE/1"})
  with urllib.request.urlopen(req,timeout=45) as inp,raw.open("xb") as out:
   count=0
   while True:
    b=inp.read(1<<20)
    if not b:break
    count+=len(b)
    if count>800000:raise RuntimeError("G94_DATA_SIZE_CAP")
    out.write(b)
  if raw.stat().st_size!=DATA_BYTES or sha_file(raw)!=DATA_SHA:raise RuntimeError("G94_DATA_IDENTITY_DRIFT")
  with raw.open(encoding="utf-8") as f:records=[{"instruction":x["question"],"category":"math_word_problem"} for x in (json.loads(line) for line in f if line.strip())]
  ranked=rank_original(records,OFFSET+CASES)
  g68=module("g94_g68","llm_g68/g68_gsm8k_http.py");g70=module("g94_g70","llm_g70/g70_gsm8k_locality.py")
  if ranked[:12]!=g68.select_heldout(records) or ranked[12:24]!=g70.select_heldout(records):raise RuntimeError("G94_RANK_CONTRACT_DRIFT")
  sel=ranked[OFFSET:OFFSET+CASES];receipt["selected_ranks"]=[OFFSET,OFFSET+CASES-1]
  receipt["selected"]=[{k:v for k,v in x.items() if k!="instruction"} for x in sel]
  g55=module("g94_g55","llm_g55/g55_gpt2_controls.py")
  if (g55.REV,g55.WEIGHT_SHA)!=(MODEL_REV,WEIGHTS_SHA):raise RuntimeError("G94_MODEL_IDENTITY_DRIFT")
  root,manifest=g55.stage();receipt["model_files"]=manifest;receipt["model_manifest_sha256"]=sha_file(root/"manifest.json")
  tok=AutoTokenizer.from_pretrained(str(root),local_files_only=True,trust_remote_code=False)
  model=AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,use_safetensors=True,trust_remote_code=False).eval()
  if not hasattr(proc,"cpu_affinity"):raise RuntimeError("G94_AFFINITY_UNAVAILABLE")
  old=proc.cpu_affinity()
  if len(old)<CPU_BUDGET:raise RuntimeError("G94_THREE_CPUS_REQUIRED")
  proc.cpu_affinity(old[:CPU_BUDGET]);receipt["fixed_affinity"]=proc.cpu_affinity();receipt["torch_interop_threads"]=torch.get_num_interop_threads()
  def encode(s):return tok(s,return_tensors="pt",add_special_tokens=False)["input_ids"]
  prefix=encode(g55.PREFIX);inputs=[]
  for x in sel:
   suffix=encode(x["instruction"]);full=torch.cat((prefix,suffix),dim=1)
   if full.shape[1]+TOKENS>model.config.n_positions:raise RuntimeError("G94_CONTEXT_OVERFLOW")
   inputs.append((x["source_row"],full,suffix))
  receipt["prefix_tokens"]=int(prefix.shape[1]);receipt["prefix_ids_sha256"]=hashlib.sha256(prefix.numpy().tobytes()).hexdigest()
  # First-token logits and greedy identity checked for every suffix.
  with torch.inference_mode():
   cache=model(input_ids=prefix,use_cache=True).past_key_values;checks=[]
   for row,full,suffix in inputs:
    a=model(input_ids=full,use_cache=True).logits[:,-1,:]
    mask=torch.ones((1,int(full.shape[1])),dtype=torch.long);pos=torch.arange(prefix.shape[1],full.shape[1]).unsqueeze(0)
    b=model(input_ids=suffix,past_key_values=copy.deepcopy(cache),attention_mask=mask,position_ids=pos,use_cache=True).logits[:,-1,:]
    if int(a.argmax(-1))!=int(b.argmax(-1)):raise RuntimeError("G94_FIRST_TOKEN_MISMATCH")
    checks.append({"source_row":row,"max_abs_logit_diff":float((a-b).abs().max())})
  receipt["first_token_checks"]=checks
  reference,_=run_baseline(model,inputs,TOKENS,torch,proc);trials=[]
  for rep in range(REPEATS):
   order=ARMS if rep%2==0 else tuple(reversed(ARMS));arms={}
   with torch.inference_mode():
    for arm in order:
     if arm=="full_prompt_all12":out,m=run_baseline(model,inputs,TOKENS,torch,proc)
     else:
      n=int(arm.rsplit("cohort",1)[1]);out,m=run_candidate(model,inputs,prefix,n,TOKENS,torch,proc)
     for row in reference:
      if out[row]!=reference[row]:raise RuntimeError("G94_EXACT_OUTPUT_MISMATCH_"+arm+"_"+str(row))
     arms[arm]=m
   trials.append({"rep":rep+1,"order":order,"arms":arms})
  metrics,decision=decide(trials);receipt["paired_trials"]=trials;receipt["metrics"]=metrics
  receipt["engineering"]="PASS";receipt["correctness"]="PASS";receipt["decision"]=decision
 except BaseException as exc:
  receipt["error"]=type(exc).__name__+": "+str(exc);receipt["traceback_tail"]=traceback.format_exc()[-3000:];raise
 finally:
  if old is not None:receipt["cpu_affinity_at_end"]=proc.cpu_affinity();proc.cpu_affinity(old)
  Path("cpu_g94_original_result.json").write_text(json.dumps(receipt,sort_keys=True,indent=2,default=str)+"\n")
  print(json.dumps({k:receipt.get(k) for k in ("gate","engineering","correctness","decision","metrics","error")},sort_keys=True),flush=True)
if __name__=="__main__":main()
