#!/usr/bin/env python3
"""G54 independent authentic GPT-2 cache-reuse screen, NOT G51 source equivalence.

Research-only; model is SHA-pinned, both arms use identical manual cached decode.
No model training, FORGE runtime access, acceptance, dispatch, or promotion.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import time

REPO = 'openai-community/gpt2'
REV = '607a30d783dfa663caf39e06633721c8d4cfcd7e'
WEIGHT_SHA = '248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707'
FILES = ('config.json', 'generation_config.json', 'merges.txt', 'model.safetensors',
         'tokenizer.json', 'tokenizer_config.json', 'vocab.json')
PREFIX = ('You are an assistant evaluating computational reuse. Answer precisely using the '
          'shared requirements, preserving correctness and avoiding unsupported claims. ') * 12
SUFFIXES = (' Question one: summarize the first requirement.',
            ' Question two: identify the main constraint.',
            ' Question three: explain the validation rule.')
TOKENS = 32
REPEATS = 5


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for data in iter(lambda: f.read(1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


def main():
    import torch
    import transformers
    from huggingface_hub import hf_hub_download
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(1)
    root = Path('g54_frozen_model')
    root.mkdir(exist_ok=False)
    receipt = {'gate': 'G54', 'type': 'INDEPENDENT_GPT2_SCREEN_NOT_FROZEN_G51_EXECUTION',
               'model_repo': REPO, 'revision': REV, 'weight_sha256': WEIGHT_SHA,
               'torch': torch.__version__, 'transformers': transformers.__version__,
               'platform': platform.platform(), 'commit': os.getenv('GITHUB_SHA', ''),
               'correctness': 'UNVERIFIED', 'acceleration': 'UNVERIFIED',
               'scientific_acceptance': 'NOT_GRANTED', 'promotion_allowed': False}
    try:
        files = []
        for name in FILES:
            f = Path(hf_hub_download(repo_id=REPO, revision=REV, filename=name, token=False))
            dest = root / name
            with f.open('rb') as inp, dest.open('xb') as out:
                for block in iter(lambda: inp.read(1024 * 1024), b''):
                    out.write(block)
            files.append({'path': name, 'sha256': sha256(dest), 'size': dest.stat().st_size})
        if next(item for item in files if item['path'] == 'model.safetensors')['sha256'] != WEIGHT_SHA:
            raise RuntimeError('WEIGHT_IDENTITY_FAILURE')
        (root / 'manifest.json').write_text(json.dumps({'revision': REV, 'files': files}, sort_keys=True))
        receipt['manifest_sha256'] = sha256(root / 'manifest.json')
        receipt['files'] = files
        tok = AutoTokenizer.from_pretrained(str(root), local_files_only=True, trust_remote_code=False)
        model = AutoModelForCausalLM.from_pretrained(str(root), local_files_only=True,
                                                    trust_remote_code=False, use_safetensors=True).eval()
        if model.config.model_type != 'gpt2' or model.config.is_encoder_decoder:
            raise RuntimeError('ARCHITECTURE_MISMATCH')

        def ids(s):
            return tok(s, return_tensors='pt', add_special_tokens=False)['input_ids']

        prefix = ids(PREFIX)
        suffixes = [ids(x) for x in SUFFIXES]
        fulls = [torch.cat((prefix, x), dim=1) for x in suffixes]
        if max(x.shape[1] for x in fulls) + TOKENS > model.config.n_positions:
            raise RuntimeError('CONTEXT_LENGTH_EXCEEDED')

        def decode(start, past=None, total_prefix=0):
            seen = total_prefix + start.shape[1]
            kw = {'input_ids': start, 'use_cache': True}
            if past is not None:
                kw['past_key_values'] = copy.deepcopy(past)
                kw['attention_mask'] = torch.ones((1, seen), dtype=torch.long)
            out = model(**kw)
            state = out.past_key_values
            logits = out.logits[:, -1, :]
            tokens = []
            for i in range(TOKENS):
                token = logits.argmax(-1, keepdim=True)
                tokens.append(token)
                if i < TOKENS - 1:
                    attention = torch.ones((1, seen + i + 1), dtype=torch.long)
                    out = model(input_ids=token, past_key_values=state,
                                attention_mask=attention, use_cache=True)
                    state, logits = out.past_key_values, out.logits[:, -1, :]
            return torch.cat(tokens, dim=1)

        def baseline():
            return [decode(x) for x in fulls]

        def reused():
            cached_prefix = model(input_ids=prefix, use_cache=True).past_key_values
            return [decode(x, past=cached_prefix, total_prefix=prefix.shape[1]) for x in suffixes]

        def measure(fn):
            start = time.perf_counter()
            result = fn()
            return time.perf_counter() - start, result

        with torch.inference_mode():
            p = model(input_ids=prefix, use_cache=True).past_key_values
            max_error = 0.0
            for full, suffix in zip(fulls, suffixes):
                a = model(input_ids=full, use_cache=True).logits[:, -1, :]
                b = model(input_ids=suffix, past_key_values=copy.deepcopy(p),
                          attention_mask=torch.ones((1, full.shape[1]), dtype=torch.long),
                          use_cache=True).logits[:, -1, :]
                max_error = max(max_error, (a - b).abs().max().item())
                if not torch.allclose(a, b, atol=1e-4, rtol=1e-4) or not torch.equal(a.argmax(-1), b.argmax(-1)):
                    raise RuntimeError('NEXT_TOKEN_LOGIT_MISMATCH')
            a, b = baseline(), reused()
            if len(a) != 3 or any(not torch.equal(x, y) for x, y in zip(a, b)):
                raise RuntimeError('GENERATION_MISMATCH')
            baseline(); reused()  # Untimed paired warm-up
            pairs = []
            for n in range(REPEATS):
                if n % 2:
                    t1, y = measure(reused)
                    t0, x = measure(baseline)
                else:
                    t0, x = measure(baseline)
                    t1, y = measure(reused)
                if any(not torch.equal(i, j) for i, j in zip(x, y)):
                    raise RuntimeError('REPETITION_TOKEN_MISMATCH')
                pairs.append({'baseline_s': t0, 'reused_s': t1, 'speedup': t0 / t1})
            median = statistics.median(p['speedup'] for p in pairs)
            receipt.update({'correctness': 'PASS', 'acceleration': 'PASS_SCREEN' if median >= 1.15 else 'FAIL_SCREEN',
                            'median_paired_speedup': median, 'pairs': pairs,
                            'first_token_max_logit_error': max_error, 'prefix_tokens': prefix.shape[1],
                            'suffix_tokens': [x.shape[1] for x in suffixes],
                            'tokens_per_request': TOKENS, 'requests_per_arm': 3,
                            'baseline': 'manual incremental use_cache=True decoding',
                            'candidate': 'same decoding + reusable cross-request prefix prefill',
                            'qualifier': 'independent five-pair screen; optimized-stack control outstanding'})
    except Exception as e:
        receipt.update({'status': 'FAIL_OR_BLOCKED', 'error': f'{type(e).__name__}: {e}'})
        raise
    finally:
        Path('g54_result.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
        print(json.dumps({k: receipt.get(k) for k in ('gate', 'correctness', 'acceleration', 'median_paired_speedup', 'error')}))

if __name__ == '__main__':
    main()
