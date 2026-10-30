#!/usr/bin/env python3
"""G62: authentic 1.1B SDPA vs same-model prompt-lookup speculative generation."""
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import statistics
import time

REPO="TinyLlama/TinyLlama-1.1B-Chat-v1.0"
REV="c13e4efb205d7a8e5d13c088aa10a9dabac9b96a"
WEIGHT_SHA="6e6001da2106d4757498752a021df6c2bdc332c650aae4bae6b0c004dcf14933"
WEIGHT_BYTES=2200119864
FILES=("config.json","generation_config.json","model.safetensors",
       "tokenizer.json","tokenizer_config.json","special_tokens_map.json")
FAMILIES=("structured","grounded","freeform")
CONTEXTS=(512,1536)
NEW_TOKENS=64
TRIALS=5
WARMUPS=2
OUTPUT=Path(os.getenv("G62_RESULT","g62_result.json"))
def sha256(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def prompt(family):
 if family=="structured":
  pattern=("event | sector=materials | amount=400 | status=verified | "
           "owner=team-a | final_result=PASS\n")
  return ("The following is a repeated public test log. Continue the last row "
          "using the same fixed schema:\n"+pattern*340+
          "event | sector=materials | amount=400 | status=")
 if family=="grounded":
  pattern=("A team inspected the river bridge on Tuesday. The inspection "
           "record notes that the bridge uses reinforced steel and records "
           "the result as structurally sound. ")
  return ("Please continue a source-grounded passage consistently:\n"+
          pattern*400+"The inspection record notes that")
 if family=="freeform":
  bits=("The mechanisms of cultural transmission depend on context, "
        "independent observation, feedback, memory, social interaction, "
        "and the environment. ")
  text="".join(
   f"Section {i} discusses alternative arguments, constraints, and examples. {bits[i%len(bits)]}"
   for i in range(410))
  return text+"In summary, the next implication is"
 raise ValueError("UNKNOWN_FROZEN_FAMILY")
def median(rows):return statistics.median(rows)
def order(i):return ("baseline","candidate") if i%2==0 else ("candidate","baseline")
def decision(cases):
 structured=[x for x in cases if x["family"]=="structured"]
 geom=math.exp(sum(math.log(x["ratio_baseline_over_candidate"]) for x in cases)/len(cases))
 okay=all(x["ratio_baseline_over_candidate"]>=1.15 and x["all_token_ids_identical"] for x in structured)
 okay=okay and geom>=1.0 and all(x["candidate_peak_allocated_mib"]<=1.10*x["baseline_peak_allocated_mib"] for x in cases)
 return ("GO_NARROW_ENGINEERING" if okay else "NO_GO",geom)
def run():
 import torch
 import transformers
 from huggingface_hub import snapshot_download
 from transformers import AutoTokenizer,AutoModelForCausalLM
 torch.set_num_threads(2)
 torch.backends.cuda.matmul.allow_tf32=False
 result={"schema":"forge.acc.g62.prompt-lookup-v1","status":"UNVERIFIED",
  "head_sha":os.getenv("GITHUB_SHA",""),"platform":platform.platform(),
  "model_repo":REPO,"revision":REV,
  "expected_checkpoint_sha256":WEIGHT_SHA,
  "torch":torch.__version__,"cuda":torch.version.cuda,
  "transformers":transformers.__version__,
  "candidate":"standard transformers prompt_lookup_num_tokens=5 max_matching_ngram_size=3",
  "baseline":"same model standard SDPA greedy generate with KV cache",
  "prior_art":"known n-gram prompt-lookup speculative generation",
  "scientific_acceptance":"NOT_GRANTED",
  "novel_acceleration":False,"production_serving_optimized":False}
 try:
  if not torch.cuda.is_available() or not torch.version.cuda or tuple(map(int,torch.version.cuda.split(".")[:2]))<(12,8):
   raise RuntimeError("NO_VALID_CUDA_BLACKWELL_RUNTIME")
  dev=torch.device("cuda:0")
  name=torch.cuda.get_device_name(dev);cc=torch.cuda.get_device_capability(dev)
  free,total=torch.cuda.mem_get_info(dev)
  if cc!=(12,0) or "NVIDIA" not in name.upper() or free<7000*1024**2:
   raise RuntimeError("GPU_ADMISSION_FAILED")
  x=torch.ones((1024,1024),device=dev);y=x@x;torch.cuda.synchronize(dev)
  if y.device.type!="cuda" or abs(y[0,0].item()-1024)>1e-3:
   raise RuntimeError("REAL_GPU_MATMUL_FAILED")
  del x,y;torch.cuda.empty_cache()
  result["gpu"]={"name":name,"capability":list(cc),
    "free_mib_before":free//1024**2,"total_mib":total//1024**2}
  snap=Path(snapshot_download(repo_id=REPO,revision=REV,token=False,allow_patterns=list(FILES)))
  weight=snap/"model.safetensors"
  if not weight.is_file() or weight.stat().st_size!=WEIGHT_BYTES or sha256(weight)!=WEIGHT_SHA:
   raise RuntimeError("AUTHENTIC_MODEL_CHECKPOINT_IDENTITY_FAILED")
  result["model_safetensors_sha256"]=sha256(weight)
  result["download_manifest"]=[{"name":name,"sha256":sha256(snap/name)}
    for name in FILES if (snap/name).is_file()]
  tok=AutoTokenizer.from_pretrained(str(snap),use_fast=True,trust_remote_code=False,local_files_only=True)
  model=AutoModelForCausalLM.from_pretrained(
   str(snap),torch_dtype=torch.float16,attn_implementation="sdpa",
   local_files_only=True,trust_remote_code=False,use_safetensors=True).eval().to(dev)
  if model.config._attn_implementation!="sdpa" or model.config.model_type!="llama" or model.config.num_hidden_layers!=22:
   raise RuntimeError("MODEL_OR_SDPA_CONFIG_MISMATCH")
  from torch.profiler import profile,ProfilerActivity
  with torch.inference_mode(),profile(activities=[ProfilerActivity.CPU]) as prof:
   model(input_ids=torch.tensor([[1,10,20,30]],dtype=torch.long,device=dev),use_cache=True)
   torch.cuda.synchronize(dev)
  if "aten::scaled_dot_product_attention" not in [e.key for e in prof.key_averages()]:
   raise RuntimeError("ACTUAL_OPTIMIZED_SDPA_OPERATOR_NOT_OBSERVED")
  result["real_sdpa_operator_proof"]="PASS"
  result["parameters"]=sum(p.numel() for p in model.parameters())
  def generation(ids,arm):
   calls={"count":0}
   def hook(*_args,**_kwargs): calls["count"]+=1
   handle=model.register_forward_pre_hook(hook)
   kwargs=dict(input_ids=ids,do_sample=False,num_beams=1,
      use_cache=True,max_new_tokens=NEW_TOKENS,eos_token_id=-1,
      pad_token_id=tok.eos_token_id)
   if arm=="candidate":kwargs.update(prompt_lookup_num_tokens=5,max_matching_ngram_size=3)
   torch.cuda.synchronize(dev);torch.cuda.reset_peak_memory_stats(dev)
   t=time.perf_counter()
   try:out=model.generate(**kwargs)
   finally:handle.remove()
   torch.cuda.synchronize(dev)
   dt=time.perf_counter()-t
   continuation=out[0,ids.shape[1]:].detach().cpu().tolist()
   if len(continuation)!=NEW_TOKENS:
    raise RuntimeError(f"GENERATION_LENGTH_MISMATCH:{arm}:{len(continuation)}")
   return {"seconds":dt,"token_ids":continuation,
      "forward_calls":calls["count"],
      "peak_allocated_mib":torch.cuda.max_memory_allocated(dev)/1024**2,
      "peak_reserved_mib":torch.cuda.max_memory_reserved(dev)/1024**2}
  cases=[]
  with torch.inference_mode():
   for family in FAMILIES:
    all_ids=tok(prompt(family),return_tensors="pt",add_special_tokens=False)["input_ids"][0]
    if all_ids.numel()<max(CONTEXTS)+NEW_TOKENS:
     raise RuntimeError("PROMPT_FAMILY_TOO_SHORT:"+family)
    for length in CONTEXTS:
     ids=all_ids[-length:].reshape(1,-1).to(dev)
     if ids.shape[1]+NEW_TOKENS>model.config.max_position_embeddings:
      raise RuntimeError("CONTEXT_LIMIT_OVERFLOW")
     for arm in ("baseline","candidate"):
      for _ in range(WARMUPS):generation(ids,arm)
     trials={"baseline":[],"candidate":[]}
     for i in range(TRIALS):
      pair={}
      for arm in order(i):
       observation=generation(ids,arm)
       trials[arm].append(observation)
       pair[arm]=observation
      if pair["baseline"]["token_ids"]!=pair["candidate"]["token_ids"]:
       raise RuntimeError(f"GREEDY_SEQUENCE_MISMATCH:{family}:{length}:{i}")
     baseline=median([v["seconds"] for v in trials["baseline"]])
     candidate=median([v["seconds"] for v in trials["candidate"]])
     if baseline<=0 or candidate<=0:raise RuntimeError("NONPOSITIVE_LATENCY")
     info={"family":family,"prompt_tokens":length,"output_tokens":NEW_TOKENS,
       "ratio_baseline_over_candidate":baseline/candidate,
       "baseline_median_s":baseline,"candidate_median_s":candidate,
       "baseline_forward_call_median":median([v["forward_calls"] for v in trials["baseline"]]),
       "candidate_forward_call_median":median([v["forward_calls"] for v in trials["candidate"]]),
       "baseline_peak_allocated_mib":max(v["peak_allocated_mib"] for v in trials["baseline"]),
       "candidate_peak_allocated_mib":max(v["peak_allocated_mib"] for v in trials["candidate"]),
       "baseline_peak_reserved_mib":max(v["peak_reserved_mib"] for v in trials["baseline"]),
       "candidate_peak_reserved_mib":max(v["peak_reserved_mib"] for v in trials["candidate"]),
       "baseline_trials":[{k:v[k] for k in ("seconds","forward_calls","peak_allocated_mib","peak_reserved_mib")} for v in trials["baseline"]],
       "candidate_trials":[{k:v[k] for k in ("seconds","forward_calls","peak_allocated_mib","peak_reserved_mib")} for v in trials["candidate"]],
       "candidate_reduced_target_forward_calls":any(
           c["forward_calls"]<b["forward_calls"] for c,b in zip(trials["candidate"],trials["baseline"])),
       "all_token_ids_identical":True,
       "greedy_output_sha256":hashlib.sha256(json.dumps(trials["baseline"][0]["token_ids"]).encode()).hexdigest()}
     cases.append(info)
     print(f"G62_CASE {family} ctx={length} ratio={info['ratio_baseline_over_candidate']:.5f} calls={info['baseline_forward_call_median']}/{info['candidate_forward_call_median']}",flush=True)
  outcome,geom=decision(cases)
  result.update({"cases":cases,"disposition":outcome,"geomean_ratio":geom,
    "status":"PASS_AUTHENTIC_MATCHED_SDPA_SPECULATIVE_SCREEN"})
 except Exception as e:
  result.update({"status":"FAIL_OR_BLOCKED","error":f"{type(e).__name__}: {e}"})
  raise
 finally:
  OUTPUT.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
  print("G62_STATUS="+result["status"],flush=True)
  print("G62_DECISION="+str(result.get("disposition")),flush=True)
if __name__=="__main__":run()
