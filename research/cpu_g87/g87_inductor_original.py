#!/usr/bin/env python3
"""CPU G87: original GPT-2 eager versus fullgraph CPU Inductor compilation."""
from __future__ import annotations
import hashlib,json,math,os,platform,statistics,time,traceback,urllib.request
from pathlib import Path

PREREG="7f2cfff5f2348a28141df4c63792a3bfb659175c"
MODEL_REV="607a30d783dfa663caf39e06633721c8d4cfcd7e"
WEIGHTS_SHA="248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
DATA_REV="3101c7d5072418e28b9008a6636bde82a006892c"
DATA_SHA="3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14"
DATA_BYTES=749738
SEED=b"G68-GPT2-HELDOUT-20261030:"
OFFSET=168;CASES=12;REPEATS=4;TOKENS=8;CPU_BUDGET=3;HORIZON=1000
ARMS=("eager2","inductor2")
THRESHOLDS={"speedup_min":1.15,"min_paired":0.90,"p95_max":1.10,
            "rss_max":1.10,"cpu_max":1.25,"compile_seconds_max":300.0,
            "break_even_max":1000,"horizon_ratio_max":0.95}

def contract():
    assert (OFFSET,CASES,REPEATS,TOKENS,CPU_BUDGET,HORIZON)==(168,12,4,8,3,1000)
    assert ARMS==("eager2","inductor2")
    assert THRESHOLDS=={"speedup_min":1.15,"min_paired":0.90,"p95_max":1.10,
      "rss_max":1.10,"cpu_max":1.25,"compile_seconds_max":300.0,
      "break_even_max":1000,"horizon_ratio_max":0.95}

def sha_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()

def module(name,rel):
    import importlib.util
    p=Path(__file__).resolve().parents[1]/rel
    s=importlib.util.spec_from_file_location(name,p)
    x=importlib.util.module_from_spec(s);s.loader.exec_module(x)
    return x

def rank_original(records,n):
    candidate=[]
    for row,item in enumerate(records):
        q=item.get("instruction","");cat=item.get("category","")
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
    if len(chosen)!=n:raise RuntimeError("G87_INSUFFICIENT_ORIGINAL_HELDOUT")
    return chosen

def schedule(sample,rep):
    names=ARMS;shift=(sample+rep)%len(names)
    order=list(names[shift:]+names[:shift])
    if rep%2:order.reverse()
    return tuple(order)

def p95(vals):
    return sorted(vals)[max(0,math.ceil(.95*len(vals))-1)]

def decide(trials,compile_seconds,compile_count,graph_breaks):
    if len(trials)!=CASES*REPEATS:raise RuntimeError("G87_INCOMPLETE_ORIGINAL_TRIALS")
    if not (0 < compile_count <= 4):raise RuntimeError("G87_INDUCTOR_GRAPH_COUNT_OUT_OF_BOUNDS")
    if graph_breaks:raise RuntimeError("G87_DYNAMO_GRAPH_BREAKS")
    for t in trials:
        if set(t["measure"])!=set(ARMS) or set(t["order"])!=set(ARMS):
            raise RuntimeError("G87_MISSING_FROZEN_ARMS")
        a=t["measure"]["eager2"];b=t["measure"]["inductor2"]
        if a["output_sha256"]!=b["output_sha256"]:
            raise RuntimeError("G87_ORIGINAL_TOKEN_PARITY_ERROR")
        for arm in ARMS:
            x=t["measure"][arm]
            if x["wall_ns"]<=0 or x["process_cpu_ns"]<=0 or x["rss_sampled"]<=0:
                raise RuntimeError("G87_INVALID_TIMING_OR_RSS")
    arms={}
    for arm in ARMS:
        w=[t["measure"][arm]["wall_ns"] for t in trials]
        arms[arm]={"median_wall_ns":statistics.median(w),"p95_wall_ns":p95(w),
          "total_process_cpu_ns":sum(t["measure"][arm]["process_cpu_ns"] for t in trials),
          "max_sampled_rss_bytes":max(t["measure"][arm]["rss_sampled"] for t in trials)}
    e=arms["eager2"];c=arms["inductor2"]
    paired=[t["measure"]["eager2"]["wall_ns"]/t["measure"]["inductor2"]["wall_ns"] for t in trials]
    per_request_saving=(e["median_wall_ns"]-c["median_wall_ns"])/1e9
    break_even=(math.ceil(compile_seconds/per_request_saving) if per_request_saving>0 else None)
    horizon_ratio=(compile_seconds+(HORIZON*c["median_wall_ns"]/1e9))/(HORIZON*e["median_wall_ns"]/1e9)
    summary={
      "primary_median_speedup_inductor2_vs_eager2":e["median_wall_ns"]/c["median_wall_ns"],
      "minimum_individual_paired_speedup_eager2_vs_inductor2":min(paired),
      "p95_inductor2_over_eager2_ratio":c["p95_wall_ns"]/e["p95_wall_ns"],
      "sampled_rss_inductor2_over_eager2_ratio":c["max_sampled_rss_bytes"]/e["max_sampled_rss_bytes"],
      "total_cpu_inductor2_over_eager2_ratio":c["total_process_cpu_ns"]/e["total_process_cpu_ns"],
      "compile_startup_seconds":compile_seconds,
      "compiled_graph_count":compile_count,"graph_break_count":graph_breaks,
      "break_even_full_responses":break_even,
      "amortized_total_wall_ratio_at_1000_responses":horizon_ratio,
      "timed_authentic_responses":len(trials)*len(ARMS),
      "timed_authentic_generated_tokens":len(trials)*len(ARMS)*TOKENS}
    ok=(summary["primary_median_speedup_inductor2_vs_eager2"]>=THRESHOLDS["speedup_min"]
      and summary["minimum_individual_paired_speedup_eager2_vs_inductor2"]>=THRESHOLDS["min_paired"]
      and summary["p95_inductor2_over_eager2_ratio"]<=THRESHOLDS["p95_max"]
      and summary["sampled_rss_inductor2_over_eager2_ratio"]<=THRESHOLDS["rss_max"]
      and summary["total_cpu_inductor2_over_eager2_ratio"]<=THRESHOLDS["cpu_max"]
      and compile_seconds<=THRESHOLDS["compile_seconds_max"]
      and break_even is not None and break_even<=THRESHOLDS["break_even_max"]
      and horizon_ratio<=THRESHOLDS["horizon_ratio_max"])
    return arms,summary,"INDUCTOR_PASS" if ok else "INDUCTOR_NO_GO"

def main():
    import psutil,torch,transformers
    from transformers import AutoTokenizer,AutoModelForCausalLM
    contract()
    if os.name!="posix" or platform.system()!="Linux" or platform.machine().lower() not in ("x86_64","amd64"):
        raise RuntimeError("G87_NOT_NATIVE_X86_64_LINUX")
    if torch.version.cuda is not None:raise RuntimeError("G87_NON_CPU_PYTORCH_BUILD")
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    proc=psutil.Process();old_aff=None
    receipt={"schema":"forge.cpu-llm-g87.authentic-inductor-compilation.v1",
      "gate":"CPU_G87","preregistration_commit":PREREG,"source_sha":os.getenv("GITHUB_SHA","UNSET"),
      "model_revision":MODEL_REV,"model_weights_sha256":WEIGHTS_SHA,
      "dataset_revision":DATA_REV,"dataset_sha256":DATA_SHA,
      "runtime":{"torch":torch.__version__,"torch_cuda":torch.version.cuda,
        "transformers":transformers.__version__,"python":platform.python_version(),
        "machine":platform.machine(),"processor":platform.processor(),
        "logical_cpu_count":os.cpu_count(),"os_name":os.name,"platform":platform.platform()},
      "engineering":"UNVERIFIED","correctness":"UNVERIFIED","decision":"UNVERIFIED",
      "scientific_acceptance":"NOT_GRANTED","promotion_allowed":False,
      "limitations":["Original GPT2 FP32 8-token CPU requests only; not production network traffic",
        "Compilation startup and warmup charged to frozen 1000-response amortization",
        "Three logical CPU affinity fixed; PyTorch inter-op threads fixed at one",
        "RSS sampled, not hardware peak; no energy metric",
        "GSM8K may be familiar to GPT2 pretraining; no training-held-out claim",
        "No GPU, native Wingless/Yggdrasil or scientific/model acceptance"]}
    compile_model=None;compile_count=0;compile_durations=[];old_counters=None
    try:
        raw=Path("cpu_g87_original_gsm8k.jsonl")
        req=urllib.request.Request(
          "https://raw.githubusercontent.com/openai/grade-school-math/"+DATA_REV+"/grade_school_math/data/test.jsonl",
          headers={"User-Agent":"FORGE-CPU-G87-Inductor/1"})
        with urllib.request.urlopen(req,timeout=45) as inp,raw.open("xb") as out:
            total=0
            while True:
                part=inp.read(1<<20)
                if not part:break
                total+=len(part)
                if total>800000:raise RuntimeError("G87_ORIGINAL_DATA_SIZE_CAP")
                out.write(part)
        if raw.stat().st_size!=DATA_BYTES or sha_file(raw)!=DATA_SHA:
            raise RuntimeError("G87_ORIGINAL_GSM8K_DATA_IDENTITY_DRIFT")
        with raw.open(encoding="utf-8") as f:
            records=[{"instruction":x["question"],"category":"math_word_problem"}
                     for x in (json.loads(line) for line in f if line.strip())]
        ranked=rank_original(records,OFFSET+CASES)
        g68=module("g87_g68","llm_g68/g68_gsm8k_http.py")
        g70=module("g87_g70","llm_g70/g70_gsm8k_locality.py")
        if ranked[:12]!=g68.select_heldout(records) or ranked[12:24]!=g70.select_heldout(records):
            raise RuntimeError("G87_ORIGINAL_RANK_CONTRACT_DRIFT")
        if len({x["source_row"] for x in ranked})!=OFFSET+CASES:
            raise RuntimeError("G87_DUPLICATED_ORIGINAL_RANKS")
        selected=ranked[OFFSET:OFFSET+CASES]
        receipt["selected"]=[{k:v for k,v in x.items() if k!="instruction"} for x in selected]
        receipt["selected_ranks"]=[OFFSET,OFFSET+CASES-1]
        g55=module("g87_g55","llm_g55/g55_gpt2_controls.py")
        if (g55.REV,g55.WEIGHT_SHA)!=(MODEL_REV,WEIGHTS_SHA):
            raise RuntimeError("G87_G55_MODEL_IDENTITY_DRIFT")
        t0=time.perf_counter();root,manifest=g55.stage()
        receipt["model_staging_wall_s"]=time.perf_counter()-t0
        receipt["model_manifest_sha256"]=sha_file(root/"manifest.json")
        receipt["model_files"]=manifest
        tokenizer=AutoTokenizer.from_pretrained(str(root),local_files_only=True,trust_remote_code=False)
        eager=AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,
            use_safetensors=True,trust_remote_code=False,attn_implementation="eager").eval()
        inductor_model=AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,
            use_safetensors=True,trust_remote_code=False,attn_implementation="eager").eval()
        if eager.config.model_type!="gpt2" or next(eager.parameters()).dtype!=torch.float32:
            raise RuntimeError("G87_ORIGINAL_FP32_MODEL_DRIFT")
        ep=list(eager.parameters());ip=list(inductor_model.parameters())
        if len(ep)!=len(ip) or any(not torch.equal(a,b) for a,b in zip(ep,ip)):
            raise RuntimeError("G87_ORIGINAL_WEIGHT_PARITY_FAILURE")
        if not hasattr(proc,"cpu_affinity"):raise RuntimeError("G87_CPU_AFFINITY_UNAVAILABLE")
        old_aff=proc.cpu_affinity()
        if len(old_aff)<CPU_BUDGET:raise RuntimeError("G87_THREE_CPU_AFFINITY_UNAVAILABLE")
        proc.cpu_affinity(old_aff[:CPU_BUDGET])
        receipt["fixed_affinity"]=proc.cpu_affinity()
        receipt["fixed_torch_interop"]=torch.get_num_interop_threads()
        def ids(s):return tokenizer(s,return_tensors="pt",add_special_tokens=False)["input_ids"]
        inputs=[]
        for item in selected:
            full=torch.cat((ids(g55.PREFIX),ids(item["instruction"])[:,:64]),dim=1)
            if full.shape[1]+TOKENS>eager.config.n_positions:raise RuntimeError("G87_CONTEXT_OVERFLOW")
            inputs.append((item["source_row"],full))
        def decode(model,full):
            start_wall=time.perf_counter_ns();start_cpu=time.process_time_ns()
            torch.set_num_threads(2)
            with torch.inference_mode():
                out=model(input_ids=full,use_cache=True)
                past,logits=out.past_key_values,out.logits[:,-1,:]
                out_tokens=[]
                for step in range(TOKENS):
                    tok=logits.argmax(-1,keepdim=True);out_tokens.append(tok)
                    if step+1<TOKENS:
                        mask=torch.ones((1,int(full.shape[1])+step+1),dtype=torch.long)
                        out=model(input_ids=tok,past_key_values=past,attention_mask=mask,use_cache=True)
                        past,logits=out.past_key_values,out.logits[:,-1,:]
            wall=time.perf_counter_ns()-start_wall;cpu=time.process_time_ns()-start_cpu
            result=torch.cat(out_tokens,dim=1).flatten().tolist()
            return result,{"wall_ns":wall,"process_cpu_ns":cpu,"rss_sampled":proc.memory_info().rss,
              "output_sha256":hashlib.sha256(json.dumps(result,separators=(",",":")).encode()).hexdigest()}
        # Warm eager on every new dynamic prompt shape before paired measurements.
        eager_refs={}
        with torch.inference_mode():
            for i,(row,full) in enumerate(inputs):
                for _ in range(2):
                    result,_=decode(eager,full)
                    if len(result)!=TOKENS:raise RuntimeError("G87_EAGER_WARMUP_TOKEN_COUNT")
                eager_refs[i]=result
        # Count only real Inductor graph compilations; fullgraph=True turns graph breaks into hard failures.
        torch._dynamo.reset()
        torch._dynamo.utils.counters.clear()
        base_inductor=torch._dynamo.backends.registry.lookup_backend("inductor")
        compile_events=[]
        def counted_inductor(gm,example_inputs):
            start=time.perf_counter()
            artifact=base_inductor(gm,example_inputs)
            compile_events.append(time.perf_counter()-start)
            return artifact
        startup=time.perf_counter()
        compile_model=torch.compile(inductor_model,backend=counted_inductor,
                                    fullgraph=True,dynamic=True,mode="default")
        compile_warmup={}
        with torch.inference_mode():
            for i,(row,full) in enumerate(inputs):
                result,_=decode(compile_model,full)
                if result!=eager_refs[i]:raise RuntimeError("G87_COMPILED_WARMUP_EXACTNESS_FAILURE")
                compile_warmup[i]=result
                if len(compile_events)>4:raise RuntimeError("G87_TOO_MANY_INDUCTOR_GRAPHS")
        compile_seconds=time.perf_counter()-startup
        graph_breaks=sum(torch._dynamo.utils.counters.get("graph_break",{}).values())
        compile_count=len(compile_events)
        receipt["compile_evidence"]={"startup_seconds":compile_seconds,
          "compiled_graph_count":compile_count,"graph_break_count":graph_breaks,
          "per_graph_compile_seconds":compile_events,"backend":"torch._inductor",
          "fullgraph":True,"dynamic":True,"mode":"default"}
        if not (0<compile_count<=4) or graph_breaks:
            raise RuntimeError("G87_INDUCTOR_GRAPH_CAPTURE_OR_FALLBACK_FAILURE")
        measured=[]
        for i,(row,full) in enumerate(inputs):
            for rep in range(REPEATS):
                order=schedule(i,rep);m={}
                for arm in order:
                    model=eager if arm=="eager2" else compile_model
                    result,timing=decode(model,full)
                    if result!=eager_refs[i]:
                        raise RuntimeError("G87_EXACT_ORIGINAL_TOKEN_MISMATCH_"+arm+"_"+str(i))
                    m[arm]=timing
                measured.append({"sample_index":i,"source_row":row,"rep":rep+1,
                  "order":order,"original_input_token_count":int(full.shape[1]),
                  "original_input_sha256":hashlib.sha256(full.numpy().tobytes()).hexdigest(),
                  "measure":m})
        arms,summary,decision=decide(measured,compile_seconds,compile_count,graph_breaks)
        receipt["original_paired_trials"]=measured
        receipt["arm_summaries"]=arms;receipt["summary"]=summary
        receipt["engineering"]="PASS";receipt["correctness"]="PASS";receipt["decision"]=decision
    except BaseException as exc:
        receipt["error"]=type(exc).__name__+": "+str(exc)
        receipt["traceback_tail"]=traceback.format_exc()[-2500:]
        raise
    finally:
        if old_aff is not None:
            receipt["cpu_affinity_at_end"]=proc.cpu_affinity()
            proc.cpu_affinity(old_aff)
        Path("cpu_g87_original_result.json").write_text(
            json.dumps(receipt,sort_keys=True,indent=2,default=str)+"\n",encoding="utf-8")
        print(json.dumps({k:receipt.get(k) for k in
          ("gate","engineering","correctness","decision","compile_evidence","summary","error")},sort_keys=True),flush=True)

if __name__=="__main__":main()
