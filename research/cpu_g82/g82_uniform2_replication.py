#!/usr/bin/env python3
"""CPU G82: original GPT2 phase-adaptive thread budget; no model modifications."""
import hashlib,importlib.util,json,math,os,platform,statistics,time,traceback,urllib.request
from pathlib import Path

PREREG="b64790aea774e35c79a0c6db539c7ad48b305b52"
MODEL_REV="607a30d783dfa663caf39e06633721c8d4cfcd7e"
WEIGHTS_SHA="248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
DATA_REV="3101c7d5072418e28b9008a6636bde82a006892c"
DATA_SHA="3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14"
DATA_BYTES=749738
SEED=b"G68-GPT2-HELDOUT-20261030:"
OFFSET=144;CASES=12;REPEATS=5;TOKENS=8;CPU_BUDGET=3
ARMS={"uniform1":(1,1),"uniform3":(3,3),"uniform2":(2,2)}
BASELINES=("uniform1","uniform3")
THRESHOLDS={"speedup_vs_uniform1_min":1.35,"speedup_vs_uniform3_min":1.05,"min_paired_vs_uniform3":0.90,
            "p95_ratio_vs_uniform3_max":1.10,"rss_ratio_vs_uniform3_max":1.10,"cpu_ratio_vs_uniform3_max":1.25}
def contract():
    assert (OFFSET,CASES,REPEATS,TOKENS,CPU_BUDGET)==(144,12,5,8,3)
    assert ARMS=={"uniform1":(1,1),"uniform3":(3,3),"uniform2":(2,2)}
    assert THRESHOLDS=={"speedup_vs_uniform1_min":1.35,"speedup_vs_uniform3_min":1.05,"min_paired_vs_uniform3":0.90,
                      "p95_ratio_vs_uniform3_max":1.10,"rss_ratio_vs_uniform3_max":1.10,"cpu_ratio_vs_uniform3_max":1.25}

def sha_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()

def module(name,rel):
    p=Path(__file__).resolve().parents[1]/rel
    s=importlib.util.spec_from_file_location(name,p)
    x=importlib.util.module_from_spec(s);s.loader.exec_module(x)
    return x

def rank_original(records,n):
    candidate=[]
    for row,item in enumerate(records):
        q=item.get("instruction","")
        cat=item.get("category","")
        if isinstance(q,str) and q.strip() and isinstance(cat,str) and cat.strip():
            candidate.append((hashlib.sha256(SEED+q.encode()).hexdigest(),row,q,cat))
    candidate.sort(key=lambda t:(t[0],t[1]))
    chosen=[];seen=set()
    for digest,row,q,cat in candidate:
        if q in seen:continue
        seen.add(q)
        chosen.append({"source_row":row,"instruction":q,"category":cat,
             "instruction_sha256":hashlib.sha256(q.encode()).hexdigest(),"rank_sha256":digest})
        if len(chosen)==n:break
    if len(chosen)!=n:raise RuntimeError("G82_INSUFFICIENT_ORIGINAL_HELDOUT")
    return chosen

def schedule(sample,rep):
    names=tuple(ARMS)
    shift=(sample+rep)%len(names)
    order=list(names[shift:]+names[:shift])
    if rep%2:order.reverse()
    return tuple(order)

def p95(vals):
    return sorted(vals)[max(0,math.ceil(0.95*len(vals))-1)]

def decide(trials):
    if len(trials)!=CASES*REPEATS:raise RuntimeError("G82_INCOMPLETE_ORIGINAL_PAIRED_TRIALS")
    for t in trials:
        if set(t["measure"])!=set(ARMS) or len(t["order"])!=len(ARMS):
            raise RuntimeError("G82_MISSING_STRONG_CONTROL")
        if len({t["measure"][a]["output_sha256"] for a in ARMS})!=1:
            raise RuntimeError("G82_ORIGINAL_TOKEN_PARITY_ERROR")
        for a in ARMS:
            x=t["measure"][a]
            if x["wall_ns"]<=0 or x["process_cpu_ns"]<=0 or x["rss_sampled"]<=0:
                raise RuntimeError("G82_INVALID_CPU_WALL_OR_RSS_TIMING")
            if x["prefill_ns"]<=0 or x["cached_decode_ns"]<=0 or x["prefill_ns"]+x["cached_decode_ns"]>x["wall_ns"]:
                raise RuntimeError("G82_INVALID_PHASE_ACCOUNTING")
    arms={}
    for a in ARMS:
        w=[t["measure"][a]["wall_ns"] for t in trials]
        arms[a]={"median_wall_ns":statistics.median(w),"p95_wall_ns":p95(w),
          "total_process_cpu_ns":sum(t["measure"][a]["process_cpu_ns"] for t in trials),
          "max_sampled_rss_bytes":max(t["measure"][a]["rss_sampled"] for t in trials)}
    c=arms["uniform2"];one=arms["uniform1"];three=arms["uniform3"]
    p=[t["measure"]["uniform3"]["wall_ns"]/t["measure"]["uniform2"]["wall_ns"] for t in trials]
    summary={"median_speedup_vs_uniform1":one["median_wall_ns"]/c["median_wall_ns"],
      "median_speedup_vs_uniform3":three["median_wall_ns"]/c["median_wall_ns"],
      "minimum_individual_paired_speedup_vs_uniform3":min(p),
      "p95_candidate_over_uniform3_ratio":c["p95_wall_ns"]/three["p95_wall_ns"],
      "sampled_rss_candidate_over_uniform3_ratio":c["max_sampled_rss_bytes"]/three["max_sampled_rss_bytes"],
      "total_cpu_candidate_over_uniform3_ratio":c["total_process_cpu_ns"]/three["total_process_cpu_ns"],
      "timed_authentic_responses":len(trials)*len(ARMS),
      "timed_authentic_generated_tokens":len(trials)*len(ARMS)*TOKENS}
    ok=summary["median_speedup_vs_uniform1"]>=THRESHOLDS["speedup_vs_uniform1_min"] and summary["median_speedup_vs_uniform3"]>=THRESHOLDS["speedup_vs_uniform3_min"] and summary["minimum_individual_paired_speedup_vs_uniform3"]>=THRESHOLDS["min_paired_vs_uniform3"] and summary["p95_candidate_over_uniform3_ratio"]<=THRESHOLDS["p95_ratio_vs_uniform3_max"] and summary["sampled_rss_candidate_over_uniform3_ratio"]<=THRESHOLDS["rss_ratio_vs_uniform3_max"] and summary["total_cpu_candidate_over_uniform3_ratio"]<=THRESHOLDS["cpu_ratio_vs_uniform3_max"]
    return arms,summary,"REPLICATION_PASS" if ok else "REPLICATION_FAIL"

def main():
    import psutil,torch,transformers
    from transformers import AutoTokenizer,AutoModelForCausalLM
    contract()
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    proc=psutil.Process();old_aff=None
    receipt={"schema":"forge.cpu-llm-g82.authentic-uniform2-replication.v1",
      "gate":"CPU_G82","preregistration_commit":PREREG,"source_sha":os.getenv("GITHUB_SHA","UNSET"),
      "model_revision":MODEL_REV,"model_weights_sha256":WEIGHTS_SHA,
      "dataset_revision":DATA_REV,"dataset_sha256":DATA_SHA,
      "runtime":{"torch":torch.__version__,"transformers":transformers.__version__,
                 "python":platform.python_version(),"machine":platform.machine(),"platform":platform.platform()},
      "engineering":"UNVERIFIED","correctness":"UNVERIFIED","replication":"UNVERIFIED",
      "scientific_acceptance":"NOT_GRANTED","promotion_allowed":False,
      "limitations":["Original pretrained GPT2 full 8-token FP32 requests; not natural network traffic",
                     "Three logical CPUs shared by all arms; PyTorch intraop thread change charged inside every request",
                     "No GPU or model weights changed, no universal token output proof beyond observed original samples",
                     "Original MIT GSM8K family with new disjoint heldout ranks",
                     "RSS sampled, not true physical peak; process CPU time measured but no energy metric",
                     "No FORGE native model, autonomy/controller or GPU ACC acceptance"]}
    try:
        raw=Path("cpu_g82_original_gsm8k.jsonl")
        req=urllib.request.Request(
          "https://raw.githubusercontent.com/openai/grade-school-math/"+DATA_REV+"/grade_school_math/data/test.jsonl",
          headers={"User-Agent":"FORGE-CPU-G82-Phase-Thread-Budget/1"})
        with urllib.request.urlopen(req,timeout=45) as inp,raw.open("xb") as out:
            total=0
            while True:
                part=inp.read(1<<20)
                if not part:break
                total+=len(part)
                if total>800000:raise RuntimeError("G82_ORIGINAL_DATA_SIZE_CAP")
                out.write(part)
        if raw.stat().st_size!=DATA_BYTES or sha_file(raw)!=DATA_SHA:
            raise RuntimeError("G82_ORIGINAL_GSM8K_DATA_IDENTITY_DRIFT")
        with raw.open(encoding="utf-8") as f:
            records=[{"instruction":x["question"],"category":"math_word_problem"}
                     for x in (json.loads(line) for line in f if line.strip())]
        ranked=rank_original(records,OFFSET+CASES)
        g68=module("g82_g68","llm_g68/g68_gsm8k_http.py")
        g70=module("g82_g70","llm_g70/g70_gsm8k_locality.py")
        if ranked[:12]!=g68.select_heldout(records) or ranked[12:24]!=g70.select_heldout(records):
            raise RuntimeError("G82_ORIGINAL_RANK_CONTRACT_DRIFT")
        if len({x["source_row"] for x in ranked})!=OFFSET+CASES:
            raise RuntimeError("G82_DUPLICATED_ORIGINAL_RANKS")
        selected=ranked[OFFSET:OFFSET+CASES]
        receipt["selected"]=[{k:v for k,v in r.items() if k!="instruction"} for r in selected]
        receipt["selected_ranks"]=[OFFSET,OFFSET+CASES-1]
        g55=module("g82_g55","llm_g55/g55_gpt2_controls.py")
        if (g55.REV,g55.WEIGHT_SHA)!=(MODEL_REV,WEIGHTS_SHA):
            raise RuntimeError("G82_G55_MODEL_IDENTITY_DRIFT")
        t0=time.perf_counter();root,manifest=g55.stage()
        receipt["model_staging_wall_s"]=time.perf_counter()-t0
        receipt["model_manifest_sha256"]=sha_file(root/"manifest.json")
        receipt["model_files"]=manifest
        tokenizer=AutoTokenizer.from_pretrained(str(root),local_files_only=True,trust_remote_code=False)
        model=AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,
               use_safetensors=True,trust_remote_code=False).eval()
        if model.config.model_type!="gpt2" or next(model.parameters()).dtype!=torch.float32:
            raise RuntimeError("G82_PRETRAINED_FP32_MODEL_DRIFT")
        if not hasattr(proc,"cpu_affinity"):raise RuntimeError("G82_CPU_AFFINITY_UNAVAILABLE")
        old_aff=proc.cpu_affinity()
        if len(old_aff)<CPU_BUDGET:raise RuntimeError("G82_THREE_CPU_AFFINITY_UNAVAILABLE")
        proc.cpu_affinity(old_aff[:CPU_BUDGET])
        receipt["fixed_affinity"]=proc.cpu_affinity()
        receipt["fixed_torch_interop"]=torch.get_num_interop_threads()
        def ids(s):return tokenizer(s,return_tensors="pt",add_special_tokens=False)["input_ids"]
        def full_decode(full,arm):
            pre,dec=ARMS[arm]
            cpu0=time.process_time_ns();wall0=time.perf_counter_ns()
            p0=time.perf_counter_ns()
            torch.set_num_threads(pre)
            with torch.inference_mode():
                out=model(input_ids=full,use_cache=True)
                past,logits=out.past_key_values,out.logits[:,-1,:]
            pre_ns=time.perf_counter_ns()-p0
            d0=time.perf_counter_ns()
            if dec!=pre:
                torch.set_num_threads(dec)
            chosen=[]
            with torch.inference_mode():
                for step in range(TOKENS):
                    token=logits.argmax(-1,keepdim=True)
                    chosen.append(token)
                    if step+1<TOKENS:
                        mask=torch.ones((1,int(full.shape[1])+step+1),dtype=torch.long)
                        out=model(input_ids=token,past_key_values=past,
                            attention_mask=mask,use_cache=True)
                        past,logits=out.past_key_values,out.logits[:,-1,:]
                result=torch.cat(chosen,dim=1).flatten().tolist()
            dec_ns=time.perf_counter_ns()-d0
            wall_ns=time.perf_counter_ns()-wall0
            cpu_ns=time.process_time_ns()-cpu0
            if len(result)!=TOKENS or int(torch.get_num_threads())!=dec:
                raise RuntimeError("G82_TOKEN_COUNT_OR_THREAD_DRIFT")
            return result,{"wall_ns":wall_ns,"process_cpu_ns":cpu_ns,
                     "prefill_ns":pre_ns,"cached_decode_ns":dec_ns,
                     "rss_sampled":proc.memory_info().rss,
                     "output_sha256":hashlib.sha256(json.dumps(result,separators=(",",":")).encode()).hexdigest()}
        public=ids("A public nonheldout example for exact original CPU decoding.")
        for _ in range(3):
            ref,_=full_decode(public,"uniform1")
            for arm in ARMS:
                got,_=full_decode(public,arm)
                if got!=ref:raise RuntimeError("G82_PUBLIC_GREEDY_TOKEN_MISMATCH_"+arm)
        inputs=[]
        for original in selected:
            full=torch.cat((ids(g55.PREFIX),ids(original["instruction"])[:,:64]),dim=1)
            if full.shape[1]+TOKENS>model.config.n_positions:
                raise RuntimeError("G82_ORIGINAL_CONTEXT_OVERFLOW")
            inputs.append((original["source_row"],full))
        measured=[]
        for i,(row,full) in enumerate(inputs):
            reference,_=full_decode(full,"uniform1")
            for rep in range(REPEATS):
                order=schedule(i,rep)
                measures={}
                for arm in order:
                    result,timing=full_decode(full,arm)
                    if result!=reference:raise RuntimeError("G82_EXACT_ORIGINAL_TOKEN_MISMATCH_"+arm+"_"+str(i))
                    measures[arm]=timing
                measured.append({"sample_index":i,"source_row":row,"rep":rep+1,
                    "order":order,"original_input_token_count":int(full.shape[1]),
                    "original_input_sha256":hashlib.sha256(full.numpy().tobytes()).hexdigest(),
                    "measure":measures})
        arms,summary,decision=decide(measured)
        receipt["original_paired_trials"]=measured
        receipt["arm_summaries"]=arms
        receipt["summary"]=summary
        receipt["engineering"]="PASS"
        receipt["correctness"]="PASS"
        receipt["replication"]=decision
    except BaseException as exc:
        receipt["error"]=type(exc).__name__+": "+str(exc)
        receipt["traceback_tail"]=traceback.format_exc()[-2500:]
        raise
    finally:
        if old_aff is not None:
            receipt["cpu_affinity_at_end"]=proc.cpu_affinity()
            proc.cpu_affinity(old_aff)
        Path("cpu_g82_original_result.json").write_text(
            json.dumps(receipt,sort_keys=True,indent=2,default=str)+"\n",encoding="utf-8")
        print(json.dumps({k:receipt.get(k) for k in
            ("gate","engineering","correctness","replication","summary","error")},sort_keys=True),flush=True)

if __name__=="__main__":main()
