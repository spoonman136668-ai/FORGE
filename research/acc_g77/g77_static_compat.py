"""G77 compatibility probe. No GPU/benchmark/acceptance claim."""
import hashlib
import json

TARGET_TRANSFORMERS = '4.52.3'
TARGET_TORCH = '2.8.0+cu128'


def check_runtime(transformers_version, torch_version):
    if transformers_version != TARGET_TRANSFORMERS or torch_version != TARGET_TORCH:
        raise RuntimeError('PINNED_RUNTIME_DRIFT')


def ids_digest(ids):
    return hashlib.sha256(json.dumps(ids, separators=(',', ':')).encode()).hexdigest()


def probe(model, ids, tokenizer, *, transformers_version, torch_version):
    """Compare original greedy and static-cache decode on real pinned runtime."""
    check_runtime(transformers_version, torch_version)
    if len(ids.shape) != 2 or ids.shape[0] != 1 or ids.shape[1] not in (512, 1536):
        raise RuntimeError('SOURCE_SHAPE_DRIFT')
    if getattr(tokenizer, 'eos_token_id', None) is None:
        raise RuntimeError('EOS_REQUIRED')
    if str(next(model.parameters()).dtype) != 'torch.float16':
        raise RuntimeError('FP16_REQUIRED')
    kwargs = dict(input_ids=ids, do_sample=False, num_beams=1, use_cache=True,
                  max_new_tokens=64, eos_token_id=-1,
                  pad_token_id=tokenizer.eos_token_id)
    baseline = model.generate(**kwargs)
    static = model.generate(**kwargs, cache_implementation='static')
    output_baseline = baseline[0, ids.shape[1]:].detach().cpu().tolist()
    output_static = static[0, ids.shape[1]:].detach().cpu().tolist()
    if len(output_baseline) != 64 or len(output_static) != 64:
        raise RuntimeError('OUTPUT_LENGTH_DRIFT')
    if output_baseline != output_static:
        raise RuntimeError('STATIC_OUTPUT_MISMATCH')
    return dict(status='COMPATIBILITY_ONLY_PASS', prompt_tokens=ids.shape[1],
                output_sha256=ids_digest(output_baseline),
                static_call_executed=True, compilation='NOT_EXPLICITLY_REQUESTED',
                cache_policy_actual='UNVERIFIED', latency='UNMEASURED',
                vram='UNMEASURED', scientific_acceptance='NOT_GRANTED')
