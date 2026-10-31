#!/usr/bin/env python3
"""CPU G85: original GPT2 phase-adaptive thread budget; no model modifications."""
import hashlib,importlib.util,json,math,os,platform,statistics,time,traceback,urllib.request
from pathlib import Path

PREREG="275284b5c2fffd8031fe2caaa570793e3fe6941a"
MODEL_REV="607a30d783dfa663caf39e06633721c8d4cfcd7e"
WEIGHTS_SHA="248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
DATA_REV="370cbcd448eb7daf32f21a6be560b70e0b33c4e3"
DATA_SHA="86c4e6aa9db7c042ec79f339dcb96d42b0075e16b8fc2e86bf0ca57e2dc565ed"
DATA_BYTES=1115394
CASES=12;REPEATS=5;TOKENS=8;CPU_BUDGET=3
PROMPT_TOKENS=96;SPAN_CHARS=2048;STRIDE_CHARS=3072;TAIL_FRACTION=0.90
ARMS={"uniform1":(1,1),"uniform3":(3,3),"uniform2":(2,2)}
BASELINES=("uniform1","uniform3")
THRESHOLDS={"speedup_vs_uniform1_min":1.35,"speedup_vs_uniform3_min":1.05,"min_paired_vs_uniform3":0.90,
            "p95_ratio_vs_uniform3_max":1.10,"rss_ratio_vs_uniform3_max":1.10,"cpu_ratio_vs_uniform3_max":1.25}
def contract():
    assert (CASES,REPEATS,TOKENS,CPU_BUDGET,PROMPT_TOKENS,SPAN_CHARS,STRIDE_CHARS)==(12,5,8,3,96,2048,3072)
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

def select_original_spans(text):
    if not isinstance(text,str) or not text:raise RuntimeError("G85_EMPTY_AUTHENTIC_SOURCE_TEXT")
    tail_start=int(len(text)*TAIL_FRACTION)
    tail=text[tail_start:]
    chosen=[]
    for i in range(CASES):
        offset=i*STRIDE_CHARS
        span=tail[offset:offset+SPAN_CHARS]
        if len(span)!=SPAN_CHARS:raise RuntimeError("G85_INSUFFICIENT_ORIGINAL_TAIL")
        chosen.append({"source_row":tail_start+offset,"source_offset":offset,
            "original_span_sha256":hashlib.sha256(span.encode("utf-8")).hexdigest(),
            "segment":span})
    if any(b["source_offset"]-a["source_offset"]<SPAN_CHARS
           for a,b in zip(chosen,chosen[1:])):
        raise RuntimeError("G85_OVERLAPPING_SOURCE_SPANS")
    if len({x["original_span_sha256"] for x in chosen})!=CASES:
        raise RuntimeError("G85_DUPLICATED_SOURCE_SPANS")
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
    if len(trials)!=CASES*REPEATS:raise RuntimeError("G85_INCOMPLETE_ORIGINAL_PAIRED_TRIALS")
    for t in trials:
        if set(t["measure"])!=set(ARMS) or len(t["order"])!=len(ARMS):
            raise RuntimeError("G85_MISSING_STRONG_CONTROL")
        if len({t["measure"][a]["output_sha256"] for a in ARMS})!=1:
            raise RuntimeError("G85_ORIGINAL_TOKEN_PARITY_ERROR")
        for a in ARMS:
            x=t["measure"][a]
            if x["wall_ns"]<=0 or x["process_cpu_ns"]<=0 or x["rss_sampled"]<=0:
                raise RuntimeError("G85_INVALID_CPU_WALL_OR_RSS_TIMING")
            if x["prefill_ns"]<=0 or x["cached_decode_ns"]<=0 or x["prefill_ns"]+x["cached_decode_ns"]>x["wall_ns"]:
                raise RuntimeError("G85_INVALID_PHASE_ACCOUNTING")
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
    receipt={"schema":"forge.cpu-llm-g85.authentic-shakespeare-transfer.v1",
      "gate":"CPU_G85","preregistration_commit":PREREG,"source_sha":os.getenv("GITHUB_SHA","UNSET"),
      "model_revision":MODEL_REV,"model_weights_sha256":WEIGHTS_SHA,
      "dataset_revision":DATA_REV,"dataset_sha256":DATA_SHA,
      "runtime":{"torch":torch.__version__,"torch_cuda":torch.version.cuda,"transformers":transformers.__version__,
                 "python":platform.python_version(),"machine":platform.machine(),"processor":platform.processor(),"logical_cpu_count":os.cpu_count(),"platform":platform.platform()},
      "engineering":"UNVERIFIED","correctness":"UNVERIFIED","transfer":"UNVERIFIED",
      "scientific_acceptance":"NOT_GRANTED","promotion_allowed":False,
      "limitations":["Original pretrained GPT2 full 8-token FP32 requests; not natural network traffic",
                     "Exactly three native ARM64 logical CPUs shared by all arms; PyTorch intraop thread change charged inside every request",
                     "No GPU or model weights changed, no universal token output proof beyond observed original samples",
                     "Pinned dramatic Shakespeare corpus; not provably unseen to GPT2 training",
                     "RSS sampled, not true physical peak; process CPU time measured but no energy metric",
                     "No FORGE native model, autonomy/controller or GPU ACC acceptance"]}
    try:
        if os.name!="posix" or platform.system()!="Linux":raise RuntimeError("G85_LINUX_ONLY")
        if platform.machine().lower() not in ("aarch64","arm64"):raise RuntimeError("G85_NOT_NATIVE_ARM64")
        if torch.version.cuda is not None:raise RuntimeError("G85_NON_CPU_PYTORCH_BUILD")
        raw=Path("cpu_g85_arm64_tinyshakespeare.txt")
        req=urllib.request.Request("https://raw.githubusercontent.com/karpathy/char-rnn/"+
             DATA_REV+"/data/tinyshakespeare/input.txt",
             headers={"User-Agent":"FORGE-CPU-G85-ARM64-Shakespeare-Transfer/1"})
        with urllib.request.urlopen(req,timeout=60) as inp,raw.open("xb") as out:
            total=0
            while True:
                part=inp.read(1<<20)
                if not part:break
                total+=len(part)
                if total>DATA_BYTES+1024:raise RuntimeError("G85_SOURCE_SIZE_CAP")
                out.write(part)
        if raw.stat().st_size!=DATA_BYTES or sha_file(raw)!=DATA_SHA:
            raise RuntimeError("G85_ORIGINAL_SHAKESPEARE_SHA_MISMATCH")
        original_text=raw.read_text(encoding="utf-8")
        selected=select_original_spans(original_text)
        receipt["selected"]=[{k:v for k,v in row.items() if k!="segment"} for row in selected]
        receipt["source_family"]="original TinyShakespeare dramatic English"
        receipt["source_tail_start_codepoint"]=int(len(original_text)*TAIL_FRACTION)
        g55=module("g85_g55","llm_g55/g55_gpt2_controls.py")
        if (g55.REV,g55.WEIGHT_SHA)!=(MODEL_REV,WEIGHTS_SHA):
            raise RuntimeError("G85_G55_MODEL_IDENTITY_DRIFT")
        t0=time.perf_counter();root,manifest=g55.stage()
        receipt["model_staging_wall_s"]=time.perf_counter()-t0
        receipt["model_manifest_sha256"]=sha_file(root/"manifest.json")
        receipt["model_files"]=manifest
        tokenizer=AutoTokenizer.from_pretrained(str(root),local_files_only=True,trust_remote_code=False)
        model=AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,
               use_safetensors=True,trust_remote_code=False).eval()
        if model.config.model_type!="gpt2" or next(model.parameters()).dtype!=torch.float32:
            raise RuntimeError("G85_PRETRAINED_FP32_MODEL_DRIFT")
        if not hasattr(proc,"cpu_affinity"):raise RuntimeError("G85_CPU_AFFINITY_UNAVAILABLE")
        old_aff=proc.cpu_affinity()
        if len(old_aff)<CPU_BUDGET:raise RuntimeError("G85_THREE_CPU_AFFINITY_UNAVAILABLE")
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
                raise RuntimeError("G85_TOKEN_COUNT_OR_THREAD_DRIFT")
            return result,{"wall_ns":wall_ns,"process_cpu_ns":cpu_ns,
                     "prefill_ns":pre_ns,"cached_decode_ns":dec_ns,
                     "rss_sampled":proc.memory_info().rss,
                     "output_sha256":hashlib.sha256(json.dumps(result,separators=(",",":")).encode()).hexdigest()}
        public=ids("A public nonheldout example for exact original CPU decoding.")
        for _ in range(3):
            ref,_=full_decode(public,"uniform1")
            for arm in ARMS:
                got,_=full_decode(public,arm)
                if got!=ref:raise RuntimeError("G85_PUBLIC_GREEDY_TOKEN_MISMATCH_"+arm)
        inputs=[]
        for original in selected:
            encoded=ids(original["segment"])
            if encoded.shape[1]<PROMPT_TOKENS:raise RuntimeError("G85_TOO_FEW_ORIGINAL_PROMPT_TOKENS")
            full=encoded[:,:PROMPT_TOKENS]
            if full.shape[1]!=PROMPT_TOKENS or full.shape[1]+TOKENS>model.config.n_positions:
                raise RuntimeError("G85_ORIGINAL_CONTEXT_OVERFLOW")
            inputs.append((original["source_row"],full))
        measured=[]
        for i,(row,full) in enumerate(inputs):
            reference,_=full_decode(full,"uniform1")
            for rep in range(REPEATS):
                order=schedule(i,rep)
                measures={}
                for arm in order:
                    result,timing=full_decode(full,arm)
                    if result!=reference:raise RuntimeError("G85_EXACT_ORIGINAL_TOKEN_MISMATCH_"+arm+"_"+str(i))
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
        receipt["transfer"]="TRANSFER_PASS" if decision=="REPLICATION_PASS" else "TRANSFER_FAIL"
    except BaseException as exc:
        receipt["error"]=type(exc).__name__+": "+str(exc)
        receipt["traceback_tail"]=traceback.format_exc()[-2500:]
        raise
    finally:
        if old_aff is not None:
            receipt["cpu_affinity_at_end"]=proc.cpu_affinity()
            proc.cpu_affinity(old_aff)
        Path("cpu_g85_arm64_result.json").write_text(
            json.dumps(receipt,sort_keys=True,indent=2,default=str)+"\n",encoding="utf-8")
        print(json.dumps({k:receipt.get(k) for k in
            ("gate","engineering","correctness","transfer","summary","error")},sort_keys=True),flush=True)

if __name__=="__main__":main()
