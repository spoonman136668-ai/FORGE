#!/usr/bin/env python3
"""CPU G88: authenticate oneDNN dispatch and compare MKLDNN enabled/disabled."""
from __future__ import annotations
import contextlib,ctypes,hashlib,importlib.util,json,math,os,platform,statistics,time,traceback,urllib.request,tempfile
from pathlib import Path

PREREG="c5247d658eaf2c0e226025660bbe8cb62b0f7b57"
MODEL_REV="607a30d783dfa663caf39e06633721c8d4cfcd7e"
WEIGHTS_SHA="248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
DATA_REV="3101c7d5072418e28b9008a6636bde82a006892c"
DATA_SHA="3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14"
DATA_BYTES=749738
SEED=b"G68-GPT2-HELDOUT-20261030:"
OFFSET=180;CASES=12;REPEATS=4;TOKENS=8;CPU_BUDGET=3
ARMS=("mkldnn_enabled2","mkldnn_disabled2")
THRESHOLDS={"speedup_min":1.15,"min_paired":.90,"p95_max":1.10,"rss_max":1.10,"cpu_max":1.25}

def contract():
    assert (OFFSET,CASES,REPEATS,TOKENS,CPU_BUDGET)==(180,12,4,8,3)
    assert ARMS==("mkldnn_enabled2","mkldnn_disabled2")
    assert THRESHOLDS=={"speedup_min":1.15,"min_paired":.90,"p95_max":1.10,"rss_max":1.10,"cpu_max":1.25}

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
    if len(out)!=n:raise RuntimeError("G88_INSUFFICIENT_ORIGINAL_HELDOUT")
    return out

def schedule(i,r):
    names=ARMS;shift=(i+r)%len(names);order=list(names[shift:]+names[:shift])
    if r%2:order.reverse()
    return tuple(order)

def p95(xs):return sorted(xs)[max(0,math.ceil(.95*len(xs))-1)]

def decide(trials):
    if len(trials)!=CASES*REPEATS:raise RuntimeError("G88_INCOMPLETE_ORIGINAL_TRIALS")
    for t in trials:
        if set(t["measure"])!=set(ARMS):raise RuntimeError("G88_MISSING_ARM")
        x=t["measure"][ARMS[0]];y=t["measure"][ARMS[1]]
        if x["output_sha256"]!=y["output_sha256"]:raise RuntimeError("G88_ORIGINAL_TOKEN_PARITY_ERROR")
    arms={}
    for a in ARMS:
        ws=[t["measure"][a]["wall_ns"] for t in trials]
        arms[a]={"median_wall_ns":statistics.median(ws),"p95_wall_ns":p95(ws),
          "total_process_cpu_ns":sum(t["measure"][a]["process_cpu_ns"] for t in trials),
          "max_sampled_rss_bytes":max(t["measure"][a]["rss_sampled"] for t in trials)}
    on=arms["mkldnn_enabled2"];off=arms["mkldnn_disabled2"]
    ratios=[t["measure"]["mkldnn_disabled2"]["wall_ns"]/t["measure"]["mkldnn_enabled2"]["wall_ns"] for t in trials]
    summary={"median_speedup_enabled_vs_disabled":off["median_wall_ns"]/on["median_wall_ns"],
      "minimum_individual_paired_speedup_disabled_vs_enabled":min(ratios),
      "p95_enabled_over_disabled_ratio":on["p95_wall_ns"]/off["p95_wall_ns"],
      "sampled_rss_enabled_over_disabled_ratio":on["max_sampled_rss_bytes"]/off["max_sampled_rss_bytes"],
      "total_cpu_enabled_over_disabled_ratio":on["total_process_cpu_ns"]/off["total_process_cpu_ns"],
      "timed_authentic_responses":len(trials)*2,"timed_authentic_generated_tokens":len(trials)*2*TOKENS}
    ok=(summary["median_speedup_enabled_vs_disabled"]>=THRESHOLDS["speedup_min"]
      and summary["minimum_individual_paired_speedup_disabled_vs_enabled"]>=THRESHOLDS["min_paired"]
      and summary["p95_enabled_over_disabled_ratio"]<=THRESHOLDS["p95_max"]
      and summary["sampled_rss_enabled_over_disabled_ratio"]<=THRESHOLDS["rss_max"]
      and summary["total_cpu_enabled_over_disabled_ratio"]<=THRESHOLDS["cpu_max"])
    return arms,summary,"MKLDNN_PASS" if ok else "MKLDNN_NO_GO"

@contextlib.contextmanager
def capture_native_stdout():
    """Capture C/C++ oneDNN verbose output emitted to file descriptor 1."""
    import sys
    sys.stdout.flush();ctypes.CDLL(None).fflush(None)
    with tempfile.TemporaryFile(mode="w+b") as f:
        saved=os.dup(1)
        try:
            os.dup2(f.fileno(),1)
            yield f
            sys.stdout.flush();ctypes.CDLL(None).fflush(None)
        finally:
            os.dup2(saved,1);os.close(saved)

def main():
    import psutil,torch,transformers
    from transformers import AutoTokenizer,AutoModelForCausalLM
    contract()
    if os.name!="posix" or platform.system()!="Linux" or platform.machine().lower() not in ("x86_64","amd64"):
        raise RuntimeError("G88_NOT_NATIVE_X86_64_LINUX")
    if torch.version.cuda is not None:raise RuntimeError("G88_NON_CPU_PYTORCH_BUILD")
    if not torch.backends.mkldnn.is_available():raise RuntimeError("G88_MKLDNN_NOT_AVAILABLE")
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    proc=psutil.Process();old_aff=None
    receipt={"schema":"forge.cpu-llm-g88.authentic-mkldnn-backend.v1","gate":"CPU_G88",
      "preregistration_commit":PREREG,"source_sha":os.getenv("GITHUB_SHA","UNSET"),
      "model_revision":MODEL_REV,"model_weights_sha256":WEIGHTS_SHA,
      "dataset_revision":DATA_REV,"dataset_sha256":DATA_SHA,
      "runtime":{"torch":torch.__version__,"torch_cuda":torch.version.cuda,
        "transformers":transformers.__version__,"python":platform.python_version(),
        "machine":platform.machine(),"processor":platform.processor(),
        "logical_cpu_count":os.cpu_count(),"platform":platform.platform(),
        "mkldnn_available":torch.backends.mkldnn.is_available()},
      "engineering":"UNVERIFIED","correctness":"UNVERIFIED","decision":"UNVERIFIED",
      "scientific_acceptance":"NOT_GRANTED","promotion_allowed":False,
      "limitations":["Original GPT2 FP32 eight-token CPU requests only",
        "Three logical CPUs fixed for both arms; PyTorch inter-op 1 and intra-op 2",
        "GSM8K questions may have been represented in pretraining",
        "RSS sampled; no energy metric; one pinned Linux host only",
        "No model weights changed, no GPU, no native Wingless/Yggdrasil or acceptance"]}
    try:
        raw=Path("cpu_g88_original_gsm8k.jsonl")
        req=urllib.request.Request("https://raw.githubusercontent.com/openai/grade-school-math/"+DATA_REV+"/grade_school_math/data/test.jsonl",
          headers={"User-Agent":"FORGE-CPU-G88-MKLDNN/1"})
        with urllib.request.urlopen(req,timeout=45) as inp,raw.open("xb") as out:
            n=0
            while True:
                b=inp.read(1<<20)
                if not b:break
                n+=len(b)
                if n>800000:raise RuntimeError("G88_DATA_SIZE_CAP")
                out.write(b)
        if raw.stat().st_size!=DATA_BYTES or sha_file(raw)!=DATA_SHA:raise RuntimeError("G88_DATA_IDENTITY_DRIFT")
        with raw.open(encoding="utf-8") as f:
            records=[{"instruction":x["question"],"category":"math_word_problem"} for x in (json.loads(line) for line in f if line.strip())]
        ranked=rank_original(records,OFFSET+CASES)
        g68=module("g88_g68","llm_g68/g68_gsm8k_http.py");g70=module("g88_g70","llm_g70/g70_gsm8k_locality.py")
        if ranked[:12]!=g68.select_heldout(records) or ranked[12:24]!=g70.select_heldout(records):raise RuntimeError("G88_RANK_CONTRACT_DRIFT")
        if len({x["source_row"] for x in ranked})!=OFFSET+CASES:raise RuntimeError("G88_DUPLICATE_RANK")
        selected=ranked[OFFSET:OFFSET+CASES]
        receipt["selected"]=[{k:v for k,v in x.items() if k!="instruction"} for x in selected]
        receipt["selected_ranks"]=[OFFSET,OFFSET+CASES-1]
        g55=module("g88_g55","llm_g55/g55_gpt2_controls.py")
        if (g55.REV,g55.WEIGHT_SHA)!=(MODEL_REV,WEIGHTS_SHA):raise RuntimeError("G88_MODEL_IDENTITY_DRIFT")
        t0=time.perf_counter();root,manifest=g55.stage()
        receipt["model_manifest_sha256"]=sha_file(root/"manifest.json");receipt["model_files"]=manifest
        tok=AutoTokenizer.from_pretrained(str(root),local_files_only=True,trust_remote_code=False)
        models={}
        for name,enabled in (("enabled",True),("disabled",False)):
            models[name]=AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,
              use_safetensors=True,trust_remote_code=False,attn_implementation="eager").eval()
        p0=list(models["enabled"].parameters());p1=list(models["disabled"].parameters())
        if len(p0)!=len(p1) or any(not torch.equal(a,b) for a,b in zip(p0,p1)):raise RuntimeError("G88_WEIGHT_PARITY_FAILURE")
        if not hasattr(proc,"cpu_affinity"):raise RuntimeError("G88_AFFINITY_UNAVAILABLE")
        old_aff=proc.cpu_affinity()
        if len(old_aff)<CPU_BUDGET:raise RuntimeError("G88_THREE_CPU_AFFINITY_UNAVAILABLE")
        proc.cpu_affinity(old_aff[:CPU_BUDGET]);receipt["fixed_affinity"]=proc.cpu_affinity()
        receipt["fixed_torch_interop"]=torch.get_num_interop_threads()
        def ids(s):return tok(s,return_tensors="pt",add_special_tokens=False)["input_ids"]
        inputs=[]
        for item in selected:
            full=torch.cat((ids(g55.PREFIX),ids(item["instruction"])[:,:64]),dim=1)
            if full.shape[1]+TOKENS>models["enabled"].config.n_positions:raise RuntimeError("G88_CONTEXT_OVERFLOW")
            inputs.append((item["source_row"],full))
        def decode(model,enabled,full):
            torch.backends.mkldnn.enabled=enabled
            t0=time.perf_counter_ns();c0=time.process_time_ns();torch.set_num_threads(2)
            with torch.inference_mode():
                out=model(input_ids=full,use_cache=True)
                past,logits=out.past_key_values,out.logits[:,-1,:];generated=[]
                for step in range(TOKENS):
                    nxt=logits.argmax(-1,keepdim=True);generated.append(nxt)
                    if step+1<TOKENS:
                        mask=torch.ones((1,int(full.shape[1])+step+1),dtype=torch.long)
                        out=model(input_ids=nxt,past_key_values=past,attention_mask=mask,use_cache=True)
                        past,logits=out.past_key_values,out.logits[:,-1,:]
            wall=time.perf_counter_ns()-t0;cpu=time.process_time_ns()-c0
            result=torch.cat(generated,dim=1).flatten().tolist()
            return result,{"wall_ns":wall,"process_cpu_ns":cpu,"rss_sampled":proc.memory_info().rss,
              "output_sha256":hashlib.sha256(json.dumps(result,separators=(",",":")).encode()).hexdigest()}
        # Verify real oneDNN primitive dispatch with its native verbose interface.
        probe=inputs[0][1]
        verbosity={}
        for name,enabled in (("enabled",True),("disabled",False)):
            with capture_native_stdout() as handle:
                with torch.backends.mkldnn.verbose(torch.backends.mkldnn.VERBOSE_ON):
                    test,tm=decode(models[name],enabled,probe)
                handle.seek(0);log=handle.read().decode("utf-8","replace")
            lines=[s for s in log.splitlines() if "onednn_verbose" in s.lower() and (",exec," in s.lower() or ",primitive,exec" in s.lower())]
            verbosity[name]={"primitive_execution_lines":len(lines),"sample":lines[:8],"captured_bytes":len(log)}
        receipt["backend_dispatch_evidence"]=verbosity
        if verbosity["enabled"]["primitive_execution_lines"]<=0:raise RuntimeError("G88_ENABLED_ARM_DID_NOT_DISPATCH_ONEDNN")
        if verbosity["disabled"]["primitive_execution_lines"]!=0:raise RuntimeError("G88_DISABLED_ARM_STILL_DISPATCHED_ONEDNN")
        # Warm both execution paths outside the measured cohort.
        for i,(row,full) in enumerate(inputs):
            a,_=decode(models["disabled"],False,full)
            for name,enabled in (("enabled",True),("disabled",False)):
                b,_=decode(models[name],enabled,full)
                if b!=a:raise RuntimeError("G88_WARMUP_EXACTNESS_"+name)
        trials=[]
        for i,(row,full) in enumerate(inputs):
            reference,_=decode(models["disabled"],False,full)
            for rep in range(REPEATS):
                arms=schedule(i,rep);measures={}
                for arm in arms:
                    enabled=arm=="mkldnn_enabled2"
                    got,tm=decode(models["enabled" if enabled else "disabled"],enabled,full)
                    if got!=reference:raise RuntimeError("G88_EXACT_TOKEN_MISMATCH_"+arm+"_"+str(i))
                    measures[arm]=tm
                trials.append({"sample_index":i,"source_row":row,"rep":rep+1,"order":arms,
                  "original_input_token_count":int(full.shape[1]),
                  "original_input_sha256":hashlib.sha256(full.numpy().tobytes()).hexdigest(),"measure":measures})
        arms,summary,decision=decide(trials)
        receipt["original_paired_trials"]=trials;receipt["arm_summaries"]=arms;receipt["summary"]=summary
        receipt["engineering"]="PASS";receipt["correctness"]="PASS";receipt["decision"]=decision
    except BaseException as exc:
        receipt["error"]=type(exc).__name__+": "+str(exc);receipt["traceback_tail"]=traceback.format_exc()[-2500:]
        raise
    finally:
        if old_aff is not None:
            receipt["cpu_affinity_at_end"]=proc.cpu_affinity();proc.cpu_affinity(old_aff)
        torch.backends.mkldnn.enabled=True
        Path("cpu_g88_original_result.json").write_text(json.dumps(receipt,sort_keys=True,indent=2,default=str)+"\n",encoding="utf-8")
        print(json.dumps({k:receipt.get(k) for k in ("gate","engineering","correctness","decision","backend_dispatch_evidence","summary","error")},sort_keys=True),flush=True)

if __name__=="__main__":main()
