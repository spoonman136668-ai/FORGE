#!/usr/bin/env python3
"""G65: source-identical real GPU FP16 cached vs chunked vs full attention logits.

No G63 admission reversal, no acceleration or root-cause claim.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import platform
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"acc_g64"))
import g64_token_forensics as g64
original=g64.original

G64_GIT_BLOB="9a9b8e3507698bc7abc40b6ec636ed2822354a96"
G64_PROMPT_HASH="19a85c78f14d5470d79d51c83a25d69a9b54953eb0024d223e82e34376529c59"
BASELINE_SHA="50a1ab137948f57c8c4f06e92ca3900770b0abd01b0e0a531df560315f746d88"
CANDIDATE_SHA="d4e72f3fbdf4b267bf167cce321fd61d4066423ab088ae406f8d20bccf49d01e"
BASELINE_ID=7866
CANDIDATE_ID=29871
POSITION=48
SHARED_TOKENS=48
REPEATS=3
MODES=("cached_one_by_one","cached_chunk_48","full_no_cache")
OUTPUT=Path(os.getenv("G65_OUTPUT","g65_result.json"))
CORPUS_PATH=Path(os.getenv("G65_CORPUS_PATH","g65_wikitext_test.txt"))

def identity():
    if g64.git_blob(Path(g64.__file__).read_bytes())!=G64_GIT_BLOB:
        raise RuntimeError("ORIGINAL_G64_FORENSIC_SOURCE_DRIFT")
    proof=g64.pinned_source_assertions()
    if (g64.ANCHOR,g64.TASK,g64.CONTEXT,g64.NEW_TOKENS,g64.PAIRS)!=(2,"natural_continuation",1536,64,5):
        raise RuntimeError("ORIGINAL_G64_FAILURE_CASE_DRIFT")
    return {"g64_source_git_blob":G64_GIT_BLOB,**proof}

def token_sha(ids):
    return hashlib.sha256(json.dumps(ids).encode("utf-8")).hexdigest()

def summarize_logits(logits):
    import torch
    z=logits.detach().float()
    values,idx=torch.topk(z,k=2)
    first=int(idx[0]);second=int(idx[1])
    a=float(z[BASELINE_ID]);b=float(z[CANDIDATE_ID])
    return {"top1_id":first,"top2_id":second,
            "top1_logit":float(values[0]),"top2_logit":float(values[1]),
            "top1_top2_margin":float(values[0]-values[1]),
            "baseline_token_id":BASELINE_ID,"baseline_logit":a,
            "candidate_token_id":CANDIDATE_ID,"candidate_logit":b,
            "candidate_minus_baseline_logit":b-a,
            "logit_storage_dtype":str(logits.dtype)}

def validate_orig_outputs(model,prompt,tokenizer):
    import torch
    outputs={}
    kwargs=dict(input_ids=prompt,do_sample=False,num_beams=1,
      use_cache=True,max_new_tokens=64,eos_token_id=-1,
      pad_token_id=tokenizer.eos_token_id)
    for arm in ("baseline","candidate"):
        k=dict(kwargs)
        if arm=="candidate":
            k.update(prompt_lookup_num_tokens=5,max_matching_ngram_size=3)
        observed=model.generate(**k)
        torch.cuda.synchronize(prompt.device)
        raw_ids=observed[0,prompt.shape[1]:].detach().cpu().tolist()
        tokens,raw_count=g64.audited_continuation(raw_ids,arm)
        actual_hash=token_sha(tokens)
        expected=BASELINE_SHA if arm=="baseline" else CANDIDATE_SHA
        if actual_hash!=expected:
            raise RuntimeError(f"ORIGINAL_G64_{arm.upper()}_TOKEN_SHA_DRIFT")
        outputs[arm]={"hash":actual_hash,"raw_generated_tokens":raw_count,"first_64_token_ids":tokens}
    b=outputs["baseline"]["first_64_token_ids"]
    c=outputs["candidate"]["first_64_token_ids"]
    if b[:POSITION]!=c[:POSITION] or (b[POSITION],c[POSITION])!=(BASELINE_ID,CANDIDATE_ID):
        raise RuntimeError("ORIGINAL_G64_DISPUTED_TOKEN_DRIFT")
    return outputs

def logits_for_mode(model,prompt,shared,mode):
    import torch
    if mode=="full_no_cache":
        full=torch.cat((prompt,shared),dim=1)
        return model(input_ids=full,use_cache=False).logits[0,-1,:]
    out=model(input_ids=prompt,use_cache=True)
    state=out.past_key_values
    if mode=="cached_chunk_48":
        attention=torch.ones((1,prompt.shape[1]+shared.shape[1]),device=prompt.device,dtype=torch.long)
        return model(input_ids=shared,past_key_values=state,
                     attention_mask=attention,use_cache=True).logits[0,-1,:]
    if mode=="cached_one_by_one":
        logits=out.logits[0,-1,:]
        for i in range(SHARED_TOKENS):
            greedy=int(logits.argmax())
            observed=int(shared[0,i])
            if greedy!=observed:
                raise RuntimeError(f"ORIGINAL_CACHED_PREFIX_TOKEN_MISMATCH_AT_{i}:{greedy}:{observed}")
            attention=torch.ones((1,prompt.shape[1]+i+1),device=prompt.device,dtype=torch.long)
            token=shared[:,i:i+1]
            out=model(input_ids=token,past_key_values=state,
                      attention_mask=attention,use_cache=True)
            state=out.past_key_values
            logits=out.logits[0,-1,:]
        return logits
    raise ValueError("UNKNOWN_FROZEN_LOGIT_MODE")

def classify(rows):
    if set(rows)!=set(MODES) or any(len(rows[k])!=REPEATS for k in MODES):
        raise ValueError("THREE_REPEATS_PER_MODE_REQUIRED")
    cached=[x["top1_id"] for x in rows["cached_one_by_one"]]
    chunk=[x["top1_id"] for x in rows["cached_chunk_48"]]
    full=[x["top1_id"] for x in rows["full_no_cache"]]
    stable=all(len(set(y))==1 for y in (cached,chunk,full))
    split=all(x==BASELINE_ID for x in cached) and all(x==CANDIDATE_ID for x in full)
    return {"cached_full_argmax_split_reproduced":split,
      "all_three_modes_repeated_stably":stable,
      "cached_top1_ids":cached,"chunked_top1_ids":chunk,"full_top1_ids":full,
      "classification":("REPRODUCED_CACHED_FULL_ARGMAX_SPLIT" if split
        else "G64_NUMERICAL_PATH_OBSERVATION_DRIFT"),
      "fp16_shape_path_sensitivity_consistent_not_causal_proof":split}

def run():
    import torch
    import transformers
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer,AutoModelForCausalLM
    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32=False
    report={"schema":"forge.acc.g65.fp16-logit-path-v1",
      "gate":"ACC-G65","status":"UNVERIFIED",
      "git_head_sha":os.environ.get("GITHUB_SHA",""),
      "platform":platform.platform(),"torch":torch.__version__,
      "cuda_runtime":torch.version.cuda,"transformers":transformers.__version__,
      "original_g63_final":"FAIL_NO_GO_UNCHANGED",
      "original_g64_verdict":"5_OF_5_REPRODUCED",
      "source_revision":original.CORPUS_REV,"model_revision":original.REV,
      "novel_acceleration":False,"scientific_acceptance":"NOT_GRANTED",
      "causal_root_cause_conclusively_proven":False}
    try:
        report["original_helper_identities"]=identity()
        corpus=original.frozen_source(CORPUS_PATH)
        sourcehash=hashlib.sha256(corpus).hexdigest()
        if sourcehash!=g64.G63_CORPUS_SHA256:
            raise RuntimeError("ORIGINAL_WIKITEXT_SHA256_DRIFT")
        report["corpus_sha256"]=sourcehash
        if not torch.cuda.is_available() or not torch.version.cuda or tuple(map(int,torch.version.cuda.split(".")[:2]))<(12,8):
            raise RuntimeError("BLACKWELL_RUNTIME_NOT_QUALIFIED")
        dev=torch.device("cuda:0")
        name=torch.cuda.get_device_name(dev)
        cc=torch.cuda.get_device_capability(dev)
        free,total=torch.cuda.mem_get_info(dev)
        if cc!=(12,0) or "NVIDIA" not in name.upper() or free<7000*1024**2:
            raise RuntimeError("GPU_ADMISSION_NO_CPU_FALLBACK")
        x=torch.ones((1024,1024),device=dev)
        y=x@x
        torch.cuda.synchronize(dev)
        if y.device.type!="cuda" or abs(float(y[0,0])-1024)>1e-3:
            raise RuntimeError("REAL_CUDA_MATMUL_FAILED")
        del x,y
        torch.cuda.empty_cache()
        report["gpu"]={"name":name,"compute_capability":list(cc),
          "free_mib_before":free//1024**2,"total_mib":total//1024**2}
        snap=Path(snapshot_download(repo_id=original.REPO,revision=original.REV,
          token=False,allow_patterns=list(original.FILES)))
        weight=snap/"model.safetensors"
        if not weight.is_file() or weight.stat().st_size!=original.WEIGHT_SIZE or g64.file_sha256(weight)!=original.WEIGHT_SHA:
            raise RuntimeError("ORIGINAL_TINYLLAMA_WEIGHT_SHA_DRIFT")
        report["model_safetensors_sha256"]=g64.file_sha256(weight)
        tok=AutoTokenizer.from_pretrained(str(snap),use_fast=True,
             local_files_only=True,trust_remote_code=False)
        model=AutoModelForCausalLM.from_pretrained(str(snap),torch_dtype=torch.float16,
          attn_implementation="sdpa",use_safetensors=True,
          local_files_only=True,trust_remote_code=False).eval().to(dev)
        if model.config.model_type!="llama" or model.config.num_hidden_layers!=22 or model.config._attn_implementation!="sdpa":
            raise RuntimeError("ORIGINAL_SDPA_LLM_CONFIG_DRIFT")
        from torch.profiler import profile,ProfilerActivity
        with torch.inference_mode(),profile(activities=[ProfilerActivity.CPU]) as prof:
            model(input_ids=torch.tensor([[1,10,20,30]],device=dev),use_cache=True)
            torch.cuda.synchronize(dev)
        if "aten::scaled_dot_product_attention" not in [x.key for x in prof.key_averages()]:
            raise RuntimeError("REAL_SDPA_DISPATCH_NOT_FOUND")
        report["real_optimized_sdpa_proof"]="PASS"
        src_ids=original.frozen_sample_tokens(tok,corpus.decode("utf-8"),original.ANCHORS[2])
        prompt=original.case_ids(torch,tok,src_ids,"natural_continuation",1536).to(dev)
        ph=token_sha(prompt[0].detach().cpu().tolist())
        if ph!=G64_PROMPT_HASH:
            raise RuntimeError("ORIGINAL_G64_PROMPT_IDS_SHA_DRIFT")
        report["prompt_ids_sha256"]=ph
        with torch.inference_mode():
            outputs=validate_orig_outputs(model,prompt,tok)
            report["original_g64_output_revalidation"]={
                k:{"sha256":v["hash"],"raw_generated_tokens":v["raw_generated_tokens"]}
                for k,v in outputs.items()}
            base=outputs["baseline"]["first_64_token_ids"]
            shared=torch.tensor([base[:SHARED_TOKENS]],device=dev,dtype=torch.long)
            rows={m:[] for m in MODES}
            for rep in range(REPEATS):
                for mode in MODES:
                    logits=logits_for_mode(model,prompt,shared,mode)
                    torch.cuda.synchronize(dev)
                    obs=summarize_logits(logits)
                    obs["repeat_index"]=rep
                    obs["mode"]=mode
                    obs["total_context_tokens"]=int(prompt.shape[1]+shared.shape[1])
                    rows[mode].append(obs)
                print("G65_REP="+str(rep)+" TOP1="+json.dumps(
                   {m:rows[m][-1]["top1_id"] for m in MODES},sort_keys=True),flush=True)
        report["modes"]=rows
        report["numeric_comparison"]=classify(rows)
        report["status"]="PASS_DIAGNOSTIC_MEASUREMENT"
    except Exception as e:
        report.update({"status":"FAIL_OR_BLOCKED","error":f"{type(e).__name__}: {e}"})
        raise
    finally:
        OUTPUT.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        print("G65_STATUS="+report["status"],flush=True)
        if report.get("numeric_comparison"):
            print("G65_CLASSIFICATION="+report["numeric_comparison"]["classification"],flush=True)

if __name__=="__main__":run()
