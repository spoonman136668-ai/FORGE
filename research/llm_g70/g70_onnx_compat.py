#!/usr/bin/env python3
"""G70: original-GPT2 vs independently exported ONNX Runtime CPU backend.

Research-only, no production performance or scientific acceptance. All
negative/source-dependency/export outcomes are retained as JSON artifacts.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import time

PREREG="51469831afc16ff1fd320656c2bd3960c4e812d6"
BASE="a3ef4e4d7fb16211367ebbdfa9367cc862ceb02f"
MODEL_REV="607a30d783dfa663caf39e06633721c8d4cfcd7e"
WEIGHTS_SHA="248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
DATA_REV="3101c7d5072418e28b9008a6636bde82a006892c"
DATA_SHA="3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14"
DATA_SIZE=749738
POSITIONS=(0,5,11)
COHORTS=("high_shared_system","unique_system")
TOKENS=8
REPEATS=2
CPU_BUDGET=3

def load(name,relative):
    p=Path(__file__).resolve().parents[1]/relative
    s=importlib.util.spec_from_file_location(name,p)
    mod=importlib.util.module_from_spec(s);s.loader.exec_module(mod)
    return mod

def file_sha(path):
    digest=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(1048576),b""):
            digest.update(block)
    return digest.hexdigest()

def sha_tokens(ids):
    return hashlib.sha256(json.dumps(ids,separators=(",",":")).encode()).hexdigest()

def pure_contract():
    assert POSITIONS==(0,5,11) and len(COHORTS)*len(POSITIONS)==6
    assert REPEATS==2 and TOKENS==8 and CPU_BUDGET==3
    assert MODEL_REV=="607a30d783dfa663caf39e06633721c8d4cfcd7e"
    assert DATA_SIZE==749738
    assert PREREG=="51469831afc16ff1fd320656c2bd3960c4e812d6"

def main():
    import urllib.request
    import psutil
    import torch
    import transformers
    from transformers import AutoModelForCausalLM,AutoTokenizer
    pure_contract()
    g55=load("g55_g70","llm_g55/g55_gpt2_controls.py")
    g68=load("g68_g70","llm_g68/g68_gsm8k_http.py")
    if not (g55.REV==g68.MODEL_REV==MODEL_REV and
            g55.WEIGHT_SHA==g68.WEIGHTS_SHA==WEIGHTS_SHA and
            g68.DATA_REV==DATA_REV and g68.DATA_SHA==DATA_SHA):
        raise RuntimeError("ORIGINAL_PINNED_SOURCE_IDENTITY_MISMATCH")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    report={
        "gate":"G70","source_sha":os.getenv("GITHUB_SHA","UNSET"),
        "preregistration_commit":PREREG,"prior_source_sha":BASE,
        "kind":"EXTERNAL_ONNXRUNTIME_GPT2_CPU_BACKEND_FEASIBILITY_NOT_SERVING",
        "model_revision":MODEL_REV,"model_weights_sha256":WEIGHTS_SHA,
        "dataset_revision":DATA_REV,"dataset_sha256":DATA_SHA,
        "torch":torch.__version__,"transformers":transformers.__version__,
        "host":platform.platform(),"cpu_budget":CPU_BUDGET,
        "positions":POSITIONS,"cohorts":COHORTS,"tokens":TOKENS,"repeats":REPEATS,
        "engineering":"UNVERIFIED","backend_feasibility":"UNVERIFIED",
        "performance_acceptance":"NOT_EVALUATED",
        "scientific_acceptance":"NOT_GRANTED","promotion_allowed":False,
        "limitations":[
            "Output parity/export-only check, NOT a production optimized server or concurrent speedup screen",
            "Only three pinned heldout human questions per artificial prefix cohort",
            "Same host, no independent serving workload or cross-host replication",
            "No dynamical batching, GPU, energy, exact physical memory peak or native model integration"
        ]
    }
    proc=psutil.Process()
    original_affinity=None
    try:
        if not hasattr(proc,"cpu_affinity"):
            raise RuntimeError("CPU_AFFINITY_UNAVAILABLE")
        original_affinity=proc.cpu_affinity()
        if len(original_affinity)<CPU_BUDGET:
            raise RuntimeError("INSUFFICIENT_CPU_BUDGET")
        proc.cpu_affinity(original_affinity[:CPU_BUDGET])
        report["cpu_affinity_verified"]=proc.cpu_affinity()
        if report["cpu_affinity_verified"]!=original_affinity[:CPU_BUDGET]:
            raise RuntimeError("CPU_AFFINITY_IDENTITY_DRIFT")

        # Independent frozen original dataset, before extracting any questions.
        src=("https://raw.githubusercontent.com/openai/grade-school-math/"
             +DATA_REV+"/grade_school_math/data/test.jsonl")
        dataset=Path("g70_original_heldout_gsm8k.jsonl")
        req=urllib.request.Request(src,headers={"User-Agent":"FORGE-G70-PINNED-ORIGINAL-GSM8K/1"})
        with urllib.request.urlopen(req,timeout=45) as resp, dataset.open("xb") as w:
            total=0
            while True:
                block=resp.read(1048576)
                if not block:break
                total+=len(block)
                if total>800000:raise RuntimeError("HELDOUT_DATASET_MAXIMUM_SIZE_BREACH")
                w.write(block)
        if dataset.stat().st_size!=DATA_SIZE or file_sha(dataset)!=DATA_SHA:
            raise RuntimeError("ORIGINAL_HELDOUT_DATASET_BYTES_MISMATCH")
        report["dataset_transport"]="ARCHIVED_ORIGINAL_GITHUB_SHA256_PASS"
        with dataset.open("r",encoding="utf-8") as f:
            rows=[{"instruction":v["question"],"category":"math_word_problem"} for v in
                  (json.loads(line) for line in f if line.strip())]
        chosen=g68.select_heldout(rows)
        report["selected_original_rows"]=[chosen[pos]["source_row"] for pos in POSITIONS]
        report["heldout_question_sha256"]=[chosen[pos]["instruction_sha256"] for pos in POSITIONS]
        root,original_files=g55.stage()
        report["model_files"]=original_files
        report["original_model_manifest_sha256"]=file_sha(root/"manifest.json")
        model=AutoModelForCausalLM.from_pretrained(str(root),trust_remote_code=False,
                   local_files_only=True,use_safetensors=True).eval()
        tokenizer=AutoTokenizer.from_pretrained(str(root),trust_remote_code=False,
                                               local_files_only=True)
        if model.config.model_type!="gpt2" or next(model.parameters()).dtype!=torch.float32:
            raise RuntimeError("WRONG_MODEL_ORIGINAL_DTYPE")
        def tok(text):
            return tokenizer(text,return_tensors="pt",add_special_tokens=False)["input_ids"]
        public=tok(g55.PREFIX)
        tasks=[]
        for name in COHORTS:
            for pos in POSITIONS:
                instruction=tok(chosen[pos]["instruction"])[:,:64]
                system=public if name=="high_shared_system" else tok(f"You are a concise assistant. Account {pos:02d}. ")
                whole=torch.cat((system,instruction),dim=1)
                if whole.shape[1]+TOKENS>model.config.n_positions:
                    raise RuntimeError("GPT2_CONTEXT_LIMIT")
                tasks.append({"cohort":name,"position":pos,"ids":whole,
                              "sha256":hashlib.sha256(whole.numpy().tobytes()).hexdigest()})
        report["prompt_input_sha256"]=[{"cohort":t["cohort"],"position":t["position"],
                                         "sha256":t["sha256"]} for t in tasks]

        def generation(backend,inp):
            start=time.perf_counter()
            with torch.inference_mode():
                out=backend.generate(input_ids=inp,do_sample=False,num_beams=1,
                    max_new_tokens=TOKENS,min_new_tokens=TOKENS,use_cache=True,
                    pad_token_id=tokenizer.eos_token_id,eos_token_id=None)
            if out.shape[-1]!=inp.shape[1]+TOKENS:
                raise RuntimeError("GENERATION_LENGTH_NOT_EIGHT")
            result=out[0,inp.shape[1]:].detach().cpu().tolist()
            return result,time.perf_counter()-start

        def manual(inp):
            # Original G68 incremental cached decoder; exact 8-token greedy.
            elapsed=0.
            with torch.inference_mode():
                first=model(input_ids=inp,use_cache=True)
                past,logits=first.past_key_values,first.logits[:,-1,:]
                made=[]
                context=inp.shape[1]
                for step in range(TOKENS):
                    item=logits.argmax(-1,keepdim=True)
                    made.append(int(item[0,0]))
                    if step<TOKENS-1:
                        next_step=model(input_ids=item,past_key_values=past,
                            attention_mask=torch.ones((1,context+step+1),dtype=torch.long),
                            use_cache=True)
                        past,logits=next_step.past_key_values,next_step.logits[:,-1,:]
                return made

        with torch.inference_mode():
            model(input_ids=tok("This is a public pretrained GPT2 compatibility warmup."),use_cache=True)

        # All original source and token identities verified BEFORE export.
        report["export_status"]="STARTED"
        export_start=time.perf_counter()
        cpu_start=time.process_time()
        try:
            import optimum
            import onnx
            import onnxruntime
            from optimum.onnxruntime import ORTModelForCausalLM
            report["onnx_version"]=onnx.__version__
            report["ort_version"]=onnxruntime.__version__
            try:
                from importlib.metadata import version
                report["optimum_version"]=version("optimum")
            except Exception:
                report["optimum_version"]="UNREPORTED"
            if report["onnx_version"]!="1.17.0" or report["ort_version"]!="1.20.1" or report["optimum_version"]!="1.24.0":
                raise RuntimeError("PINNED_ONNX_VERSION_MISMATCH")
            options=onnxruntime.SessionOptions()
            options.intra_op_num_threads=1
            options.inter_op_num_threads=1
            options.graph_optimization_level=onnxruntime.GraphOptimizationLevel.ORT_ENABLE_ALL
            ort=ORTModelForCausalLM.from_pretrained(str(root),export=True,
                use_cache=True,use_merged=False,provider="CPUExecutionProvider",
                session_options=options,use_io_binding=False,
                local_files_only=True,trust_remote_code=False)
            providers=[]
            graphs=[]
            dirs=[Path(str(ort.model_save_dir)),Path(str(root))]
            for d in dirs:
                if d.exists():
                    for p in d.rglob("*.onnx"):
                        if p.is_file():
                            providers.append(p)
            for p in sorted(set(providers)):
                graphs.append({"name":p.name,"size_bytes":p.stat().st_size,
                               "sha256":file_sha(p)})
            if not graphs:raise RuntimeError("ONNX_EXPORTED_GRAPH_MISSING")
            report["onnx_graph_files"]=graphs
            provider_names=set()
            for attr in ("model","model_with_past","decoder","decoder_with_past"):
                session=getattr(ort,attr,None)
                if hasattr(session,"get_providers"):
                    provider_names.update(session.get_providers())
            if "CPUExecutionProvider" not in provider_names or provider_names-{"CPUExecutionProvider"}:
                raise RuntimeError("NOT_CPU_ONLY_ONNX_EXECUTION_PROVIDER")
            report["ort_activated_providers"]=sorted(provider_names)
            report["export_status"]="PASS"
        except BaseException as e:
            report["export_status"]="BLOCKED_EXPORT"
            report["error"]=type(e).__name__+": "+str(e)
            raise
        finally:
            report["onnx_export_wall_s"]=time.perf_counter()-export_start
            report["onnx_export_process_cpu_s"]=time.process_time()-cpu_start

        report["ort_inference_results"]=[]
        for t in tasks:
            baseline,baseline_wall=generation(model,t["ids"])
            incremental=manual(t["ids"])
            if baseline!=incremental:
                raise RuntimeError("ORIGINAL_PT_REFERENCE_MANUAL_TOKEN_PARITY_FAIL")
            pair={"cohort":t["cohort"],"position":t["position"],
                  "input_sha256":t["sha256"],"reference_token_sha256":sha_tokens(baseline),
                  "pt_reference_elapsed_s":baseline_wall,"runs":[]}
            for n in range(REPEATS):
                observed,elapsed=generation(ort,t["ids"])
                if observed!=baseline:
                    report["backend_feasibility"]="FAIL_PARITY"
                    raise RuntimeError("ORT_GREEDY_OUTPUT_MISMATCH_"+t["cohort"]+"_"+str(t["position"]))
                pair["runs"].append({"iteration":n+1,"tokens_sha256":sha_tokens(observed),
                                     "elapsed_s":elapsed})
            report["ort_inference_results"].append(pair)
        if proc.cpu_affinity()!=original_affinity[:CPU_BUDGET]:
            raise RuntimeError("CPU_AFFINITY_DRIFT_AFTER_INFERENCE")
        report["engineering"]="PASS"
        report["backend_feasibility"]="PASS"
        report["process_rss_sample_bytes"]=proc.memory_info().rss
    except BaseException as e:
        if not report.get("error"):
            report["error"]=type(e).__name__+": "+str(e)
        if report["backend_feasibility"]=="UNVERIFIED":
            report["backend_feasibility"]="BLOCKED_ENV_OR_BACKEND"
        raise
    finally:
        if original_affinity is not None:
            proc.cpu_affinity(original_affinity)
        Path("g70_result.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
        print(json.dumps({k:report.get(k) for k in ("gate","engineering","backend_feasibility",
              "export_status","error","performance_acceptance","scientific_acceptance")},sort_keys=True))

if __name__=="__main__":
    main()
