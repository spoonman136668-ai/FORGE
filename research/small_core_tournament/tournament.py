#!/usr/bin/env python3
"""Standalone, development-only FORGE small-core tournament. Requires PyTorch."""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import math
import os
import platform
import random
import subprocess
import sys
import tempfile
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

# cuBLAS requires this before the first CUDA context for deterministic matmuls.
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import torch
from torch import nn
from torch.nn import functional as F

ENTITIES = 20
MODULUS = 16
CLASSES = ENTITIES + MODULUS
PAD, EDGE, BASE, ADD, SUB, MUL, GRAPH, ARITH = range(CLASSES, CLASSES + 8)
DEPTH = ARITH + 1
TRAIN_DEPTHS = (2, 3, 4)
OOD_DEPTHS = (8, 12)
DEPTH_TOKEN = {hops: DEPTH + hops for hops in (*TRAIN_DEPTHS, *OOD_DEPTHS)}
VOCAB = DEPTH + 1
ROWS = ENTITIES + 1
HEADS = 4
METHODS = ("dense", "scaffold", "scramble", "spectral", "loops", "stability", "pointer", "evolution")
OPTIMIZATION = frozenset(("scaffold", "spectral", "loops", "evolution"))
ANTI_MEMORIZATION = frozenset(("scramble", "stability", "pointer"))
SCHEMA = "forge.small-core-tournament.dev.v1"
CPU_SEED = 1729
GPU_SEEDS = (2718, 3141, 5772)


@dataclass(frozen=True)
class Profile:
    width: int
    dense_hidden: int
    steps: int
    batch: int
    eval_per_task: int
    search_per_task: int


CPU = Profile(64, 1000, 192, 16, 128, 24)
GPU = Profile(192, 7000, 768, 32, 256, 48)


def digest(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def set_seed(seed):
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")


def apply_permutation(tokens, labels, permutation):
    """Rename entity tokens only, including graph answers. Numeric values stay fixed."""
    renamed = torch.where(tokens < ENTITIES, permutation[tokens.clamp(max=ENTITIES - 1)], tokens)
    answers = torch.where(labels < ENTITIES, permutation[labels.clamp(max=ENTITIES - 1)], labels)
    return renamed, answers


def case(rng, task, depth, distractors=False):
    """A directed backbone with distracting leaves, and a random row order."""
    length = rng.randrange(13, 17)
    attachments = sorted(rng.randrange(length) for _ in range(ENTITIES - length))
    if distractors:
        # Concentrate distractors around the queried segment instead of lengthening the prompt.
        attachments = sorted(rng.randrange(max(1, depth)) for _ in attachments)
    parents = [0, *range(length - 1), *attachments]
    rotation = rng.randrange(ENTITIES)
    names = [(index + rotation) % ENTITIES for index in range(ENTITIES)]
    records = []
    if task == GRAPH:
        # The clean label convention contains a deliberately exploitable surface shortcut.
        successors = [*range(1, length), length - 1, *attachments]
        records = [[names[key], names[target], PAD, EDGE] for key, target in enumerate(successors)]
        query = [names[0], DEPTH_TOKEN[depth], PAD, GRAPH]
        target = names[depth]
        signature = (task, length, tuple(attachments))
    else:
        literals = [rng.randrange(MODULUS) for _ in range(ENTITIES)]
        ops = [BASE, *(rng.choice((ADD, SUB, MUL)) for _ in range(ENTITIES - 1))]
        values = [literals[0]]
        records.append([names[0], PAD, ENTITIES + literals[0], BASE])
        for key, parent in enumerate(parents[1:], start=1):
            left, right, op = values[parent], literals[key], ops[key]
            result = {ADD: left + right, SUB: left - right, MUL: left * right}[op]
            values.append(result % MODULUS)
            records.append([names[key], names[parent], ENTITIES + right, op])
        query = [names[depth], DEPTH_TOKEN[depth], PAD, ARITH]
        target = ENTITIES + values[depth]
        signature = (
            task, length, tuple(zip(ops[:length], literals[:length])),
            tuple(sorted(zip(attachments, ops[length:], literals[length:]))),
        )
    rng.shuffle(records)
    return [query, *records], target, digest(signature)


def draw(rng, stage, split, depth, count, task, device, distractors=False):
    # Across rounds and splits, a structure has exactly one owner bucket.
    offset = 5 * (stage - 1)
    buckets = {"train": {offset, offset + 1, offset + 2},
               "search": {offset + 3}, "eval": {offset + 4}}[split]
    tokens, labels, signatures, permutations = [], [], [], []
    while len(tokens) < count:
        hops = rng.choice(TRAIN_DEPTHS) if depth is None else depth
        row, label, key = case(rng, task, hops, distractors)
        if int(key[:8], 16) % 15 not in buckets:
            continue
        names = list(range(ENTITIES))
        while True:
            rng.shuffle(names)
            if all(i != j for i, j in enumerate(names)):
                break
        swapped = names.copy()
        # A minority of clean examples are already relabeled. Every token is in the same vocabulary.
        if rng.random() < 0.25:
            rng.shuffle(names)
            row = [[names[value] if value < ENTITIES else value for value in item] for item in row]
            label = names[label] if label < ENTITIES else label
        tokens.append(row)
        labels.append(label)
        signatures.append(key)
        permutations.append(swapped)
    x = torch.tensor(tokens, device=device)
    y = torch.tensor(labels, device=device)
    pairing = torch.tensor(permutations, device=device)
    swapped_x = torch.where(x < ENTITIES, pairing.gather(1, x.flatten(1).clamp(max=ENTITIES - 1)).view_as(x), x)
    swapped_y = torch.where(y < ENTITIES, pairing.gather(1, y[:, None].clamp(max=ENTITIES - 1))[:, 0], y)
    return x, y, swapped_x, swapped_y, permutations, signatures


def build_data(profile, seed, stage, device):
    rng = random.Random(73_751 + seed)
    half_batch = profile.batch // 2
    streams = [
        draw(rng, stage, "train", None, profile.steps * half_batch, task, device)
        for task in (GRAPH, ARITH)
    ]
    train = tuple(
        torch.cat([group[column].reshape(profile.steps, half_batch, *group[column].shape[1:])
                   for group in streams], dim=1)
        for column in (0, 1, 2, 3)
    )

    def evaluation(split, count, distractors=False):
        return {
            f"{bucket}/{name}": draw(rng, stage, split, depth, count, task, device, distractors)
            for bucket, depth in (("id", None), *((f"ood{hops}", hops) for hops in OOD_DEPTHS))
            if split != "search" or bucket == "id"
            for name, task in (("graph", GRAPH), ("arithmetic", ARITH))
        }

    search = evaluation("search", profile.search_per_task)
    test = evaluation("eval", profile.eval_per_task)
    if stage > 1:
        test.update({f"noisy/{key}": val for key, val in evaluation("eval", profile.eval_per_task, True).items()})

    def fingerprint(groups):
        return digest([[[item.cpu().tolist() for item in group[:4]], group[5]] for group in groups])

    return train, search, test, {
        "train": fingerprint(streams), "search": fingerprint(search.values()), "evaluation": fingerprint(test.values()),
    }


class FeedForward(nn.Module):
    """Dense FFN with an optional exactly sized, used residual weight slice."""

    def __init__(self, width, hidden, remainder=0, *, nonlinear=True):
        super().__init__()
        self.nonlinear = nonlinear
        self.up = nn.Linear(width, hidden, bias=False)
        self.down = nn.Linear(hidden, width, bias=False)
        self.tail = nn.Parameter(torch.zeros(remainder)) if remainder else None

    def forward(self, x):
        projected = self.up(x)
        out = self.down(F.gelu(projected) if self.nonlinear else projected)
        if self.tail is None:
            return out
        width = x.size(-1)
        direct, shifted = self.tail[:width], self.tail[width:]
        out = out + F.pad(x[..., :direct.numel()] * direct, (0, width - direct.numel()))
        if shifted.numel():
            out = out + F.pad(x.roll(1, -1)[..., :shifted.numel()] * shifted, (0, width - shifted.numel()))
        return out


class DenseBlock(nn.Module):
    def __init__(self, width, hidden, remainder):
        super().__init__()
        self.query_key_value = nn.Linear(width, 3 * width, bias=False)
        self.mix = nn.Linear(width, width, bias=False)
        self.attn_norm = nn.LayerNorm(width)
        self.ff_norm = nn.LayerNorm(width)
        self.ff = FeedForward(width, hidden, remainder)

    def forward(self, state, topology):
        batch, rows, width = state.shape
        q, k, v = self.query_key_value(self.attn_norm(state)).reshape(
            batch, rows, 3, HEADS, width // HEADS
        ).permute(2, 0, 3, 1, 4)
        scores = (q @ k.transpose(-1, -2)) / math.sqrt(width // HEADS)
        if topology is not None:
            scores = scores.masked_fill(~topology, float("-inf"))
        attention = (scores.softmax(dim=-1) @ v).transpose(1, 2).reshape_as(state)
        state = state + self.mix(attention)
        return state + self.ff(self.ff_norm(state))


class SpectralBlock(nn.Module):
    """Four fixed orthogonal operators in a DCT basis, with top-2 routing per band."""

    def __init__(self, width, hidden, remainder):
        super().__init__()
        self.route = FeedForward(width, hidden, remainder)
        self.norm = nn.LayerNorm(width, elementwise_affine=False)
        i = torch.arange(width, dtype=torch.float64)
        basis = (torch.pi / width * (i[:, None] + 0.5) * i[None, :]).cos() * math.sqrt(2 / width)
        basis[:, 0] /= math.sqrt(2)
        self.register_buffer("basis", basis.float(), persistent=False)

    def forward(self, state, topology):
        normalized = self.norm(state)
        attention = (normalized @ normalized.transpose(-1, -2) / math.sqrt(state.size(-1))).softmax(-1)
        context = attention @ normalized
        spectrum = context @ self.basis
        bands = state.size(-1) // 4
        coefficients = self.route(context).unflatten(-1, (4, bands))
        top = coefficients.topk(2, dim=-2).indices
        selected = torch.zeros_like(coefficients, dtype=torch.bool).scatter_(-2, top, True)
        gains = coefficients.masked_fill(~selected, float("-inf")).softmax(dim=-2)
        operators = torch.stack([spectrum.roll(j * bands, -1) for j in range(4)], dim=-2)
        return state + (operators * gains.repeat_interleave(4, dim=-1)).sum(-2) @ self.basis.T


class PointerBlock(nn.Module):
    """Read immutable per-example rows through a learned, explicit soft pointer."""

    def __init__(self, width, hidden, remainder):
        super().__init__()
        self.address = nn.Linear(width, width, bias=False)
        self.key = nn.Linear(width, width, bias=False)
        self.values = FeedForward(width, hidden, remainder, nonlinear=False)
        self.gate = nn.Linear(2 * width, width)
        self.norm = nn.LayerNorm(width)

    def prepare(self, keys, values, allowed):
        allowed = allowed.expand(keys.size(0), 1, keys.size(1))
        return self.key(keys), self.values(values), allowed

    def forward(self, state, memory):
        keys, values, allowed = memory
        pointer = (self.address(state) @ keys.transpose(-1, -2)).masked_fill(~allowed, float("-inf"))
        read = (pointer / math.sqrt(state.size(-1))).softmax(-1) @ values
        gate = self.gate(torch.cat((state, read), dim=-1)).sigmoid()
        return self.norm(state + gate * read)


class Scaffold(nn.Module):
    """A train-only low-rank residual whose maximum initial rank equals core width."""

    def __init__(self, width):
        super().__init__()
        self.up = nn.Parameter(torch.empty(width, width))
        self.down = nn.Parameter(torch.empty(width, width))
        nn.init.orthogonal_(self.up)
        nn.init.orthogonal_(self.down)

    def forward(self, state, step_fraction):
        # Each singular direction fades continuously across its own rank interval.
        if step_fraction >= 1:
            return state
        width = self.up.size(0)
        remaining = min(float(width), width * (1 - step_fraction))
        rank = math.ceil(remaining)
        lifted = state @ self.up[:rank].T
        if remaining < rank:
            faded = lifted[..., -1:] * (remaining - rank + 1)
            lifted = torch.cat((lifted[..., :-1], faded), dim=-1)
        return state + 0.25 * (lifted @ self.down[:, :rank].T)


def split_capacity(extra, width):
    """Partition exact parameter slack between two fully used projections."""
    hidden, remainder = divmod(extra, 2 * width)
    if hidden < 2:
        raise ValueError("parameter target too small for core")
    return (hidden // 2, 0), (hidden - hidden // 2, remainder)


class Model(nn.Module):
    def __init__(self, profile, method):
        super().__init__()
        flags = set(method.split("+"))
        width = self.width = profile.width
        self.kind = "pointer" if "pointer" in flags else "spectral" if "spectral" in flags else "dense"
        self.embedding = nn.Embedding(VOCAB, width // 4)
        self.readout = nn.Linear(width, CLASSES)
        self.final_norm = nn.LayerNorm(width)
        self.halt = nn.Linear(2, 1) if "loops" in flags else None
        if self.halt is not None:
            nn.init.zeros_(self.halt.weight)
            nn.init.constant_(self.halt.bias, -0.3)
        self.scratch_key = nn.Linear(width // 4, width, bias=False) if self.kind == "pointer" else None
        shared = VOCAB * (width // 4) + (width + 1) * CLASSES + 2 * width
        dense_fixed = 2 * (4 * width * width + 4 * width)
        self.target = shared + dense_fixed + 4 * width * profile.dense_hidden
        fixed, block = {
            "dense": (dense_fixed, DenseBlock),
            "spectral": (0, SpectralBlock),
            "pointer": (width * (width // 4) + 2 * (4 * width * width + 3 * width), PointerBlock),
        }[self.kind]
        halt_count = 3 if self.halt is not None else 0
        widths = split_capacity(self.target - shared - fixed - halt_count, width)
        self.blocks = nn.ModuleList(block(width, hidden, rest) for hidden, rest in widths)
        self.scaffold = Scaffold(width) if "scaffold" in flags else None
        self.register_buffer("answer_is_entity", torch.arange(CLASSES) < ENTITIES, persistent=False)

    def counts(self):
        train = sum(p.numel() for p in self.parameters() if p.requires_grad)
        scaffold = sum(p.numel() for p in self.scaffold.parameters()) if self.scaffold is not None else 0
        return train, train - scaffold

    def embed_rows(self, tokens):
        # All queries share a learned marker. One fixed coordinate carries the hop count.
        embedded = self.embedding(tokens.clamp(max=DEPTH))
        hops = (tokens[:, 0, 1] - DEPTH).clamp_min(0)
        embedded[:, 0, 1, 0] += hops / max(TRAIN_DEPTHS)
        return embedded.flatten(-2)

    def forward(self, tokens, *, step_fraction=1.0, topology=None):
        embedded = self.embed_rows(tokens)
        state = embedded[:, :1] if self.kind == "pointer" else embedded
        if self.scaffold is not None and self.training:
            state = self.scaffold(state, step_fraction)
        if self.kind == "pointer":
            keys = self.scratch_key(self.embedding(tokens[:, 1:, 0]))
            allowed = tokens.new_ones((2, ENTITIES), dtype=torch.bool) if topology is None else topology[:2, 0, 1:]
            memories = [
                block.prepare(keys, embedded[:, 1:], mask[None, None])
                for block, mask in zip(self.blocks, allowed)
            ]
        else:
            memories = [topology, topology]

        alive = state.new_ones((state.size(0), 1, 1))
        total_steps = state.new_zeros((state.size(0), 1, 1))
        active = torch.arange(state.size(0), device=state.device)
        max_sweeps = 3 if self.halt is not None else 2 if self.kind == "pointer" else 1
        for sweep in range(max_sweeps):
            previous = state
            if self.halt is not None and not self.training and sweep > 0:
                active = active[alive.index_select(0, active).flatten() > 0]
                if active.numel() == 0:
                    break
                proposed = state.index_select(0, active)
                for block, memory in zip(self.blocks, memories):
                    subset = tuple(value.index_select(0, active) for value in memory) if self.kind == "pointer" else memory
                    proposed = block(proposed, subset)
                state = state.index_copy(0, active, proposed)
            else:
                proposed = state
                for block, memory in zip(self.blocks, memories):
                    proposed = block(proposed, memory)
                state = previous + alive * (proposed - previous)
            total_steps = total_steps + alive
            if self.halt is not None:
                delta = (state[:, :1] - previous[:, :1]).square().mean(-1, keepdim=True)
                signal = torch.cat((delta, torch.full_like(delta, (sweep + 1) / max_sweeps)), dim=-1)
                probability = self.halt(signal).sigmoid()
                keep = (probability < 0.5).to(state.dtype)
                if self.training:
                    keep = keep + (probability.detach() - probability)
                alive = alive * keep

        hidden = self.final_norm(state)
        logits = self.readout(hidden[:, 0])
        allowed = (tokens[:, :1, -1] == GRAPH) == self.answer_is_entity
        return logits.masked_fill(~allowed, float("-inf")), hidden, total_steps.mean()


def topology_for(seed, device):
    generator = torch.Generator().manual_seed(seed)
    links = torch.rand((HEADS, ROWS, ROWS), generator=generator) > 0.3
    links |= torch.eye(ROWS, dtype=torch.bool)
    links[:, :, 0] = True
    links[:, 0, 1] = True
    return links.to(device)


def fraction_at(update, steps):
    return min(1.0, update / max(1, (3 * steps) // 4))


def contraction_flops(model, batch, fraction=1.0):
    """Count 2 FLOPs/MAC for forward contractions at maximum latent depth."""
    width = model.width
    sweeps = 3 if model.halt is not None else 2 if model.kind == "pointer" else 1
    readout = width * CLASSES
    halt = sweeps * 2 if model.halt is not None else 0
    if model.kind == "pointer":
        prep = ENTITIES * width * (width // 4)
        for block in model.blocks:
            prep += ENTITIES * (width * width + 2 * width * block.values.up.out_features)
        per_sweep = 2 * (3 * width * width + 2 * ENTITIES * width)
        state_rows = 1
    else:
        prep = 0
        per_sweep = 0
        for block in model.blocks:
            ff_width = block.ff.up.out_features if model.kind == "dense" else block.route.up.out_features
            linear = (4 if model.kind == "dense" else 2) * width * width + 2 * width * ff_width
            per_sweep += ROWS * linear + 2 * ROWS * ROWS * width
        state_rows = ROWS
    scaffold = 0
    if model.scaffold is not None and fraction < 1:
        scaffold = state_rows * 2 * width * math.ceil(width * (1 - fraction))
    return 2 * batch * (prep + sweeps * per_sweep + halt + readout + scaffold)


def train_cost(model, method, batch, fraction):
    # Forward plus two corresponding backward contractions per matrix multiply.
    views = 2 if "stability" in method.split("+") else 1
    return views * 3 * contraction_flops(model, batch, fraction)


def optimizer_for(model):
    return torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01, foreach=False)


def update_model(model, optimizer, batch, method, fraction, topology, permutation_rng):
    flags = method.split("+")
    x, target, swapped, swapped_target = batch
    if "scramble" in flags:
        names = torch.randperm(ENTITIES, generator=permutation_rng).to(x.device)
        x, target = apply_permutation(x, target, names)
    optimizer.zero_grad(set_to_none=True)
    logits, hidden, steps = model(x, step_fraction=fraction, topology=topology)
    loss = F.cross_entropy(logits, target)
    if "stability" in flags:
        second, paired_hidden, _ = model(swapped, step_fraction=fraction, topology=topology)
        agreement = 1.0 - F.cosine_similarity(hidden, paired_hidden, dim=-1).mean()
        loss = 0.5 * (loss + F.cross_entropy(second, swapped_target)) + 0.2 * agreement
    if model.halt is not None:
        loss = loss + 0.01 * steps
    if not loss.isfinite().item():
        raise FloatingPointError("non-finite training loss")
    loss.backward()
    norm = nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0, foreach=False)
    if not norm.isfinite().item():
        raise FloatingPointError("non-finite gradient")
    optimizer.step()
    return loss.detach().item(), steps.detach().item()


@torch.inference_mode()
def evaluate(model, datasets, batch_size, topology=None, *, paired=True, predictions=False):
    model.eval()
    metrics = {}
    for key, (x, target, swapped, swapped_target, names, signatures) in datasets.items():
        outputs = []
        for rows in x.split(batch_size):
            logits, _, sweeps = model(rows, topology=topology)
            outputs.append((logits.argmax(-1), sweeps))
        clean = torch.cat([output[0] for output in outputs])
        before = clean.eq(target)
        result = {
            "count": len(x), "correct": int(before.sum()),
            "mean_sweeps": sum(float(output[1]) * len(output[0]) for output in outputs) / len(x),
            "unique_structures": len(set(signatures)),
        }
        if paired:
            renamed = torch.cat([model(rows, topology=topology)[0].argmax(-1) for rows in swapped.split(batch_size)])
            after = renamed.eq(swapped_target)
            mapping = torch.tensor(names, device=x.device)
            expected = torch.where(clean < ENTITIES,
                                   mapping.gather(1, clean[:, None].clamp(max=ENTITIES - 1))[:, 0], clean)
            result.update(swapped_correct=int(after.sum()), clean_correct_swapped_wrong=int((before & ~after).sum()),
                          prediction_equivariant=int(renamed.eq(expected).sum()))
            if predictions:
                result.update(
                    target=target.tolist(), clean_prediction=clean.tolist(), renamed_target=swapped_target.tolist(),
                    renamed_prediction=renamed.tolist(), permutation=names, structure=signatures,
                )
        metrics[key] = result
    return metrics


def accuracy(metrics):
    return sum(row["correct"] for row in metrics.values()) / sum(row["count"] for row in metrics.values())


def summarize(metrics):
    clean = {key: row for key, row in metrics.items() if not key.startswith("noisy/")}
    summary = {
        "id": accuracy({key: row for key, row in clean.items() if key.startswith("id/")}),
        "ood": accuracy({key: row for key, row in clean.items() if key.startswith("ood")}),
        "clean": accuracy(clean),
    }
    for depth in ("ood8", "ood12"):
        summary[depth] = accuracy({key: row for key, row in clean.items() if key.startswith(depth)})
    count = sum(row["count"] for row in clean.values())
    summary["substituted"] = sum(row["swapped_correct"] for row in clean.values()) / count
    # The integer difference avoids unstable subtraction at strictly tied gates.
    summary["signed_gap"] = sum(row["correct"] - row["swapped_correct"] for row in clean.values()) / count
    summary["drop"] = max(0.0, summary["signed_gap"])
    summary["clean_correct_swapped_wrong"] = sum(row["clean_correct_swapped_wrong"] for row in clean.values()) / count
    summary["prediction_equivariance"] = sum(row["prediction_equivariant"] for row in clean.values()) / count
    summary["mean_inference_sweeps"] = sum(row["mean_sweeps"] * row["count"] for row in clean.values()) / count
    noisy = {key: row for key, row in metrics.items() if key.startswith("noisy/ood")}
    if noisy:
        summary["noisy_ood"] = accuracy(noisy)
    return summary


@torch.no_grad()
def prune_half(model, random_seed=None):
    parameters = [p for name, p in model.named_parameters() if p.requires_grad and not name.startswith("scaffold.")]
    magnitudes = torch.cat([p.flatten().abs() for p in parameters])
    pruned = magnitudes.numel() // 2
    if random_seed is None:
        order = magnitudes.argsort(stable=True)
    else:
        generator = torch.Generator().manual_seed(random_seed)
        order = torch.randperm(magnitudes.numel(), generator=generator).to(magnitudes.device)
    mask = torch.ones_like(magnitudes, dtype=torch.bool)
    mask[order[:pruned]] = False
    for parameter, keep in zip(parameters, mask.split([p.numel() for p in parameters])):
        parameter.mul_(keep.reshape_as(parameter))
    return pruned


def sync(device):
    if device.type == "cuda":
        torch.cuda.synchronize(device)


def run_arm(profile, method, seed, device, datasets, budget, stage):
    set_seed(seed)
    train, search, test, _ = datasets
    sync(device)
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
    start = time.perf_counter()
    cpu_start = time.process_time()
    model = Model(profile, method).to(device)
    counts = model.counts()
    if counts[1] != model.target:
        raise RuntimeError(f"{method} does not match the dense parameter count")
    optimizer = optimizer_for(model)
    mutation_rng = random.Random(seed + 184)
    permutation_rng = torch.Generator().manual_seed(seed + 195)
    update = 0
    charged = 0
    history = []
    population = []
    winner_topology = None
    winner_seed = None
    failure = None

    def check_budget(amount):
        if charged + amount > budget:
            raise RuntimeError("common training contraction budget exceeded")

    def burst(candidate, candidate_optimizer, length, topology):
        nonlocal update, charged
        candidate.train()
        for _ in range(length):
            fraction = fraction_at(update, profile.steps)
            cost = train_cost(candidate, method, profile.batch, fraction)
            check_budget(cost)
            charged += cost
            batch = [column[update] for column in train]
            update += 1
            loss, steps = update_model(candidate, candidate_optimizer, batch, method, fraction, topology, permutation_rng)
            history.append((loss, steps))

    try:
        if "evolution" in method.split("+"):
            length = max(1, min(16, profile.steps // 12))
            for generation in range(2):
                candidates = []
                for member in range(3):
                    # Each generation inherits the previous winner's weights; topology seed mutates.
                    if member == 0 and winner_seed is not None:
                        candidate_seed = winner_seed
                    else:
                        candidate_seed = ((winner_seed or 0) ^ mutation_rng.randrange(1, 2**31)) % (2**31)
                    candidate = copy.deepcopy(model)
                    candidate_optimizer = torch.optim.SGD(candidate.parameters(), lr=0.015, momentum=0.9, weight_decay=0.01)
                    topology = topology_for(candidate_seed, device)
                    burst(candidate, candidate_optimizer, length, topology)
                    search_count = sum(len(rows[0]) for rows in search.values())
                    cost = contraction_flops(candidate, search_count)
                    check_budget(cost)
                    charged += cost
                    score = accuracy(evaluate(candidate, search, profile.batch, topology, paired=False))
                    population.append({
                        "generation": generation, "topology_seed": candidate_seed, "search_accuracy": score,
                    })
                    candidates.append((score, candidate_seed, candidate))
                _, winner_seed, model = max(candidates, key=lambda row: (row[0], -row[1]))
                winner_topology = topology_for(winner_seed, device)
                del candidates, candidate, candidate_optimizer
            optimizer = optimizer_for(model)
        burst(model, optimizer, profile.steps - update, winner_topology)
    except FloatingPointError as error:
        failure = str(error)

    sync(device)
    train_seconds = time.perf_counter() - start
    result = {
        "method": method, "seed": seed, "train_parameters": counts[0], "inference_parameters": counts[1],
        "steps": update, "training_examples": update * profile.batch,
        "charged_training_contraction_flops": charged, "training_contraction_flops_cap": budget,
        "train_seconds": train_seconds, "training_host_cpu_seconds": time.process_time() - cpu_start,
        "failure_mode": failure,
        "initial_loss": history[0][0] if history else None, "last_loss": history[-1][0] if history else None,
        "mean_training_sweeps": sum(row[1] for row in history) / len(history) if history else None,
        "scratchpad_raw_bytes_per_example": ENTITIES * 4 * 8 if model.kind == "pointer" else 0,
        "population_search": population, "winning_topology_seed": winner_seed,
    }
    if failure is not None:
        return result

    sync(device)
    start = time.perf_counter()
    buckets = evaluate(model, test, profile.batch, winner_topology, predictions=True)
    result.update(summary=summarize(buckets), buckets=buckets)
    if stage == 2:
        random_control = copy.deepcopy(model)
        result["pruned_parameters"] = prune_half(model)
        result["pruned_summary"] = summarize(evaluate(model, test, profile.batch, winner_topology))
        result["random_pruned_parameters"] = prune_half(random_control, random_seed=seed + 707)
        result["random_pruned_summary"] = summarize(evaluate(random_control, test, profile.batch, winner_topology))
    sync(device)
    result["evaluation_seconds"] = time.perf_counter() - start
    if device.type == "cuda":
        result["cuda_peak_allocated_bytes"] = torch.cuda.max_memory_allocated(device)
    return result


def common_budget(profile, methods):
    envelopes = []
    for method in methods:
        model = Model(profile, method)
        max_step = train_cost(model, method, profile.batch, 0.0)
        search_cost = contraction_flops(model, 2 * profile.search_per_task) if "evolution" in method.split("+") else 0
        envelopes.append(profile.steps * max_step + 6 * search_cost)
    return max(envelopes)


def classify(round_runs, methods, stage):
    by_method = {method: [run for run in round_runs if run["method"] == method] for method in methods}
    baseline = {run["seed"]: run for run in by_method["dense"]}
    decisions = {}
    candidates = []
    roster = {method: index for index, method in enumerate(methods)}
    for method, runs in by_method.items():
        failures, improvement = [], []
        for run in runs:
            dense = baseline[run["seed"]]
            run["wall_clock_ratio"] = run["train_seconds"] / dense["train_seconds"]
            if run["failure_mode"]:
                failures.append(f"seed {run['seed']}: {run['failure_mode']}")
                continue
            if "summary" not in dense:
                failures.append(f"seed {run['seed']}: dense baseline diverged")
                continue
            if method == "dense":
                continue
            current, reference = run["summary"], dense["summary"]
            ood_gain = current["ood"] - reference["ood"]
            drop_gain = reference["drop"] - current["drop"]
            run["deltas_vs_dense"] = {
                "id": current["id"] - reference["id"], "ood": ood_gain,
                "substitution_drop": current["drop"] - reference["drop"],
            }
            improvement.append((ood_gain, drop_gain))
            if ood_gain <= 0:
                failures.append(f"seed {run['seed']}: OOD accuracy did not beat dense")
            if drop_gain <= 0:
                failures.append(f"seed {run['seed']}: substitution drop did not beat dense")
            if run["wall_clock_ratio"] > 2 and run["wall_clock_ratio"] * (1 - current["ood"]) > 1 - reference["ood"]:
                failures.append(f"seed {run['seed']}: >2x training time without proportional OOD error reduction")
        if method == "dense":
            decisions[method] = {"verdict": "REFERENCE" if not failures else "FAIL", "reasons": failures}
            continue
        if not failures and stage > 1:
            mean_ood, mean_drop = (sum(gain) / len(gain) for gain in zip(*improvement))
            if min(mean_ood, mean_drop) < 0.02:
                failures.append("mean gains did not both reach 2 percentage points")
        if failures:
            decisions[method] = {"verdict": "ELIMINATED", "reasons": failures}
        else:
            candidates.append((min(gain for pair in improvement for gain in pair), method))

    ordered = [method for _, method in sorted(candidates, key=lambda item: (-item[0], roster[item[1]]))]
    finalists = ordered[:4 if stage == 1 else 3]
    for method in ordered:
        decisions[method] = {
            "verdict": "ADVANCE" if method in finalists else "ELIMINATED",
            "reasons": [] if method in finalists else ["ranked below the advancement cutoff"],
        }
    return decisions, finalists


def synthesis_comparison(runs, methods):
    combined = methods[-1]
    by_seed = {(run["seed"], run["method"]): run for run in runs}
    comparisons = {}
    for run in (row for row in runs if row["method"] == combined):
        cells = {}
        for method in methods[:-1]:
            reference = by_seed[run["seed"], method]
            if "summary" in reference and "summary" in run:
                target, control = run["summary"], reference["summary"]
                cells[method] = {
                    "ood_gain": target["ood"] - control["ood"],
                    "substitution_drop_reduction": control["drop"] - target["drop"],
                }
        comparisons[str(run["seed"])] = cells
    complete = all(len(row) == len(methods) - 1 for row in comparisons.values())
    contrasts = [[row[method] for row in comparisons.values()] for method in methods[:-1]] if complete else []
    replicated = complete and all(
        all(all(value > 0 for value in row.values()) for row in contrast)
        and all(sum(row[metric] for row in contrast) / len(contrast) >= 0.02 for metric in contrast[0])
        for contrast in contrasts
    )
    return {"combined": combined, "per_seed": comparisons, "beats_all_comparators": replicated}


def source_info():
    script = Path(__file__).resolve()
    source = {"script_sha256": hashlib.sha256(script.read_bytes()).hexdigest()}
    try:
        rel = subprocess.check_output(["git", "-C", str(script.parent), "rev-parse", "--show-prefix"],
                                      text=True, stderr=subprocess.DEVNULL).strip() + script.name
        sha, tree = subprocess.check_output(["git", "-C", str(script.parent), "rev-parse", "HEAD", "HEAD^{tree}"],
                                            text=True, stderr=subprocess.DEVNULL).split()
        committed = subprocess.check_output(["git", "-C", str(script.parent), "show", f"{sha}:{rel}"],
                                            stderr=subprocess.DEVNULL)
        if hashlib.sha256(committed).hexdigest() == source["script_sha256"]:
            source.update(commit=sha, tree=tree)
    except (OSError, subprocess.CalledProcessError):
        pass  # Uploaded Colab copies still carry a hash of the exact standalone source.
    return source


def warm_runtime(profile, device):
    """Prime shared kernels and lazy optimizer imports before the first arm is timed."""
    set_seed(0)
    model = Model(profile, "dense").to(device)
    optimizer = optimizer_for(model)
    fixture = torch.full((profile.batch, ROWS, 4), PAD, device=device)
    fixture[:, 0, -1] = GRAPH
    target = torch.arange(profile.batch, device=device) % ENTITIES
    for _ in range(2):
        optimizer.zero_grad(set_to_none=True)
        logits, _, _ = model(fixture)
        F.cross_entropy(logits, target).backward()
        optimizer.step()
    sync(device)


def make_receipt(stage, profile, methods, seeds, device, reference=None, review_ref=None):
    source = source_info()
    warm_runtime(profile, device)
    budget = common_budget(profile, methods)
    runs, fingerprints = [], {}
    started = time.perf_counter()
    for seed in seeds:
        datasets = build_data(profile, seed, stage, device)
        fingerprints[str(seed)] = datasets[3]
        for method in methods:
            run = run_arm(profile, method, seed, device, datasets, budget, stage)
            runs.append(run)
            cells = run.get("summary", {})
            print(f"round {stage} seed {seed} {method}: ID={cells.get('id')} OOD={cells.get('ood')} "
                  f"drop={cells.get('drop')} train={run['train_seconds']:.3f}s failure={run['failure_mode']}", flush=True)
    if source_info() != source:
        raise RuntimeError("tournament source changed during the run")
    decisions, finalists = classify(runs, methods, stage)
    receipt = {
        "schema": SCHEMA, "evidence_class": "SYNTHETIC_DEVELOPMENT_ONLY", "round": stage,
        "source": source, "configuration": asdict(profile), "methods": list(methods),
        "device": str(device), "hardware": torch.cuda.get_device_name(device) if device.type == "cuda" else platform.machine(),
        "platform": platform.platform(), "python": sys.version.split()[0], "torch": str(torch.__version__),
        "torch_threads": torch.get_num_threads(), "seeds": list(seeds),
        "data_fingerprints": fingerprints, "reference_receipt_sha256": reference, "owner_review_reference": review_ref,
        "training_budget": {"updates": profile.steps, "contraction_flops_cap": budget},
        "runs": runs, "decisions": decisions, "finalists": finalists,
        "total_seconds": time.perf_counter() - started,
    }
    if stage == 3:
        receipt["synthesis"] = synthesis_comparison(runs, methods)
    return {**receipt, "receipt_sha256": digest(receipt)}


def read_previous(path, expected_round):
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as compressed:
            receipt = json.load(compressed)
    else:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    claimed = receipt.pop("receipt_sha256", None)
    if claimed != digest(receipt) or receipt.get("schema") != SCHEMA or receipt.get("round") != expected_round:
        raise ValueError("receipt hash, schema, or round mismatch")
    if receipt.get("source", {}).get("script_sha256") != source_info()["script_sha256"]:
        raise ValueError("previous receipt came from a different runner source")
    if expected_round == 2 and receipt.get("status") == "NO_ELIGIBLE_ARMS" and receipt.get("finalists") == []:
        return {**receipt, "receipt_sha256": claimed}
    expected_profile = CPU if expected_round == 1 else GPU
    expected_seeds = [CPU_SEED] if expected_round == 1 else list(GPU_SEEDS)
    if receipt["configuration"] != asdict(expected_profile) or receipt["seeds"] != expected_seeds:
        raise ValueError("previous receipt does not use the fixed tournament profile")
    if expected_round == 1 and receipt["methods"] != list(METHODS):
        raise ValueError("Round 1 has an incomplete roster")
    if ("dense" not in receipt["methods"] or len(receipt["methods"]) != len(set(receipt["methods"]))
            or not set(receipt["methods"]) <= set(METHODS)):
        raise ValueError("unknown or duplicate method in previous receipt")
    identities = [(row["method"], row["seed"]) for row in receipt["runs"]]
    if Counter(identities) != Counter((method, seed) for method in receipt["methods"] for seed in expected_seeds):
        raise ValueError("missing or repeated method/seed results in previous receipt")
    decisions, finalists = classify(receipt["runs"], receipt["methods"], expected_round)
    if decisions != receipt["decisions"] or finalists != receipt["finalists"]:
        raise ValueError("previous receipt decisions do not match the frozen gate")
    if decisions["dense"]["verdict"] != "REFERENCE":
        raise ValueError("previous receipt has no valid baseline")
    return {**receipt, "receipt_sha256": claimed}


def synthesis_arms(finalists):
    optimization = next((method for method in finalists if method in OPTIMIZATION), None)
    anti_memorization = next((method for method in finalists if method in ANTI_MEMORIZATION), None)
    if optimization is None or anti_memorization is None:
        return ()
    return ("dense", optimization, anti_memorization, f"{optimization}+{anti_memorization}")


def save_receipt(path, receipt):
    # Publish the finished receipt atomically, with an exclusive destination.
    with tempfile.TemporaryDirectory(dir=path.parent) as draft:
        temp = Path(draft, "receipt")
        content = (json.dumps(receipt, sort_keys=True, allow_nan=False) + "\n").encode()
        if path.suffix == ".gz":
            content = gzip.compress(content, mtime=0)
        temp.write_bytes(content)
        os.link(temp, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round", type=int, choices=(1, 2, 3), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--previous", type=Path, help="Receipt from the previous round")
    parser.add_argument("--owner-review", help="Reference to the FORGE-native owner decision for this run")
    options = parser.parse_args()
    if options.output.exists() or not options.output.parent.is_dir():
        parser.error("choose an unused output path in an existing directory")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    if options.round == 1:
        if options.previous or options.owner_review:
            parser.error("Round 1 uses the development CPU work order")
        receipt = make_receipt(1, CPU, METHODS, (CPU_SEED,), torch.device("cpu"))
    else:
        if not options.previous or not (options.owner_review or "").strip():
            parser.error("GPU rounds require the previous receipt and a FORGE-native owner review reference")
        try:
            previous = read_previous(options.previous, options.round - 1)
        except (OSError, ValueError, KeyError, TypeError) as error:
            parser.error(str(error))
        methods = ("dense", *previous["finalists"]) if options.round == 2 else synthesis_arms(previous["finalists"])
        if len(methods) < 2:
            receipt = {
                "schema": SCHEMA, "evidence_class": "SYNTHETIC_DEVELOPMENT_ONLY", "round": options.round,
                "source": source_info(), "reference_receipt_sha256": previous["receipt_sha256"],
                "owner_review_reference": options.owner_review, "status": "NO_ELIGIBLE_ARMS", "finalists": [],
            }
            save_receipt(options.output, {**receipt, "receipt_sha256": digest(receipt)})
            print(f"round {options.round}: no eligible arms; receipt={options.output}")
            return
        if not torch.cuda.is_available():
            parser.error("choose a CUDA GPU runtime in Colab for Round 2 or 3")
        receipt = make_receipt(options.round, GPU, methods, GPU_SEEDS, torch.device("cuda"),
                               previous["receipt_sha256"], options.owner_review)
    save_receipt(options.output, receipt)
    print(f"receipt={options.output} sha256={receipt['receipt_sha256']} finalists={receipt['finalists']}")


if __name__ == "__main__":
    main()
