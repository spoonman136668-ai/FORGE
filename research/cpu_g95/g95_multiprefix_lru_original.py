#!/usr/bin/env python3
"""CPU G95: bounded LRU prefix KV reuse under interleaved multi-prefix GPT2 traffic."""
from __future__ import annotations
import copy,hashlib,importlib.util,json,math,os,platform,statistics,time,traceback,urllib.request
from collections import OrderedDict
from pathlib import Path

PREREG="5402308d56b354b599a8f4aecf81a0a15df9715e"
MODEL_REV="607a30d783dfa663caf39e06633721c8d4cfcd7e"
WEIGHTS_SHA="248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
DATA_REV="3101c7d5072418e28b9008a6636bde82a006892c"
DATA_SHA="3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14"
DATA_BYTES=749738
SEED=b"G68-GPT2-HELDOUT-20261030:"
OFFSET,QUESTIONS,REPEATS,TOKENS,CPU_BUDGET=264,12,4,8,3
CAPACITIES=(1,2,4)
ARMS=("no_prefix_cache","lru_capacity1","lru_capacity2","lru_capacity4")
PREFIX_TEXTS=(
 ("You are an assistant evaluating computational reuse. Answer precisely using the shared requirements, preserving correctness and avoiding unsupported claims. ")*12,
 ("You are an assistant evaluating computational reuse. Use the shared criteria to answer accurately, be concise, and do not make unsupported claims. ")*12,
 ("You are an assistant assessing computational reuse. Follow the shared requirements carefully, preserve correctness, and distinguish evidence from assumptions. ")*12,
 ("You are an assistant reviewing computational reuse. Give a precise answer based on the shared rules and avoid claims that evidence does not support. ")*12,
)
THRESHOLDS={"throughput_min":1.15,"min_paired":0.90,"p95_max":1.10,"cpu_max":1.10,"rss_max":1.15}

def contract():
 assert (OFFSET,QUESTIONS,REPEATS,TOKENS,CPU_BUDGET)==(264,12,4,8,3)
 assert CAPACITIES==(1,2,4)
 assert ARMS==("no_prefix_cache","lru_capacity1","lru_capacity2","lru_capacity4")
 assert len(PREFIX_TEXTS)==4 and len(set(PREFIX_TEXTS))==4
 assert all(x.count("You are an assistant")==12 for x in PREFIX_TEXTS)
 assert THRESHOLDS=={"throughput_min":1.15,"min_paired":0.90,"p95_max":1.10,"cpu_max":1.10,"rss_max":1.15}

def sha_file(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def module(name,rel):
 p=Path(__file__).resolve().parents[1]/rel
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

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
 if len(out)!=n:raise RuntimeError("G95_INSUFFICIENT_ORIGINAL_HELDOUT")
 return out

class PrefixLRU:
 def __init__(self,capacity):
  if capacity not in CAPACITIES:raise ValueError("G95_INVALID_CACHE_CAPACITY")
  self.capacity=capacity;self.entries=OrderedDict();self.evictions=[]
 def get(self,key):
  if key not in self.entries:return None
  value=self.entries.pop(key);self.entries[key]=value
  return value
 def put(self,key,value):
  if key in self.entries:self.entries.pop(key)
  evicted=None
  if len(self.entries)>=self.capacity:
   evicted_key,evicted_value=self.entries.popitem(last=False)
   evicted={"key":evicted_key,"kv_bytes":evicted_value["kv_bytes"]}
   self.evictions.append(evicted)
  self.entries[key]=value
  return evicted
 def resident_bytes(self):
  return sum(v["kv_bytes"] for v in self.entries.values())
 def keys_lru_to_mru(self):return list(self.entries.keys())

def tensor_tree_digest(value):
 h=hashlib.sha256()
 def visit(x):
  if isinstance(x,(tuple,list)):
   h.update(type(x).__name__.encode());h.update(str(len(x)).encode())
   for y in x:visit(y)
  elif hasattr(x,"detach") and hasattr(x,"dtype"):
   t=x.detach().cpu().contiguous()
   h.update(str(t.dtype).encode());h.update(str(tuple(t.shape)).encode());h.update(t.numpy().tobytes())
  else:raise RuntimeError("G95_UNSUPPORTED_CACHE_TREE")
 visit(value);return h.hexdigest()

def tensor_tree_bytes(value):
 total=0
 def visit(x):
  nonlocal total
  if isinstance(x,(tuple,list)):
   for y in x:visit(y)
  elif hasattr(x,"numel") and hasattr(x,"element_size"):
   total+=int(x.numel())*int(x.element_size())
  else:raise RuntimeError("G95_UNSUPPORTED_CACHE_TREE")
 visit(value);return total

def tensor_storage_ptrs(value):
 ptrs=set()
 def visit(x):
  if isinstance(x,(tuple,list)):
   for y in x:visit(y)
  elif hasattr(x,"data_ptr"):ptrs.add(int(x.data_ptr()))
  else:raise RuntimeError("G95_UNSUPPORTED_CACHE_TREE")
 visit(value);return ptrs

def build_stream(items):
 # Three questions per prefix, round-robin prefix order, repeated for four cycles.
 per_prefix={p:[] for p in range(4)}
 for i,item in enumerate(items):per_prefix[i%4].append(item)
 if any(len(v)!=3 for v in per_prefix.values()):raise RuntimeError("G95_PREFIX_QUESTION_ALLOCATION")
 stream=[]
 for cycle in range(REPEATS):
  for qidx in range(3):
   for prefix_id in range(4):
    row,suffix=per_prefix[prefix_id][qidx]
    stream.append({"cycle":cycle,"prefix_id":prefix_id,"question_index":qidx,"source_row":row,"suffix":suffix})
 return stream

def request_decode(model,full,suffix,past,prefix_len,tokens,torch,proc):
 start=time.perf_counter_ns();cpu0=time.process_time_ns()
 plen=int(suffix.shape[1]);total=prefix_len+plen
 mask=torch.ones((1,total),dtype=torch.long)
 pos=torch.arange(prefix_len,total,dtype=torch.long).unsqueeze(0)
 out=model(input_ids=suffix,past_key_values=past,attention_mask=mask,position_ids=pos,use_cache=True)
 state,logits=out.past_key_values,out.logits[:,-1,:];generated=[];decode_start=time.perf_counter_ns()
 for step in range(tokens):
  nxt=logits.argmax(-1,keepdim=True);generated.append(nxt)
  if step+1<tokens:
   mask=torch.ones((1,total+step+1),dtype=torch.long)
   pos=torch.tensor([[total+step]],dtype=torch.long)
   out=model(input_ids=nxt,past_key_values=state,attention_mask=mask,position_ids=pos,use_cache=True)
   state,logits=out.past_key_values,out.logits[:,-1,:]
 dec=time.perf_counter_ns()-decode_start
 ids=torch.cat(generated,dim=1).flatten().tolist()
 return ids,{"request_wall_ns":time.perf_counter_ns()-start,"request_cpu_ns":time.process_time_ns()-cpu0,
  "suffix_prefill_ns":0,"decode_ns":dec,"cache_copy_ns":0,"output_sha256":hashlib.sha256(json.dumps(ids,separators=(",",":")).encode()).hexdigest(),
  "rss_bytes":proc.memory_info().rss}

def baseline_request(model,full,tokens,torch,proc):
 t0=time.perf_counter_ns();c0=time.process_time_ns()
 with torch.inference_mode():
  out=model(input_ids=full,use_cache=True)
  past,logits=out.past_key_values,out.logits[:,-1,:]
  generated=[];decode_start=time.perf_counter_ns()
  for step in range(tokens):
   nxt=logits.argmax(-1,keepdim=True);generated.append(nxt)
   if step+1<tokens:
    mask=torch.ones((1,int(full.shape[1])+step+1),dtype=torch.long)
    pos=torch.tensor([[int(full.shape[1])+step]],dtype=torch.long)
    out=model(input_ids=nxt,past_key_values=past,attention_mask=mask,position_ids=pos,use_cache=True)
    past,logits=out.past_key_values,out.logits[:,-1,:]
 decode=time.perf_counter_ns()-decode_start
 ids=torch.cat(generated,dim=1).flatten().tolist()
 return ids,{"request_wall_ns":time.perf_counter_ns()-t0,"request_cpu_ns":time.process_time_ns()-c0,
  "prefix_build_ns":0,"cache_copy_ns":0,"decode_ns":decode,"output_sha256":hashlib.sha256(json.dumps(ids,separators=(",",":")).encode()).hexdigest(),
  "rss_bytes":proc.memory_info().rss}

def key_for(prefix_ids,tokenizer_fingerprint):
 material={"model_revision":MODEL_REV,"weights_sha256":WEIGHTS_SHA,"tokenizer_fingerprint":tokenizer_fingerprint,
  "dtype":"float32","cache_semantics":"gpt2-causal-fp32-v1","prefix_ids_sha256":hashlib.sha256(prefix_ids.numpy().tobytes()).hexdigest()}
 return hashlib.sha256(json.dumps(material,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def run_no_cache(model,stream,prefixes,torch,proc):
 start=time.perf_counter_ns();cpu0=time.process_time_ns();rows=[];outs={}
 with torch.inference_mode():
  for idx,req in enumerate(stream):
   full=torch.cat((prefixes[req["prefix_id"]],req["suffix"]),dim=1)
   ids,m=baseline_request(model,full,TOKENS,torch,proc);outs[idx]=ids
   rows.append({"stream_index":idx,"cycle":req["cycle"],"prefix_id":req["prefix_id"],"source_row":req["source_row"],**m})
 wall=time.perf_counter_ns()-start;cpu=time.process_time_ns()-cpu0
 return outs,{"wall_ns":wall,"cpu_ns":cpu,"rows":rows,"responses":len(outs),"generated_tokens":sum(map(len,outs.values())),
  "max_rss":max(x["rss_bytes"] for x in rows),"hits":0,"misses":len(stream),"evictions":0,"retained_kv_bytes":0,
  "hashes":{str(k):hashlib.sha256(json.dumps(v,separators=(",",":")).encode()).hexdigest() for k,v in outs.items()}}

def run_lru(model,stream,prefixes,prefix_keys,capacity,torch,proc):
 cache=PrefixLRU(capacity);start=time.perf_counter_ns();cpu0=time.process_time_ns();rows=[];outs={}
 with torch.inference_mode():
  for idx,req in enumerate(stream):
   t0=time.perf_counter_ns();c0=time.process_time_ns()
   pid=req["prefix_id"];key=prefix_keys[pid];entry=cache.get(key);hit=entry is not None;build_ns=0;evicted=None
   if entry is None:
    tb=time.perf_counter_ns();pout=model(input_ids=prefixes[pid],use_cache=True);past=pout.past_key_values
    build_ns=time.perf_counter_ns()-tb
    entry={"past":past,"snapshot":tensor_tree_digest(past),"kv_bytes":tensor_tree_bytes(past)}
    evicted=cache.put(key,entry)
   tc=time.perf_counter_ns();request_past=copy.deepcopy(entry["past"]);copy_ns=time.perf_counter_ns()-tc
   if tensor_tree_ptrs:=tensor_storage_ptrs(request_past):
    if tensor_tree_ptrs & tensor_storage_ptrs(entry["past"]):raise RuntimeError("G95_CACHE_STORAGE_ALIAS")
   suffix=req["suffix"];prefix_len=int(prefixes[pid].shape[1])
   ids,m=request_decode(model,torch.cat((prefixes[pid],suffix),dim=1),suffix,request_past,prefix_len,TOKENS,torch,proc)
   if tensor_tree_digest(entry["past"])!=entry["snapshot"]:raise RuntimeError("G95_RESIDENT_KV_MUTATED")
   wall=time.perf_counter_ns()-t0;cpu=time.process_time_ns()-c0
   outs[idx]=ids
   rows.append({"stream_index":idx,"cycle":req["cycle"],"prefix_id":pid,"source_row":req["source_row"],
    "cache_key":key,"hit":hit,"miss":not hit,"evicted_key":evicted["key"] if evicted else None,
    "cache_occupancy":len(cache.entries),"lru_keys":cache.keys_lru_to_mru(),
    "prefix_build_ns":build_ns,"cache_copy_ns":copy_ns,"request_wall_ns":wall,"request_cpu_ns":cpu,
    "suffix_prefill_ns":m["request_wall_ns"]-m["decode_ns"],"decode_ns":m["decode_ns"],
    "rss_bytes":m["rss_bytes"],"resident_kv_bytes":cache.resident_bytes(),
    "resident_snapshot_sha256":entry["snapshot"],"output_sha256":m["output_sha256"]})
 wall=time.perf_counter_ns()-start;cpu=time.process_time_ns()-cpu0
 return outs,{"wall_ns":wall,"cpu_ns":cpu,"rows":rows,"responses":len(outs),"generated_tokens":sum(map(len,outs.values())),
  "max_rss":max(x["rss_bytes"] for x in rows),"hits":sum(x["hit"] for x in rows),"misses":sum(x["miss"] for x in rows),
  "evictions":len(cache.evictions),"eviction_rows":cache.evictions,"retained_kv_bytes":cache.resident_bytes(),
  "max_resident_kv_bytes":max(x["resident_kv_bytes"] for x in rows),
  "hashes":{str(k):hashlib.sha256(json.dumps(v,separators=(",",":")).encode()).hexdigest() for k,v in outs.items()}}

def percentile95(xs):return sorted(xs)[max(0,math.ceil(.95*len(xs))-1)]
def decide(trials):
 if len(trials)!=REPEATS:raise RuntimeError("G95_INCOMPLETE_REPETITIONS")
 summaries={};base_runs=[t["arms"]["no_prefix_cache"] for t in trials]
 for arm in ARMS:
  runs=[t["arms"][arm] for t in trials]
  if any(x["responses"]!=48 or x["generated_tokens"]!=48*TOKENS for x in runs):raise RuntimeError("G95_INCOMPLETE_STREAM_"+arm)
  summaries[arm]={"median_wall_ns":statistics.median(x["wall_ns"] for x in runs),
   "median_tokens_per_second":statistics.median([48*TOKENS/(x["wall_ns"]/1e9) for x in runs]),
   "total_cpu_ns":sum(x["cpu_ns"] for x in runs),"max_sampled_rss_bytes":max(x["max_rss"] for x in runs),
   "hits":sum(x["hits"] for x in runs),"misses":sum(x["misses"] for x in runs),
   "evictions":sum(x["evictions"] for x in runs),"final_retained_kv_bytes":max(x["retained_kv_bytes"] for x in runs),
   "max_resident_kv_bytes":max(x.get("max_resident_kv_bytes",0) for x in runs),
   "p95_request_ns":percentile95([r["request_wall_ns"] for x in runs for r in x["rows"]])}
 base=summaries["no_prefix_cache"];base_rows=[r for x in base_runs for r in x["rows"]];qual=[]
 for cap in CAPACITIES:
  arm="lru_capacity"+str(cap);x=summaries[arm];cand_runs=[t["arms"][arm] for t in trials]
  btimes=[r["request_wall_ns"] for z in base_runs for r in z["rows"]]
  ctimes=[r["request_wall_ns"] for z in cand_runs for r in z["rows"]]
  paired=[b/c for b,c in zip(btimes,ctimes)]
  metrics={"capacity":cap,"throughput_speedup":x["median_tokens_per_second"]/base["median_tokens_per_second"],
   "minimum_paired_request_speedup":min(paired),"p95_latency_ratio":x["p95_request_ns"]/base["p95_request_ns"],
   "cpu_ratio":x["total_cpu_ns"]/base["total_cpu_ns"],"rss_ratio":x["max_sampled_rss_bytes"]/base["max_sampled_rss_bytes"],
   "hit_rate":x["hits"]/(x["hits"]+x["misses"]) if x["hits"]+x["misses"] else 0,
   "evictions":x["evictions"],"max_resident_kv_bytes":x["max_resident_kv_bytes"]}
  metrics["qualifies"]=(metrics["throughput_speedup"]>=THRESHOLDS["throughput_min"] and
   metrics["minimum_paired_request_speedup"]>=THRESHOLDS["min_paired"] and metrics["p95_latency_ratio"]<=THRESHOLDS["p95_max"] and
   metrics["cpu_ratio"]<=THRESHOLDS["cpu_max"] and metrics["rss_ratio"]<=THRESHOLDS["rss_max"])
  qual.append(metrics)
 winners=sorted([x for x in qual if x["qualifies"]],key=lambda x:(-x["throughput_speedup"],x["capacity"]))
 return {"arms":summaries,"capacity_qualification":qual,"selected_capacity":winners[0]["capacity"] if winners else None,
  "timed_authentic_responses":REPEATS*len(ARMS)*48,"timed_authentic_generated_tokens":REPEATS*len(ARMS)*48*TOKENS},("MULTIPREFIX_LRU_PASS" if winners else "MULTIPREFIX_LRU_NO_GO")

def main():
 import torch,transformers,psutil
 from transformers import AutoTokenizer,AutoModelForCausalLM
 contract()
 if platform.system()!="Linux" or platform.machine().lower() not in ("x86_64","amd64"):raise RuntimeError("G95_NOT_NATIVE_LINUX_X86_64")
 if torch.version.cuda is not None:raise RuntimeError("G95_NON_CPU_RUNTIME")
 torch.set_num_threads(2);torch.set_num_interop_threads(1)
 if torch.get_num_threads()!=2 or torch.get_num_interop_threads()!=1:raise RuntimeError("G95_THREAD_CONTRACT_MISMATCH")
 proc=psutil.Process();old=None
 receipt={"schema":"forge.cpu-llm-g95.multi-prefix-lru.v1","gate":"CPU_G95","preregistration_commit":PREREG,
  "source_sha":os.getenv("GITHUB_SHA","UNSET"),"model_revision":MODEL_REV,"model_weights_sha256":WEIGHTS_SHA,
  "dataset_revision":DATA_REV,"dataset_sha256":DATA_SHA,"engineering":"UNVERIFIED","correctness":"UNVERIFIED",
  "decision":"UNVERIFIED","scientific_acceptance":"NOT_GRANTED","promotion_allowed":False,
  "runtime":{"torch":torch.__version__,"transformers":transformers.__version__,"python":platform.python_version(),
  "platform":platform.platform(),"machine":platform.machine(),"cpu":platform.processor(),"logical_cpus":os.cpu_count(),\n  "torch_intraop_threads":torch.get_num_threads(),"torch_interop_threads":torch.get_num_interop_threads()},
  "limitations":["Four exact prefix keys and deterministic round-robin traffic only","Original GPT2 FP32 CPU workload; one Linux x86_64 virtualized host, 3-core affinity",
   "GSM8K rank cohort disjoint but not proven unseen in GPT2 pretraining","Sampled RSS, no energy metric",
   "No production/general-traffic/other-model/scientific acceptance/promotion claim"]}
 try:
  raw=Path("cpu_g95_original_gsm8k.jsonl")
  req=urllib.request.Request("https://raw.githubusercontent.com/openai/grade-school-math/"+DATA_REV+"/grade_school_math/data/test.jsonl",headers={"User-Agent":"FORGE-CPU-G95-MULTIPREFIX-LRU/1"})
  with urllib.request.urlopen(req,timeout=45) as inp,raw.open("xb") as out:
   count=0
   while True:
    b=inp.read(1<<20)
    if not b:break
    count+=len(b)
    if count>800000:raise RuntimeError("G95_DATA_SIZE_CAP")
    out.write(b)
  if raw.stat().st_size!=DATA_BYTES or sha_file(raw)!=DATA_SHA:raise RuntimeError("G95_DATA_IDENTITY_DRIFT")
  with raw.open(encoding="utf-8") as f:records=[{"instruction":x["question"],"category":"math_word_problem"} for x in (json.loads(line) for line in f if line.strip())]
  ranked=rank_original(records,OFFSET+QUESTIONS)
  g68=module("g95_g68","llm_g68/g68_gsm8k_http.py");g70=module("g95_g70","llm_g70/g70_gsm8k_locality.py")
  if ranked[:12]!=g68.select_heldout(records) or ranked[12:24]!=g70.select_heldout(records):raise RuntimeError("G95_RANK_CONTRACT_DRIFT")
  selected=ranked[OFFSET:OFFSET+QUESTIONS]
  receipt["selected_ranks"]=[OFFSET,OFFSET+QUESTIONS-1]
  receipt["selected"]=[{k:v for k,v in x.items() if k!="instruction"} for x in selected]
  g55=module("g95_g55","llm_g55/g55_gpt2_controls.py")
  if (g55.REV,g55.WEIGHT_SHA)!=(MODEL_REV,WEIGHTS_SHA):raise RuntimeError("G95_MODEL_IDENTITY_DRIFT")
  root,manifest=g55.stage();receipt["model_files"]=manifest;receipt["model_manifest_sha256"]=sha_file(root/"manifest.json")
  tok=AutoTokenizer.from_pretrained(str(root),local_files_only=True,trust_remote_code=False)
  model=AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,use_safetensors=True,trust_remote_code=False).eval()
  if not hasattr(proc,"cpu_affinity"):raise RuntimeError("G95_AFFINITY_UNAVAILABLE")
  old=proc.cpu_affinity()
  if len(old)<CPU_BUDGET:raise RuntimeError("G95_THREE_CPUS_REQUIRED")
  proc.cpu_affinity(old[:CPU_BUDGET]);receipt["fixed_affinity"]=proc.cpu_affinity()
  receipt["torch_interop_threads"]=torch.get_num_interop_threads()
  def encode(txt):return tok(txt,return_tensors="pt",add_special_tokens=False)["input_ids"]
  prefixes=[encode(x) for x in PREFIX_TEXTS]
  tokfp=hashlib.sha256("".join(x["sha256"] for x in manifest).encode()).hexdigest()
  pkeys=[key_for(x,tokfp) for x in prefixes]
  if len(set(pkeys))!=4:raise RuntimeError("G95_PREFIX_KEY_COLLISION")
  items=[]
  for i,item in enumerate(selected):
   pid=i%4;suffix=encode(item["instruction"])
   full=torch.cat((prefixes[pid],suffix),dim=1)
   if full.shape[1]+TOKENS>model.config.n_positions:raise RuntimeError("G95_CONTEXT_OVERFLOW")
   items.append((item["source_row"],suffix))
  stream=build_stream(items)
  receipt["prefixes"]=[{"prefix_id":i,"text_sha256":hashlib.sha256(PREFIX_TEXTS[i].encode()).hexdigest(),
    "token_ids_sha256":hashlib.sha256(prefixes[i].numpy().tobytes()).hexdigest(),"tokens":int(prefixes[i].shape[1]),
    "cache_key":pkeys[i]} for i in range(4)]
  receipt["stream_sha256"]=hashlib.sha256(json.dumps([{k:v for k,v in x.items() if k!="suffix"} for x in stream],sort_keys=True,separators=(",",":")).encode()).hexdigest()
  # Verify next-token logits for all twelve exact prefix/suffix pairs.
  checks=[]
  with torch.inference_mode():
   for pid in range(4):
    pc=model(input_ids=prefixes[pid],use_cache=True).past_key_values
    for row,suffix in items[pid::4]:
     full=torch.cat((prefixes[pid],suffix),dim=1)
     a=model(input_ids=full,use_cache=True).logits[:,-1,:]
     mask=torch.ones((1,int(full.shape[1])),dtype=torch.long)
     pos=torch.arange(int(prefixes[pid].shape[1]),int(full.shape[1])).unsqueeze(0)
     b=model(input_ids=suffix,past_key_values=copy.deepcopy(pc),attention_mask=mask,position_ids=pos,use_cache=True).logits[:,-1,:]
     if int(a.argmax(-1))!=int(b.argmax(-1)):raise RuntimeError("G95_FIRST_TOKEN_MISMATCH")
     checks.append({"prefix_id":pid,"source_row":row,"max_abs_logit_diff":float((a-b).abs().max())})
  receipt["first_token_checks"]=checks
  references={}
  with torch.inference_mode():
   for idx,req0 in enumerate(stream):
    pid=req0["prefix_id"];row=req0["source_row"];suffix=req0["suffix"]
    full=torch.cat((prefixes[pid],suffix),dim=1)
    ids,_=baseline_request(model,full,TOKENS,torch,proc);references[idx]=ids
  trials=[]
  for rep in range(REPEATS):
   order=ARMS if rep%2==0 else tuple(reversed(ARMS));arms={}
   with torch.inference_mode():
    for arm in order:
     if arm=="no_prefix_cache":out,m=run_no_cache(model,stream,prefixes,torch,proc)
     else:
      cap=int(arm.rsplit("capacity",1)[1]);out,m=run_lru(model,stream,prefixes,pkeys,cap,torch,proc)
     for idx in references:
      if out[idx]!=references[idx]:raise RuntimeError("G95_EXACT_TOKEN_MISMATCH_"+arm+"_"+str(idx))
     arms[arm]=m
   trials.append({"rep":rep+1,"order":order,"arms":arms})
  metrics,decision=decide(trials)
  receipt["paired_trials"]=trials;receipt["metrics"]=metrics
  receipt["engineering"]="PASS";receipt["correctness"]="PASS";receipt["decision"]=decision
 except BaseException as exc:
  receipt["error"]=type(exc).__name__+": "+str(exc);receipt["traceback_tail"]=traceback.format_exc()[-3000:];raise
 finally:
  if old is not None:receipt["cpu_affinity_at_end"]=proc.cpu_affinity();proc.cpu_affinity(old)
  Path("cpu_g95_original_result.json").write_text(json.dumps(receipt,sort_keys=True,indent=2,default=str)+"\n",encoding="utf-8")
  print(json.dumps({k:receipt.get(k) for k in ("gate","engineering","correctness","decision","metrics","error")},sort_keys=True),flush=True)
if __name__=="__main__":main()
