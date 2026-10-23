#!/usr/bin/env python3
from __future__ import annotations

import dataclasses
import hashlib
import io
import json
import math
import random
import re
from collections import Counter, defaultdict
from typing import Iterable, Sequence

PAD = 256
BOS = 257
EOS = 258
VOCAB_SIZE = 259
MAX_SOURCE_BYTES = 2048
MAX_TARGET_BYTES = 512
PARAMETER_CEILING = 600_000
INFERENCE_STATE_CEILING = 3_145_728
TRAINING_CHECKPOINT_CEILING = 12_582_912
MANDATORY_SEEDS = (1701, 1702)
CHECKPOINT_EPOCHS = (4, 8, 12)
BATCH_SIZE = 32

_WS = re.compile(r"\s+")
_CLAUSE = re.compile(r"[^.!?;]+[.!?;]?", re.UNICODE)

@dataclasses.dataclass(frozen=True)
class Triple:
    subject: str
    predicate: str
    object: str

@dataclasses.dataclass(frozen=True)
class Example:
    role: str
    graph_sha256: str
    triples: tuple[Triple, ...]
    reference: str

@dataclasses.dataclass(frozen=True)
class CandidateConfig:
    min_template_support: int
    max_templates_per_predicate: int
    joiner: str

@dataclasses.dataclass(frozen=True)
class CheckpointMetric:
    role: str
    seed: int
    epoch: int
    requested_coverage: float
    chrf: float
    missing_triples: int
    retained_model_bytes: int

CANDIDATE_GRID = tuple(
    CandidateConfig(min_support, max_templates, joiner)
    for min_support in (1, 2)
    for max_templates in (4, 8)
    for joiner in (" ", "; ")
)

def normalize_space(value: str) -> str:
    return _WS.sub(" ", value.strip())

def normalize_predicate(value: str) -> str:
    return normalize_space(value).casefold()

def surface_alias(value: str) -> str:
    value = normalize_space(value.replace("_", " "))
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return normalize_space(value)

def graph_serialization(triples: Sequence[Triple]) -> bytes:
    payload = [[normalize_space(t.subject), normalize_space(t.predicate), normalize_space(t.object)] for t in triples]
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

def encode_source(triples: Sequence[Triple]) -> list[int] | None:
    raw = graph_serialization(triples)
    if len(raw) > MAX_SOURCE_BYTES:
        return None
    return list(raw) + [EOS]

def encode_target(text: str) -> tuple[list[int], list[int]] | None:
    raw = normalize_space(text).encode("utf-8")
    if len(raw) > MAX_TARGET_BYTES:
        return None
    return [BOS, *raw], [*raw, EOS]

def decode_generated(ids: Iterable[int]) -> str | None:
    data = bytearray()
    for token in ids:
        if token == EOS:
            break
        if token in (PAD, BOS):
            continue
        if not 0 <= token <= 255:
            return None
        data.append(token)
        if len(data) > MAX_TARGET_BYTES:
            return None
    try:
        return bytes(data).decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return None

def _require_role(examples: Sequence[Example], allowed: set[str]) -> None:
    bad = sorted({e.role for e in examples if e.role not in allowed})
    if bad:
        raise ValueError(f"forbidden role(s): {bad}")

def _replace_once_casefold(text: str, needle: str, replacement: str) -> str | None:
    needle = surface_alias(needle)
    if not needle:
        return None
    pattern = re.compile(re.escape(needle), re.IGNORECASE)
    if not pattern.search(text):
        return None
    return pattern.sub(replacement, text, count=1)

def delex_clause(reference: str, triple: Triple) -> str | None:
    reference = normalize_space(reference)
    subj = surface_alias(triple.subject)
    obj = surface_alias(triple.object)
    if not subj or not obj:
        return None
    for match in _CLAUSE.finditer(reference):
        clause = normalize_space(match.group(0))
        folded = clause.casefold()
        if subj.casefold() not in folded or obj.casefold() not in folded:
            continue
        x = _replace_once_casefold(clause, subj, "{S}")
        if x is None:
            continue
        x = _replace_once_casefold(x, obj, "{O}")
        if x is None or "{S}" not in x or "{O}" not in x:
            continue
        return normalize_space(x)
    return None

def canonical_json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")

def fit_candidate(examples: Sequence[Example]) -> dict:
    _require_role(examples, {"L9_TRAIN"})
    counts: dict[str, Counter] = defaultdict(Counter)
    for ex in examples:
        for triple in ex.triples:
            template = delex_clause(ex.reference, triple)
            if template is not None:
                counts[normalize_predicate(triple.predicate)][template] += 1
    templates = {}
    for predicate, counter in sorted(counts.items()):
        ranked = sorted(counter.items(), key=lambda kv: (-kv[1], len(kv[0].encode("utf-8")), kv[0].encode("utf-8")))
        templates[predicate] = [{"template": t, "support": n} for t, n in ranked[:8]]
    state = {"schema": "l9.compositional-pattern.v1", "templates": templates}
    if len(canonical_json_bytes(state)) > INFERENCE_STATE_CEILING:
        raise ValueError("candidate retained state exceeds ceiling")
    return state

def realize_candidate(state: dict, triples: Sequence[Triple], config: CandidateConfig) -> str | None:
    if config not in CANDIDATE_GRID:
        raise ValueError("candidate config is outside frozen grid")
    clauses = []
    for triple in triples:
        predicate = normalize_predicate(triple.predicate)
        options = state.get("templates", {}).get(predicate, [])[:config.max_templates_per_predicate]
        eligible = [x for x in options if int(x["support"]) >= config.min_template_support]
        if not eligible:
            return None
        template = str(eligible[0]["template"])
        clause = template.replace("{S}", surface_alias(triple.subject)).replace("{O}", surface_alias(triple.object))
        clauses.append(normalize_space(clause))
    return normalize_space(config.joiner.join(clauses)) if clauses else None

def canonical_facts(triples: Sequence[Triple]) -> str:
    return " ".join(f"{surface_alias(t.subject)} {normalize_space(t.predicate)} {surface_alias(t.object)}." for t in triples)

def _graph_sha(triples: Sequence[Triple]) -> str:
    canonical = sorted((normalize_space(t.subject), normalize_space(t.predicate), normalize_space(t.object)) for t in triples)
    payload = json.dumps(canonical, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def _predicate_multiset(triples: Sequence[Triple]) -> Counter:
    return Counter(normalize_predicate(t.predicate) for t in triples)

def _entity_tokens(triples: Sequence[Triple]) -> set[str]:
    toks = set()
    for t in triples:
        for value in (t.subject, t.object):
            toks.update(x for x in re.split(r"\W+", surface_alias(value).casefold()) if x)
    return toks

def _counter_jaccard(a: Counter, b: Counter) -> float:
    keys = set(a) | set(b)
    if not keys:
        return 1.0
    inter = sum(min(a[k], b[k]) for k in keys)
    union = sum(max(a[k], b[k]) for k in keys)
    return inter / union if union else 1.0

def _set_jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if (a or b) else 1.0

def fit_retrieval(examples: Sequence[Example]) -> dict:
    _require_role(examples, {"L9_TRAIN"})
    groups: dict[str, dict] = {}
    for ex in examples:
        gid = _graph_sha(ex.triples)
        ref = normalize_space(ex.reference)
        item = groups.get(gid)
        candidate = (len(ref.encode("utf-8")), ref.encode("utf-8"), ref)
        if item is None or candidate[:2] < (item["reference_bytes"], item["reference_sort"]):
            groups[gid] = {
                "reference": ref,
                "reference_bytes": candidate[0],
                "reference_sort": candidate[1],
                "predicates": dict(_predicate_multiset(ex.triples)),
                "entities": sorted(_entity_tokens(ex.triples)),
            }
    serial = {"schema": "l9.train-reference-retrieval.v1", "graphs": {}}
    for gid, item in sorted(groups.items()):
        serial["graphs"][gid] = {
            "reference": item["reference"],
            "predicates": item["predicates"],
            "entities": item["entities"],
        }
    if len(canonical_json_bytes(serial)) > INFERENCE_STATE_CEILING:
        raise ValueError("retrieval retained state exceeds ceiling")
    return serial

def realize_retrieval(state: dict, triples: Sequence[Triple]) -> str | None:
    gid = _graph_sha(triples)
    graphs = state.get("graphs", {})
    if gid in graphs:
        return graphs[gid]["reference"]
    p = _predicate_multiset(triples)
    e = _entity_tokens(triples)
    ranked = []
    for key, item in graphs.items():
        pred = Counter({str(k): int(v) for k, v in item["predicates"].items()})
        ent = set(item["entities"])
        ranked.append((-_counter_jaccard(p, pred), -_set_jaccard(e, ent), key, item["reference"]))
    if not ranked:
        return None
    ranked.sort()
    return ranked[0][3]

def expected_gru_parameters() -> int:
    emb = 2 * VOCAB_SIZE * 96
    one_gru = 3 * 192 * 96 + 3 * 192 * 192 + 2 * 3 * 192
    out = 192 * VOCAB_SIZE + VOCAB_SIZE
    return emb + 2 * one_gru + out

def expected_transformer_parameters() -> int:
    d, ff = 96, 192
    embedding = VOCAB_SIZE * d
    attention = 3 * d * d + 3 * d + d * d + d
    feedforward = d * ff + ff + ff * d + d
    encoder_layer = attention + feedforward + 2 * (2 * d)
    decoder_layer = 2 * attention + feedforward + 3 * (2 * d)
    encoder = 2 * encoder_layer + 2 * d
    decoder = 2 * decoder_layer + 2 * d
    out = d * VOCAB_SIZE + VOCAB_SIZE
    return embedding + encoder + decoder + out

def _torch():
    import torch
    return torch

def seed_torch(seed: int):
    if seed not in MANDATORY_SEEDS:
        raise ValueError("seed outside frozen mandatory set")
    random.seed(seed)
    torch = _torch()
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    return torch

def build_gru_model():
    torch = _torch()
    nn = torch.nn

    class GRUSeq2Seq(nn.Module):
        def __init__(self):
            super().__init__()
            self.src_embedding = nn.Embedding(VOCAB_SIZE, 96, padding_idx=PAD)
            self.tgt_embedding = nn.Embedding(VOCAB_SIZE, 96, padding_idx=PAD)
            self.encoder = nn.GRU(96, 192, num_layers=1, batch_first=True, dropout=0.0)
            self.decoder = nn.GRU(96, 192, num_layers=1, batch_first=True, dropout=0.0)
            self.output = nn.Linear(192, VOCAB_SIZE)

        def forward(self, src, src_lengths, tgt_in):
            packed = nn.utils.rnn.pack_padded_sequence(
                self.src_embedding(src), src_lengths.cpu(), batch_first=True, enforce_sorted=False
            )
            _, hidden = self.encoder(packed)
            decoded, _ = self.decoder(self.tgt_embedding(tgt_in), hidden)
            return self.output(decoded)

        def greedy(self, src, src_lengths, max_steps=MAX_TARGET_BYTES + 1):
            packed = nn.utils.rnn.pack_padded_sequence(
                self.src_embedding(src), src_lengths.cpu(), batch_first=True, enforce_sorted=False
            )
            _, hidden = self.encoder(packed)
            token = torch.full((src.shape[0], 1), BOS, dtype=torch.long, device=src.device)
            outputs = []
            for _ in range(max_steps):
                decoded, hidden = self.decoder(self.tgt_embedding(token[:, -1:]), hidden)
                logits = self.output(decoded[:, -1, :])
                nxt = logits.argmax(dim=-1, keepdim=True)
                outputs.append(nxt)
                token = torch.cat([token, nxt], dim=1)
                if bool((nxt == EOS).all()):
                    break
            return torch.cat(outputs, dim=1) if outputs else token[:, :0]

    model = GRUSeq2Seq()
    actual = sum(p.numel() for p in model.parameters() if p.requires_grad)
    if actual != expected_gru_parameters() or actual > PARAMETER_CEILING:
        raise RuntimeError(f"GRU parameter identity drift: {actual}")
    return model

def _sinusoidal(torch, length: int, d_model: int):
    position = torch.arange(length, dtype=torch.float32).unsqueeze(1)
    div = torch.exp(torch.arange(0, d_model, 2, dtype=torch.float32) * (-math.log(10000.0) / d_model))
    pe = torch.zeros(length, d_model, dtype=torch.float32)
    pe[:, 0::2] = torch.sin(position * div)
    pe[:, 1::2] = torch.cos(position * div)
    return pe.unsqueeze(0)

def build_transformer_model():
    torch = _torch()
    nn = torch.nn

    class SmallTransformer(nn.Module):
        def __init__(self):
            super().__init__()
            self.embedding = nn.Embedding(VOCAB_SIZE, 96, padding_idx=PAD)
            self.register_buffer("position", _sinusoidal(torch, MAX_SOURCE_BYTES + 2, 96), persistent=False)
            self.transformer = nn.Transformer(
                d_model=96, nhead=4, num_encoder_layers=2, num_decoder_layers=2,
                dim_feedforward=192, dropout=0.1, activation="gelu",
                batch_first=True, norm_first=True
            )
            self.output = nn.Linear(96, VOCAB_SIZE)

        def _embed(self, x):
            if x.shape[1] > self.position.shape[1]:
                raise ValueError("sequence exceeds frozen positional capacity")
            return self.embedding(x) * math.sqrt(96.0) + self.position[:, :x.shape[1], :].to(x.device)

        def forward(self, src, tgt_in):
            tgt_len = tgt_in.shape[1]
            causal = nn.Transformer.generate_square_subsequent_mask(tgt_len, device=tgt_in.device)
            hidden = self.transformer(
                self._embed(src), self._embed(tgt_in),
                tgt_mask=causal,
                src_key_padding_mask=(src == PAD),
                tgt_key_padding_mask=(tgt_in == PAD),
                memory_key_padding_mask=(src == PAD),
            )
            return self.output(hidden)

        def greedy(self, src, max_steps=MAX_TARGET_BYTES + 1):
            token = torch.full((src.shape[0], 1), BOS, dtype=torch.long, device=src.device)
            for _ in range(max_steps):
                logits = self.forward(src, token)[:, -1, :]
                nxt = logits.argmax(dim=-1, keepdim=True)
                token = torch.cat([token, nxt], dim=1)
                if bool((nxt == EOS).all()):
                    break
            return token[:, 1:]

    model = SmallTransformer()
    actual = sum(p.numel() for p in model.parameters() if p.requires_grad)
    if actual != expected_transformer_parameters() or actual > PARAMETER_CEILING:
        raise RuntimeError(f"Transformer parameter identity drift: {actual}")
    return model

def _training_pairs(examples: Sequence[Example]):
    _require_role(examples, {"L9_TRAIN"})
    pairs = []
    excluded_source = excluded_target = 0
    for ex in examples:
        src = encode_source(ex.triples)
        tgt = encode_target(ex.reference)
        if src is None:
            excluded_source += 1
            continue
        if tgt is None:
            excluded_target += 1
            continue
        pairs.append((src, tgt[0], tgt[1]))
    if not pairs:
        raise ValueError("no eligible training pairs")
    return pairs, {"excluded_source_overlength": excluded_source, "excluded_target_overlength": excluded_target}

def _pad(torch, seqs, pad=PAD):
    lengths = torch.tensor([len(x) for x in seqs], dtype=torch.long)
    width = max(int(x) for x in lengths)
    out = torch.full((len(seqs), width), pad, dtype=torch.long)
    for i, seq in enumerate(seqs):
        out[i, :len(seq)] = torch.tensor(seq, dtype=torch.long)
    return out, lengths

def _checkpoint_bytes(torch, model, optimizer=None, epoch=None) -> bytes:
    bio = io.BytesIO()
    payload = {"model": model.state_dict()}
    if optimizer is not None:
        payload["optimizer"] = optimizer.state_dict()
    if epoch is not None:
        payload["epoch"] = int(epoch)
    torch.save(payload, bio)
    return bio.getvalue()

def train_neural(arm: str, examples: Sequence[Example], seed: int, device: str = "cpu") -> dict:
    if arm not in {"GRU_SEQ2SEQ", "SMALL_TRANSFORMER"}:
        raise ValueError("unknown neural arm")
    torch = seed_torch(seed)
    pairs, exclusions = _training_pairs(examples)
    model = build_gru_model() if arm == "GRU_SEQ2SEQ" else build_transformer_model()
    model.to(device)
    lr = 0.001 if arm == "GRU_SEQ2SEQ" else 0.0005
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    checkpoints = {}
    indices = list(range(len(pairs)))
    for epoch in range(1, max(CHECKPOINT_EPOCHS) + 1):
        rng = random.Random(seed * 1000 + epoch)
        rng.shuffle(indices)
        model.train()
        for start in range(0, len(indices), BATCH_SIZE):
            batch = [pairs[i] for i in indices[start:start+BATCH_SIZE]]
            src, src_len = _pad(torch, [x[0] for x in batch])
            tgt_in, _ = _pad(torch, [x[1] for x in batch])
            labels, _ = _pad(torch, [x[2] for x in batch])
            src, src_len, tgt_in, labels = src.to(device), src_len.to(device), tgt_in.to(device), labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(src, src_len, tgt_in) if arm == "GRU_SEQ2SEQ" else model(src, tgt_in)
            loss = torch.nn.functional.cross_entropy(
                logits.reshape(-1, VOCAB_SIZE), labels.reshape(-1), ignore_index=PAD
            )
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
        if epoch in CHECKPOINT_EPOCHS:
            inference = _checkpoint_bytes(torch, model)
            training = _checkpoint_bytes(torch, model, optimizer, epoch)
            if len(inference) > INFERENCE_STATE_CEILING:
                raise ValueError(f"{arm} inference state exceeds ceiling")
            if len(training) > TRAINING_CHECKPOINT_CEILING:
                raise ValueError(f"{arm} training checkpoint exceeds ceiling")
            checkpoints[epoch] = {
                "inference_state": inference,
                "inference_bytes": len(inference),
                "training_checkpoint_bytes": len(training),
            }
    return {"arm": arm, "seed": seed, "checkpoints": checkpoints, "exclusions": exclusions, "model": model}

def choose_checkpoint(metrics: Sequence[CheckpointMetric]) -> dict[int, int]:
    if not metrics:
        raise ValueError("no selection metrics")
    if any(m.role != "L9_SELECT" for m in metrics):
        raise ValueError("checkpoint selection may use L9_SELECT only")
    chosen = {}
    for seed in MANDATORY_SEEDS:
        options = [m for m in metrics if m.seed == seed and m.epoch in CHECKPOINT_EPOCHS]
        if not options:
            raise ValueError(f"missing SELECT metrics for mandatory seed {seed}")
        options.sort(key=lambda m: (
            -m.requested_coverage,
            -m.chrf,
            m.missing_triples,
            m.retained_model_bytes,
            m.epoch,
        ))
        chosen[seed] = options[0].epoch
    return chosen

def assert_audit_not_used(examples: Sequence[Example]) -> None:
    if any(e.role == "L9_AUDIT_DEV" for e in examples):
        raise ValueError("L9_AUDIT_DEV is forbidden before frozen checkpoint selection")
