#!/usr/bin/env python3
"""G55: bounded exact-reuse falsifier on SHA-pinned pretrained GPT-2.

No speed claims, no model modification, no science promotion. Read-only observation.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import platform
import re

REPO = 'openai-community/gpt2'
REV = '607a30d783dfa663caf39e06633721c8d4cfcd7e'
WEIGHT_SHA256 = '248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707'
WEIGHT_BLOCK_BYTES = 4096
ACTIVATION_BLOCK_VALUES = 32
SHARED_PREFIX = ('You are an assistant evaluating computational reuse. Answer precisely using the '
                 'shared requirements, preserving correctness and avoiding unsupported claims. ') * 12
SUFFIXES = (
    ' Question one: summarize the first requirement.',
    ' Question two: identify the main constraint.',
    ' Question three: explain the validation rule.',
)
INDEPENDENT = (
    'Molecular biology distinguishes the replication of DNA from the transcription of RNA. Explain the roles of enzymes and proofreading in a cell.',
    'A coastal lighthouse is repaired before a winter storm; engineers discuss foundation loads, wind pressure, and salt corrosion.',
    'A financial ledger reconciles debits and credits across business units. Describe how a transaction rollback is verified.',
)

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()

def exact_row_reuse(rows):
    seen = set()
    duplicates = 0
    for layer, row in rows:
        key = (layer, row)
        if key in seen:
            duplicates += 1
        seen.add(key)
    return {'eligible_rows': len(rows), 'duplicate_rows': duplicates,
            'duplicate_rate': duplicates / len(rows) if rows else None}

def zero_block_counts(values, block):
    if len(values) % block:
        raise ValueError('BLOCK_MISALIGNED')
    return {'values': len(values), 'exact_zero_values': sum(x == 0 for x in values),
            'blocks': len(values)//block,
            'all_zero_blocks': sum(all(x == 0 for x in values[i:i+block])
                                   for i in range(0, len(values), block))}

def duplicate_cross_layer_blocks(named_bytes, block_size):
    seen = {}
    total = distinct = same_layer = cross_layer = 0
    for layer, raw in named_bytes:
        distinct += 1
        for offset in range(0, len(raw)-len(raw)%block_size, block_size):
            chunk = raw[offset:offset+block_size]
            total += 1
            digest = hashlib.sha256(chunk).digest()
            prior = seen.get(digest)
            if prior is None:
                seen[digest] = (layer, chunk)
            else:
                first_layer, original = prior
                if original != chunk:
                    raise RuntimeError('HASH_COLLISION_BLOCK')
                if layer == first_layer:
                    same_layer += 1
                else:
                    cross_layer += 1
    return {'tensors': distinct, 'eligible_blocks': total,
            'same_layer_duplicate_blocks': same_layer,
            'cross_layer_duplicate_blocks': cross_layer,
            'cross_layer_duplicate_rate': cross_layer / total if total else None,
            'cross_layer_candidate_bytes': cross_layer * block_size}

def main():
    import torch
    import transformers
    from huggingface_hub import hf_hub_download
    from transformers import AutoTokenizer, AutoModelForCausalLM
    torch.set_num_threads(1)
    result = {'gate': 'G55', 'scope': 'PRETRAINED_GPT2_EXACT_REUSE_SCREEN_ONLY',
              'repo': REPO, 'revision': REV, 'weight_sha256_expected': WEIGHT_SHA256,
              'torch': torch.__version__, 'transformers': transformers.__version__,
              'host': platform.platform(), 'git_head': os.getenv('GITHUB_SHA'),
              'promotion_allowed': False, 'scientific_acceptance': 'NOT_GRANTED',
              'hardware_speedup': 'NOT_MEASURED', 'status': 'NOT_STARTED'}
    try:
        weight = Path(hf_hub_download(REPO, filename='model.safetensors', revision=REV, token=False))
        observed_sha = sha256_file(weight)
        if observed_sha != WEIGHT_SHA256:
            raise RuntimeError('AUTHENTIC_WEIGHT_SHA_MISMATCH')
        result.update({'weight_sha256_actual': observed_sha, 'weight_bytes': weight.stat().st_size})
        tok = AutoTokenizer.from_pretrained(REPO, revision=REV, trust_remote_code=False, token=False)
        model = AutoModelForCausalLM.from_pretrained(
            REPO, revision=REV, use_safetensors=True, trust_remote_code=False, token=False).eval()
        if model.config.model_type != 'gpt2' or model.config.n_layer != 12:
            raise RuntimeError('AUTHENTIC_MODEL_ARCHITECTURE_MISMATCH')
        prefix_len = tok(SHARED_PREFIX, add_special_tokens=False, return_tensors='pt')['input_ids'].shape[1]
        cases = [('related_' + str(i), SHARED_PREFIX+s, prefix_len) for i, s in enumerate(SUFFIXES)]
        cases.extend(('independent_' + str(i), s, 0) for i, s in enumerate(INDEPENDENT))
        eligible_rows = []
        zero_total = zero_values = zero_blocks = block_total = 0
        hook_handles = []
        current = {'offset': 0, 'case': '', 'positive': False}
        positive = {}
        try:
            for layer, block in enumerate(model.transformer.h):
                def prehook_fc(module, args, layer=layer):
                    hidden = args[0].detach().to(torch.float32).cpu().contiguous().numpy()
                    if not current['positive']:
                        for t in range(current['offset'], hidden.shape[1]):
                            eligible_rows.append((layer, hidden[0, t].tobytes()))
                    if current['positive']:
                        positive[(layer, current['case'])] = tuple(
                            hashlib.sha256(hidden[0, t].tobytes()).hexdigest()
                            for t in range(hidden.shape[1]))
                def prehook_proj(module, args, layer=layer):
                    nonlocal zero_total, zero_values, zero_blocks, block_total
                    if current['positive']:
                        return
                    x = args[0].detach().to(torch.float32).cpu().contiguous()
                    if x.shape[-1] != 3072:
                        raise RuntimeError('MLP_HIDDEN_DIMENSION_DRIFT')
                    z = x.eq(0)
                    zero_values += int(z.sum())
                    zero_total += z.numel()
                    zz = z.reshape(-1, ACTIVATION_BLOCK_VALUES)
                    zero_blocks += int(zz.all(dim=-1).sum())
                    block_total += zz.shape[0]
                hook_handles.extend([
                    block.mlp.c_fc.register_forward_pre_hook(prehook_fc),
                    block.mlp.c_proj.register_forward_pre_hook(prehook_proj)])
            with torch.inference_mode():
                for case, text, offset in cases:
                    ids = tok(text, add_special_tokens=False, return_tensors='pt')['input_ids']
                    if offset >= ids.shape[1]:
                        raise RuntimeError('INVALID_NONPREFIX_BOUNDARY')
                    current.update({'offset': offset, 'case': case, 'positive': False})
                    model(input_ids=ids, use_cache=True)
                pos_text = 'Positive control: the same exact test string.'
                for case in ('positive_a', 'positive_b'):
                    current.update({'offset': 0, 'case': case, 'positive': True})
                    model(input_ids=tok(pos_text, add_special_tokens=False,
                         return_tensors='pt')['input_ids'], use_cache=True)
        finally:
            for h in hook_handles:
                h.remove()
        positive_pass = all(positive[(layer, 'positive_a')] ==
                            positive[(layer, 'positive_b')] for layer in range(12))
        if not positive_pass:
            raise RuntimeError('REPEAT_DETECTION_POSITIVE_CONTROL_FAIL')
        result['exact_nonprefix_mlp_input'] = exact_row_reuse(eligible_rows)
        result['positive_repeat_control_12_layers'] = 'PASS'
        result['mlp_gelu_zero'] = {
            'observed_values': zero_total, 'exact_zero_values': zero_values,
            'zero_fraction': zero_values / zero_total, 'blocks_32': block_total,
            'all_zero_blocks_32': zero_blocks,
            'all_zero_block_fraction': zero_blocks / block_total}
        mats = []
        for name, p in model.named_parameters():
            if re.match(r'^transformer\.h\.\d+\.(attn\.(c_attn|c_proj)|mlp\.(c_fc|c_proj))\.weight$', name):
                layer = int(name.split('.')[2])
                mats.append((layer, p.detach().cpu().contiguous().numpy().tobytes()))
        if len(mats) != 48:
            raise RuntimeError(f'WEIGHT_MATRIX_SCOPE_DRIFT:{len(mats)}')
        result['cross_layer_weight_blocks_4096'] = duplicate_cross_layer_blocks(
            mats, WEIGHT_BLOCK_BYTES)
        result['case_specs'] = [
            {'name': case, 'prefix_tokens_excluded': offset,
             'total_tokens': len(tok(text, add_special_tokens=False)['input_ids'])}
            for case, text, offset in cases]
        h1 = result['exact_nonprefix_mlp_input']['duplicate_rate']
        h2 = result['mlp_gelu_zero']['all_zero_block_fraction']
        h3 = result['cross_layer_weight_blocks_4096']['cross_layer_duplicate_rate']
        result['screen_thresholds'] = {
            'nonprefix_exact_mlp_reuse_min': 0.01,
            'full_32_value_block_exact_zero_min': 0.05,
            'cross_layer_exact_4096byte_weight_block_min': 0.01}
        result['hypotheses'] = {
            'nonprefix_exact_mlp_reuse': 'GO' if h1 >= 0.01 else 'NO_GO',
            'exact_structured_activation_zero': 'GO' if h2 >= 0.05 else 'NO_GO',
            'exact_cross_layer_weight_block_reuse': 'GO' if h3 >= 0.01 else 'NO_GO'}
        result['status'] = 'PASS_AUTHENTIC_SCREEN'
    except Exception as e:
        result.update({'status': 'FAIL_OR_BLOCKED',
                       'error': f'{type(e).__name__}: {e}'})
        raise
    finally:
        Path('g55_result.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
        print(json.dumps({'gate': result['gate'], 'status': result['status'],
              'hypotheses': result.get('hypotheses'), 'error': result.get('error')}))

if __name__ == '__main__':
    main()
