"""FORGE Core Multi-Method Experimental Training Benchmarks (Gate 17).

Provides real, deterministic, pure-stdlib micro-training entrypoints executed
inside isolated workspaces by `f139/nci04_experiment_runner.py` and
`f139/nci04_training_campaign.py` across three distinct theoretical method tracks:
  1. `LLM-Experimental` — Next-token sequence prediction comparing baseline SGD,
     clipped momentum, and trust-region adaptive updates (real cross-entropy).
  2. `GLM-WorldModel` — Latent state-transition world model under regime shift
     comparing linear dynamics vs. slow-fast residual consolidation (OOD MSE).
  3. `AGI-Kernel` — Sequential 3-task continual learning measuring retention +
     forward transfer without catastrophic forgetting (composite retention).

Zero paid model calls, zero external dependencies, deterministic via
`FORGE_EXPERIMENT_SEEDS`, writes real metrics to `FORGE_METRICS_OUT` and
serialized model checkpoints to `FORGE_CHECKPOINT_DIR` (never auto-promoted).
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import random
import sys


def _seeds_from_env() -> list[int]:
    raw = os.environ.get("FORGE_EXPERIMENT_SEEDS", "13,29,53")
    return [int(s.strip()) for s in raw.split(",") if s.strip()]


def _softmax(logits: list[float]) -> list[float]:
    m = max(logits)
    exps = [math.exp(max(-40.0, min(40.0, z - m))) for z in logits]
    s = sum(exps)
    return [e / s for e in exps]


def run_llm_experimental(variant: str) -> dict:
    """Real bigram/trigram-context next-token micro-training (vocab=8, ctx=8)."""
    seeds = _seeds_from_env()
    vocab = 8
    losses: list[float] = []
    final_weights: list[list[float]] = []

    for seed in seeds:
        rng = random.Random(seed + 100)
        # Ground-truth stochastic Markov transition matrix (sharpened non-uniform)
        true_probs = []
        for i in range(vocab):
            row = [0.05] * vocab
            row[(i + 1) % vocab] = 0.55
            row[(i + 3) % vocab] = 0.25
            s = sum(row)
            true_probs.append([p / s for p in row])

        def sample_next(cur: int) -> int:
            u = rng.random()
            acc = 0.0
            for idx, p in enumerate(true_probs[cur]):
                acc += p
                if u <= acc:
                    return idx
            return vocab - 1

        # Train stream (180 tokens) + held-out eval stream (80 tokens)
        train_seq = [0]
        for _ in range(180):
            train_seq.append(sample_next(train_seq[-1]))
        eval_seq = [rng.randrange(vocab)]
        for _ in range(80):
            eval_seq.append(sample_next(eval_seq[-1]))

        W = [[0.0] * vocab for _ in range(vocab)]
        V = [[0.0] * vocab for _ in range(vocab)]
        G2 = [[1e-4] * vocab for _ in range(vocab)]

        for epoch in range(4):
            for t in range(len(train_seq) - 1):
                x, y = train_seq[t], train_seq[t + 1]
                probs = _softmax(W[x])
                for j in range(vocab):
                    grad = probs[j] - (1.0 if j == y else 0.0)
                    if variant == "sgd_baseline":
                        W[x][j] -= 0.12 * grad
                    elif variant == "momentum_clipped":
                        g_clip = max(-0.5, min(0.5, grad))
                        V[x][j] = 0.75 * V[x][j] + g_clip
                        W[x][j] -= 0.14 * V[x][j]
                    elif variant == "l2_cosine_sgd":
                        progress = (epoch * len(train_seq) + t) / float(4 * len(train_seq))
                        lr = 0.04 + 0.22 * (0.5 * (1.0 + math.cos(math.pi * progress)))
                        target_p = (1.0 - 0.06) if j == y else (0.06 / (vocab - 1))
                        sm_grad = probs[j] - target_p
                        W[x][j] -= lr * (sm_grad + 0.004 * W[x][j])
                    elif variant == "trust_region_adaptive":
                        G2[x][j] = 0.90 * G2[x][j] + 0.10 * (grad * grad)
                        step = 0.28 * grad / (math.sqrt(G2[x][j]) + 0.05)
                        step = max(-0.35, min(0.35, step))
                        W[x][j] = max(-4.0, min(4.0, W[x][j] - step))
                    else:
                        raise ValueError(f"Unknown LLM variant: {variant}")

        ce = 0.0
        for t in range(len(eval_seq) - 1):
            probs = _softmax(W[eval_seq[t]])
            ce += -math.log(max(1e-9, probs[eval_seq[t + 1]]))
        losses.append(ce / (len(eval_seq) - 1))
        final_weights = W

    mean_loss = round(sum(losses) / len(losses), 6)
    return {
        "metrics": {
            "val_loss": mean_loss,
            "perplexity": round(math.exp(min(20.0, mean_loss)), 6),
            "variant": variant,
        },
        "checkpoint": {"variant": variant, "weights_sample": final_weights[:2]},
    }


def run_glm_world_model(variant: str) -> dict:
    """Real latent state-transition world-model micro-training under regime shift."""
    seeds = _seeds_from_env()
    dim = 4
    ood_mses: list[float] = []
    last_state: dict = {}

    for seed in seeds:
        rng = random.Random(seed + 200)
        A_base = [rng.uniform(-0.8, 0.8) for _ in range(dim)]
        A_shift = [A_base[i] + rng.uniform(-0.6, 0.6) for i in range(dim)]

        w_slow = [0.0] * dim
        w_fast = [0.0] * dim

        # Phase 1: Base world dynamics (50 steps)
        for _ in range(50):
            s = [rng.gauss(0.0, 0.8) for _ in range(dim)]
            y = sum(A_base[i] * s[i] for i in range(dim)) + rng.gauss(0.0, 0.04)
            pred = sum((w_slow[i] + w_fast[i]) * s[i] for i in range(dim))
            err = y - pred
            for i in range(dim):
                w_slow[i] += 0.15 * err * s[i]

        # Phase 2: Shifted world dynamics with outlier spikes (25 steps)
        errs = []
        for step in range(25):
            s = [rng.gauss(0.0, 0.8) for _ in range(dim)]
            y_clean = sum(A_shift[i] * s[i] for i in range(dim))
            y_obs = y_clean + (8.0 if step in (6, 12) else rng.gauss(0.0, 0.04))
            pred = sum((w_slow[i] + w_fast[i]) * s[i] for i in range(dim))
            if step >= 15:
                errs.append((y_clean - pred) ** 2)
            err = y_obs - pred
            if variant == "linear_dynamics_baseline":
                for i in range(dim):
                    w_slow[i] += 0.12 * err * s[i]
            elif variant == "slow_fast_world_model":
                c_err = max(-0.9, min(0.9, err))
                for i in range(dim):
                    w_fast[i] = max(-1.5, min(1.5, 0.90 * w_fast[i] + 0.25 * c_err * s[i]))
                    if abs(err) <= 1.5:
                        w_slow[i] = max(-3.0, min(3.0, w_slow[i] + 0.03 * w_fast[i]))
            else:
                raise ValueError(f"Unknown GLM variant: {variant}")

        ood_mses.append(sum(errs) / len(errs))
        last_state = {"w_slow": [round(x, 5) for x in w_slow], "w_fast": [round(x, 5) for x in w_fast]}

    mean_mse = round(sum(ood_mses) / len(ood_mses), 6)
    return {
        "metrics": {"ood_mse": mean_mse, "variant": variant},
        "checkpoint": last_state,
    }


def run_agi_kernel(variant: str) -> dict:
    """Real 3-task continual learning micro-benchmark measuring retention + transfer."""
    seeds = _seeds_from_env()
    dim = 4
    avg_mses: list[float] = []
    last_ckpt: dict = {}

    for seed in seeds:
        rng = random.Random(seed + 300)
        tasks = [
            [rng.uniform(-0.9, 0.9) for _ in range(dim)]
            for _ in range(3)
        ]
        # Shared slow core + per-task consolidated anchor for elastic kernel
        w = [0.0] * dim
        anchor = [0.0] * dim
        importance = [0.0] * dim

        for tidx, w_true in enumerate(tasks):
            for _ in range(35):
                x = [rng.gauss(0.0, 0.7) for _ in range(dim)]
                y = sum(w_true[i] * x[i] for i in range(dim))
                pred = sum(w[i] * x[i] for i in range(dim))
                err = y - pred
                for i in range(dim):
                    grad = -err * x[i]
                    if variant == "naive_finetune_baseline":
                        w[i] -= 0.18 * grad
                    elif variant == "elastic_consolidated_kernel":
                        reg = importance[i] * (w[i] - anchor[i])
                        w[i] -= 0.16 * (grad + 0.35 * reg)
                    else:
                        raise ValueError(f"Unknown AGI variant: {variant}")
            if variant == "elastic_consolidated_kernel":
                for i in range(dim):
                    anchor[i] = (anchor[i] * tidx + w[i]) / (tidx + 1)
                    importance[i] += 0.6

        # Evaluate across ALL 3 tasks after sequential training
        task_errs = []
        for w_true in tasks:
            for _ in range(15):
                x = [rng.gauss(0.0, 0.7) for _ in range(dim)]
                y = sum(w_true[i] * x[i] for i in range(dim))
                pred = sum(w[i] * x[i] for i in range(dim))
                task_errs.append((y - pred) ** 2)
        avg_mses.append(sum(task_errs) / len(task_errs))
        last_ckpt = {"w": [round(v, 5) for v in w], "anchor": [round(v, 5) for v in anchor]}

    mean_mse = round(sum(avg_mses) / len(avg_mses), 6)
    return {
        "metrics": {"continual_mse": mean_mse, "variant": variant},
        "checkpoint": last_ckpt,
    }


def _emit(result: dict) -> None:
    metrics_out = os.environ.get("FORGE_METRICS_OUT")
    ckpt_dir = os.environ.get("FORGE_CHECKPOINT_DIR")
    if ckpt_dir:
        Path(ckpt_dir, "checkpoint.json").write_text(
            json.dumps(result["checkpoint"], sort_keys=True), encoding="utf-8"
        )
    if metrics_out:
        Path(metrics_out).write_text(
            json.dumps(result["metrics"], sort_keys=True), encoding="utf-8"
        )
    else:
        print(json.dumps(result["metrics"], sort_keys=True))


if __name__ == "__main__":
    # Invoked via thin wrapper scripts or directly with `FORGE_METHOD_TASK=family:variant`
    spec_str = os.environ.get("FORGE_METHOD_TASK", "")
    if len(sys.argv) >= 2:
        spec_str = sys.argv[1]
    family, _, variant = spec_str.partition(":")
    if family == "LLM-Experimental":
        _emit(run_llm_experimental(variant))
    elif family == "GLM-WorldModel":
        _emit(run_glm_world_model(variant))
    elif family == "AGI-Kernel":
        _emit(run_agi_kernel(variant))
    else:
        raise SystemExit(f"Unsupported FORGE_METHOD_TASK: {spec_str!r}")
