#!/usr/bin/env python3
"""CPU G77 original GPT2 FFN exact-zero opportunity screen; no sparse model replacement."""
import hashlib,importlib.util,json,os,platform,statistics,time,traceback,urllib.request
from pathlib import Path

PREREG="da9b9dc83be89e0bb274ad36afea73faabaa8901"
MODEL_REV="607a30d783dfa663caf39e06633721c8d4cfcd7e"
WEIGHTS_SHA="248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
DATA_REV="3101c7d5072418e28b9008a6636bde82a006892c"
DATA_SHA="3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14"
DATA_BYTES=749738
SEED=b"G68-GPT2-HELDOUT-20261030:"
HELDOUT_START=84;CASES=12;STEPS=8;LAYERS=12;MLP_WIDTH=3072;CPU_BUDGET=3
FREEZE={"median_exact_zero":0.20,"min_layer_exact_zero":0.05,"max_zero_free_positions":0.10}

def contract():
    assert (HELDOUT_START,CASES,STEPS,LAYERS,MLP_WIDTH,CPU_BUDGET)==(84,12,8,12,3072,3)
    assert FREEZE=={"median_exact_zero":0.20,"min_layer_exact_zero":0.05,"max_zero_free_positions":0.10}

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()

def module(name,relative):
    path=Path(__file__).resolve().parents[1]/relative
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def rank_human(records,n):
    a=[]
    for row,record in enumerate(records):
        q=record.get("instruction","")
        c=record.get("category","")
        if isinstance(q,str) and q.strip() and isinstance(c,str) and c.strip():
            a.append((hashlib.sha256(SEED+q.encode()).hexdigest(),row,q,c))
    a.sort(key=lambda x:(x[0],x[1]))
    seen=set();chosen=[]
    for rank,row,q,c in a:
        if q in seen:continue
        seen.add(q)
        chosen.append({"source_row":row,"instruction":q,"category":c,
             "instruction_sha256":hashlib.sha256(q.encode()).hexdigest(),"rank_sha256":rank})
        if len(chosen)==n:break
    if len(chosen)!=n:raise RuntimeError("G77_INSUFFICIENT_AUTHENTIC_ORIGINAL_QUESTIONS")
    return chosen

def zero_counts(x,torch):
    if x.dtype!=torch.float32 or tuple(x.shape)!=(MLP_WIDTH,) or not bool(torch.isfinite(x).all()):
        raise RuntimeError("G77_INVALID_ORIGINAL_GELU_ACTIVATION")
    exact=int(torch.count_nonzero(x==0.0).item())
    near6=int(torch.count_nonzero(x.abs()<1e-6).item())
    near4=int(torch.count_nonzero(x.abs()<1e-4).item())
    positive=int(torch.count_nonzero(x>0).item())
    negative=int(torch.count_nonzero(x<0).item())
    if not 0<=exact<=near6<=near4<=MLP_WIDTH or exact+positive+negative!=MLP_WIDTH:
        raise RuntimeError("G77_INCONSISTENT_ZERO_OR_SIGN_COUNT")
    return {"zero":exact,"near_1e6":near6,"near_1e4":near4,
            "positive":positive,"negative":negative,"total":MLP_WIDTH}

def main():
    import torch,psutil,transformers
    from transformers import AutoTokenizer,AutoModelForCausalLM
    contract();torch.set_num_threads(1);torch.set_num_interop_threads(1)
    proc=psutil.Process();original_affinity=None
    receipt={"schema":"forge.cpu-g77.original-gpt2-ffn-exactzero.v1",
      "gate":"CPU_G77","preregistration_commit":PREREG,"source_sha":os.getenv("GITHUB_SHA","UNSET"),
      "model_revision":MODEL_REV,"original_weights_sha256":WEIGHTS_SHA,
      "dataset_revision":DATA_REV,"dataset_sha256":DATA_SHA,
      "model_executed":False,"scientific_acceptance":"NOT_GRANTED",
      "promotion_allowed":False,"exact_token_correctness":"ORIGINAL_ONLY_NO_SPARSE_COMPARISON",
      "performance":"NOT_MEASURED","engineering":"UNVERIFIED","feasibility":"UNVERIFIED",
      "runtime":{"torch":torch.__version__,"transformers":transformers.__version__,
                 "python":platform.python_version(),"platform":platform.platform()},
      "limitations":["Survey of exact FFN GELU zeros, not an implemented sparse alternative",
         "No saved time, exact downstream token parity for sparsified model or energy evidence",
         "Rounding/reduction order may change on any future sparse kernel",
         "Original MIT GSM8K heldout disjoint rows in same source family",
         "One original Linux CPU host; sampled RSS is not physical peak",
         "No GPU ACC, model acceptance or FORGE production/promotion"]}
    handles=[]
    try:
        raw=Path("cpu_g77_original_gsm8k.jsonl")
        url="https://raw.githubusercontent.com/openai/grade-school-math/"+DATA_REV+"/grade_school_math/data/test.jsonl"
        req=urllib.request.Request(url,headers={"User-Agent":"FORGE-CPU-G77-Original-GPT2-FFN/1"})
        with urllib.request.urlopen(req,timeout=45) as src,raw.open("xb") as dst:
            n=0
            while True:
                b=src.read(1<<20)
                if not b:break
                n+=len(b)
                if n>800000:raise RuntimeError("G77_DATASET_SIZE_CAP")
                dst.write(b)
        if raw.stat().st_size!=DATA_BYTES or sha256_file(raw)!=DATA_SHA:
            raise RuntimeError("G77_ORIGINAL_DATASET_SOURCE_MISMATCH")
        with raw.open(encoding="utf-8") as f:
            rows=[{"instruction":o["question"],"category":"math_word_problem"}
                  for o in (json.loads(line) for line in f if line.strip())]
        rank=rank_human(rows,HELDOUT_START+CASES)
        g68=module("g77_g68","llm_g68/g68_gsm8k_http.py")
        g70=module("g77_g70","llm_g70/g70_gsm8k_locality.py")
        if rank[:12]!=g68.select_heldout(rows) or rank[12:24]!=g70.select_heldout(rows):
            raise RuntimeError("G77_ORIGINAL_DISJOINT_RANK_DRIFT")
        selected=rank[HELDOUT_START:HELDOUT_START+CASES]
        if len({x["source_row"] for x in rank})!=HELDOUT_START+CASES:
            raise RuntimeError("G77_ORIGINAL_RANK_NONUNIQUE")
        receipt["heldout"]=[{k:v for k,v in x.items() if k!="instruction"} for x in selected]
        receipt["heldout_ranks"]=[HELDOUT_START,HELDOUT_START+CASES-1]
        g55=module("g77_g55","llm_g55/g55_gpt2_controls.py")
        if (g55.REV,g55.WEIGHT_SHA)!=(MODEL_REV,WEIGHTS_SHA):
            raise RuntimeError("G77_MODEL_SHA_REVISION_DRIFT")
        t0=time.perf_counter();root,manifest=g55.stage()
        receipt["original_staging_s"]=time.perf_counter()-t0
        receipt["staged_manifest_sha256"]=sha256_file(root/"manifest.json")
        receipt["staged_files"]=manifest
        tokenizer=AutoTokenizer.from_pretrained(str(root),trust_remote_code=False,local_files_only=True)
        model=AutoModelForCausalLM.from_pretrained(str(root),trust_remote_code=False,
                 local_files_only=True,use_safetensors=True).eval()
        if model.config.model_type!="gpt2" or next(model.parameters()).dtype!=torch.float32:
            raise RuntimeError("G77_UNEXPECTED_ORIGINAL_FP32_MODEL")
        if not hasattr(proc,"cpu_affinity"):raise RuntimeError("G77_UNAVAILABLE_CPU_AFFINITY")
        original_affinity=proc.cpu_affinity()
        if len(original_affinity)<CPU_BUDGET:raise RuntimeError("G77_INSUFFICIENT_CPUS")
        proc.cpu_affinity(original_affinity[:CPU_BUDGET])
        receipt["fixed_affinity"]=proc.cpu_affinity()
        def ids(s):return tokenizer(s,return_tensors="pt",add_special_tokens=False)["input_ids"]
        with torch.inference_mode():
            public=ids("A public nonheldout original model warmup.")
            model(input_ids=public,use_cache=True)
        # One bucket per original model forward, one last-token exact activation per layer.
        bucket=None;counts=[];original_tokens=[]
        def hook(layer):
            def capture(_module,_args,output):
                if bucket is None:raise RuntimeError("G77_ACTIVATION_OUTSIDE_ORIGINAL_FORWARD")
                if layer in bucket:raise RuntimeError("G77_DOUBLE_LAYER_HOOK")
                if not isinstance(output,torch.Tensor) or output.ndim!=3 or output.shape[0]!=1:
                    raise RuntimeError("G77_NATIVE_GELU_OUTPUT_SHAPE")
                bucket[layer]=zero_counts(output[0,-1,:],torch)
            return capture
        for layer in range(LAYERS):
            act=model.transformer.h[layer].mlp.act
            if not hasattr(act,"register_forward_hook"):
                raise RuntimeError("G77_NO_NATIVE_ACTIVATION_HOOK_"+str(layer))
            handles.append(act.register_forward_hook(hook(layer)))
        if len(handles)!=LAYERS:raise RuntimeError("G77_MISSING_NATIVE_LAYER_HOOKS")
        start=time.perf_counter()
        with torch.inference_mode():
            for item in selected:
                full=torch.cat((ids(g55.PREFIX),ids(item["instruction"])[:,:64]),dim=1)
                if full.shape[1]+STEPS>model.config.n_positions:
                    raise RuntimeError("G77_CONTEXT_EXCEEDS_PRETRAINED_MODEL")
                current=full;past=None;generated=[]
                for step in range(STEPS):
                    bucket={}
                    out=model(input_ids=current,past_key_values=past,use_cache=True)
                    if set(bucket)!=set(range(LAYERS)):
                        raise RuntimeError("G77_ORIGINAL_LAYER_HOOK_SET_INCOMPLETE")
                    if any(bucket[x]["total"]!=MLP_WIDTH for x in bucket):
                        raise RuntimeError("G77_ORIGINAL_ACTIVATION_DIM_DRIFT")
                    token=int(out.logits[0,-1,:].argmax().item())
                    generated.append(token)
                    for layer in range(LAYERS):
                        counts.append({"source_row":item["source_row"],"step":step,
                                       "layer":layer,**bucket[layer]})
                    past=out.past_key_values
                    current=torch.tensor([[token]],dtype=torch.long)
                original_tokens.append({
                  "source_row":item["source_row"],
                  "input_sha256":hashlib.sha256(full.numpy().tobytes()).hexdigest(),
                  "original_greedy_token_sha256":hashlib.sha256(json.dumps(generated,separators=(",",":")).encode()).hexdigest()})
        receipt["original_collection_wall_s"]=time.perf_counter()-start
        receipt["original_model_rss_sample_bytes"]=proc.memory_info().rss
        receipt["model_executed"]=True
        if len(counts)!=LAYERS*CASES*STEPS or len(original_tokens)!=CASES:
            raise RuntimeError("G77_INCOMPLETE_ORIGINAL_ACTIVATION_COVERAGE")
        layers=[]
        for layer in range(LAYERS):
            entries=[x for x in counts if x["layer"]==layer]
            if len(entries)!=CASES*STEPS:raise RuntimeError("G77_WRONG_LAYER_POSITION_COUNT")
            layers.append({"layer":layer,"original_positions":len(entries),
               "exact_zero":sum(x["zero"] for x in entries),
               "near_1e6":sum(x["near_1e6"] for x in entries),
               "near_1e4":sum(x["near_1e4"] for x in entries),
               "element_total":len(entries)*MLP_WIDTH,
               "exact_zero_fraction":sum(x["zero"] for x in entries)/(len(entries)*MLP_WIDTH)})
        median_zero=statistics.median(x["zero"]/MLP_WIDTH for x in counts)
        min_layer=min(x["exact_zero_fraction"] for x in layers)
        free_frac=sum(x["zero"]==0 for x in counts)/len(counts)
        receipt["original_tokens"]=original_tokens
        receipt["original_activation_counts"]=counts
        receipt["per_layer"]=layers
        receipt["summary"]={"authentic_positions":CASES*STEPS,
          "original_gelu_activation_vectors":len(counts),"n_layers":LAYERS,
          "original_float32_elements_counted":len(counts)*MLP_WIDTH,
          "median_exact_zero_fraction":median_zero,
          "min_layer_exact_zero_fraction":min_layer,
          "zero_free_position_fraction":free_frac,
          "mean_exact_zero_fraction":sum(x["zero"] for x in counts)/(len(counts)*MLP_WIDTH)}
        receipt["engineering"]="PASS"
        receipt["feasibility"]="GO_FOR_FUTURE_SEPARATE_ORIGINAL_SPARSE_TEST" if (
            median_zero>=FREEZE["median_exact_zero"] and
            min_layer>=FREEZE["min_layer_exact_zero"] and
            free_frac<=FREEZE["max_zero_free_positions"]) else "NO_GO_FEASIBILITY"
    except BaseException as exc:
        receipt["error"]=type(exc).__name__+": "+str(exc)
        receipt["traceback_tail"]=traceback.format_exc()[-2500:]
        raise
    finally:
        for h in handles:h.remove()
        if original_affinity is not None:
            receipt["affinity_end"]=proc.cpu_affinity()
            proc.cpu_affinity(original_affinity)
        Path("cpu_g77_original_result.json").write_text(
          json.dumps(receipt,sort_keys=True,indent=2,default=str)+"\n",encoding="utf-8")
        print(json.dumps({k:receipt.get(k) for k in
          ("gate","engineering","feasibility","summary","error")},sort_keys=True),flush=True)
if __name__=="__main__":main()
