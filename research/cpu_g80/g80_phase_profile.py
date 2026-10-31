#!/usr/bin/env python3
"""Original GPT-2 CPU latency phase attribution, never an accelerator or promotion."""
import hashlib,importlib.util,json,math,os,platform,statistics,time,traceback,urllib.request
from pathlib import Path

PREREG="b2d8b285b004cb2e496f7541a4c8edd5d545e329"
MODEL_REV="607a30d783dfa663caf39e06633721c8d4cfcd7e"
WEIGHTS_SHA="248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
DATA_REV="3101c7d5072418e28b9008a6636bde82a006892c"
DATA_SHA="3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14"
DATA_BYTES=749738
SEED=b"G68-GPT2-HELDOUT-20261030:"
OFFSET=120;CASES=12;REPEATS=6;TOKENS=8;PROFILE_CASES=3;CPU_BUDGET=3
PHASES=("prefill","cached_forward","token_selection")
PRIORITY={
    "cached":{"median":0.60,"per_row":0.50,"rows":9},
    "prefill":{"median":0.45,"per_row":0.40,"rows":9},
    "token":{"median":0.20,"per_row":0.15,"rows":9}}
def contract():
    assert (OFFSET,CASES,REPEATS,TOKENS,PROFILE_CASES,CPU_BUDGET)==(120,12,6,8,3,3)
    assert PHASES==("prefill","cached_forward","token_selection")
    assert PRIORITY=={"cached":{"median":.60,"per_row":.50,"rows":9},
                     "prefill":{"median":.45,"per_row":.40,"rows":9},
                     "token":{"median":.20,"per_row":.15,"rows":9}}

def hash_file(path):
    sha=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):sha.update(b)
    return sha.hexdigest()

def module(name,rel):
    path=Path(__file__).resolve().parents[1]/rel
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m

def rank_original(records,n):
    entries=[]
    for row,item in enumerate(records):
        q=item.get("instruction","")
        cat=item.get("category","")
        if isinstance(q,str) and q.strip() and isinstance(cat,str) and cat.strip():
            entries.append((hashlib.sha256(SEED+q.encode()).hexdigest(),row,q,cat))
    entries.sort(key=lambda z:(z[0],z[1]))
    seen=set();chosen=[]
    for digest,row,q,cat in entries:
        if q in seen:continue
        seen.add(q)
        chosen.append({"source_row":row,"instruction":q,"category":cat,
            "question_sha256":hashlib.sha256(q.encode()).hexdigest(),"rank_sha256":digest})
        if len(chosen)==n:break
    if len(chosen)!=n:raise RuntimeError("G80_INSUFFICIENT_ORIGINAL_HELDOUT")
    return chosen

def nearest_p95(vals):
    return sorted(vals)[max(0,math.ceil(.95*len(vals))-1)]

def phase_stats(entries):
    """Unprofiled exact partitions; fail-closed on incomplete timers."""
    if len(entries)!=CASES*REPEATS:raise RuntimeError("G80_INCOMPLETE_PAIRED_PHASE_RECORDS")
    per_row=[]
    for sample in range(CASES):
        row=[r for r in entries if r["sample"]==sample]
        if len(row)!=REPEATS or len({r["rep"] for r in row})!=REPEATS:
            raise RuntimeError("G80_WRONG_ORIGINAL_REPETITIONS")
        if len({r["tokens_sha256"] for r in row})!=1:
            raise RuntimeError("G80_ORIGINAL_OUTPUT_INCONSISTENT_ACROSS_REPETITIONS")
        for r in row:
            if set(r["phases_ns"])!=set(PHASES) or r["full_request_wall_ns"]<=0:
                raise RuntimeError("G80_INCOMPLETE_WALL_PARTITION")
            if any(not isinstance(x,int) or x<0 for x in r["phases_ns"].values()):
                raise RuntimeError("G80_NEGATIVE_OR_NONINTEGER_PHASE")
            if sum(r["phases_ns"].values())<=0 or sum(r["phases_ns"].values())>r["full_request_wall_ns"]:
                raise RuntimeError("G80_IMPOSSIBLE_PHASE_ACCOUNTING")
            if r["full_request_cpu_ns"]<0 or not all(v>=0 for v in r["cpu_phases_ns"].values()):
                raise RuntimeError("G80_INVALID_CPU_PHASE")
        v={name:statistics.median(t["phases_ns"][name]/t["full_request_wall_ns"] for t in row)
           for name in PHASES}
        per_row.append({"sample":sample,"source_row":row[0]["source_row"],
            "phase_fraction_median":v,"median_wall_ns":statistics.median(x["full_request_wall_ns"] for x in row)})
    medians={name:statistics.median(x["phase_fraction_median"][name] for x in per_row) for name in PHASES}
    count={name:0 for name in PHASES}
    count["cached_forward"]=sum(x["phase_fraction_median"]["cached_forward"]>=PRIORITY["cached"]["per_row"] for x in per_row)
    count["prefill"]=sum(x["phase_fraction_median"]["prefill"]>=PRIORITY["prefill"]["per_row"] for x in per_row)
    count["token_selection"]=sum(x["phase_fraction_median"]["token_selection"]>=PRIORITY["token"]["per_row"] for x in per_row)
    if medians["cached_forward"]>=PRIORITY["cached"]["median"] and count["cached_forward"]>=9:
        target="TARGET_CACHED_FORWARD"
    elif medians["prefill"]>=PRIORITY["prefill"]["median"] and count["prefill"]>=9:
        target="TARGET_PREFILL"
    elif medians["token_selection"]>=PRIORITY["token"]["median"] and count["token_selection"]>=9:
        target="TARGET_PYTHON_TOKEN"
    else:
        target="NO_SINGLE_DOMINANT_PHASE"
    return {"priority":target,"per_row":per_row,"median_phase_fractions":medians,
        "rows_above_frozen_cutoffs":count,
        "median_full_request_ns":statistics.median(x["full_request_wall_ns"] for x in entries),
        "p95_full_request_ns":nearest_p95([x["full_request_wall_ns"] for x in entries])}

def main():
    import torch,transformers,psutil
    from transformers import AutoTokenizer,AutoModelForCausalLM
    from torch.profiler import profile,ProfilerActivity
    contract();torch.set_num_threads(1);torch.set_num_interop_threads(1)
    proc=psutil.Process();previous_aff=None
    receipt={"schema":"forge.cpu-llm-g80.original-phase-attribution.v1",
      "gate":"CPU_G80","preregistration_commit":PREREG,
      "source_sha":os.getenv("GITHUB_SHA","UNSET"),
      "original_model_revision":MODEL_REV,"original_weight_sha256":WEIGHTS_SHA,
      "original_dataset_revision":DATA_REV,"original_dataset_sha256":DATA_SHA,
      "runtime":{"torch":torch.__version__,"transformers":transformers.__version__,
          "python":platform.python_version(),"platform":platform.platform(),
          "machine":platform.machine()},
      "engineering":"UNVERIFIED","performance":"NOT_EVALUATED",
      "scientific_acceptance":"NOT_GRANTED","promotion_allowed":False,
      "priority":"UNVERIFIED",
      "caveats":["Profiler self-CPU event time is NOT unprofiled wall and should not be divided into it",
                 "Standalone 8-token original FP32 GPT2 CPU decode, no HTTP/service/energy/GPU extrapolation",
                 "Source-family overlap with prior GSM8K research but fixed disjoint original questions",
                 "No proposed mechanism, accelerator, token-accuracy change or accepted scientific improvement",
                 "Sampled process RSS is not physical peak"]}
    try:
        raw=Path("cpu_g80_original_gsm8k.jsonl")
        req=urllib.request.Request("https://raw.githubusercontent.com/openai/grade-school-math/"+
               DATA_REV+"/grade_school_math/data/test.jsonl",
               headers={"User-Agent":"FORGE-CPU-G80-Original-Profiler/1"})
        with urllib.request.urlopen(req,timeout=45) as inp,raw.open("xb") as out:
            total=0
            while True:
                b=inp.read(1<<20)
                if not b:break
                total+=len(b)
                if total>800000:raise RuntimeError("G80_ORIGINAL_DATASET_TOO_LARGE")
                out.write(b)
        if raw.stat().st_size!=DATA_BYTES or hash_file(raw)!=DATA_SHA:
            raise RuntimeError("G80_ORIGINAL_DATASET_SHA_FAIL")
        with raw.open(encoding="utf-8") as f:
            records=[{"instruction":v["question"],"category":"math_word_problem"}
                     for v in (json.loads(line) for line in f if line.strip())]
        ranked=rank_original(records,OFFSET+CASES)
        g68=module("g80_g68","llm_g68/g68_gsm8k_http.py")
        g70=module("g80_g70","llm_g70/g70_gsm8k_locality.py")
        if (ranked[:12]!=g68.select_heldout(records) or
            ranked[12:24]!=g70.select_heldout(records) or
            len({v["source_row"] for v in ranked})!=OFFSET+CASES):
            raise RuntimeError("G80_RANK_CUSTODY_DRIFT")
        selected=ranked[OFFSET:OFFSET+CASES]
        receipt["heldout_ranks"]=[OFFSET,OFFSET+CASES-1]
        receipt["heldout"]=[{k:v for k,v in d.items() if k!="instruction"} for d in selected]
        g55=module("g80_g55","llm_g55/g55_gpt2_controls.py")
        if (g55.REV,g55.WEIGHT_SHA)!=(MODEL_REV,WEIGHTS_SHA):
            raise RuntimeError("G80_MODEL_SOURCE_IDENTITY_FAIL")
        st=time.perf_counter();root,manifest=g55.stage()
        receipt["model_stage_s"]=time.perf_counter()-st
        receipt["model_manifest_sha256"]=hash_file(root/"manifest.json")
        receipt["model_files"]=manifest
        tokenizer=AutoTokenizer.from_pretrained(str(root),trust_remote_code=False,local_files_only=True)
        model=AutoModelForCausalLM.from_pretrained(str(root),trust_remote_code=False,
                   local_files_only=True,use_safetensors=True).eval()
        if model.config.model_type!="gpt2" or next(model.parameters()).dtype!=torch.float32:
            raise RuntimeError("G80_NOT_ORIGINAL_GPT2_FP32")
        if not hasattr(proc,"cpu_affinity"):raise RuntimeError("G80_AFFINITY_NOT_SUPPORTED")
        previous_aff=proc.cpu_affinity()
        if len(previous_aff)<CPU_BUDGET:raise RuntimeError("G80_THREE_LOGICAL_CPUS_UNAVAILABLE")
        proc.cpu_affinity(previous_aff[:CPU_BUDGET])
        receipt["cpu_affinity"]=proc.cpu_affinity()
        receipt["torch_threads"]=torch.get_num_threads()
        receipt["torch_interop_threads"]=torch.get_num_interop_threads()
        def ids(t):return tokenizer(t,return_tensors="pt",add_special_tokens=False)["input_ids"]
        def original_decode(full):
            phases={name:0 for name in PHASES};cpu={name:0 for name in PHASES}
            wall_start=time.perf_counter_ns();cpu_start=time.process_time_ns()
            with torch.inference_mode():
                p0=time.perf_counter_ns();c0=time.process_time_ns()
                out=model(input_ids=full,use_cache=True)
                phases["prefill"]+=time.perf_counter_ns()-p0
                cpu["prefill"]+=time.process_time_ns()-c0
                past,logits=out.past_key_values,out.logits[:,-1,:]
                chosen=[]
                for step in range(TOKENS):
                    p0=time.perf_counter_ns();c0=time.process_time_ns()
                    token=logits.argmax(-1,keepdim=True)
                    chosen.append(token)
                    phases["token_selection"]+=time.perf_counter_ns()-p0
                    cpu["token_selection"]+=time.process_time_ns()-c0
                    if step+1<TOKENS:
                        p0=time.perf_counter_ns();c0=time.process_time_ns()
                        mask=torch.ones((1,int(full.shape[1])+step+1),dtype=torch.long)
                        out=model(input_ids=token,past_key_values=past,attention_mask=mask,use_cache=True)
                        phases["cached_forward"]+=time.perf_counter_ns()-p0
                        cpu["cached_forward"]+=time.process_time_ns()-c0
                        past,logits=out.past_key_values,out.logits[:,-1,:]
                p0=time.perf_counter_ns();c0=time.process_time_ns()
                token_ids=torch.cat(chosen,dim=1).flatten().tolist()
                phases["token_selection"]+=time.perf_counter_ns()-p0
                cpu["token_selection"]+=time.process_time_ns()-c0
            wall_ns=time.perf_counter_ns()-wall_start
            proc_ns=time.process_time_ns()-cpu_start
            return {"tokens":token_ids,"phases_ns":phases,"cpu_phases_ns":cpu,
                    "full_request_wall_ns":wall_ns,"full_request_cpu_ns":proc_ns,
                    "rss_sample_bytes":proc.memory_info().rss}
        public=ids("A public nonheldout original warmup for latency attribution.")
        for _ in range(3):original_decode(public)
        prompts=[]
        for item in selected:
            full=torch.cat((ids(g55.PREFIX),ids(item["instruction"])[:,:64]),dim=1)
            if full.shape[1]+TOKENS>model.config.n_positions:raise RuntimeError("G80_CONTEXT_OVERFLOW")
            prompts.append((item["source_row"],full))
        records_out=[]
        for i,(source_row,full) in enumerate(prompts):
            for rep in range(REPEATS):
                out=original_decode(full)
                if len(out["tokens"])!=TOKENS:raise RuntimeError("G80_WRONG_TOKEN_COUNT")
                records_out.append({"sample":i,"source_row":source_row,"rep":rep+1,
                    "input_token_count":int(full.shape[1]),
                    "original_input_sha256":hashlib.sha256(full.numpy().tobytes()).hexdigest(),
                    "tokens_sha256":hashlib.sha256(json.dumps(out.pop("tokens"),separators=(",",":")).encode()).hexdigest(),
                    **out})
        summary=phase_stats(records_out)
        # Profiler is diagnostic; run only after all authoritative unprofiled timings.
        profiles=[]
        for i,(source_row,full) in enumerate(prompts[:PROFILE_CASES]):
            with profile(activities=[ProfilerActivity.CPU],record_shapes=False,
                         profile_memory=False,with_stack=False) as prof:
                q=original_decode(full)
            prior=records_out[i*REPEATS]["tokens_sha256"]
            digest=hashlib.sha256(json.dumps(q["tokens"],separators=(",",":")).encode()).hexdigest()
            if digest!=prior:raise RuntimeError("G80_PROFILER_CHANGES_ORIGINAL_OUTPUT")
            keys=prof.key_averages()
            operators=sorted(
                ({"op":str(k.key),"calls":int(k.count),"self_cpu_time_us":float(k.self_cpu_time_total)}
                 for k in keys),
                key=lambda x:-x["self_cpu_time_us"])
            profiles.append({"sample":i,"source_row":source_row,
                "original_output_sha256":digest,"event_count":len(operators),
                "operator_total_self_cpu_us":sum(x["self_cpu_time_us"] for x in operators),
                "top_20_operators":operators[:20],
                "profiled_wall_ns_NOT_comparable":q["full_request_wall_ns"]})
        if len(profiles)!=PROFILE_CASES or any(p["event_count"]==0 for p in profiles):
            raise RuntimeError("G80_NO_ORIGINAL_TORCH_PROFILER_EVENTS")
        receipt["original_unprofiled_responses"]=records_out
        receipt["original_profiler_diagnostics"]=profiles
        receipt["summary"]=summary
        receipt["priority"]=summary["priority"]
        receipt["engineering"]="PASS"
    except BaseException as exc:
        receipt["error"]=type(exc).__name__+": "+str(exc)
        receipt["traceback_tail"]=traceback.format_exc()[-2600:]
        raise
    finally:
        if previous_aff is not None:
            receipt["affinity_end"]=proc.cpu_affinity()
            proc.cpu_affinity(previous_aff)
        Path("cpu_g80_original_result.json").write_text(
            json.dumps(receipt,indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8")
        print(json.dumps({k:receipt.get(k) for k in ("gate","engineering","priority","summary","error")},sort_keys=True),flush=True)

if __name__=="__main__":main()
