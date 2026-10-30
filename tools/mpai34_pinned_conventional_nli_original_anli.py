"""MP-AI34: original-source-pinned conventional NLI ONNX competitor.

Qualify conventional classifier cross-encoder/nli-MiniLM2-L6-H768,
ONNX pre-existing quantized AVX2 export, frozen upstream Git revision and
full original model SHA256. Original independently authored and human-labeled
36 ANLI examples from MP-AI33, same exact source identities and categories.
This is a *PUBLIC EXPOSED DEVELOPMENT COMPARISON*, NOT an independently
blinded or contamination-free holdout or authority to promote any classifier.

Linux-only ephemeral CPU, no Torch/Paid API, protected repository untouched.
Model and dataset data remain in private ephemeral scratch. Only aggregate
metrics and immutable pins printed. No new truth labels manufactured.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import socket
import statistics
import sys
import tempfile
import time
import urllib.request

import mpai33_independent_anli_adversarial_development as a33

MODEL_REPO="cross-encoder/nli-MiniLM2-L6-H768"
MODEL_REV="f3b1e8aac2451320dfe2ce56673b3f2ec63e6f03"
MODEL_FILE="onnx/model_quint8_avx2.onnx"
MODEL_SHA256="44391a5241a62e0083c1a8899a71e69a092b95aea5ba89e14062925468eceac7"
MODEL_MIN_BYTES=80_000_000
MODEL_MAX_BYTES=90_000_000
TOKENIZER_FILE="tokenizer.json"
CONFIG_FILE="config.json"
ANLI_FROZEN_SELECTION="9918f7e1318464c4d3c4ff95db08ae671609ce422417cae649a42cac2f41adf2"
ANLI_FROZEN_PROTOCOL="ef8fd038d9b9e543581502b61f5f1a4915cbd1b0a59a17804115a119f1a48894"
ANLI_SCRIPT_GIT_BLOB="b99afe402459977f9d8493746766d1bae7ccd8ac"
EXPECTED_PRIOR={"phi_correct":16,"phi_false_positive":7,
 "phi_valid_entailments":2,"total":36,"gold_entailments":9}
STAGE="INIT"

def need(v,code):
    if not v:raise RuntimeError("MPAI34_"+code)
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
def canonical(v):
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True)
def url(name):
    return "https://huggingface.co/"+MODEL_REPO+"/resolve/"+MODEL_REV+"/"+name+"?download=true"
def download(name,path,limit,expected=None):
    need(not path.exists(),"SCRATCH_COLLISION")
    request=urllib.request.Request(url(name),headers={"User-Agent":"MPAI34-noncommercial-pinned-conventional-NLI/1"})
    digest=hashlib.sha256();n=0;t0=time.monotonic()
    with urllib.request.urlopen(request,timeout=70) as inp,path.open("xb") as out:
        while True:
            block=inp.read(1024*1024)
            if not block:break
            n+=len(block)
            need(n<=limit and time.monotonic()-t0<720,"PINNED_DOWNLOAD_BUDGET")
            digest.update(block);out.write(block)
    got=digest.hexdigest()
    need(n>16 and (not expected or got==expected),"PINNED_SOURCE_CONTENT_DRIFT")
    return {"sha256":got,"bytes":n}
def label_mapping(config):
    actual=config.get("id2label")
    need(actual=={"0":"contradiction","1":"entailment","2":"neutral"},
         "EXACT_MODEL_3WAY_LABEL_MAP")
    need(config.get("model_type")=="roberta" and config.get("num_labels",3)==3,
         "MODEL_CLASSIFIER_TYPE")
    return ("NO","YES","UNKNOWN")
def data_selection(private):
    source=a33.source_download(private)
    rows=a33.source_rows(source)
    selected,manifest=a33.select(rows)
    need(manifest==ANLI_FROZEN_SELECTION,"ORIGINAL_ANLI_TASK_SELECTION_CHANGED")
    protocol=a33.prereg_digest(selected,manifest)
    need(protocol==ANLI_FROZEN_PROTOCOL,"ORIGINAL_ANLI_PROTOCOL_CHANGED")
    need(len(selected)==36,"ANLI_36_SAMPLES")
    return rows,selected
def protocol_digest(config_hash,tok_hash):
    return sha(canonical({
        "protocol":"mpai34-conventional-nli-cpu-onnx-original-human-36-v1",
        "model_repo":MODEL_REPO,"revision":MODEL_REV,
        "original_onnx_sha256":MODEL_SHA256,
        "tokenizer_sha256":tok_hash,"config_sha256":config_hash,
        "original_anli_selection":ANLI_FROZEN_SELECTION,
        "original_anli_annotated_protocol":ANLI_FROZEN_PROTOCOL,
        "label_mapping":["NO","YES","UNKNOWN"],
        "max_tokens":512,"input_truncation":"tokenizer-native-longest_first",
        "intra_op_threads":4,"inter_op_threads":1,
        "untuned_argmax":True,"temperature":None,
        "threshold_tuning":False,
        "scientific_first_use":False,"hidden_gold":False,
        "prior_phi_reference":EXPECTED_PRIOR,
        "production_authority":False,
    }).encode())
def public_markers(meta,selection_sha,config_sha,tok_sha):
    print("MPAI34_MODEL_REPO="+MODEL_REPO,flush=True)
    print("MPAI34_MODEL_PINNED_REV="+MODEL_REV,flush=True)
    print("MPAI34_AUTHENTIC_MODEL_EXPECTED_SHA256="+MODEL_SHA256,flush=True)
    print("MPAI34_CONFIG_SHA256="+config_sha,flush=True)
    print("MPAI34_TOKENIZER_SHA256="+tok_sha,flush=True)
    print("MPAI34_FROZEN_SOURCE_SELECTION_SHA256="+selection_sha,flush=True)
    print("MPAI34_PREMODEL_PROTOCOL_SHA256="+protocol_digest(config_sha,tok_sha),flush=True)
    print("MPAI34_SOURCE_INDEPENDENT_HUMAN_ANNOTATIONS=TRUE",flush=True)
    print("MPAI34_PUBLIC_DATA_NOT_HIDDEN_FIRST_USE=TRUE",flush=True)
    print("MPAI34_COMPETITOR_TRAINED_SNLI_MNLI_NOT_ANLI_BY_MODEL_CARD=TRUE",flush=True)
    print("MPAI34_MODEL_PRETRAINING_CONTAMINATION_UNVERIFIED=TRUE",flush=True)
    print("MPAI34_MODEL_LICENSE=APACHE-2.0",flush=True)
    print("MPAI34_ANLI_DATA_LICENSE=CC-BY-NC-4.0",flush=True)
def main():
    global STAGE
    parser=argparse.ArgumentParser()
    parser.add_argument("--phase",choices=("freeze","evaluate"),required=True)
    parser.add_argument("--expected-protocol",default="")
    args=parser.parse_args()
    need(os.environ.get("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE",
         "OWNER_REPOSITORY_ID")
    need(os.environ.get("GITHUB_RUN_ATTEMPT")=="1","NO_RETRIES_OR_REPLAY")
    need(not os.environ.get("OPENAI_API_KEY"),"PAID_API_FORBIDDEN")
    need(os.name=="posix","GITHUB_HOSTED_LINUX_REQUIRED")
    if args.phase=="evaluate":
        need(bool(re.fullmatch(r"[0-9a-f]{64}",args.expected_protocol)),
             "FROZEN_PROTOCOL_REQUIRED")
    STAGE="SOURCES"
    with tempfile.TemporaryDirectory(prefix="mpai34-ephemeral-custody-") as private_name:
        private=Path(private_name)
        rows,selected=data_selection(private)
        # Freeze source content identity before inspecting answers/labels.
        STAGE="MODEL_METADATA"
        confpath=private/"config.json"
        tokpath=private/"tokenizer.json"
        config_meta=download(CONFIG_FILE,confpath,10000)
        tok_meta=download(TOKENIZER_FILE,tokpath,5000000)
        config=json.loads(confpath.read_text("utf-8"))
        maplabels=label_mapping(config)
        public_markers(config_meta,ANLI_FROZEN_SELECTION,
                       config_meta["sha256"],tok_meta["sha256"])
        candidate_protocol=protocol_digest(config_meta["sha256"],tok_meta["sha256"])
        if args.phase=="freeze":
            print("MPAI34_METADATA_ONLY_TASK_SELECTION=PASS",flush=True)
            print("MPAI34_LABELS_NOT_READ_BY_PREREGISTRATION=TRUE",flush=True)
            print("MPAI34_NO_MODEL_INFERENCE_AT_FREEZE=TRUE",flush=True)
            print("MPAI34_FREEZE=PASS",flush=True)
            return
        need(candidate_protocol==args.expected_protocol,
             "LINUX_INDEPENDENT_JOB_PROTOCOL_DRIFT")
        STAGE="INDEPENDENT_GOLD_AND_MODEL"
        row_map={r["uid"]:r for r in rows}
        tasks=[]
        for one in selected:
            src=row_map[one["uid"]]
            need(src["gold_label"] in ("e","n","c"),"ORIGINAL_HUMAN_GOLD")
            p=src["context"]
            h=src["statement"]
            need(p.strip() and h.strip() and
                 len(p)<8500 and len(h)<900,"ANLI_TEXT_BUDGET")
            tasks.append((one["category"],p,h,{"e":"YES","n":"UNKNOWN","c":"NO"}[src["gold_label"]]))
        need(len(tasks)==36 and sum(x[3]=="YES" for x in tasks)==9,
             "ORIGINAL_36_GOLD_DISTRIBUTION")
        print("MPAI34_ORIGINAL_ANLI_HUMAN_GOLD_VERIFIED=PASS",flush=True)
        modelpath=private/"model-original-quantized.onnx"
        modelmeta=download(MODEL_FILE,modelpath,MODEL_MAX_BYTES,
                           expected=MODEL_SHA256)
        need(MODEL_MIN_BYTES<modelmeta["bytes"]<=MODEL_MAX_BYTES,
             "MODEL_BYTE_CAP")
        print("MPAI34_MODEL_FULL_SHA256=PASS",flush=True)
        print("MPAI34_MODEL_BYTES="+str(modelmeta["bytes"]),flush=True)
        # From here, isolate against accidental network-based model service.
        os.environ["HF_HUB_OFFLINE"]="1"
        socket.socket=lambda *a,**kw: (_ for _ in ()).throw(RuntimeError(
               "MPAI34_OFFLINE_ONLY_INFERENCE"))
        import numpy as np
        import onnxruntime as ort
        from tokenizers import Tokenizer
        start_load=time.perf_counter()
        tokenizer=Tokenizer.from_file(str(tokpath))
        tokenizer.enable_truncation(max_length=512,strategy="longest_first")
        opts=ort.SessionOptions()
        opts.intra_op_num_threads=4
        opts.inter_op_num_threads=1
        opts.graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        session=ort.InferenceSession(str(modelpath),sess_options=opts,
                      providers=["CPUExecutionProvider"])
        input_names={x.name for x in session.get_inputs()}
        need(input_names.issubset({"input_ids","attention_mask","token_type_ids"}) and
             {"input_ids","attention_mask"}.issubset(input_names),
             "QUANTIZED_ONNX_INPUT_INTERFACE")
        outputs=session.get_outputs()
        need(len(outputs)>=1,"CLASSIFICATION_OUTPUT_MISSING")
        load_ms=max(1,int((time.perf_counter()-start_load)*1000))
        STAGE="AUTHENTIC_CONVENTIONAL_INFERENCE"
        results=[]
        for family,premise,hypothesis,gold in tasks:
            started=time.perf_counter()
            tok=tokenizer.encode(premise,hypothesis)
            n=len(tok.ids)
            need(0<n<=512,"TOKEN_CONTEXT")
            data={"input_ids":np.asarray([tok.ids],dtype=np.int64),
                "attention_mask":np.asarray([tok.attention_mask],dtype=np.int64),
                "token_type_ids":np.asarray([tok.type_ids],dtype=np.int64)}
            logits=session.run(None,{k:data[k] for k in input_names})[0]
            need(logits.shape==(1,3) and bool(np.isfinite(logits).all()),
                 "THREE_WAY_LOGITS")
            label=maplabels[int(np.argmax(logits[0]))]
            elapsed=max(1,int((time.perf_counter()-started)*1000))
            results.append({"family":family,"gold":gold,
                 "pred":label,"latency_ms":elapsed,"input_tokens":n})
        need(len(results)==36,"COMPLETE_REAL_36_INFERENCE")
        # Never dump original premise/hypothesis, predicted per-example labels,
        # selected UIDs, source gold or logits. Aggregates only.
        for category in a33.SOURCE_FAMILIES:
            rr=[x for x in results if x["family"]==category]
            need(len(rr)==6,"FAMILY_SIX_ORIGINAL")
            print("MPAI34_FAMILY_"+category.upper().replace("-","_")+"="+
                  canonical({"cases":6,
                    "correct":sum(x["pred"]==x["gold"] for x in rr),
                    "hard_false_positives":sum(x["pred"]=="YES" and x["gold"]!="YES" for x in rr),
                    "valid_entailments":sum(x["gold"]=="YES" for x in rr),
                    "valid_entailments_recognized":sum(x["pred"]=="YES" and x["gold"]=="YES" for x in rr)}),
                  flush=True)
        total_correct=sum(x["pred"]==x["gold"] for x in results)
        false_positives=sum(x["pred"]=="YES" and x["gold"]!="YES" for x in results)
        positives=sum(x["pred"]=="YES" and x["gold"]=="YES" for x in results)
        print("MPAI34_NLI_MODEL_CORRECT="+str(total_correct)+"_OF_36",flush=True)
        print("MPAI34_NLI_MODEL_HARD_FALSE_POSITIVES="+str(false_positives),flush=True)
        print("MPAI34_NLI_MODEL_SUPPORTED_ENTAILMENTS="+str(positives)+"_OF_9",flush=True)
        print("MPAI34_PREVIOUS_PHI_CORRECT=16_OF_36",flush=True)
        print("MPAI34_PREVIOUS_PHI_HARD_FALSE_POSITIVES=7",flush=True)
        print("MPAI34_PREVIOUS_PHI_SUPPORTED_ENTAILMENTS=2_OF_9",flush=True)
        print("MPAI34_NLI_CPU_LOAD_MS="+str(load_ms),flush=True)
        print("MPAI34_NLI_CPU_MEDIAN_INFERENCE_MS="+str(int(statistics.median(x["latency_ms"] for x in results))),flush=True)
        print("MPAI34_NLI_CPU_TOTAL_INFERENCE_MS="+str(sum(x["latency_ms"] for x in results)),flush=True)
        print("MPAI34_NLI_CPU_PEAK_RSS_BYTES_APPROX="+str(int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024),flush=True)
        print("MPAI34_NLI_ORIGINAL_SOURCE_INFERENCE_CALLS=36",flush=True)
        print("MPAI34_ZERO_HARD_FP="+("PASS" if false_positives==0 else "FAIL"),flush=True)
        print("MPAI34_SAME_HARDWARE_LATENCY_COMPARISON=NOT_AVAILABLE",flush=True)
        print("MPAI34_MODEL_PRETRAINING_CONTAMINATION_UNVERIFIED=TRUE",flush=True)
        print("MPAI34_SCIENTIFIC_ACCEPTANCE=BLOCKED",flush=True)
        print("MPAI34_FORGE_AUTONOMY_CONTROLLER_UNMODIFIED=TRUE",flush=True)
        print("MPAI34_ACCEPTED_MINDPALACE_MEMORY_WRITES=0",flush=True)
    print("MPAI34_PRIVATE_SOURCE_MODEL_SCRATCH_REMOVED=PASS",flush=True)

if __name__=="__main__":
    try:main()
    except Exception as e:
        tag=str(e)
        safe=tag if re.fullmatch(r"MPAI34_[A-Z0-9_]{3,100}",tag) else "MPAI34_PRIVATE_EXCEPTION"
        print("MPAI34_SAFE_FAILURE="+safe,flush=True)
        print("MPAI34_SAFE_STAGE="+STAGE,flush=True)
        print("MPAI34_SAFE_TYPE="+type(e).__name__,flush=True)
        sys.exit(2)
