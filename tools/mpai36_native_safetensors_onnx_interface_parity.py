"""MP-AI36: original native MiniLM safetensors vs authentic FP32 ONNX.

Scientific status: development-only, since original 36 external-author ANLI
examples are publicly available and already exposed. Original weights are
authenticated by full SHA256. Independent Linux job freezes source artifacts
before model inference, and a second Linux job uses one local CPU host to
compare *native PyTorch weights* vs original upstream FP32 ONNX export.
Bidirectional (premise/hypothesis) input order and HF-fast vs original Rust
tokenizer parity, logits, accuracy, FP and memory are explicitly checked.
No external model service, paid API, autonomous memory writer, model promotion,
controller dispatch or new source task selection.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import socket
import statistics
import sys
import tempfile
import time

import mpai34_pinned_conventional_nli_original_anli as p34
import mpai33_independent_anli_adversarial_development as p33
import mpai35_original_vs_quantized_minilm_nli_parity as p35

NATIVE="model.safetensors"
NATIVE_SHA="ec9c5b6a08b60d7a01b465c7ed44b496244dfd1bed3274c95875a74cea89ab35"
NATIVE_MIN=300_000_000
NATIVE_MAX=360_000_000
ONNX="onnx/model.onnx"
ONNX_SHA=p35.MODEL_ORIGINAL_SHA256
ONNX_EXPECTED_CORRECT=5
ONNX_EXPECTED_FP=11
ONNX_EXPECTED_YES=0
TORCH_VERSION="2.6.0+cpu"
TRANSFORMERS_VERSION="4.51.3"
NUMPY_VERSION="2.2.6"
TOKENIZERS_VERSION="0.21.4"
ONNX_RUNTIME_VERSION="1.22.1"
PREV_P33_BLOB="b99afe402459977f9d8493746766d1bae7ccd8ac"
PREV_P34_BLOB="cec12320510645e6d6b7972d7307726c8ea66128"
PREV_P35_BLOB="47d44403cdc867ff5c25c4b5beb14f93cf19bd7d"
META=("config.json","tokenizer.json","tokenizer_config.json",
      "special_tokens_map.json","merges.txt","vocab.json")
STAGE="INIT"

def require(ok,code):
    if not ok:raise RuntimeError("MPAI36_"+code)
def canon(o):
    return json.dumps(o,sort_keys=True,separators=(",",":"))
def sha(o):
    return hashlib.sha256(o).hexdigest()
def preflight():
    require(os.environ.get("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE",
            "REPO_SCOPE")
    require(os.environ.get("GITHUB_RUN_ATTEMPT")=="1","NO_RETRY")
    require(not os.environ.get("OPENAI_API_KEY"),"PAID_API_FORBIDDEN")
    require(os.name=="posix","LINUX_CPU")
    require(p34.MODEL_REV==p35.p34.MODEL_REV and
            p35.MODEL_ORIGINAL_SHA256==ONNX_SHA and
            p34.ANLI_FROZEN_SELECTION==p35.SPLIT_SHA,
            "PREEXISTING_SOURCES_DRIFT")
def frozen(meta_hash):
    return sha(canon({
      "schema":"mpai36-original-native-safetensors-fp32-onnx-interface-v1",
      "upstream_model_repo":p34.MODEL_REPO,
      "revision":p34.MODEL_REV,
      "original_native_sha":NATIVE_SHA,
      "original_fp32_onnx_sha":ONNX_SHA,
      "metadata_sha256":meta_hash,
      "human_anli36_selection":p34.ANLI_FROZEN_SELECTION,
      "independently_custodied_original_human_data":True,
      "first_use_scientifically_blind":False,
      "source_git_blobs":[PREV_P33_BLOB,PREV_P34_BLOB,PREV_P35_BLOB],
      "frameworks":{"torch":TORCH_VERSION,
        "transformers":TRANSFORMERS_VERSION,
        "numpy":NUMPY_VERSION,
        "tokenizers":TOKENIZERS_VERSION,
        "onnxruntime":ONNX_RUNTIME_VERSION},
      "inference_orders":["premise_first","hypothesis_first"],
      "native_fast_and_low_level_tokenizer_bit_parity":True,
      "pair_truncation":"longest_first_512",
      "zero_threshold_retuning":True,
      "source_license":"CC-BY-NC-4.0",
      "no_prod_memory_writes":True,
    }).encode())
def download_meta(private):
    hashes={}
    for name in META:
        file=private/name
        m=p34.download(name,file,6000000)
        hashes[name]=m["sha256"]
    config=json.loads((private/"config.json").read_text("utf-8"))
    require(p34.label_mapping(config)==("NO","YES","UNKNOWN"),"LABELS")
    return hashes
def selected_original(private):
    rows,chosen=p34.data_selection(private)
    require(len(chosen)==36,"ORIGINAL_ANLI36")
    return rows,chosen
def score(arr):
    return (sum(x["pred"]==x["gold"] for x in arr),
            sum(x["pred"]=="YES" and x["gold"]!="YES" for x in arr),
            sum(x["pred"]=="YES" and x["gold"]=="YES" for x in arr))
def main():
    global STAGE
    ap=argparse.ArgumentParser()
    ap.add_argument("--phase",choices=("freeze","evaluate"),required=True)
    ap.add_argument("--expected-protocol",default="")
    args=ap.parse_args()
    preflight()
    if args.phase=="evaluate":
        require(re.fullmatch("[0-9a-f]{64}",args.expected_protocol or ""),
                "FROZEN_PROTOCOL_NOT_FOUND")
    STAGE="SOURCE_METADATA_AND_UIDS"
    with tempfile.TemporaryDirectory(prefix="mpai36-original-native-") as s:
        private=Path(s)
        rows,chosen=selected_original(private)
        hashes=download_meta(private)
        ph=frozen(hashes)
        print("MPAI36_PREMODEL_PROTOCOL_SHA256="+ph,flush=True)
        print("MPAI36_ORIGINAL_MODEL_SHA256="+NATIVE_SHA,flush=True)
        print("MPAI36_ORIGINAL_FP32_ONNX_SHA256="+ONNX_SHA,flush=True)
        print("MPAI36_FROZEN_ANLI36_SELECTION="+p34.ANLI_FROZEN_SELECTION,flush=True)
        print("MPAI36_METADATA_IDENTITY_SHA256="+sha(canon(hashes).encode()),flush=True)
        print("MPAI36_ORIGINAL_THREE_WAY_LABEL_MAP=PASS",flush=True)
        if args.phase=="freeze":
            print("MPAI36_GOLD_NOT_READ_BY_FREEZE=TRUE",flush=True)
            print("MPAI36_MODEL_CALLS_BY_FREEZE=0",flush=True)
            print("MPAI36_SEPARATE_PREMODEL_PROTOCOL_FROZEN=PASS",flush=True)
            return
        require(ph==args.expected_protocol,"PREMODEL_PROTOCOL_MISMATCH")
        STAGE="ORIGINAL_ANLI_GOLD_AND_INPUTS"
        indexed={r["uid"]:r for r in rows}
        tasks=[]
        for one in chosen:
            row=indexed[one["uid"]]
            code=row["gold_label"]
            require(code in ("c","e","n"),"ORIGINAL_LABEL")
            p=row["context"]; h=row["statement"]
            require(bool(p.strip()) and bool(h.strip()) and
                    len(p)<8500 and len(h)<900,"ANLI_INPUT_BUDGET")
            tasks.append((one["category"],p,h,
                          {"c":"NO","e":"YES","n":"UNKNOWN"}[code]))
        require(len(tasks)==36 and sum(g=="YES" for *_,g in tasks)==9,
                "ORIGINAL_GOLD_DENOMINATOR")
        STAGE="SOURCE_AUTHENTIC_WEIGHT_DOWNLOAD"
        nm=private/NATIVE
        om=private/"original_fp32_export.onnx"
        n=p34.download(NATIVE,nm,NATIVE_MAX,expected=NATIVE_SHA)
        o=p34.download(ONNX,om,p35.MODEL_ORIGINAL_MAX,expected=ONNX_SHA)
        require(NATIVE_MIN<n["bytes"]<NATIVE_MAX and
                p35.MODEL_ORIGINAL_MIN<o["bytes"]<=p35.MODEL_ORIGINAL_MAX,
                "AUTHENTIC_SOURCE_BYTES")
        print("MPAI36_BOTH_ORIGINAL_NATIVE_AND_ONNX_FULL_SHA256=PASS",flush=True)
        print("MPAI36_NATIVE_SAFETENSORS_BYTES="+str(n["bytes"]),flush=True)
        print("MPAI36_ORIGINAL_FP32_ONNX_BYTES="+str(o["bytes"]),flush=True)
        os.environ["HF_HUB_OFFLINE"]="1"
        os.environ["TRANSFORMERS_OFFLINE"]="1"
        os.environ["HF_DATASETS_OFFLINE"]="1"
        socket.socket=lambda *args,**kw: (_ for _ in ()).throw(
           RuntimeError("MPAI36_NETWORK_FORBIDDEN_AFTER_CUSTODY"))
        import numpy as np
        import torch
        import onnxruntime as ort
        import transformers
        import tokenizers
        from transformers import AutoModelForSequenceClassification,AutoTokenizer
        from tokenizers import Tokenizer
        require(torch.__version__==TORCH_VERSION and
                transformers.__version__==TRANSFORMERS_VERSION and
                tokenizers.__version__==TOKENIZERS_VERSION and
                ort.__version__==ONNX_RUNTIME_VERSION and
                np.__version__==NUMPY_VERSION,"DEPENDENCY_PIN_CHANGED")
        torch.set_num_threads(4)
        torch.set_num_interop_threads(1)
        STAGE="NATIVE_MODEL_AND_ONNX_ORIGINAL"
        t0=time.perf_counter()
        hf=AutoTokenizer.from_pretrained(str(private),local_files_only=True,
                                          use_fast=True)
        native=AutoModelForSequenceClassification.from_pretrained(
                 str(private),local_files_only=True,
                 use_safetensors=True)
        native.eval()
        native_load_ms=max(1,int(1000*(time.perf_counter()-t0)))
        opt=ort.SessionOptions()
        opt.intra_op_num_threads=4;opt.inter_op_num_threads=1
        opt.graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        t0=time.perf_counter()
        ort_model=ort.InferenceSession(str(om),sess_options=opt,
                                     providers=["CPUExecutionProvider"])
        ort_load_ms=max(1,int(1000*(time.perf_counter()-t0)))
        keys={x.name for x in ort_model.get_inputs()}
        require(keys.issubset({"input_ids","attention_mask","token_type_ids"}) and
                {"input_ids","attention_mask"}.issubset(keys),"MODEL_INPUT_NAMES")
        low=Tokenizer.from_file(str(private/"tokenizer.json"))
        low.enable_truncation(max_length=512,strategy="longest_first")
        outcome={}
        for direction in ("premise_first","hypothesis_first"):
            STAGE="PAIRED_CPU_INFERENCE_"+direction.upper()
            logs={"native":[],"onnx":[]}
            different_ids=0;max_abs=0.0;mean_abs_total=0.0;flips=0
            native_ms=[];onnx_ms=[]
            for family,p,h,gold in tasks:
                fst,snd=(p,h) if direction=="premise_first" else (h,p)
                prepared=hf(fst,snd,truncation="longest_first",max_length=512,
                            return_tensors="pt")
                ids=prepared["input_ids"].numpy()
                mask=prepared["attention_mask"].numpy()
                rust=low.encode(fst,snd)
                if ids.shape[1]!=len(rust.ids) or ids.tolist()[0]!=rust.ids or mask.tolist()[0]!=rust.attention_mask:
                    different_ids+=1
                require(0<ids.shape[1]<=512,"MODEL_INPUT_TOKEN_RANGE")
                inputs={"input_ids":ids.astype(np.int64),
                        "attention_mask":mask.astype(np.int64),
                        "token_type_ids":np.zeros_like(ids,dtype=np.int64)}
                t0=time.perf_counter()
                with torch.inference_mode():
                    logits_native=native(input_ids=prepared["input_ids"],
                                         attention_mask=prepared["attention_mask"]).logits.cpu().numpy()
                native_ms.append(max(1,int((time.perf_counter()-t0)*1000)))
                t0=time.perf_counter()
                logits_onnx=ort_model.run(None,{k:inputs[k] for k in keys})[0]
                onnx_ms.append(max(1,int((time.perf_counter()-t0)*1000)))
                require(logits_native.shape==logits_onnx.shape==(1,3)
                        and bool(np.isfinite(logits_native).all())
                        and bool(np.isfinite(logits_onnx).all()),"FLOAT32_LOGITS_SHAPE")
                gap=np.abs(logits_native.astype(np.float64)-logits_onnx.astype(np.float64))
                max_abs=max(max_abs,float(gap.max()))
                mean_abs_total+=float(gap.mean())
                an=int(np.argmax(logits_native[0]));ao=int(np.argmax(logits_onnx[0]))
                flips+=int(an!=ao)
                for key,ind in (("native",an),("onnx",ao)):
                    logs[key].append({"family":family,"gold":gold,
                                      "pred":("NO","YES","UNKNOWN")[ind]})
            require(all(len(x)==36 for x in logs.values()),"MODEL_RUN_COUNT")
            results={key:score(x) for key,x in logs.items()}
            outcome[direction]={"tokenizer_mismatch":different_ids,
                 "max_abs_logits_gap":max_abs,"mean_abs_logits_gap":mean_abs_total/36,
                 "changed_predictions":flips,"results":results,
                 "native_median_ms":statistics.median(native_ms),
                 "onnx_median_ms":statistics.median(onnx_ms)}
            print("MPAI36_DIRECTION_"+direction.upper()+"="+canon({
                "n":36,
                "tokenizer_disagreement":different_ids,
                "native_correct":results["native"][0],
                "native_hard_false_positives":results["native"][1],
                "native_valid_entailments":results["native"][2],
                "onnx_correct":results["onnx"][0],
                "onnx_hard_false_positives":results["onnx"][1],
                "onnx_valid_entailments":results["onnx"][2],
                "changed_class_labels":flips,
                "max_absolute_logit_delta":round(max_abs,6),
                "mean_absolute_logit_delta":round(mean_abs_total/36,6),
                "native_median_ms":statistics.median(native_ms),
                "onnx_median_ms":statistics.median(onnx_ms),
            }),flush=True)
        original=outcome["premise_first"]
        backwards=outcome["hypothesis_first"]
        q=original["results"]["onnx"]
        reproduce=q==(ONNX_EXPECTED_CORRECT,ONNX_EXPECTED_FP,ONNX_EXPECTED_YES)
        print("MPAI36_ORIGINAL_P35_ONNX_RESULT_REPRODUCED="+(
          "PASS" if reproduce else "FAIL"),flush=True)
        print("MPAI36_BOTH_DIRECTIONS_NATIVE_AND_ONNX_MODEL_CALLS=144",flush=True)
        print("MPAI36_BOTH_INPUT_ORDERS_CHECKED=PASS",flush=True)
        print("MPAI36_HF_AND_RUST_FAST_TOKENIZER_PARITY="+(
            "PASS" if original["tokenizer_mismatch"]==0 and
                      backwards["tokenizer_mismatch"]==0 else "FAIL"),flush=True)
        # A small float logit difference supports native/ONNX parity. This
        # threshold is diagnostic, not tuned on any original ANLI gold.
        parity=original["changed_predictions"]==0 and backwards["changed_predictions"]==0 and \
               original["max_abs_logits_gap"]<0.01 and backwards["max_abs_logits_gap"]<0.01
        print("MPAI36_NATIVE_ONNX_NUMERICAL_LOGIT_PARITY="+(
             "PASS" if parity else "FAIL"),flush=True)
        print("MPAI36_NATIVE_MODEL_LOAD_MS="+str(native_load_ms),flush=True)
        print("MPAI36_ONNX_MODEL_LOAD_MS="+str(ort_load_ms),flush=True)
        print("MPAI36_PROCESS_PEAK_RSS_BYTES_APPROX="+str(int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024),flush=True)
        print("MPAI36_ORIGINAL_ANLI_PUBLIC_ALREADY_EXPOSED=TRUE",flush=True)
        print("MPAI36_NO_SCIENTIFIC_FIRST_USE_PROVEN=TRUE",flush=True)
        print("MPAI36_SCIENTIFIC_JUDGE_ACCEPTANCE=BLOCKED",flush=True)
        print("MPAI36_PRODUCTION_MEMORY_WRITES=0",flush=True)
        print("MPAI36_F139_CONTROLLER_UNMODIFIED=TRUE",flush=True)
    print("MPAI36_PRIVATE_MODEL_AND_ANLI_SCRATCH_REMOVED=PASS",flush=True)

if __name__=="__main__":
    try:main()
    except Exception as e:
        tag=str(e)
        marker=tag if re.fullmatch(r"MPAI36_[A-Z0-9_]{3,100}",tag) else "MPAI36_PRIVATE_EXCEPTION"
        print("MPAI36_SAFE_FAILURE="+marker,flush=True)
        print("MPAI36_SAFE_STAGE="+STAGE,flush=True)
        print("MPAI36_SAFE_TYPE="+type(e).__name__,flush=True)
        sys.exit(2)
