#!/usr/bin/env python3
"""ACC G64: five controlled reproductions of G63 WikiText-2 exact-output divergence.

No threshold change, no G63 acceptance reversal, no speculative optimization claim.
Preexecution contract: docs/research/ACC-G64-PREEXEC-20261030.md.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"acc_g63"))
import g63_heldout_wikitext as original
from g63_heldout_wikitext import audited_continuation, file_sha256

G63_SOURCE_BLOB = "33cdfa236ae79c3eed0c1968cb5d839d4af4b3d7"
G62_SOURCE_BLOB = "b32a30456b019b044207e9d428db04c36e0290ca"
G63_CORPUS_SHA256 = "d790b833ef8cf03a90db7bf1271b7520b83c45ce07ba3c1a9699df81e239eca0"
ANCHOR = 2
TASK = "natural_continuation"
CONTEXT = 1536
NEW_TOKENS = 64
PAIRS = 5
WARMUPS = 2
OUTPUT = Path(os.environ.get("G64_OUTPUT","g64_result.json"))
CORPUS_FILE = Path(os.environ.get("G64_CORPUS_PATH","g64_wikitext_test.txt"))

def git_blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()

def pinned_source_assertions():
    g63=Path(original.__file__).read_bytes()
    g62=Path(original.__file__).resolve().parents[1]/"acc_g62"/"g62_prompt_lookup.py"
    if git_blob(g63)!=G63_SOURCE_BLOB or git_blob(g62.read_bytes())!=G62_SOURCE_BLOB:
        raise RuntimeError("G63_G62_HELPER_GIT_BLOB_IDENTITY_DRIFT")
    if (original.ANCHORS[ANCHOR],TASK,CONTEXT)!=(.73,"natural_continuation",1536):
        raise RuntimeError("ORIGINAL_FAILURE_CASE_IDENTITY_DRIFT")
    if original.GEN!=NEW_TOKENS or original.REPO!="TinyLlama/TinyLlama-1.1B-Chat-v1.0":
        raise RuntimeError("ORIGINAL_MODEL_OR_OUTPUT_CONTRACT_DRIFT")
    return {"g63_original_git_blob":G63_SOURCE_BLOB,"g62_original_git_blob":G62_SOURCE_BLOB}

def paired_order(n):
    return ("baseline","candidate") if n%2==0 else ("candidate","baseline")

def first_difference(a:list[int],b:list[int])->dict:
    if len(a)!=NEW_TOKENS or len(b)!=NEW_TOKENS:
        raise ValueError("EXPECTED_EXACTLY_64_ACCEPTED_IDS_PER_ARM")
    i=next((i for i,(x,y) in enumerate(zip(a,b)) if x!=y),None)
    if i is None:
        return {"equal":True,"first_mismatch_index":None,"same_prefix_tokens":NEW_TOKENS}
    return {"equal":False,"first_mismatch_index":i,"same_prefix_tokens":i,
            "baseline_token_id":a[i],"candidate_token_id":b[i]}

def first_unequal_across_repeats(sequences):
    if not sequences:return None
    first=sequences[0]
    diffs=[first_difference(first,x)["first_mismatch_index"]
           for x in sequences[1:] if x!=first]
    return min(diffs) if diffs else None

def run():
    import torch
    import transformers
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer, AutoModelForCausalLM
    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32=False
    receipt={"schema":"forge.acc.g64.g63-exact-divergence-forensics.v1",
       "gate":"ACC-G64","status":"UNVERIFIED",
       "source_head":os.getenv("GITHUB_SHA",""),
       "platform":platform.platform(),
       "torch":torch.__version__,"cuda_runtime":torch.version.cuda,
       "transformers":transformers.__version__,
       "original_g63_final":"FAIL_NO_GO_UNCHANGED",
       "original_g63_failed_run":41042643715,
       "original_failing_case":{"anchor_index":ANCHOR,"task":TASK,"context_tokens":CONTEXT},
       "model_revision":original.REV,
       "model_safetensors_sha256_expected":original.WEIGHT_SHA,
       "corpus_original_git_blob":original.CORPUS_BLOB,
       "corpus_sha256_expected":G63_CORPUS_SHA256,
       "precommitted_pairs":PAIRS,
       "accepted_tokens":NEW_TOKENS,
       "novel_acceleration_claim":False,
       "science_acceptance":"NOT_GRANTED",
       "model_or_prompt_tuning_performed":False}
    try:
        receipt.update(pinned_source_assertions())
        raw=original.frozen_source(CORPUS_FILE)
        if hashlib.sha256(raw).hexdigest()!=G63_CORPUS_SHA256:
            raise RuntimeError("FROZEN_CORPUS_SHA256_MISMATCH")
        receipt["actual_corpus_sha256"]=hashlib.sha256(raw).hexdigest()
        if not torch.cuda.is_available() or not torch.version.cuda or tuple(map(int,torch.version.cuda.split(".")[:2]))<(12,8):
            raise RuntimeError("NO_VALID_BLACKWELL_CUDA_NO_CPU_FALLBACK")
        device=torch.device("cuda:0")
        name=torch.cuda.get_device_name(device)
        cc=torch.cuda.get_device_capability(device)
        free,total=torch.cuda.mem_get_info(device)
        if cc!=(12,0) or "NVIDIA" not in name.upper() or free<7000*1024**2:
            raise RuntimeError("REAL_RTX_GPU_ADMISSION_FAILED")
        m=torch.ones((1024,1024),device=device)
        computed=m@m
        torch.cuda.synchronize(device)
        if computed.device.type!="cuda" or abs(float(computed[0,0])-1024)>.001:
            raise RuntimeError("REAL_GPU_MATMUL_FAILED")
        del m,computed
        torch.cuda.empty_cache()
        receipt["gpu"]={"name":name,"compute_capability":list(cc),
          "free_mib_before":free//1024**2,"total_mib":total//1024**2}
        snapshot=Path(snapshot_download(
            repo_id=original.REPO,revision=original.REV,token=False,
            allow_patterns=list(original.FILES)))
        weight=snapshot/"model.safetensors"
        if (not weight.is_file() or weight.stat().st_size!=original.WEIGHT_SIZE
            or file_sha256(weight)!=original.WEIGHT_SHA):
            raise RuntimeError("AUTHENTIC_ORIGINAL_TINYLLAMA_CHECKPOINT_DRIFT")
        receipt["model_safetensors_sha256_actual"]=file_sha256(weight)
        tokenizer=AutoTokenizer.from_pretrained(
            str(snapshot),use_fast=True,local_files_only=True,trust_remote_code=False)
        model=AutoModelForCausalLM.from_pretrained(
            str(snapshot),torch_dtype=torch.float16,attn_implementation="sdpa",
            use_safetensors=True,local_files_only=True,trust_remote_code=False).eval().to(device)
        if (model.config.model_type!="llama" or model.config.num_hidden_layers!=22
             or model.config._attn_implementation!="sdpa"):
            raise RuntimeError("ORIGINAL_MODEL_SDPA_CONFIGURATION_DRIFT")
        from torch.profiler import profile,ProfilerActivity
        with torch.inference_mode(),profile(activities=[ProfilerActivity.CPU]) as prof:
            model(input_ids=torch.tensor([[1,10,20,30]],dtype=torch.long,device=device),use_cache=True)
            torch.cuda.synchronize(device)
        if "aten::scaled_dot_product_attention" not in [x.key for x in prof.key_averages()]:
            raise RuntimeError("OPTIMIZED_SDPA_ACTUAL_OPERATOR_MISSING")
        receipt["real_optimized_sdpa_operator"]="PASS"
        source_tokens=original.frozen_sample_tokens(
            tokenizer,raw.decode("utf-8"),original.ANCHORS[ANCHOR])
        prompt_ids=original.case_ids(torch,tokenizer,source_tokens,TASK,CONTEXT).to(device)
        prompt_list=prompt_ids[0].detach().cpu().tolist()
        receipt["prompt_token_sha256"]=hashlib.sha256(
            json.dumps(prompt_list).encode("utf-8")).hexdigest()
        receipt["prompt_tokens"]=len(prompt_list)
        if len(prompt_list)!=CONTEXT:
            raise RuntimeError("ORIGINAL_PROMPT_CONTEXT_DRIFT")
        if CONTEXT+NEW_TOKENS+5>model.config.max_position_embeddings:
            raise RuntimeError("POSITION_LIMIT_VIOLATED")

        def generate(arm):
            counts={"n":0}
            def hook(*_args,**_kwargs):counts["n"]+=1
            handler=model.register_forward_pre_hook(hook)
            kwargs=dict(input_ids=prompt_ids,do_sample=False,num_beams=1,
              use_cache=True,max_new_tokens=NEW_TOKENS,eos_token_id=-1,
              pad_token_id=tokenizer.eos_token_id)
            if arm=="candidate":
                kwargs.update(prompt_lookup_num_tokens=5,max_matching_ngram_size=3)
            torch.cuda.synchronize(device)
            torch.cuda.reset_peak_memory_stats(device)
            start=time.perf_counter()
            try:
                result=model.generate(**kwargs)
            finally:
                handler.remove()
            torch.cuda.synchronize(device)
            dt=time.perf_counter()-start
            raw_ids=result[0,CONTEXT:].detach().cpu().tolist()
            accepted,raw_count=audited_continuation(raw_ids,arm)
            return {"arm":arm,"first_64_token_ids":accepted,
               "accepted_64_ids_sha256":hashlib.sha256(
                    json.dumps(accepted).encode("utf-8")).hexdigest(),
               "raw_generated_tokens":raw_count,
               "extra_generated_tokens_charged":raw_count-NEW_TOKENS,
               "forward_calls":counts["n"],"elapsed_s":dt,
               "gpu_peak_allocated_mib":torch.cuda.max_memory_allocated(device)/1024**2}

        with torch.inference_mode():
            for arm in ("baseline","candidate"):
                for _ in range(WARMUPS):
                    generate(arm)
            pairs=[]
            for n in range(PAIRS):
                result={}
                for arm in paired_order(n):
                    result[arm]=generate(arm)
                diff=first_difference(result["baseline"]["first_64_token_ids"],
                                      result["candidate"]["first_64_token_ids"])
                pairs.append({"pair_index":n,"order":list(paired_order(n)),
                    "baseline":result["baseline"],"candidate":result["candidate"],
                    "difference":diff})
                print(f"G64_PAIR={n} exact={diff['equal']} first_diff={diff['first_mismatch_index']}",flush=True)
            receipt["pairs"]=pairs
            receipt["pair_mismatch_count"]=sum(not p["difference"]["equal"] for p in pairs)
            receipt["within_baseline_first_divergence"]=first_unequal_across_repeats(
                [p["baseline"]["first_64_token_ids"] for p in pairs])
            receipt["within_candidate_first_divergence"]=first_unequal_across_repeats(
                [p["candidate"]["first_64_token_ids"] for p in pairs])
            first=next((p for p in pairs if not p["difference"]["equal"]),None)
            if first is not None:
                index=first["difference"]["first_mismatch_index"]
                shared=first["baseline"]["first_64_token_ids"][:index]
                full=torch.cat((prompt_ids,torch.tensor([shared],dtype=torch.long,device=device)),dim=1) if shared else prompt_ids
                logits=model(input_ids=full,use_cache=False).logits[0,-1].float()
                vals,ids=torch.topk(logits,k=2)
                top1=int(ids[0]);top2=int(ids[1])
                actual_b=first["difference"]["baseline_token_id"]
                actual_c=first["difference"]["candidate_token_id"]
                receipt["fresh_full_forward_reference"]={
                  "paired_index":first["pair_index"],"mismatch_index":index,
                  "full_forward_context_tokens":full.shape[1],
                  "fresh_top1_token_id":top1,"fresh_top2_token_id":top2,
                  "fresh_top1_logit":float(vals[0]),"fresh_top2_logit":float(vals[1]),
                  "fresh_top1_top2_margin":float(vals[0]-vals[1]),
                  "fresh_argmax_matches_baseline":top1==actual_b,
                  "fresh_argmax_matches_candidate":top1==actual_c,
                  "reference_is_independent_full_forward_not_proof_of_causality":True}
            receipt["disposition"]=(
              "REPRODUCED_DIVERGENCE" if receipt["pair_mismatch_count"]
              else "NOT_REPRODUCED")
            receipt["status"]="PASS_BOUNDED_FORENSIC_EXECUTION"
    except Exception as e:
        receipt.update({"status":"FAIL_OR_BLOCKED","error":f"{type(e).__name__}: {e}"})
        raise
    finally:
        OUTPUT.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        print("G64_STATUS="+receipt["status"],flush=True)
        print("G64_DISPOSITION="+str(receipt.get("disposition","UNVERIFIED")),flush=True)

if __name__=="__main__":run()
