#!/usr/bin/env python3
"""G96 original GPT-2 development-only execution; never reads held-out ranks."""
import hashlib,json,os,platform,time,traceback
from pathlib import Path
import math,statistics
from g96_original_adapter import _g95,select_cohort,run_policy,assert_parity
from g96_admission import POLICIES,build_traffic,traffic_digest,BYTE_LIMIT

def main():
 import torch,transformers,psutil
 from transformers import AutoTokenizer,AutoModelForCausalLM
 g=_g95()
 if platform.system()!="Linux" or platform.machine().lower() not in ("x86_64","amd64"):
  raise RuntimeError("G96_ORIGINAL_CPU_LINUX_ONLY")
 if torch.__version__!="2.5.1+cpu" or transformers.__version__!="4.48.3" or torch.version.cuda is not None:
  raise RuntimeError("G96_RUNTIME_DRIFT")
 torch.set_num_threads(2);torch.set_num_interop_threads(1)
 proc=psutil.Process();old=None
 receipt={"schema":"forge.cpu-g96.development.v1","gate":"CPU_G96","phase":"DEVELOPMENT_ONLY",
  "head":os.getenv("GITHUB_SHA","UNSET"),"selected_ranks":[276,287],
  "model_revision":g.MODEL_REV,"weights_sha256":g.WEIGHTS_SHA,"data_revision":g.DATA_REV,
  "data_sha256":g.DATA_SHA,"policies":list(POLICIES),"engineering":"UNVERIFIED",
  "correctness":"UNVERIFIED","decision":"DEVELOPMENT_ONLY","promotion_allowed":False,
  "scientific_acceptance":"NOT_GRANTED","heldout_executed":False}
 try:
  raw=Path("cpu_g96_development_gsm8k.jsonl")
  import urllib.request
  req=urllib.request.Request("https://raw.githubusercontent.com/openai/grade-school-math/"+g.DATA_REV+"/grade_school_math/data/test.jsonl",
    headers={"User-Agent":"FORGE-CPU-G96-DEVELOPMENT/1"})
  with urllib.request.urlopen(req,timeout=45) as f:
   data=f.read(800001)
  if len(data)!=g.DATA_BYTES or hashlib.sha256(data).hexdigest()!=g.DATA_SHA:
   raise RuntimeError("G96_DATASET_IDENTITY_DRIFT")
  raw.write_bytes(data)
  records=[{"instruction":x["question"],"category":"math_word_problem"} for x in (json.loads(line) for line in data.decode().splitlines() if line.strip())]
  selected=select_cohort(records,"development")
  receipt["selected_question_hashes"]=[x["instruction_sha256"] for x in selected]
  g55=g.module("g96_g55","llm_g55/g55_gpt2_controls.py")
  if (g55.REV,g55.WEIGHT_SHA)!=(g.MODEL_REV,g.WEIGHTS_SHA):raise RuntimeError("G96_MODEL_IDENTITY_DRIFT")
  root,manifest=g55.stage();receipt["model_manifest_sha256"]=g.sha_file(root/"manifest.json")
  tok=AutoTokenizer.from_pretrained(str(root),local_files_only=True,trust_remote_code=False)
  model=AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,use_safetensors=True,trust_remote_code=False).eval()
  old=proc.cpu_affinity()
  if len(old)<3:raise RuntimeError("G96_THREE_CPUS_REQUIRED")
  proc.cpu_affinity(old[:3]);receipt["affinity"]=proc.cpu_affinity()
  def encode(s):return tok(s,return_tensors="pt",add_special_tokens=False)["input_ids"]
  prefixes=[encode(s) for s in g.PREFIX_TEXTS]
  tokfp=hashlib.sha256("".join(x["sha256"] for x in manifest).encode()).hexdigest()
  # Overflow prefixes use fixed markers, never inferred from held-out.
  prefixes.extend(encode(g.PREFIX_TEXTS[i]+f" [G96_OVERFLOW_{i:02d}]") for i in range(4))
  keys=[g.key_for(p,tokfp) for p in prefixes]
  if len(set(keys))!=8:raise RuntimeError("G96_PREFIX_KEY_COLLISION")
  # Each prefix receives three development questions, deterministic by rank.
  suffixes=[encode(x["instruction"]) for x in selected]
  kvbytes=[]
  with torch.inference_mode():
   for p in prefixes:
    if int(p.shape[1])+max(int(s.shape[1]) for s in suffixes)+g.TOKENS>model.config.n_positions:
     raise RuntimeError("G96_CONTEXT_OVERFLOW")
    kvbytes.append(g.tensor_tree_bytes(model(input_ids=p,use_cache=True).past_key_values))
  receipt["prefix_kv_bytes"]=kvbytes
  # Development-only calibration: independently time four prefix prefills and clones.
  prefill=[];clone=[]
  import copy
  with torch.inference_mode():
   for p in prefixes[:4]:
    t=time.perf_counter_ns();past=model(input_ids=p,use_cache=True).past_key_values
    prefill.append(time.perf_counter_ns()-t)
    t=time.perf_counter_ns();copy.deepcopy(past);clone.append(time.perf_counter_ns()-t)
  calibration={"prefix_prefill_ns":int(sorted(prefill)[len(prefill)//2]),
    "clone_ns":int(sorted(clone)[len(clone)//2]),"expected_reuses":2}
  receipt["calibration"]=calibration
  receipt["thresholds"]=g.THRESHOLDS
  receipt["repetitions"]=4
  receipt["strata"]={}
  for stratum in ("round_robin","bursty","overflow","mixed"):
   layout=build_traffic(stratum,cycles=1)
   stream=[]
   for i,item in enumerate(layout):
    pid=item["prefix_id"];qid=(i//4)%3
    src=selected[(pid%4)+4*qid]
    stream.append({"prefix_id":pid,"source_row":src["source_row"],"suffix":suffixes[(pid%4)+4*qid],
      "prefix_kv_bytes":kvbytes[pid]})
   references={}
   with torch.inference_mode():
    for i,req in enumerate(stream):
     full=torch.cat((prefixes[req["prefix_id"]],req["suffix"]),dim=1)
     references[i],_=g.baseline_request(model,full,g.TOKENS,torch,proc)
   repetitions=[]
   for rep in range(4):
    arms={}
    order=POLICIES if rep%2==0 else tuple(reversed(POLICIES))
    for policy in order:
     out,metrics=run_policy(model,stream,prefixes,keys,policy,torch,proc,
       calibration=calibration if policy=="cost_aware" else None)
     assert_parity(references,out)
     arms[policy]=metrics
    repetitions.append({"rep":rep+1,"order":list(order),"arms":arms})
   baseline=[r["arms"]["no_cache"] for r in repetitions]
   verdict={}
   for policy in POLICIES[1:]:
    candidate=[r["arms"][policy] for r in repetitions]
    bt=[x["request_wall_ns"] for r in baseline for x in r["rows"]]
    ct=[x["request_wall_ns"] for r in candidate for x in r["rows"]]
    if len(bt)!=192 or len(ct)!=192:raise RuntimeError("G96_INCOMPLETE_PAIRED_REPETITIONS")
    bps=statistics.median(48*g.TOKENS/(r["wall_ns"]/1e9) for r in baseline)
    cps=statistics.median(48*g.TOKENS/(r["wall_ns"]/1e9) for r in candidate)
    p95=lambda x:sorted(x)[math.ceil(.95*len(x))-1]
    m={"throughput_speedup":cps/bps,
       "minimum_paired_request_speedup":min(b/c for b,c in zip(bt,ct)),
       "p95_latency_ratio":p95(ct)/p95(bt),
       "cpu_ratio":sum(r["cpu_ns"] for r in candidate)/sum(r["cpu_ns"] for r in baseline),
       "rss_ratio":max(r["max_rss"] for r in candidate)/max(r["max_rss"] for r in baseline),
       "max_resident_kv_bytes":max(r["max_resident_kv_bytes"] for r in candidate),
       "hits":sum(r["hits"] for r in candidate),"misses":sum(r["misses"] for r in candidate)}
    m["qualifies"]=(m["throughput_speedup"]>=g.THRESHOLDS["throughput_min"]
      and m["minimum_paired_request_speedup"]>=g.THRESHOLDS["min_paired"]
      and m["p95_latency_ratio"]<=g.THRESHOLDS["p95_max"]
      and m["cpu_ratio"]<=g.THRESHOLDS["cpu_max"]
      and m["rss_ratio"]<=g.THRESHOLDS["rss_max"]
      and m["max_resident_kv_bytes"]<=BYTE_LIMIT)
    verdict[policy]=m
   receipt["strata"][stratum]={"traffic_sha256":traffic_digest(layout),"requests_per_rep":len(stream),
     "repetitions":repetitions,"exact_parity":True,"metrics":verdict}
  receipt["development_qualifying_policies"]=[p for p in POLICIES[1:] if all(
    receipt["strata"][s]["metrics"][p]["qualifies"] for s in receipt["strata"])]
  receipt["decision"]="DEVELOPMENT_CANDIDATE" if receipt["development_qualifying_policies"] else "DEVELOPMENT_NO_GO"
  receipt["engineering"]="PASS";receipt["correctness"]="PASS"
 except BaseException as e:
  receipt["error"]=type(e).__name__+": "+str(e);receipt["traceback_tail"]=traceback.format_exc()[-3000:]
  raise
 finally:
  if old is not None:proc.cpu_affinity(old)
  Path("cpu_g96_development_result.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")

if __name__=="__main__":main()
