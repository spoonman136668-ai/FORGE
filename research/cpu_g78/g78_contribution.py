#!/usr/bin/env python3
"""CPU G78 original GPT-2 selective FFN contribution survey; NOT accelerated inference."""
import hashlib,importlib.util,json,math,os,platform,statistics,time,traceback,urllib.request
from pathlib import Path

PREREG="f00c272eeda7311a42a18c9fe4c5bec46f8aa9e3"
MODEL_REV="607a30d783dfa663caf39e06633721c8d4cfcd7e"
WEIGHTS_SHA="248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
DATA_REV="3101c7d5072418e28b9008a6636bde82a006892c"
DATA_SHA="3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14"
SEED=b"G68-GPT2-HELDOUT-20261030:"
DATA_BYTES=749738
OFFSET=96;CASES=12;STEPS=8;LAYERS=12;WIDTH=3072;OUT=768;KEEP=1536;CPUS=3
FROZEN={"median_l2_error_max":0.010,"p95_l2_error_max":0.030,
        "each_layer_median_l2_max":0.020,"worst_coordinate_abs_max":0.15}

def contract():
    assert (OFFSET,CASES,STEPS,LAYERS,WIDTH,OUT,KEEP,CPUS)==(96,12,8,12,3072,768,1536,3)
    assert FROZEN=={"median_l2_error_max":0.010,"p95_l2_error_max":0.030,
        "each_layer_median_l2_max":0.020,"worst_coordinate_abs_max":0.15}

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()

def module(name,path):
    p=Path(__file__).resolve().parents[1]/path
    sp=importlib.util.spec_from_file_location(name,p)
    x=importlib.util.module_from_spec(sp)
    sp.loader.exec_module(x)
    return x

def rank_human(records,n):
    x=[]
    for row,v in enumerate(records):
        q=v.get("instruction","")
        c=v.get("category","")
        if isinstance(q,str) and q.strip() and isinstance(c,str) and c.strip():
            x.append((hashlib.sha256(SEED+q.encode()).hexdigest(),row,q,c))
    x.sort(key=lambda v:(v[0],v[1]))
    seen=set();out=[]
    for digest,row,q,c in x:
        if q in seen:continue
        seen.add(q)
        out.append({"source_row":row,"instruction":q,"category":c,
           "instruction_sha256":hashlib.sha256(q.encode()).hexdigest(),"rank_sha256":digest})
        if len(out)==n:break
    if len(out)!=n:raise RuntimeError("G78_INSUFFICIENT_ORIGINAL_HUMAN_HELDOUT")
    return out

def p95(v):
    return sorted(v)[max(0,math.ceil(len(v)*.95)-1)]

def pick(mask_input,weight_norm,torch):
    if (mask_input.ndim!=1 or tuple(mask_input.shape)!=(WIDTH,)
        or weight_norm.ndim!=1 or tuple(weight_norm.shape)!=(WIDTH,)
        or not bool(torch.isfinite(mask_input).all())
        or not bool(torch.isfinite(weight_norm).all())):
        raise RuntimeError("G78_INVALID_ORIGINAL_ACTIVATION_OR_NORM")
    importance=mask_input.abs()*weight_norm
    indexes=torch.argsort(importance,descending=True,stable=True)[:KEEP]
    out=torch.zeros_like(mask_input)
    out[indexes]=mask_input[indexes]
    if len(indexes)!=KEEP or len(set(indexes.tolist()))!=KEEP:
        raise RuntimeError("G78_EXACT_KEEP_IDENTITY_FAILED")
    return out,indexes,importance

def projected_error(a,mlp,weight_norm,torch):
    if a.dtype!=torch.float32 or tuple(a.shape)!=(WIDTH,) or not bool(torch.isfinite(a).all()):
        raise RuntimeError("G78_INVALID_NATIVE_FFN_INPUT")
    w=mlp.c_proj.weight
    b=mlp.c_proj.bias
    if tuple(w.shape)!=(WIDTH,OUT) or tuple(b.shape)!=(OUT,) or w.dtype!=torch.float32:
        raise RuntimeError("G78_ORIGINAL_PROJECTION_SHAPE_DRIFT")
    start=time.perf_counter_ns();cpu0=time.process_time_ns()
    baseline=mlp.c_proj(a.unsqueeze(0))[0]
    masked,ids,importance=pick(a,weight_norm,torch)
    masked_out=mlp.c_proj(masked.unsqueeze(0))[0]
    wall_ns=time.perf_counter_ns()-start
    cpu_ns=time.process_time_ns()-cpu0
    difference=baseline-masked_out
    if not (bool(torch.isfinite(baseline).all()) and bool(torch.isfinite(masked_out).all())
            and bool(torch.isfinite(difference).all())):
        raise RuntimeError("G78_NONFINITE_ORIGINAL_PROJECTED_ERROR")
    base_norm=float(torch.linalg.vector_norm(baseline).item())
    error_norm=float(torch.linalg.vector_norm(difference).item())
    max_abs=float(difference.abs().max().item())
    if any(not math.isfinite(x) for x in (base_norm,error_norm,max_abs)):
        raise RuntimeError("G78_ERROR_METRIC_NONFINITE")
    return {"original_activation_sha256":hashlib.sha256(a.numpy().tobytes()).hexdigest(),
            "relative_l2_error":error_norm/max(base_norm,1e-8),
            "max_coordinate_abs_difference":max_abs,
            "retained_channels":len(ids),"masked_channels":WIDTH-len(ids),
            "maximum_importance":float(importance.max().item()),
            "selection_and_dense_projection_wall_ns":wall_ns,
            "selection_and_dense_projection_cpu_ns":cpu_ns}

def main():
    import psutil,torch,transformers
    from transformers import AutoTokenizer,AutoModelForCausalLM
    contract();torch.set_num_threads(1);torch.set_num_interop_threads(1)
    proc=psutil.Process();old_aff=None;handles=[]
    receipt={"schema":"forge.cpu-g78.original-gpt2-ffn-contribution.v1",
       "gate":"CPU_G78","preregistration_commit":PREREG,
       "source_sha":os.getenv("GITHUB_SHA","UNSET"),
       "model_revision":MODEL_REV,"model_weights_sha256":WEIGHTS_SHA,
       "dataset_revision":DATA_REV,"dataset_sha256":DATA_SHA,
       "runtime":{"torch":torch.__version__,"transformers":transformers.__version__,
                  "platform":platform.platform()},
       "engineering":"UNVERIFIED","feasibility":"UNVERIFIED",
       "performance":"NOT_MEASURED","masked_model_token_parity":"NOT_TESTED",
       "scientific_acceptance":"NOT_GRANTED","promotion_allowed":False,
       "caveats":["Original GPT-2 activations and original dense c_proj, but not a sparse compute engine",
        "Importances require all original FFN activations; selection overhead cannot be ignored",
        "Masking is approximate and changing FP32 values, no downstream token parity tested",
        "No end-to-end latency gain, GPU inference, scientific or model promotion claimed",
        "One Linux CPU original-model host, sampled RSS not true peak",
        "Heldout original GSM8K disjoint questions, same source family"]}
    try:
        url="https://raw.githubusercontent.com/openai/grade-school-math/"+DATA_REV+"/grade_school_math/data/test.jsonl"
        raw=Path("cpu_g78_gsm8k_original.jsonl")
        req=urllib.request.Request(url,headers={"User-Agent":"FORGE-CPU-G78-Original-Contribution/1"})
        with urllib.request.urlopen(req,timeout=45) as src,raw.open("xb") as dst:
            total=0
            while True:
                part=src.read(1<<20)
                if not part:break
                total+=len(part)
                if total>800000:raise RuntimeError("G78_ORIGINAL_SOURCE_SIZE_CAP")
                dst.write(part)
        if raw.stat().st_size!=DATA_BYTES or sha(raw)!=DATA_SHA:
            raise RuntimeError("G78_ORIGINAL_DATA_SHA_DRIFT")
        with raw.open(encoding="utf-8") as f:
            records=[{"instruction":z["question"],"category":"math_word_problem"}
                 for z in (json.loads(line) for line in f if line.strip())]
        ranked=rank_human(records,OFFSET+CASES)
        g68=module("g78_g68","llm_g68/g68_gsm8k_http.py")
        g70=module("g78_g70","llm_g70/g70_gsm8k_locality.py")
        if (ranked[:12]!=g68.select_heldout(records) or
            ranked[12:24]!=g70.select_heldout(records) or
            len({x["source_row"] for x in ranked})!=OFFSET+CASES):
            raise RuntimeError("G78_FIRST_USE_DISJOINT_RANK_DRIFT")
        chosen=ranked[OFFSET:OFFSET+CASES]
        receipt["heldout_ranks"]=[OFFSET,OFFSET+CASES-1]
        receipt["heldout"]=[{k:v for k,v in x.items() if k!="instruction"} for x in chosen]
        g55=module("g78_g55","llm_g55/g55_gpt2_controls.py")
        if (g55.REV,g55.WEIGHT_SHA)!=(MODEL_REV,WEIGHTS_SHA):
            raise RuntimeError("G78_FROZEN_G55_MODEL_IDENTITY")
        stage0=time.perf_counter();root,files=g55.stage()
        receipt["model_stage_s"]=time.perf_counter()-stage0
        receipt["original_manifest_sha256"]=sha(root/"manifest.json")
        receipt["files"]=files
        tokenizer=AutoTokenizer.from_pretrained(str(root),local_files_only=True,trust_remote_code=False)
        model=AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,
                    use_safetensors=True,trust_remote_code=False).eval()
        if model.config.model_type!="gpt2" or next(model.parameters()).dtype!=torch.float32:
            raise RuntimeError("G78_MODEL_TYPE_OR_DTYPE_DRIFT")
        if not hasattr(proc,"cpu_affinity"):raise RuntimeError("G78_NO_CPU_AFFINITY")
        old_aff=proc.cpu_affinity()
        if len(old_aff)<CPUS:raise RuntimeError("G78_CPU_BUDGET_UNAVAILABLE")
        proc.cpu_affinity(old_aff[:CPUS]);receipt["fixed_affinity"]=proc.cpu_affinity()
        t0=time.perf_counter()
        with torch.inference_mode():
            norms=[torch.linalg.vector_norm(model.transformer.h[i].mlp.c_proj.weight,dim=1)
                   for i in range(LAYERS)]
        receipt["norm_precompute_s"]=time.perf_counter()-t0
        receipt["norm_logical_bytes"]=sum(x.numel()*x.element_size() for x in norms)
        if any(tuple(n.shape)!=(WIDTH,) or not bool(torch.isfinite(n).all()) for n in norms):
            raise RuntimeError("G78_BAD_ORIGINAL_NORMS")
        def ids(s):return tokenizer(s,return_tensors="pt",add_special_tokens=False)["input_ids"]
        with torch.inference_mode():
            model(input_ids=ids("A public nonheldout warmup prompt."),use_cache=True)
        bucket=None
        def hook(layer):
            def capture(_module,_args,value):
                if bucket is None or layer in bucket:raise RuntimeError("G78_UNEXPECTED_DUPLICATE_ACTIVATION")
                if not isinstance(value,torch.Tensor) or value.ndim!=3 or value.shape[0]!=1:
                    raise RuntimeError("G78_NATIVE_GELU_SHAPE_INVALID")
                original=value[0,-1,:].detach().clone()
                if original.dtype!=torch.float32 or original.shape!=(WIDTH,):
                    raise RuntimeError("G78_NATIVE_FLOAT32_WIDTH_INVALID")
                bucket[layer]=original
            return capture
        for layer in range(LAYERS):
            handles.append(model.transformer.h[layer].mlp.act.register_forward_hook(hook(layer)))
        if len(handles)!=LAYERS:raise RuntimeError("G78_NATIVE_HOOK_COUNT")
        records_out=[];token_outputs=[]
        collect_t0=time.perf_counter()
        with torch.inference_mode():
            for case in chosen:
                full=torch.cat((ids(g55.PREFIX),ids(case["instruction"])[:,:64]),dim=1)
                if full.shape[1]+STEPS>model.config.n_positions:
                    raise RuntimeError("G78_ORIGINAL_CONTEXT_OVERFLOW")
                current=full;past=None;tokens=[]
                for step in range(STEPS):
                    bucket={}
                    out=model(input_ids=current,past_key_values=past,use_cache=True)
                    if set(bucket)!=set(range(LAYERS)):
                        raise RuntimeError("G78_MISSING_NATIVE_ACTIVATION_LAYER")
                    token=int(out.logits[0,-1,:].argmax().item());tokens.append(token)
                    for layer in range(LAYERS):
                        m=model.transformer.h[layer].mlp
                        result=projected_error(bucket[layer],m,norms[layer],torch)
                        records_out.append({"source_row":case["source_row"],"step":step,"layer":layer,**result})
                    past=out.past_key_values
                    current=torch.tensor([[token]],dtype=torch.long)
                token_outputs.append({"source_row":case["source_row"],
                    "input_sha256":hashlib.sha256(full.numpy().tobytes()).hexdigest(),
                    "original_greedy_token_sha256":hashlib.sha256(json.dumps(tokens,separators=(",",":")).encode()).hexdigest()})
        receipt["collection_wall_s"]=time.perf_counter()-collect_t0
        receipt["sampled_process_rss_bytes"]=proc.memory_info().rss
        if len(records_out)!=CASES*STEPS*LAYERS or len(token_outputs)!=CASES:
            raise RuntimeError("G78_ORIGINAL_CPROJ_SAMPLE_COUNT_DRIFT")
        per_layer=[]
        for layer in range(LAYERS):
            samples=[z for z in records_out if z["layer"]==layer]
            if len(samples)!=CASES*STEPS:raise RuntimeError("G78_ORIGINAL_LAYER_COUNT_DRIFT")
            per_layer.append({"layer":layer,"pairs":len(samples),
                 "median_relative_l2_error":statistics.median(z["relative_l2_error"] for z in samples),
                 "p95_relative_l2_error":p95([z["relative_l2_error"] for z in samples]),
                 "worst_coordinate_abs_difference":max(z["max_coordinate_abs_difference"] for z in samples)})
        errors=[z["relative_l2_error"] for z in records_out]
        median=statistics.median(errors);p95err=p95(errors)
        layer_worst_median=max(x["median_relative_l2_error"] for x in per_layer)
        worst=max(z["max_coordinate_abs_difference"] for z in records_out)
        receipt["measurements"]=records_out
        receipt["per_layer"]=per_layer
        receipt["original_tokens"]=token_outputs
        receipt["summary"]={"original_token_positions":CASES*STEPS,
           "original_activation_pairs":len(records_out),
           "retained_per_vector":KEEP,"masked_per_vector":WIDTH-KEEP,
           "median_relative_l2_error":median,
           "p95_relative_l2_error":p95err,
           "largest_layer_median_relative_l2_error":layer_worst_median,
           "worst_coordinate_abs_difference":worst}
        receipt["engineering"]="PASS"
        receipt["feasibility"]="GO_FOR_SEPARATE_ORIGINAL_SPARSE_ENGINE" if (
            median<=FROZEN["median_l2_error_max"] and
            p95err<=FROZEN["p95_l2_error_max"] and
            layer_worst_median<=FROZEN["each_layer_median_l2_max"] and
            worst<=FROZEN["worst_coordinate_abs_max"]) else "NO_GO_FEASIBILITY"
    except BaseException as exc:
        receipt["error"]=type(exc).__name__+": "+str(exc)
        receipt["traceback_tail"]=traceback.format_exc()[-2400:]
        raise
    finally:
        for h in handles:h.remove()
        if old_aff is not None:
            receipt["affinity_end"]=proc.cpu_affinity();proc.cpu_affinity(old_aff)
        Path("cpu_g78_original_result.json").write_text(
             json.dumps(receipt,sort_keys=True,indent=2,default=str)+"\n",encoding="utf-8")
        print(json.dumps({k:receipt.get(k) for k in ("gate","engineering","feasibility","summary","error")},sort_keys=True),flush=True)
if __name__=="__main__":main()
