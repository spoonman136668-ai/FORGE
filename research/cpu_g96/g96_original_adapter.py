#!/usr/bin/env python3
"""G96 original-GPT2 integration adapter. Deliberately no held-out execution."""
from __future__ import annotations
import copy, hashlib, json, time
from g96_admission import AdmissionCache, POLICIES, BYTE_LIMIT, build_traffic, traffic_digest
from pathlib import Path
import importlib.util

def _g95():
    path=Path(__file__).resolve().parents[1]/"cpu_g95"/"g95_multiprefix_lru_original.py"
    spec=importlib.util.spec_from_file_location("g96_pinned_g95",path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    if mod.SEED!=b"G68-GPT2-HELDOUT-20261030:" or mod.WEIGHTS_SHA!="248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707":
        raise RuntimeError("G96_G95_SOURCE_CONTRACT_DRIFT")
    return mod

def select_cohort(records,phase):
    """Only rank selection, no model loading or model output inspection."""
    if phase not in ("development","heldout"):raise ValueError("G96_INVALID_PHASE")
    original=_g95()
    ranked=original.rank_original(records,300)
    start=276 if phase=="development" else 288
    selected=ranked[start:start+12]
    if len(selected)!=12:raise RuntimeError("G96_COHORT_INCOMPLETE")
    if len({x["instruction_sha256"] for x in selected})!=12:raise RuntimeError("G96_COHORT_DUPLICATES")
    if {x["instruction_sha256"] for x in selected}&{x["instruction_sha256"] for x in ranked[264:276]}:
        raise RuntimeError("G96_G95_OVERLAP")
    return selected

def run_policy(model,stream,prefixes,keys,policy,torch,proc,*,calibration=None):
    """All request overhead, admission, prefix prefill, cloning and decoding is charged."""
    g95=_g95()
    cache=AdmissionCache(policy,calibration=calibration)
    outputs={};rows=[]
    start=time.perf_counter_ns();cpu0=time.process_time_ns()
    with torch.inference_mode():
        for idx,req in enumerate(stream):
            t0=time.perf_counter_ns();c0=time.process_time_ns()
            pid=req["prefix_id"];suffix=req["suffix"]
            full=torch.cat((prefixes[pid],suffix),dim=1)
            key=keys[pid]
            # Conservative immutable bound; caller must supply exact measured KV bytes.
            expected_bytes=req["prefix_kv_bytes"]
            if expected_bytes>BYTE_LIMIT:raise RuntimeError("G96_PREFIX_EXCEEDS_BUDGET")
            def build():
                result=model(input_ids=prefixes[pid],use_cache=True).past_key_values
                if g95.tensor_tree_bytes(result)!=expected_bytes:raise RuntimeError("G96_KV_SIZE_DRIFT")
                return {"past":result,"snapshot":g95.tensor_tree_digest(result)}
            entry,hit,admitted=cache.request(key,expected_bytes,build)
            clone_ns=0
            if entry is None:
                ids,m=g95.baseline_request(model,full,g95.TOKENS,torch,proc)
            else:
                tc=time.perf_counter_ns()
                request_past=copy.deepcopy(entry["past"])
                clone_ns=time.perf_counter_ns()-tc
                if g95.tensor_storage_ptrs(request_past)&g95.tensor_storage_ptrs(entry["past"]):
                    raise RuntimeError("G96_KV_STORAGE_ALIAS")
                ids,m=g95.request_decode(model,full,suffix,request_past,int(prefixes[pid].shape[1]),g95.TOKENS,torch,proc)
                if g95.tensor_tree_digest(entry["past"])!=entry["snapshot"]:
                    raise RuntimeError("G96_RESIDENT_KV_MUTATION")
            outputs[idx]=ids
            rows.append({"index":idx,"prefix_id":pid,"source_row":req["source_row"],"hit":hit,
                "admitted":admitted,"bypass":entry is None,"clone_ns":clone_ns,
                "request_wall_ns":time.perf_counter_ns()-t0,"request_cpu_ns":time.process_time_ns()-c0,
                "resident_kv_bytes":cache.resident_bytes(),"rss_bytes":proc.memory_info().rss,
                "output_sha256":hashlib.sha256(json.dumps(ids,separators=(",",":")).encode()).hexdigest()})
            if len(cache.entries)>4 or cache.resident_bytes()>BYTE_LIMIT:
                raise RuntimeError("G96_CACHE_BUDGET_VIOLATION")
    return outputs,{"wall_ns":time.perf_counter_ns()-start,"cpu_ns":time.process_time_ns()-cpu0,
        "rows":rows,"hits":cache.hits,"misses":cache.misses,"evictions":cache.evictions,
        "admissions":cache.admissions,"bypasses":cache.bypasses,
        "max_resident_kv_bytes":max((r["resident_kv_bytes"] for r in rows),default=0),
        "max_rss":max((r["rss_bytes"] for r in rows),default=0)}

def assert_parity(reference,outputs):
    if reference.keys()!=outputs.keys():raise RuntimeError("G96_RESPONSE_SET_MISMATCH")
    for k in reference:
        if reference[k]!=outputs[k]:raise RuntimeError("G96_EXACT_TOKEN_MISMATCH_"+str(k))
