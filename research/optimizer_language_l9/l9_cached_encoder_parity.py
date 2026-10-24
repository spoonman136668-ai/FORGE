#!/usr/bin/env python3
"""Isolated efficient conventional Transformer inference; frozen L9 untouched.

Engineering-only synthetic CPU equivalence probe. No WebNLG source reads,
TRAIN/SELECT/AUDIT/TEST inference, checkpoint loads, or scientific first-use.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

FROZEN_MODEL_BLOB = "710ce648a30ffc55647f689c5f4aa3ac13b07066"
FROZEN_SELECT_BLOB = "91f8108af5e6f3a25e2a8ca07dc3674bd2358f4e"
FROZEN_ROLE_SHA = "b9995c1846f5e1d99bf8bc4083dde0ebb41140906284bcf050a7ed6fe0efe726"


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def require_frozen_source(root: Path) -> None:
    original = (root / "l9_model_suite.py").read_bytes()
    selector = (root / "l9_neural_select_only.py").read_bytes()
    if git_blob(original) != FROZEN_MODEL_BLOB or git_blob(selector) != FROZEN_SELECT_BLOB:
        raise ValueError("L9_CACHED_PARITY_ABORT_FROZEN_SOURCE_IDENTITY_DRIFT")


def cached_encoder_greedy(net, src, *, max_steps: int):
    """Exact nn.Transformer encoder/decoder components; no altered model weights.

    Reuses unchanged encoder memory across generated tokens. Decoder still
    recomputes growing prefixes; this is NOT a key/value-cache implementation.
    Same EOS/argmax/byte cap, masks, positional encodings and frozen weights as
    SmallTransformer.greedy. Call only with eval()/inference_mode().
    """
    import torch
    from l9_model_suite import PAD, BOS, EOS
    if net.training:
        raise ValueError("L9_CACHED_PARITY_REQUIRES_EVAL")
    if type(max_steps) is not int or max_steps < 1 or max_steps > 513:
        raise ValueError("L9_CACHED_PARITY_BAD_STEP_CAP")
    if src.ndim != 2 or src.shape[0] != 1 or src.shape[1] < 1:
        raise ValueError("L9_CACHED_PARITY_REQUIRES_SINGLE_GRAPH")
    if src.dtype != torch.long or torch.any(src == PAD):
        raise ValueError("L9_CACHED_PARITY_REQUIRES_UNPADDED_SOURCE")
    source_pad = (src == PAD)
    memory = net.transformer.encoder(net._embed(src), src_key_padding_mask=source_pad)
    token = torch.full((src.shape[0], 1), BOS, dtype=torch.long, device=src.device)
    for _ in range(max_steps):
        causal = torch.nn.Transformer.generate_square_subsequent_mask(
            token.shape[1], device=token.device)
        hidden = net.transformer.decoder(
            net._embed(token), memory,
            tgt_mask=causal,
            tgt_key_padding_mask=(token == PAD),
            memory_key_padding_mask=source_pad)
        next_id = net.output(hidden)[:, -1, :].argmax(dim=-1, keepdim=True)
        token = torch.cat([token, next_id], dim=1)
        if bool((next_id == EOS).all()):
            break
    return token[:, 1:]


def synthetic_equivalence(*, seeds=(1701, 1702, 31), steps: int = 12) -> dict:
    import torch
    import l9_model_suite as frozen

    require_frozen_source(Path(__file__).resolve().parent)
    torch.set_num_threads(2)
    tests = []
    for seed, source in zip(seeds, ((1, 2, 3, 4, 5, 6),
                                   tuple(range(3, 100)),
                                   (20, 22, 99, 127))):
        torch.manual_seed(seed)
        net = frozen.build_transformer_model().eval()
        src = torch.tensor([source], dtype=torch.long)
        observed = {"encoder_calls": 0}
        def observe(_module, _args, _output):
            observed["encoder_calls"] += 1
        handle = net.transformer.encoder.register_forward_hook(observe)
        try:
            with torch.inference_mode():
                original = net.greedy(src, max_steps=steps)
                original_calls = observed["encoder_calls"]
                observed["encoder_calls"] = 0
                cached = cached_encoder_greedy(net, src, max_steps=steps)
                cached_calls = observed["encoder_calls"]
                if not torch.equal(original, cached):
                    raise AssertionError("L9_CACHED_PARITY_GREEDY_TOKEN_DIVERGENCE")
                if original_calls != original.shape[1] or cached_calls != 1:
                    raise AssertionError("L9_CACHED_PARITY_ENCODER_CALL_MISMATCH")
                # Compare logits at multiple matched prefixes, not merely tokens.
                prefix = torch.cat([
                    torch.full((1, 1), frozen.BOS, dtype=torch.long),
                    original[:, :min(4, max(original.shape[1] - 1, 0))]
                ], dim=1)
                full_logits = net.forward(src, prefix)[:, -1, :]
                memory = net.transformer.encoder(net._embed(src),
                    src_key_padding_mask=(src == frozen.PAD))
                causal = torch.nn.Transformer.generate_square_subsequent_mask(
                    prefix.shape[1], device=prefix.device)
                decoded = net.transformer.decoder(
                    net._embed(prefix), memory, tgt_mask=causal,
                    tgt_key_padding_mask=(prefix == frozen.PAD),
                    memory_key_padding_mask=(src == frozen.PAD))
                cached_logits = net.output(decoded)[:, -1, :]
                max_error = (full_logits - cached_logits).abs().max().item()
                if not torch.allclose(full_logits, cached_logits, rtol=0, atol=2e-6):
                    raise AssertionError("L9_CACHED_PARITY_LOGIT_DIVERGENCE")
                tests.append({
                    "seed": seed,
                    "source_tokens": len(source),
                    "generated_tokens": original.shape[1],
                    "old_encoder_invocations": original_calls,
                    "cached_encoder_invocations": cached_calls,
                    "max_abs_logit_difference": max_error,
                    "exact_token_equivalence": True,
                })
        finally:
            handle.remove()

    report = {
        "schema": "forge.optimizer.language.l9.cached-encoder-synthetic-parity-v1",
        "frozen_model_git_blob": FROZEN_MODEL_BLOB,
        "frozen_selector_git_blob": FROZEN_SELECT_BLOB,
        "source_role_sha256": FROZEN_ROLE_SHA,
        "torch": torch.__version__,
        "synthetic_only": True,
        "checkpoint_weights_loaded": False,
        "train_select_audit_test_loaded": False,
        "original_frozen_greedy_changed": False,
        "original_frozen_selection_jobs_changed": False,
        "kv_cache_implemented": False,
        "model_quality_improvement_claimed": False,
        "scientific_cost_pareto_qualified": False,
        "test_cases": tests,
        "disposition": "SYNTHETIC_ENCODER_CACHING_EQUIVALENCE_ONLY",
    }
    return report


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("L9_CACHED_PARITY_RECEIPT_OVERWRITE")
    r = synthetic_equivalence()
    args.out.write_bytes((json.dumps(r, sort_keys=True,
                   separators=(",", ":")) + "\n").encode("utf-8"))
    print("L9_CACHED_ENCODER_SYNTHETIC_PARITY=PASS")
    print("L9_SCIENTIFIC_COST_PARETO_QUALIFIED=FALSE")


if __name__ == "__main__":
    main()
