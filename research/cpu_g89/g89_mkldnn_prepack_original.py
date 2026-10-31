#!/usr/bin/env python3
"""CPU G89: exact GPT2 Conv1D->Linear representation plus explicit oneDNN prepacking."""
from __future__ import annotations
import copy,hashlib,importlib.util,json,math,os,platform,statistics,time,traceback,urllib.request
from pathlib import Path

PREREG="09a5849d63fab89f187a31501335b29886c92f26"
MODEL_REV="607a30d783dfa663caf39e06633721c8d4cfcd7e"
WEIGHTS_SHA="248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
DATA_REV="3101c7d5072418e28b9008a6636bde82a006892c"
DATA_SHA="3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14"
DATA_BYTES=749738
SEED=b"G68-GPT2-HELDOUT-20261030:"
OFFSET=192;CASES=12;REPEATS=4;TOKENS=8;CPU_BUDGET=3;HORIZON=1000
ARMS=("original_conv1d2","mkldnn_prepacked_linear2")
THRESHOLDS={"speedup_min":1.15,"min_paired":.90,"p95_max":1.10,
 "rss_max":1.10,"cpu_max":1.25,"conversion_seconds_max":300.0,
 "break_even_max":1000,"horizon_ratio_max":.95}

def contract():
    assert (OFFSET,CASES,REPEATS,TOKENS,CPU_BUDGET,HORIZON)==(192,12,4,8,3,1000)
    assert ARMS==("original_conv1d2","mkldnn_prepacked_linear2")
    assert THRESHOLDS=={"speedup_min":1.15,"min_paired":.90,"p95_max":1.10,
     "rss_max":1.10,"cpu_max":1.25,"conversion_seconds_max":300.0,
     "break_even_max":1000,"horizon_ratio_max":.95}

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
    if len(out)!=n:raise RuntimeError("G89_INSUFFICIENT_ORIGINAL_HELDOUT")
    return out

def schedule(i,r):
    names=ARMS;shift=(i+r)%len(names);out=list(names[shift:]+names[:shift])
    if r%2:out.reverse()
    return tuple(out)

def p95(xs):return sorted(xs)[max(0,math.ceil(.95*len(xs))-1)]

def decide(trials,conversion_seconds):
    if len(trials)!=CASES*REPEATS:raise RuntimeError("G89_INCOMPLETE_ORIGINAL_TRIALS")
    for t in trials:
        if set(t["measure"])!=set(ARMS):raise RuntimeError("G89_MISSING_ARM")
        if t["measure"][ARMS[0]]["output_sha256"]!=t["measure"][ARMS[1]]["output_sha256"]:
            raise RuntimeError("G89_ORIGINAL_TOKEN_PARITY_ERROR")
    arms={}
    for arm in ARMS:
        wall=[t["measure"][arm]["wall_ns"] for t in trials]
        arms[arm]={"median_wall_ns":statistics.median(wall),"p95_wall_ns":p95(wall),
          "total_process_cpu_ns":sum(t["measure"][arm]["process_cpu_ns"] for t in trials),
          "max_sampled_rss_bytes":max(t["measure"][arm]["rss_sampled"] for t in trials)}
    eager=arms["original_conv1d2"];candidate=arms["mkldnn_prepacked_linear2"]
    paired=[t["measure"]["original_conv1d2"]["wall_ns"]/t["measure"]["mkldnn_prepacked_linear2"]["wall_ns"] for t in trials]
    per_request=(eager["median_wall_ns"]-candidate["median_wall_ns"])/1e9
    be=math.ceil(conversion_seconds/per_request) if per_request>0 else None
    horizon=(conversion_seconds+HORIZON*candidate["median_wall_ns"]/1e9)/(HORIZON*eager["median_wall_ns"]/1e9)
    summary={"median_speedup_prepacked_vs_original":eager["median_wall_ns"]/candidate["median_wall_ns"],
      "minimum_individual_paired_speedup":min(paired),
      "p95_prepacked_over_original_ratio":candidate["p95_wall_ns"]/eager["p95_wall_ns"],
      "sampled_rss_prepacked_over_original_ratio":candidate["max_sampled_rss_bytes"]/eager["max_sampled_rss_bytes"],
      "total_cpu_prepacked_over_original_ratio":candidate["total_process_cpu_ns"]/eager["total_process_cpu_ns"],
      "conversion_and_prepack_seconds":conversion_seconds,"break_even_full_responses":be,
      "amortized_total_wall_ratio_at_1000_responses":horizon,
      "timed_authentic_responses":len(trials)*2,"timed_authentic_generated_tokens":len(trials)*2*TOKENS}
    ok=(summary["median_speedup_prepacked_vs_original"]>=THRESHOLDS["speedup_min"]
      and summary["minimum_individual_paired_speedup"]>=THRESHOLDS["min_paired"]
      and summary["p95_prepacked_over_original_ratio"]<=THRESHOLDS["p95_max"]
      and summary["sampled_rss_prepacked_over_original_ratio"]<=THRESHOLDS["rss_max"]
      and summary["total_cpu_prepacked_over_original_ratio"]<=THRESHOLDS["cpu_max"]
      and conversion_seconds<=THRESHOLDS["conversion_seconds_max"]
      and be is not None and be<=THRESHOLDS["break_even_max"]
      and horizon<=THRESHOLDS["horizon_ratio_max"])
    return arms,summary,"MKLDNN_PREPACK_PASS" if ok else "MKLDNN_PREPACK_NO_GO"

def convert_conv1d_to_linear(model,torch):
    """Replace HF GPT2 Conv1D(nx,nf) with affine-equivalent nn.Linear(nf,nx) layout."""
    conversions=[]
    def visit(parent,prefix=""):
        for name,child in list(parent.named_children()):
            path=(prefix+"."+name).strip(".")
            if child.__class__.__name__=="Conv1D" and hasattr(child,"weight") and hasattr(child,"bias"):
                nx,nf=child.weight.shape
                linear=torch.nn.Linear(int(nx),int(nf),bias=True,dtype=child.weight.dtype)
                with torch.no_grad():
                    linear.weight.copy_(child.weight.detach().T.contiguous())
                    linear.bias.copy_(child.bias.detach())
                if not torch.equal(linear.weight.detach().T.contiguous(),child.weight.detach()):
                    raise RuntimeError("G89_CONV1D_LINEAR_WEIGHT_NOT_EXACT_"+path)
                if not torch.equal(linear.bias.detach(),child.bias.detach()):
                    raise RuntimeError("G89_CONV1D_LINEAR_BIAS_NOT_EXACT_"+path)
                conversions.append({"path":path,"in_features":int(nx),"out_features":int(nf),
                  "weight_original_sha256":hashlib.sha256(child.weight.detach().cpu().contiguous().numpy().tobytes()).hexdigest(),
                  "weight_linear_sha256":hashlib.sha256(linear.weight.detach().cpu().contiguous().numpy().tobytes()).hexdigest()})
                setattr(parent,name,linear)
            else:
                visit(child,path)
    visit(model)
    return conversions

def profile_linear_dispatch(model,torch,full):
    from torch.profiler import profile,ProfilerActivity
    torch.backends.mkldnn.enabled=True
    torch.set_num_threads(2)
    with profile(activities=[ProfilerActivity.CPU],record_shapes=False) as prof:
        with torch.inference_mode():
            model(input_ids=full,use_cache=True)
    rows=[]
    for x in prof.key_averages():
        if "mkldnn" in x.key.lower() or "onednn" in x.key.lower():
            rows.append({"key":x.key,"count":x.count,"self_cpu_time_total":x.self_cpu_time_total})
    linear=sum(x["count"] for x in rows if x["key"]=="aten::mkldnn_linear")
    return {"mkldnn_operator_events":rows,"mkldnn_linear_calls":linear}

def main():
    import psutil,torch,transformers
    from transformers import AutoTokenizer,AutoModelForCausalLM
    contract()
    if os.name!="posix" or platform.system()!="Linux" or platform.machine().lower() not in ("x86_64","amd64"):
        raise RuntimeError("G89_NOT_NATIVE_X86_64_LINUX")
    if torch.version.cuda is not None:raise RuntimeError("G89_NON_CPU_PYTORCH_BUILD")
    if not torch.backends.mkldnn.is_available():raise RuntimeError("G89_MKLDNN_NOT_AVAILABLE")
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    proc=psutil.Process();old_aff=None
    receipt={"schema":"forge.cpu-llm-g89.authentic-mkldnn-prepack.v1","gate":"CPU_G89",
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
        "No model weights trained or changed; no GPU, Wingless/Yggdrasil or promotion"]}
    try:
        raw=Path("cpu_g89_original_gsm8k.jsonl")
        req=urllib.request.Request("https://raw.githubusercontent.com/openai/grade-school-math/"+DATA_REV+"/grade_school_math/data/test.jsonl",
          headers={"User-Agent":"FORGE-CPU-G89-MKLDNN-PREPACK/1"})
        with urllib.request.urlopen(req,timeout=45) as inp,raw.open("xb") as out:
            n=0
            while True:
                b=inp.read(1<<20)
                if not b:break
                n+=len(b)
                if n>800000:raise RuntimeError("G89_DATA_SIZE_CAP")
                out.write(b)
        if raw.stat().st_size!=DATA_BYTES or sha_file(raw)!=DATA_SHA:raise RuntimeError("G89_DATA_IDENTITY_DRIFT")
        with raw.open(encoding="utf-8") as f:
            records=[{"instruction":x["question"],"category":"math_word_problem"} for x in (json.loads(line) for line in f if line.strip())]
        ranked=rank_original(records,OFFSET+CASES)
        g68=module("g89_g68","llm_g68/g68_gsm8k_http.py");g70=module("g89_g70","llm_g70/g70_gsm8k_locality.py")
        if ranked[:12]!=g68.select_heldout(records) or ranked[12:24]!=g70.select_heldout(records):raise RuntimeError("G89_RANK_CONTRACT_DRIFT")
        if len({x["source_row"] for x in ranked})!=OFFSET+CASES:raise RuntimeError("G89_DUPLICATE_RANK")
        selected=ranked[OFFSET:OFFSET+CASES]
        receipt["selected"]=[{k:v for k,v in x.items() if k!="instruction"} for x in selected]
        receipt["selected_ranks"]=[OFFSET,OFFSET+CASES-1]
        g55=module("g89_g55","llm_g55/g55_gpt2_controls.py")
        if (g55.REV,g55.WEIGHT_SHA)!=(MODEL_REV,WEIGHTS_SHA):raise RuntimeError("G89_MODEL_IDENTITY_DRIFT")
        stage_start=time.perf_counter();root,manifest=g55.stage()
        receipt["model_manifest_sha256"]=sha_file(root/"manifest.json");receipt["model_files"]=manifest
        tok=AutoTokenizer.from_pretrained(str(root),local_files_only=True,trust_remote_code=False)
        original=AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,use_safetensors=True,trust_remote_code=False).eval()
        candidate=AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,use_safetensors=True,trust_remote_code=False).eval()
        ep=list(original.parameters());cp=list(candidate.parameters())
        if len(ep)!=len(cp) or any(not torch.equal(a,b) for a,b in zip(ep,cp)):raise RuntimeError("G89_ORIGINAL_WEIGHT_PARITY_FAILURE")
        if not hasattr(proc,"cpu_affinity"):raise RuntimeError("G89_AFFINITY_UNAVAILABLE")
        old_aff=proc.cpu_affinity()
        if len(old_aff)<CPU_BUDGET:raise RuntimeError("G89_THREE_CPU_AFFINITY_UNAVAILABLE")
        proc.cpu_affinity(old_aff[:CPU_BUDGET]);receipt["fixed_affinity"]=proc.cpu_affinity()
        receipt["fixed_torch_interop"]=torch.get_num_interop_threads()
        conv_start=time.perf_counter()
        conversions=convert_conv1d_to_linear(candidate,torch)
        receipt["conv1d_conversion_count"]=len(conversions)
        if len(conversions)!=int(candidate.config.n_layer)*4:raise RuntimeError("G89_UNEXPECTED_GPT2_CONV1D_COUNT")
        from torch.utils.mkldnn import to_mkldnn
        prepacked=to_mkldnn(candidate,dtype=torch.float32).eval()
        conversion_seconds=time.perf_counter()-conv_start
        receipt["converted_projection_inventory"]=conversions
        receipt["conversion_and_prepack_seconds"]=conversion_seconds
        def ids(s):return tok(s,return_tensors="pt",add_special_tokens=False)["input_ids"]
        inputs=[]
        for item in selected:
            full=torch.cat((ids(g55.PREFIX),ids(item["instruction"])[:,:64]),dim=1)
            if full.shape[1]+TOKENS>original.config.n_positions:raise RuntimeError("G89_CONTEXT_OVERFLOW")
            inputs.append((item["source_row"],full))
        def decode(model,full):
            torch.backends.mkldnn.enabled=True
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
        # Actual operator proof must be on the authentic original prompt tensor.
        backend_proof=profile_linear_dispatch(prepacked,torch,inputs[0][1])
        baseline_proof=profile_linear_dispatch(original,torch,inputs[0][1])
        receipt["backend_dispatch_evidence"]={"candidate":backend_proof,"baseline":baseline_proof}
        if backend_proof["mkldnn_linear_calls"]<=0:raise RuntimeError("G89_CANDIDATE_MKLDNN_LINEAR_NOT_DISPATCHED")
        if baseline_proof["mkldnn_linear_calls"]!=0:raise RuntimeError("G89_BASELINE_MKLDNN_LINEAR_DISPATCHED")
        # Verify exactness before timing; no mismatched output is counted.
        for i,(row,full) in enumerate(inputs):
            a,_=decode(original,full);b,_=decode(prepacked,full)
            if a!=b:raise RuntimeError("G89_WARMUP_EXACTNESS_FAILURE_"+str(i))
        measured=[]
        for i,(row,full) in enumerate(inputs):
            reference,_=decode(original,full)
            for rep in range(REPEATS):
                measures={}
                for arm in schedule(i,rep):
                    model=original if arm=="original_conv1d2" else prepacked
                    result,timing=decode(model,full)
                    if result!=reference:raise RuntimeError("G89_EXACT_TOKEN_MISMATCH_"+arm+"_"+str(i))
                    measures[arm]=timing
                measured.append({"sample_index":i,"source_row":row,"rep":rep+1,
                  "order":schedule(i,rep),"original_input_token_count":int(full.shape[1]),
                  "original_input_sha256":hashlib.sha256(full.numpy().tobytes()).hexdigest(),
                  "measure":measures})
        arms,summary,decision=decide(measured,conversion_seconds)
        receipt["original_paired_trials"]=measured;receipt["arm_summaries"]=arms
        receipt["summary"]=summary;receipt["engineering"]="PASS";receipt["correctness"]="PASS";receipt["decision"]=decision
    except BaseException as exc:
        receipt["error"]=type(exc).__name__+": "+str(exc);receipt["traceback_tail"]=traceback.format_exc()[-2500:]
        raise
    finally:
        if old_aff is not None:
            receipt["cpu_affinity_at_end"]=proc.cpu_affinity();proc.cpu_affinity(old_aff)
        Path("cpu_g89_original_result.json").write_text(json.dumps(receipt,sort_keys=True,indent=2,default=str)+"\n",encoding="utf-8")
        print(json.dumps({k:receipt.get(k) for k in ("gate","engineering","correctness","decision","backend_dispatch_evidence","summary","error")},sort_keys=True),flush=True)

if __name__=="__main__":main()
