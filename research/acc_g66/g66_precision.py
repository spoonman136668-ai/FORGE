#!/usr/bin/env python3
"""ACC G66 frozen numerical precision experiment, not an acceleration claim."""
from __future__ import annotations
import gc, hashlib, json, os, platform, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"acc_g65"))
import g65_logit_path as original
g64=original.g64
g63=g64.original

G65_BLOB="6dd9bbed1793237fa5d4d34e7c9762aaec45471a"
DTYPES=("float16","float32")
MODES=("cached_one_by_one","cached_chunk_48","full_no_cache")
REPEATS=3
GENERATED=64
RESULT=Path(os.getenv("G66_RESULT","g66_result.json"))
CORPUS=Path(os.getenv("G66_CORPUS","g66_wikitext_test.txt"))

def frozen_identity():
 if g64.git_blob(Path(original.__file__).read_bytes())!=G65_BLOB:
  raise RuntimeError("G65_CANONICAL_SOURCE_DRIFT")
 result=original.identity()
 if original.MODES!=MODES or original.REPEATS!=REPEATS:
  raise RuntimeError("G65_FROZEN_NUMERICAL_PATH_DRIFT")
 return {"g65_source_blob":G65_BLOB,**result}

def sha_ids(ids):
 return hashlib.sha256(json.dumps(ids).encode()).hexdigest()

def first_difference(a,b):
 if len(a)!=GENERATED or len(b)!=GENERATED:raise RuntimeError("OUTPUT_LENGTH_NOT_64")
 for i,(x,y) in enumerate(zip(a,b)):
  if x!=y:return {"same":False,"index":i,"baseline_id":x,"candidate_id":y}
 return {"same":True,"index":None}

def categorical(rows):
 if set(rows)!=set(DTYPES) or any(set(rows[d])!=set(MODES) for d in DTYPES):
  raise ValueError("EXPECTED_ALL_PRECISIONS_AND_MODES")
 for d in DTYPES:
  if any(len(rows[d][m])!=REPEATS for m in MODES):
   raise ValueError("EXPECTED_THREE_MODE_REPEATS")
 d=rows["float32"]
 vals={m:[x["greedy_argmax_id"] for x in d[m]] for m in MODES}
 consistent=all(len(set(x))==1 for x in vals.values())
 resolved=consistent and len({x[0] for x in vals.values()})==1
 return {"fp32_forced_shared48_cached_vs_full_split_resolved":resolved,
         "fp32_forced_shared48_comparison":"FP32_CACHED_FULL_SPLIT_RESOLVED" if resolved else "FP32_CACHED_FULL_SPLIT_PERSISTS",
         "fp32_top1_by_mode":vals,
         "g63_original_qualification":"FAIL_NO_GO_UNCHANGED"}

def logits_forced_prefix(model,prompt,shared,mode):
 import torch
 if mode=="full_no_cache":
  return model(input_ids=torch.cat((prompt,shared),dim=1),use_cache=False).logits[0,-1,:]
 first=model(input_ids=prompt,use_cache=True)
 state=first.past_key_values
 if mode=="cached_chunk_48":
  mask=torch.ones((1,prompt.shape[1]+shared.shape[1]),device=prompt.device,dtype=torch.long)
  return model(input_ids=shared,past_key_values=state,attention_mask=mask,use_cache=True).logits[0,-1,:]
 if mode=="cached_one_by_one":
  for i in range(shared.shape[1]):
   mask=torch.ones((1,prompt.shape[1]+i+1),device=prompt.device,dtype=torch.long)
   out=model(input_ids=shared[:,i:i+1],past_key_values=state,attention_mask=mask,use_cache=True)
   state=out.past_key_values
  return out.logits[0,-1,:]
 raise ValueError("UNKNOWN_FROZEN_LOGIT_MODE")

def original_generate(model,prompt,tokenizer,arm):
 import torch
 kwargs=dict(input_ids=prompt,do_sample=False,num_beams=1,use_cache=True,
  max_new_tokens=GENERATED,eos_token_id=-1,pad_token_id=tokenizer.eos_token_id)
 if arm=="candidate":kwargs.update(prompt_lookup_num_tokens=5,max_matching_ngram_size=3)
 output=model.generate(**kwargs)
 torch.cuda.synchronize(prompt.device)
 raw=output[0,prompt.shape[1]:].detach().cpu().tolist()
 accepted,count=g64.audited_continuation(raw,arm)
 return {"tokens":accepted,"sha256":sha_ids(accepted),"raw_count":count,
         "charged_extra_tokens":count-GENERATED}

def run():
 import torch
 import transformers
 from transformers import AutoModelForCausalLM,AutoTokenizer
 from huggingface_hub import snapshot_download
 torch.set_num_threads(2)
 torch.backends.cuda.matmul.allow_tf32=False
 receipt={"schema":"forge.acc.g66.fp16-fp32-numerical-forensics.v1",
  "status":"UNVERIFIED","source_head":os.getenv("GITHUB_SHA",""),
  "torch":torch.__version__,"cuda":torch.version.cuda,"transformers":transformers.__version__,
  "platform":platform.platform(),"original_g63_final":"FAIL_NO_GO_UNCHANGED",
  "scientific_acceptance":"NOT_GRANTED","novel_acceleration":False,
  "diagnostic_not_production_change":True}
 try:
  receipt["sources"]=frozen_identity()
  source=g63.frozen_source(CORPUS)
  if hashlib.sha256(source).hexdigest()!=g64.G63_CORPUS_SHA256:
   raise RuntimeError("FROZEN_WIKITEXT_BYTES_DRIFT")
  receipt["corpus_sha256"]=hashlib.sha256(source).hexdigest()
  if not torch.cuda.is_available() or not torch.version.cuda or tuple(map(int,torch.version.cuda.split(".")[:2]))<(12,8):
   raise RuntimeError("INVALID_REAL_BLACKWELL_CUDA_RUNTIME")
  device=torch.device("cuda:0")
  free,total=torch.cuda.mem_get_info(device)
  name=torch.cuda.get_device_name(device);cc=torch.cuda.get_device_capability(device)
  if cc!=(12,0) or "NVIDIA" not in name.upper() or free<7500*1024**2:
   raise RuntimeError("GPU_IDENTITY_OR_VRAM_UNAVAILABLE")
  a=torch.ones((1024,1024),device=device);b=a@a;torch.cuda.synchronize(device)
  if b.device.type!="cuda" or abs(float(b[0,0])-1024)>1e-4:
   raise RuntimeError("REAL_CUDA_MATMUL_FAILED")
  del a,b
  torch.cuda.empty_cache()
  receipt["gpu"]={"name":name,"compute_capability":list(cc),"free_mib_before":free//1024**2,"total_mib":total//1024**2}
  snap=Path(snapshot_download(repo_id=g63.REPO,revision=g63.REV,token=False,allow_patterns=list(g63.FILES)))
  p=snap/"model.safetensors"
  if not p.is_file() or p.stat().st_size!=g63.WEIGHT_SIZE or g64.file_sha256(p)!=g63.WEIGHT_SHA:
   raise RuntimeError("AUTHENTIC_TINYLLAMA_WEIGHT_SHA_DRIFT")
  receipt["actual_weight_sha256"]=g64.file_sha256(p)
  tok=AutoTokenizer.from_pretrained(str(snap),use_fast=True,local_files_only=True,trust_remote_code=False)
  src_tokens=g63.frozen_sample_tokens(tok,source.decode("utf-8"),g63.ANCHORS[2])
  prompt=g63.case_ids(torch,tok,src_tokens,"natural_continuation",1536).to(device)
  if original.token_sha(prompt[0].detach().cpu().tolist())!=original.G64_PROMPT_HASH:
   raise RuntimeError("ORIGINAL_G64_PROMPT_TOKEN_HASH_DRIFT")
  receipt["prompt_sha256"]=original.G64_PROMPT_HASH
  results={};generation={}
  from torch.profiler import profile,ProfilerActivity
  with torch.inference_mode():
   for label,dtype in (("float16",torch.float16),("float32",torch.float32)):
    model=AutoModelForCausalLM.from_pretrained(str(snap),torch_dtype=dtype,
      attn_implementation="sdpa",use_safetensors=True,local_files_only=True,
      trust_remote_code=False).eval().to(device)
    if (model.config.model_type!="llama" or model.config.num_hidden_layers!=22
        or model.config._attn_implementation!="sdpa"
        or next(model.parameters()).dtype!=dtype
        or next(model.parameters()).device.type!="cuda"):
     raise RuntimeError("MODEL_DTYPE_OR_ATTENTION_DRIFT")
    with profile(activities=[ProfilerActivity.CPU]) as prof:
     model(input_ids=prompt[:,:16],use_cache=True)
     torch.cuda.synchronize(device)
    if "aten::scaled_dot_product_attention" not in [x.key for x in prof.key_averages()]:
     raise RuntimeError("REAL_SDPA_OPERATOR_MISSING")
    if label=="float16":
     original.validate_orig_outputs(model,prompt,tok)
    arms={arm:original_generate(model,prompt,tok,arm) for arm in ("baseline","candidate")}
    delta=first_difference(arms["baseline"]["tokens"],arms["candidate"]["tokens"])
    if label=="float16":
     if (arms["baseline"]["sha256"]!=original.BASELINE_SHA or
       arms["candidate"]["sha256"]!=original.CANDIDATE_SHA or
       delta["index"]!=original.POSITION or
       (delta["baseline_id"],delta["candidate_id"])!=(original.BASELINE_ID,original.CANDIDATE_ID)):
      raise RuntimeError("G64_FP16_GENERATION_REPRODUCTION_DRIFT")
    generation[label]={
      "baseline_sha256":arms["baseline"]["sha256"],
      "candidate_sha256":arms["candidate"]["sha256"],
      "baseline_raw_count":arms["baseline"]["raw_count"],
      "candidate_raw_count":arms["candidate"]["raw_count"],
      "candidate_extra_work_charged_tokens":arms["candidate"]["charged_extra_tokens"],
      "first_difference":delta,
      "exact_parity":delta["same"]
    }
    shared=torch.tensor([arms["baseline"]["tokens"][:original.SHARED_TOKENS]],device=device,dtype=torch.long) if label=="float16" else frozen_shared
    if label=="float16":
     frozen_shared=shared.clone()
    # FP32 uses the ORIGINAL FP16-verified frozen prefix, not its own generated prefix.
    rows={m:[] for m in MODES}
    torch.cuda.reset_peak_memory_stats(device)
    for repetition in range(REPEATS):
     for mode in MODES:
      logits=logits_forced_prefix(model,prompt,shared,mode)
      torch.cuda.synchronize(device)
      item=original.summarize_logits(logits)
      item.update({"repeat":repetition,"total_context_tokens":1584})
      rows[mode].append(item)
     print("G66_PRECISION="+label+" REP="+str(repetition)+" GREEDY="+json.dumps(
       {k:rows[k][-1]["greedy_argmax_id"] for k in MODES},sort_keys=True),flush=True)
    results[label]=rows
    receipt.setdefault("memory",{})[label]={
       "gpu_peak_allocated_mib":torch.cuda.max_memory_allocated(device)/1024**2,
       "gpu_peak_reserved_mib":torch.cuda.max_memory_reserved(device)/1024**2}
    del model
    gc.collect()
    torch.cuda.empty_cache()
  receipt["generation_comparison"]=generation
  receipt["logit_modes"]=results
  receipt["precision_decision"]=categorical(results)
  receipt["precision_decision"]["fp32_generation_parity"]=(
      "FP32_GENERATION_PARITY_PASS" if generation["float32"]["exact_parity"]
      else "FP32_GENERATION_PARITY_FAIL")
  receipt["status"]="PASS_DIAGNOSTIC_MEASUREMENT"
 except Exception as e:
  receipt.update({"status":"FAIL_OR_BLOCKED","error":f"{type(e).__name__}: {e}"})
  raise
 finally:
  RESULT.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n",encoding="utf-8")
  print("G66_STATUS="+receipt["status"],flush=True)
  if "precision_decision" in receipt:print("G66_DECISION="+json.dumps(receipt["precision_decision"],sort_keys=True),flush=True)
if __name__=="__main__":run()
