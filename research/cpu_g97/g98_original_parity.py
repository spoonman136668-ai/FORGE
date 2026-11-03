#!/usr/bin/env python3
"""G98 guarded original-model parity comparison; development-only.

Caller supplies the pinned original G97 model, frozen development stream and
reference outputs. This module never selects protected cohorts or promotes.
"""
import hashlib,json,os,platform,time
from pathlib import Path
from g97_original_adapter import run_g97
from g98_timing_probe import run_instrumented

COUNTERS=("hits","misses","evictions","admissions","bypasses","max_resident_kv_bytes")
ROW_FIELDS=("index","prefix_id","source_row","hit","admitted","bypass",
            "resident_kv_bytes","output_sha256")

def compare(model,stream,prefixes,keys,torch,proc,*,model_revision,weights_sha256,
            stream_sha256,reference_outputs,output_path):
    if os.getenv("G98_DEVELOPMENT_ONLY")!="1":
        raise RuntimeError("G98_DEVELOPMENT_ONLY_GUARD")
    sha=os.getenv("GITHUB_SHA")
    if not sha or len(sha)!=40 or any(c not in "0123456789abcdef" for c in sha):
        raise RuntimeError("G98_SOURCE_IDENTITY_MISSING")
    if len(stream)!=48 or not model_revision or len(weights_sha256)!=64 or len(stream_sha256)!=64:
        raise RuntimeError("G98_FROZEN_INPUT_IDENTITY_MISSING")
    receipt={"schema":"forge.cpu-g98.original-parity.v1","phase":"DEVELOPMENT_ONLY",
             "source_sha":sha,"model_revision":model_revision,
             "weights_sha256":weights_sha256,"development_stream_sha256":stream_sha256,
             "platform":platform.platform(),"heldout_executed":False,
             "promotion_allowed":False,"parity":"UNVERIFIED","timing_accepted":False}
    try:
        with torch.inference_mode():
            plain,baseline=run_g97(model,stream,prefixes,keys,torch,proc)
            instrumented,measured,timing=run_instrumented(model,stream,prefixes,keys,torch,proc)
        if plain!=reference_outputs or instrumented!=plain:
            raise RuntimeError("G98_EXACT_TOKEN_PARITY_FAIL")
        if any(baseline[k]!=measured[k] for k in COUNTERS):
            raise RuntimeError("G98_CACHE_COUNTER_PARITY_FAIL")
        if len(baseline["rows"])!=len(measured["rows"]) or any(
            any(a[k]!=b[k] for k in ROW_FIELDS)
            for a,b in zip(baseline["rows"],measured["rows"])):
            raise RuntimeError("G98_CACHE_ROW_OR_KV_STATE_PARITY_FAIL")
        if len(timing["durations_ns"]["kv_clone"])!=sum(x["hit"] or x["admitted"] for x in measured["rows"]):
            raise RuntimeError("G98_CLONE_EVENT_DRIFT")
        receipt.update(parity="PASS",timing_accepted=True,timing=timing,
                       cache_counters={k:measured[k] for k in COUNTERS},
                       output_digest=hashlib.sha256(json.dumps(instrumented,sort_keys=True).encode()).hexdigest())
    except BaseException as exc:
        receipt["error"]=type(exc).__name__+": "+str(exc)
        raise
    finally:
        Path(output_path).write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    return receipt
