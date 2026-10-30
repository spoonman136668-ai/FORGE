"""MP-AI35 original unquantized ONNX vs original INT8-AVX2 ONNX parity.

Same authenticated upstream MiniLM revision, tokenizer/config, frozen ANLI36,
CPU host, ONNXRuntime, preprocessing and paired inference. Inputs precomputed
exactly once. Full SHA256 of BOTH actual weight files, including 329MB fp32.
No gold exposed in preregistration, no thresholds tuned, no admitted judge.
P34's published quantized results MUST reproduce to interpret differences.
This comparison does not test native PyTorch checkpoint vs FP32 ONNX export.
Public original ANLI is not a blind first use/contamination-proof benchmark.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
import re
import resource
import shutil
import socket
import statistics
import sys
import tempfile
import time

import mpai34_pinned_conventional_nli_original_anli as p34
import mpai33_independent_anli_adversarial_development as p33

MODEL_ORIGINAL="onnx/model.onnx"
MODEL_ORIGINAL_SHA256="807d33fffefd95ad60e2a91f54eed50a92aa53c077945a6842bb587a49a3fdf3"
MODEL_ORIGINAL_MIN=300_000_000
MODEL_ORIGINAL_MAX=360_000_000
MODEL_QUANT=p34.MODEL_FILE
MODEL_QUANT_SHA256=p34.MODEL_SHA256
P34_GIT_BLOB="cec12320510645e6d6b7972d7307726c8ea66128"
P33_GIT_BLOB="b99afe402459977f9d8493746766d1bae7ccd8ac"
EXPECTED_QUANT_CORRECT=7
EXPECTED_QUANT_HARD_FP=11
EXPECTED_QUANT_VALID_YES=0
SPLIT_SHA=p34.ANLI_FROZEN_SELECTION
PROTOCOL_BEFORE=p34.ANLI_FROZEN_PROTOCOL
STAGE="INIT"

def require(v,code):
    if not v: raise RuntimeError("MPAI35_"+code)
def hash_json(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def protocol(conf,tok):
    return hash_json({
      "schema":"mpai35-samecpu-paired-unchanged-original-quantized-miniLM-nli-v1",
      "upstream_model_repo":p34.MODEL_REPO,
      "upstream_model_revision":p34.MODEL_REV,
      "model_original_path":MODEL_ORIGINAL,
      "model_original_sha256":MODEL_ORIGINAL_SHA256,
      "model_quant_path":MODEL_QUANT,
      "model_quant_sha256":MODEL_QUANT_SHA256,
      "model_config_sha256":conf,"model_tokenizer_sha256":tok,
      "original_p34_source_blob":P34_GIT_BLOB,
      "original_p33_source_blob":P33_GIT_BLOB,
      "original_human_36_task_selection":SPLIT_SHA,
      "original_selection_protocol":PROTOCOL_BEFORE,
      "tokenizer":"same precomputed native longest_first 512",
      "runtime":"onnxruntime CPUExecutionProvider",
      "cpu_threads":4,"same_linux_host":True,
      "quant_reference_score":{"correct":7,"hard_false_positive":11,
                              "valid_yes":0},
      "threshold_tuning":False,"hard_false_positive_budget":0,
      "scientific_first_use":False,
      "source_license":"CC-BY-NC-4.0",
      "output":"aggregate only; zero gold/reference text logs",
      "production_writes":False,
    })
def download_metadata(private):
    c=private/"config.json";t=private/"tokenizer.json"
    conf=p34.download("config.json",c,10000)
    tok=p34.download("tokenizer.json",t,5000000)
    mapping=p34.label_mapping(json.loads(c.read_text("utf-8")))
    require(mapping==("NO","YES","UNKNOWN"),"LABEL_ORDER_CHANGED")
    return c,t,conf["sha256"],tok["sha256"]
def original_36(private):
    data=p33.source_download(private)
    rows=p33.source_rows(data)
    chosen,source_sha=p33.select(rows)
    require(source_sha==SPLIT_SHA and
            p33.prereg_digest(chosen,source_sha)==PROTOCOL_BEFORE,
            "AUTHENTIC_ANLI_SELECTION_DRIFT")
    require(len(chosen)==36,"SELECTED_TASK_COUNT")
    return rows,chosen
def preflight():
    require(os.environ.get("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE",
            "REPO_ID")
    require(os.environ.get("GITHUB_RUN_ATTEMPT")=="1","NO_RETRY")
    require(not os.environ.get("OPENAI_API_KEY"),"NO_PAID_API")
    require(os.name=="posix","LINUX_SAME_HOST_REQUIRED")
    require(p34.MODEL_SHA256==MODEL_QUANT_SHA256 and
            p34.MODEL_REV=="f3b1e8aac2451320dfe2ce56673b3f2ec63e6f03",
            "MODEL_REVISION_DRIFT")
    require(p34.ANLI_FROZEN_SELECTION==SPLIT_SHA,
            "FROZEN_ANLI_SHA_CHANGED")
def score(rows):
    exact=sum(x["pred"]==x["gold"] for x in rows)
    fp=sum(x["pred"]=="YES" and x["gold"]!="YES" for x in rows)
    tp=sum(x["pred"]=="YES" and x["gold"]=="YES" for x in rows)
    return exact,fp,tp
def main():
    global STAGE
    parser=argparse.ArgumentParser()
    parser.add_argument("--phase",choices=("freeze","evaluate"),required=True)
    parser.add_argument("--expected-protocol",default="")
    args=parser.parse_args()
    preflight()
    if args.phase=="evaluate":
        require(re.fullmatch(r"[0-9a-f]{64}",args.expected_protocol or ""),
                "FIRST_JOB_PROTOCOL_MISSING")
    STAGE="SOURCE_CUSTODY"
    with tempfile.TemporaryDirectory(prefix="mpai35-paired-private-") as scratch:
        from pathlib import Path
        private=Path(scratch)
        rows,selected=original_36(private)
        conf,tok,conf_sha,tok_sha=download_metadata(private)
        digest=protocol(conf_sha,tok_sha)
        print("MPAI35_FROZEN_PARITY_PROTOCOL_SHA256="+digest,flush=True)
        print("MPAI35_MODEL_ORIGINAL_ONNX_SHA256="+MODEL_ORIGINAL_SHA256,flush=True)
        print("MPAI35_MODEL_QUANT_ONNX_SHA256="+MODEL_QUANT_SHA256,flush=True)
        print("MPAI35_MODEL_CONFIG_SHA256="+conf_sha,flush=True)
        print("MPAI35_MODEL_TOKENIZER_SHA256="+tok_sha,flush=True)
        print("MPAI35_REUSED_HUMAN_ANLI_36_SOURCE_SELECTION_SHA256="+SPLIT_SHA,flush=True)
        print("MPAI35_METADATA_ONLY_SELECTION=PASS",flush=True)
        if args.phase=="freeze":
            print("MPAI35_GOLD_NOT_ACCESSED_AT_FREEZE=TRUE",flush=True)
            print("MPAI35_NO_MODEL_EXECUTION_AT_FREEZE=TRUE",flush=True)
            print("MPAI35_FIRST_JOB_PREMODEL_COMMITMENT=PASS",flush=True)
            return
        require(digest==args.expected_protocol,"SEPARATE_PREREGISTRATION_MISMATCH")
        STAGE="LOAD_PRIVATE_GOLD"
        byid={r["uid"]:r for r in rows}
        tasks=[]
        for one in selected:
            r=byid[one["uid"]]
            require(r["gold_label"] in ("c","e","n"),"ORIGINAL_GOLD_LABEL")
            premise=r["context"]; hypothesis=r["statement"]
            require(premise.strip() and hypothesis.strip() and
                    len(premise)<8500 and len(hypothesis)<900,
                    "BENCHMARK_INPUT_LENGTH")
            gold={"c":"NO","e":"YES","n":"UNKNOWN"}[r["gold_label"]]
            tasks.append((one["category"],premise,hypothesis,gold))
        require(len(tasks)==36 and sum(x[-1]=="YES" for x in tasks)==9,
                "ORIGINAL_HUMAN_36_GOLD_DISTRIBUTION")
        STAGE="DOWNLOAD_AUTHENTIC_MODELS"
        fp32=private/"original_float32.onnx"
        quant=private/"original_quant_avx2.onnx"
        f=p34.download(MODEL_ORIGINAL,fp32,MODEL_ORIGINAL_MAX,
                       expected=MODEL_ORIGINAL_SHA256)
        require(MODEL_ORIGINAL_MIN<f["bytes"]<=MODEL_ORIGINAL_MAX,
                "ORIGINAL_MODEL_SIZE")
        q=p34.download(MODEL_QUANT,quant,p34.MODEL_MAX_BYTES,
                       expected=MODEL_QUANT_SHA256)
        require(p34.MODEL_MIN_BYTES<q["bytes"]<=p34.MODEL_MAX_BYTES,
                "QUANT_MODEL_SIZE")
        print("MPAI35_BOTH_ORIGINAL_MODEL_FULL_SHA256=PASS",flush=True)
        print("MPAI35_ORIGINAL_FP32_ONNX_BYTES="+str(f["bytes"]),flush=True)
        print("MPAI35_ORIGINAL_INT8_ONNX_BYTES="+str(q["bytes"]),flush=True)
        os.environ["HF_HUB_OFFLINE"]="1"
        socket.socket=lambda *a,**kw:(_ for _ in ()).throw(RuntimeError(
             "MPAI35_OFFLINE_INFERENCE_ONLY"))
        import numpy as np
        import onnxruntime as ort
        from tokenizers import Tokenizer
        tokenizer=Tokenizer.from_file(str(tok))
        tokenizer.enable_truncation(max_length=512,strategy="longest_first")
        cache=[]
        for family,p,h,gold in tasks:
            e=tokenizer.encode(p,h)
            require(0<len(e.ids)<=512,"TOKENIZATION_BOUNDS")
            cache.append((family,gold,{
              "input_ids":np.asarray([e.ids],dtype=np.int64),
              "attention_mask":np.asarray([e.attention_mask],dtype=np.int64),
              "token_type_ids":np.asarray([e.type_ids],dtype=np.int64)
            },len(e.ids)))
        print("MPAI35_SHARED_IDENTICAL_TOKENIZATION=PASS",flush=True)
        opts=ort.SessionOptions()
        opts.intra_op_num_threads=4;opts.inter_op_num_threads=1
        opts.graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        STAGE="RUN_FP32_AND_INT8_CPU"
        sessions={}
        loads={}
        for name,path in (("fp32",fp32),("int8",quant)):
            start=time.perf_counter()
            sess=ort.InferenceSession(str(path),sess_options=opts,
                                      providers=["CPUExecutionProvider"])
            loads[name]=max(1,int((time.perf_counter()-start)*1000))
            keys={v.name for v in sess.get_inputs()}
            require(keys.issubset({"input_ids","attention_mask","token_type_ids"}) and
                    {"input_ids","attention_mask"}.issubset(keys),
                    "MODEL_INPUT_PARITY")
            require(len(sess.get_outputs())>=1,"OUTPUT_MISSING")
            sessions[name]=(sess,keys)
        out={"fp32":[],"int8":[]}
        flips=0
        for i,(family,gold,data,n) in enumerate(cache):
            predictions={}
            for name in (("fp32","int8") if i%2==0 else ("int8","fp32")):
                sess,keys=sessions[name]
                start=time.perf_counter()
                logits=sess.run(None,{k:data[k] for k in keys})[0]
                elapsed=max(1,int((time.perf_counter()-start)*1000))
                require(logits.shape==(1,3) and bool(np.isfinite(logits).all()),
                        "ACTUAL_LOGITS_SCHEMA")
                label=("NO","YES","UNKNOWN")[int(np.argmax(logits[0]))]
                predictions[name]=label
                out[name].append({"family":family,"gold":gold,"pred":label,
                                  "ms":elapsed,"tokens":n})
            flips+=int(predictions["fp32"]!=predictions["int8"])
        require(all(len(out[k])==36 for k in out),"ORIGINAL_36_COMPLETED")
        results={k:score(out[k]) for k in out}
        quant_prior=(EXPECTED_QUANT_CORRECT,EXPECTED_QUANT_HARD_FP,
                     EXPECTED_QUANT_VALID_YES)
        print("MPAI35_QUANT_P34_BASELINE_REPRODUCED="+(
            "PASS" if results["int8"]==quant_prior else "FAIL"),flush=True)
        for k in ("fp32","int8"):
            exact,fp,tp=results[k]
            print("MPAI35_"+k.upper()+"_CORRECT="+str(exact)+"_OF_36",flush=True)
            print("MPAI35_"+k.upper()+"_HARD_FALSE_POSITIVES="+str(fp),flush=True)
            print("MPAI35_"+k.upper()+"_SUPPORTED_ENTAILMENTS="+str(tp)+"_OF_9",flush=True)
            print("MPAI35_"+k.upper()+"_LOAD_MS="+str(loads[k]),flush=True)
            print("MPAI35_"+k.upper()+"_MEDIAN_INFERENCE_MS="+str(int(statistics.median(x["ms"] for x in out[k]))),flush=True)
            print("MPAI35_"+k.upper()+"_TOTAL_INFERENCE_MS="+str(sum(x["ms"] for x in out[k])),flush=True)
        print("MPAI35_FP32_INT8_CHANGED_LABELS="+str(flips)+"_OF_36",flush=True)
        for category in p33.SOURCE_FAMILIES:
            rr={name:[z for z in out[name] if z["family"]==category]
                for name in ("fp32","int8")}
            require(all(len(v)==6 for v in rr.values()),"ORIGINAL_FAMILY_SIZE")
            fcorrect,ffp,_=score(rr["fp32"])
            qcorrect,qfp,_=score(rr["int8"])
            print("MPAI35_CATEGORY_"+category.upper().replace("-","_")+"="+
                  json.dumps({"n":6,"fp32_correct":fcorrect,"int8_correct":qcorrect,
                  "fp32_hard_fp":ffp,"int8_hard_fp":qfp},
                  sort_keys=True,separators=(",",":")),flush=True)
        print("MPAI35_ORIGINAL_SOURCE_INFERENCE_CALLS=72",flush=True)
        print("MPAI35_SAME_HOST_SAME_TOKENS_SAME_ORT=TRUE",flush=True)
        print("MPAI35_HOST_PEAK_RSS_BYTES_APPROX="+str(int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024),flush=True)
        print("MPAI35_ORIGINAL_ANLI_PUBLIC_EXPOSED_DEVELOPMENT=TRUE",flush=True)
        print("MPAI35_NO_MODEL_THRESHOLD_TUNING=TRUE",flush=True)
        print("MPAI35_CONVENTIONAL_NLI_SCIENTIFIC_ACCEPTANCE=BLOCKED",flush=True)
        print("MPAI35_FORGE_AUTONOMY_UNMODIFIED=TRUE",flush=True)
        print("MPAI35_ACCEPTED_MEMORY_WRITES=0",flush=True)
    print("MPAI35_ALL_PRIVATE_SOURCE_AND_MODEL_REMOVED=PASS",flush=True)
if __name__=="__main__":
    try:main()
    except Exception as exc:
        tag=str(exc)
        label=tag if re.fullmatch(r"MPAI35_[A-Z0-9_]{3,100}",tag) else "MPAI35_PRIVATE_EXCEPTION"
        print("MPAI35_SAFE_FAILURE="+label,flush=True)
        print("MPAI35_SAFE_STAGE="+STAGE,flush=True)
        print("MPAI35_SAFE_TYPE="+type(exc).__name__,flush=True)
        sys.exit(2)
