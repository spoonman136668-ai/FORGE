"""G76I diagnostic-only CPU/CUDA timeline. No speedup claims."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

SCHEMA = "forge.acc.g76i.cuda-timeline.v1"

def necessary_removable_fraction(target=1.15):
    if not 1 < target < float("inf"):
        raise ValueError("INVALID_TARGET")
    return 1.0 - 1.0 / target

def validate_trace(trace: dict) -> dict:
    if not isinstance(trace, dict) or not isinstance(trace.get("traceEvents"), list):
        raise ValueError("INVALID_CHROME_TRACE")
    events = trace["traceEvents"]
    cpu = sum(1 for e in events if e.get("ph") == "X" and "cpu" in str(e.get("cat","")).lower())
    kernels = sum(1 for e in events if e.get("ph") == "X" and "kernel" in str(e.get("cat","")).lower())
    runtime = sum(1 for e in events if e.get("ph") == "X" and "cuda_runtime" in (str(e.get("cat",""))+" "+str(e.get("name",""))).lower())
    return dict(total_events=len(events), cpu_events=cpu, kernel_events=kernels,
                cuda_runtime_events=runtime, launch_overhead_fraction="UNMEASURED",
                speedup="UNMEASURED", note="Category counts are not eligible launch overhead.")

def run_timeline(model, ids, tokenizer, output_dir, *, tokens=64):
    import torch
    from torch.profiler import profile, ProfilerActivity
    if not torch.cuda.is_available() or ids.device.type != "cuda":
        raise RuntimeError("CUDA_REQUIRED")
    if next(model.parameters()).dtype != torch.float16:
        raise RuntimeError("FROZEN_FP16_REQUIRED")
    if ids.ndim != 2 or tuple(ids.shape) not in ((1,512),(1,1536)) or tokens != 64:
        raise RuntimeError("PROTOCOL_DRIFT")
    if tokenizer.eos_token_id is None:
        raise RuntimeError("TOKENIZER_EOS_REQUIRED")
    out = Path(output_dir)
    if not out.is_dir():
        raise RuntimeError("OUTPUT_DIRECTORY_REQUIRED")
    trace = out / f"g76i_cuda_trace_{ids.shape[1]}.json"
    report = out / f"g76i_report_{ids.shape[1]}.json"
    if trace.exists() or report.exists():
        raise RuntimeError("OUTPUT_COLLISION")
    kwargs = dict(input_ids=ids, do_sample=False, num_beams=1, use_cache=True,
                  max_new_tokens=64, eos_token_id=-1, pad_token_id=tokenizer.eos_token_id)
    with torch.inference_mode():
        reference = model.generate(**kwargs)
        torch.cuda.synchronize(ids.device)
        expected = reference[0,ids.shape[1]:].detach().cpu().tolist()
        if len(expected) != 64:
            raise RuntimeError("REFERENCE_TOKEN_LENGTH_DRIFT")
        with profile(activities=[ProfilerActivity.CPU,ProfilerActivity.CUDA],
                     record_shapes=False,profile_memory=False,with_stack=False) as prof:
            observed = model.generate(**kwargs)
            torch.cuda.synchronize(ids.device)
        actual = observed[0,ids.shape[1]:].detach().cpu().tolist()
    if actual != expected:
        raise RuntimeError("PROFILED_OUTPUT_MISMATCH")
    prof.export_chrome_trace(str(trace))
    raw = trace.read_bytes()
    result = dict(schema=SCHEMA,context_tokens=ids.shape[1],
                  tokens_sha256=hashlib.sha256(json.dumps(expected,separators=(",",":")).encode()).hexdigest(),
                  trace_sha256=hashlib.sha256(raw).hexdigest(),trace_bytes=len(raw),
                  summary=validate_trace(json.loads(raw)),profiled_output_parity="PASS",
                  launch_overhead_fraction="UNVERIFIED",cuda_graph_speedup="UNVERIFIED",
                  necessary_removable_fraction=necessary_removable_fraction(),
                  qualification="NOT_GRANTED")
    report.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    return result
