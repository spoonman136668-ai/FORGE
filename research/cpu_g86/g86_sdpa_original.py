#!/usr/bin/env python3
"""CPU G86: unchanged original GPT2 weights, eager versus real SDPA backend."""
import hashlib,importlib.util,json,math,os,platform,statistics,time,traceback,urllib.request
from pathlib import Path

PREREG="30b5e1b7cd6e2df40e2923312120dc5808bb1602"
MODEL_REV="607a30d783dfa663caf39e06633721c8d4cfcd7e"
WEIGHTS_SHA="248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
DATA_REV="3101c7d5072418e28b9008a6636bde82a006892c"
DATA_SHA="3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14"
DATA_BYTES=749738
SEED=b"G68-GPT2-HELDOUT-20261030:"
OFFSET=156;CASES=12;REPEATS=4;TOKENS=8;CPU_BUDGET=3
ARMS=("eager1","eager2","eager3","sdpa1","sdpa2","sdpa3")
ARM_SPEC={"eager1":("eager",1),"eager2":("eager",2),"eager3":("eager",3),"sdpa1":("sdpa",1),"sdpa2":("sdpa",2),"sdpa3":("sdpa",3)}
THRESHOLDS={"speedup_min":1.15,"min_paired":0.90,"p95_max":1.10,"rss_max":1.10,"cpu_max":1.25}
def contract():
    assert (OFFSET,CASES,REPEATS,TOKENS,CPU_BUDGET)==(156,12,4,8,3)
    assert ARMS==("eager1","eager2","eager3","sdpa1","sdpa2","sdpa3")
    assert THRESHOLDS=={"speedup_min":1.15,"min_paired":0.90,"p95_max":1.10,"rss_max":1.10,"cpu_max":1.25}

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
    if len(chosen)!=n:raise RuntimeError("G86_INSUFFICIENT_ORIGINAL_HELDOUT")
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
    if len(trials)!=CASES*REPEATS:raise RuntimeError("G86_INCOMPLETE_ORIGINAL_PAIRED_TRIALS")
    for t in trials:
        if set(t["measure"])!=set(ARMS) or len(t["order"])!=len(ARMS):
            raise RuntimeError("G86_MISSING_BACKEND_OR_THREAD_CONTROL")
        if len({t["measure"][a]["output_sha256"] for a in ARMS})!=1:
            raise RuntimeError("G86_ORIGINAL_TOKEN_PARITY_ERROR")
        for a in ARMS:
            x=t["measure"][a]
            if x["wall_ns"]<=0 or x["process_cpu_ns"]<=0 or x["rss_sampled"]<=0:
                raise RuntimeError("G86_INVALID_CPU_WALL_OR_RSS_TIMING")
            if x["backend_dispatch_calls"]<=0:
                raise RuntimeError("G86_BACKEND_NOT_DISPATCHED_"+a)
            if a.startswith("eager") and x["sdpa_dispatch_calls"]!=0:
                raise RuntimeError("G86_EAGER_SDPA_FALLBACK_"+a)
            if a.startswith("sdpa") and x["sdpa_dispatch_calls"]<=0:
                raise RuntimeError("G86_SDPA_NOT_ACTUALLY_CALLED_"+a)
    arms={}
    for a in ARMS:
        w=[t["measure"][a]["wall_ns"] for t in trials]
        arms[a]={"median_wall_ns":statistics.median(w),"p95_wall_ns":p95(w),
          "total_process_cpu_ns":sum(t["measure"][a]["process_cpu_ns"] for t in trials),
          "max_sampled_rss_bytes":max(t["measure"][a]["rss_sampled"] for t in trials)}
    c=arms["sdpa2"];e=arms["eager2"]
    paired=[t["measure"]["eager2"]["wall_ns"]/t["measure"]["sdpa2"]["wall_ns"] for t in trials]
    summary={
      "primary_median_speedup_sdpa2_vs_eager2":e["median_wall_ns"]/c["median_wall_ns"],
      "minimum_individual_paired_speedup_eager2_vs_sdpa2":min(paired),
      "p95_sdpa2_over_eager2_ratio":c["p95_wall_ns"]/e["p95_wall_ns"],
      "sampled_rss_sdpa2_over_eager2_ratio":c["max_sampled_rss_bytes"]/e["max_sampled_rss_bytes"],
      "total_cpu_sdpa2_over_eager2_ratio":c["total_process_cpu_ns"]/e["total_process_cpu_ns"],
      "timed_authentic_responses":len(trials)*len(ARMS),
      "timed_authentic_generated_tokens":len(trials)*len(ARMS)*TOKENS
    }
    ok=(summary["primary_median_speedup_sdpa2_vs_eager2"]>=THRESHOLDS["speedup_min"]
      and summary["minimum_individual_paired_speedup_eager2_vs_sdpa2"]>=THRESHOLDS["min_paired"]
      and summary["p95_sdpa2_over_eager2_ratio"]<=THRESHOLDS["p95_max"]
      and summary["sampled_rss_sdpa2_over_eager2_ratio"]<=THRESHOLDS["rss_max"]
      and summary["total_cpu_sdpa2_over_eager2_ratio"]<=THRESHOLDS["cpu_max"])
    return arms,summary,"SDPA_PASS" if ok else "SDPA_NO_GO"


def main():
    import psutil,torch,transformers
    from transformers import AutoTokenizer,AutoModelForCausalLM
    contract()
    if os.name!="posix" or platform.system()!="Linux" or platform.machine().lower() not in ("x86_64","amd64"):
        raise RuntimeError("G86_NOT_NATIVE_X86_64_LINUX")
    if torch.version.cuda is not None:raise RuntimeError("G86_NON_CPU_PYTORCH_BUILD")
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    proc=psutil.Process();old_aff=None
    receipt={"schema":"forge.cpu-llm-g86.authentic-sdpa-attention.v1",
      "gate":"CPU_G86","preregistration_commit":PREREG,"source_sha":os.getenv("GITHUB_SHA","UNSET"),
      "model_revision":MODEL_REV,"model_weights_sha256":WEIGHTS_SHA,
      "dataset_revision":DATA_REV,"dataset_sha256":DATA_SHA,
      "runtime":{"torch":torch.__version__,"torch_cuda":torch.version.cuda,"transformers":transformers.__version__,
                 "python":platform.python_version(),"machine":platform.machine(),"processor":platform.processor(),
                 "logical_cpu_count":os.cpu_count(),"os_name":os.name,"platform":platform.platform()},
      "engineering":"UNVERIFIED","correctness":"UNVERIFIED","decision":"UNVERIFIED",
      "scientific_acceptance":"NOT_GRANTED","promotion_allowed":False,
      "limitations":["Original GPT2 FP32 8-token decoding only; not production network traffic",
        "SDPA backend changes operation ordering and may have hardware-dependent numeric behavior",
        "Three CPU logical cores fixed across both attention implementations and thread arms",
        "RSS sampled, not physical peak; no energy metric",
        "GSM8K evaluation prompts may be familiar to model pretraining",
        "No GPU, native Wingless/Yggdrasil or scientific/model acceptance"]}
    try:
        raw=Path("cpu_g86_original_gsm8k.jsonl")
        req=urllib.request.Request(
          "https://raw.githubusercontent.com/openai/grade-school-math/"+DATA_REV+"/grade_school_math/data/test.jsonl",
          headers={"User-Agent":"FORGE-CPU-G86-SDPA-Attention/1"})
        with urllib.request.urlopen(req,timeout=45) as inp,raw.open("xb") as out:
            total=0
            while True:
                part=inp.read(1<<20)
                if not part:break
                total+=len(part)
                if total>800000:raise RuntimeError("G86_ORIGINAL_DATA_SIZE_CAP")
                out.write(part)
        if raw.stat().st_size!=DATA_BYTES or sha_file(raw)!=DATA_SHA:
            raise RuntimeError("G86_ORIGINAL_GSM8K_DATA_IDENTITY_DRIFT")
        with raw.open(encoding="utf-8") as f:
            records=[{"instruction":x["question"],"category":"math_word_problem"}
                     for x in (json.loads(line) for line in f if line.strip())]
        ranked=rank_original(records,OFFSET+CASES)
        g68=module("g86_g68","llm_g68/g68_gsm8k_http.py")
        g70=module("g86_g70","llm_g70/g70_gsm8k_locality.py")
        if ranked[:12]!=g68.select_heldout(records) or ranked[12:24]!=g70.select_heldout(records):
            raise RuntimeError("G86_ORIGINAL_RANK_CONTRACT_DRIFT")
        if len({x["source_row"] for x in ranked})!=OFFSET+CASES:
            raise RuntimeError("G86_DUPLICATED_ORIGINAL_RANKS")
        selected=ranked[OFFSET:OFFSET+CASES]
        receipt["selected"]=[{k:v for k,v in r.items() if k!="instruction"} for r in selected]
        receipt["selected_ranks"]=[OFFSET,OFFSET+CASES-1]
        g55=module("g86_g55","llm_g55/g55_gpt2_controls.py")
        if (g55.REV,g55.WEIGHT_SHA)!=(MODEL_REV,WEIGHTS_SHA):
            raise RuntimeError("G86_G55_MODEL_IDENTITY_DRIFT")
        t0=time.perf_counter();root,manifest=g55.stage()
        receipt["model_staging_wall_s"]=time.perf_counter()-t0
        receipt["model_manifest_sha256"]=sha_file(root/"manifest.json")
        receipt["model_files"]=manifest
        tokenizer=AutoTokenizer.from_pretrained(str(root),local_files_only=True,trust_remote_code=False)
        eager_model=AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,
            use_safetensors=True,trust_remote_code=False,attn_implementation="eager").eval()
        sdpa_model=AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,
            use_safetensors=True,trust_remote_code=False,attn_implementation="sdpa").eval()
        for label,model,expected in (("eager",eager_model,"eager"),("sdpa",sdpa_model,"sdpa")):
            if model.config.model_type!="gpt2" or next(model.parameters()).dtype!=torch.float32:
                raise RuntimeError("G86_PRETRAINED_FP32_MODEL_DRIFT_"+label)
            if getattr(model.config,"_attn_implementation",None)!=expected:
                raise RuntimeError("G86_ATTENTION_BACKEND_CONFIG_MISMATCH_"+label)
        eager_params=list(eager_model.parameters());sdpa_params=list(sdpa_model.parameters())
        if len(eager_params)!=len(sdpa_params) or any(not torch.equal(a,b) for a,b in zip(eager_params,sdpa_params)):
            raise RuntimeError("G86_ATTENTION_MODEL_WEIGHT_PARITY_FAILURE")
        if not hasattr(proc,"cpu_affinity"):raise RuntimeError("G86_CPU_AFFINITY_UNAVAILABLE")
        old_aff=proc.cpu_affinity()
        if len(old_aff)<CPU_BUDGET:raise RuntimeError("G86_THREE_CPU_AFFINITY_UNAVAILABLE")
        proc.cpu_affinity(old_aff[:CPU_BUDGET])
        receipt["fixed_affinity"]=proc.cpu_affinity()
        receipt["fixed_torch_interop"]=torch.get_num_interop_threads()
        import transformers.models.gpt2.modeling_gpt2 as gpt2_modeling
        dispatch={"sdpa":0,"eager":0}
        active_backend=["none"]
        original_sdpa=torch.nn.functional.scaled_dot_product_attention
        original_eager=gpt2_modeling.eager_attention_forward
        def counted_sdpa(*args,**kwargs):
            if active_backend[0]=="sdpa":dispatch["sdpa"]+=1
            return original_sdpa(*args,**kwargs)
        def counted_eager(*args,**kwargs):
            if active_backend[0]=="eager":dispatch["eager"]+=1
            return original_eager(*args,**kwargs)
        torch.nn.functional.scaled_dot_product_attention=counted_sdpa
        gpt2_modeling.eager_attention_forward=counted_eager
        models={"eager":eager_model,"sdpa":sdpa_model}
        def ids(s):return tokenizer(s,return_tensors="pt",add_special_tokens=False)["input_ids"]
        def full_decode(arm,full):
            backend,threads=ARM_SPEC[arm]
            model=models[backend]
            active_backend[0]=backend
            start_sdpa=dispatch["sdpa"];start_eager=dispatch["eager"]
            cpu0=time.process_time_ns();wall0=time.perf_counter_ns()
            torch.set_num_threads(threads)
            with torch.inference_mode():
                out=model(input_ids=full,use_cache=True,output_attentions=False)
                past,logits=out.past_key_values,out.logits[:,-1,:]
                chosen=[]
                for step in range(TOKENS):
                    token=logits.argmax(-1,keepdim=True)
                    chosen.append(token)
                    if step+1<TOKENS:
                        mask=torch.ones((1,int(full.shape[1])+step+1),dtype=torch.long)
                        out=model(input_ids=token,past_key_values=past,attention_mask=mask,
                                  use_cache=True,output_attentions=False)
                        past,logits=out.past_key_values,out.logits[:,-1,:]
                result=torch.cat(chosen,dim=1).flatten().tolist()
            wall_ns=time.perf_counter_ns()-wall0
            cpu_ns=time.process_time_ns()-cpu0
            sdpa_calls=dispatch["sdpa"]-start_sdpa
            eager_calls=dispatch["eager"]-start_eager
            if len(result)!=TOKENS or int(torch.get_num_threads())!=threads:
                raise RuntimeError("G86_TOKEN_COUNT_OR_THREAD_DRIFT_"+arm)
            if backend=="sdpa" and (sdpa_calls<=0 or eager_calls!=0):
                raise RuntimeError("G86_SDPA_BACKEND_NOT_EXCLUSIVELY_DISPATCHED")
            if backend=="eager" and (eager_calls<=0 or sdpa_calls!=0):
                raise RuntimeError("G86_EAGER_BACKEND_NOT_EXCLUSIVELY_DISPATCHED")
            return result,{"wall_ns":wall_ns,"process_cpu_ns":cpu_ns,
                "rss_sampled":proc.memory_info().rss,"output_sha256":
                hashlib.sha256(json.dumps(result,separators=(",",":")).encode()).hexdigest(),
                "sdpa_dispatch_calls":sdpa_calls,"eager_dispatch_calls":eager_calls,
                "backend_dispatch_calls":sdpa_calls+eager_calls}
        public=ids("A public nonheldout example for exact original CPU decoding.")
        for _ in range(2):
            ref,_=full_decode("eager1",public)
            for arm in ARMS:
                got,_=full_decode(arm,public)
                if got!=ref:raise RuntimeError("G86_PUBLIC_BACKEND_TOKEN_MISMATCH_"+arm)
        inputs=[]
        for original in selected:
            full=torch.cat((ids(g55.PREFIX),ids(original["instruction"])[:,:64]),dim=1)
            if full.shape[1]+TOKENS>eager_model.config.n_positions:raise RuntimeError("G86_ORIGINAL_CONTEXT_OVERFLOW")
            inputs.append((original["source_row"],full))
        measured=[]
        reference_hashes=[]
        for i,(row,full) in enumerate(inputs):
            reference,_=full_decode("eager2",full)
            reference_hashes.append(hashlib.sha256(json.dumps(reference,separators=(",",":")).encode()).hexdigest())
            for rep in range(REPEATS):
                order=schedule(i,rep);measures={}
                for arm in order:
                    result,timing=full_decode(arm,full)
                    if result!=reference:raise RuntimeError("G86_EXACT_ORIGINAL_TOKEN_MISMATCH_"+arm+"_"+str(i))
                    measures[arm]=timing
                measured.append({"sample_index":i,"source_row":row,"rep":rep+1,"order":order,
                    "original_input_token_count":int(full.shape[1]),
                    "original_input_sha256":hashlib.sha256(full.numpy().tobytes()).hexdigest(),
                    "measure":measures})
        arms,summary,decision=decide(measured)
        receipt["original_paired_trials"]=measured
        receipt["arm_summaries"]=arms
        receipt["summary"]=summary
        receipt["reference_output_hashes"]=reference_hashes
        receipt["engineering"]="PASS";receipt["correctness"]="PASS";receipt["decision"]=decision
    except BaseException as exc:
        receipt["error"]=type(exc).__name__+": "+str(exc)
        receipt["traceback_tail"]=traceback.format_exc()[-2500:]
        raise
    finally:
        if "active_backend" in locals():active_backend[0]="none"
        if "original_sdpa" in locals():torch.nn.functional.scaled_dot_product_attention=original_sdpa
        if "original_eager" in locals():gpt2_modeling.eager_attention_forward=original_eager
        if old_aff is not None:
            receipt["cpu_affinity_at_end"]=proc.cpu_affinity()
            proc.cpu_affinity(old_aff)
        Path("cpu_g86_original_result.json").write_text(
            json.dumps(receipt,sort_keys=True,indent=2,default=str)+"\n",encoding="utf-8")
        print(json.dumps({k:receipt.get(k) for k in
            ("gate","engineering","correctness","decision","summary","error")},sort_keys=True),flush=True)

if __name__=="__main__":main()
