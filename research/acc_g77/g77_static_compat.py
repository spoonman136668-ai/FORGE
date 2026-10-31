"""G77 static KV compatibility: fail-closed diagnostics, not a benchmark."""
import hashlib
import json

TARGET_TRANSFORMERS = "4.52.3"
TARGET_TORCH = "2.8.0+cu128"

def check_runtime(transformers_version=None, torch_version=None):
    import torch
    import transformers
    actual_transformers = transformers.__version__
    actual_torch = torch.__version__
    if actual_transformers != TARGET_TRANSFORMERS or actual_torch != TARGET_TORCH:
        raise RuntimeError("PINNED_RUNTIME_DRIFT")
    if transformers_version is not None and transformers_version != actual_transformers:
        raise RuntimeError("CALLER_TRANSFORMERS_VERSION_DRIFT")
    if torch_version is not None and torch_version != actual_torch:
        raise RuntimeError("CALLER_TORCH_VERSION_DRIFT")
    return actual_transformers, actual_torch

def ids_digest(ids):
    return hashlib.sha256(json.dumps(ids, separators=(",", ":")).encode()).hexdigest()

def probe(model, ids, tokenizer, *, transformers_version=None, torch_version=None):
    """Check exact greedy outputs on actual pinned CUDA FP16 runtime."""
    import torch
    check_runtime(transformers_version, torch_version)
    if not torch.cuda.is_available() or ids.device.type != "cuda":
        raise RuntimeError("CUDA_REQUIRED")
    if len(ids.shape) != 2 or ids.shape[0] != 1 or ids.shape[1] not in (512, 1536):
        raise RuntimeError("SOURCE_SHAPE_DRIFT")
    if getattr(tokenizer, "eos_token_id", None) is None:
        raise RuntimeError("EOS_REQUIRED")
    parameters = list(model.parameters())
    if not parameters or any(p.device.type != "cuda" for p in parameters):
        raise RuntimeError("CUDA_MODEL_REQUIRED")
    if any(p.is_floating_point() and p.dtype != torch.float16 for p in parameters):
        raise RuntimeError("FP16_REQUIRED")
    if model.training:
        raise RuntimeError("EVAL_MODE_REQUIRED")
    kwargs = dict(input_ids=ids, do_sample=False, num_beams=1, use_cache=True,
                  max_new_tokens=64, eos_token_id=-1,
                  pad_token_id=tokenizer.eos_token_id)
    with torch.inference_mode():
        baseline = model.generate(**kwargs)
        torch.cuda.synchronize(ids.device)
        static = model.generate(**kwargs, cache_implementation="static")
        torch.cuda.synchronize(ids.device)
    output_baseline = baseline[0, ids.shape[1]:].detach().cpu().tolist()
    output_static = static[0, ids.shape[1]:].detach().cpu().tolist()
    if len(output_baseline) != 64 or len(output_static) != 64:
        raise RuntimeError("OUTPUT_LENGTH_DRIFT")
    if output_baseline != output_static:
        raise RuntimeError("STATIC_OUTPUT_MISMATCH")
    return dict(status="OUTPUT_PARITY_PASS_CACHE_POLICY_UNVERIFIED",
                prompt_tokens=ids.shape[1], output_sha256=ids_digest(output_baseline),
                static_call_executed=True, compilation="NOT_EXPLICITLY_REQUESTED",
                cache_policy_actual="UNVERIFIED", latency="UNMEASURED",
                vram="UNMEASURED", scientific_acceptance="NOT_GRANTED")
