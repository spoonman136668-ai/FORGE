#!/usr/bin/env python3
"""G97 original GPT-2 development-only experiment.

Reuses the frozen G96 model, cohort, decoding and measurement implementation.
Adds an independently frozen development stream, G97 arm, and immutable receipts.
No protected held-out ranks are read.
"""
import hashlib, json, math, os, platform, statistics, sys, time, traceback
from pathlib import Path
import copy

HERE = Path(__file__).resolve().parent
G96 = HERE.parent / "cpu_g96"
sys.path.insert(0, str(G96))
from g96_development_original import _g95, select_cohort, build_traffic, traffic_digest, BYTE_LIMIT, POLICIES
from g96_original_adapter import run_policy, assert_parity
from g97_original_adapter import run_g97
from g97_stream_manifest import freeze, canonical_bytes, STRATA, REPETITIONS

def p95(values):
    return sorted(values)[math.ceil(.95 * len(values))-1]

def evaluate(baseline, candidate, tokens):
    bt = [row["request_wall_ns"] for rep in baseline for row in rep["rows"]]
    ct = [row["request_wall_ns"] for rep in candidate for row in rep["rows"]]
    if len(bt) != 192 or len(ct) != 192:
        raise RuntimeError("G97_PAIRED_REQUEST_COUNT_DRIFT")
    bps = statistics.median(48*tokens/(r["wall_ns"]/1e9) for r in baseline)
    cps = statistics.median(48*tokens/(r["wall_ns"]/1e9) for r in candidate)
    return {"throughput_speedup": cps/bps,
            "minimum_paired_request_speedup": min(b/c for b,c in zip(bt,ct)),
            "p95_latency_ratio": p95(ct)/p95(bt),
            "cpu_ratio": sum(r["cpu_ns"] for r in candidate)/sum(r["cpu_ns"] for r in baseline),
            "rss_ratio": max(r["max_rss"] for r in candidate)/max(r["max_rss"] for r in baseline),
            "max_resident_kv_bytes": max(r["max_resident_kv_bytes"] for r in candidate),
            "hits": sum(r["hits"] for r in candidate),
            "misses": sum(r["misses"] for r in candidate),
            "evictions": sum(r["evictions"] for r in candidate),
            "bypasses": sum(r["bypasses"] for r in candidate)}

def main():
    import torch, transformers, psutil, urllib.request
    from transformers import AutoTokenizer, AutoModelForCausalLM
    g = _g95()
    if platform.system() != "Linux" or platform.machine().lower() not in ("x86_64", "amd64"):
        raise RuntimeError("G97_ORIGINAL_CPU_LINUX_ONLY")
    if torch.__version__ != "2.5.1+cpu" or transformers.__version__ != "4.48.3" or torch.version.cuda is not None:
        raise RuntimeError("G97_RUNTIME_DRIFT")
    torch.set_num_threads(2); torch.set_num_interop_threads(1)
    proc = psutil.Process(); old = None
    receipt = {"schema":"forge.cpu-g97.development.v1", "phase":"DEVELOPMENT_ONLY",
               "source_sha":os.getenv("GITHUB_SHA", "UNSET"),
               "engineering":"UNVERIFIED", "correctness":"UNVERIFIED",
               "decision":"UNVERIFIED", "scientific_acceptance":"NOT_GRANTED",
               "promotion_allowed":False, "heldout_executed":False,
               "model_revision":g.MODEL_REV, "weights_sha256":g.WEIGHTS_SHA,
               "data_revision":g.DATA_REV, "data_sha256":g.DATA_SHA}
    try:
        req = urllib.request.Request(
            "https://raw.githubusercontent.com/openai/grade-school-math/"+g.DATA_REV+"/grade_school_math/data/test.jsonl",
            headers={"User-Agent":"FORGE-CPU-G97-DEVELOPMENT/1"})
        with urllib.request.urlopen(req,timeout=45) as f:
            data = f.read(800001)
        if len(data)!=g.DATA_BYTES or hashlib.sha256(data).hexdigest()!=g.DATA_SHA:
            raise RuntimeError("G97_DATASET_IDENTITY_DRIFT")
        records=[{"instruction":x["question"],"category":"math_word_problem"}
                 for x in (json.loads(line) for line in data.decode().splitlines() if line.strip())]
        selected=select_cohort(records,"development")
        manifest,digest=freeze(selected)
        Path("cpu_g97_development_stream.json").write_bytes(canonical_bytes(manifest))
        receipt["development_stream_sha256"]=digest
        receipt["selected_question_hashes"]=[x["instruction_sha256"] for x in selected]
        g55=g.module("g97_g55","llm_g55/g55_gpt2_controls.py")
        if (g55.REV,g55.WEIGHT_SHA)!=(g.MODEL_REV,g.WEIGHTS_SHA):
            raise RuntimeError("G97_MODEL_IDENTITY_DRIFT")
        root,model_manifest=g55.stage()
        receipt["model_manifest_sha256"]=g.sha_file(root/"manifest.json")
        tok=AutoTokenizer.from_pretrained(str(root),local_files_only=True,trust_remote_code=False)
        model=AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,use_safetensors=True,trust_remote_code=False).eval()
        old=proc.cpu_affinity()
        if len(old)<3:raise RuntimeError("G97_THREE_CPUS_REQUIRED")
        proc.cpu_affinity(old[:3]);receipt["affinity"]=proc.cpu_affinity()
        def encode(s):return tok(s,return_tensors="pt",add_special_tokens=False)["input_ids"]
        prefixes=[encode(s) for s in g.PREFIX_TEXTS]
        prefixes.extend(encode(g.PREFIX_TEXTS[i]+f" [G96_OVERFLOW_{i:02d}]") for i in range(4))
        tokfp=hashlib.sha256("".join(x["sha256"] for x in model_manifest).encode()).hexdigest()
        keys=[g.key_for(p,tokfp) for p in prefixes]
        if len(set(keys))!=8:raise RuntimeError("G97_PREFIX_KEY_COLLISION")
        suffixes=[encode(x["instruction"]) for x in selected]
        kvbytes=[]
        with torch.inference_mode():
            for prefix in prefixes:
                if int(prefix.shape[1])+max(int(s.shape[1]) for s in suffixes)+g.TOKENS>model.config.n_positions:
                    raise RuntimeError("G97_CONTEXT_OVERFLOW")
                kvbytes.append(g.tensor_tree_bytes(model(input_ids=prefix,use_cache=True).past_key_values))
        prefill=[];clone=[]
        with torch.inference_mode():
            for prefix in prefixes[:4]:
                t=time.perf_counter_ns();past=model(input_ids=prefix,use_cache=True).past_key_values
                prefill.append(time.perf_counter_ns()-t)
                t=time.perf_counter_ns();copy.deepcopy(past);clone.append(time.perf_counter_ns()-t)
        calibration={"prefix_prefill_ns":int(statistics.median(prefill)),
                     "clone_ns":int(statistics.median(clone)),"expected_reuses":2}
        receipt["calibration"]=calibration
        receipt["strata"]={}
        from g98_original_parity import compare as g98_compare
        g98_diagnostics={}
        arms=tuple(POLICIES)+("g97_overflow_bypass",)
        for stratum in STRATA:
            layout=build_traffic(stratum,cycles=1)
            if traffic_digest(layout)!=manifest["strata"][stratum]["traffic_sha256"]:
                raise RuntimeError("G97_TRAFFIC_DRIFT")
            stream=[]
            for i,item in enumerate(layout):
                pid=item["prefix_id"];qid=(i//4)%3;src=selected[(pid%4)+4*qid]
                expected=manifest["strata"][stratum]["requests"][i]
                if (expected["prefix_id"],expected["source_row"],expected["instruction_sha256"])!=(
                        pid,src["source_row"],src["instruction_sha256"]):
                    raise RuntimeError("G97_MANIFEST_STREAM_MISMATCH")
                stream.append({"prefix_id":pid,"source_row":src["source_row"],
                               "suffix":suffixes[(pid%4)+4*qid],"prefix_kv_bytes":kvbytes[pid]})
            references={}
            with torch.inference_mode():
                for i,item in enumerate(stream):
                    full=torch.cat((prefixes[item["prefix_id"]],item["suffix"]),dim=1)
                    references[i],_=g.baseline_request(model,full,g.TOKENS,torch,proc)
            reps=[]
            for rep in range(REPETITIONS):
                results={}
                order=arms if rep%2==0 else tuple(reversed(arms))
                for policy in order:
                    if policy=="g97_overflow_bypass":
                        outputs,metrics=run_g97(model,stream,prefixes,keys,torch,proc)
                    else:
                        outputs,metrics=run_policy(model,stream,prefixes,keys,policy,torch,proc,
                            calibration=calibration if policy=="cost_aware" else None)
                    assert_parity(references,outputs)
                    results[policy]=metrics
                reps.append({"rep":rep+1,"order":order,"arms":results})
            # Original G97 overflow-bypass comparison, fail closed before timing acceptance.
            g98_diagnostics[stratum]=g98_compare(
                model,stream,prefixes,keys,torch,proc,
                model_revision=receipt["model_revision"],
                weights_sha256=receipt["weights_sha256"],
                stream_sha256=receipt["development_stream_sha256"],
                reference_outputs=references,
                output_path="cpu_g98_"+stratum+"_parity.json")
            baseline=[r["arms"]["no_cache"] for r in reps]
            metrics={p:evaluate(baseline,[r["arms"][p] for r in reps],g.TOKENS) for p in arms[1:]}
            for p,m in metrics.items():
                m["qualifies"]=(m["throughput_speedup"]>=1.15
                    and m["minimum_paired_request_speedup"]>=.90
                    and m["p95_latency_ratio"]<=1.10 and m["cpu_ratio"]<=1.10
                    and m["rss_ratio"]<=1.15 and m["max_resident_kv_bytes"]<=BYTE_LIMIT)
            if stratum=="overflow":
                candidate=sum(r["arms"]["g97_overflow_bypass"]["wall_ns"] for r in reps)
                lru=sum(r["arms"]["lru"]["wall_ns"] for r in reps)
                metrics["g97_overflow_bypass"]["improves_overflow_lru"]=candidate<lru
            receipt["strata"][stratum]={"traffic_sha256":traffic_digest(layout),
                                       "repetitions":reps,"metrics":metrics,"exact_parity":True}
        qualifies=all(receipt["strata"][s]["metrics"]["g97_overflow_bypass"]["qualifies"] for s in STRATA)
        qualifies=qualifies and receipt["strata"]["overflow"]["metrics"]["g97_overflow_bypass"]["improves_overflow_lru"]
        receipt["decision"]="DEVELOPMENT_CANDIDATE" if qualifies else "DEVELOPMENT_NO_GO"
        Path("cpu_g98_development_timing.json").write_text(json.dumps({
            "schema":"forge.cpu-g98.original-development-timing.v1",
            "phase":"DEVELOPMENT_ONLY","source_sha":receipt["source_sha"],
            "development_stream_sha256":receipt["development_stream_sha256"],
            "model_revision":receipt["model_revision"],"weights_sha256":receipt["weights_sha256"],
            "heldout_executed":False,"promotion_allowed":False,
            "performance_verdict":"NOT_EVALUATED",
            "diagnostic_only":True,"strata":g98_diagnostics},sort_keys=True,indent=2)+"\n")
        receipt["engineering"]="PASS";receipt["correctness"]="PASS"
    except BaseException as e:
        receipt["error"]=type(e).__name__+": "+str(e)
        receipt["traceback_tail"]=traceback.format_exc()[-3000:]
        raise
    finally:
        if old is not None:proc.cpu_affinity(old)
        Path("cpu_g97_development_result.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")

if __name__=="__main__":main()
